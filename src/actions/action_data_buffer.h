#pragma once

#include <stdint.h>
#include <string.h>

/**
 * ActionDataBuffer
 *
 * Generic 8-byte data buffer for multi-sensor data collection.
 * Allows actions to write sensor readings into specific buffer slots,
 * then send all accumulated data in a single CAN message.
 *
 * Design:
 * - Fixed 8-byte buffer (matches CAN message size)
 * - Slot-based addressing (slots 0-7)
 * - Tracks which bytes are valid/used
 * - Zero-overhead abstraction for embedded systems
 *
 * Example Usage:
 *   ActionDataBuffer buffer;
 *
 *   // Read GPIO into slot 0
 *   uint8_t gpio_value = 1;
 *   buffer.write(0, &gpio_value, 1);
 *
 *   // Read 16-bit ADC into slots 1-2
 *   uint16_t adc_value = 1023;
 *   buffer.write(1, (uint8_t*)&adc_value, 2);
 *
 *   // Read 3-byte I2C sensor into slots 3-5
 *   uint8_t i2c_data[3] = {10, 20, 30};
 *   buffer.write(3, i2c_data, 3);
 *
 *   // Send buffer as CAN message
 *   uint8_t length;
 *   const uint8_t* data = buffer.read_all(length);
 *   can->send_message(0x600, data, length);
 *   buffer.clear();
 */
class ActionDataBuffer {
public:
    /**
     * Constructor - initializes buffer to all zeros
     */
    ActionDataBuffer();

    /**
     * Write data to buffer at specified slot
     *
     * @param slot Starting slot index (0-7)
     * @param data Pointer to data to write
     * @param length Number of bytes to write
     * @return true if successful, false if out of bounds
     */
    bool write(uint8_t slot, const uint8_t* data, uint8_t length);

    /**
     * Write single byte to buffer slot
     *
     * @param slot Slot index (0-7)
     * @param value Byte value to write
     * @return true if successful
     */
    bool write_byte(uint8_t slot, uint8_t value);

    /**
     * Write 16-bit value to buffer (little-endian)
     *
     * @param slot Starting slot index (0-6)
     * @param value 16-bit value to write
     * @return true if successful
     */
    bool write_uint16(uint8_t slot, uint16_t value);

    /**
     * Write 32-bit value to buffer (little-endian)
     *
     * @param slot Starting slot index (0-4)
     * @param value 32-bit value to write
     * @return true if successful
     */
    bool write_uint32(uint8_t slot, uint32_t value);

    /**
     * Read entire buffer for transmission
     *
     * @param valid_length Output: number of valid bytes (highest used slot + 1)
     * @return Pointer to buffer data (always 8 bytes, check valid_length)
     */
    const uint8_t* read_all(uint8_t& valid_length) const;

    /**
     * Read single byte from buffer slot
     *
     * @param slot Slot index (0-7)
     * @param value Output: byte value
     * @return true if slot is valid and used
     */
    bool read_byte(uint8_t slot, uint8_t& value) const;

    /**
     * Get pointer to raw buffer (for direct access)
     * Use with caution - prefer write() methods
     *
     * @return Pointer to 8-byte buffer
     */
    const uint8_t* get_raw_buffer() const;

    /**
     * Get used length (highest used slot + 1)
     *
     * @return Number of bytes that should be sent
     */
    uint8_t get_used_length() const;

    /**
     * Check if a specific slot is marked as used
     *
     * @param slot Slot index (0-7)
     * @return true if slot contains valid data
     */
    bool is_slot_used(uint8_t slot) const;

    /**
     * Clear entire buffer and reset all slot markers
     */
    void clear();

    /**
     * Clear specific slot range
     *
     * @param start_slot First slot to clear (0-7)
     * @param length Number of slots to clear
     * @return true if successful
     */
    bool clear_range(uint8_t start_slot, uint8_t length);

private:
    uint8_t buffer_[8];       // 8-byte data buffer
    bool slot_used_[8];       // Tracks which bytes contain valid data

    /**
     * Validate slot bounds
     *
     * @param slot Starting slot
     * @param length Length in bytes
     * @return true if access is within bounds
     */
    inline bool is_valid_access(uint8_t slot, uint8_t length) const {
        return (slot < 8) && (length > 0) && (slot + length <= 8);
    }
};

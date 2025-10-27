#pragma once

#include <stdint.h>
#include <stdbool.h>

/**
 * I2CInterface
 *
 * Abstract base class for platform-agnostic I2C communication.
 * Each platform (SAMD51, RP2040, ESP32, STM32) implements this interface.
 *
 * Design Goals:
 * - Platform-independent action logic
 * - Pin validation integrated into interface
 * - Error reporting via get_last_error()
 * - Zero-overhead virtual calls in release builds
 *
 * Usage:
 *   I2CInterface* i2c = create_platform_i2c();  // Factory
 *
 *   if (i2c->initialize(PA12, PA13, 100000)) {
 *       uint8_t data[3];
 *       if (i2c->read(0x68, 0x3B, data, 3)) {
 *           // Process accelerometer data
 *       }
 *   }
 */
class I2CInterface {
public:
    virtual ~I2CInterface() {}

    /**
     * Initialize I2C peripheral with specific pins
     *
     * @param sda_pin SDA pin number (platform-specific)
     * @param scl_pin SCL pin number (platform-specific)
     * @param frequency_hz I2C clock frequency (default 100kHz)
     * @return true if initialization successful
     */
    virtual bool initialize(uint8_t sda_pin, uint8_t scl_pin, uint32_t frequency_hz = 100000) = 0;

    /**
     * Write data to I2C device register
     *
     * @param address 7-bit I2C device address (0-127)
     * @param reg Register address to write to
     * @param data Pointer to data bytes
     * @param length Number of bytes to write
     * @return true if write successful
     */
    virtual bool write(uint8_t address, uint8_t reg, const uint8_t* data, uint8_t length) = 0;

    /**
     * Write single byte to I2C device register
     *
     * @param address 7-bit I2C device address
     * @param reg Register address
     * @param value Byte value to write
     * @return true if write successful
     */
    virtual bool write_byte(uint8_t address, uint8_t reg, uint8_t value) = 0;

    /**
     * Read data from I2C device register
     *
     * @param address 7-bit I2C device address (0-127)
     * @param reg Register address to read from
     * @param data Pointer to buffer for received data
     * @param length Number of bytes to read
     * @return true if read successful
     */
    virtual bool read(uint8_t address, uint8_t reg, uint8_t* data, uint8_t length) = 0;

    /**
     * Read single byte from I2C device register
     *
     * @param address 7-bit I2C device address
     * @param reg Register address
     * @param value Output: byte value read
     * @return true if read successful
     */
    virtual bool read_byte(uint8_t address, uint8_t reg, uint8_t& value) = 0;

    /**
     * Validate if pin can be used for I2C SDA
     * Platform-specific validation
     *
     * @param pin Pin number to validate
     * @return true if pin supports SDA
     */
    virtual bool is_valid_sda_pin(uint8_t pin) const = 0;

    /**
     * Validate if pin can be used for I2C SCL
     * Platform-specific validation
     *
     * @param pin Pin number to validate
     * @return true if pin supports SCL
     */
    virtual bool is_valid_scl_pin(uint8_t pin) const = 0;

    /**
     * Get last error message
     * Useful for debugging and user feedback
     *
     * @return Pointer to error string (empty if no error)
     */
    virtual const char* get_last_error() const = 0;

    /**
     * Check if I2C peripheral is initialized and ready
     *
     * @return true if initialized
     */
    virtual bool is_initialized() const = 0;

    /**
     * Deinitialize I2C peripheral
     * Frees pins and disables peripheral
     */
    virtual void deinitialize() = 0;

    /**
     * Scan I2C bus for devices
     * Useful for debugging and device discovery
     *
     * @param found_addresses Output: array to store found addresses
     * @param max_addresses Maximum number of addresses to store
     * @return Number of devices found
     */
    virtual uint8_t scan_bus(uint8_t* found_addresses, uint8_t max_addresses) = 0;
};

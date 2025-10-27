#pragma once

#include <stdint.h>
#include <stdbool.h>

/**
 * SAMD51 Pin Capabilities
 *
 * Defines compile-time pin capability tables for SAMD51 Feather M4 CAN.
 * Used for validating pin usage before allocation.
 *
 * Design:
 * - Compile-time constant tables (zero runtime overhead)
 * - Platform-specific (SAMD51 only)
 * - Integrates with PinManager for runtime validation
 *
 * References:
 * - SAMD51_PIN_REFERENCE.md for complete pin mapping
 * - Adafruit Feather M4 CAN schematic
 */

/**
 * Pin Capabilities Structure
 *
 * Describes what a specific pin can do on SAMD51.
 */
struct PinCapabilities {
    uint8_t pin_number;        // Arduino pin number
    bool can_gpio;             // Can be used as digital GPIO
    bool can_pwm;              // Supports PWM via TCC
    bool can_adc;              // Has ADC channel
    bool can_dac;              // Has DAC output
    bool can_i2c_sda;          // Can be I2C SDA (via SERCOM)
    bool can_i2c_scl;          // Can be I2C SCL (via SERCOM)
    uint8_t sercom_instance;   // SERCOM number (0-5), 0xFF if none
    uint8_t sercom_pad;        // SERCOM pad number (0-3), 0xFF if none
    uint8_t tcc_instance;      // TCC instance (0-2), 0xFF if none
    uint8_t tcc_channel;       // TCC channel (0-7), 0xFF if none
    bool is_reserved;          // Reserved by hardware (CAN, USB)
    const char* pin_name;      // Human-readable name (e.g., "PA12", "A0")
};

/**
 * Get pin capabilities for a specific pin
 *
 * @param pin Arduino pin number
 * @return Pointer to capabilities structure, nullptr if pin not found
 */
const PinCapabilities* samd51_get_pin_capabilities(uint8_t pin);

/**
 * Validate if pin supports specific mode
 *
 * @param pin Arduino pin number
 * @param mode Intended pin mode (from pin_manager.h PinMode enum)
 * @return true if pin supports this mode
 */
bool samd51_validate_pin_for_mode(uint8_t pin, uint8_t mode);

/**
 * Check if pin is hardware-reserved (CAN, USB, etc)
 *
 * @param pin Arduino pin number
 * @return true if pin is reserved and cannot be used
 */
bool samd51_is_pin_reserved(uint8_t pin);

/**
 * Get SERCOM instance and pad for I2C pin
 *
 * @param pin Arduino pin number
 * @param is_sda true for SDA, false for SCL
 * @param sercom_out Output: SERCOM instance (0-5)
 * @param pad_out Output: SERCOM pad (0-3)
 * @return true if pin supports I2C and sercom/pad found
 */
bool samd51_get_i2c_sercom(uint8_t pin, bool is_sda, uint8_t& sercom_out, uint8_t& pad_out);

/**
 * Get TCC instance and channel for PWM pin
 *
 * @param pin Arduino pin number
 * @param tcc_out Output: TCC instance (0-2)
 * @param channel_out Output: TCC channel (0-7)
 * @return true if pin supports PWM and tcc/channel found
 */
bool samd51_get_pwm_tcc(uint8_t pin, uint8_t& tcc_out, uint8_t& channel_out);

/**
 * Initialize pin capability system
 * Marks hardware-reserved pins in PinManager
 *
 * @param pin_mgr Pointer to PinManager instance
 */
void samd51_init_pin_capabilities(class PinManager* pin_mgr);

/**
 * Log pin capability information to Serial
 * Useful for debugging
 *
 * @param pin Arduino pin number
 */
void samd51_log_pin_capabilities(uint8_t pin);

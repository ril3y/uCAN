#pragma once

#include <stdint.h>
#include "../utils/pin_error_logger.h"

/**
 * Pin Modes
 *
 * Defines the different ways a pin can be used.
 * Tracks pin allocation at runtime to prevent conflicts.
 */
enum PinMode : uint8_t {
    PINMODE_UNUSED = 0,        // Pin not allocated
    PINMODE_GPIO_INPUT,        // Digital input
    PINMODE_GPIO_OUTPUT,       // Digital output
    PINMODE_PWM,               // PWM output
    PINMODE_ADC,               // Analog input
    PINMODE_DAC,               // Analog output (DAC)
    PINMODE_I2C_SDA,           // I2C data line
    PINMODE_I2C_SCL,           // I2C clock line
    PINMODE_SPI_MOSI,          // SPI data out
    PINMODE_SPI_MISO,          // SPI data in
    PINMODE_SPI_SCK,           // SPI clock
    PINMODE_SPI_CS,            // SPI chip select
    PINMODE_RESERVED           // Reserved by hardware (CAN, USB, etc)
};

/**
 * PinManager
 *
 * Manages pin allocation and usage tracking at runtime.
 * Prevents pin conflicts by tracking which pins are in use.
 *
 * Design:
 * - Static allocation tracking (no heap allocation)
 * - Validates pin availability before allocation
 * - Integrates with platform-specific capability tables
 * - Logs errors via pin_error_logger
 *
 * Example Usage:
 *   PinManager pin_mgr;
 *
 *   // Allocate pin 13 for PWM
 *   if (!pin_mgr.allocate_pin(13, PIN_PWM)) {
 *       // Allocation failed - pin in use or not PWM-capable
 *   }
 *
 *   // Free pin when done
 *   pin_mgr.free_pin(13);
 *
 *   // Check availability before use
 *   if (pin_mgr.is_available(13, PIN_GPIO_OUTPUT)) {
 *       // Safe to use pin 13 for GPIO output
 *   }
 */
class PinManager {
public:
    /**
     * Constructor - initializes all pins as unused
     */
    PinManager();

    /**
     * Allocate a pin for specific mode
     *
     * @param pin Pin number to allocate
     * @param mode Intended pin mode
     * @return true if allocated successfully, false if already in use or invalid
     */
    bool allocate_pin(uint8_t pin, PinMode mode);

    /**
     * Free a previously allocated pin
     *
     * @param pin Pin number to free
     */
    void free_pin(uint8_t pin);

    /**
     * Get current usage mode of a pin
     *
     * @param pin Pin number to query
     * @return Current PinMode (PIN_UNUSED if not allocated)
     */
    PinMode get_usage(uint8_t pin) const;

    /**
     * Check if pin is available for intended mode
     * Does not modify allocation state
     *
     * @param pin Pin number to check
     * @param intended_mode Intended usage mode
     * @return true if pin can be allocated for this mode
     */
    bool is_available(uint8_t pin, PinMode intended_mode) const;

    /**
     * Check if pin is currently allocated
     *
     * @param pin Pin number to check
     * @return true if pin is in use
     */
    bool is_allocated(uint8_t pin) const;

    /**
     * Check if two modes are compatible
     * Some modes can coexist (e.g., GPIO input can become ADC)
     *
     * @param current Current pin mode
     * @param intended Intended pin mode
     * @return true if modes are compatible
     */
    bool are_modes_compatible(PinMode current, PinMode intended) const;

    /**
     * Clear all pin allocations
     * Used during initialization or reset
     */
    void clear_all();

    /**
     * Log current pin allocation status to Serial
     * Useful for debugging
     */
    void log_pin_status() const;

    /**
     * Get string representation of pin mode
     *
     * @param mode Pin mode
     * @return String name of mode
     */
    static const char* mode_to_string(PinMode mode);

private:
    static constexpr uint8_t MAX_PINS = 32;  // Maximum pin count for SAMD51
    PinMode usage_map_[MAX_PINS];            // Current usage for each pin

    /**
     * Validate pin number is within bounds
     *
     * @param pin Pin number
     * @return true if valid
     */
    inline bool is_valid_pin(uint8_t pin) const {
        return pin < MAX_PINS;
    }
};

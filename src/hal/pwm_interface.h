#pragma once

#include <stdint.h>
#include <stdbool.h>

/**
 * PWMInterface
 *
 * Abstract base class for platform-agnostic PWM control.
 * Each platform (SAMD51, RP2040, ESP32, STM32) implements this interface.
 *
 * Design Goals:
 * - Platform-independent PWM configuration
 * - Frequency and resolution control (not just duty cycle)
 * - Pin validation integrated into interface
 * - TCC/Timer channel management abstracted
 *
 * Usage:
 *   PWMInterface* pwm = create_platform_pwm();  // Factory
 *
 *   // Configure PWM: Pin 13, 1kHz, 50% duty, 8-bit resolution
 *   if (pwm->configure(13, 1000, 50, 8)) {
 *       // PWM running
 *   }
 *
 *   // Change duty cycle only (keep frequency)
 *   pwm->set_duty(13, 75);  // 75% duty cycle
 *
 *   // Stop PWM
 *   pwm->stop(13);
 */
class PWMInterface {
public:
    virtual ~PWMInterface() {}

    /**
     * Configure PWM on pin with full parameters
     *
     * @param pin Pin number to configure
     * @param frequency_hz PWM frequency in Hz (1 - 100000 typical)
     * @param duty_percent Duty cycle percentage (0-100)
     * @param resolution_bits Resolution in bits (8, 10, 12, 16 typical)
     * @return true if configuration successful
     */
    virtual bool configure(uint8_t pin, uint32_t frequency_hz, uint8_t duty_percent, uint8_t resolution_bits = 8) = 0;

    /**
     * Set duty cycle only (preserve frequency and resolution)
     *
     * @param pin Pin number
     * @param duty_percent New duty cycle percentage (0-100)
     * @return true if successful
     */
    virtual bool set_duty(uint8_t pin, uint8_t duty_percent) = 0;

    /**
     * Stop PWM on pin
     *
     * @param pin Pin number
     * @return true if successful
     */
    virtual bool stop(uint8_t pin) = 0;

    /**
     * Validate if pin supports PWM
     * Platform-specific validation
     *
     * @param pin Pin number to validate
     * @return true if pin supports PWM
     */
    virtual bool is_valid_pwm_pin(uint8_t pin) const = 0;

    /**
     * Get current PWM configuration for pin
     *
     * @param pin Pin number
     * @param freq Output: frequency in Hz
     * @param duty Output: duty cycle percentage (0-100)
     * @return true if pin has active PWM configuration
     */
    virtual bool get_config(uint8_t pin, uint32_t& freq, uint8_t& duty) const = 0;

    /**
     * Get last error message
     *
     * @return Pointer to error string (empty if no error)
     */
    virtual const char* get_last_error() const = 0;

    /**
     * Check if pin is currently configured for PWM
     *
     * @param pin Pin number
     * @return true if pin has active PWM
     */
    virtual bool is_active(uint8_t pin) const = 0;

    /**
     * Stop all PWM outputs
     * Useful for emergency stop or reset
     */
    virtual void stop_all() = 0;
};

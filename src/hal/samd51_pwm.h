#pragma once

#include "pwm_interface.h"

/**
 * SAMD51_PWM
 *
 * SAMD51-specific PWM implementation using TCC (Timer Counter for Control).
 * Provides frequency control, not just duty cycle.
 *
 * Features:
 * - Full frequency control (1 Hz - 48 MHz theoretical, 100 kHz practical)
 * - Resolution control (8, 10, 12, 16 bit)
 * - Pin validation using samd51_pin_caps
 * - TCC channel management
 *
 * Limitations:
 * - Pins on same TCC channel share frequency
 * - High frequencies reduce resolution
 * - Maximum 3 TCC instances (TCC0, TCC1, TCC2)
 *
 * TCC Channel Sharing:
 * - TCC0: 8 channels (many pins)
 * - TCC1: 8 channels (many pins)
 * - TCC2: 2 channels (fewer pins)
 */
class SAMD51_PWM : public PWMInterface {
public:
    SAMD51_PWM();
    ~SAMD51_PWM() override;

    bool configure(uint8_t pin, uint32_t frequency_hz, uint8_t duty_percent, uint8_t resolution_bits = 8) override;
    bool set_duty(uint8_t pin, uint8_t duty_percent) override;
    bool stop(uint8_t pin) override;
    bool is_valid_pwm_pin(uint8_t pin) const override;
    bool get_config(uint8_t pin, uint32_t& freq, uint8_t& duty) const override;
    const char* get_last_error() const override;
    bool is_active(uint8_t pin) const override;
    void stop_all() override;

private:
    /**
     * PWM Configuration for a pin
     */
    struct PWMConfig {
        bool active;
        uint32_t frequency_hz;
        uint8_t duty_percent;
        uint8_t resolution_bits;
        uint8_t tcc_instance;
        uint8_t tcc_channel;
    };

    static constexpr uint8_t MAX_PINS = 32;
    PWMConfig configs_[MAX_PINS];
    mutable char last_error_[64];  // Mutable for error reporting from const methods

    /**
     * Set error message
     */
    void set_error(const char* error) const;

    /**
     * Configure TCC for PWM
     *
     * @param pin Pin number
     * @param freq Frequency in Hz
     * @param resolution Resolution in bits
     * @return true if TCC configured successfully
     */
    bool configure_tcc(uint8_t pin, uint32_t freq, uint8_t resolution);

    /**
     * Validate resolution
     *
     * @param resolution Resolution in bits
     * @return true if valid (8, 10, 12, 16)
     */
    bool is_valid_resolution(uint8_t resolution) const;

    /**
     * Calculate TCC period for frequency and resolution
     *
     * @param freq Frequency in Hz
     * @param resolution Resolution in bits
     * @param period Output: TCC period value
     * @return true if calculation successful
     */
    bool calculate_period(uint32_t freq, uint8_t resolution, uint32_t& period) const;

    /**
     * Check if frequency change would affect other pins on same TCC
     *
     * @param tcc_instance TCC instance (0-2)
     * @param new_freq New frequency
     * @return true if safe (no conflicts)
     */
    bool check_frequency_conflict(uint8_t tcc_instance, uint32_t new_freq) const;
};

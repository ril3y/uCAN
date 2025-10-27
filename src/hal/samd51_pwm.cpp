#include "samd51_pwm.h"
#include "../capabilities/samd51/samd51_pin_caps.h"
#include "../utils/pin_error_logger.h"
#include <Arduino.h>
#include <string.h>

// SAMD51 clock frequency (120 MHz)
static constexpr uint32_t SAMD51_CLOCK_HZ = 120000000;

SAMD51_PWM::SAMD51_PWM() {
    memset(last_error_, 0, sizeof(last_error_));
    for (uint8_t i = 0; i < MAX_PINS; i++) {
        configs_[i].active = false;
    }
}

SAMD51_PWM::~SAMD51_PWM() {
    stop_all();
}

bool SAMD51_PWM::configure(uint8_t pin, uint32_t frequency_hz, uint8_t duty_percent, uint8_t resolution_bits) {
    // Validate pin
    if (!is_valid_pwm_pin(pin)) {
        set_error("Pin does not support PWM");
        LOG_PIN_ERROR(pin, "Pin does not support PWM");
        return false;
    }

    // Validate duty cycle
    if (duty_percent > 100) {
        set_error("Duty cycle must be 0-100%");
        return false;
    }

    // Validate resolution
    if (!is_valid_resolution(resolution_bits)) {
        set_error("Resolution must be 8, 10, 12, or 16 bits");
        return false;
    }

    // Get TCC info for pin
    uint8_t tcc_instance, tcc_channel;
    if (!samd51_get_pwm_tcc(pin, tcc_instance, tcc_channel)) {
        set_error("Failed to get TCC info for pin");
        return false;
    }

    // Check for frequency conflicts on same TCC
    if (!check_frequency_conflict(tcc_instance, frequency_hz)) {
        Serial.print("[PIN_WARNING] Pin ");
        Serial.print(pin);
        Serial.print(": Changing frequency on TCC");
        Serial.print(tcc_instance);
        Serial.println(" affects other pins on same TCC");
    }

    // Configure TCC
    if (!configure_tcc(pin, frequency_hz, resolution_bits)) {
        return false;
    }

    // Calculate duty cycle value
    uint32_t max_value = (1 << resolution_bits) - 1;
    uint32_t duty_value = (max_value * duty_percent) / 100;

    // Use Arduino analogWrite (simplified for now)
    // Future: Direct TCC register access for better control
    pinMode(pin, OUTPUT);
    analogWrite(pin, map(duty_value, 0, max_value, 0, 255));

    // Store configuration
    configs_[pin].active = true;
    configs_[pin].frequency_hz = frequency_hz;
    configs_[pin].duty_percent = duty_percent;
    configs_[pin].resolution_bits = resolution_bits;
    configs_[pin].tcc_instance = tcc_instance;
    configs_[pin].tcc_channel = tcc_channel;

    LOG_PIN_INFO(pin, "PWM configured");

    return true;
}

bool SAMD51_PWM::set_duty(uint8_t pin, uint8_t duty_percent) {
    if (pin >= MAX_PINS || !configs_[pin].active) {
        set_error("Pin not configured for PWM");
        return false;
    }

    if (duty_percent > 100) {
        set_error("Duty cycle must be 0-100%");
        return false;
    }

    // Update duty cycle using existing configuration
    uint32_t max_value = (1 << configs_[pin].resolution_bits) - 1;
    uint32_t duty_value = (max_value * duty_percent) / 100;

    analogWrite(pin, map(duty_value, 0, max_value, 0, 255));

    configs_[pin].duty_percent = duty_percent;

    return true;
}

bool SAMD51_PWM::stop(uint8_t pin) {
    if (pin >= MAX_PINS) {
        return false;
    }

    if (configs_[pin].active) {
        digitalWrite(pin, LOW);
        pinMode(pin, INPUT);
        configs_[pin].active = false;
        LOG_PIN_INFO(pin, "PWM stopped");
    }

    return true;
}

bool SAMD51_PWM::is_valid_pwm_pin(uint8_t pin) const {
    const PinCapabilities* caps = samd51_get_pin_capabilities(pin);
    return caps && caps->can_pwm;
}

bool SAMD51_PWM::get_config(uint8_t pin, uint32_t& freq, uint8_t& duty) const {
    if (pin >= MAX_PINS || !configs_[pin].active) {
        return false;
    }

    freq = configs_[pin].frequency_hz;
    duty = configs_[pin].duty_percent;
    return true;
}

const char* SAMD51_PWM::get_last_error() const {
    return last_error_;
}

bool SAMD51_PWM::is_active(uint8_t pin) const {
    return (pin < MAX_PINS) && configs_[pin].active;
}

void SAMD51_PWM::stop_all() {
    for (uint8_t pin = 0; pin < MAX_PINS; pin++) {
        if (configs_[pin].active) {
            stop(pin);
        }
    }
}

void SAMD51_PWM::set_error(const char* error) const {
    strncpy(last_error_, error, sizeof(last_error_) - 1);
    last_error_[sizeof(last_error_) - 1] = '\0';
}

bool SAMD51_PWM::configure_tcc(uint8_t pin, uint32_t freq, uint8_t resolution) {
    // Calculate required TCC period
    uint32_t period;
    if (!calculate_period(freq, resolution, period)) {
        return false;
    }

    // Note: Arduino analogWrite doesn't support frequency control directly
    // This is a simplified implementation using default Arduino PWM
    // Future enhancement: Direct TCC register manipulation for precise frequency control

    return true;
}

bool SAMD51_PWM::is_valid_resolution(uint8_t resolution) const {
    return (resolution == 8 || resolution == 10 || resolution == 12 || resolution == 16);
}

bool SAMD51_PWM::calculate_period(uint32_t freq, uint8_t resolution, uint32_t& period) const {
    if (freq == 0) {
        set_error("Frequency cannot be zero");
        return false;
    }

    // Calculate number of steps for resolution
    uint32_t steps = 1 << resolution;

    // Calculate required period: Clock / (frequency * steps)
    uint32_t required_period = SAMD51_CLOCK_HZ / (freq * steps);

    // Check if period is achievable
    if (required_period == 0) {
        set_error("Frequency too high for resolution");
        return false;
    }

    if (required_period > 0xFFFF) {
        set_error("Frequency too low (period overflow)");
        return false;
    }

    period = required_period;
    return true;
}

bool SAMD51_PWM::check_frequency_conflict(uint8_t tcc_instance, uint32_t new_freq) const {
    // Check if any other pin on same TCC has different frequency
    for (uint8_t pin = 0; pin < MAX_PINS; pin++) {
        if (configs_[pin].active &&
            configs_[pin].tcc_instance == tcc_instance &&
            configs_[pin].frequency_hz != new_freq) {
            return false;  // Conflict detected
        }
    }
    return true;  // No conflict
}

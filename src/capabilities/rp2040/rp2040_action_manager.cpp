#include "rp2040_action_manager.h"

#ifdef PLATFORM_RP2040

#include <Arduino.h>
#include "../../capabilities/board_capabilities.h"

// ============================================================================
// Custom Command Implementations
// ============================================================================

/**
 * PWM Frequency Custom Command
 * Format: pwm_freq:PIN:FREQUENCY
 * Example: pwm_freq:15:1000 (set GP15 to 1kHz PWM)
 *
 * RP2040 PWM is more flexible than SAMD51 - can set frequency per slice
 */
class PWMFreqCommand : public CustomCommand {
public:
    const char* get_name() const override { return "pwm_freq"; }
    const char* get_description() const override {
        return "Set PWM frequency for a pin (125MHz/divisor)";
    }
    const char* get_category() const override { return "PWM"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        static const ParamDef params[] = {
            {"pin", "GPIO pin number (0-29)", PARAM_UINT8, 0, 29, nullptr, true},
            {"frequency", "Frequency in Hz (1-125000000)", PARAM_UINT32, 1, 125000000, nullptr, true}
        };
        count = 2;
        return params;
    }

    bool execute(const char* params) override {
        if (!params) return false;

        // Parse PIN:FREQUENCY
        char buffer[32];
        strncpy(buffer, params, sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\0';

        char* colon = strchr(buffer, ':');
        if (!colon) return false;

        *colon = '\0';
        uint8_t pin = atoi(buffer);
        uint32_t frequency = atoi(colon + 1);

        if (pin >= platform_capabilities.gpio_count || frequency == 0) {
            return false;
        }

        // RP2040 PWM frequency calculation
        // PWM frequency = 125MHz / (divisor * wrap)
        // For simplicity, use wrap=65535 and calculate divisor
        uint32_t clock_freq = 125000000;  // 125 MHz
        uint16_t wrap = 65535;
        float divisor = (float)clock_freq / (frequency * wrap);

        if (divisor < 1.0f || divisor > 255.0f) {
            return false;  // Out of range
        }

        // Configure PWM
        pinMode(pin, OUTPUT);
        analogWriteFreq(frequency);
        analogWriteResolution(16);  // 16-bit for RP2040

        return true;
    }
};

/**
 * Internal Temperature Sensor Command
 * Format: adc_temp
 * Returns temperature in 0.01°C units via CAN
 */
class ADCTempCommand : public CustomCommand {
public:
    ADCTempCommand(RP2040ActionManager* manager) : manager_(manager) {}

    const char* get_name() const override { return "adc_temp"; }
    const char* get_description() const override {
        return "Read internal temperature sensor and send via CAN";
    }
    const char* get_category() const override { return "Analog"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        static const ParamDef params[] = {
            {"can_id", "CAN ID for temperature response", PARAM_HEX, 0, 0x7FF, nullptr, true}
        };
        count = 1;
        return params;
    }

    bool execute(const char* params) override {
        if (!params || !manager_) return false;

        uint32_t can_id = strtoul(params, nullptr, 16);
        if (can_id == 0 || can_id > 0x7FF) {
            return false;
        }

        // Read internal temperature sensor (ADC4)
        analogReadTemp();  // Initialize temperature sensor
        float temp_c = analogReadTemp();

        // Convert to 0.01°C units (int16)
        int16_t temp_hundredths = (int16_t)(temp_c * 100.0f);

        // Send as CAN message (2 bytes, signed, big-endian)
        uint8_t data[2];
        data[0] = (temp_hundredths >> 8) & 0xFF;
        data[1] = temp_hundredths & 0xFF;

        return manager_->execute_can_send_action(can_id, data, 2);
    }

private:
    RP2040ActionManager* manager_;
};

/**
 * GPIO Pulse Command
 * Format: gpio_pulse:PIN:DURATION_MS
 * Pulse a GPIO pin HIGH for specified duration, then LOW
 */
class GPIOPulseCommand : public CustomCommand {
public:
    const char* get_name() const override { return "gpio_pulse"; }
    const char* get_description() const override {
        return "Pulse GPIO pin HIGH for specified duration";
    }
    const char* get_category() const override { return "GPIO"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        static const ParamDef params[] = {
            {"pin", "GPIO pin number (0-29)", PARAM_UINT8, 0, 29, nullptr, true},
            {"duration_ms", "Pulse duration in milliseconds", PARAM_UINT16, 1, 10000, nullptr, true}
        };
        count = 2;
        return params;
    }

    bool execute(const char* params) override {
        if (!params) return false;

        // Parse PIN:DURATION_MS
        char buffer[32];
        strncpy(buffer, params, sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\0';

        char* colon = strchr(buffer, ':');
        if (!colon) return false;

        *colon = '\0';
        uint8_t pin = atoi(buffer);
        uint16_t duration = atoi(colon + 1);

        if (pin >= platform_capabilities.gpio_count || duration == 0) {
            return false;
        }

        // Execute pulse
        pinMode(pin, OUTPUT);
        digitalWrite(pin, HIGH);
        delay(duration);
        digitalWrite(pin, LOW);

        return true;
    }
};

// ============================================================================
// RP2040ActionManager Implementation
// ============================================================================

RP2040ActionManager::RP2040ActionManager()
    : ActionManagerBase()
{
}

RP2040ActionManager::~RP2040ActionManager() {
    // Nothing to clean up
}

bool RP2040ActionManager::execute_gpio_action(ActionType type, uint8_t pin) {
    // Validate pin number
    if (pin >= platform_capabilities.gpio_count) {
        return false;
    }

    switch (type) {
        case ACTION_GPIO_SET:
            pinMode(pin, OUTPUT);
            digitalWrite(pin, HIGH);
            return true;

        case ACTION_GPIO_CLEAR:
            pinMode(pin, OUTPUT);
            digitalWrite(pin, LOW);
            return true;

        case ACTION_GPIO_TOGGLE:
            pinMode(pin, OUTPUT);
            digitalWrite(pin, !digitalRead(pin));
            return true;

        default:
            return false;
    }
}

bool RP2040ActionManager::execute_pwm_action(uint8_t pin, uint8_t duty) {
    if (!platform_capabilities.has_capability(CAP_GPIO_PWM)) {
        return false;
    }

    if (pin >= platform_capabilities.gpio_count) {
        return false;
    }

    // RP2040 supports 16-bit PWM, but we'll use 8-bit for compatibility
    pinMode(pin, OUTPUT);
    analogWrite(pin, duty);
    return true;
}

bool RP2040ActionManager::execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
    // RP2040 Pico board doesn't have built-in NeoPixel
    // External NeoPixels should be handled via custom actions or external library
    return false;
}

bool RP2040ActionManager::execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id) {
    if (!platform_capabilities.has_capability(CAP_GPIO_ANALOG)) {
        return false;
    }

    // RP2040 has 12-bit ADC (but reads as 10-bit by default)
    analogReadResolution(12);
    int adc_value = analogRead(adc_pin);

    // Send as CAN message (2 bytes, big-endian, 12-bit value)
    uint8_t data[2];
    data[0] = (adc_value >> 8) & 0xFF;
    data[1] = adc_value & 0xFF;

    return execute_can_send_action(response_id, data, 2);
}

bool RP2040ActionManager::save_rules_impl() {
    // Use RP2040 flash storage to persist rules
    // This also saves the device name in the flash header
    return save_rules_to_flash(rules_, get_rule_count());
}

uint8_t RP2040ActionManager::load_rules_impl() {
    // Load rules from RP2040 flash storage
    // This also loads the device name from the flash header
    return load_rules_from_flash(rules_, MAX_ACTION_RULES);
}

void RP2040ActionManager::register_custom_commands() {
    // Register PWM frequency command
    static PWMFreqCommand pwm_freq_cmd;
    custom_commands_.register_command(&pwm_freq_cmd);

    // Register temperature sensor command
    static ADCTempCommand adc_temp_cmd(this);
    custom_commands_.register_command(&adc_temp_cmd);

    // Register GPIO pulse command
    static GPIOPulseCommand gpio_pulse_cmd;
    custom_commands_.register_command(&gpio_pulse_cmd);
}

#endif // PLATFORM_RP2040

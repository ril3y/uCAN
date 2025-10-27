#include "samd51_action_manager.h"

#ifdef PLATFORM_SAMD51

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "../../capabilities/board_capabilities.h"

// ============================================================================
// Custom Command Implementations
// ============================================================================

/**
 * NeoPixel Custom Command
 * Format: neopixel:R:G:B[:BRIGHTNESS]
 * Example: neopixel:255:0:0:128 (red at 50% brightness)
 */
class NeoPixelCommand : public CustomCommand {
public:
    NeoPixelCommand(Adafruit_NeoPixel* pixel) : pixel_(pixel) {}

    const char* get_name() const override { return "neopixel"; }
    const char* get_description() const override {
        return "Set built-in NeoPixel color and brightness";
    }
    const char* get_category() const override { return "Visual"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        static const ParamDef params[] = {
            {"red", "Red component (0-255)", PARAM_UINT8, 0, 255, nullptr, true},
            {"green", "Green component (0-255)", PARAM_UINT8, 0, 255, nullptr, true},
            {"blue", "Blue component (0-255)", PARAM_UINT8, 0, 255, nullptr, true},
            {"brightness", "Brightness level (0-255)", PARAM_UINT8, 0, 255, nullptr, false}
        };
        count = 4;
        return params;
    }

    bool execute(const char* params) override {
        if (!pixel_ || !params) return false;

        // Parse R:G:B[:BRIGHTNESS]
        char buffer[64];
        strncpy(buffer, params, sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\0';

        char* tokens[4];
        uint8_t token_count = 0;
        char* ptr = buffer;

        while (token_count < 4 && ptr && *ptr != '\0') {
            tokens[token_count++] = ptr;
            ptr = strchr(ptr, ':');
            if (ptr) {
                *ptr = '\0';
                ptr++;
            }
        }

        if (token_count < 3) return false;

        uint8_t r = atoi(tokens[0]);
        uint8_t g = atoi(tokens[1]);
        uint8_t b = atoi(tokens[2]);
        uint8_t brightness = (token_count >= 4) ? atoi(tokens[3]) : 255;

        if (brightness > 0 && brightness < 255) {
            pixel_->setBrightness(brightness);
        }
        pixel_->setPixelColor(0, pixel_->Color(r, g, b));
        pixel_->show();

        return true;
    }

private:
    Adafruit_NeoPixel* pixel_;
};

/**
 * DAC Custom Command
 * Format: dac:CHANNEL:VALUE
 * Example: dac:0:2048 (set DAC0 to 1.65V, mid-scale)
 */
class DACCommand : public CustomCommand {
public:
    const char* get_name() const override { return "dac"; }
    const char* get_description() const override {
        return "Set DAC output voltage (12-bit: 0-4095 = 0-3.3V)";
    }
    const char* get_category() const override { return "Analog"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        static const ParamDef params[] = {
            {"channel", "DAC channel (0=A0, 1=A1)", PARAM_ENUM, 0, 1, "0,1", true},
            {"value", "12-bit DAC value (0-4095)", PARAM_UINT16, 0, 4095, nullptr, true}
        };
        count = 2;
        return params;
    }

    bool execute(const char* params) override {
        if (!params) return false;

        // Parse CHANNEL:VALUE
        char buffer[32];
        strncpy(buffer, params, sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\0';

        char* colon = strchr(buffer, ':');
        if (!colon) return false;

        *colon = '\0';
        uint8_t channel = atoi(buffer);
        uint16_t value = atoi(colon + 1);

        if (channel > 1 || value > 4095) return false;

        // SAMD51 has 2 DAC channels: A0 (PA02) and A1 (PA05)
        uint8_t dac_pin = (channel == 0) ? A0 : A1;

        // Use analogWriteResolution for 12-bit DAC
        analogWriteResolution(12);
        analogWrite(dac_pin, value);

        return true;
    }
};

// ============================================================================
// SAMD51ActionManager Implementation
// ============================================================================

SAMD51ActionManager::SAMD51ActionManager()
    : ActionManagerBase()
    , neopixel_(nullptr)
{
}

SAMD51ActionManager::~SAMD51ActionManager() {
    if (neopixel_) {
        delete neopixel_;
        neopixel_ = nullptr;
    }
}

bool SAMD51ActionManager::initialize(CANInterface* can_if) {
    // Initialize NeoPixel if available
    if (platform_capabilities.neopixel_available) {
        neopixel_ = new Adafruit_NeoPixel(1, platform_capabilities.neopixel_pin, NEO_GRB + NEO_KHZ800);
        if (neopixel_) {
            neopixel_->begin();
            neopixel_->setBrightness(50);  // Default 20% brightness
            neopixel_->setPixelColor(0, neopixel_->Color(0, 0, 0));
            neopixel_->show();
        }
    }

    // Call base class initialization
    return ActionManagerBase::initialize(can_if);
}

bool SAMD51ActionManager::execute_gpio_action(ActionType type, uint8_t pin) {
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

bool SAMD51ActionManager::execute_pwm_action(uint8_t pin, uint8_t duty) {
    if (!platform_capabilities.has_capability(CAP_GPIO_PWM)) {
        return false;
    }

    if (pin >= platform_capabilities.gpio_count) {
        return false;
    }

    // SAMD51 supports 12-bit PWM, but we'll use 8-bit for compatibility
    pinMode(pin, OUTPUT);
    analogWrite(pin, duty);
    return true;
}

bool SAMD51ActionManager::execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
    if (!platform_capabilities.has_capability(CAP_NEOPIXEL) || !neopixel_) {
        return false;
    }

    if (brightness > 0) {
        neopixel_->setBrightness(brightness);
    }
    neopixel_->setPixelColor(0, neopixel_->Color(r, g, b));
    neopixel_->show();
    return true;
}

bool SAMD51ActionManager::execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id) {
    if (!platform_capabilities.has_capability(CAP_GPIO_ANALOG)) {
        return false;
    }

    // SAMD51 has 12-bit ADC
    analogReadResolution(12);
    int adc_value = analogRead(adc_pin);

    // Send as CAN message (2 bytes, big-endian, 12-bit value)
    uint8_t data[2];
    data[0] = (adc_value >> 8) & 0xFF;
    data[1] = adc_value & 0xFF;

    return execute_can_send_action(response_id, data, 2);
}

bool SAMD51ActionManager::save_rules_impl() {
    // Count active rules
    uint8_t active_count = 0;
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id != 0) {
            active_count++;
        }
    }

    // Save to Flash using SAMD51-specific storage
    return save_rules_to_flash(rules_, active_count);
}

uint8_t SAMD51ActionManager::load_rules_impl() {
    // Load rules from Flash
    return load_rules_from_flash(rules_, MAX_ACTION_RULES);
}

void SAMD51ActionManager::register_custom_commands() {
    // Register NeoPixel command if available
    if (neopixel_) {
        static NeoPixelCommand neopixel_cmd(neopixel_);
        custom_commands_.register_command(&neopixel_cmd);
    }

    // Register DAC command if available
    if (platform_capabilities.has_capability(CAP_GPIO_DAC)) {
        static DACCommand dac_cmd;
        custom_commands_.register_command(&dac_cmd);
    }
}

#endif // PLATFORM_SAMD51

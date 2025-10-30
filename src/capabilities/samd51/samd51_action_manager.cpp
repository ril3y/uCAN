#include "samd51_action_manager.h"

#ifdef PLATFORM_SAMD51

#include <Arduino.h>
#include "../../capabilities/board_capabilities.h"
#include "../../boards/board_interface.h"
#include "../../boards/board_registry.h"

// Include board implementation for NeoPixel delegation (if Feather M4 CAN)
#ifdef ARDUINO_ADAFRUIT_FEATHER_M4_CAN
#include "../../boards/feather_m4_can/board_impl.h"
#endif

// ============================================================================
// Custom Command Implementations
// ============================================================================

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
    , board_impl_(nullptr)
{
}

SAMD51ActionManager::~SAMD51ActionManager() {
    if (board_impl_) {
        delete board_impl_;
        board_impl_ = nullptr;
    }
}

bool SAMD51ActionManager::initialize(CANInterface* can_if) {
    // Call base class initialization
    if (!ActionManagerBase::initialize(can_if)) {
        return false;
    }

    // Create board-specific implementation (if available)
    board_impl_ = BoardFactory::create();
    if (board_impl_) {
        if (!board_impl_->initialize(this)) {
            Serial.println("WARNING;Board-specific initialization failed");
            delete board_impl_;
            board_impl_ = nullptr;
        } else {
            // Register board-specific custom commands
            board_impl_->register_custom_commands(custom_commands_);
        }
    }

    return true;
}

void SAMD51ActionManager::update_board_periodic() {
    // Update board-specific periodic tasks
    if (board_impl_) {
        board_impl_->update_periodic();
    }
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
    // Delegate to board implementation if available
#ifdef ARDUINO_ADAFRUIT_FEATHER_M4_CAN
    if (board_impl_) {
        FeatherM4CANBoard* feather_board = static_cast<FeatherM4CANBoard*>(board_impl_);
        return feather_board->set_neopixel(r, g, b, brightness);
    }
#endif

    // No NeoPixel support without board implementation
    return false;
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
    // Register DAC command if available
    if (platform_capabilities.has_capability(CAP_GPIO_DAC)) {
        static DACCommand dac_cmd;
        custom_commands_.register_command(&dac_cmd);
    }

    // Board-specific commands are registered in initialize()
}

void SAMD51ActionManager::platform_reset() {
    NVIC_SystemReset();  // SAMD51 system reset
}

#endif // PLATFORM_SAMD51

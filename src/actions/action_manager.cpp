#include "action_manager.h"
#include <Arduino.h>
#include <string.h>

// NeoPixel support (SAMD51 only)
#ifdef PLATFORM_SAMD51
#include <Adafruit_NeoPixel.h>
extern Adafruit_NeoPixel* neopixel_instance;  // Defined in samd51_can.cpp if available
#endif

ActionManager::ActionManager()
    : can_interface_(nullptr)
    , initialized_(false)
    , next_rule_id_(1)
{
    // Clear all rules
    memset(rules_, 0, sizeof(rules_));
}

ActionManager::~ActionManager() {
    // Nothing to clean up
}

bool ActionManager::initialize(CANInterface* can_if) {
    if (!can_if) {
        return false;
    }

    can_interface_ = can_if;
    initialized_ = true;

    // Try to load rules from storage
    load_rules();

    return true;
}

uint8_t ActionManager::check_and_execute(const CANMessage& message) {
    if (!initialized_) {
        return 0;
    }

    uint8_t matches = 0;

    // Check each active rule
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id != 0 && rules_[i].enabled) {
            if (matches_rule(message, rules_[i])) {
                if (execute_action(rules_[i], message)) {
                    matches++;
                }
            }
        }
    }

    return matches;
}

uint8_t ActionManager::add_rule(const ActionRule& rule) {
    if (!initialized_) {
        return 0;
    }

    // Validate action is supported on this platform
    if (!is_action_supported(rule.action)) {
        return 0;
    }

    // Find empty slot
    int8_t slot = find_empty_slot();
    if (slot < 0) {
        return 0;  // No space
    }

    // Assign rule ID if not provided
    ActionRule new_rule = rule;
    if (new_rule.id == 0) {
        new_rule.id = next_rule_id_++;
        // Wrap around if needed (skip 0)
        if (next_rule_id_ == 0) {
            next_rule_id_ = 1;
        }
    }

    // Store rule
    rules_[slot] = new_rule;

    return new_rule.id;
}

bool ActionManager::remove_rule(uint8_t rule_id) {
    int8_t index = find_rule_index(rule_id);
    if (index < 0) {
        return false;
    }

    // Clear the rule (set ID to 0)
    memset(&rules_[index], 0, sizeof(ActionRule));
    return true;
}

bool ActionManager::set_rule_enabled(uint8_t rule_id, bool enabled) {
    int8_t index = find_rule_index(rule_id);
    if (index < 0) {
        return false;
    }

    rules_[index].enabled = enabled;
    return true;
}

const ActionRule* ActionManager::get_rule(uint8_t rule_id) const {
    int8_t index = find_rule_index(rule_id);
    if (index < 0) {
        return nullptr;
    }

    return &rules_[index];
}

uint8_t ActionManager::get_rule_count() const {
    uint8_t count = 0;
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id != 0) {
            count++;
        }
    }
    return count;
}

void ActionManager::clear_all_rules() {
    memset(rules_, 0, sizeof(rules_));
    next_rule_id_ = 1;
}

void ActionManager::list_rules(void (*callback)(const ActionRule& rule)) const {
    if (!callback) {
        return;
    }

    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id != 0) {
            callback(rules_[i]);
        }
    }
}

// ============================================================================
// Rule Matching
// ============================================================================

bool ActionManager::matches_rule(const CANMessage& message, const ActionRule& rule) const {
    // Check CAN ID match with mask
    if ((message.id & rule.can_id_mask) != (rule.can_id & rule.can_id_mask)) {
        return false;
    }

    // If data_length is 0, accept any data length
    if (rule.data_length > 0) {
        // Check if message has enough data
        if (message.length < rule.data_length) {
            return false;
        }

        // Check data bytes with mask
        for (uint8_t i = 0; i < rule.data_length; i++) {
            if ((message.data[i] & rule.data_mask[i]) != (rule.data[i] & rule.data_mask[i])) {
                return false;
            }
        }
    }

    return true;
}

// ============================================================================
// Action Execution
// ============================================================================

bool ActionManager::execute_action(const ActionRule& rule, const CANMessage& message) {
    switch (rule.action) {
        case ACTION_GPIO_SET:
        case ACTION_GPIO_CLEAR:
        case ACTION_GPIO_TOGGLE:
            return execute_gpio_action(rule.action, rule.params.gpio.pin);

        case ACTION_PWM_SET:
            return execute_pwm_action(rule.params.pwm.pin, rule.params.pwm.duty);

        case ACTION_NEOPIXEL_COLOR:
            return execute_neopixel_action(
                rule.params.neopixel.r,
                rule.params.neopixel.g,
                rule.params.neopixel.b,
                rule.params.neopixel.brightness
            );

        case ACTION_NEOPIXEL_OFF:
            return execute_neopixel_action(0, 0, 0, 0);

        case ACTION_CAN_SEND:
            return execute_can_send_action(
                rule.params.can_send.can_id,
                rule.params.can_send.data,
                rule.params.can_send.length
            );

        case ACTION_ADC_READ_SEND:
            return execute_adc_read_send_action(
                rule.params.adc.adc_pin,
                rule.params.adc.response_id
            );

        default:
            return false;  // Unsupported action
    }
}

bool ActionManager::execute_gpio_action(ActionType type, uint8_t pin) {
    // Validate pin number (basic check)
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

bool ActionManager::execute_pwm_action(uint8_t pin, uint8_t duty) {
    if (!platform_capabilities.has_capability(CAP_GPIO_PWM)) {
        return false;
    }

    if (pin >= platform_capabilities.gpio_count) {
        return false;
    }

    pinMode(pin, OUTPUT);
    analogWrite(pin, duty);
    return true;
}

bool ActionManager::execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
#ifdef PLATFORM_SAMD51
    if (!platform_capabilities.has_capability(CAP_NEOPIXEL)) {
        return false;
    }

    // Use NeoPixel from samd51_can if available
    // For now, just set the built-in NeoPixel directly
    if (platform_capabilities.neopixel_available) {
        Adafruit_NeoPixel pixel(1, platform_capabilities.neopixel_pin, NEO_GRB + NEO_KHZ800);
        pixel.begin();
        if (brightness > 0) {
            pixel.setBrightness(brightness);
        }
        pixel.setPixelColor(0, pixel.Color(r, g, b));
        pixel.show();
        return true;
    }
#endif
    return false;
}

bool ActionManager::execute_can_send_action(uint32_t can_id, const uint8_t* data, uint8_t length) {
    if (!can_interface_ || !can_interface_->is_ready()) {
        return false;
    }

    CANMessage msg;
    msg.id = can_id;
    msg.extended = (can_id > 0x7FF);
    msg.remote = false;
    msg.length = (length > 8) ? 8 : length;
    msg.timestamp = millis();
    memcpy(msg.data, data, msg.length);

    return can_interface_->send_message(msg);
}

bool ActionManager::execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id) {
    if (!platform_capabilities.has_capability(CAP_GPIO_ANALOG)) {
        return false;
    }

    // Read ADC value
    int adc_value = analogRead(adc_pin);

    // Send as CAN message (2 bytes, big-endian)
    uint8_t data[2];
    data[0] = (adc_value >> 8) & 0xFF;
    data[1] = adc_value & 0xFF;

    return execute_can_send_action(response_id, data, 2);
}

// ============================================================================
// Helper Methods
// ============================================================================

int8_t ActionManager::find_empty_slot() const {
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id == 0) {
            return i;
        }
    }
    return -1;  // No empty slots
}

int8_t ActionManager::find_rule_index(uint8_t rule_id) const {
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id == rule_id) {
            return i;
        }
    }
    return -1;  // Not found
}

// ============================================================================
// Persistence (Stub - to be implemented)
// ============================================================================

bool ActionManager::save_rules() {
    // TODO: Implement EEPROM/Flash storage
    // For RP2040: Use Pico SDK flash API
    // For SAMD51: Use FlashStorage library
    return false;
}

uint8_t ActionManager::load_rules() {
    // TODO: Implement EEPROM/Flash loading
    return 0;
}

// ============================================================================
// Helper Functions
// ============================================================================

const char* action_type_to_string(ActionType type) {
    switch (type) {
        case ACTION_NONE: return "NONE";
        case ACTION_GPIO_SET: return "GPIO_SET";
        case ACTION_GPIO_CLEAR: return "GPIO_CLEAR";
        case ACTION_GPIO_TOGGLE: return "GPIO_TOGGLE";
        case ACTION_CAN_SEND: return "CAN_SEND";
        case ACTION_PWM_SET: return "PWM_SET";
        case ACTION_NEOPIXEL_COLOR: return "NEOPIXEL_COLOR";
        case ACTION_NEOPIXEL_OFF: return "NEOPIXEL_OFF";
        case ACTION_ADC_READ: return "ADC_READ";
        case ACTION_ADC_READ_SEND: return "ADC_READ_SEND";
        default: return "UNKNOWN";
    }
}

bool is_action_supported(ActionType type) {
    switch (type) {
        case ACTION_GPIO_SET:
        case ACTION_GPIO_CLEAR:
        case ACTION_GPIO_TOGGLE:
            return platform_capabilities.has_capability(CAP_GPIO_DIGITAL);

        case ACTION_CAN_SEND:
            return platform_capabilities.has_capability(CAP_CAN_SEND);

        case ACTION_PWM_SET:
            return platform_capabilities.has_capability(CAP_GPIO_PWM);

        case ACTION_NEOPIXEL_COLOR:
        case ACTION_NEOPIXEL_OFF:
            return platform_capabilities.has_capability(CAP_NEOPIXEL);

        case ACTION_ADC_READ:
        case ACTION_ADC_READ_SEND:
            return platform_capabilities.has_capability(CAP_GPIO_ANALOG);

        default:
            return false;
    }
}

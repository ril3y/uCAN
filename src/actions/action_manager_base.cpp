#include "action_manager_base.h"
#include <Arduino.h>
#include <string.h>
#include "../capabilities/board_capabilities.h"

ActionManagerBase::ActionManagerBase()
    : can_interface_(nullptr)
    , initialized_(false)
    , next_rule_id_(1)
{
    // Clear all rules
    memset(rules_, 0, sizeof(rules_));
}

ActionManagerBase::~ActionManagerBase() {
    // Nothing to clean up (derived classes handle their own resources)
}

bool ActionManagerBase::initialize(CANInterface* can_if) {
    if (!can_if) {
        return false;
    }

    can_interface_ = can_if;
    initialized_ = true;

    // Let platform register its custom commands
    register_custom_commands();

    // Try to load rules from storage
    load_rules();

    return true;
}

uint8_t ActionManagerBase::check_and_execute(const CANMessage& message) {
    if (!initialized_) {
        return 0;
    }

    uint8_t matches = 0;

    // Check each active rule
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id != 0 && rules_[i].enabled) {
            if (matches_rule(message, rules_[i])) {
                bool success = execute_action(rules_[i], message);

                // Report action execution
                Serial.print("ACTION;");
                Serial.print(rules_[i].id);
                Serial.print(";");
                Serial.print(action_type_to_string(rules_[i].action));
                Serial.print(";0x");
                Serial.print(message.id, HEX);
                Serial.print(";");
                Serial.println(success ? "OK" : "FAIL");

                if (success) {
                    matches++;
                }
            }
        }
    }

    return matches;
}

uint8_t ActionManagerBase::update_periodic() {
    if (!initialized_) {
        return 0;
    }

    uint8_t executed = 0;
    uint32_t current_ms = millis();

    // Check each rule for periodic actions
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        ActionRule& rule = rules_[i];

        // Skip empty or disabled rules
        if (rule.id == 0 || !rule.enabled) {
            continue;
        }

        // Only handle periodic send actions
        if (rule.action != ACTION_CAN_SEND_PERIODIC) {
            continue;
        }

        uint32_t interval = rule.params.can_send.interval_ms;

        // Skip if interval not set
        if (interval == 0) {
            continue;
        }

        // Check if enough time has passed
        if (current_ms - rule.last_execute_ms >= interval) {
            // Execute the CAN send
            if (execute_can_send_action(
                rule.params.can_send.can_id,
                rule.params.can_send.data,
                rule.params.can_send.length)) {

                rule.last_execute_ms = current_ms;
                rule.execute_count++;
                executed++;
            }
        }
    }

    return executed;
}

uint8_t ActionManagerBase::add_rule(const ActionRule& rule) {
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

    // Auto-save to persistent storage
    save_rules();

    return new_rule.id;
}

uint8_t ActionManagerBase::parse_and_add_rule(const char* command_str) {
    if (!initialized_ || !command_str) {
        return 0;
    }

    // Parse format: ID:CAN_ID:CAN_MASK:DATA:DATA_MASK:DATA_LEN:ACTION_TYPE:PARAM_SOURCE:PARAM1:PARAM2:...
    // PARAM_SOURCE is optional for backward compatibility
    char buffer[256];
    strncpy(buffer, command_str, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    char* tokens[16];
    uint8_t token_count = 0;
    char* ptr = buffer;

    // Tokenize by colon
    while (token_count < 16 && ptr && *ptr != '\0') {
        tokens[token_count++] = ptr;
        ptr = strchr(ptr, ':');
        if (ptr) {
            *ptr = '\0';
            ptr++;
        }
    }

    // Need at least: ID, CAN_ID, CAN_MASK, DATA, DATA_MASK, DATA_LEN, ACTION_TYPE
    if (token_count < 7) {
        return 0;
    }

    ActionRule rule;
    memset(&rule, 0, sizeof(rule));

    // Parse rule ID (0 = auto-assign)
    rule.id = atoi(tokens[0]);
    rule.enabled = true;

    // Parse CAN ID
    rule.can_id = strtoul(tokens[1], nullptr, 16);

    // Parse CAN ID mask (empty or "0x000" = match any)
    if (strlen(tokens[2]) > 0) {
        rule.can_id_mask = strtoul(tokens[2], nullptr, 16);
    } else {
        rule.can_id_mask = 0x000;  // Match any
    }

    // Parse data pattern (skip tokens[3])
    // Parse data mask (skip tokens[4])
    // Parse data length
    rule.data_length = atoi(tokens[5]);

    // Parse action type
    const char* action_type = tokens[6];

    // NEW: Parse parameter source (token 7, optional for backward compatibility)
    // v2.0: PARAM_SOURCE is REQUIRED (no backward compatibility)
    rule.param_data_offset = 0;

    // Token 7 MUST be "candata" or "fixed"
    if (token_count < 8) {
        // Missing PARAM_SOURCE field - error
        return 0;
    }

    if (strcmp(tokens[7], "candata") == 0 || strcmp(tokens[7], "can") == 0) {
        rule.param_source = PARAM_FROM_CAN_DATA;
    } else if (strcmp(tokens[7], "fixed") == 0 || strcmp(tokens[7], "rule") == 0) {
        rule.param_source = PARAM_FROM_RULE;
    } else {
        // Invalid PARAM_SOURCE value - error
        return 0;
    }

    uint8_t param_start_index = 8;  // Parameters always start at token 8 in v2.0

    // Parse action-specific parameters based on param_source
    if (strcmp(action_type, "GPIO_SET") == 0) {
        rule.action = ACTION_GPIO_SET;
        if (rule.param_source == PARAM_FROM_RULE && token_count > param_start_index) {
            rule.params.gpio.pin = atoi(tokens[param_start_index]);
        }

    } else if (strcmp(action_type, "GPIO_CLEAR") == 0) {
        rule.action = ACTION_GPIO_CLEAR;
        if (rule.param_source == PARAM_FROM_RULE && token_count > param_start_index) {
            rule.params.gpio.pin = atoi(tokens[param_start_index]);
        }

    } else if (strcmp(action_type, "GPIO_TOGGLE") == 0) {
        rule.action = ACTION_GPIO_TOGGLE;
        if (rule.param_source == PARAM_FROM_RULE && token_count > param_start_index) {
            rule.params.gpio.pin = atoi(tokens[param_start_index]);
        }

    } else if (strcmp(action_type, "PWM_SET") == 0) {
        rule.action = ACTION_PWM_SET;
        if (rule.param_source == PARAM_FROM_RULE && token_count > param_start_index + 1) {
            rule.params.pwm.pin = atoi(tokens[param_start_index]);
            rule.params.pwm.duty = atoi(tokens[param_start_index + 1]);
        }

    } else if (strcmp(action_type, "NEOPIXEL") == 0) {
        rule.action = ACTION_NEOPIXEL_COLOR;
        if (rule.param_source == PARAM_FROM_RULE && token_count > param_start_index + 3) {
            rule.params.neopixel.r = atoi(tokens[param_start_index]);
            rule.params.neopixel.g = atoi(tokens[param_start_index + 1]);
            rule.params.neopixel.b = atoi(tokens[param_start_index + 2]);
            rule.params.neopixel.brightness = atoi(tokens[param_start_index + 3]);
        }

    } else if (strcmp(action_type, "NEOPIXEL_OFF") == 0) {
        rule.action = ACTION_NEOPIXEL_OFF;

    } else if (strcmp(action_type, "CAN_SEND") == 0) {
        rule.action = ACTION_CAN_SEND;
        if (token_count > param_start_index + 1) {
            rule.params.can_send.can_id = strtoul(tokens[param_start_index], nullptr, 16);
            // Parse data bytes from tokens[param_start_index + 1] (comma-separated)
            const char* data_str = tokens[param_start_index + 1];
            rule.params.can_send.length = 0;
            // TODO: Parse comma-separated data bytes
        }

    } else if (strcmp(action_type, "CAN_SEND_PERIODIC") == 0) {
        rule.action = ACTION_CAN_SEND_PERIODIC;
        if (token_count > param_start_index + 2) {
            rule.params.can_send.can_id = strtoul(tokens[param_start_index], nullptr, 16);
            // Parse data bytes from tokens[param_start_index + 1] (comma-separated)
            const char* data_str = tokens[param_start_index + 1];
            rule.params.can_send.length = 0;
            // TODO: Parse comma-separated data bytes
            // Parse interval
            rule.params.can_send.interval_ms = atoi(tokens[param_start_index + 2]);
        }

    } else {
        // Unsupported action type
        return 0;
    }

    // Add the rule
    return add_rule(rule);
}

bool ActionManagerBase::remove_rule(uint8_t rule_id) {
    int8_t index = find_rule_index(rule_id);
    if (index < 0) {
        return false;
    }

    // Clear the rule (set ID to 0)
    memset(&rules_[index], 0, sizeof(ActionRule));

    // Auto-save to persistent storage
    save_rules();

    return true;
}

bool ActionManagerBase::set_rule_enabled(uint8_t rule_id, bool enabled) {
    int8_t index = find_rule_index(rule_id);
    if (index < 0) {
        return false;
    }

    rules_[index].enabled = enabled;

    // Auto-save to persistent storage
    save_rules();

    return true;
}

const ActionRule* ActionManagerBase::get_rule(uint8_t rule_id) const {
    int8_t index = find_rule_index(rule_id);
    if (index < 0) {
        return nullptr;
    }

    return &rules_[index];
}

uint8_t ActionManagerBase::get_rule_count() const {
    uint8_t count = 0;
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id != 0) {
            count++;
        }
    }
    return count;
}

void ActionManagerBase::clear_all_rules() {
    memset(rules_, 0, sizeof(rules_));
    next_rule_id_ = 1;
}

void ActionManagerBase::list_rules(void (*callback)(const ActionRule& rule)) const {
    if (!callback) {
        return;
    }

    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id != 0) {
            callback(rules_[i]);
        }
    }
}

void ActionManagerBase::print_rules() const {
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id == 0) {
            continue;  // Skip empty slots
        }

        const ActionRule& rule = rules_[i];

        // Format: RULE;{ID};{CAN_ID};{MASK};{DATA};{DATA_MASK};{DATA_LEN};{ACTION};{PARAM_SOURCE};{PARAMS...}
        // This format matches what parse_and_add_rule() expects, allowing copy/paste
        Serial.print("RULE;");
        Serial.print(rule.id);
        Serial.print(";0x");
        Serial.print(rule.can_id, HEX);
        Serial.print(";0x");
        Serial.print(rule.can_id_mask, HEX);
        Serial.print(";");

        // DATA field - hex bytes separated by commas (or empty if data_length == 0)
        if (rule.data_length > 0) {
            for (uint8_t j = 0; j < rule.data_length; j++) {
                if (j > 0) Serial.print(",");
                if (rule.data[j] < 0x10) Serial.print("0");
                Serial.print(rule.data[j], HEX);
            }
        }
        Serial.print(";");

        // DATA_MASK field - hex bytes separated by commas (or empty if data_length == 0)
        if (rule.data_length > 0) {
            for (uint8_t j = 0; j < rule.data_length; j++) {
                if (j > 0) Serial.print(",");
                if (rule.data_mask[j] < 0x10) Serial.print("0");
                Serial.print(rule.data_mask[j], HEX);
            }
        }
        Serial.print(";");

        // DATA_LEN field
        Serial.print(rule.data_length);
        Serial.print(";");

        // ACTION field
        Serial.print(action_type_to_string(rule.action));
        Serial.print(";");

        // PARAM_SOURCE field
        Serial.print(param_source_to_string(rule.param_source));

        // PARAMS fields (only if param_source == PARAM_FROM_RULE)
        if (rule.param_source == PARAM_FROM_RULE) {
            switch (rule.action) {
                case ACTION_GPIO_SET:
                case ACTION_GPIO_CLEAR:
                case ACTION_GPIO_TOGGLE:
                    Serial.print(";");
                    Serial.print(rule.params.gpio.pin);
                    break;

                case ACTION_PWM_SET:
                    Serial.print(";");
                    Serial.print(rule.params.pwm.pin);
                    Serial.print(";");
                    Serial.print(rule.params.pwm.duty);
                    break;

                case ACTION_NEOPIXEL_COLOR:
                    Serial.print(";");
                    Serial.print(rule.params.neopixel.r);
                    Serial.print(";");
                    Serial.print(rule.params.neopixel.g);
                    Serial.print(";");
                    Serial.print(rule.params.neopixel.b);
                    Serial.print(";");
                    Serial.print(rule.params.neopixel.brightness);
                    break;

                case ACTION_CAN_SEND:
                case ACTION_CAN_SEND_PERIODIC:
                    Serial.print(";0x");
                    Serial.print(rule.params.can_send.can_id, HEX);
                    Serial.print(";");
                    // CAN data bytes (comma-separated hex)
                    for (uint8_t j = 0; j < rule.params.can_send.length; j++) {
                        if (j > 0) Serial.print(",");
                        if (rule.params.can_send.data[j] < 0x10) Serial.print("0");
                        Serial.print(rule.params.can_send.data[j], HEX);
                    }
                    if (rule.action == ACTION_CAN_SEND_PERIODIC) {
                        Serial.print(";");
                        Serial.print(rule.params.can_send.interval_ms);
                    }
                    break;

                case ACTION_NEOPIXEL_OFF:
                case ACTION_BUFFER_CLEAR:
                    // No parameters
                    break;

                // Phase 1 actions - not yet supported in print due to union storage
                // These need fixed parameters from rule definition
                case ACTION_PWM_CONFIGURE:
                case ACTION_I2C_WRITE:
                case ACTION_I2C_READ_BUFFER:
                case ACTION_GPIO_READ_BUFFER:
                case ACTION_ADC_READ_BUFFER:
                case ACTION_BUFFER_SEND:
                    // TODO: Add when union supports Phase 1 parameters
                    break;

                default:
                    break;
            }
        }
        // If param_source == PARAM_FROM_CAN_DATA, no parameters are output

        Serial.println();
    }
}

// ============================================================================
// Rule Matching
// ============================================================================

bool ActionManagerBase::matches_rule(const CANMessage& message, const ActionRule& rule) const {
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
// Action Execution Dispatcher
// ============================================================================

bool ActionManagerBase::execute_action(const ActionRule& rule, const CANMessage& message) {
    // Determine if we should extract parameters from CAN data or use fixed rule parameters
    bool use_can_data = (rule.param_source == PARAM_FROM_CAN_DATA);

    switch (rule.action) {
        case ACTION_GPIO_SET:
        case ACTION_GPIO_CLEAR:
        case ACTION_GPIO_TOGGLE: {
            uint8_t pin;
            if (use_can_data) {
                const ActionDefinition* def = get_action_definition(rule.action);
                if (def && def->param_count >= 1) {
                    pin = extract_uint8(message.data + rule.param_data_offset, def->param_map[0]);
                } else {
                    return false;  // No definition available
                }
            } else {
                pin = rule.params.gpio.pin;
            }
            return execute_gpio_action(rule.action, pin);
        }

        case ACTION_PWM_SET: {
            uint8_t pin, duty;
            if (use_can_data) {
                const ActionDefinition* def = get_action_definition(rule.action);
                if (def && def->param_count >= 2) {
                    pin = extract_uint8(message.data + rule.param_data_offset, def->param_map[0]);
                    duty = extract_uint8(message.data + rule.param_data_offset, def->param_map[1]);
                } else {
                    return false;
                }
            } else {
                pin = rule.params.pwm.pin;
                duty = rule.params.pwm.duty;
            }
            return execute_pwm_action(pin, duty);
        }

        case ACTION_NEOPIXEL_COLOR: {
            uint8_t r, g, b, brightness;
            if (use_can_data) {
                const ActionDefinition* def = get_action_definition(rule.action);
                if (def && def->param_count >= 4) {
                    r = extract_uint8(message.data + rule.param_data_offset, def->param_map[0]);
                    g = extract_uint8(message.data + rule.param_data_offset, def->param_map[1]);
                    b = extract_uint8(message.data + rule.param_data_offset, def->param_map[2]);
                    brightness = extract_uint8(message.data + rule.param_data_offset, def->param_map[3]);
                } else {
                    return false;
                }
            } else {
                r = rule.params.neopixel.r;
                g = rule.params.neopixel.g;
                b = rule.params.neopixel.b;
                brightness = rule.params.neopixel.brightness;
            }
            return execute_neopixel_action(r, g, b, brightness);
        }

        case ACTION_NEOPIXEL_OFF:
            return execute_neopixel_action(0, 0, 0, 0);

        case ACTION_CAN_SEND:
            return execute_can_send_action(
                rule.params.can_send.can_id,
                rule.params.can_send.data,
                rule.params.can_send.length
            );

        case ACTION_CAN_SEND_PERIODIC:
            // Periodic actions are mainly handled by update_periodic()
            // but can also be triggered by CAN messages to start/restart
            return execute_can_send_action(
                rule.params.can_send.can_id,
                rule.params.can_send.data,
                rule.params.can_send.length
            );

        default:
            return false;  // Unsupported action
    }
}

// ============================================================================
// Platform-Agnostic CAN Send
// ============================================================================

bool ActionManagerBase::execute_can_send_action(uint32_t can_id, const uint8_t* data, uint8_t length) {
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

// ============================================================================
// Persistence (Delegates to Platform Implementation)
// ============================================================================

bool ActionManagerBase::save_rules() {
    return save_rules_impl();
}

uint8_t ActionManagerBase::load_rules() {
    uint8_t loaded = load_rules_impl();

    // Update next_rule_id to be higher than any loaded rule ID
    if (loaded > 0) {
        uint8_t max_id = 0;
        for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
            if (rules_[i].id > max_id) {
                max_id = rules_[i].id;
            }
        }
        next_rule_id_ = max_id + 1;
    }

    return loaded;
}

// ============================================================================
// Helper Methods
// ============================================================================

int8_t ActionManagerBase::find_empty_slot() const {
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id == 0) {
            return i;
        }
    }
    return -1;  // No empty slots
}

int8_t ActionManagerBase::find_rule_index(uint8_t rule_id) const {
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id == rule_id) {
            return i;
        }
    }
    return -1;  // Not found
}

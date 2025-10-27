#include "action_manager.h"
#include <Arduino.h>
#include <string.h>
#include "../capabilities/board_capabilities.h"
#include "../utils/pin_error_logger.h"

// Platform-specific pin capabilities
#ifdef PLATFORM_SAMD51
#include "../capabilities/samd51/samd51_pin_caps.h"
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

    // Phase 1: Initialize pin capability system
    #ifdef PLATFORM_SAMD51
    samd51_init_pin_capabilities(&pin_manager_);
    Serial.println("[INIT] Pin capability system initialized");
    #endif

    // Phase 1: Initialize data buffer
    action_buffer_.clear();
    Serial.println("[INIT] Action data buffer initialized");

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

uint8_t ActionManager::update_periodic() {
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

    // Auto-save to persistent storage
    save_rules();

    return new_rule.id;
}

uint8_t ActionManager::parse_and_add_rule(const char* command_str) {
    if (!initialized_ || !command_str) {
        return 0;
    }

    // Parse format: ID:CAN_ID:CAN_MASK:DATA:DATA_MASK:DATA_LEN:ACTION_TYPE:PARAM1:PARAM2:...
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

    if (strcmp(action_type, "GPIO_SET") == 0 && token_count >= 8) {
        rule.action = ACTION_GPIO_SET;
        rule.params.gpio.pin = atoi(tokens[7]);

    } else if (strcmp(action_type, "GPIO_CLEAR") == 0 && token_count >= 8) {
        rule.action = ACTION_GPIO_CLEAR;
        rule.params.gpio.pin = atoi(tokens[7]);

    } else if (strcmp(action_type, "GPIO_TOGGLE") == 0 && token_count >= 8) {
        rule.action = ACTION_GPIO_TOGGLE;
        rule.params.gpio.pin = atoi(tokens[7]);

    } else if (strcmp(action_type, "PWM_SET") == 0 && token_count >= 9) {
        rule.action = ACTION_PWM_SET;
        rule.params.pwm.pin = atoi(tokens[7]);
        rule.params.pwm.duty = atoi(tokens[8]);

    } else if (strcmp(action_type, "NEOPIXEL_COLOR") == 0 && token_count >= 11) {
        rule.action = ACTION_NEOPIXEL_COLOR;
        rule.params.neopixel.r = atoi(tokens[7]);
        rule.params.neopixel.g = atoi(tokens[8]);
        rule.params.neopixel.b = atoi(tokens[9]);
        rule.params.neopixel.brightness = atoi(tokens[10]);

    } else if (strcmp(action_type, "NEOPIXEL_OFF") == 0) {
        rule.action = ACTION_NEOPIXEL_OFF;

    } else if (strcmp(action_type, "CAN_SEND_PERIODIC") == 0 && token_count >= 10) {
        rule.action = ACTION_CAN_SEND_PERIODIC;
        rule.params.can_send.can_id = strtoul(tokens[7], nullptr, 16);
        // Parse data bytes from tokens[8] (comma-separated)
        const char* data_str = tokens[8];
        rule.params.can_send.length = 0;
        // TODO: Parse comma-separated data bytes
        // Parse interval
        rule.params.can_send.interval_ms = atoi(tokens[9]);

    } else {
        // Unsupported action type
        return 0;
    }

    // Add the rule
    return add_rule(rule);
}

bool ActionManager::remove_rule(uint8_t rule_id) {
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

bool ActionManager::set_rule_enabled(uint8_t rule_id, bool enabled) {
    int8_t index = find_rule_index(rule_id);
    if (index < 0) {
        return false;
    }

    rules_[index].enabled = enabled;

    // Auto-save to persistent storage
    save_rules();

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

void ActionManager::print_rules() const {
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id == 0) {
            continue;  // Skip empty slots
        }

        const ActionRule& rule = rules_[i];

        // Format: ACTION;ID;ENABLED;CAN_ID;ACTION_TYPE;DETAILS
        char buffer[128];
        snprintf(buffer, sizeof(buffer), "ACTION;%d;%s;0x%lX;%s",
            rule.id,
            rule.enabled ? "true" : "false",
            (unsigned long)rule.can_id,
            action_type_to_string(rule.action));

        Serial.print(buffer);

        // Add action-specific parameters
        switch (rule.action) {
            case ACTION_GPIO_SET:
            case ACTION_GPIO_CLEAR:
            case ACTION_GPIO_TOGGLE:
                Serial.print(";Pin:");
                Serial.print(rule.params.gpio.pin);
                break;
            case ACTION_PWM_SET:
                Serial.print(";Pin:");
                Serial.print(rule.params.pwm.pin);
                Serial.print(" Duty:");
                Serial.print(rule.params.pwm.duty);
                break;
            case ACTION_NEOPIXEL_COLOR:
                Serial.print(";R:");
                Serial.print(rule.params.neopixel.r);
                Serial.print(" G:");
                Serial.print(rule.params.neopixel.g);
                Serial.print(" B:");
                Serial.print(rule.params.neopixel.b);
                Serial.print(" Br:");
                Serial.print(rule.params.neopixel.brightness);
                break;
            case ACTION_CAN_SEND:
            case ACTION_CAN_SEND_PERIODIC:
                Serial.print(";CAN:0x");
                Serial.print(rule.params.can_send.can_id, HEX);
                if (rule.action == ACTION_CAN_SEND_PERIODIC) {
                    Serial.print(" Int:");
                    Serial.print(rule.params.can_send.interval_ms);
                    Serial.print("ms");
                }
                break;
            default:
                break;
        }

        Serial.println();
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
#ifdef PLATFORM_SAMD51
    // Count active rules
    uint8_t active_count = 0;
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        if (rules_[i].id != 0) {
            active_count++;
        }
    }

    // Save to Flash
    return save_rules_to_flash(rules_, active_count);
#elif defined(PLATFORM_RP2040)
    // TODO: Implement RP2040 flash storage
    return false;
#else
    return false;
#endif
}

uint8_t ActionManager::load_rules() {
#ifdef PLATFORM_SAMD51
    // Try to load rules from Flash
    uint8_t loaded = load_rules_from_flash(rules_, MAX_ACTION_RULES);

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
#elif defined(PLATFORM_RP2040)
    // TODO: Implement RP2040 flash loading
    return 0;
#else
    return 0;
#endif
}

// ============================================================================
// Phase 1: New Action Handlers
// ============================================================================

#ifdef PLATFORM_SAMD51

bool ActionManager::execute_pwm_configure_action(uint8_t pin, uint32_t freq_hz, uint8_t duty, uint8_t resolution) {
    // Validate pin supports PWM
    if (!pwm_interface_.is_valid_pwm_pin(pin)) {
        LOG_PIN_ERROR(pin, "Pin does not support PWM");
        return false;
    }

    // Check pin availability
    if (!pin_manager_.is_available(pin, PINMODE_PWM)) {
        LOG_PIN_ERROR(pin, "Pin already allocated or reserved");
        return false;
    }

    // Allocate pin for PWM
    if (!pin_manager_.allocate_pin(pin, PINMODE_PWM)) {
        LOG_PIN_ERROR(pin, "Failed to allocate pin for PWM");
        return false;
    }

    // Configure PWM with frequency
    bool result = pwm_interface_.configure(pin, freq_hz, duty, resolution);
    if (result) {
        Serial.printf("[ACTION] PWM configured: pin=%d freq=%luHz duty=%d%% res=%d-bit\n",
                     pin, freq_hz, duty, resolution);
    }
    return result;
}

bool ActionManager::execute_i2c_write_action(uint8_t sda, uint8_t scl, uint8_t addr, uint8_t reg, uint8_t data) {
    // Initialize I2C
    if (!i2c_interface_.initialize(sda, scl)) {
        Serial.printf("[I2C_ERROR] Failed to initialize: %s\n", i2c_interface_.get_last_error());
        return false;
    }

    // Write single byte
    bool result = i2c_interface_.write(addr, reg, &data, 1);
    if (result) {
        Serial.printf("[ACTION] I2C write: addr=0x%02X reg=0x%02X data=0x%02X\n", addr, reg, data);
    } else {
        Serial.printf("[I2C_ERROR] Write failed: %s\n", i2c_interface_.get_last_error());
    }
    return result;
}

bool ActionManager::execute_i2c_read_buffer_action(uint8_t sda, uint8_t scl, uint8_t addr, uint8_t reg,
                                                    uint8_t num_bytes, uint8_t slot) {
    // Validate buffer slot
    if (slot + num_bytes > 8) {
        Serial.printf("[BUFFER_ERROR] I2C read would overflow buffer: slot=%d bytes=%d\n", slot, num_bytes);
        return false;
    }

    // Initialize I2C
    if (!i2c_interface_.initialize(sda, scl)) {
        Serial.printf("[I2C_ERROR] Failed to initialize: %s\n", i2c_interface_.get_last_error());
        return false;
    }

    // Read data into temporary buffer
    uint8_t temp_data[8];
    if (!i2c_interface_.read(addr, reg, temp_data, num_bytes)) {
        Serial.printf("[I2C_ERROR] Read failed: %s\n", i2c_interface_.get_last_error());
        return false;
    }

    // Write to action buffer
    if (!action_buffer_.write(slot, temp_data, num_bytes)) {
        Serial.printf("[BUFFER_ERROR] Failed to write I2C data to buffer slot %d\n", slot);
        return false;
    }

    Serial.printf("[ACTION] I2C read to buffer: addr=0x%02X reg=0x%02X bytes=%d slot=%d\n",
                 addr, reg, num_bytes, slot);
    return true;
}

bool ActionManager::execute_gpio_read_buffer_action(uint8_t pin, uint8_t slot) {
    // Validate buffer slot
    if (slot >= 8) {
        Serial.printf("[BUFFER_ERROR] Invalid buffer slot: %d\n", slot);
        return false;
    }

    // Check pin availability for input
    if (!pin_manager_.is_available(pin, PINMODE_GPIO_INPUT)) {
        LOG_PIN_ERROR(pin, "Pin not available for GPIO input");
        return false;
    }

    // Allocate pin
    if (!pin_manager_.allocate_pin(pin, PINMODE_GPIO_INPUT)) {
        LOG_PIN_ERROR(pin, "Failed to allocate pin");
        return false;
    }

    // Configure pin as input
    pinMode(pin, INPUT);

    // Read pin state
    uint8_t value = digitalRead(pin) ? 1 : 0;

    // Write to buffer
    if (!action_buffer_.write(slot, &value, 1)) {
        Serial.printf("[BUFFER_ERROR] Failed to write GPIO to buffer slot %d\n", slot);
        return false;
    }

    Serial.printf("[ACTION] GPIO read to buffer: pin=%d value=%d slot=%d\n", pin, value, slot);
    return true;
}

bool ActionManager::execute_adc_read_buffer_action(uint8_t pin, uint8_t slot) {
    // Validate buffer slot (ADC uses 2 bytes)
    if (slot + 1 >= 8) {
        Serial.printf("[BUFFER_ERROR] ADC read would overflow buffer: slot=%d\n", slot);
        return false;
    }

    // Check pin availability for ADC
    if (!pin_manager_.is_available(pin, PINMODE_ADC)) {
        LOG_PIN_ERROR(pin, "Pin not available for ADC");
        return false;
    }

    // Allocate pin
    if (!pin_manager_.allocate_pin(pin, PINMODE_ADC)) {
        LOG_PIN_ERROR(pin, "Failed to allocate pin for ADC");
        return false;
    }

    // Read ADC value (10-bit or 12-bit depending on platform)
    uint16_t adc_value = analogRead(pin);

    // Write as uint16 (little-endian)
    uint8_t data[2] = {
        static_cast<uint8_t>(adc_value & 0xFF),
        static_cast<uint8_t>((adc_value >> 8) & 0xFF)
    };

    if (!action_buffer_.write(slot, data, 2)) {
        Serial.printf("[BUFFER_ERROR] Failed to write ADC to buffer slot %d\n", slot);
        return false;
    }

    Serial.printf("[ACTION] ADC read to buffer: pin=%d value=%d slot=%d\n", pin, adc_value, slot);
    return true;
}

bool ActionManager::execute_buffer_send_action(uint32_t can_id, uint8_t length, bool clear_after) {
    // Validate length
    if (length > 8) {
        Serial.printf("[BUFFER_ERROR] Invalid CAN length: %d\n", length);
        return false;
    }

    // Get buffer data
    uint8_t valid_length;
    const uint8_t* data = action_buffer_.read_all(valid_length);

    // Use requested length or valid length, whichever is smaller
    uint8_t send_length = (length < valid_length) ? length : valid_length;

    // Send CAN message
    bool result = execute_can_send_action(can_id, data, send_length);

    // Clear buffer if requested
    if (clear_after) {
        action_buffer_.clear();
        Serial.println("[ACTION] Buffer cleared after send");
    }

    if (result) {
        Serial.printf("[ACTION] Buffer sent as CAN: id=0x%03lX len=%d clear=%d\n",
                     can_id, send_length, clear_after);
    }
    return result;
}

bool ActionManager::execute_buffer_clear_action() {
    action_buffer_.clear();
    Serial.println("[ACTION] Buffer manually cleared");
    return true;
}

#endif // PLATFORM_SAMD51

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
        case ACTION_CAN_SEND_PERIODIC: return "CAN_SEND_PERIODIC";
        case ACTION_PWM_SET: return "PWM_SET";
        case ACTION_NEOPIXEL_COLOR: return "NEOPIXEL_COLOR";
        case ACTION_NEOPIXEL_OFF: return "NEOPIXEL_OFF";
        // Phase 1 actions
        case ACTION_PWM_CONFIGURE: return "PWM_CONFIGURE";
        case ACTION_I2C_WRITE: return "I2C_WRITE";
        case ACTION_I2C_READ_BUFFER: return "I2C_READ_BUFFER";
        case ACTION_GPIO_READ_BUFFER: return "GPIO_READ_BUFFER";
        case ACTION_ADC_READ_BUFFER: return "ADC_READ_BUFFER";
        case ACTION_BUFFER_SEND: return "BUFFER_SEND";
        case ACTION_BUFFER_CLEAR: return "BUFFER_CLEAR";
        default: return "UNKNOWN";
    }
}

bool is_action_supported(ActionType type) {
    switch (type) {
        case ACTION_GPIO_SET:
        case ACTION_GPIO_CLEAR:
        case ACTION_GPIO_TOGGLE:
        case ACTION_GPIO_READ_BUFFER:
            return platform_capabilities.has_capability(CAP_GPIO_DIGITAL);

        case ACTION_CAN_SEND:
        case ACTION_CAN_SEND_PERIODIC:
        case ACTION_BUFFER_SEND:
            return platform_capabilities.has_capability(CAP_CAN_SEND);

        case ACTION_PWM_SET:
        case ACTION_PWM_CONFIGURE:
            return platform_capabilities.has_capability(CAP_GPIO_PWM);

        case ACTION_NEOPIXEL_COLOR:
        case ACTION_NEOPIXEL_OFF:
            return platform_capabilities.has_capability(CAP_NEOPIXEL);

        // Phase 1 actions
        case ACTION_ADC_READ_BUFFER:
            return platform_capabilities.has_capability(CAP_GPIO_ANALOG);

        case ACTION_I2C_WRITE:
        case ACTION_I2C_READ_BUFFER:
            return platform_capabilities.has_capability(CAP_I2C);

        case ACTION_BUFFER_CLEAR:
            return true;  // Always supported

        default:
            return false;
    }
}

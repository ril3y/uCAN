#ifdef PLATFORM_ESP32

#include "esp32_action_manager.h"
#include "../../boards/board_interface.h"
#include "../../boards/board_registry.h"
#include <Preferences.h>
#include <Arduino.h>
#include <WiFi.h>

// ============================================================================
// Custom Command Implementations
// ============================================================================

// DAC is only available on original ESP32, not ESP32-S2/S3/C3
#if !defined(CONFIG_IDF_TARGET_ESP32S2) && !defined(CONFIG_IDF_TARGET_ESP32S3) && !defined(CONFIG_IDF_TARGET_ESP32C3)
/**
 * DAC Custom Command
 * Format: dac:PIN:VALUE
 * Example: dac:25:128 (set GPIO25 DAC to 128/255 = 1.65V)
 * Note: Only available on original ESP32 (GPIO25/26)
 */
class DACCommand : public CustomCommand {
public:
    const char* get_name() const override { return "dac"; }
    const char* get_description() const override {
        return "Set DAC output (GPIO25/26, 8-bit: 0-255)";
    }
    const char* get_category() const override { return "Analog"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        static const ParamDef params[] = {
            {"pin", "DAC pin (25 or 26)", PARAM_ENUM, 25, 26, "25,26", true},
            {"value", "8-bit DAC value (0-255)", PARAM_UINT8, 0, 255, nullptr, true}
        };
        count = 2;
        return params;
    }

    bool execute(const char* params) override {
        if (!params) return false;

        // Parse PIN:VALUE
        char buffer[32];
        strncpy(buffer, params, sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\0';

        char* colon = strchr(buffer, ':');
        if (!colon) return false;

        *colon = '\0';
        uint8_t pin = atoi(buffer);
        uint8_t value = atoi(colon + 1);

        // ESP32 has DAC on GPIO25 and GPIO26 only
        if (pin != 25 && pin != 26) {
            Serial.println("ERROR: DAC only available on GPIO25, GPIO26");
            return false;
        }

        dacWrite(pin, value);  // 8-bit DAC (0-255)
        Serial.printf("DAC pin %d set to %d\n", pin, value);
        return true;
    }
};
#endif // Original ESP32 only

/**
 * WiFi Info Custom Command
 * Format: wifi
 * Example: wifi (displays WiFi status)
 */
class WiFiCommand : public CustomCommand {
public:
    const char* get_name() const override { return "wifi"; }
    const char* get_description() const override {
        return "Get WiFi status and connection info";
    }
    const char* get_category() const override { return "Network"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        count = 0;
        return nullptr;
    }

    bool execute(const char* params) override {
        // Report WiFi status
        Serial.println("STATUS:WIFI");
        Serial.printf("  Enabled: %s\n", WiFi.getMode() != WIFI_MODE_NULL ? "Yes" : "No");

        if (WiFi.getMode() != WIFI_MODE_NULL) {
            Serial.printf("  Status: %s\n", WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected");

            if (WiFi.status() == WL_CONNECTED) {
                Serial.printf("  SSID: %s\n", WiFi.SSID().c_str());
                Serial.printf("  IP: %s\n", WiFi.localIP().toString().c_str());
                Serial.printf("  RSSI: %d dBm\n", WiFi.RSSI());
            }
        }
        return true;
    }
};

// ============================================================================
// ESP32ActionManager Implementation
// ============================================================================

// PWM configuration for LEDC
#define PWM_FREQ 5000      // 5 kHz PWM frequency
#define PWM_RESOLUTION 8   // 8-bit resolution (0-255)

// Preferences namespace for flash storage
#define PREFS_NAMESPACE "ucan"

ESP32ActionManager::ESP32ActionManager()
    : ActionManagerBase()
    , board_impl_(nullptr) {

    // Initialize PWM channel tracking
    for (int i = 0; i < 16; i++) {
        pwm_channels_[i].pin = 0;
        pwm_channels_[i].channel = i;
        pwm_channels_[i].in_use = false;
    }
}

ESP32ActionManager::~ESP32ActionManager() {
    // Clean up board implementation
    if (board_impl_) {
        delete board_impl_;
        board_impl_ = nullptr;
    }

    // Detach all PWM channels
    for (int i = 0; i < 16; i++) {
        if (pwm_channels_[i].in_use) {
            ledcDetachPin(pwm_channels_[i].pin);
        }
    }
}

bool ESP32ActionManager::initialize(CANInterface* can_if) {
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
            Serial.printf("STATUS;INFO;Board: %s\n", board_impl_->get_board_name());
        }
    }

    Serial.println("ESP32 Action Manager initialized");
    return true;
}

// GPIO Actions
bool ESP32ActionManager::execute_gpio_action(ActionType type, uint8_t pin) {
    // Validate pin number
    if (pin >= GPIO_COUNT) {
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

// PWM Actions using LEDC
bool ESP32ActionManager::execute_pwm_action(uint8_t pin, uint8_t duty) {
    // Validate pin
    if (pin >= GPIO_COUNT) {
        return false;
    }

    // Find or allocate LEDC channel for this pin
    uint8_t channel = allocate_pwm_channel(pin);
    if (channel >= 16) {
        return false;  // No channels available
    }

    // Setup PWM if not already configured
    if (!setup_pwm(pin, channel)) {
        return false;
    }

    // Set duty cycle (0-255 maps to 0-100%)
    ledcWrite(channel, duty);
    return true;
}

// NeoPixel Actions
bool ESP32ActionManager::execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
    // NeoPixel support is now handled by board implementations
    // Generic ESP32 boards don't have NeoPixels
    // Board-specific implementations (T-CAN485, etc.) handle their own NeoPixels
    return false;
}

// ADC Actions
bool ESP32ActionManager::execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id) {
    // ESP32 ADC pins: GPIO32-GPIO39 (ADC1), GPIO0,2,4,12-15,25-27 (ADC2)
    // ADC2 cannot be used when WiFi is active

    // Read ADC value (12-bit: 0-4095)
    uint16_t adc_value = analogRead(adc_pin);

    // Convert to millivolts (assuming 3.3V reference)
    uint32_t millivolts = (adc_value * 3300) / 4095;

    // Send CAN response with ADC value
    uint8_t data[4];
    data[0] = adc_pin;
    data[1] = (adc_value >> 8) & 0xFF;  // ADC high byte
    data[2] = adc_value & 0xFF;         // ADC low byte
    data[3] = (millivolts >> 8) & 0xFF; // mV high byte (optional)

    return execute_can_send_action(response_id, data, 4);
}

// Persistence using Preferences API
bool ESP32ActionManager::save_rules_impl() {
    Preferences prefs;
    if (!prefs.begin(PREFS_NAMESPACE, false)) {
        return false;
    }

    // Count active rules
    uint8_t count = get_rule_count();
    prefs.putUChar("rule_count", count);

    // Save each rule
    for (uint8_t i = 0; i < MAX_ACTION_RULES; i++) {
        const ActionRule* rule = get_rule(i);
        if (rule && rule->id != 0) {
            char key[16];
            snprintf(key, sizeof(key), "rule_%d", i);
            prefs.putBytes(key, rule, sizeof(ActionRule));
        }
    }

    prefs.end();
    Serial.printf("Saved %d rules to flash\n", count);
    return true;
}

uint8_t ESP32ActionManager::load_rules_impl() {
    Preferences prefs;
    if (!prefs.begin(PREFS_NAMESPACE, true)) {  // true = read-only
        return 0;
    }

    uint8_t count = prefs.getUChar("rule_count", 0);
    uint8_t loaded = 0;

    // Load each saved rule
    for (uint8_t i = 0; i < MAX_ACTION_RULES && i < count; i++) {
        char key[16];
        snprintf(key, sizeof(key), "rule_%d", i);

        ActionRule rule;
        size_t len = prefs.getBytes(key, &rule, sizeof(ActionRule));

        if (len == sizeof(ActionRule) && rule.id != 0) {
            if (add_rule(rule) != 0) {
                loaded++;
            }
        }
    }

    prefs.end();
    Serial.printf("Loaded %d rules from flash\n", loaded);
    return loaded;
}

// Custom Commands
void ESP32ActionManager::register_custom_commands() {
    // Register platform-wide commands

    // DAC command (only on original ESP32 - platform feature check)
    #if !defined(CONFIG_IDF_TARGET_ESP32S2) && !defined(CONFIG_IDF_TARGET_ESP32S3) && !defined(CONFIG_IDF_TARGET_ESP32C3)
    if (get_board_config().has_feature(FEATURE_GPIO_DAC)) {
        static DACCommand dac_cmd;
        custom_commands_.register_command(&dac_cmd);
    }
    #endif

    // WiFi info command (available on all ESP32 variants)
    static WiFiCommand wifi_cmd;
    custom_commands_.register_command(&wifi_cmd);

    // Register board-specific commands
    if (board_impl_) {
        board_impl_->register_custom_commands(custom_commands_);
    }
}

// Action Definition Queries
const ActionDefinition* ESP32ActionManager::get_action_definition(ActionType action) const {
    // Implemented in esp32_action_defs.cpp
    extern const ActionDefinition* esp32_get_action_definition(ActionType action);
    return esp32_get_action_definition(action);
}

const ActionDefinition* const* ESP32ActionManager::get_all_action_definitions(uint8_t& count) const {
    // Implemented in esp32_action_defs.cpp
    extern const ActionDefinition* const* esp32_get_all_action_definitions(uint8_t& count);
    return esp32_get_all_action_definitions(count);
}

// Private Helper Methods

uint8_t ESP32ActionManager::allocate_pwm_channel(uint8_t pin) {
    // Check if pin already has a channel
    for (int i = 0; i < 16; i++) {
        if (pwm_channels_[i].in_use && pwm_channels_[i].pin == pin) {
            return i;
        }
    }

    // Allocate a new channel
    for (int i = 0; i < 16; i++) {
        if (!pwm_channels_[i].in_use) {
            pwm_channels_[i].pin = pin;
            pwm_channels_[i].in_use = true;
            return i;
        }
    }

    return 255;  // No channels available
}

void ESP32ActionManager::free_pwm_channel(uint8_t pin) {
    for (int i = 0; i < 16; i++) {
        if (pwm_channels_[i].in_use && pwm_channels_[i].pin == pin) {
            ledcDetachPin(pin);
            pwm_channels_[i].in_use = false;
            pwm_channels_[i].pin = 0;
            return;
        }
    }
}

bool ESP32ActionManager::setup_pwm(uint8_t pin, uint8_t channel) {
    if (channel >= 16) {
        return false;
    }

    // Configure LEDC channel
    ledcSetup(channel, PWM_FREQ, PWM_RESOLUTION);
    ledcAttachPin(pin, channel);

    return true;
}

#endif // PLATFORM_ESP32

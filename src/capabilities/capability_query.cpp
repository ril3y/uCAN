#include <Arduino.h>
#include <ArduinoJson.h>
#include <string.h>
#include "board_capabilities.h"
#include "../actions/action_manager_base.h"

#ifdef PLATFORM_ESP32
#include <Preferences.h>
#endif

// External reference to action manager (defined in main.cpp)
extern ActionManagerBase* action_manager;

// Device name storage (mutable, can be changed at runtime)
char device_name[MAX_DEVICE_NAME_LENGTH] = "";  // Empty = use default board name

/**
 * Send capabilities as JSON response
 *
 * Format: CAPS;{json object}
 * Example: CAPS;{"board":"<device name>","chip":"<chip name>",...}
 */
void send_capabilities_json() {
    // Create JSON document (stack allocated for efficiency)
    JsonDocument doc;

    // Board info - use custom device name if set, otherwise default board name
    doc["board"] = get_device_name();
    doc["chip"] = platform_capabilities.chip_name;

    // Clock speed in MHz (calculate from F_CPU define)
    #ifdef F_CPU
        doc["clock_mhz"] = F_CPU / 1000000.0;
    #else
        doc["clock_mhz"] = 0;  // Unknown if F_CPU not defined
    #endif

    // Memory info in KB
    doc["flash_kb"] = platform_capabilities.flash_size / 1024.0;
    doc["ram_kb"] = platform_capabilities.ram_size / 1024.0;

    // Protocol and firmware versions
    doc["protocol_version"] = "2.0";
    doc["firmware_version"] = "2.2.0";

    // GPIO info as object
    JsonObject gpio = doc["gpio"].to<JsonObject>();
    gpio["total"] = platform_capabilities.gpio_count;
    gpio["pwm"] = platform_capabilities.pwm_channels;
    gpio["adc"] = platform_capabilities.adc_channels;
    gpio["dac"] = platform_capabilities.dac_channels;

    // Platform-specific hardware info (implemented per-platform)
    JsonObject hardware = doc["hardware"].to<JsonObject>();
    add_platform_hardware_info(hardware);

    // CAN info with required fields (platform-specific values)
    JsonObject can = doc["can"].to<JsonObject>();
    can["controllers"] = platform_capabilities.can_controllers;
    can["max_bitrate"] = platform_capabilities.can_max_bitrate;
    can["fd_capable"] = false;  // CAN-FD not supported on any current platform
    can["filters"] = platform_capabilities.can_filters;

    // Action system info
    doc["max_rules"] = platform_capabilities.max_action_rules;  // Platform-specific rule limit from board config

    // Feature flags as array of strings
    JsonArray features = doc["features"].to<JsonArray>();
    features.add("action_system");  // Required by tests
    features.add("rules_engine");   // Required by tests
    if (platform_capabilities.has_capability(CAP_GPIO_DIGITAL)) features.add("GPIO");
    if (platform_capabilities.has_capability(CAP_GPIO_PWM)) features.add("PWM");
    if (platform_capabilities.has_capability(CAP_GPIO_ANALOG)) features.add("ADC");
    if (platform_capabilities.has_capability(CAP_GPIO_DAC)) features.add("DAC");
    if (platform_capabilities.has_capability(CAP_NEOPIXEL)) features.add("NEOPIXEL");
    if (platform_capabilities.has_capability(CAP_CAN_SEND)) features.add("CAN_SEND");
    if (platform_capabilities.has_capability(CAP_FLASH_STORAGE)) features.add("FLASH");
    if (platform_capabilities.has_capability(CAP_CRYPTO)) features.add("CRYPTO");
    if (platform_capabilities.has_capability(CAP_RTC)) features.add("RTC");
    if (platform_capabilities.has_capability(CAP_I2S)) features.add("I2S");
    if (platform_capabilities.has_capability(CAP_I2C)) features.add("I2C");

    // Send formatted JSON response
    Serial.print("CAPS;");
    serializeJson(doc, Serial);
    Serial.println();
}

/**
 * Send available pin information
 *
 * Format: PINS;<total>;<pwm_pins>;<adc_pins>;<dac_pins>[;<special>]
 */
void send_pin_info() {
    Serial.print("PINS;");
    Serial.print(platform_capabilities.gpio_count);
    Serial.print(";PWM:");
    Serial.print(platform_capabilities.pwm_channels);
    Serial.print(";ADC:");
    Serial.print(platform_capabilities.adc_channels);
    Serial.print(";DAC:");
    Serial.print(platform_capabilities.dac_channels);

    // Add NeoPixel info if available
    if (platform_capabilities.neopixel_available) {
        Serial.print(";NEO:");
        Serial.print(platform_capabilities.neopixel_pin);
    }

    Serial.println();
}

/**
 * Send supported action types
 *
 * Format: ACTIONS;<action1>,<action2>,...
 */
void send_supported_actions() {
    Serial.print("ACTIONS;");

    bool first = true;
    auto print_action = [&first](const char* action) {
        if (!first) Serial.print(",");
        Serial.print(action);
        first = false;
    };

    // Universal actions (all platforms)
    if (platform_capabilities.has_capability(CAP_GPIO_DIGITAL)) {
        print_action("GPIO_SET");
        print_action("GPIO_CLEAR");
        print_action("GPIO_TOGGLE");
    }

    if (platform_capabilities.has_capability(CAP_CAN_SEND)) {
        print_action("CAN_SEND");
        print_action("CAN_SEND_PERIODIC");
    }

    // Platform-specific actions
    if (platform_capabilities.has_capability(CAP_GPIO_PWM)) {
        print_action("PWM_SET");
    }

    if (platform_capabilities.has_capability(CAP_NEOPIXEL)) {
        print_action("NEOPIXEL_COLOR");
        print_action("NEOPIXEL_OFF");
    }

    if (platform_capabilities.has_capability(CAP_GPIO_ANALOG)) {
        print_action("ADC_READ");
        if (platform_capabilities.has_capability(CAP_CAN_SEND)) {
            print_action("ADC_READ_SEND");
        }
    }

    if (platform_capabilities.has_capability(CAP_I2C)) {
        print_action("I2C_WRITE");
        print_action("I2C_READ_BUFFER");
    }

    Serial.println();
}

/**
 * Set custom device name
 *
 * @param name New device name (max MAX_DEVICE_NAME_LENGTH chars)
 */
void set_device_name(const char* name) {
    if (!name) {
        device_name[0] = '\0';  // Clear name
        return;
    }

    // Copy name, ensuring null termination
    strncpy(device_name, name, MAX_DEVICE_NAME_LENGTH - 1);
    device_name[MAX_DEVICE_NAME_LENGTH - 1] = '\0';

    // Save to persistent storage
    bool saved = save_device_name();

    // Send status update with persistence info
    Serial.print("STATUS;NAME_SET;Device name set to: ");
    Serial.print(device_name);
    if (saved) {
        Serial.println(" (saved to flash)");
    } else {
        Serial.println(" (RAM only, not persisted)");
    }
}

/**
 * Get current device name
 *
 * @return Current device name, or board name if not set
 */
const char* get_device_name() {
    if (device_name[0] != '\0') {
        return device_name;
    }
    return platform_capabilities.board_name;
}

/**
 * Load device name from persistent storage
 *
 * Device name is loaded automatically with rules on startup for SAMD51/RP2040,
 * but needs explicit loading from Preferences for ESP32.
 *
 * @return true if custom name is loaded (non-empty)
 */
bool load_device_name() {
#if defined(PLATFORM_ESP32)
    // ESP32: Load from Preferences API
    Preferences prefs;
    if (!prefs.begin("ucan", true)) {  // Read-only
        return false;
    }

    String name = prefs.getString("device_name", "");
    prefs.end();

    if (name.length() > 0 && name.length() < MAX_DEVICE_NAME_LENGTH) {
        strncpy(device_name, name.c_str(), MAX_DEVICE_NAME_LENGTH - 1);
        device_name[MAX_DEVICE_NAME_LENGTH - 1] = '\0';
        return true;
    }
    return false;
#else
    // SAMD51/RP2040: Device name is loaded automatically when rules are loaded
    // This happens in main.cpp setup() via action_manager->load_rules()
    return (device_name[0] != '\0');
#endif
}

/**
 * Save device name to persistent storage
 *
 * Triggers a flash write by saving all rules (which includes device name).
 * The device name is stored in the flash header alongside rules.
 *
 * @return true if name was saved successfully
 */
bool save_device_name() {
    if (!action_manager) {
        return false;  // Action manager not initialized yet
    }

#if defined(PLATFORM_SAMD51)
    // SAMD51: Device name is saved in FlashHeader alongside rules
    // Trigger a rules save which will save the device name too
    return action_manager->save_rules();

#elif defined(PLATFORM_RP2040)
    // RP2040: Device name is saved in FlashHeader alongside rules
    // Trigger a rules save which will save the device name too
    return action_manager->save_rules();

#elif defined(PLATFORM_ESP32)
    // ESP32: Device name is saved separately in Preferences API
    Preferences prefs;
    if (!prefs.begin("ucan", false)) {
        return false;
    }
    bool result = prefs.putString("device_name", device_name);
    prefs.end();
    return result;

#else
    return false;
#endif
}

#include <Arduino.h>
#include <ArduinoJson.h>
#include <string.h>
#include "board_capabilities.h"

// Device name storage (mutable, can be changed at runtime)
char device_name[MAX_DEVICE_NAME_LENGTH] = "";  // Empty = use default board name

/**
 * Send capabilities as JSON response
 *
 * Format: CAPS;{json object}
 * Example: CAPS;{"board":"Feather M4 CAN","chip":"ATSAME51",...}
 */
void send_capabilities_json() {
    // Create JSON document (stack allocated for efficiency)
    JsonDocument doc;

    // Board info
    doc["board"] = platform_capabilities.board_name;
    doc["chip"] = platform_capabilities.chip_name;
    doc["manufacturer"] = platform_capabilities.manufacturer;

    // Add device name if set, otherwise use board name
    if (device_name[0] != '\0') {
        doc["device_name"] = device_name;
    } else {
        doc["device_name"] = platform_capabilities.board_name;
    }

    // Resource counts
    doc["gpio"] = platform_capabilities.gpio_count;
    doc["pwm"] = platform_capabilities.pwm_channels;
    doc["adc"] = platform_capabilities.adc_channels;
    doc["dac"] = platform_capabilities.dac_channels;
    doc["max_rules"] = platform_capabilities.max_action_rules;

    // Memory info
    JsonObject memory = doc["memory"].to<JsonObject>();
    memory["flash"] = platform_capabilities.flash_size;
    memory["ram"] = platform_capabilities.ram_size;
    memory["storage"] = platform_capabilities.storage_size;

    // CAN info
    JsonObject can = doc["can"].to<JsonObject>();
    can["hardware"] = platform_capabilities.can_hardware;
    can["controller"] = platform_capabilities.can_controller;

    // NeoPixel info (if available)
    if (platform_capabilities.neopixel_available) {
        JsonObject neo = doc["neopixel"].to<JsonObject>();
        neo["pin"] = platform_capabilities.neopixel_pin;
        neo["power_pin"] = platform_capabilities.neopixel_power_pin;
    }

    // Feature flags as array of strings
    JsonArray features = doc["features"].to<JsonArray>();
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
    save_device_name();

    // Send status update
    Serial.print("STATUS;NAME_SET;Device name set to: ");
    Serial.println(device_name);
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
 * @return true if name was loaded
 */
bool load_device_name() {
#if defined(PLATFORM_SAMD51)
    // SAMD51: Use EEPROM emulation or Flash storage
    // For now, just return false (not implemented)
    // TODO: Implement Flash storage
    return false;
#elif defined(PLATFORM_RP2040)
    // RP2040: Use Flash storage
    // TODO: Implement Flash storage
    return false;
#else
    return false;
#endif
}

/**
 * Save device name to persistent storage
 *
 * @return true if name was saved
 */
bool save_device_name() {
#if defined(PLATFORM_SAMD51)
    // SAMD51: Use EEPROM emulation or Flash storage
    // For now, just return false (not implemented)
    // TODO: Implement Flash storage
    return false;
#elif defined(PLATFORM_RP2040)
    // RP2040: Use Flash storage
    // TODO: Implement Flash storage
    return false;
#else
    return false;
#endif
}

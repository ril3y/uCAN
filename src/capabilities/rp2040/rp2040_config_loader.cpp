/**
 * RP2040 Default Configuration Loader Implementation
 *
 * Platform-specific implementation for loading default configuration rules.
 * Works with any config header that defines DefaultRuleConfig structures.
 *
 * @file rp2040_config_loader.cpp
 * @author ril3y
 * @date 2025-10-28
 */

#if defined(PLATFORM_RP2040) && defined(HAS_DEFAULT_CONFIG)

#include <Arduino.h>
#include <hardware/clocks.h>
#include "rp2040_config_loader.h"
#include "../board_capabilities.h"

// Include config header if default config is enabled
#ifdef HAS_DEFAULT_CONFIG
#include "../../configs/golf_cart_config.h"
#endif

// Forward declarations of RP2040 flash functions
extern bool init_flash_storage();
extern uint8_t load_rules_from_flash(ActionRule* rules, uint8_t max_count);
extern bool save_rules_to_flash(const ActionRule* rules, uint8_t count);

// Flash constants (match rp2040_flash_storage.cpp)
#define FLASH_MAGIC_NUMBER 0x55434154  // "UCAN"
#define FLASH_TOTAL_SIZE (2 * 1024 * 1024)
#define FLASH_SECTOR_SIZE 4096
#define FLASH_STORAGE_OFFSET (FLASH_TOTAL_SIZE - FLASH_SECTOR_SIZE)
#define XIP_BASE 0x10000000
#define FLASH_STORAGE_ADDRESS (XIP_BASE + FLASH_STORAGE_OFFSET)

struct FlashHeader {
    uint32_t magic;
    uint8_t version;
    uint8_t rule_count;
    uint8_t reserved[2];
    char device_name[32];
};

// ============================================================================
// Private Helper Functions
// ============================================================================

/**
 * Check if flash contains valid rules
 */
static bool flash_has_valid_rules() {
    const FlashHeader* header = (const FlashHeader*)FLASH_STORAGE_ADDRESS;
    return (header->magic == FLASH_MAGIC_NUMBER);
}

/**
 * Check if reset button is pressed
 */
static bool reset_button_pressed(uint8_t pin) {
    pinMode(pin, INPUT_PULLUP);
    delay(10);  // Debounce
    return (digitalRead(pin) == LOW);
}

#ifdef HAS_DEFAULT_CONFIG

/**
 * Convert DefaultRuleConfig to ActionRule
 *
 * Creates a periodic CAN send rule from config data.
 *
 * @param config Source configuration
 * @param rule_id Rule ID (1-255)
 * @return ActionRule ready for action manager
 */
static ActionRule create_rule_from_config(const DefaultRuleConfig& config, uint8_t rule_id) {
    ActionRule rule = {0};

    // Rule management
    rule.id = rule_id;
    rule.enabled = true;

    // Trigger: No CAN RX trigger (periodic only)
    rule.can_id = 0x000;
    rule.can_id_mask = 0x000;
    rule.data_length = 0;

    // Action: Send CAN message periodically
    rule.action = ACTION_CAN_SEND_PERIODIC;
    rule.params.can_send.can_id = config.can_id;
    rule.params.can_send.interval_ms = config.interval_ms;
    rule.params.can_send.length = 8;

    // Copy message data
    memcpy(rule.params.can_send.data, config.data, 8);

    // Initialize periodic state
    rule.last_execute_ms = 0;
    rule.execute_count = 0;

    return rule;
}

/**
 * Write default rules to flash
 */
static uint8_t write_default_rules_to_flash(ActionManagerBase* manager) {
    if (!manager) {
        return 0;
    }

    // Note: CRC validation removed - the CRC8 bytes in the data are part of the
    // golf cart protocol and will be sent as-is on the CAN bus. No need to validate.

    // Create temporary rule array
    ActionRule rules[DEFAULT_NUM_RULES];

    // Convert each config to ActionRule
    for (uint8_t i = 0; i < DEFAULT_NUM_RULES; i++) {
        rules[i] = create_rule_from_config(default_rules[i], i + 1);
    }

    // Save to flash
    if (save_rules_to_flash(rules, DEFAULT_NUM_RULES)) {
        return DEFAULT_NUM_RULES;
    }

    return 0;
}

#endif // HAS_DEFAULT_CONFIG

// ============================================================================
// Public API Implementation
// ============================================================================

bool init_default_config(ActionManagerBase* manager) {
#ifndef HAS_DEFAULT_CONFIG
    // No default config defined at compile time
    Serial.println("INFO: No default configuration enabled");
    return true;  // Not an error, just no config to load
#else

    Serial.println("DEBUG: init_default_config() called");

    if (!manager) {
        Serial.println("ERROR: Config loader requires valid action manager");
        return false;
    }

    Serial.println("DEBUG: Initializing flash storage...");

    // Initialize flash storage
    if (!init_flash_storage()) {
        Serial.println("ERROR: Failed to initialize flash storage");
        return false;
    }

    Serial.println("DEBUG: Flash storage initialized");

    bool button_pressed = reset_button_pressed(DEFAULT_CONFIG_RESET_PIN);
    bool flash_valid = flash_has_valid_rules();
    bool loaded_from_flash = false;

    Serial.print("DEBUG: Button pressed = ");
    Serial.println(button_pressed ? "YES" : "NO");
    Serial.print("DEBUG: Flash valid = ");
    Serial.println(flash_valid ? "YES" : "NO");

    // Decide whether to write default rules
    if (button_pressed) {
        Serial.println("INFO: Reset button pressed - writing default configuration rules");
        uint8_t written = write_default_rules_to_flash(manager);
        if (written == 0) {
            Serial.println("ERROR: Failed to write default rules to flash");
            return false;
        }
        Serial.print("INFO: Wrote ");
        Serial.print(written);
        Serial.println(" default rules to flash");

    } else if (!flash_valid) {
        Serial.println("INFO: Flash empty - initializing with default configuration");
        uint8_t written = write_default_rules_to_flash(manager);
        if (written == 0) {
            Serial.println("ERROR: Failed to write default rules to flash");
            return false;
        }
        Serial.print("INFO: Wrote ");
        Serial.print(written);
        Serial.println(" default rules to flash");

    } else {
        // Flash has valid rules, will be loaded by main.cpp
        loaded_from_flash = true;
    }

    // Print status banner
    print_config_status(DEFAULT_CONFIG_NAME, loaded_from_flash);

    return true;
#endif // HAS_DEFAULT_CONFIG
}

void print_config_status(const char* config_name, bool loaded_from_flash) {
#ifdef HAS_DEFAULT_CONFIG
    Serial.println("========================================");
    Serial.print("Configuration: ");
    Serial.println(config_name);
    Serial.println("========================================");
    Serial.print("Platform: RP2040 @ ");
    Serial.print(clock_get_hz(clk_sys) / 1000000);
    Serial.println(" MHz");
    Serial.print("Reset Pin: GP");
    Serial.println(DEFAULT_CONFIG_RESET_PIN);
    Serial.println();

    if (loaded_from_flash) {
        Serial.println("Status: Loaded existing rules from flash");
    } else {
        Serial.println("Status: Initialized with default configuration rules");
    }

    Serial.println();
    Serial.println("Configured Messages:");
    Serial.println("-------------------");

    for (uint8_t i = 0; i < DEFAULT_NUM_RULES; i++) {
        Serial.print("  0x");
        if (default_rules[i].can_id < 0x100) Serial.print("0");
        if (default_rules[i].can_id < 0x10) Serial.print("0");
        Serial.print(default_rules[i].can_id, HEX);
        Serial.print(" @ ");
        Serial.print(default_rules[i].interval_ms);
        Serial.print("ms - ");
        Serial.println(default_rules[i].description);
    }

    Serial.println();
    Serial.print("Total: ");
    Serial.print(DEFAULT_NUM_RULES);
    Serial.print(" rules (");
    Serial.print(platform_capabilities.max_action_rules - DEFAULT_NUM_RULES);
    Serial.println(" slots free for custom rules)");
    Serial.println();
    Serial.println("To reset to defaults:");
    Serial.print("  Hold button on GP");
    Serial.print(DEFAULT_CONFIG_RESET_PIN);
    Serial.println(" during boot");
    Serial.println("========================================");
#endif
}

#endif // PLATFORM_RP2040 && HAS_DEFAULT_CONFIG

#ifdef PLATFORM_ESP32

#include "../board_capabilities.h"
#include "../../actions/action_types.h"
#include "../../boards/board_registry.h"
#include <Preferences.h>

/**
 * ESP32 Flash Storage using Preferences API
 *
 * ESP32 uses the Preferences library which provides a simple key-value
 * storage API backed by NVS (Non-Volatile Storage) flash.
 *
 * Benefits over direct NVS:
 * - Automatic wear leveling
 * - Namespace support
 * - Type-safe get/put methods
 * - Automatic initialization
 */

#define PREFS_NAMESPACE "ucan"
#define DEVICE_NAME_KEY "device_name"

// Initialize flash storage (called during startup)
bool init_flash_storage() {
    // Preferences automatically initializes NVS
    // Nothing to do here for ESP32
    return true;
}

// Save rules to flash (implemented in ESP32ActionManager)
bool save_rules_to_flash(const ActionRule* rules, uint8_t count) {
    Preferences prefs;
    if (!prefs.begin(PREFS_NAMESPACE, false)) {
        return false;
    }

    prefs.putUChar("rule_count", count);

    for (uint8_t i = 0; i < count; i++) {
        if (rules[i].id != 0) {
            char key[16];
            snprintf(key, sizeof(key), "rule_%d", i);
            prefs.putBytes(key, &rules[i], sizeof(ActionRule));
        }
    }

    prefs.end();
    return true;
}

// Load rules from flash (implemented in ESP32ActionManager)
uint8_t load_rules_from_flash(ActionRule* rules, uint8_t max_count) {
    Preferences prefs;
    if (!prefs.begin(PREFS_NAMESPACE, true)) {  // Read-only
        return 0;
    }

    uint8_t count = prefs.getUChar("rule_count", 0);
    uint8_t loaded = 0;

    for (uint8_t i = 0; i < max_count && i < count; i++) {
        char key[16];
        snprintf(key, sizeof(key), "rule_%d", i);

        size_t len = prefs.getBytes(key, &rules[i], sizeof(ActionRule));
        if (len == sizeof(ActionRule) && rules[i].id != 0) {
            loaded++;
        }
    }

    prefs.end();
    return loaded;
}

// Erase all flash storage
bool erase_flash_storage() {
    Preferences prefs;
    if (!prefs.begin(PREFS_NAMESPACE, false)) {
        return false;
    }

    bool result = prefs.clear();
    prefs.end();
    return result;
}

// Get storage statistics
bool get_flash_storage_stats(uint32_t* used_bytes, uint32_t* total_bytes, uint8_t* rule_capacity) {
    // NVS doesn't provide easy stats, return estimates
    if (used_bytes) *used_bytes = 0;  // Unknown
    if (total_bytes) *total_bytes = 0x6000;  // NVS partition is typically 24KB
    if (rule_capacity) *rule_capacity = MAX_ACTION_RULES;
    return true;
}

// Note: Device name storage functions (save_device_name, load_device_name)
// are implemented in capability_query.cpp for all platforms including ESP32

#endif // PLATFORM_ESP32

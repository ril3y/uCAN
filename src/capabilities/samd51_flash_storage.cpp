#ifdef PLATFORM_SAMD51

#include <Adafruit_SPIFlash.h>
#include "../actions/action_types.h"
#include "../actions/action_manager_base.h"
#include "board_capabilities.h"

// Flash storage configuration
#define FLASH_STORAGE_START_ADDRESS 0x00000  // Start of flash
#define FLASH_MAGIC_NUMBER 0x55434154  // "UCAT" in hex
#define FLASH_VERSION 1

// Flash layout
struct FlashHeader {
    uint32_t magic;           // Magic number to identify valid data
    uint8_t version;          // Storage format version
    uint8_t rule_count;       // Number of rules stored
    uint8_t reserved[2];      // Reserved for future use
    char device_name[MAX_DEVICE_NAME_LENGTH];
};

// QSPI Flash configuration for Feather M4 CAN
Adafruit_FlashTransport_QSPI flashTransport;
Adafruit_SPIFlash flash(&flashTransport);

static bool flash_initialized = false;

/**
 * Initialize Flash storage
 */
bool init_flash_storage() {
    if (flash_initialized) {
        return true;
    }

    if (!flash.begin()) {
        return false;
    }

    flash_initialized = true;
    return true;
}

/**
 * Save action rules to Flash
 */
bool save_rules_to_flash(const ActionRule* rules, uint8_t count) {
    if (!init_flash_storage()) {
        return false;
    }

    // Prepare header
    FlashHeader header;
    header.magic = FLASH_MAGIC_NUMBER;
    header.version = FLASH_VERSION;
    header.rule_count = count;
    strncpy(header.device_name, device_name, MAX_DEVICE_NAME_LENGTH - 1);
    header.device_name[MAX_DEVICE_NAME_LENGTH - 1] = '\0';

    // Write header
    if (!flash.writeBuffer(FLASH_STORAGE_START_ADDRESS,
                          (uint8_t*)&header, sizeof(FlashHeader))) {
        return false;
    }

    // Write rules
    uint32_t rules_address = FLASH_STORAGE_START_ADDRESS + sizeof(FlashHeader);
    if (!flash.writeBuffer(rules_address,
                          (uint8_t*)rules,
                          sizeof(ActionRule) * count)) {
        return false;
    }

    return true;
}

/**
 * Load action rules from Flash
 */
uint8_t load_rules_from_flash(ActionRule* rules, uint8_t max_count) {
    if (!init_flash_storage()) {
        return 0;
    }

    // Read header
    FlashHeader header;
    if (!flash.readBuffer(FLASH_STORAGE_START_ADDRESS,
                         (uint8_t*)&header, sizeof(FlashHeader))) {
        return 0;
    }

    // Verify magic number
    if (header.magic != FLASH_MAGIC_NUMBER) {
        return 0;  // No valid data in flash
    }

    // Verify version
    if (header.version != FLASH_VERSION) {
        return 0;  // Incompatible version
    }

    // Load device name
    strncpy(device_name, header.device_name, MAX_DEVICE_NAME_LENGTH - 1);
    device_name[MAX_DEVICE_NAME_LENGTH - 1] = '\0';

    // Read rules
    uint8_t count_to_load = (header.rule_count < max_count) ? header.rule_count : max_count;
    uint32_t rules_address = FLASH_STORAGE_START_ADDRESS + sizeof(FlashHeader);

    if (!flash.readBuffer(rules_address,
                         (uint8_t*)rules,
                         sizeof(ActionRule) * count_to_load)) {
        return 0;
    }

    return count_to_load;
}

/**
 * Erase Flash storage (clear all rules and device name)
 */
bool erase_flash_storage() {
    if (!init_flash_storage()) {
        return false;
    }

    // Calculate total size to erase
    uint32_t size = sizeof(FlashHeader) + (sizeof(ActionRule) * MAX_ACTION_RULES);

    // Erase the sector containing our data
    // Flash sectors are typically 4KB, so we'll erase enough sectors
    uint32_t sectors = (size + 4095) / 4096;

    for (uint32_t i = 0; i < sectors; i++) {
        if (!flash.eraseSector(i)) {
            return false;
        }
    }

    return true;
}

#endif // PLATFORM_SAMD51

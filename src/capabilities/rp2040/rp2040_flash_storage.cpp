/**
 * RP2040 Flash Storage Implementation
 *
 * Provides persistent storage for action rules and device names using the
 * RP2040's built-in 2MB flash memory. This implementation mirrors the SAMD51
 * flash storage but uses the Pico SDK's flash APIs instead of SPI flash.
 *
 * FLASH SAFETY CONSIDERATIONS:
 * - RP2040 flash has ~100,000 erase cycles per sector
 * - Flash sectors are 4KB (4096 bytes) on RP2040
 * - Writing requires erasing the entire sector first
 * - Flash writes MUST disable interrupts (including USB) briefly
 * - We use the last sector of flash to avoid firmware conflicts
 *
 * MEMORY LAYOUT:
 * - Flash storage location: Last 4KB sector (0x001FF000 on 2MB flash)
 * - Layout: [FlashHeader][ActionRule array]
 * - FlashHeader includes magic number, version, rule count, and device name
 *
 * WEAR LEVELING:
 * - Basic strategy: Only write when rules or device name actually change
 * - Future improvement: Implement multi-sector rotation if write frequency becomes an issue
 *
 * @file rp2040_flash_storage.cpp
 * @author Riley (ril3y)
 * @date 2025
 */

#ifdef PLATFORM_RP2040

#include <Arduino.h>
#include <hardware/flash.h>
#include <hardware/sync.h>
#include <string.h>
#include "../../actions/action_types.h"
#include "../../actions/action_manager_base.h"
#include "../board_capabilities.h"

// ============================================================================
// Flash Storage Configuration
// ============================================================================

// Magic number to identify valid flash data: "UCAN" in hex
#define FLASH_MAGIC_NUMBER 0x55434154
#define FLASH_VERSION 1

// RP2040 flash specifications
#define FLASH_SECTOR_SIZE 4096              // RP2040 flash sector size
#define FLASH_PAGE_SIZE 256                 // RP2040 flash page size
#define FLASH_TOTAL_SIZE (2 * 1024 * 1024)  // 2MB total flash

// Storage location: Use last sector of flash (safe from firmware)
// XIP_BASE is the memory-mapped flash base address (0x10000000)
#define FLASH_STORAGE_OFFSET (FLASH_TOTAL_SIZE - FLASH_SECTOR_SIZE)  // Offset from flash start
#define FLASH_STORAGE_ADDRESS (XIP_BASE + FLASH_STORAGE_OFFSET)      // Memory-mapped address

// ============================================================================
// Flash Data Structures
// ============================================================================

/**
 * Flash Header Structure
 *
 * Stored at the beginning of the flash storage sector. Contains metadata
 * about the stored rules and the user-configurable device name.
 */
struct FlashHeader {
    uint32_t magic;           // Magic number to identify valid data (FLASH_MAGIC_NUMBER)
    uint8_t version;          // Storage format version (FLASH_VERSION)
    uint8_t rule_count;       // Number of rules stored (0-MAX_ACTION_RULES)
    uint8_t reserved[2];      // Reserved for future use (padding)
    char device_name[MAX_DEVICE_NAME_LENGTH];  // User-configurable device name
};

// ============================================================================
// Static Variables
// ============================================================================

static bool flash_initialized = false;

// ============================================================================
// Flash Storage Functions
// ============================================================================

/**
 * Initialize Flash Storage
 *
 * Verifies that flash parameters are correct and the storage area is accessible.
 * This is a lightweight operation since we're using memory-mapped flash.
 *
 * @return true if flash storage is ready, false on error
 */
bool init_flash_storage() {
    if (flash_initialized) {
        return true;
    }

    // Verify flash storage offset is sector-aligned
    if ((FLASH_STORAGE_OFFSET % FLASH_SECTOR_SIZE) != 0) {
        Serial.println("ERROR: Flash storage offset not sector-aligned");
        return false;
    }

    // Verify we have enough space for header + max rules
    uint32_t required_size = sizeof(FlashHeader) + (sizeof(ActionRule) * MAX_ACTION_RULES);
    if (required_size > FLASH_SECTOR_SIZE) {
        Serial.println("ERROR: Flash sector too small for storage");
        return false;
    }

    flash_initialized = true;
    return true;
}

/**
 * Save Action Rules to Flash
 *
 * Writes the FlashHeader and action rules to the flash storage sector.
 * This operation:
 * 1. Erases the entire 4KB sector
 * 2. Writes the header with device name
 * 3. Writes all active rules
 *
 * WARNING: This function disables interrupts briefly during flash operations!
 * USB serial and CAN interrupts will be paused for ~100ms.
 *
 * @param rules Array of ActionRule structures to save
 * @param count Number of rules to save (0 to MAX_ACTION_RULES)
 * @return true if save successful, false on error
 */
bool save_rules_to_flash(const ActionRule* rules, uint8_t count) {
    if (!init_flash_storage()) {
        return false;
    }

    if (!rules || count > MAX_ACTION_RULES) {
        return false;
    }

    // Prepare buffer (must be sector-aligned for flash operations)
    // We'll prepare the entire sector in RAM before writing
    static uint8_t sector_buffer[FLASH_SECTOR_SIZE] __attribute__((aligned(4)));
    memset(sector_buffer, 0xFF, FLASH_SECTOR_SIZE);  // Erased flash reads as 0xFF

    // Prepare header
    FlashHeader* header = (FlashHeader*)sector_buffer;
    header->magic = FLASH_MAGIC_NUMBER;
    header->version = FLASH_VERSION;
    header->rule_count = count;
    header->reserved[0] = 0;
    header->reserved[1] = 0;
    strncpy(header->device_name, device_name, MAX_DEVICE_NAME_LENGTH - 1);
    header->device_name[MAX_DEVICE_NAME_LENGTH - 1] = '\0';

    // Copy rules after header
    if (count > 0) {
        uint8_t* rules_ptr = sector_buffer + sizeof(FlashHeader);
        memcpy(rules_ptr, rules, sizeof(ActionRule) * count);
    }

    // CRITICAL SECTION: Disable interrupts during flash operations
    // This is required by the RP2040 hardware - flash operations conflict with XIP
    uint32_t interrupts = save_and_disable_interrupts();

    // Erase the flash sector
    flash_range_erase(FLASH_STORAGE_OFFSET, FLASH_SECTOR_SIZE);

    // Write the prepared buffer to flash
    // Note: flash_range_program requires data to be in RAM, not flash
    flash_range_program(FLASH_STORAGE_OFFSET, sector_buffer, FLASH_SECTOR_SIZE);

    // END CRITICAL SECTION: Restore interrupts
    restore_interrupts(interrupts);

    // Verify write by reading back magic number
    const FlashHeader* verify_header = (const FlashHeader*)FLASH_STORAGE_ADDRESS;
    if (verify_header->magic != FLASH_MAGIC_NUMBER) {
        Serial.println("ERROR: Flash write verification failed");
        return false;
    }

    return true;
}

/**
 * Load Action Rules from Flash
 *
 * Reads the FlashHeader and action rules from flash storage.
 * This operation:
 * 1. Verifies magic number and version
 * 2. Loads device name into global device_name variable
 * 3. Copies rules to provided array
 *
 * @param rules Array to store loaded ActionRule structures
 * @param max_count Maximum number of rules to load (size of rules array)
 * @return Number of rules loaded (0 if flash empty or error)
 */
uint8_t load_rules_from_flash(ActionRule* rules, uint8_t max_count) {
    if (!init_flash_storage()) {
        return 0;
    }

    if (!rules || max_count == 0) {
        return 0;
    }

    // Read header from memory-mapped flash
    const FlashHeader* header = (const FlashHeader*)FLASH_STORAGE_ADDRESS;

    // Verify magic number
    if (header->magic != FLASH_MAGIC_NUMBER) {
        // Flash is empty or corrupted
        return 0;
    }

    // Verify version
    if (header->version != FLASH_VERSION) {
        Serial.print("WARNING: Flash version mismatch (expected ");
        Serial.print(FLASH_VERSION);
        Serial.print(", got ");
        Serial.print(header->version);
        Serial.println(")");
        return 0;
    }

    // Load device name from header
    strncpy(device_name, header->device_name, MAX_DEVICE_NAME_LENGTH - 1);
    device_name[MAX_DEVICE_NAME_LENGTH - 1] = '\0';

    // Determine how many rules to load
    uint8_t count_to_load = (header->rule_count < max_count) ? header->rule_count : max_count;

    if (count_to_load == 0) {
        return 0;  // No rules to load
    }

    // Load rules from flash
    const uint8_t* rules_ptr = (const uint8_t*)FLASH_STORAGE_ADDRESS + sizeof(FlashHeader);
    memcpy(rules, rules_ptr, sizeof(ActionRule) * count_to_load);

    return count_to_load;
}

/**
 * Erase Flash Storage
 *
 * Completely erases the flash storage sector, clearing all rules and device name.
 * This sets the flash back to the erased state (all 0xFF bytes).
 *
 * WARNING: This function disables interrupts briefly during flash erase!
 *
 * @return true if erase successful, false on error
 */
bool erase_flash_storage() {
    if (!init_flash_storage()) {
        return false;
    }

    // CRITICAL SECTION: Disable interrupts during flash erase
    uint32_t interrupts = save_and_disable_interrupts();

    // Erase the storage sector
    flash_range_erase(FLASH_STORAGE_OFFSET, FLASH_SECTOR_SIZE);

    // END CRITICAL SECTION: Restore interrupts
    restore_interrupts(interrupts);

    // Verify erase by checking magic number is no longer present
    const FlashHeader* header = (const FlashHeader*)FLASH_STORAGE_ADDRESS;
    if (header->magic == FLASH_MAGIC_NUMBER) {
        Serial.println("ERROR: Flash erase verification failed");
        return false;
    }

    return true;
}

/**
 * Get Flash Storage Statistics
 *
 * Returns information about flash usage and storage capacity.
 * Useful for diagnostics and monitoring wear.
 *
 * @param used_bytes Output: Number of bytes currently in use
 * @param total_bytes Output: Total available storage bytes
 * @param rule_capacity Output: Maximum rules that can be stored
 * @return true if statistics retrieved successfully
 */
bool get_flash_storage_stats(uint32_t* used_bytes, uint32_t* total_bytes, uint8_t* rule_capacity) {
    if (!init_flash_storage()) {
        return false;
    }

    if (total_bytes) {
        *total_bytes = FLASH_SECTOR_SIZE;
    }

    if (rule_capacity) {
        uint32_t available_space = FLASH_SECTOR_SIZE - sizeof(FlashHeader);
        *rule_capacity = available_space / sizeof(ActionRule);
    }

    if (used_bytes) {
        const FlashHeader* header = (const FlashHeader*)FLASH_STORAGE_ADDRESS;
        if (header->magic == FLASH_MAGIC_NUMBER) {
            *used_bytes = sizeof(FlashHeader) + (header->rule_count * sizeof(ActionRule));
        } else {
            *used_bytes = 0;  // Flash is empty
        }
    }

    return true;
}

#endif // PLATFORM_RP2040

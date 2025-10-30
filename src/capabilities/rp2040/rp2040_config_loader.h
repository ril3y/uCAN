/**
 * RP2040 Default Configuration Loader
 *
 * Platform-specific implementation for loading default configuration rules
 * from compile-time config headers into flash storage.
 *
 * This module provides the interface for initializing the RP2040 with
 * default rules defined in config headers (e.g., golf_cart_config.h).
 *
 * @file rp2040_config_loader.h
 * @author ril3y
 * @date 2025-10-28
 */

#pragma once

#if defined(PLATFORM_RP2040) && defined(HAS_DEFAULT_CONFIG)

#include "../../actions/action_manager_base.h"

/**
 * Initialize RP2040 with default configuration
 *
 * This function should be called during setup(), after flash storage is
 * initialized but before the main loop starts.
 *
 * Behavior:
 * 1. Check if reset button is pressed (defined in config header)
 * 2. Check if flash contains valid rules
 * 3. If button pressed OR flash empty: Write default rules from config
 * 4. Print status information via Serial
 *
 * Config headers included via build flags (e.g., -DHAS_DEFAULT_CONFIG)
 *
 * @param manager Pointer to initialized ActionManagerBase
 * @return true if initialization successful, false on error
 */
bool init_default_config(ActionManagerBase* manager);

/**
 * Print configuration status banner
 *
 * Displays information about loaded rules and how to reset to defaults
 *
 * @param config_name Name of the loaded configuration
 * @param loaded_from_flash True if rules were loaded from existing flash
 */
void print_config_status(const char* config_name, bool loaded_from_flash);

#endif // PLATFORM_RP2040 && HAS_DEFAULT_CONFIG

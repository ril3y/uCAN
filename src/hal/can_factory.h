#pragma once

#include "can_interface.h"
#include "../boards/board_registry.h"

// Include platform-specific CAN implementations based on detected platform
#ifdef PLATFORM_RP2040
    #include "rp2040_can.h"
#endif

#ifdef PLATFORM_SAMD51
    #include "samd51_can.h"
#endif

#ifdef PLATFORM_ESP32
    #include "esp32_can.h"
#endif

#ifdef PLATFORM_STM32
    #include "stm32_can.h"
#endif

/**
 * Factory class to create the appropriate CAN interface for the current platform
 *
 * This factory uses the centralized board registry to automatically select
 * the correct CAN implementation based on compile-time platform detection.
 */
class CANFactory {
public:
    /**
     * Create a CAN interface instance for the current platform
     * @return Pointer to CANInterface instance (caller owns memory)
     */
    static CANInterface* create() {
        #ifdef PLATFORM_RP2040
            return new RP2040CAN();
        #elif defined(PLATFORM_SAMD51)
            return new SAMD51CAN();
        #elif defined(PLATFORM_ESP32)
            return new ESP32CAN();
        #elif defined(PLATFORM_STM32)
            return new STM32CAN();
        #else
            #error "Unsupported platform - no CAN implementation available"
        #endif
    }

    /**
     * Get the platform name for the current build
     * @return Platform name string
     */
    static const char* get_platform_name() {
        return PLATFORM_NAME;
    }

    /**
     * Get the board name for the current build
     * @return Board name string
     */
    static const char* get_board_name() {
        return BOARD_NAME;
    }

    /**
     * Get default configuration for the current platform
     * Uses board-specific defaults from board registry
     * @return Default CANConfig structure
     */
    static CANConfig get_default_config() {
        CANConfig config;
        config.bitrate = DEFAULT_CAN_BITRATE;
        config.loopback_mode = false;
        config.listen_only_mode = false;
        config.acceptance_filter = 0;
        config.acceptance_mask = 0;
        config.enable_timestamps = true;
        return config;
    }
};
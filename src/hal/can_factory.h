#pragma once

#include "can_interface.h"
#include "platform_config.h"

#ifdef PLATFORM_RP2040
    #include "rp2040_can.h"
#endif

#ifdef PLATFORM_SAMD51
    #include "samd51_can.h"
#endif

/**
 * Factory class to create the appropriate CAN interface for the current platform
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
     * Get default configuration for the current platform
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
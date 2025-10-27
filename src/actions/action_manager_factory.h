#pragma once

#include "action_manager_base.h"
#include "../hal/platform_config.h"

// Platform-specific includes
#ifdef PLATFORM_SAMD51
#include "../capabilities/samd51/samd51_action_manager.h"
#endif

#ifdef PLATFORM_RP2040
#include "../capabilities/rp2040/rp2040_action_manager.h"
#endif

#ifdef PLATFORM_ESP32
// Future: #include "../capabilities/esp32/esp32_action_manager.h"
#endif

#ifdef PLATFORM_STM32
// Future: #include "../capabilities/stm32/stm32_action_manager.h"
#endif

/**
 * ActionManagerFactory
 *
 * Factory pattern for creating platform-specific ActionManager instances.
 * Uses compile-time platform detection to instantiate the correct implementation.
 *
 * Usage:
 *   ActionManagerBase* manager = ActionManagerFactory::create();
 *   manager->initialize(can_interface);
 *
 * Memory Management:
 *   - Factory returns a dynamically allocated instance
 *   - Caller is responsible for deletion
 *   - For embedded systems, recommend single global instance
 */
class ActionManagerFactory {
public:
    /**
     * Create platform-specific ActionManager instance
     * @return Pointer to ActionManagerBase-derived instance, or nullptr on failure
     */
    static ActionManagerBase* create() {
#ifdef PLATFORM_SAMD51
        return new SAMD51ActionManager();
#elif defined(PLATFORM_RP2040)
        return new RP2040ActionManager();
#elif defined(PLATFORM_ESP32)
        // Future: return new ESP32ActionManager();
        return nullptr;
#elif defined(PLATFORM_STM32)
        // Future: return new STM32ActionManager();
        return nullptr;
#else
        #error "No ActionManager implementation for this platform"
        return nullptr;
#endif
    }

    /**
     * Get platform name string
     * @return Human-readable platform name
     */
    static const char* get_platform_name() {
#ifdef PLATFORM_SAMD51
        return "SAMD51";
#elif defined(PLATFORM_RP2040)
        return "RP2040";
#elif defined(PLATFORM_ESP32)
        return "ESP32";
#elif defined(PLATFORM_STM32)
        return "STM32";
#else
        return "Unknown";
#endif
    }

private:
    // Prevent instantiation
    ActionManagerFactory() = delete;
    ~ActionManagerFactory() = delete;
};

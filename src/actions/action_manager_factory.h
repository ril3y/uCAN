#pragma once

#include "action_manager_base.h"
#include "../boards/board_registry.h"

// Platform-specific includes based on detected platform
#ifdef PLATFORM_SAMD51
#include "../capabilities/samd51/samd51_action_manager.h"
#endif

#ifdef PLATFORM_RP2040
#include "../capabilities/rp2040/rp2040_action_manager.h"
#endif

#ifdef PLATFORM_ESP32
#include "../capabilities/esp32/esp32_action_manager.h"
#endif

#ifdef PLATFORM_STM32
#include "../capabilities/stm32/stm32_action_manager.h"
#endif

/**
 * ActionManagerFactory
 *
 * Factory pattern for creating platform-specific ActionManager instances.
 * Uses the centralized board registry for platform detection and instantiation.
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
        return new ESP32ActionManager();
#elif defined(PLATFORM_STM32)
        return new STM32ActionManager();
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
        return PLATFORM_NAME;
    }

    /**
     * Get board name string
     * @return Human-readable board name
     */
    static const char* get_board_name() {
        return BOARD_NAME;
    }

    /**
     * Get maximum number of action rules for current board
     * @return Max action rules supported
     */
    static uint8_t get_max_action_rules() {
        return MAX_ACTION_RULES;
    }

private:
    // Prevent instantiation
    ActionManagerFactory() = delete;
    ~ActionManagerFactory() = delete;
};

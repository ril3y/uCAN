#include "../actions/action_types.h"
#include "../actions/action_manager_base.h"
#include "board_capabilities.h"

#ifdef PLATFORM_SAMD51

/**
 * SAMD51 Default Action Rules
 *
 * These rules provide visual feedback using the onboard NeoPixel:
 * - Rule 1: Yellow flash on any CAN RX (catch-all rule)
 *
 * Note: TX and error feedback are not implemented via rules since they
 * aren't triggered by received CAN messages. Those could be added as
 * periodic "heartbeat" style indicators if needed.
 *
 * Users can disable, modify, or remove these rules via action commands.
 */

/**
 * Load default SAMD51-specific action rules
 *
 * This function is called during initialization to set up visual feedback
 * rules for the Feather M4 CAN board.
 *
 * @param manager Pointer to the ActionManagerBase
 * @return Number of rules loaded
 */
uint8_t load_samd51_default_rules(ActionManagerBase* manager) {
    if (!manager) {
        return 0;
    }

    uint8_t loaded = 0;

    // Rule 1: Yellow NeoPixel on any CAN RX (any ID, any data)
    ActionRule rx_rule = {0};
    rx_rule.id = 0;  // Will be assigned by manager
    rx_rule.enabled = true;
    rx_rule.can_id = 0x000;
    rx_rule.can_id_mask = 0x000;  // Match any CAN ID
    rx_rule.data_length = 0;  // Match any data length
    // data_mask all zeros = don't care about data bytes
    rx_rule.action = ACTION_NEOPIXEL_COLOR;
    rx_rule.params.neopixel.r = 255;
    rx_rule.params.neopixel.g = 255;
    rx_rule.params.neopixel.b = 0;  // Yellow
    rx_rule.params.neopixel.brightness = 64;  // 25% brightness
    rx_rule.last_execute_ms = 0;
    rx_rule.execute_count = 0;

    if (manager->add_rule(rx_rule) > 0) {
        loaded++;
    }

    // Note: TX and error feedback require different mechanism
    // since they're not triggered by received CAN messages.
    // For now, we'll keep those in the HAL layer or add a
    // callback system later.

    return loaded;
}

#endif // PLATFORM_SAMD51

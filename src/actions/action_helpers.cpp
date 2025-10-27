#include "action_types.h"
#include "../capabilities/board_capabilities.h"

/**
 * Convert ActionType enum to string
 */
const char* action_type_to_string(ActionType type) {
    switch (type) {
        case ACTION_NONE:                return "NONE";
        case ACTION_GPIO_SET:            return "GPIO_SET";
        case ACTION_GPIO_CLEAR:          return "GPIO_CLEAR";
        case ACTION_GPIO_TOGGLE:         return "GPIO_TOGGLE";
        case ACTION_CAN_SEND:            return "CAN_SEND";
        case ACTION_CAN_SEND_PERIODIC:   return "CAN_SEND_PERIODIC";
        case ACTION_PWM_SET:             return "PWM_SET";
        case ACTION_NEOPIXEL_COLOR:      return "NEOPIXEL";
        case ACTION_NEOPIXEL_OFF:        return "NEOPIXEL_OFF";
        case ACTION_PWM_CONFIGURE:       return "PWM_CONFIGURE";
        case ACTION_I2C_WRITE:           return "I2C_WRITE";
        case ACTION_I2C_READ_BUFFER:     return "I2C_READ_BUFFER";
        case ACTION_GPIO_READ_BUFFER:    return "GPIO_READ_BUFFER";
        case ACTION_ADC_READ_BUFFER:     return "ADC_READ_BUFFER";
        case ACTION_BUFFER_SEND:         return "BUFFER_SEND";
        case ACTION_BUFFER_CLEAR:        return "BUFFER_CLEAR";
        default:                         return "UNKNOWN";
    }
}

/**
 * Check if an action is supported on the current platform
 *
 * This function checks against the platform capabilities to determine
 * if a given action type can be executed.
 *
 * @param type Action type to check
 * @return true if action is supported, false otherwise
 */
bool is_action_supported(ActionType type) {
    // Universal actions supported on all platforms
    switch (type) {
        case ACTION_GPIO_SET:
        case ACTION_GPIO_CLEAR:
        case ACTION_GPIO_TOGGLE:
            return platform_capabilities.has_capability(CAP_GPIO_DIGITAL);

        case ACTION_CAN_SEND:
        case ACTION_CAN_SEND_PERIODIC:
            return platform_capabilities.has_capability(CAP_CAN_SEND);

        // Platform-specific actions
        case ACTION_PWM_SET:
        case ACTION_PWM_CONFIGURE:
            return platform_capabilities.has_capability(CAP_GPIO_PWM);

        case ACTION_NEOPIXEL_COLOR:
        case ACTION_NEOPIXEL_OFF:
            return platform_capabilities.has_capability(CAP_NEOPIXEL);

        case ACTION_I2C_WRITE:
        case ACTION_I2C_READ_BUFFER:
            return platform_capabilities.has_capability(CAP_I2C);

        case ACTION_GPIO_READ_BUFFER:
            return platform_capabilities.has_capability(CAP_GPIO_DIGITAL);

        case ACTION_ADC_READ_BUFFER:
            return platform_capabilities.has_capability(CAP_GPIO_ANALOG);

        case ACTION_BUFFER_SEND:
        case ACTION_BUFFER_CLEAR:
            return true;  // All platforms support buffer operations

        case ACTION_NONE:
        default:
            return false;
    }
}

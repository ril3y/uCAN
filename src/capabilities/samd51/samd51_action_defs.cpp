#include "../../actions/param_mapping.h"
#include "../../actions/action_types.h"

#ifdef PLATFORM_SAMD51

// ============================================================================
// SAMD51-Specific Action Definitions
// ============================================================================

// ----------------------------------------------------------------------------
// NeoPixel RGB Control
// ----------------------------------------------------------------------------

static const ParamMapping NEOPIXEL_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "r", "action_param"},           // Red from byte 0
    {1, 0, 8, PARAM_UINT8, 0, 255, "g", "action_param"},           // Green from byte 1
    {2, 0, 8, PARAM_UINT8, 0, 255, "b", "action_param"},           // Blue from byte 2
    {3, 0, 8, PARAM_UINT8, 0, 255, "brightness", "action_param"}   // Brightness from byte 3
};

static const ActionDefinition NEOPIXEL_DEF = {
    .action = ACTION_NEOPIXEL_COLOR,
    .name = "NEOPIXEL",
    .description = "Control onboard NeoPixel RGB LED",
    .category = "Display",
    .trigger_type = "can_msg",
    .param_count = 4,
    .param_map = NEOPIXEL_PARAMS
};

// ----------------------------------------------------------------------------
// PWM Control
// ----------------------------------------------------------------------------

static const ParamMapping PWM_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin", "action_param"},    // Pin number from byte 0
    {1, 0, 8, PARAM_UINT8, 0, 255, "duty", "action_param"}    // Duty cycle from byte 1
};

static const ActionDefinition PWM_DEF = {
    .action = ACTION_PWM_SET,
    .name = "PWM_SET",
    .description = "Set PWM duty cycle on pin",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 2,
    .param_map = PWM_PARAMS
};

// ----------------------------------------------------------------------------
// GPIO Control (Single Pin)
// ----------------------------------------------------------------------------

static const ParamMapping GPIO_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin", "action_param"}     // Pin number from byte 0
};

static const ActionDefinition GPIO_SET_DEF = {
    .action = ACTION_GPIO_SET,
    .name = "GPIO_SET",
    .description = "Set GPIO pin HIGH",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 1,
    .param_map = GPIO_PARAMS
};

static const ActionDefinition GPIO_CLEAR_DEF = {
    .action = ACTION_GPIO_CLEAR,
    .name = "GPIO_CLEAR",
    .description = "Set GPIO pin LOW",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 1,
    .param_map = GPIO_PARAMS
};

static const ActionDefinition GPIO_TOGGLE_DEF = {
    .action = ACTION_GPIO_TOGGLE,
    .name = "GPIO_TOGGLE",
    .description = "Toggle GPIO pin state",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 1,
    .param_map = GPIO_PARAMS
};

// ----------------------------------------------------------------------------
// CAN Send
// ----------------------------------------------------------------------------

static const ParamMapping CAN_SEND_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "can_id", "output_param"},     // CAN ID to send to
};

static const ActionDefinition CAN_SEND_DEF = {
    .action = ACTION_CAN_SEND,
    .name = "CAN_SEND",
    .description = "Send CAN message",
    .category = "CAN",
    .trigger_type = "can_msg",
    .param_count = 1,
    .param_map = CAN_SEND_PARAMS
};

// ----------------------------------------------------------------------------
// CAN Send Periodic
// ----------------------------------------------------------------------------

static const ParamMapping CAN_SEND_PERIODIC_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "can_id", "output_param"},     // CAN ID to send to
    {1, 0, 8, PARAM_UINT8, 0, 255, "interval_ms", "trigger_param"} // Interval in milliseconds (simplified)
};

static const ActionDefinition CAN_SEND_PERIODIC_DEF = {
    .action = ACTION_CAN_SEND_PERIODIC,
    .name = "CAN_SEND_PERIODIC",
    .description = "Send CAN message periodically",
    .category = "CAN",
    .trigger_type = "periodic",
    .param_count = 2,
    .param_map = CAN_SEND_PERIODIC_PARAMS
};

// ============================================================================
// Action Definition Registry for SAMD51
// ============================================================================

static const ActionDefinition* SAMD51_ACTION_DEFS[] = {
    &GPIO_SET_DEF,
    &GPIO_CLEAR_DEF,
    &GPIO_TOGGLE_DEF,
    &PWM_DEF,
    &NEOPIXEL_DEF,
    &CAN_SEND_DEF,
    &CAN_SEND_PERIODIC_DEF
};

static const uint8_t SAMD51_ACTION_COUNT = sizeof(SAMD51_ACTION_DEFS) / sizeof(SAMD51_ACTION_DEFS[0]);

// ============================================================================
// Platform Implementation of Registry Functions
// ============================================================================

const ActionDefinition* get_action_definition(ActionType action) {
    for (uint8_t i = 0; i < SAMD51_ACTION_COUNT; i++) {
        const ActionDefinition* def = SAMD51_ACTION_DEFS[i];
        if (def->action == action) {
            return def;
        }
    }
    return nullptr;
}

const ActionDefinition* const* get_all_action_definitions(uint8_t& count) {
    count = SAMD51_ACTION_COUNT;
    return SAMD51_ACTION_DEFS;
}

#endif // PLATFORM_SAMD51

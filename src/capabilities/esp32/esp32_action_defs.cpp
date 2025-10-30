#ifdef PLATFORM_ESP32

#include <cstddef>
#include "../../actions/action_types.h"
#include "../../actions/param_mapping.h"

// GPIO Actions
static const ParamMapping GPIO_SET_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 39, "pin", "action_param", "GPIO Pin", "GPIO pin number (0-39)"}
};

static const ParamMapping GPIO_CLEAR_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 39, "pin", "action_param", "GPIO Pin", "GPIO pin number (0-39)"}
};

static const ParamMapping GPIO_TOGGLE_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 39, "pin", "action_param", "GPIO Pin", "GPIO pin number (0-39)"}
};

// PWM Actions
static const ParamMapping PWM_SET_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 39, "pin", "action_param", "PWM Pin", "GPIO pin for PWM output"},
    {1, 0, 8, PARAM_UINT8, 0, 255, "duty", "action_param", "Duty Cycle", "PWM duty cycle (0-255)"}
};

// NeoPixel Actions (if board has NeoPixel)
static const ParamMapping NEOPIXEL_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "r", "action_param", "Red", "Red intensity (0-255)"},
    {1, 0, 8, PARAM_UINT8, 0, 255, "g", "action_param", "Green", "Green intensity (0-255)"},
    {2, 0, 8, PARAM_UINT8, 0, 255, "b", "action_param", "Blue", "Blue intensity (0-255)"},
    {3, 0, 8, PARAM_UINT8, 0, 255, "brightness", "action_param", "Brightness", "Overall brightness (0-255)"}
};

// ADC Read Actions
static const ParamMapping ADC_READ_BUFFER_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 39, "adc_pin", "action_param", "ADC Pin", "ADC input pin"}
};

// CAN Send Actions
static const ParamMapping CAN_SEND_PARAMS[] = {
    {0, 0, 11, PARAM_UINT16, 0, 0x7FF, "can_id", "action_param", "CAN ID", "CAN message ID"},
    {1, 0, 8, PARAM_UINT8, 0, 8, "length", "action_param", "Length", "Data length (0-8 bytes)"}
};

// Action Definitions
static const ActionDefinition GPIO_SET_DEF = {
    .action = ACTION_GPIO_SET,
    .name = "GPIO_SET",
    .description = "Set GPIO pin HIGH",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 1,
    .param_map = GPIO_SET_PARAMS
};

static const ActionDefinition GPIO_CLEAR_DEF = {
    .action = ACTION_GPIO_CLEAR,
    .name = "GPIO_CLEAR",
    .description = "Set GPIO pin LOW",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 1,
    .param_map = GPIO_CLEAR_PARAMS
};

static const ActionDefinition GPIO_TOGGLE_DEF = {
    .action = ACTION_GPIO_TOGGLE,
    .name = "GPIO_TOGGLE",
    .description = "Toggle GPIO pin state",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 1,
    .param_map = GPIO_TOGGLE_PARAMS
};

static const ActionDefinition PWM_SET_DEF = {
    .action = ACTION_PWM_SET,
    .name = "PWM_SET",
    .description = "Set PWM duty cycle (LEDC)",
    .category = "PWM",
    .trigger_type = "can_msg",
    .param_count = 2,
    .param_map = PWM_SET_PARAMS
};

static const ActionDefinition NEOPIXEL_DEF = {
    .action = ACTION_NEOPIXEL_COLOR,
    .name = "NEOPIXEL",
    .description = "Set NeoPixel RGB color",
    .category = "Display",
    .trigger_type = "can_msg",
    .param_count = 4,
    .param_map = NEOPIXEL_PARAMS
};

static const ActionDefinition ADC_READ_BUFFER_DEF = {
    .action = ACTION_ADC_READ_BUFFER,
    .name = "ADC_READ",
    .description = "Read ADC value into buffer",
    .category = "Analog",
    .trigger_type = "can_msg",
    .param_count = 1,
    .param_map = ADC_READ_BUFFER_PARAMS
};

static const ActionDefinition CAN_SEND_DEF = {
    .action = ACTION_CAN_SEND,
    .name = "CAN_SEND",
    .description = "Send CAN message",
    .category = "CAN",
    .trigger_type = "can_msg",
    .param_count = 2,
    .param_map = CAN_SEND_PARAMS
};

// Array of pointers to action definitions
static const ActionDefinition* ACTION_DEFS[] = {
    &GPIO_SET_DEF,
    &GPIO_CLEAR_DEF,
    &GPIO_TOGGLE_DEF,
    &PWM_SET_DEF,
    &NEOPIXEL_DEF,
    &ADC_READ_BUFFER_DEF,
    &CAN_SEND_DEF
};

#define ACTION_DEF_COUNT (sizeof(ACTION_DEFS) / sizeof(ActionDefinition*))

// Action definition query functions (called by action manager)
const ActionDefinition* esp32_get_action_definition(ActionType action) {
    for (size_t i = 0; i < ACTION_DEF_COUNT; i++) {
        if (ACTION_DEFS[i]->action == action) {
            return ACTION_DEFS[i];
        }
    }
    return nullptr;
}

const ActionDefinition* const* esp32_get_all_action_definitions(uint8_t& count) {
    count = ACTION_DEF_COUNT;
    return ACTION_DEFS;
}

#endif // PLATFORM_ESP32

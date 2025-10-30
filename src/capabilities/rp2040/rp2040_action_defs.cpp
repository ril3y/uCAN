#include "rp2040_action_manager.h"
#include "../../actions/param_mapping.h"
#include "../../actions/action_types.h"

#ifdef PLATFORM_RP2040

// ============================================================================
// RP2040-Specific Action Definitions
// ============================================================================
// RP2040 (Raspberry Pi Pico) hardware capabilities:
// - Basic GPIO
// - Hardware PWM (16 channels, 16-bit duty cycle)
// - 12-bit ADC (4 external channels + temperature sensor)
// - NO built-in NeoPixel
// - NO hardware I2C support in this configuration
// ============================================================================

// ----------------------------------------------------------------------------
// GPIO Control (Single Pin)
// ----------------------------------------------------------------------------

static const ParamMapping GPIO_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin", "action_param", "GPIO Pin Number", "Pin to control (e.g., 25 for onboard LED)"}
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
// PWM Control
// ----------------------------------------------------------------------------

static const ParamMapping PWM_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin", "action_param", "PWM Pin", "Pin number supporting PWM (e.g., GP0-GP29)"},
    {1, 0, 8, PARAM_UINT8, 0, 255, "duty", "action_param", "Duty Cycle", "PWM duty cycle (0=off, 128=50%, 255=full)"}
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
// CAN Send
// ----------------------------------------------------------------------------

static const ParamMapping CAN_SEND_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "can_id", "output_param", "CAN Message ID", "Target CAN ID to send message to (e.g., 0x100)"}
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
    {0, 0, 8, PARAM_UINT8, 0, 255, "can_id", "output_param", "CAN Message ID", "Target CAN ID to send message to (e.g., 0x100)"},
    {1, 0, 8, PARAM_UINT8, 0, 255, "interval_ms", "trigger_param", "Send Interval", "How often to send in milliseconds (e.g., 100 = 10Hz)"}
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

// ----------------------------------------------------------------------------
// PWM with Frequency Control
// ----------------------------------------------------------------------------

static const ParamMapping PWM_CONFIGURE_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin", "action_param", "PWM Pin", "Pin number supporting PWM"},
    {1, 0, 16, PARAM_UINT16, 1, 100000, "freq_hz", "action_param", "Frequency", "PWM frequency in Hz (1-100000)"},
    {3, 0, 8, PARAM_UINT8, 0, 100, "duty_percent", "action_param", "Duty Cycle", "PWM duty cycle percentage (0-100)"},
    {4, 0, 8, PARAM_UINT8, 8, 16, "resolution", "action_param", "Resolution", "PWM resolution in bits (8, 10, 12, or 16)"}
};

static const ActionDefinition PWM_CONFIGURE_DEF = {
    .action = ACTION_PWM_CONFIGURE,
    .name = "PWM_CONFIGURE",
    .description = "Configure PWM with frequency, duty cycle, and resolution",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 4,
    .param_map = PWM_CONFIGURE_PARAMS
};

// ----------------------------------------------------------------------------
// GPIO Read to Buffer
// ----------------------------------------------------------------------------

static const ParamMapping GPIO_READ_BUFFER_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin", "action_param", "GPIO Pin", "Pin to read"},
    {1, 0, 8, PARAM_UINT8, 0, 7, "buffer_slot", "output_param", "Buffer Slot", "Slot in data buffer (0-7)"}
};

static const ActionDefinition GPIO_READ_BUFFER_DEF = {
    .action = ACTION_GPIO_READ_BUFFER,
    .name = "GPIO_READ_BUFFER",
    .description = "Read GPIO pin state into data buffer",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 2,
    .param_map = GPIO_READ_BUFFER_PARAMS
};

// ----------------------------------------------------------------------------
// ADC Read to Buffer
// ----------------------------------------------------------------------------

static const ParamMapping ADC_READ_BUFFER_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin", "action_param", "ADC Pin", "Analog pin to read (26-29 for ADC0-3)"},
    {1, 0, 8, PARAM_UINT8, 0, 6, "buffer_slot", "output_param", "Buffer Slot", "Starting slot in buffer (0-6, uses 2 bytes)"}
};

static const ActionDefinition ADC_READ_BUFFER_DEF = {
    .action = ACTION_ADC_READ_BUFFER,
    .name = "ADC_READ_BUFFER",
    .description = "Read ADC value into data buffer (12-bit, 2 bytes)",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 2,
    .param_map = ADC_READ_BUFFER_PARAMS
};

// ----------------------------------------------------------------------------
// Buffer Send
// ----------------------------------------------------------------------------

static const ParamMapping BUFFER_SEND_PARAMS[] = {
    {0, 0, 32, PARAM_UINT32, 0, 0x7FF, "can_id", "output_param", "CAN ID", "CAN message ID to send (0x000-0x7FF)"},
    {4, 0, 8, PARAM_UINT8, 1, 8, "length", "output_param", "Length", "Number of bytes to send from buffer (1-8)"},
    {5, 0, 1, PARAM_BOOL, 0, 1, "clear_after", "output_param", "Clear After", "Clear buffer after sending (0=no, 1=yes)"}
};

static const ActionDefinition BUFFER_SEND_DEF = {
    .action = ACTION_BUFFER_SEND,
    .name = "BUFFER_SEND",
    .description = "Send data buffer as CAN message",
    .category = "CAN",
    .trigger_type = "can_msg",
    .param_count = 3,
    .param_map = BUFFER_SEND_PARAMS
};

// ----------------------------------------------------------------------------
// Buffer Clear
// ----------------------------------------------------------------------------

static const ActionDefinition BUFFER_CLEAR_DEF = {
    .action = ACTION_BUFFER_CLEAR,
    .name = "BUFFER_CLEAR",
    .description = "Clear data buffer manually",
    .category = "System",
    .trigger_type = "can_msg",
    .param_count = 0,
    .param_map = nullptr
};

// ============================================================================
// Action Definition Registry for RP2040
// ============================================================================

static const ActionDefinition* RP2040_ACTION_DEFS[] = {
    &GPIO_SET_DEF,
    &GPIO_CLEAR_DEF,
    &GPIO_TOGGLE_DEF,
    &PWM_DEF,
    &CAN_SEND_DEF,
    &CAN_SEND_PERIODIC_DEF,
    &PWM_CONFIGURE_DEF,
    &GPIO_READ_BUFFER_DEF,
    &ADC_READ_BUFFER_DEF,
    &BUFFER_SEND_DEF,
    &BUFFER_CLEAR_DEF
    // NOTE: NO NeoPixel support (no onboard NeoPixel on Pico)
    // NOTE: NO I2C actions (not implemented in this configuration)
};

static const uint8_t RP2040_ACTION_COUNT = sizeof(RP2040_ACTION_DEFS) / sizeof(RP2040_ACTION_DEFS[0]);

// ============================================================================
// RP2040ActionManager Method Implementations
// ============================================================================

const ActionDefinition* RP2040ActionManager::get_action_definition(ActionType action) const {
    for (uint8_t i = 0; i < RP2040_ACTION_COUNT; i++) {
        const ActionDefinition* def = RP2040_ACTION_DEFS[i];
        if (def->action == action) {
            return def;
        }
    }
    return nullptr;
}

const ActionDefinition* const* RP2040ActionManager::get_all_action_definitions(uint8_t& count) const {
    count = RP2040_ACTION_COUNT;
    return RP2040_ACTION_DEFS;
}

#endif // PLATFORM_RP2040

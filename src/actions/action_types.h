#pragma once

#include <stdint.h>
#include <stdbool.h>

// Forward declaration for ParamSource (defined in param_mapping.h)
// This avoids circular dependency between action_types.h and param_mapping.h
enum ParamSource : uint8_t;

/**
 * Action Types
 *
 * Defines the types of actions that can be triggered by CAN messages.
 * Not all action types are available on all platforms - check
 * platform_capabilities to determine support.
 */
enum ActionType {
    ACTION_NONE = 0,           // No action (rule disabled)

    // Universal GPIO actions (all platforms)
    ACTION_GPIO_SET,           // Set pin HIGH
    ACTION_GPIO_CLEAR,         // Set pin LOW
    ACTION_GPIO_TOGGLE,        // Toggle pin state

    // CAN actions (all platforms)
    ACTION_CAN_SEND,           // Send CAN message once
    ACTION_CAN_SEND_PERIODIC,  // Send CAN message periodically

    // Platform-specific actions (require capability check)
    ACTION_PWM_SET,            // Set PWM duty cycle (SAMD51, ESP32)
    ACTION_NEOPIXEL_COLOR,     // Set NeoPixel RGB color (SAMD51)
    ACTION_NEOPIXEL_OFF,       // Turn off NeoPixel (SAMD51)
};

/**
 * Action Parameters
 *
 * Union to hold parameters for different action types.
 * Only the relevant field should be used based on ActionType.
 */
union ActionParams {
    // GPIO actions: ACTION_GPIO_SET, ACTION_GPIO_CLEAR, ACTION_GPIO_TOGGLE
    struct {
        uint8_t pin;           // GPIO pin number
    } gpio;

    // PWM actions: ACTION_PWM_SET
    struct {
        uint8_t pin;           // PWM pin number
        uint8_t duty;          // Duty cycle (0-255)
    } pwm;

    // NeoPixel actions: ACTION_NEOPIXEL_COLOR
    struct {
        uint8_t r;             // Red (0-255)
        uint8_t g;             // Green (0-255)
        uint8_t b;             // Blue (0-255)
        uint8_t brightness;    // Brightness (0-255), 0 = use default
    } neopixel;

    // CAN send actions: ACTION_CAN_SEND_PERIODIC
    struct {
        uint32_t can_id;       // CAN ID to send
        uint8_t data[8];       // Data bytes
        uint8_t length;        // Data length (0-8)
        uint32_t interval_ms;  // Interval in ms (for periodic)
    } can_send;

    // Raw bytes for storage/serialization
    uint8_t raw[12];
};

/**
 * Action Rule
 *
 * Defines a CAN message pattern and the action to execute when matched.
 * Rules are evaluated in order for each received CAN message.
 *
 * NEW in v2.0: Supports parameter extraction from CAN data bytes.
 * - param_source: PARAM_FROM_RULE (default, backward compatible) or PARAM_FROM_CAN_DATA
 * - param_data_offset: Byte offset in CAN data where parameter extraction begins
 */
struct ActionRule {
    // Rule management
    uint8_t id;                // Rule ID (1-255, 0 = unused slot)
    bool enabled;              // Rule is active

    // CAN message matching
    uint32_t can_id;           // CAN ID to match
    uint32_t can_id_mask;      // CAN ID mask (0xFFFFFFFF = exact match)
    uint8_t data[8];           // Data pattern to match
    uint8_t data_mask[8];      // Data mask (0xFF = must match, 0x00 = don't care)
    uint8_t data_length;       // Number of data bytes to match (0 = any length)

    // Action to execute
    ActionType action;         // Action type
    ActionParams params;       // Action-specific parameters (used when param_source = PARAM_FROM_RULE)

    // Periodic action state (for ACTION_CAN_SEND_PERIODIC)
    uint32_t last_execute_ms;  // Last execution timestamp (millis())
    uint32_t execute_count;    // Number of times executed

    // NEW: Parameter source control (v2.0)
    ParamSource param_source;  // Where to get action parameters from
    uint8_t param_data_offset; // CAN data byte offset for parameter extraction (default 0)
};

// Helper functions for action validation
const char* action_type_to_string(ActionType type);
bool is_action_supported(ActionType type);  // Check against platform capabilities

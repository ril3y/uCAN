#pragma once

#include <stdint.h>
#include <stdbool.h>

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
    ACTION_CAN_SEND,           // Send CAN message

    // Platform-specific actions (require capability check)
    ACTION_PWM_SET,            // Set PWM duty cycle (SAMD51, ESP32)
    ACTION_NEOPIXEL_COLOR,     // Set NeoPixel RGB color (SAMD51)
    ACTION_NEOPIXEL_OFF,       // Turn off NeoPixel (SAMD51)
    ACTION_ADC_READ,           // Read ADC value (all with ADC)
    ACTION_ADC_READ_SEND,      // Read ADC and send via CAN (all with ADC)
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

    // CAN send actions: ACTION_CAN_SEND
    struct {
        uint32_t can_id;       // CAN ID to send
        uint8_t data[8];       // Data bytes
        uint8_t length;        // Data length (0-8)
    } can_send;

    // ADC actions: ACTION_ADC_READ_SEND
    struct {
        uint8_t adc_pin;       // ADC pin to read
        uint32_t response_id;  // CAN ID for response
    } adc;

    // Raw bytes for storage/serialization
    uint8_t raw[12];
};

/**
 * Action Rule
 *
 * Defines a CAN message pattern and the action to execute when matched.
 * Rules are evaluated in order for each received CAN message.
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
    ActionParams params;       // Action-specific parameters
};

// Helper functions for action validation
const char* action_type_to_string(ActionType type);
bool is_action_supported(ActionType type);  // Check against platform capabilities

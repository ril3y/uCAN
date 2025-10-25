#pragma once

#include "action_types.h"
#include "../hal/can_interface.h"
#include "../hal/platform_config.h"
#include "../capabilities/board_capabilities.h"

// Platform-specific maximum rules (compile-time constants)
#ifdef PLATFORM_RP2040
    #define MAX_ACTION_RULES 16    // RP2040 limit
#elif defined(PLATFORM_SAMD51)
    #define MAX_ACTION_RULES 64    // SAMD51 limit
#elif defined(PLATFORM_ESP32)
    #define MAX_ACTION_RULES 32    // ESP32 limit
#else
    #define MAX_ACTION_RULES 8     // Default/minimal
#endif

/**
 * ActionManager
 *
 * Manages action rules and executes them when CAN messages match.
 * Provides methods to add, remove, list, and execute action rules.
 */
class ActionManager {
public:
    ActionManager();
    ~ActionManager();

    /**
     * Initialize the action manager
     * @param can_if Pointer to CAN interface for sending messages
     * @return true if successful
     */
    bool initialize(CANInterface* can_if);

    /**
     * Check if a CAN message matches any rules and execute actions
     * @param message The received CAN message
     * @return Number of rules that matched and executed
     */
    uint8_t check_and_execute(const CANMessage& message);

    /**
     * Add a new action rule
     * @param rule The rule to add
     * @return Rule ID if successful, 0 on failure
     */
    uint8_t add_rule(const ActionRule& rule);

    /**
     * Remove an action rule by ID
     * @param rule_id ID of rule to remove
     * @return true if removed
     */
    bool remove_rule(uint8_t rule_id);

    /**
     * Enable/disable a rule
     * @param rule_id ID of rule
     * @param enabled New enabled state
     * @return true if successful
     */
    bool set_rule_enabled(uint8_t rule_id, bool enabled);

    /**
     * Get a rule by ID
     * @param rule_id ID of rule
     * @return Pointer to rule, nullptr if not found
     */
    const ActionRule* get_rule(uint8_t rule_id) const;

    /**
     * Get number of active rules
     * @return Count of non-empty rules
     */
    uint8_t get_rule_count() const;

    /**
     * Clear all rules
     */
    void clear_all_rules();

    /**
     * List all rules (for debugging/query)
     * Calls callback for each active rule
     */
    void list_rules(void (*callback)(const ActionRule& rule)) const;

    /**
     * Save rules to persistent storage (EEPROM/Flash)
     * @return true if successful
     */
    bool save_rules();

    /**
     * Load rules from persistent storage
     * @return Number of rules loaded
     */
    uint8_t load_rules();

private:
    ActionRule rules_[MAX_ACTION_RULES];
    CANInterface* can_interface_;
    bool initialized_;
    uint8_t next_rule_id_;

    /**
     * Check if a CAN message matches a rule's pattern
     * @param message The CAN message to check
     * @param rule The rule to match against
     * @return true if message matches rule
     */
    bool matches_rule(const CANMessage& message, const ActionRule& rule) const;

    /**
     * Execute an action
     * @param rule The rule containing the action
     * @param message The triggering CAN message (for context)
     * @return true if action executed successfully
     */
    bool execute_action(const ActionRule& rule, const CANMessage& message);

    /**
     * Execute GPIO action
     */
    bool execute_gpio_action(ActionType type, uint8_t pin);

    /**
     * Execute PWM action
     */
    bool execute_pwm_action(uint8_t pin, uint8_t duty);

    /**
     * Execute NeoPixel action
     */
    bool execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness);

    /**
     * Execute CAN send action
     */
    bool execute_can_send_action(uint32_t can_id, const uint8_t* data, uint8_t length);

    /**
     * Execute ADC read and send action
     */
    bool execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id);

    /**
     * Find empty slot for new rule
     * @return Index of empty slot, -1 if full
     */
    int8_t find_empty_slot() const;

    /**
     * Find rule index by ID
     * @return Index of rule, -1 if not found
     */
    int8_t find_rule_index(uint8_t rule_id) const;
};

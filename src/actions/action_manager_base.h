#pragma once

#include "action_types.h"
#include "custom_command.h"
#include "param_mapping.h"
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
 * ActionManagerBase
 *
 * Abstract base class for managing action rules across multiple platforms.
 * Contains all platform-agnostic logic (parsing, storage, matching).
 * Platform-specific execution is delegated to derived classes.
 *
 * This design allows:
 * - Code reuse across platforms (rule matching, parsing, persistence)
 * - Platform isolation (NeoPixel code only in SAMD51ActionManager)
 * - Easy addition of new platforms
 */
class ActionManagerBase {
public:
    ActionManagerBase();
    virtual ~ActionManagerBase();

    /**
     * Initialize the action manager
     * @param can_if Pointer to CAN interface for sending messages
     * @return true if successful
     */
    virtual bool initialize(CANInterface* can_if);

    /**
     * Check if a CAN message matches any rules and execute actions
     * @param message The received CAN message
     * @return Number of rules that matched and executed
     */
    uint8_t check_and_execute(const CANMessage& message);

    /**
     * Update periodic actions - call this in main loop
     * Checks all periodic actions and executes if interval elapsed
     * @return Number of periodic actions executed
     */
    uint8_t update_periodic();

    /**
     * Add a new action rule
     * @param rule The rule to add
     * @return Rule ID if successful, 0 on failure
     */
    uint8_t add_rule(const ActionRule& rule);

    /**
     * Parse and add action rule from command string
     * Format: ID:CAN_ID:CAN_MASK:DATA:DATA_MASK:DATA_LEN:ACTION_TYPE:PARAMS
     * @param command_str Command string after "action:add:"
     * @return Rule ID if successful, 0 on failure
     */
    uint8_t parse_and_add_rule(const char* command_str);

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
     * Print all rules to Serial in protocol format
     * This is the implementation-specific formatting
     */
    void print_rules() const;

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

    /**
     * Get custom command registry for this platform
     * @return Reference to custom command registry
     */
    CustomCommandRegistry& get_custom_commands() { return custom_commands_; }

    /**
     * Send CAN message (public for use by custom commands)
     * Platform-agnostic helper that uses CANInterface
     * @param can_id CAN message ID
     * @param data Data bytes
     * @param length Data length (0-8)
     * @return true if message sent successfully
     */
    bool execute_can_send_action(uint32_t can_id, const uint8_t* data, uint8_t length);

    /**
     * Get action definition for specific action type
     * Platform must provide definitions for all supported actions
     * @param action The action type to query
     * @return Pointer to ActionDefinition, or nullptr if not supported
     */
    virtual const ActionDefinition* get_action_definition(ActionType action) const = 0;

    /**
     * Get all action definitions supported by this platform
     * @param count Output parameter - number of definitions returned
     * @return Array of ActionDefinition pointers
     */
    virtual const ActionDefinition* const* get_all_action_definitions(uint8_t& count) const = 0;

protected:
    // Platform-specific action execution (pure virtual methods)

    /**
     * Execute GPIO action (set/clear/toggle)
     * All platforms must implement basic GPIO
     */
    virtual bool execute_gpio_action(ActionType type, uint8_t pin) = 0;

    /**
     * Execute PWM action (set duty cycle)
     * Platform must return false if PWM not supported
     */
    virtual bool execute_pwm_action(uint8_t pin, uint8_t duty) = 0;

    /**
     * Execute NeoPixel action (set color/brightness)
     * Platform must return false if NeoPixel not available
     */
    virtual bool execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) = 0;

    /**
     * Execute ADC read and send action
     * Platform must return false if ADC not available
     */
    virtual bool execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id) = 0;

    /**
     * Save rules to platform-specific persistent storage
     * @return true if successful, false if not supported/failed
     */
    virtual bool save_rules_impl() = 0;

    /**
     * Load rules from platform-specific persistent storage
     * @return Number of rules loaded
     */
    virtual uint8_t load_rules_impl() = 0;

    /**
     * Register platform-specific custom commands
     * Called during initialize() to populate custom command registry
     */
    virtual void register_custom_commands() = 0;

    // Shared resources accessible to derived classes
    ActionRule rules_[MAX_ACTION_RULES];
    CANInterface* can_interface_;
    bool initialized_;
    uint8_t next_rule_id_;
    CustomCommandRegistry custom_commands_;

private:
    /**
     * Check if a CAN message matches a rule's pattern
     * @param message The CAN message to check
     * @param rule The rule to match against
     * @return true if message matches rule
     */
    bool matches_rule(const CANMessage& message, const ActionRule& rule) const;

    /**
     * Execute an action (dispatches to platform-specific implementations)
     * @param rule The rule containing the action
     * @param message The triggering CAN message (for context)
     * @return true if action executed successfully
     */
    bool execute_action(const ActionRule& rule, const CANMessage& message);

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

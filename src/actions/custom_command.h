#pragma once

#include <stdint.h>

/**
 * Parameter Types for UI generation
 */
enum ParamType {
    PARAM_UINT8,      // 0-255
    PARAM_UINT16,     // 0-65535
    PARAM_UINT32,     // 0-4294967295
    PARAM_INT8,       // -128 to 127
    PARAM_INT16,      // -32768 to 32767
    PARAM_INT32,      // -2147483648 to 2147483647
    PARAM_FLOAT,      // Floating point
    PARAM_BOOL,       // true/false
    PARAM_STRING,     // Text string
    PARAM_HEX,        // Hexadecimal value
    PARAM_ENUM        // Enumerated choice (defined by options)
};

/**
 * Parameter Definition
 *
 * Describes a single parameter for UI generation
 */
struct ParamDef {
    const char* name;           // Parameter name (e.g., "brightness")
    const char* description;    // Human-readable description
    ParamType type;             // Parameter type
    uint32_t min_value;         // Minimum value (for numeric types)
    uint32_t max_value;         // Maximum value (for numeric types)
    const char* options;        // Comma-separated options (for PARAM_ENUM)
    bool required;              // Is this parameter required?
};

/**
 * CustomCommand
 *
 * Abstract base class for platform-specific custom commands.
 * Allows platforms to register custom commands that the UI can discover.
 */
class CustomCommand {
public:
    virtual ~CustomCommand() {}

    /**
     * Get command name (e.g., "neopixel", "dac_set")
     * @return Command name string
     */
    virtual const char* get_name() const = 0;

    /**
     * Get command description
     * @return Human-readable description
     */
    virtual const char* get_description() const = 0;

    /**
     * Get command category (e.g., "GPIO", "Display", "Communication")
     * @return Category string
     */
    virtual const char* get_category() const = 0;

    /**
     * Get parameter definitions
     * @param count Output: number of parameters
     * @return Array of parameter definitions
     */
    virtual const ParamDef* get_parameters(uint8_t& count) const = 0;

    /**
     * Execute the command
     * @param params Parameter string (everything after "command_name:")
     * @return true if successful
     */
    virtual bool execute(const char* params) = 0;
};

/**
 * CustomCommandRegistry
 *
 * Manages platform-specific custom commands.
 * Allows UI to discover available commands.
 */
class CustomCommandRegistry {
public:
    static const uint8_t MAX_CUSTOM_COMMANDS = 16;

    CustomCommandRegistry();

    /**
     * Register a custom command
     * @param command Pointer to command instance
     * @return true if registered successfully
     */
    bool register_command(CustomCommand* command);

    /**
     * Execute a custom command
     * @param name Command name
     * @param params Parameters string
     * @return true if command found and executed
     */
    bool execute_command(const char* name, const char* params);

    /**
     * Get number of registered commands
     */
    uint8_t get_command_count() const;

    /**
     * Get command by index
     * @param index Command index (0 to count-1)
     * @return Pointer to command, or nullptr if invalid index
     */
    CustomCommand* get_command(uint8_t index) const;

    /**
     * Print all registered commands in JSON format for UI
     * Format: CUSTOMCMD;{JSON}
     * JSON contains: name, description, category, parameters[]
     */
    void print_commands() const;

    /**
     * Print a single command's details in JSON format
     * @param command Command to print
     */
    void print_command_json(const CustomCommand* command) const;

private:
    CustomCommand* commands_[MAX_CUSTOM_COMMANDS];
    uint8_t command_count_;
};

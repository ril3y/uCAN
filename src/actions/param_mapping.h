#pragma once

#include "action_types.h"
#include "custom_command.h"
#include <stdint.h>

/**
 * Parameter Source
 *
 * Defines where action parameters are sourced from.
 */
enum ParamSource : uint8_t {
    PARAM_FROM_RULE = 0,     // Use fixed parameters stored in rule (default, backward compatible)
    PARAM_FROM_CAN_DATA = 1  // Extract parameters from received CAN data bytes
};

/**
 * Parameter Mapping
 *
 * Defines how to extract a single parameter from CAN data bytes.
 * This is a compile-time constant stored in Flash (PROGMEM).
 *
 * Memory: Lives in Flash, not RAM.
 */
struct ParamMapping {
    uint8_t data_byte_index;    // Which CAN data byte (0-7)
    uint8_t bit_offset;         // Bit offset within byte (0-7, for bit-packed data)
    uint8_t bit_length;         // Number of bits to extract (1-8, default 8 for full byte)
    ParamType type;             // Parameter type (uint8, uint16, etc.)
    uint32_t min_value;         // Minimum valid value (for validation/clamping)
    uint32_t max_value;         // Maximum valid value (for validation/clamping)
    const char* name;           // Parameter name (for UI discovery)
    const char* role;           // Parameter role: "action_param", "trigger_param", "output_param" (v2.0)
};

/**
 * Action Definition
 *
 * Defines an action type and how to extract its parameters from CAN data.
 * This is a compile-time constant stored in Flash (PROGMEM).
 *
 * Memory: Lives in Flash, not RAM.
 */
struct ActionDefinition {
    ActionType action;              // Action type enum
    const char* name;               // Action name (e.g., "NEOPIXEL", "PWM_SET")
    const char* description;        // Human-readable description
    const char* category;           // Category (e.g., "GPIO", "Display", "Communication")
    const char* trigger_type;       // Trigger type: "can_msg", "periodic", "gpio", "manual" (v2.0)
    uint8_t param_count;            // Number of parameters
    const ParamMapping* param_map;  // Parameter mapping array (Flash pointer)
};

// ============================================================================
// Parameter Extraction Functions (Inline for Performance)
// ============================================================================

/**
 * Extract uint8 parameter from CAN data
 *
 * Optimized for speed - inlined, minimal branches.
 * Supports bit-level extraction for packed data.
 *
 * @param can_data CAN message data array (8 bytes)
 * @param mapping Parameter mapping definition
 * @return Extracted uint8 value (clamped to min/max)
 */
inline uint8_t extract_uint8(const uint8_t* can_data, const ParamMapping& mapping) {
    // Bounds check on byte index
    if (mapping.data_byte_index > 7) {
        return 0;
    }

    uint8_t raw_value = can_data[mapping.data_byte_index];

    // If bit_length < 8, extract specific bits
    if (mapping.bit_length < 8) {
        uint8_t mask = (1 << mapping.bit_length) - 1;
        raw_value = (raw_value >> mapping.bit_offset) & mask;
    }

    // Clamp to min/max range
    if (raw_value < mapping.min_value) raw_value = (uint8_t)mapping.min_value;
    if (raw_value > mapping.max_value) raw_value = (uint8_t)mapping.max_value;

    return raw_value;
}

/**
 * Extract uint16 parameter from CAN data (little-endian)
 *
 * Reads 2 consecutive bytes starting at data_byte_index.
 *
 * @param can_data CAN message data array (8 bytes)
 * @param mapping Parameter mapping definition
 * @return Extracted uint16 value (clamped to min/max)
 */
inline uint16_t extract_uint16(const uint8_t* can_data, const ParamMapping& mapping) {
    // Bounds check
    if (mapping.data_byte_index > 6) {  // Need 2 bytes
        return 0;
    }

    // Little-endian: low byte first
    uint16_t value = can_data[mapping.data_byte_index] |
                     (can_data[mapping.data_byte_index + 1] << 8);

    // Clamp to min/max range
    if (value < mapping.min_value) value = (uint16_t)mapping.min_value;
    if (value > mapping.max_value) value = (uint16_t)mapping.max_value;

    return value;
}

/**
 * Extract int8 parameter from CAN data (signed)
 *
 * @param can_data CAN message data array (8 bytes)
 * @param mapping Parameter mapping definition
 * @return Extracted int8 value (clamped to min/max)
 */
inline int8_t extract_int8(const uint8_t* can_data, const ParamMapping& mapping) {
    if (mapping.data_byte_index > 7) {
        return 0;
    }

    int8_t value = (int8_t)can_data[mapping.data_byte_index];

    // Clamp to min/max range (interpret as signed)
    int8_t min = (int8_t)mapping.min_value;
    int8_t max = (int8_t)mapping.max_value;
    if (value < min) value = min;
    if (value > max) value = max;

    return value;
}

/**
 * Extract int16 parameter from CAN data (little-endian, signed)
 *
 * @param can_data CAN message data array (8 bytes)
 * @param mapping Parameter mapping definition
 * @return Extracted int16 value (clamped to min/max)
 */
inline int16_t extract_int16(const uint8_t* can_data, const ParamMapping& mapping) {
    if (mapping.data_byte_index > 6) {
        return 0;
    }

    int16_t value = (int16_t)(can_data[mapping.data_byte_index] |
                              (can_data[mapping.data_byte_index + 1] << 8));

    // Clamp to min/max range
    int16_t min = (int16_t)mapping.min_value;
    int16_t max = (int16_t)mapping.max_value;
    if (value < min) value = min;
    if (value > max) value = max;

    return value;
}

/**
 * Extract uint32 parameter from CAN data (little-endian)
 *
 * Reads 4 consecutive bytes starting at data_byte_index.
 *
 * @param can_data CAN message data array (8 bytes)
 * @param mapping Parameter mapping definition
 * @return Extracted uint32 value (clamped to min/max)
 */
inline uint32_t extract_uint32(const uint8_t* can_data, const ParamMapping& mapping) {
    // Bounds check
    if (mapping.data_byte_index > 4) {  // Need 4 bytes
        return 0;
    }

    uint32_t value = can_data[mapping.data_byte_index] |
                     (can_data[mapping.data_byte_index + 1] << 8) |
                     (can_data[mapping.data_byte_index + 2] << 16) |
                     (can_data[mapping.data_byte_index + 3] << 24);

    // Clamp to min/max range
    if (value < mapping.min_value) value = mapping.min_value;
    if (value > mapping.max_value) value = mapping.max_value;

    return value;
}

/**
 * Extract float parameter from CAN data (IEEE 754, little-endian)
 *
 * Reads 4 consecutive bytes as a 32-bit float.
 * NOTE: No clamping applied to float values.
 *
 * @param can_data CAN message data array (8 bytes)
 * @param mapping Parameter mapping definition
 * @return Extracted float value
 */
inline float extract_float(const uint8_t* can_data, const ParamMapping& mapping) {
    if (mapping.data_byte_index > 4) {
        return 0.0f;
    }

    // Reinterpret 4 bytes as float (union for type punning)
    union {
        uint32_t u;
        float f;
    } converter;

    converter.u = can_data[mapping.data_byte_index] |
                  (can_data[mapping.data_byte_index + 1] << 8) |
                  (can_data[mapping.data_byte_index + 2] << 16) |
                  (can_data[mapping.data_byte_index + 3] << 24);

    return converter.f;
}

/**
 * Extract boolean parameter from CAN data (single bit)
 *
 * @param can_data CAN message data array (8 bytes)
 * @param mapping Parameter mapping definition (bit_offset specifies which bit)
 * @return true if bit is set, false otherwise
 */
inline bool extract_bool(const uint8_t* can_data, const ParamMapping& mapping) {
    if (mapping.data_byte_index > 7) {
        return false;
    }

    uint8_t byte_value = can_data[mapping.data_byte_index];
    uint8_t bit_mask = 1 << mapping.bit_offset;

    return (byte_value & bit_mask) != 0;
}

// ============================================================================
// Action Definition Registry
// ============================================================================

/**
 * Get action definition by action type
 *
 * Platform-specific implementations provide this function to return
 * Flash-based action definitions.
 *
 * @param action Action type to look up
 * @return Pointer to action definition (Flash), or nullptr if not found
 */
const ActionDefinition* get_action_definition(ActionType action);

/**
 * Get all action definitions for this platform
 *
 * @param count Output: Number of action definitions returned
 * @return Pointer to array of ActionDefinition pointers (Flash)
 */
const ActionDefinition* const* get_all_action_definitions(uint8_t& count);

/**
 * Print action definition in compact JSON format
 *
 * Format: ACTIONDEF;{"i":1,"n":"NAME","d":"DESC","p":[...]}
 *
 * @param def Action definition to print
 */
void print_action_definition_json(const ActionDefinition* def);

/**
 * Print all action definitions for this platform
 *
 * Outputs multiple ACTIONDEF lines, one per action.
 */
void print_all_action_definitions();

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Convert ParamType enum to string
 *
 * @param type Parameter type
 * @return String representation (e.g., "uint8", "uint16")
 */
const char* param_type_to_string(ParamType type);

/**
 * Convert ParamSource enum to string
 *
 * @param source Parameter source
 * @return String representation (e.g., "fixed", "candata")
 */
const char* param_source_to_string(ParamSource source);

/**
 * Parse ParamSource from string
 *
 * @param str String to parse (e.g., "fixed", "candata")
 * @return ParamSource enum, or PARAM_FROM_RULE if invalid
 */
ParamSource parse_param_source(const char* str);

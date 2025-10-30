#include "param_mapping.h"
#include <Arduino.h>
#include <string.h>

// ============================================================================
// Helper Functions Implementation
// ============================================================================

const char* param_type_to_string(ParamType type) {
    switch (type) {
        case PARAM_UINT8:   return "uint8";
        case PARAM_UINT16:  return "uint16";
        case PARAM_UINT32:  return "uint32";
        case PARAM_INT8:    return "int8";
        case PARAM_INT16:   return "int16";
        case PARAM_INT32:   return "int32";
        case PARAM_FLOAT:   return "float";
        case PARAM_BOOL:    return "bool";
        case PARAM_STRING:  return "string";
        case PARAM_HEX:     return "hex";
        case PARAM_ENUM:    return "enum";
        default:            return "unknown";
    }
}

const char* param_source_to_string(ParamSource source) {
    switch (source) {
        case PARAM_FROM_RULE:     return "fixed";
        case PARAM_FROM_CAN_DATA: return "candata";
        default:                  return "unknown";
    }
}

ParamSource parse_param_source(const char* str) {
    if (!str) {
        return PARAM_FROM_RULE;
    }

    if (strcmp(str, "candata") == 0 || strcmp(str, "can") == 0) {
        return PARAM_FROM_CAN_DATA;
    }

    if (strcmp(str, "fixed") == 0 || strcmp(str, "rule") == 0) {
        return PARAM_FROM_RULE;
    }

    // Default to fixed parameters for backward compatibility
    return PARAM_FROM_RULE;
}

// ============================================================================
// JSON Serialization
// ============================================================================

void print_action_definition_json(const ActionDefinition* def) {
    if (!def) {
        return;
    }

    // Start output: ACTIONDEF;{JSON}
    Serial.print("ACTIONDEF;{");

    // Action ID (enum value)
    Serial.print("\"i\":");
    Serial.print((int)def->action);
    Serial.print(",");

    // Action name
    Serial.print("\"n\":\"");
    Serial.print(def->name);
    Serial.print("\",");

    // Description
    Serial.print("\"d\":\"");
    Serial.print(def->description);
    Serial.print("\",");

    // Category
    Serial.print("\"c\":\"");
    Serial.print(def->category);
    Serial.print("\",");

    // Trigger type (v2.0)
    Serial.print("\"trig\":\"");
    Serial.print(def->trigger_type);
    Serial.print("\",");

    // Parameters array
    Serial.print("\"p\":[");

    for (uint8_t i = 0; i < def->param_count; i++) {
        if (i > 0) {
            Serial.print(",");
        }

        const ParamMapping& param = def->param_map[i];

        Serial.print("{");

        // Parameter name
        Serial.print("\"n\":\"");
        Serial.print(param.name);
        Serial.print("\",");

        // Parameter type (numeric code)
        Serial.print("\"t\":");
        Serial.print((int)param.type);
        Serial.print(",");

        // Data byte index
        Serial.print("\"b\":");
        Serial.print(param.data_byte_index);
        Serial.print(",");

        // Bit offset
        Serial.print("\"o\":");
        Serial.print(param.bit_offset);
        Serial.print(",");

        // Bit length
        Serial.print("\"l\":");
        Serial.print(param.bit_length);
        Serial.print(",");

        // Range (min-max)
        Serial.print("\"r\":\"");
        Serial.print(param.min_value);
        Serial.print("-");
        Serial.print(param.max_value);
        Serial.print("\",");

        // Parameter role (v2.0)
        Serial.print("\"role\":\"");
        Serial.print(param.role);
        Serial.print("\"");

        // Label (optional, for UI)
        if (param.label != nullptr) {
            Serial.print(",\"label\":\"");
            Serial.print(param.label);
            Serial.print("\"");
        }

        // Hint (optional, for UI)
        if (param.hint != nullptr) {
            Serial.print(",\"hint\":\"");
            Serial.print(param.hint);
            Serial.print("\"");
        }

        Serial.print("}");
    }

    Serial.print("]");

    Serial.println("}");
}

// ============================================================================
// NOTE: Action definition functions removed
// ============================================================================
// These are now pure virtual methods in ActionManagerBase:
//   - get_action_definition(ActionType action) const = 0
//   - get_all_action_definitions(uint8_t& count) const = 0
//
// Each platform implements these methods in their action manager class:
//   - RP2040ActionManager (rp2040_action_defs.cpp)
//   - SAMD51ActionManager (samd51_action_defs.cpp)
// ============================================================================

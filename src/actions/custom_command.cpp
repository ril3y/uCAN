#include "custom_command.h"
#include "param_mapping.h"
#include <Arduino.h>
#include <string.h>

CustomCommandRegistry::CustomCommandRegistry() : command_count_(0) {
    memset(commands_, 0, sizeof(commands_));
}

bool CustomCommandRegistry::register_command(CustomCommand* command) {
    if (!command || command_count_ >= MAX_CUSTOM_COMMANDS) {
        return false;
    }

    commands_[command_count_++] = command;
    return true;
}

bool CustomCommandRegistry::execute_command(const char* name, const char* params) {
    if (!name) {
        return false;
    }

    for (uint8_t i = 0; i < command_count_; i++) {
        if (strcmp(commands_[i]->get_name(), name) == 0) {
            return commands_[i]->execute(params);
        }
    }

    return false;  // Command not found
}

uint8_t CustomCommandRegistry::get_command_count() const {
    return command_count_;
}

CustomCommand* CustomCommandRegistry::get_command(uint8_t index) const {
    if (index >= command_count_) {
        return nullptr;
    }
    return commands_[index];
}

void CustomCommandRegistry::print_command_json(const CustomCommand* command) const {
    if (!command) return;

    Serial.print("CUSTOMCMD;{");
    Serial.print("\"name\":\"");
    Serial.print(command->get_name());
    Serial.print("\",\"description\":\"");
    Serial.print(command->get_description());
    Serial.print("\",\"category\":\"");
    Serial.print(command->get_category());
    Serial.print("\",\"parameters\":[");

    uint8_t param_count = 0;
    const ParamDef* params = command->get_parameters(param_count);

    for (uint8_t i = 0; i < param_count; i++) {
        if (i > 0) Serial.print(",");
        Serial.print("{\"name\":\"");
        Serial.print(params[i].name);
        Serial.print("\",\"description\":\"");
        Serial.print(params[i].description);
        Serial.print("\",\"type\":\"");
        Serial.print(param_type_to_string(params[i].type));
        Serial.print("\",\"required\":");
        Serial.print(params[i].required ? "true" : "false");

        // Add min/max for numeric types
        if (params[i].type <= PARAM_INT32) {
            Serial.print(",\"min\":");
            Serial.print(params[i].min_value);
            Serial.print(",\"max\":");
            Serial.print(params[i].max_value);
        }

        // Add options for enum type
        if (params[i].type == PARAM_ENUM && params[i].options) {
            Serial.print(",\"options\":\"");
            Serial.print(params[i].options);
            Serial.print("\"");
        }

        Serial.print("}");
    }

    Serial.println("]}");
}

void CustomCommandRegistry::print_commands() const {
    for (uint8_t i = 0; i < command_count_; i++) {
        print_command_json(commands_[i]);
    }
}

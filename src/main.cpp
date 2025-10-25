#include <Arduino.h>
#include "hal/can_factory.h"
#include "hal/platform_config.h"
#include "capabilities/board_capabilities.h"
#include "actions/action_manager.h"

// Global CAN interface instance
CANInterface* can_interface = nullptr;

// Global action manager instance
ActionManager action_manager;

// Command buffer for serial input
static char command_buffer[256];
static uint8_t command_index = 0;

// Statistics reporting
static unsigned long last_stats_time = 0;
static const unsigned long STATS_INTERVAL = 5000;  // 5 seconds

// Heartbeat functionality
#ifdef ENABLE_HEARTBEAT
static unsigned long last_heartbeat_time = 0;
static const unsigned long HEARTBEAT_INTERVAL = 1000;  // 1 second
static uint32_t heartbeat_counter = 0;
void send_heartbeat();
#endif

// Forward declarations
void process_serial_input();
void handle_command(const char* command);
void handle_send_command(const char* params);
void handle_config_command(const char* params);
void handle_get_command(const char* params);
void handle_control_command(const char* params);
void handle_action_command(const char* params);
void send_status(const char* type, const char* message, const char* details = nullptr);
void send_error(CANError error, const char* description);
void send_stats();
void process_can_messages();

void setup() {
  Serial.begin(DEFAULT_SERIAL_BAUD);
  pinMode(LED_BUILTIN, OUTPUT);
  
  // Wait for serial port to be ready (up to 3 seconds)
  unsigned long start_time = millis();
  while (!Serial && (millis() - start_time) < 3000) {
    delay(10);
  }
  
  // Create platform-specific CAN interface
  can_interface = CANFactory::create();
  if (!can_interface) {
    send_status("ERROR", "Failed to create CAN interface");
    while (1) delay(1000);  // Halt on error
  }
  
  // Initialize CAN with default configuration
  CANConfig config = CANFactory::get_default_config();
  
  if (can_interface->initialize(config)) {
    char details[128];
    snprintf(details, sizeof(details), "%s @ %lukbps", 
             can_interface->get_version(), config.bitrate/1000);
    send_status("CONNECTED", can_interface->get_platform_name(), details);
  } else {
    CANError error = can_interface->get_error_status();
    send_error(error, "CAN initialization failed");
    while (1) delay(1000);  // Halt on error
  }

  // Initialize action manager
  if (action_manager.initialize(can_interface)) {
    send_status("INFO", "Action manager initialized");
  } else {
    send_status("WARNING", "Action manager initialization failed");
  }

  last_stats_time = millis();
}

void loop() {
  // Blink LED to show we're alive
  static unsigned long last_blink = 0;
  if (millis() - last_blink > 1000) {
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    last_blink = millis();
  }
  
  // Process CAN messages
  process_can_messages();
  
  // Handle serial commands
  process_serial_input();
  
  // Send periodic statistics
  if (millis() - last_stats_time >= STATS_INTERVAL) {
    send_stats();
    last_stats_time = millis();
  }

  // Send periodic heartbeat (if enabled)
#ifdef ENABLE_HEARTBEAT
  if (millis() - last_heartbeat_time >= HEARTBEAT_INTERVAL) {
    send_heartbeat();
    last_heartbeat_time = millis();
  }
#endif
  
  // Check for CAN errors
  CANError error = can_interface->get_error_status();
  if (error != CAN_ERROR_NONE) {
    send_error(error, "CAN error detected");
    can_interface->clear_errors();
  }
}

void process_can_messages() {
  if (!can_interface || !can_interface->is_ready()) {
    return;
  }
  
  CANMessage message;
  while (can_interface->receive_message(message)) {
    // Send CAN_RX message in protocol format
    Serial.print("CAN_RX;0x");
    Serial.print(message.id, HEX);
    Serial.print(";");
    
    // Format data bytes
    for (uint8_t i = 0; i < message.length; i++) {
      if (i > 0) Serial.print(",");
      if (message.data[i] < 0x10) Serial.print("0");
      Serial.print(message.data[i], HEX);
    }
    
    // Add timestamp if available
    if (message.timestamp > 0) {
      Serial.print(";");
      Serial.print(message.timestamp);
    }

    Serial.println();

    // Check and execute any matching action rules
    action_manager.check_and_execute(message);
  }
}

void process_serial_input() {
  while (Serial.available()) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {
      if (command_index > 0) {
        command_buffer[command_index] = '\0';
        handle_command(command_buffer);
        command_index = 0;
      }
    } else if (command_index < sizeof(command_buffer) - 1) {
      command_buffer[command_index++] = c;
    }
  }
}

void handle_command(const char* command) {
  if (strncmp(command, "send:", 5) == 0) {
    handle_send_command(command + 5);
  } else if (strncmp(command, "config:", 7) == 0) {
    handle_config_command(command + 7);
  } else if (strncmp(command, "get:", 4) == 0) {
    handle_get_command(command + 4);
  } else if (strncmp(command, "control:", 8) == 0) {
    handle_control_command(command + 8);
  } else if (strncmp(command, "action:", 7) == 0) {
    handle_action_command(command + 7);
  }
  // Silently ignore unknown commands for protocol compatibility
}

void handle_send_command(const char* params) {
  // Parse format: ID:DATA
  char* colon_pos = strchr(params, ':');
  if (!colon_pos) {
    return;
  }
  
  *colon_pos = '\0';
  const char* id_str = params;
  const char* data_str = colon_pos + 1;
  
  // Parse CAN ID
  uint32_t can_id = strtoul(id_str, NULL, 16);
  
  CANMessage message;
  message.id = can_id;
  message.extended = (can_id > 0x7FF);
  message.remote = false;
  message.length = 0;
  message.timestamp = millis();
  
  // Parse data bytes (comma-separated hex)
  char data_copy[strlen(data_str) + 1];
  strcpy(data_copy, data_str);
  
  char* token = strtok(data_copy, ",");
  while (token != NULL && message.length < CAN_MAX_DATA_LENGTH) {
    message.data[message.length] = strtoul(token, NULL, 16);
    message.length++;
    token = strtok(NULL, ",");
  }
  
  // Send message
  if (can_interface->send_message(message)) {
    // Echo back as CAN_TX
    Serial.print("CAN_TX;0x");
    Serial.print(message.id, HEX);
    Serial.print(";");
    
    for (uint8_t i = 0; i < message.length; i++) {
      if (i > 0) Serial.print(",");
      if (message.data[i] < 0x10) Serial.print("0");
      Serial.print(message.data[i], HEX);
    }
    
    Serial.print(";");
    Serial.println(message.timestamp);
  } else {
    send_error(CAN_ERROR_OTHER, "Failed to send message");
  }
}

void handle_config_command(const char* params) {
  // Parse format: PARAMETER:VALUE
  char* colon_pos = strchr(params, ':');
  if (!colon_pos) {
    return;
  }
  
  *colon_pos = '\0';
  const char* param = params;
  const char* value = colon_pos + 1;
  
  if (strcmp(param, "baudrate") == 0) {
    uint32_t baudrate = atol(value);
    
    // Reinitialize CAN with new baudrate
    can_interface->deinitialize();
    CANConfig config = CANFactory::get_default_config();
    config.bitrate = baudrate;
    
    if (can_interface->initialize(config)) {
      send_status("CONFIG", "Baudrate changed", value);
    } else {
      send_error(CAN_ERROR_CONFIG_ERROR, "Failed to change baudrate");
    }
  } else if (strcmp(param, "filter") == 0) {
    uint32_t filter = strtoul(value, NULL, 16);
    can_interface->set_filter(filter, 0x7FF);  // Standard ID mask
    send_status("CONFIG", "Filter set", value);
  } else if (strcmp(param, "visual") == 0) {
    // Handle visual feedback configuration
    if (strcmp(value, "on") == 0) {
      can_interface->set_visual_feedback_enabled(true);
      send_status("CONFIG", "Visual feedback enabled");
    } else if (strcmp(value, "off") == 0) {
      can_interface->set_visual_feedback_enabled(false);
      send_status("CONFIG", "Visual feedback disabled");
    } else {
      send_error(CAN_ERROR_CONFIG_ERROR, "Invalid visual config (use 'on' or 'off')");
    }
  }
}

void handle_get_command(const char* param) {
  if (strcmp(param, "status") == 0) {
    CANStatistics stats;
    can_interface->get_statistics(stats);
    
    char details[64];
    snprintf(details, sizeof(details), "RX:%lu TX:%lu ERR:%lu", 
             stats.rx_count, stats.tx_count, stats.error_count);
    send_status("INFO", "Running", details);
    
  } else if (strcmp(param, "version") == 0) {
    char version_info[256];
    snprintf(version_info, sizeof(version_info), 
             "Platform: %s, Version: %s, Protocol: %s", 
             can_interface->get_platform_name(),
             can_interface->get_version(),
             PROTOCOL_VERSION);
    send_status("INFO", version_info);
    
  } else if (strcmp(param, "stats") == 0) {
    send_stats();
  } else if (strcmp(param, "visual") == 0) {
    // Get visual feedback status
    bool enabled = can_interface->is_visual_feedback_enabled();
    const char* status = enabled ? "enabled" : "disabled";
    send_status("INFO", "Visual feedback", status);

  } else if (strcmp(param, "capabilities") == 0) {
    // Send platform capabilities as JSON
    send_capabilities_json();

  } else if (strcmp(param, "pins") == 0) {
    // Send available pin information
    send_pin_info();

  } else if (strcmp(param, "actions") == 0) {
    // Send supported action types
    send_supported_actions();
  }
}

void handle_control_command(const char* action) {
  if (strcmp(action, "reset") == 0) {
    send_status("INFO", "Resetting device");
    delay(100);
    // Platform-specific reset
    #ifdef PLATFORM_RP2040
      watchdog_reboot(0, 0, 0);
    #else
      NVIC_SystemReset();
    #endif
    
  } else if (strcmp(action, "clear") == 0) {
    can_interface->reset_statistics();
    send_status("INFO", "Statistics cleared");
  }
}

void send_status(const char* type, const char* message, const char* details) {
  Serial.print("STATUS;");
  Serial.print(type);
  Serial.print(";");
  Serial.print(message);
  if (details) {
    Serial.print(";");
    Serial.print(details);
  }
  Serial.println();
}

void send_error(CANError error, const char* description) {
  Serial.print("CAN_ERR;0x");
  if (error < 0x10) Serial.print("0");
  Serial.print(error, HEX);
  Serial.print(";");
  Serial.println(description);
}

void send_stats() {
  CANStatistics stats;
  can_interface->get_statistics(stats);

  Serial.print("STATS;");
  Serial.print(stats.rx_count);
  Serial.print(";");
  Serial.print(stats.tx_count);
  Serial.print(";");
  Serial.print(stats.error_count);
  Serial.print(";");
  Serial.print(stats.bus_load_percent);
  Serial.print(";");
  Serial.println(millis());
}

#ifdef ENABLE_HEARTBEAT
void send_heartbeat() {
  if (!can_interface || !can_interface->is_ready()) {
    return;
  }

  // Create heartbeat CAN message (ID 0x100)
  CANMessage message;
  message.id = 0x100;
  message.extended = false;
  message.remote = false;
  message.length = 8;
  message.timestamp = millis();

  // Pack heartbeat counter (4 bytes) and uptime (4 bytes)
  message.data[0] = (heartbeat_counter >> 24) & 0xFF;
  message.data[1] = (heartbeat_counter >> 16) & 0xFF;
  message.data[2] = (heartbeat_counter >> 8) & 0xFF;
  message.data[3] = heartbeat_counter & 0xFF;

  uint32_t uptime_sec = millis() / 1000;
  message.data[4] = (uptime_sec >> 24) & 0xFF;
  message.data[5] = (uptime_sec >> 16) & 0xFF;
  message.data[6] = (uptime_sec >> 8) & 0xFF;
  message.data[7] = uptime_sec & 0xFF;

  if (can_interface->send_message(message)) {
    heartbeat_counter++;

    // Echo to serial
    Serial.print("CAN_TX;0x");
    Serial.print(message.id, HEX);
    Serial.print(";");

    for (uint8_t i = 0; i < message.length; i++) {
      if (i > 0) Serial.print(",");
      if (message.data[i] < 0x10) Serial.print("0");
      Serial.print(message.data[i], HEX);
    }

    Serial.print(";");
    Serial.println(message.timestamp);
  }
}
#endif

// ============================================================================
// Action Command Handler
// ============================================================================

void handle_action_command(const char* params) {
  // Parse action subcommands
  if (strncmp(params, "add:", 4) == 0) {
    // Parse: add:ID:CAN_ID:CAN_MASK:DATA:DATA_MASK:ACTION_TYPE:PARAMS
    // Simplified for now: add:ID:CAN_ID:::ACTION_TYPE:PARAM
    char params_copy[128];
    strncpy(params_copy, params + 4, sizeof(params_copy) - 1);
    params_copy[sizeof(params_copy) - 1] = '\0';

    // Simple parser for: ID:CAN_ID:::GPIO_TOGGLE:PIN
    char* tokens[8];
    uint8_t token_count = 0;
    char* ptr = params_copy;

    while (token_count < 8 && *ptr) {
      tokens[token_count++] = ptr;
      char* next = strchr(ptr, ':');
      if (next) {
        *next = '\0';
        ptr = next + 1;
      } else {
        break;
      }
    }

    if (token_count < 4) {
      send_status("ERROR", "Invalid action format");
      return;
    }

    ActionRule rule;
    memset(&rule, 0, sizeof(rule));

    rule.id = atoi(tokens[0]);
    rule.can_id = strtoul(tokens[1], nullptr, 16);
    rule.can_id_mask = 0x7FF;  // Default standard ID mask
    rule.enabled = true;

    // Parse action type
    if (token_count >= 4) {
      if (strcmp(tokens[3], "GPIO_TOGGLE") == 0 && token_count >= 5) {
        rule.action = ACTION_GPIO_TOGGLE;
        rule.params.gpio.pin = atoi(tokens[4]);
      } else if (strcmp(tokens[3], "GPIO_SET") == 0 && token_count >= 5) {
        rule.action = ACTION_GPIO_SET;
        rule.params.gpio.pin = atoi(tokens[4]);
      } else if (strcmp(tokens[3], "GPIO_CLEAR") == 0 && token_count >= 5) {
        rule.action = ACTION_GPIO_CLEAR;
        rule.params.gpio.pin = atoi(tokens[4]);
      } else {
        send_status("ERROR", "Unsupported action type");
        return;
      }
    }

    uint8_t added_id = action_manager.add_rule(rule);
    if (added_id > 0) {
      char details[32];
      snprintf(details, sizeof(details), "Rule %d added", added_id);
      send_status("INFO", "Action added", details);
    } else {
      send_status("ERROR", "Failed to add action");
    }

  } else if (strncmp(params, "remove:", 7) == 0) {
    uint8_t rule_id = atoi(params + 7);
    if (action_manager.remove_rule(rule_id)) {
      send_status("INFO", "Action removed");
    } else {
      send_status("ERROR", "Action not found");
    }

  } else if (strcmp(params, "list") == 0) {
    uint8_t count = action_manager.get_rule_count();
    char details[32];
    snprintf(details, sizeof(details), "%d rules active", count);
    send_status("INFO", "Actions", details);

    // List each rule
    action_manager.list_rules([](const ActionRule& rule) {
      Serial.print("ACTION;");
      Serial.print(rule.id);
      Serial.print(";0x");
      Serial.print(rule.id, HEX);
      Serial.print(";");
      Serial.print(action_type_to_string(rule.action));
      Serial.print(";");
      Serial.print(rule.enabled ? "EN" : "DIS");
      Serial.println();
    });

  } else if (strncmp(params, "enable:", 7) == 0) {
    uint8_t rule_id = atoi(params + 7);
    if (action_manager.set_rule_enabled(rule_id, true)) {
      send_status("INFO", "Action enabled");
    } else {
      send_status("ERROR", "Action not found");
    }

  } else if (strncmp(params, "disable:", 8) == 0) {
    uint8_t rule_id = atoi(params + 8);
    if (action_manager.set_rule_enabled(rule_id, false)) {
      send_status("INFO", "Action disabled");
    } else {
      send_status("ERROR", "Action not found");
    }

  } else if (strcmp(params, "clear") == 0) {
    action_manager.clear_all_rules();
    send_status("INFO", "All actions cleared");
  }
}
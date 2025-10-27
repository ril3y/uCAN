#include <Arduino.h>
#include "hal/can_factory.h"
#include "hal/platform_config.h"
#include "capabilities/board_capabilities.h"
#include "actions/action_manager_factory.h"

// Global CAN interface instance
CANInterface* can_interface = nullptr;

// Global action manager instance (polymorphic pointer to platform-specific implementation)
ActionManagerBase* action_manager = nullptr;

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
void handle_set_command(const char* params);
void handle_control_command(const char* params);
void handle_action_command(const char* params);
void handle_custom_command(const char* params);
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

  // Create platform-specific action manager
  action_manager = ActionManagerFactory::create();
  if (!action_manager) {
    send_status("ERROR", "Failed to create action manager");
    while (1) delay(1000);  // Halt on error
  }

  // Initialize action manager
  if (action_manager->initialize(can_interface)) {
    char details[128];
    snprintf(details, sizeof(details), "%s action manager", ActionManagerFactory::get_platform_name());
    send_status("INFO", "Action manager initialized", details);

    // Try to load rules from persistent storage first
    uint8_t loaded = action_manager->load_rules();
    if (loaded > 0) {
      char details[64];
      snprintf(details, sizeof(details), "Loaded %d rule(s) from storage", loaded);
      send_status("INFO", "Rules restored", details);
    } else {
      // No saved rules, load platform-specific defaults if available
#ifdef PLATFORM_SAMD51
      loaded = load_samd51_default_rules(action_manager);
      if (loaded > 0) {
        char details[64];
        snprintf(details, sizeof(details), "Loaded %d default rule(s)", loaded);
        send_status("INFO", "Default rules loaded", details);
        // Save defaults to flash for next boot
        action_manager->save_rules();
      }
#endif
    }
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

  // Update periodic actions
  if (action_manager) {
    action_manager->update_periodic();
  }

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
    if (action_manager) {
      action_manager->check_and_execute(message);
    }
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
  } else if (strncmp(command, "set:", 4) == 0) {
    handle_set_command(command + 4);
  } else if (strncmp(command, "control:", 8) == 0) {
    handle_control_command(command + 8);
  } else if (strncmp(command, "action:", 7) == 0) {
    handle_action_command(command + 7);
  } else if (strncmp(command, "custom:", 7) == 0) {
    handle_custom_command(command + 7);
  } else {
    // Return error for unknown commands per protocol spec
    char error_msg[128];
    snprintf(error_msg, sizeof(error_msg), "Unknown command: %.60s", command);
    Serial.print("STATUS;ERROR;COMMAND;");
    Serial.println(error_msg);
  }
}

void handle_send_command(const char* params) {
  // Parse format: ID:DATA
  char* colon_pos = strchr(params, ':');
  if (!colon_pos) {
    Serial.println("STATUS;ERROR;PARAM;Missing CAN ID in send command");
    return;
  }

  *colon_pos = '\0';
  const char* id_str = params;
  const char* data_str = colon_pos + 1;

  // Validate CAN ID is not empty
  if (strlen(id_str) == 0) {
    Serial.println("STATUS;ERROR;PARAM;Missing CAN ID in send command");
    return;
  }

  // Parse CAN ID and validate hex format
  char* endptr;
  uint32_t can_id = strtoul(id_str, &endptr, 16);

  // Check if parsing failed (no valid hex digits)
  if (endptr == id_str) {
    Serial.print("STATUS;ERROR;PARAM;Invalid CAN ID format: ");
    Serial.println(id_str);
    return;
  }

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
  while (token != NULL) {
    // Check if we're exceeding max data length
    if (message.length >= CAN_MAX_DATA_LENGTH) {
      Serial.println("STATUS;ERROR;PARAM;Too many data bytes (max 8)");
      return;
    }

    // Validate hex format for data byte
    char* data_endptr;
    unsigned long byte_val = strtoul(token, &data_endptr, 16);

    // Check if parsing failed or invalid hex
    if (data_endptr == token || *data_endptr != '\0') {
      Serial.print("STATUS;ERROR;PARAM;Invalid hex data: ");
      Serial.println(token);
      return;
    }

    // Check if byte value is out of range
    if (byte_val > 0xFF) {
      Serial.print("STATUS;ERROR;PARAM;Data byte out of range (0-FF): ");
      Serial.println(token);
      return;
    }

    message.data[message.length] = (uint8_t)byte_val;
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
  } else if (strcmp(param, "mode") == 0) {
    // Handle loopback mode configuration
    if (strcmp(value, "loopback") == 0) {
      if (can_interface->set_loopback_mode(true)) {
        send_status("CONFIG", "Loopback mode enabled");
      } else {
        send_status("ERROR", "Loopback mode not supported on this platform");
      }
    } else if (strcmp(value, "normal") == 0) {
      if (can_interface->set_loopback_mode(false)) {
        send_status("CONFIG", "Normal mode enabled");
      } else {
        send_status("ERROR", "Mode change failed");
      }
    } else {
      send_status("ERROR", "Invalid mode (use 'loopback' or 'normal')");
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

  } else if (strcmp(param, "capabilities") == 0) {
    // Send platform capabilities as JSON
    send_capabilities_json();

  } else if (strcmp(param, "pins") == 0) {
    // Send available pin information
    send_pin_info();

  } else if (strcmp(param, "actions") == 0) {
    // Send supported action types
    send_supported_actions();

  } else if (strcmp(param, "name") == 0) {
    // Send device name
    Serial.print("NAME;");
    Serial.println(get_device_name());

  } else if (strcmp(param, "commands") == 0) {
    // Send custom commands in JSON format
    if (action_manager) {
      action_manager->get_custom_commands().print_commands();
    }

  } else if (strcmp(param, "actiondefs") == 0) {
    // Send action definitions for UI discovery
    print_all_action_definitions();

  } else if (strncmp(param, "actiondef:", 10) == 0) {
    // Get specific action definition by action type number
    uint8_t action_type = atoi(param + 10);
    const ActionDefinition* def = get_action_definition((ActionType)action_type);
    if (def) {
      print_action_definition_json(def);
    } else {
      send_status("ERROR", "Action definition not found");
    }
  }
}

void handle_set_command(const char* params) {
  // Parse format: PARAM:VALUE
  char* colon_pos = strchr(params, ':');
  if (!colon_pos) {
    return;
  }

  *colon_pos = '\0';
  const char* param = params;
  const char* value = colon_pos + 1;

  if (strcmp(param, "name") == 0) {
    // Set device name
    set_device_name(value);
  } else {
    // Unknown parameter, silently ignore
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
  if (!action_manager) {
    send_status("ERROR", "Action manager not initialized");
    return;
  }

  // Parse action subcommands
  if (strncmp(params, "add:", 4) == 0) {
    // Use ActionManager's parser
    uint8_t added_id = action_manager->parse_and_add_rule(params + 4);
    if (added_id > 0) {
      char message[64];
      snprintf(message, sizeof(message), "Rule added with ID: %d", added_id);
      send_status("INFO", message);
    } else {
      send_status("ERROR", "Failed to add action");
    }

  } else if (strncmp(params, "remove:", 7) == 0 || strncmp(params, "delete:", 7) == 0) {
    // Support both remove and delete commands
    const char* id_str = (strncmp(params, "remove:", 7) == 0) ? (params + 7) : (params + 7);
    uint8_t rule_id = atoi(id_str);
    if (action_manager->remove_rule(rule_id)) {
      send_status("INFO", "Action removed");
    } else {
      send_status("ERROR", "Action not found");
    }

  } else if (strncmp(params, "edit:", 5) == 0) {
    // Edit existing rule: action:edit:ID:CAN_ID:MASK:DATA:DMASK:LEN:ACTION:PARAM_SOURCE:PARAMS
    // First remove the old rule, then add the new one with the same ID
    char* colon_pos = strchr(params + 5, ':');
    if (!colon_pos) {
      send_status("ERROR", "Invalid edit format");
      return;
    }

    uint8_t rule_id = atoi(params + 5);

    // Remove the existing rule
    if (!action_manager->remove_rule(rule_id)) {
      send_status("ERROR", "Rule not found");
      return;
    }

    // Add the new rule with the same ID
    // Format the add command string by prepending the ID
    char add_params[256];
    snprintf(add_params, sizeof(add_params), "%d%s", rule_id, colon_pos);

    uint8_t added_id = action_manager->parse_and_add_rule(add_params);
    if (added_id > 0) {
      char message[64];
      snprintf(message, sizeof(message), "Rule %d updated", rule_id);
      send_status("INFO", message);
    } else {
      send_status("ERROR", "Failed to update rule");
    }

  } else if (strcmp(params, "list") == 0) {
    uint8_t count = action_manager->get_rule_count();
    char details[32];
    snprintf(details, sizeof(details), "%d rules active", count);
    send_status("INFO", "Actions", details);

    // Let ActionManager handle the formatting
    action_manager->print_rules();

  } else if (strncmp(params, "enable:", 7) == 0) {
    uint8_t rule_id = atoi(params + 7);
    if (action_manager->set_rule_enabled(rule_id, true)) {
      send_status("INFO", "Action enabled");
    } else {
      send_status("ERROR", "Action not found");
    }

  } else if (strncmp(params, "disable:", 8) == 0) {
    uint8_t rule_id = atoi(params + 8);
    if (action_manager->set_rule_enabled(rule_id, false)) {
      send_status("INFO", "Action disabled");
    } else {
      send_status("ERROR", "Action not found");
    }

  } else if (strcmp(params, "clear") == 0) {
    action_manager->clear_all_rules();
    send_status("INFO", "All actions cleared");
  }
}

// ============================================================================
// Custom Command Handler
// ============================================================================

void handle_custom_command(const char* params) {
  if (!action_manager) {
    send_status("ERROR", "Action manager not initialized");
    return;
  }

  // Parse format: COMMAND_NAME:PARAM1:PARAM2:...
  // Example: neopixel:255:0:0:128
  char buffer[256];
  strncpy(buffer, params, sizeof(buffer) - 1);
  buffer[sizeof(buffer) - 1] = '\0';

  char* colon = strchr(buffer, ':');
  const char* command_name = buffer;
  const char* command_params = "";

  if (colon) {
    *colon = '\0';
    command_params = colon + 1;
  }

  // Execute custom command
  if (action_manager->get_custom_commands().execute_command(command_name, command_params)) {
    send_status("INFO", "Custom command executed", command_name);
  } else {
    send_status("ERROR", "Custom command failed or not found", command_name);
  }
}
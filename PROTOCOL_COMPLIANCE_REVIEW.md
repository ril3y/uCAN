# uCAN Protocol Compliance Review

**Review Date:** 2025-01-27
**Protocol Version:** 2.0
**Reviewer:** ril3y
**Firmware Files Reviewed:**
- `docs/PROTOCOL.md` (Protocol Specification)
- `src/main.cpp` (Command Handler Implementation)
- `src/actions/action_manager_base.cpp` (Action System Implementation)
- `src/actions/action_manager_base.h` (Action System Interface)
- `src/actions/action_types.h` (Action Type Definitions)
- `src/hal/can_interface.h` (CAN Error Definitions)

---

## Executive Summary

This review identified **17 discrepancies** between the protocol specification (PROTOCOL.md) and the firmware implementation. Issues range from critical (error response format inconsistencies) to minor (missing field validation). The firmware is generally well-structured but has several areas where implementation diverges from documented behavior.

**Critical Issues:** 3
**High Priority:** 6
**Medium Priority:** 5
**Low Priority:** 3

---

## Critical Issues (Fix Immediately)

### 1. Error Response Format Inconsistency ⚠️ CRITICAL

**Protocol Specification (Lines 1698-1702):**
```
STATUS;ERROR;Command;Invalid format
STATUS;ERROR;Command;Unknown command
STATUS;ERROR;Command;Invalid parameter
```

**Firmware Implementation (src/main.cpp:433-439):**
```cpp
void send_error(CANError error, const char* description) {
  Serial.print("CAN_ERR;0x");
  if (error < 0x10) Serial.print("0");
  Serial.print(error, HEX);
  Serial.print(";");
  Serial.println(description);
}
```

**Problem:** The firmware has two different error response formats:
1. `STATUS;ERROR;Category;Message` (used by `send_status()`)
2. `CAN_ERR;{ERROR_CODE};{DESCRIPTION}` (used by `send_error()`)

**Impact:**
- Protocol spec documents only `STATUS;ERROR` format for command errors
- `CAN_ERR` format is documented for CAN bus errors only (lines 198-214)
- TUI/client parsers expecting `STATUS;ERROR` will miss errors sent via `send_error()`

**Location in Code:**
- `src/main.cpp:272` - Uses `send_error(CAN_ERROR_OTHER, "Failed to send message")`
- `src/main.cpp:298` - Uses `send_error(CAN_ERROR_CONFIG_ERROR, "Failed to change baudrate")`

**Recommended Fix:**
```cpp
// For CAN-related errors, keep CAN_ERR format
void send_can_error(CANError error, const char* description) {
  Serial.print("CAN_ERR;0x");
  if (error < 0x10) Serial.print("0");
  Serial.print(error, HEX);
  Serial.print(";");
  Serial.println(description);
}

// For command/protocol errors, use STATUS;ERROR format
void send_command_error(const char* category, const char* message) {
  send_status("ERROR", category, message);
}
```

Then update call sites:
- Line 272: `send_command_error("CAN", "Failed to send message")`
- Line 298: `send_command_error("Configuration", "Failed to change baudrate")`

---

### 2. CAN_ERR Format Mismatch ⚠️ CRITICAL

**Protocol Specification (Line 200):**
```
Format: CAN_ERR;{ERROR_TYPE};{DETAILS};{TIMESTAMP}
```

**Firmware Implementation (src/main.cpp:433-439):**
```cpp
Serial.print("CAN_ERR;0x");
Serial.print(error, HEX);  // Sends hex code, not ERROR_TYPE string
Serial.print(";");
Serial.println(description);  // Missing timestamp
```

**Problem:**
1. Protocol expects string error types like `BUS_OFF`, `TX_FAILED`
2. Firmware sends hex codes like `0x01`, `0x10`
3. Missing timestamp field

**Impact:**
- Parsers expecting string types will fail
- Missing timestamp prevents error correlation with other events

**Recommended Fix:**
```cpp
void send_can_error(CANError error, const char* description) {
  Serial.print("CAN_ERR;");
  Serial.print(can_error_to_string(error));  // Convert to string
  Serial.print(";");
  Serial.print(description);
  Serial.print(";");
  Serial.println(millis());  // Add timestamp
}

// Add helper function
const char* can_error_to_string(CANError error) {
  switch (error) {
    case CAN_ERROR_BUS_OFF: return "BUS_OFF";
    case CAN_ERROR_PASSIVE: return "ERROR_PASSIVE";
    case CAN_ERROR_WARNING: return "ERROR_WARNING";
    case CAN_ERROR_ARBITRATION_LOST: return "ARBITRATION_LOST";
    case CAN_ERROR_BUFFER_OVERFLOW: return "RX_OVERFLOW";
    case CAN_ERROR_CONFIG_ERROR: return "CONFIG_ERROR";
    default: return "OTHER";
  }
}
```

---

### 3. Missing PARAM_SOURCE Validation ⚠️ CRITICAL

**Protocol Specification (Lines 207-214, 788):**
```
Token 7 MUST be "candata" or "fixed"
```

**Firmware Implementation (src/actions/action_manager_base.cpp:210-223):**
```cpp
if (token_count < 8) {
    // Missing PARAM_SOURCE field - error
    return 0;
}

if (strcmp(tokens[7], "candata") == 0 || strcmp(tokens[7], "can") == 0) {
    rule.param_source = PARAM_FROM_CAN_DATA;
} else if (strcmp(tokens[7], "fixed") == 0 || strcmp(tokens[7], "rule") == 0) {
    rule.param_source = PARAM_FROM_RULE;
} else {
    // Invalid PARAM_SOURCE value - error
    return 0;
}
```

**Problem:**
- Code accepts "can" and "rule" as aliases, but protocol doesn't document these
- No error message sent when validation fails (line 213, 222)
- Silent failure confuses users

**Impact:**
- Users don't know why their command failed
- Debugging is difficult without error feedback

**Recommended Fix:**
```cpp
if (token_count < 8) {
    send_status("ERROR", "Invalid action format", "Missing PARAM_SOURCE field");
    return 0;
}

if (strcmp(tokens[7], "candata") == 0) {
    rule.param_source = PARAM_FROM_CAN_DATA;
} else if (strcmp(tokens[7], "fixed") == 0) {
    rule.param_source = PARAM_FROM_RULE;
} else {
    send_status("ERROR", "Invalid PARAM_SOURCE", "Must be 'candata' or 'fixed'");
    return 0;
}
```

---

## High Priority Issues

### 4. Hex Case Inconsistency

**Protocol Specification (Lines 48-53):**
```
- Examples in this document show lowercase hex (e.g., `0x100`, `0xff`)
- **Implementations MAY output uppercase or lowercase** (case-insensitive)
- Parsers MUST accept both uppercase and lowercase hex values
- Arduino firmware outputs uppercase (e.g., `0x100` becomes `0X100`)
```

**Firmware Implementation:**
```cpp
// src/main.cpp:163-172 - Outputs uppercase
Serial.print("0x");
Serial.print(message.id, HEX);  // Arduino Serial.print(x, HEX) outputs uppercase

// src/main.cpp:259-266 - Same uppercase output
Serial.print("0x");
Serial.print(message.id, HEX);
```

**Problem:**
- Protocol says "0x100 becomes 0X100" but code outputs "0x100" (lowercase 'x')
- Actual output is `0x` prefix with uppercase hex digits: `0xABCD` not `0XABCD`
- Documentation error, not code error

**Impact:** Minor - documentation inaccuracy

**Recommended Fix:** Update PROTOCOL.md line 53:
```markdown
- Arduino firmware outputs uppercase hex digits with lowercase prefix (e.g., `0x100`, `0xFF`)
```

---

### 5. Missing Command Error Responses

**Protocol Specification:** Documents specific error messages but firmware doesn't send them

**Locations:**
1. **Line 221** - `handle_command()` silently ignores unknown commands
   ```cpp
   // Silently ignore unknown commands for protocol compatibility
   ```
   Should send: `STATUS;ERROR;Command;Unknown command`

2. **Line 228** - `handle_send_command()` no error on missing colon
   ```cpp
   if (!colon_pos) {
       return;  // Silent failure
   }
   ```
   Should send: `STATUS;ERROR;Command;Invalid send format`

3. **Line 279** - `handle_config_command()` no error on missing colon
   ```cpp
   if (!colon_pos) {
       return;  // Silent failure
   }
   ```
   Should send: `STATUS;ERROR;Configuration;Invalid config format`

**Impact:** Users get no feedback when commands fail parsing

**Recommended Fix:**
```cpp
void handle_command(const char* command) {
  if (strncmp(command, "send:", 5) == 0) {
    handle_send_command(command + 5);
  } else if (strncmp(command, "config:", 7) == 0) {
    handle_config_command(command + 7);
  } // ... other handlers
  else {
    send_status("ERROR", "Command", "Unknown command");
  }
}

void handle_send_command(const char* params) {
  char* colon_pos = strchr(params, ':');
  if (!colon_pos) {
    send_status("ERROR", "Command", "Invalid send format - expected 'send:ID:DATA'");
    return;
  }
  // ... rest of function
}
```

---

### 6. ACTION Message Format Missing Fields

**Protocol Specification (Lines 585-607):**
```
Format: ACTION;{RULE_ID};{ACTION_TYPE};{TRIGGER_CAN_ID};{STATUS}

Examples:
ACTION;1;GPIO_SET;0x100;OK
ACTION;5;NEOPIXEL;0x500;OK
ACTION;3;PWM_SET;0x200;FAIL
```

**Firmware Implementation (src/actions/action_manager_base.cpp:49-57):**
```cpp
Serial.print("ACTION;");
Serial.print(rules_[i].id);
Serial.print(";");
Serial.print(action_type_to_string(rules_[i].action));
Serial.print(";0x");
Serial.print(message.id, HEX);
Serial.print(";");
Serial.println(success ? "OK" : "FAIL");
```

**Problem:** Format is correct, but NO validation that message.id fits in output format

**Impact:** If `message.id` is extended (29-bit), the hex representation could be very long

**Recommended Enhancement:**
```cpp
// Ensure consistent hex formatting
char hex_buf[16];
snprintf(hex_buf, sizeof(hex_buf), "0x%lX", (unsigned long)message.id);
Serial.print(hex_buf);
```

---

### 7. RULE Output Format Doesn't Match Protocol

**Protocol Specification (Lines 923-948):**
```
Response Format:
RULE;{ID};{CAN_ID};{CAN_MASK};{DATA};{DATA_MASK};{DATA_LEN};{ACTION};{PARAM_SOURCE};{PARAMS...}

Examples:
RULE;1;0x500;0xFFFFFFFF;;;0;NEOPIXEL;candata
RULE;2;0x100;0xFFFFFFFF;;;0;GPIO_SET;fixed;13
```

**Firmware Implementation (src/actions/action_manager_base.cpp:361-478):**
```cpp
Serial.print("RULE;");
Serial.print(rule.id);
Serial.print(";0x");
Serial.print(rule.can_id, HEX);
Serial.print(";0x");
Serial.print(rule.can_id_mask, HEX);
// ... continues correctly
```

**Problem:** Actually CORRECT! But inconsistent uppercase/lowercase hex (see issue #4)

**Impact:** None - code matches spec

**Status:** No fix needed, just document review confirmation

---

### 8. Missing Validation for action:edit Command

**Protocol Specification (Lines 875-919):**
```
Error Cases:
STATUS;ERROR;Rule not found          (if RULE_ID doesn't exist)
STATUS;ERROR;Failed to update rule   (if new rule parameters are invalid)
```

**Firmware Implementation (src/main.cpp:535-564):**
```cpp
// Remove the existing rule
if (!action_manager->remove_rule(rule_id)) {
  send_status("ERROR", "Rule not found");  // ✅ Correct
  return;
}

uint8_t added_id = action_manager->parse_and_add_rule(add_params);
if (added_id > 0) {
  char message[64];
  snprintf(message, sizeof(message), "Rule %d updated", rule_id);
  send_status("INFO", message);  // ✅ Correct
} else {
  send_status("ERROR", "Failed to update rule");  // ✅ Correct
}
```

**Problem:** Actually CORRECT! Code matches protocol spec.

**Status:** No fix needed

---

### 9. Missing Parameter Count Validation

**Protocol Specification (Lines 829-852):** Shows examples with specific parameter counts

**Firmware Implementation (src/actions/action_manager_base.cpp:228-290):**
```cpp
} else if (strcmp(action_type, "GPIO_SET") == 0) {
    rule.action = ACTION_GPIO_SET;
    if (rule.param_source == PARAM_FROM_RULE && token_count > param_start_index) {
        rule.params.gpio.pin = atoi(tokens[param_start_index]);
    }
```

**Problem:**
- Only checks `token_count > param_start_index` (at least 1 parameter)
- Doesn't validate exact parameter count per action type
- NEOPIXEL needs 4 params, but code only checks `token_count > param_start_index + 3`

**Impact:**
- Missing parameters default to 0, causing unexpected behavior
- No error message for wrong parameter count

**Recommended Fix:**
```cpp
} else if (strcmp(action_type, "GPIO_SET") == 0) {
    rule.action = ACTION_GPIO_SET;
    if (rule.param_source == PARAM_FROM_RULE) {
        if (token_count < param_start_index + 1) {
            send_status("ERROR", "GPIO_SET requires 1 parameter (pin)");
            return 0;
        }
        rule.params.gpio.pin = atoi(tokens[param_start_index]);
    }
```

---

## Medium Priority Issues

### 10. Incomplete CAN_SEND Parameter Parsing

**Protocol Specification (Line 851):**
```
action:add:0:0x600:0xFFFFFFFF:::0:NEOPIXEL:fixed:255:128:0:200
```

**Firmware Implementation (src/actions/action_manager_base.cpp:265-273):**
```cpp
} else if (strcmp(action_type, "CAN_SEND") == 0) {
    rule.action = ACTION_CAN_SEND;
    if (token_count > param_start_index + 1) {
        rule.params.can_send.can_id = strtoul(tokens[param_start_index], nullptr, 16);
        // Parse data bytes from tokens[param_start_index + 1] (comma-separated)
        const char* data_str = tokens[param_start_index + 1];
        rule.params.can_send.length = 0;
        // TODO: Parse comma-separated data bytes  ⚠️ NOT IMPLEMENTED
    }
```

**Problem:** Data byte parsing is stubbed out with TODO comment

**Impact:** CAN_SEND and CAN_SEND_PERIODIC actions cannot be configured via serial commands

**Recommended Fix:**
```cpp
// Parse comma-separated data bytes
const char* data_str = tokens[param_start_index + 1];
rule.params.can_send.length = 0;

char data_copy[64];
strncpy(data_copy, data_str, sizeof(data_copy) - 1);
data_copy[sizeof(data_copy) - 1] = '\0';

char* byte_token = strtok(data_copy, ",");
while (byte_token && rule.params.can_send.length < 8) {
    rule.params.can_send.data[rule.params.can_send.length++] =
        strtoul(byte_token, nullptr, 16);
    byte_token = strtok(nullptr, ",");
}
```

---

### 11. STATUS Message Inconsistent Format

**Protocol Specification (Line 219):**
```
Format: STATUS;{LEVEL};{CATEGORY};{MESSAGE}
```

**Firmware Implementation:** Uses different field orders in different places:

1. **src/main.cpp:68** (Startup):
   ```cpp
   send_status("CONNECTED", can_interface->get_platform_name(), details);
   // Output: STATUS;CONNECTED;SAMD51_CAN;SAMD51_CAN v2.0 @ 500kbps
   // Format: STATUS;{LEVEL};{CATEGORY};{MESSAGE}  ✅ CORRECT
   ```

2. **src/main.cpp:296** (Config changed):
   ```cpp
   send_status("CONFIG", "Baudrate changed", value);
   // Output: STATUS;CONFIG;Baudrate changed;250000
   // Format: STATUS;{CATEGORY};{MESSAGE};{VALUE}  ❌ WRONG LEVEL
   ```

3. **src/main.cpp:332** (Get status):
   ```cpp
   send_status("INFO", "Running", details);
   // Output: STATUS;INFO;Running;RX:1234 TX:567 ERR:2
   // Format: STATUS;{LEVEL};{CATEGORY};{MESSAGE}  ✅ CORRECT
   ```

**Problem:** Line 296 uses "CONFIG" as level instead of category

**Recommended Fix:**
```cpp
send_status("INFO", "Configuration", "Baudrate changed to 250kbps");
```

---

### 12. Missing get:actiondef Error Handling

**Protocol Specification (Lines 755-768):**
```
get:actiondef:{ACTION_ID}

Example:
get:actiondef:7

Response:
ACTIONDEF;{"i":7,"n":"NEOPIXEL",...}
```

**Firmware Implementation (src/main.cpp:373-381):**
```cpp
} else if (strncmp(param, "actiondef:", 10) == 0) {
    uint8_t action_type = atoi(param + 10);
    const ActionDefinition* def = get_action_definition((ActionType)action_type);
    if (def) {
        print_action_definition_json(def);
    } else {
        send_status("ERROR", "Action definition not found");  // ✅ CORRECT
    }
}
```

**Problem:** Protocol doesn't document the error response format for missing definitions

**Impact:** Minor - error handling exists but undocumented

**Recommended Fix:** Add to PROTOCOL.md after line 768:
```markdown
**Error Response:**
```
STATUS;ERROR;Action definition not found
```
```

---

### 13. action:clear Response Undocumented

**Protocol Specification (Lines 955-962):**
```
action:clear

Response:
STATUS;INFO;All rules cleared
```

**Firmware Implementation (src/main.cpp:591-593):**
```cpp
} else if (strcmp(params, "clear") == 0) {
    action_manager->clear_all_rules();
    send_status("INFO", "All actions cleared");  // ✅ CORRECT
}
```

**Problem:** Response says "All actions cleared" but protocol says "All rules cleared"

**Impact:** Minor inconsistency in terminology

**Recommended Fix:** Update protocol to match firmware, or vice versa. Prefer "rules" for consistency:
```cpp
send_status("INFO", "All rules cleared");
```

---

### 14. Missing action:enable/disable Documentation

**Protocol Specification:** No documentation for these commands

**Firmware Implementation (src/main.cpp:575-589):**
```cpp
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
```

**Problem:** Implemented commands not documented in protocol

**Impact:** Users don't know these commands exist

**Recommended Fix:** Add to PROTOCOL.md after line 919:
```markdown
### action:enable - Enable Action Rule

Format: `action:enable:{RULE_ID}`

**Example:**
```
action:enable:1
```

**Response:**
```
STATUS;INFO;Action enabled
```

**Error Response:**
```
STATUS;ERROR;Action not found
```

### action:disable - Disable Action Rule

Format: `action:disable:{RULE_ID}`

**Example:**
```
action:disable:1
```

**Response:**
```
STATUS;INFO;Action disabled
```

**Error Response:**
```
STATUS;ERROR;Action not found
```
```

---

## Low Priority Issues

### 15. custom: Command Handler Undocumented

**Protocol Specification:** No documentation

**Firmware Implementation (src/main.cpp:218-220, 601-628):**
```cpp
} else if (strncmp(command, "custom:", 7) == 0) {
    handle_custom_command(command + 7);
}

void handle_custom_command(const char* params) {
    // Full implementation exists
}
```

**Problem:** Entire custom command system not documented in PROTOCOL.md

**Impact:** Advanced feature unavailable to users without documentation

**Recommended Fix:** Add section to PROTOCOL.md documenting custom command system

---

### 16. set:name Command Undocumented

**Protocol Specification:** No documentation

**Firmware Implementation (src/main.cpp:385-402):**
```cpp
void handle_set_command(const char* params) {
  char* colon_pos = strchr(params, ':');
  if (!colon_pos) {
      return;
  }

  *colon_pos = '\0';
  const char* param = params;
  const char* value = colon_pos + 1;

  if (strcmp(param, "name") == 0) {
    set_device_name(value);
  }
}
```

**Problem:** No response sent after setting name

**Impact:** User doesn't know if command succeeded

**Recommended Fix:**
```cpp
if (strcmp(param, "name") == 0) {
    set_device_name(value);
    send_status("INFO", "Device name set", value);
}
```

---

### 17. control: Command Handler Undocumented

**Protocol Specification:** No documentation

**Firmware Implementation (src/main.cpp:404-419):**
```cpp
void handle_control_command(const char* action) {
  if (strcmp(action, "reset") == 0) {
    send_status("INFO", "Resetting device");
    delay(100);
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
```

**Problem:** Implemented control commands not in protocol spec

**Impact:** Useful features undiscoverable by users

**Recommended Fix:** Document in PROTOCOL.md

---

## Summary of Recommended Actions

### Immediate (Critical) - Week 1
1. ✅ **Fix error response format** - Separate CAN_ERR from STATUS;ERROR
2. ✅ **Add timestamp to CAN_ERR** - Per protocol spec
3. ✅ **Add PARAM_SOURCE validation messages** - User feedback on failures

### High Priority - Week 2
4. ✅ **Add command validation errors** - All handle_*_command() functions
5. ✅ **Implement CAN_SEND data parsing** - Remove TODO, make functional
6. ✅ **Add parameter count validation** - Prevent silent zero-defaults

### Medium Priority - Week 3
7. ✅ **Update STATUS message consistency** - Fix CONFIG vs INFO level
8. ✅ **Document action:enable/disable** - Add to protocol spec
9. ✅ **Add set:name response** - User feedback

### Low Priority - Week 4
10. ✅ **Document custom: commands** - Full section in protocol
11. ✅ **Document control: commands** - Add reset and clear
12. ✅ **Fix hex case documentation** - Clarify actual output format

---

## Testing Recommendations

After implementing fixes, test these scenarios:

1. **Error Handling:**
   ```
   send invalid command → expect STATUS;ERROR;Command;Unknown command
   send:INVALID → expect STATUS;ERROR;Command;Invalid send format
   action:add:0:0x100:0x7FF:::0:UNKNOWN:fixed → expect error
   ```

2. **CAN_ERR Format:**
   ```
   Trigger bus-off condition → expect CAN_ERR;BUS_OFF;description;timestamp
   Fill RX buffer → expect CAN_ERR;RX_OVERFLOW;description;timestamp
   ```

3. **Parameter Validation:**
   ```
   action:add:0:0x100:0x7FF:::0:GPIO_SET:fixed → expect error (missing pin)
   action:add:0:0x100:0x7FF:::0:GPIO_SET:invalid → expect error (bad PARAM_SOURCE)
   ```

4. **CAN_SEND Parsing:**
   ```
   action:add:0:0x100:0x7FF:::0:CAN_SEND:fixed:0x200:FF,00,AA,BB
   → verify data bytes parsed correctly
   ```

---

## Files Requiring Updates

**Firmware:**
- `src/main.cpp` - Primary command handler fixes
- `src/actions/action_manager_base.cpp` - Parameter parsing and validation
- `src/actions/action_types.h` - Add helper function declarations

**Documentation:**
- `docs/PROTOCOL.md` - Add missing commands, fix error format examples, clarify hex format

**New Files Needed:**
- `src/utils/protocol_helpers.cpp` - String conversion functions
- `src/utils/protocol_helpers.h` - Helper declarations

---

## Conclusion

The firmware is well-structured and mostly compliant with the protocol specification. The main issues are:

1. **Inconsistent error reporting** - Mix of CAN_ERR and STATUS;ERROR formats
2. **Missing user feedback** - Silent failures on invalid commands
3. **Incomplete implementations** - CAN_SEND data parsing stubbed
4. **Undocumented features** - control:, custom:, action:enable/disable work but aren't documented

All issues are fixable with focused effort over 2-4 weeks. The architecture supports these fixes without major refactoring.

**Priority:** Focus on Critical and High priority issues first for best user experience impact.

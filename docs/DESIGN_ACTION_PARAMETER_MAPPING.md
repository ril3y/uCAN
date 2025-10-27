# CAN Data Action Parameter Mapping Design

**Version:** 2.0
**Date:** 2025-01-25
**Author:** ril3y
**Status:** ✅ IMPLEMENTED (Firmware & Protocol v2.0)

## Executive Summary

This design extends the uCAN action system to support **CAN data-driven actions**, where parameters for actions (NeoPixel color, PWM duty cycle, servo positions) are extracted from received CAN message data bytes instead of being hard-coded in rules.

**Key Innovation:** A single CAN message can control hardware directly without pre-configuration. For example, `CAN ID 0x500` with data `[R, G, B, Brightness, 0, 0, 0, 0]` directly sets NeoPixel color.

**Memory Footprint:** Adds only 2 bytes per rule with minimal Flash overhead.

---

## Problem Statement

### Current Limitation

Rules currently have **fixed parameters** defined when the rule is created:

```cpp
// Current: Parameters are fixed at rule creation
ActionRule rule;
rule.action = ACTION_NEOPIXEL_COLOR;
rule.params.neopixel.r = 255;  // Always red
rule.params.neopixel.g = 0;
rule.params.neopixel.b = 0;
rule.params.neopixel.brightness = 128;
```

**Problem:** To change the NeoPixel color, you must delete and recreate the rule or send a different CAN ID with a different rule. This doesn't scale for:
- **Multi-value control:** Controlling 4 servos requires 4 rules instead of 1
- **Dynamic parameters:** RGB lighting effects need many pre-defined rules
- **Sensor feedback:** Can't easily map sensor data directly to actuators

### Desired Behavior

```cpp
// New: Parameters extracted from CAN data at runtime
ActionRule rule;
rule.action = ACTION_NEOPIXEL_COLOR;
rule.param_source = PARAM_FROM_CAN_DATA;  // Use CAN data bytes

// When CAN message arrives: ID=0x500, Data=[100, 200, 50, 255, ...]
// Firmware automatically extracts:
//   R = data[0] = 100
//   G = data[1] = 200
//   B = data[2] = 50
//   Brightness = data[3] = 255
```

---

## Design Goals

1. **Memory Efficient:** Minimal per-rule overhead (target: <4 bytes)
2. **Fast Execution:** Parameter extraction adds <10 CPU cycles
3. **Backward Compatible:** Existing fixed-parameter rules continue to work
4. **UI Discoverable:** UI can query action definitions and generate forms
5. **Extensible:** Easy to add new actions with custom parameter mappings
6. **Platform Independent:** Works on RP2040, SAMD51, ESP32

---

## Architecture Overview

### Three-Tier System

```
┌─────────────────────────────────────────────────────────────┐
│  1. ACTION DEFINITIONS (Compile-time, Flash)                │
│     - Defines what parameters each action needs             │
│     - Stored in platform-specific code                      │
│     - Used for UI discovery and validation                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. ACTION RULES (Runtime, RAM)                             │
│     - Matches CAN messages to actions                       │
│     - NEW: param_source flag (fixed vs. CAN data)          │
│     - Lightweight (2-byte overhead per rule)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. PARAMETER EXTRACTION (Runtime, inline functions)        │
│     - Extracts values from CAN data bytes                   │
│     - Fast bit-level operations                             │
│     - Zero dynamic allocation                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Data Structures

### 1. Parameter Source (New)

Defines where action parameters come from:

```cpp
/**
 * Parameter Source
 *
 * Defines where action parameters are sourced from.
 */
enum ParamSource : uint8_t {
    PARAM_FROM_RULE = 0,     // Use fixed parameters stored in rule (backward compatible)
    PARAM_FROM_CAN_DATA = 1  // Extract parameters from received CAN data bytes
};
```

**Memory:** 1 byte per rule (can be bit-packed later)

### 2. Parameter Mapping (Compile-time)

Defines how to extract a parameter from CAN data:

```cpp
/**
 * Parameter Mapping
 *
 * Defines how to extract a single parameter from CAN data bytes.
 * This is a compile-time constant (stored in Flash, not RAM).
 */
struct ParamMapping {
    uint8_t data_byte_index;    // Which CAN data byte (0-7)
    uint8_t bit_offset;         // Bit offset within byte (0-7, for packed data)
    uint8_t bit_length;         // Number of bits (1-8, for packed data)
    ParamType type;             // Data type (uint8, uint16, etc.)

    // Validation (optional, can be used by UI)
    uint32_t min_value;         // Minimum valid value
    uint32_t max_value;         // Maximum valid value
    const char* name;           // Parameter name (for UI)
};
```

**Memory:** Lives in Flash (PROGMEM), not counted against RAM budget.

### 3. Action Definition (Compile-time)

Defines an action type and its parameter requirements:

```cpp
/**
 * Action Definition
 *
 * Defines an action type and how to extract its parameters from CAN data.
 * This is a compile-time constant stored in Flash.
 */
struct ActionDefinition {
    ActionType action;                  // Action type enum
    const char* name;                   // Action name (e.g., "NEOPIXEL")
    const char* description;            // Human-readable description
    uint8_t param_count;                // Number of parameters
    const ParamMapping* param_map;      // Parameter mapping array (Flash pointer)
};
```

**Memory:** Lives in Flash, not RAM.

### 4. Extended ActionRule (Runtime)

Add parameter source to existing rule structure:

```cpp
struct ActionRule {
    // Existing fields (unchanged)
    uint8_t id;
    bool enabled;
    uint32_t can_id;
    uint32_t can_id_mask;
    uint8_t data[8];
    uint8_t data_mask[8];
    uint8_t data_length;
    ActionType action;
    ActionParams params;
    uint32_t last_execute_ms;
    uint32_t execute_count;

    // NEW: Parameter source flag
    ParamSource param_source;  // Where to get parameters from

    // OPTIONAL: Byte offset for advanced use cases
    uint8_t param_data_offset; // CAN data byte offset (default 0)
};
```

**Memory Overhead:**
- `param_source`: 1 byte
- `param_data_offset`: 1 byte (optional)
- **Total:** 2 bytes per rule

**Impact on SAMD51 (64 rules):** 64 rules × 2 bytes = 128 bytes (0.07% of 192KB RAM)

---

## Parameter Extraction Engine

### Fast Inline Extraction

```cpp
/**
 * Extract uint8 parameter from CAN data
 *
 * Optimized for speed - inlined, no branches.
 *
 * @param can_data CAN message data array
 * @param mapping Parameter mapping definition
 * @return Extracted uint8 value
 */
inline uint8_t extract_uint8(const uint8_t* can_data, const ParamMapping& mapping) {
    uint8_t raw_value = can_data[mapping.data_byte_index];

    // If bit_length < 8, extract specific bits
    if (mapping.bit_length < 8) {
        uint8_t mask = (1 << mapping.bit_length) - 1;
        raw_value = (raw_value >> mapping.bit_offset) & mask;
    }

    // Optional: Clamp to min/max (can be disabled for speed)
    if (raw_value < mapping.min_value) raw_value = mapping.min_value;
    if (raw_value > mapping.max_value) raw_value = mapping.max_value;

    return raw_value;
}

/**
 * Extract uint16 parameter from CAN data (little-endian)
 */
inline uint16_t extract_uint16(const uint8_t* can_data, const ParamMapping& mapping) {
    uint16_t value = can_data[mapping.data_byte_index] |
                     (can_data[mapping.data_byte_index + 1] << 8);
    return value;
}

// Similar functions for int8, int16, uint32, float...
```

**Performance:**
- uint8 extraction: ~5-10 CPU cycles
- uint16 extraction: ~8-12 CPU cycles
- No dynamic allocation
- No function call overhead (inlined)

---

## Action Execution Flow

### Current Flow (Fixed Parameters)

```cpp
bool ActionManagerBase::execute_action(const ActionRule& rule, const CANMessage& message) {
    switch (rule.action) {
        case ACTION_NEOPIXEL_COLOR:
            return execute_neopixel_action(
                rule.params.neopixel.r,        // From rule
                rule.params.neopixel.g,        // From rule
                rule.params.neopixel.b,        // From rule
                rule.params.neopixel.brightness // From rule
            );
    }
}
```

### New Flow (CAN Data Parameters)

```cpp
bool ActionManagerBase::execute_action(const ActionRule& rule, const CANMessage& message) {
    switch (rule.action) {
        case ACTION_NEOPIXEL_COLOR: {
            uint8_t r, g, b, brightness;

            if (rule.param_source == PARAM_FROM_CAN_DATA) {
                // Extract from CAN data bytes
                const ActionDefinition* def = get_action_definition(rule.action);
                r = extract_uint8(message.data, def->param_map[0]);
                g = extract_uint8(message.data, def->param_map[1]);
                b = extract_uint8(message.data, def->param_map[2]);
                brightness = extract_uint8(message.data, def->param_map[3]);
            } else {
                // Use fixed parameters from rule (backward compatible)
                r = rule.params.neopixel.r;
                g = rule.params.neopixel.g;
                b = rule.params.neopixel.b;
                brightness = rule.params.neopixel.brightness;
            }

            return execute_neopixel_action(r, g, b, brightness);
        }
    }
}
```

---

## Example Action Definitions

### NeoPixel RGB Control

```cpp
// Parameter mappings (Flash storage)
static const ParamMapping NEOPIXEL_PARAMS[] PROGMEM = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "r"},           // R from byte 0
    {1, 0, 8, PARAM_UINT8, 0, 255, "g"},           // G from byte 1
    {2, 0, 8, PARAM_UINT8, 0, 255, "b"},           // B from byte 2
    {3, 0, 8, PARAM_UINT8, 0, 255, "brightness"}   // Brightness from byte 3
};

// Action definition (Flash storage)
static const ActionDefinition NEOPIXEL_DEF PROGMEM = {
    .action = ACTION_NEOPIXEL_COLOR,
    .name = "NEOPIXEL",
    .description = "Control NeoPixel RGB LED",
    .param_count = 4,
    .param_map = NEOPIXEL_PARAMS
};
```

**CAN Message Format:**
```
CAN ID: 0x500
Data:   [R, G, B, Brightness, 0, 0, 0, 0]
Example: 0x500: [255, 128, 0, 200, 0, 0, 0, 0]  -> Orange at 78% brightness
```

### PWM Control (Single Actuator)

```cpp
static const ParamMapping PWM_PARAMS[] PROGMEM = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin"},    // Pin from byte 0
    {1, 0, 8, PARAM_UINT8, 0, 255, "duty"}    // Duty from byte 1
};

static const ActionDefinition PWM_DEF PROGMEM = {
    .action = ACTION_PWM_SET,
    .name = "PWM_SET",
    .description = "Set PWM duty cycle",
    .param_count = 2,
    .param_map = PWM_PARAMS
};
```

**CAN Message Format:**
```
CAN ID: 0x501
Data:   [Pin, Duty, 0, 0, 0, 0, 0, 0]
Example: 0x501: [5, 128, 0, 0, 0, 0, 0, 0]  -> Pin 5 at 50% duty
```

### Multi-Servo Control (4 Servos)

```cpp
// New action type for multi-servo
enum ActionType {
    // ... existing actions ...
    ACTION_MULTI_SERVO,  // Control up to 8 servos from one message
};

static const ParamMapping MULTI_SERVO_PARAMS[] PROGMEM = {
    {0, 0, 8, PARAM_UINT8, 0, 180, "servo1_angle"},
    {1, 0, 8, PARAM_UINT8, 0, 180, "servo2_angle"},
    {2, 0, 8, PARAM_UINT8, 0, 180, "servo3_angle"},
    {3, 0, 8, PARAM_UINT8, 0, 180, "servo4_angle"},
    {4, 0, 8, PARAM_UINT8, 0, 180, "servo5_angle"},
    {5, 0, 8, PARAM_UINT8, 0, 180, "servo6_angle"},
    {6, 0, 8, PARAM_UINT8, 0, 180, "servo7_angle"},
    {7, 0, 8, PARAM_UINT8, 0, 180, "servo8_angle"}
};

static const ActionDefinition MULTI_SERVO_DEF PROGMEM = {
    .action = ACTION_MULTI_SERVO,
    .name = "MULTI_SERVO",
    .description = "Control up to 8 servos simultaneously",
    .param_count = 8,
    .param_map = MULTI_SERVO_PARAMS
};
```

**CAN Message Format:**
```
CAN ID: 0x502
Data:   [S1, S2, S3, S4, S5, S6, S7, S8]  (angles 0-180 degrees)
Example: 0x502: [90, 45, 135, 90, 0, 180, 90, 90]
```

### Bit-Packed Switch Control

```cpp
// Control 8 digital outputs from 1 byte
static const ParamMapping SWITCH_BANK_PARAMS[] PROGMEM = {
    {0, 0, 1, PARAM_UINT8, 0, 1, "switch1"},  // Bit 0
    {0, 1, 1, PARAM_UINT8, 0, 1, "switch2"},  // Bit 1
    {0, 2, 1, PARAM_UINT8, 0, 1, "switch3"},  // Bit 2
    {0, 3, 1, PARAM_UINT8, 0, 1, "switch4"},  // Bit 3
    {0, 4, 1, PARAM_UINT8, 0, 1, "switch5"},  // Bit 4
    {0, 5, 1, PARAM_UINT8, 0, 1, "switch6"},  // Bit 5
    {0, 6, 1, PARAM_UINT8, 0, 1, "switch7"},  // Bit 6
    {0, 7, 1, PARAM_UINT8, 0, 1, "switch8"}   // Bit 7
};

static const ActionDefinition SWITCH_BANK_DEF PROGMEM = {
    .action = ACTION_GPIO_BANK_SET,
    .name = "GPIO_BANK",
    .description = "Control 8 GPIO pins from bit field",
    .param_count = 8,
    .param_map = SWITCH_BANK_PARAMS
};
```

**CAN Message Format:**
```
CAN ID: 0x503
Data:   [Bitfield, 0, 0, 0, 0, 0, 0, 0]
Example: 0x503: [0b10101010, 0, ...]  -> Switches 2,4,6,8 ON, others OFF
```

---

## UI Discovery Protocol

### Compact JSON Format (IMPLEMENTED ✅)

**Decision:** JSON is THE format used in Protocol v2.0. No alternative formats are supported.

**Rationale:** SAMD51/RP2040/ESP32 have sufficient RAM for JSON serialization. Compact field names minimize bandwidth.

**Protocol Command:**
```
get:actiondef:<ACTION_TYPE>
```

**Response Format:**
```
ACTIONDEF;{"i":1,"n":"NEOPIXEL","d":"Control RGB LED","p":[{"n":"r","t":0,"r":"0-255"},{"n":"g","t":0,"r":"0-255"},{"n":"b","t":0,"r":"0-255"},{"n":"br","t":0,"r":"0-255"}]}
```

**JSON Structure:**
```json
{
  "i": 1,                      // Action ID (enum value)
  "n": "NEOPIXEL",             // Name
  "d": "Control RGB LED",      // Description
  "p": [                       // Parameters array
    {
      "n": "r",                // Parameter name
      "t": 0,                  // Type (0=uint8, 1=uint16, 2=uint32, etc.)
      "b": 0,                  // Data byte index
      "o": 0,                  // Bit offset
      "l": 8,                  // Bit length
      "r": "0-255"             // Range (min-max)
    },
    {
      "n": "g",
      "t": 0,
      "b": 1,
      "o": 0,
      "l": 8,
      "r": "0-255"
    },
    // ... more parameters
  ]
}
```

**Bandwidth Analysis:**
- Typical action: ~150-300 bytes
- All actions (10-20 types): 1.5-6KB total
- One-time query at startup
- **Verdict:** Acceptable for 115200 baud (13ms - 52ms total)

**Benefits:**
- Self-documenting protocol
- Easy UI parsing
- Future extensible
- Standard format (no custom parsers needed)
- RAM is not a constraint on target platforms

**Alternative Considered (REJECTED):**
An enumerated protocol format was considered for bandwidth reduction (~100 bytes per action vs ~200 bytes for JSON), but was rejected for lack of self-documentation and difficulty extending.

---

## Protocol Extensions (PROTOCOL.md)

### New Commands

#### Get Action Definition

**Command:**
```
get:actiondef:<ACTION_TYPE>
```

**Response:**
```
ACTIONDEF;{JSON}
```

**Example:**
```
< get:actiondef:NEOPIXEL
> ACTIONDEF;{"i":1,"n":"NEOPIXEL","d":"Control RGB LED","p":[...]}
```

#### Get All Action Definitions

**Command:**
```
get:actiondefs
```

**Response (multiple lines):**
```
ACTIONDEF;{JSON_ACTION_1}
ACTIONDEF;{JSON_ACTION_2}
...
```

#### Add Rule with CAN Data Parameters

**Format:**
```
action:add:<RULE_ID>:<CAN_ID>:<CAN_MASK>:<DATA>:<DATA_MASK>:<DATA_LEN>:<ACTION_TYPE>:<PARAM_SOURCE>:<PARAMS>
```

**Fields:**
- `PARAM_SOURCE`: `fixed` or `candata`

**Examples:**

**Fixed parameters (backward compatible):**
```
action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL_COLOR:fixed:255:0:0:128
```

**CAN data parameters:**
```
action:add:0:0x500:0xFFFFFFFF:::4:NEOPIXEL_COLOR:candata
                                │                  └─ Use CAN data bytes
                                └─ Data length = 4 bytes minimum
```

**Multi-servo example:**
```
action:add:0:0x502:0xFFFFFFFF:::8:MULTI_SERVO:candata
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

**Files to Create/Modify:**

1. **src/actions/param_mapping.h** (NEW)
   - Define `ParamSource`, `ParamMapping`, `ActionDefinition`
   - Define extraction functions (`extract_uint8`, etc.)
   - Define action definition registry

2. **src/actions/action_types.h** (MODIFY)
   - Add `ParamSource` enum
   - Add new action types (MULTI_SERVO, GPIO_BANK, etc.)

3. **src/actions/action_manager_base.h** (MODIFY)
   - Add `ParamSource param_source` to `ActionRule`
   - Add `uint8_t param_data_offset` to `ActionRule`
   - Add `const ActionDefinition* get_action_definition(ActionType)` method

4. **src/actions/action_manager_base.cpp** (MODIFY)
   - Update `execute_action()` to check `param_source`
   - Add parameter extraction logic
   - Update `parse_and_add_rule()` to parse `PARAM_SOURCE` field

**Deliverable:** Core parameter mapping system compiles and passes unit tests.

### Phase 2: Platform Action Definitions (Week 2)

**Files to Create:**

1. **src/capabilities/samd51/samd51_action_defs.cpp** (NEW)
   - Define SAMD51-specific action parameter mappings
   - Include: NeoPixel, PWM, DAC, ADC, GPIO bank
   - Register action definitions in Flash

2. **src/capabilities/rp2040/rp2040_action_defs.cpp** (NEW)
   - Define RP2040-specific action mappings
   - Include: PWM, GPIO bank, ADC, onboard LED

3. **src/capabilities/samd51/samd51_action_manager.cpp** (MODIFY)
   - Update action execution to support CAN data parameters
   - Register platform action definitions

**Deliverable:** Platform-specific actions defined and discoverable.

### Phase 3: Protocol Extensions (Week 3)

**Files to Modify:**

1. **can_tui/PROTOCOL.md** (MODIFY)
   - Document new `ACTIONDEF` response format
   - Document `get:actiondef` command
   - Document updated `action:add` syntax with `PARAM_SOURCE`

2. **src/main.cpp** (MODIFY)
   - Add command handling for `get:actiondef`
   - Add command handling for `get:actiondefs`
   - Implement JSON serialization for action definitions

**Deliverable:** Protocol extensions documented and implemented.

### Phase 4: TUI Integration (Week 4)

**Files to Create/Modify:**

1. **can_tui/models/action_definition.py** (NEW)
   - Python dataclass for `ActionDefinition`
   - JSON parsing from `ACTIONDEF` responses

2. **can_tui/services/action_discovery.py** (NEW)
   - Query board for action definitions at startup
   - Cache action definitions for UI form generation

3. **can_tui/widgets/action_rule_form.py** (MODIFY)
   - Generate form fields from `ActionDefinition`
   - Support both fixed and CAN data parameter modes
   - Add "Use CAN Data" checkbox

**Deliverable:** TUI can discover actions and generate forms dynamically.

### Phase 5: Testing and Examples (Week 5)

**Files to Create:**

1. **examples/neopixel_can_control/** (NEW)
   - Example: Control NeoPixel via CAN data
   - Python script to send CAN messages with RGB values

2. **examples/multi_servo_control/** (NEW)
   - Example: Control 4 servos from one CAN message
   - Demonstrates choreographed motion

3. **tests/test_param_extraction.cpp** (NEW)
   - Unit tests for parameter extraction functions
   - Test bit-packed data extraction
   - Test boundary conditions

**Deliverable:** Working examples and comprehensive tests.

---

## Memory Analysis

### Per-Rule Overhead

**Current `ActionRule` size:** ~70 bytes

**New fields:**
- `param_source`: 1 byte
- `param_data_offset`: 1 byte

**New size:** ~72 bytes (+2.9%)

**Impact:**

| Platform | Max Rules | Current RAM | New RAM | Increase |
|----------|-----------|-------------|---------|----------|
| RP2040   | 16        | 1,120 bytes | 1,152 bytes | +32 bytes |
| SAMD51   | 64        | 4,480 bytes | 4,608 bytes | +128 bytes |
| ESP32    | 32        | 2,240 bytes | 2,304 bytes | +64 bytes |

**Conclusion:** Negligible impact (<0.1% of total RAM).

### Flash Overhead

**Action definitions:** ~100-200 bytes per action type (stored in Flash)

**Extraction functions:** ~200 bytes total (inlined, minimal overhead)

**Estimated total:** 1-2KB Flash

**Conclusion:** Acceptable (<1% of Flash on all platforms).

---

## Backward Compatibility

### Existing Rules Continue to Work

**Default behavior:** If `param_source` is not specified, defaults to `PARAM_FROM_RULE`.

**Migration:** No action required. Old rules work as-is.

### Protocol Compatibility

**Old TUI + New Firmware:** TUI doesn't need to know about action definitions. Old commands work.

**New TUI + Old Firmware:** New TUI falls back to manual parameter entry if action definitions not available.

---

## Advanced Use Cases

### 1. Racing Dashboard

**Scenario:** Racing car with central CAN bus. Dashboard displays RPM, speed, gear. Control shift light LEDs directly from ECU CAN messages.

**CAN Message:**
```
ID: 0x600 (Engine Status)
Data: [RPM_HIGH, RPM_LOW, Speed, Gear, Temp, Throttle, 0, 0]
```

**Action Rule:**
```cpp
// Extract RPM (16-bit) and control NeoPixel shift light
action:add:0:0x600:0xFFFFFFFF:::6:NEOPIXEL_RPM_INDICATOR:candata
```

**Implementation:** Custom action extracts RPM, calculates color gradient (green→yellow→red).

### 2. Proportional Valve Control

**Scenario:** Industrial hydraulic system. CAN message from PLC contains valve position (12-bit) and flow rate (12-bit) packed into 3 bytes.

**CAN Message:**
```
ID: 0x701
Data: [Valve_High:Valve_Low:Flow_High, Flow_Low, 0, 0, 0, 0]
Valve: bits 0-11 (0-4095)
Flow:  bits 12-23 (0-4095)
```

**Action Definition:**
```cpp
static const ParamMapping VALVE_PARAMS[] PROGMEM = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "valve_low"},   // Byte 0
    {1, 0, 4, PARAM_UINT8, 0, 15, "valve_high"},   // Byte 1, bits 0-3
    {1, 4, 4, PARAM_UINT8, 0, 15, "flow_low"},     // Byte 1, bits 4-7
    {2, 0, 8, PARAM_UINT8, 0, 255, "flow_high"}    // Byte 2
};
```

**Extraction:**
```cpp
uint16_t valve = (data[1] & 0x0F) << 8 | data[0];  // 12-bit value
uint16_t flow = data[2] << 4 | (data[1] >> 4);      // 12-bit value
```

### 3. IMU-Driven Servo Stabilization

**Scenario:** Drone gimbal. IMU sends pitch/roll/yaw (6 bytes). Servos correct in real-time.

**CAN Message:**
```
ID: 0x800 (IMU Data)
Data: [Pitch_H, Pitch_L, Roll_H, Roll_L, Yaw_H, Yaw_L, 0, 0]
```

**Action:** Extract 16-bit signed angles, drive 3 servos for stabilization.

---

## Security Considerations

### Input Validation

**Risk:** Malicious CAN messages could send out-of-range values.

**Mitigation:**
1. **Range clamping** in extraction functions (already implemented)
2. **Platform-specific validation** in `execute_*_action()` methods
3. **Configurable per-rule validation** (future enhancement)

### CAN Bus Access Control

**Risk:** Any device on CAN bus can trigger actions.

**Mitigation:**
1. **CAN ID filtering** - Only respond to specific IDs
2. **Data pattern matching** - Require specific data signatures
3. **Enable/disable rules** - Disable untrusted rules at runtime

---

## Performance Benchmarks (Estimated)

| Operation | CPU Cycles | Time @ 120MHz | Time @ 240MHz |
|-----------|------------|---------------|---------------|
| Rule matching | 50-100 | 0.4-0.8 µs | 0.2-0.4 µs |
| extract_uint8 | 5-10 | 0.04-0.08 µs | 0.02-0.04 µs |
| extract_uint16 | 8-12 | 0.07-0.1 µs | 0.03-0.05 µs |
| NeoPixel update | 2000-3000 | 17-25 µs | 8-12 µs |
| PWM update | 100-200 | 0.8-1.7 µs | 0.4-0.8 µs |

**Conclusion:** Parameter extraction overhead is negligible (<1 µs).

---

## Alternative Designs Considered

### Alternative 1: Callback Functions

**Approach:** Store function pointers in rules that extract parameters.

**Pros:**
- Maximum flexibility
- Easy to add custom extractors

**Cons:**
- Function pointers consume 4 bytes each
- Call overhead (~10-20 cycles)
- Harder to serialize for persistence

**Verdict:** Rejected due to RAM overhead.

### Alternative 2: Scripting Engine

**Approach:** Embed Lua/Wren interpreter for custom parameter extraction.

**Pros:**
- Ultimate flexibility
- User-programmable without firmware updates

**Cons:**
- Large Flash footprint (50-100KB)
- RAM overhead (10-20KB)
- Complexity

**Verdict:** Rejected for embedded constraints. Could be future enhancement for ESP32.

### Alternative 3: Fixed-Size Mapping Table

**Approach:** Pre-define 256 possible mappings in ROM. Rules reference by index.

**Pros:**
- Zero per-rule overhead
- Fast lookup

**Cons:**
- Inflexible
- Wastes Flash space
- Doesn't scale

**Verdict:** Rejected for lack of extensibility.

---

## Future Enhancements

### 1. Conditional Actions

Execute action only if extracted parameter meets condition:

```cpp
struct ActionCondition {
    uint8_t param_index;        // Which parameter to check
    ComparisonOp op;            // ==, !=, <, >, <=, >=
    uint32_t threshold;         // Comparison value
};

// Example: Only set NeoPixel if brightness > 50
rule.condition.param_index = 3;  // Brightness parameter
rule.condition.op = GREATER_THAN;
rule.condition.threshold = 50;
```

### 2. Parameter Transformation

Apply math operations before using parameter:

```cpp
enum TransformOp {
    TRANSFORM_NONE,
    TRANSFORM_SCALE,      // param = param * scale / 256
    TRANSFORM_OFFSET,     // param = param + offset
    TRANSFORM_LINEAR,     // param = (param * a) + b
    TRANSFORM_LOOKUP      // param = lookup_table[param]
};

// Example: Convert 0-255 to servo angle (0-180)
ParamTransform transform = {
    .op = TRANSFORM_SCALE,
    .scale = 180,
    .divisor = 255
};
```

### 3. Multi-Message Actions

Combine parameters from multiple CAN messages:

```cpp
// Wait for both 0x600 and 0x601, then execute
rule.trigger_mode = TRIGGER_MULTI_MESSAGE;
rule.message_ids = {0x600, 0x601};
rule.timeout_ms = 100;  // Invalidate if messages too far apart
```

### 4. Action Chaining

Execute multiple actions in sequence:

```cpp
rule.action_chain = {
    ACTION_GPIO_SET,
    ACTION_DELAY_MS,
    ACTION_NEOPIXEL_COLOR,
    ACTION_CAN_SEND
};
```

---

## Conclusion

This design provides a **memory-efficient, fast, and extensible** system for CAN data-driven actions. The 2-byte per-rule overhead is negligible, while the Flash-based action definitions enable powerful UI discovery and dynamic parameter mapping.

**Key Benefits:**
- Single CAN message controls complex hardware directly
- Scales from simple (1 LED) to complex (8 servos) without firmware changes
- UI automatically generates forms for any action type
- Backward compatible with existing rules
- Minimal performance impact (<1 µs parameter extraction)

**Next Steps:**
1. Review and approve design
2. Implement Phase 1 (Core Infrastructure)
3. Test on SAMD51 Feather M4 CAN
4. Extend to RP2040 and ESP32
5. Update TUI for action discovery

---

**End of Design Document**

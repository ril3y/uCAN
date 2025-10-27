# Multi-Step Actions & Data Buffer System Design

**Date:** 2025-01-27
**Status:** Design Proposal - Phase 1 Implementation Plan
**Context:** Addressing limitations in current 1-to-1 rule system + data storage

---

## Problem Statement

### Current Limitations

**Current Architecture:**
- Each rule = 1 CAN ID → 1 action
- No action chaining or sequencing
- No data storage between actions
- No way to collect multiple sensor readings and send in one CAN message

**What Users Need:**

**Example 1: Multi-Sensor Collection**
```
CAN 0x500 arrives →
  1. Read GPIO pin 13 → store in buffer[0]
  2. Read ADC A0 (temperature) → store in buffer[1:2] (16-bit)
  3. Read I2C accelerometer (3 bytes) → store in buffer[3:5]
  4. Send buffer as CAN 0x600
```

**Example 2: PWM Control**
- Current PWM action only has: pin, duty cycle (0-255)
- Missing: frequency control, resolution configuration
- Must be abstract base class (platform-agnostic)

**Example 3: I2C Communication**
- I2C capability missing from capabilities enum (bug!)
- Hardware supports I2C but not exposed
- Must be abstract base class with per-platform pin validation

---

## Current System Analysis

### What Works Well

1. **Action Definitions** - Self-describing via `get:actiondefs`
2. **CAN Data Extraction** - `candata` mode allows dynamic parameter extraction
3. **Custom Commands** - Platform-specific extensibility already exists!

### What's Missing

1. **I2C Support** - Not defined in capabilities enum
2. **PWM Frequency Control** - Only duty cycle supported
3. **Action Chaining** - No way to execute multiple actions from one trigger
4. **Data Flow** - Can't pass action outputs to next action
5. **Conditional Logic** - No if/then/else support

---

## Core Innovation: Action Data Buffer

**The Key Insight:**
Instead of specific "READ_SEND" actions, create a generic 8-byte data buffer that actions can READ into and SEND from.

### Data Buffer Architecture

```cpp
// Global action data buffer (matches CAN message size)
class ActionDataBuffer {
private:
    uint8_t buffer_[8];
    bool slot_used_[8];  // Track which bytes are valid

public:
    // Write data to buffer slot
    bool write(uint8_t slot, const uint8_t* data, uint8_t length) {
        if (slot + length > 8) return false;
        memcpy(&buffer_[slot], data, length);
        for (uint8_t i = 0; i < length; i++) {
            slot_used_[slot + i] = true;
        }
        return true;
    }

    // Read entire buffer for sending
    const uint8_t* read_all(uint8_t& valid_length) {
        // Find highest used slot
        valid_length = 0;
        for (uint8_t i = 7; i >= 0 && i < 255; i--) {
            if (slot_used_[i]) {
                valid_length = i + 1;
                break;
            }
        }
        return buffer_;
    }

    // Clear buffer
    void clear() {
        memset(buffer_, 0, 8);
        memset(slot_used_, 0, 8);
    }
};

// Global instance
ActionDataBuffer action_buffer;
```

**Benefits:**
- ✅ Generic: Works for GPIO, ADC, I2C, any sensor
- ✅ Flexible: Can pack multiple values in one CAN message
- ✅ Efficient: No redundant CAN sends
- ✅ Simple: Just slot index + data

**Example Usage:**
```cpp
// Action 1: Read GPIO → buffer[0]
action_buffer.write(0, &gpio_value, 1);

// Action 2: Read ADC → buffer[1:2]
uint16_t adc_value = analogRead(A0);
action_buffer.write(1, (uint8_t*)&adc_value, 2);

// Action 3: Read I2C → buffer[3:5]
uint8_t i2c_data[3];
read_i2c(0x50, 0x00, i2c_data, 3);
action_buffer.write(3, i2c_data, 3);

// Action 4: Send buffer
can_interface->send_message(0x600, action_buffer.read_all(len), len);
```

---

## Solution: Four-Tier Approach (Revised)

### Tier 0: Data Buffer System (FOUNDATION)

**Implement action data buffer as core infrastructure:**
- Global 8-byte buffer for inter-action data storage
- Slot-based addressing (0-7)
- Actions can READ into buffer or SEND from buffer
- Automatic buffer clearing after send

### Tier 1: Abstract Base Classes + Missing Actions (Immediate)

**Create abstract interfaces for common peripherals:**

#### Abstract I2C Interface (Platform-Agnostic)

```cpp
// src/hal/i2c_interface.h
class I2CInterface {
public:
    virtual ~I2CInterface() {}

    // Initialize I2C with specific pins
    virtual bool initialize(uint8_t sda_pin, uint8_t scl_pin, uint32_t frequency_hz = 100000) = 0;

    // Write data to I2C device
    virtual bool write(uint8_t address, uint8_t reg, const uint8_t* data, uint8_t length) = 0;

    // Read data from I2C device
    virtual bool read(uint8_t address, uint8_t reg, uint8_t* data, uint8_t length) = 0;

    // Validate if pin can be used for I2C
    virtual bool is_valid_sda_pin(uint8_t pin) const = 0;
    virtual bool is_valid_scl_pin(uint8_t pin) const = 0;

    // Get error string
    virtual const char* get_last_error() const = 0;
};

// Platform-specific implementation
// src/hal/samd51_i2c.h
class SAMD51_I2C : public I2CInterface {
    // Implements SERCOM-based I2C with pin validation
};
```

**New Buffer-Based Actions:**
```cpp
ACTION_I2C_WRITE        // Write data to I2C device
  - sda_pin (uint8, 0-255, action_param)        ← NEW: configurable pins
  - scl_pin (uint8, 0-255, action_param)        ← NEW: configurable pins
  - i2c_address (uint8, 0-127, action_param)
  - register_addr (uint8, 0-255, action_param)
  - data (uint8[], from CAN or fixed)

ACTION_I2C_READ_BUFFER  // Read from I2C → store in action buffer
  - sda_pin (uint8, action_param)
  - scl_pin (uint8, action_param)
  - i2c_address (uint8, action_param)
  - register_addr (uint8, action_param)
  - num_bytes (uint8, action_param)
  - buffer_slot (uint8, output_param)  ← NEW: where in buffer to store
```

#### Abstract PWM Interface (Platform-Agnostic)

```cpp
// src/hal/pwm_interface.h
class PWMInterface {
public:
    virtual ~PWMInterface() {}

    // Configure PWM on pin
    virtual bool configure(uint8_t pin, uint32_t frequency_hz, uint8_t duty_percent, uint8_t resolution_bits = 8) = 0;

    // Set duty cycle only (keep frequency)
    virtual bool set_duty(uint8_t pin, uint8_t duty_percent) = 0;

    // Stop PWM
    virtual bool stop(uint8_t pin) = 0;

    // Validate if pin supports PWM
    virtual bool is_valid_pwm_pin(uint8_t pin) const = 0;

    // Get current configuration
    virtual bool get_config(uint8_t pin, uint32_t& freq, uint8_t& duty) const = 0;
};

// Platform-specific implementation
// src/hal/samd51_pwm.h
class SAMD51_PWM : public PWMInterface {
    // Implements TCC-based PWM with pin validation
};
```

**Enhanced PWM Actions:**
```cpp
ACTION_PWM_CONFIGURE  // Full PWM configuration
  - pin (uint8, action_param)
  - frequency_hz (uint16, action_param) ← NEW!
  - duty_percent (uint8, 0-100, action_param)
  - resolution_bits (uint8, 8/10/12/16, action_param) ← NEW!

ACTION_PWM_SET        // Just change duty cycle (keep frequency)
  - pin (uint8, action_param)
  - duty_percent (uint8, 0-100, action_param)
```

#### Buffer-Based Read Actions (Replaces Specific READ_SEND)

```cpp
ACTION_GPIO_READ_BUFFER  // Read GPIO → store in buffer
  - pin (uint8, action_param)
  - buffer_slot (uint8, output_param) ← which byte in buffer

ACTION_ADC_READ_BUFFER   // Read ADC → store in buffer
  - pin (uint8, action_param)
  - buffer_slot (uint8, output_param) ← 16-bit value uses 2 bytes

ACTION_BUFFER_SEND       // Send buffer contents as CAN message
  - can_id (uint32, output_param)
  - length (uint8, output_param) ← how many bytes to send
  - clear_after (bool, output_param) ← clear buffer after send
```

**Benefits:**
- ✅ Solves I2C and PWM limitations
- ✅ Uses existing action system
- ✅ UI can discover via `get:actiondefs`
- ✅ No breaking changes

**Limitations:**
- ❌ Still 1-to-1 rules
- ❌ No multi-step sequences

---

### Tier 2: Action Chaining (Medium-term)

**Add rule chaining for sequential execution:**

```cpp
struct ActionRule {
    uint8_t rule_id;
    uint32_t can_id;
    uint32_t can_mask;
    ActionType action;
    uint8_t params[8];
    uint8_t next_rule_id;      // NEW: Execute this rule after current action
    uint16_t chain_delay_ms;   // NEW: Wait this long before next action
};
```

**Protocol Extension:**
```
action:add:{RULE_ID}:{CAN_ID}:{MASK}::::{ACTION}:{PARAM_SOURCE}:{PARAMS}:{NEXT_RULE_ID}:{DELAY_MS}
                                                                           ^^^^^^^^^^^^^^ ^^^^^^^^
                                                                           NEW fields
```

**Example: Chain 3 Actions**
```
# Rule 1: Set NeoPixel blue (then chain to rule 2)
action:add:1:0x500:0xFFFFFFFF:::0:NEOPIXEL:fixed:0:0:255:255:2:10

# Rule 2: Set PWM from CAN data (then chain to rule 3)
action:add:2:0x500:0xFFFFFFFF:::0:PWM_CONFIGURE:candata:3:0

# Rule 3: Read GPIO and send response (no chain)
action:add:3:0x500:0xFFFFFFFF:::0:GPIO_READ_SEND:fixed:13:0x600:0:0

# Result: One CAN message triggers all 3 actions in sequence
```

**Benefits:**
- ✅ Solves your exact use case
- ✅ Simple firmware implementation
- ✅ UI can show flowchart of chains
- ✅ Backward compatible (next_rule_id=0 means no chain)

**Limitations:**
- ❌ Only linear sequences (A→B→C, no branching)
- ❌ Can't pass data between actions (yet)
- ❌ No conditional execution

---

### Tier 3: Custom Command Sequences (Advanced)

**Use existing Custom Command system for complex logic:**

The firmware ALREADY has a `CustomCommand` system that allows platform-specific commands with arbitrary logic!

**Example Custom Command: Complex Sequence**
```cpp
class MultiStepCommand : public CustomCommand {
public:
    const char* get_name() const override { return "sequence"; }
    const char* get_description() const override {
        return "Execute multi-step action sequence";
    }

    bool execute(const char* params) override {
        // Parse params: "neopixel:0,0,255,255;pwm:13,1000,50;gpio_read:13,0x600"

        // Execute sequence:
        set_neopixel(0, 0, 255, 255);  // Blue
        delay(10);
        set_pwm_freq(13, 1000, 50);    // Pin 13, 1kHz, 50%
        delay(10);
        uint8_t pin_state = read_gpio(13);
        send_can_response(0x600, &pin_state, 1);

        return true;
    }
};
```

**Protocol Usage:**
```
# Register sequence as rule trigger
action:add:1:0x500:0xFFFFFFFF:::0:CUSTOM_COMMAND:fixed:sequence:neopixel:0,0,255,255;pwm:13,1000,50;gpio_read:13,0x600

# Or execute directly via command
custom:sequence:neopixel:0,0,255,255;pwm:13,1000,50;gpio_read:13,0x600
```

**Benefits:**
- ✅ Maximum flexibility - arbitrary C++ code
- ✅ Can implement ANY logic (loops, conditions, state machines)
- ✅ Can pass data between steps via local variables
- ✅ Platform-specific optimizations
- ✅ Uses existing infrastructure (`get:commands`)

**Limitations:**
- ❌ Requires firmware programming for new sequences
- ❌ Not discoverable like action definitions
- ❌ More complex for UI developers

---

## Recommendation: Hybrid Approach

**Phase 1 (Now):**
1. Add I2C capability flag
2. Create I2C action definitions
3. Enhance PWM action with frequency parameter
4. Add GPIO_READ_SEND action

**Phase 2 (Next Sprint):**
1. Implement action chaining (next_rule_id)
2. Update protocol docs
3. Add UI support for chain visualization

**Phase 3 (Future):**
1. Expand custom commands for platform-specific sequences
2. Add scripting engine for user-defined sequences (optional)

---

## Action Definition Examples

### I2C Write Action (Proposed)

```json
{
  "i": 20,
  "n": "I2C_WRITE",
  "d": "Write data to I2C device",
  "c": "Communication",
  "trig": "can_msg",
  "p": [
    {
      "n": "i2c_addr",
      "t": 0,
      "b": 0,
      "o": 0,
      "l": 7,
      "r": "0-127",
      "role": "action_param"
    },
    {
      "n": "reg_addr",
      "t": 0,
      "b": 1,
      "o": 0,
      "l": 8,
      "r": "0-255",
      "role": "action_param"
    },
    {
      "n": "data",
      "t": 0,
      "b": 2,
      "o": 0,
      "l": 8,
      "r": "0-255",
      "role": "action_param"
    }
  ]
}
```

**Usage:**
```
# Write value 0x42 to register 0x10 of I2C device at address 0x50
action:add:0:0x500:0xFFFFFFFF:::0:I2C_WRITE:candata

# Send CAN message: 0x500:[50, 10, 42]
send:0x500:50,10,42
```

### Enhanced PWM Action (Proposed)

```json
{
  "i": 21,
  "n": "PWM_CONFIGURE",
  "d": "Configure PWM with frequency and duty cycle",
  "c": "GPIO",
  "trig": "can_msg",
  "p": [
    {
      "n": "pin",
      "t": 0,
      "b": 0,
      "o": 0,
      "l": 8,
      "r": "0-255",
      "role": "action_param"
    },
    {
      "n": "freq_hz",
      "t": 1,
      "b": 1,
      "o": 0,
      "l": 16,
      "r": "1-20000",
      "role": "action_param"
    },
    {
      "n": "duty_percent",
      "t": 0,
      "b": 3,
      "o": 0,
      "l": 8,
      "r": "0-100",
      "role": "action_param"
    }
  ]
}
```

**Usage:**
```
# Set pin 13 to 1kHz @ 50% duty cycle
# CAN data: [13, 0xE8, 0x03, 50]  (freq = 0x03E8 = 1000 Hz)
send:0x500:0D,E8,03,32
```

---

## UI Considerations

### For Simple Actions (Current System)
- ✅ UI already works
- ✅ `get:actiondefs` provides all needed info
- ✅ Form builder can generate UI dynamically

### For Chained Actions (Tier 2)
**UI Should:**
1. Show flowchart view of chained rules
2. Allow drag-and-drop action ordering
3. Display delay between steps
4. Warn if chain creates loops

**Example UI:**
```
┌──────────────┐
│ CAN 0x500    │
│ Trigger      │
└──────┬───────┘
       │
       ▼
┌────────────────┐
│ NeoPixel Blue  │  [10ms delay]
└──────┬─────────┘
       │
       ▼
┌────────────────┐
│ PWM from Data  │  [0ms delay]
└──────┬─────────┘
       │
       ▼
┌────────────────┐
│ Read GPIO 13   │
│ Send → 0x600   │
└────────────────┘
```

### For Custom Commands (Tier 3)
**UI Should:**
1. Query `get:commands` for available custom commands
2. Generate forms based on parameter definitions
3. Show command category and description
4. Provide syntax help for complex parameters

---

## Implementation Priority

### HIGH PRIORITY (Do Now)
- [ ] Add `CAP_I2C` to capability flags
- [ ] Create I2C action definitions
- [ ] Add frequency parameter to PWM action
- [ ] Document new actions in PROTOCOL.md

### MEDIUM PRIORITY (Next)
- [ ] Implement action chaining (next_rule_id)
- [ ] Add chain delay support
- [ ] Update protocol for chain commands
- [ ] Add chain visualization to docs

### LOW PRIORITY (Future)
- [ ] Expand custom command examples
- [ ] Create scripting/macro system
- [ ] Add conditional execution
- [ ] Implement data passing between actions

---

## Open Questions for Discussion

1. **Chain Cycle Detection:** Should firmware detect infinite loops (A→B→A)?
2. **Parameter Passing:** How to pass action outputs to next action in chain?
3. **Error Handling:** If action 2 fails in chain, should action 3 still execute?
4. **Memory Limits:** How many chained actions before we run out of RAM?
5. **UI Complexity:** Should UI hide chaining for simple users, show for advanced?

---

## Backwards Compatibility

All proposed changes maintain backwards compatibility:

- ✅ Existing rules continue to work
- ✅ `next_rule_id=0` means "no chain" (default)
- ✅ New actions have new IDs, don't conflict with existing
- ✅ Protocol extends with optional fields at end

---

## Next Steps

1. Review this design with team
2. Decide on Phase 1 action additions (I2C, PWM freq)
3. Prototype action chaining firmware
4. Update protocol documentation
5. Create UI mockups for chain visualization

**Questions? Feedback?** Comment on this document or discuss in next meeting.

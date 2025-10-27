# Phase 1 Implementation - Executive Summary

**Date:** 2025-01-27
**Status:** Ready for Implementation
**Target:** Production-ready multi-sensor data collection system

---

## What We're Building

### Core Innovation: Data Buffer System

Instead of separate "read and send" actions for each sensor type, we're creating a **generic 8-byte data buffer** that actions can write to and read from.

**Example Use Case:**
```
Rule 1: Read GPIO pin 13 → buffer[0]
Rule 2: Read ADC A0 → buffer[1:2]
Rule 3: Read I2C accelerometer → buffer[3:5]
Rule 4: Send buffer as CAN message 0x600
```

**Result:** One CAN message with data from 3 different sensors!

---

## Key Problems We're Solving

### 1. ❌ I2C Missing Entirely (Bug!)
- Hardware supports I2C
- Not in capabilities enum
- No actions defined

**FIX:** Add `CAP_I2C` + abstract interface + SAMD51 implementation

### 2. ❌ PWM Limited (Only Duty Cycle)
- Current: Only pin + duty cycle
- Missing: Frequency control, resolution

**FIX:** Add `PWM_CONFIGURE` action with frequency parameter

### 3. ❌ No Multi-Sensor Data Collection
- Current: Can't combine readings from multiple sources
- Want: Read 3 sensors → send all in 1 CAN message

**FIX:** ActionDataBuffer + buffer-based read actions

### 4. ❌ No Pin Validation
- Can accidentally use CAN pins, USB pins
- No error messages when invalid pins used
- Pin conflicts not detected

**FIX:** Pin capability database + PinManager + error logging

---

## Architecture: Abstract Base Classes

### Why Abstract Interfaces?

**Problem:** Each platform (SAMD51, RP2040, ESP32, STM32) has different I2C/PWM implementations

**Solution:** Define abstract interface, each platform implements specifics

**Benefits:**
- ✅ Core action logic is platform-agnostic
- ✅ Easy to add new platforms
- ✅ Pin validation is platform-specific
- ✅ Error handling is consistent

### I2C Interface Example

```cpp
// Abstract (platform-agnostic)
class I2CInterface {
    virtual bool initialize(uint8_t sda, uint8_t scl, uint32_t freq) = 0;
    virtual bool write(uint8_t addr, uint8_t reg, const uint8_t* data, uint8_t len) = 0;
    virtual bool read(uint8_t addr, uint8_t reg, uint8_t* data, uint8_t len) = 0;
    virtual bool is_valid_sda_pin(uint8_t pin) const = 0;  // Platform-specific!
};

// SAMD51-specific implementation
class SAMD51_I2C : public I2CInterface {
    // Uses SERCOM modules
    // Validates pins against SERCOM capability table
    // Logs errors to Serial
};

// RP2040 implementation (future)
class RP2040_I2C : public I2CInterface {
    // Uses hardware I2C peripheral
    // Different pin validation rules
};
```

---

## New Actions Summary

### Buffer-Based Read Actions

| Action | Purpose | Parameters |
|--------|---------|------------|
| `GPIO_READ_BUFFER` | Read digital pin → buffer | pin, buffer_slot |
| `ADC_READ_BUFFER` | Read analog pin → buffer | pin, buffer_slot |
| `I2C_READ_BUFFER` | Read I2C device → buffer | sda, scl, addr, reg, num_bytes, buffer_slot |

### Buffer Management

| Action | Purpose | Parameters |
|--------|---------|------------|
| `BUFFER_SEND` | Send buffer as CAN message | can_id, length, clear_after |
| `BUFFER_CLEAR` | Clear buffer manually | (none) |

### Enhanced Peripherals

| Action | Purpose | Parameters |
|--------|---------|------------|
| `PWM_CONFIGURE` | PWM with frequency control | pin, freq_hz, duty_percent, resolution |
| `I2C_WRITE` | Write to I2C device | sda, scl, addr, reg, data |

---

## Pin Validation System

### SAMD51 Pin Limitations

**Reserved (Cannot Use):**
- PA22, PA23: CAN TX/RX (hardwired to transceiver)
- PA24, PA25, PA27, PA28: USB (system use)

**I2C Pins:**
- Default: PA12 (SDA), PA13 (SCL) - SERCOM2
- Alternatives: Many pins via other SERCOM modules
- **Conflict:** Default I2C and SPI share same SERCOM!

**PWM Pins:**
- Most digital pins via TCC0/1/2
- Pins on same TCC channel share frequency

**ADC Pins:**
- Only A0, A1, A2, A3, A4, A5

### Error Logging

All pin validation errors go to Serial:

```
[PIN_ERROR] Pin 22: Cannot use CAN TX pin for GPIO
[PIN_ERROR] Pin 13: Pin already allocated for PWM
[PIN_WARNING] Pin A0: Shared between ADC and DAC
```

UI can parse these for user-friendly error messages.

---

## Example: Multi-Sensor Reading

### Scenario
Read 3 different sensors and send all data in one CAN message:
1. Digital switch on GPIO 13
2. Temperature from ADC A0 (10-bit → 2 bytes)
3. Accelerometer via I2C (3 axes → 3 bytes)

### Rules Configuration

```
# Rule 1: Read GPIO 13 → buffer[0]
action:add:1:0x500:0xFFFFFFFF:::0:GPIO_READ_BUFFER:candata
# CAN data: [13, 0] - pin 13, slot 0

# Rule 2: Read ADC A0 → buffer[1:2]
action:add:2:0x500:0xFFFFFFFF:::0:ADC_READ_BUFFER:candata
# CAN data: [A0, 1] - pin A0, slot 1 (uses 2 bytes)

# Rule 3: Read I2C accelerometer → buffer[3:5]
action:add:3:0x500:0xFFFFFFFF:::0:I2C_READ_BUFFER:candata
# CAN data: [PA12, PA13, 0x68, 0x3B, 3, 3]
# SDA, SCL, I2C addr, reg, 3 bytes, slot 3

# Rule 4: Send buffer as CAN 0x600
action:add:4:0x500:0xFFFFFFFF:::0:BUFFER_SEND:fixed:0x600:6:1
# Send CAN ID 0x600, 6 bytes, clear after
```

### CAN Data Layout

After all rules execute:

```
Buffer[0] = GPIO state (0 or 1)
Buffer[1:2] = ADC value (16-bit)
Buffer[3:5] = Accelerometer X,Y,Z (3 bytes)

CAN Message 0x600: [GPIO, ADC_L, ADC_H, ACC_X, ACC_Y, ACC_Z]
```

**ONE CAN message** contains data from **THREE sensors**!

---

## Example: Periodic Sensor Telemetry

### Scenario
Send sensor readings periodically (e.g., every 100ms) without requiring external CAN trigger.

**Use Case:** Autonomous data logging - read 8 GPIO pins and broadcast state every 100ms

### Rules Configuration

```
# Rule 1-8: Read GPIO pins 5-12 → buffer[0:7] (triggered by periodic timer)
action:add:1:0xFFFFFFFF:0x00000000:::0:GPIO_READ_BUFFER:fixed:5:0
action:add:2:0xFFFFFFFF:0x00000000:::0:GPIO_READ_BUFFER:fixed:6:1
action:add:3:0xFFFFFFFF:0x00000000:::0:GPIO_READ_BUFFER:fixed:7:2
# ... (repeat for pins 8-12 → buffer slots 3-7)

# Rule 9: Periodic send (100ms interval)
action:add:9:0xFFFFFFFF:0x00000000:::0:CAN_SEND_PERIODIC:fixed:0x700:8:100
# CAN ID 0x700, 8 bytes from buffer, 100ms interval
```

### How It Works

1. **CAN_SEND_PERIODIC** fires every 100ms (no CAN trigger needed)
2. Before sending, it executes GPIO_READ_BUFFER rules to populate buffer
3. Buffer data is sent as CAN ID 0x700

**Key Insight:** Buffer is shared state between actions!
- Read actions populate buffer
- Send actions transmit buffer contents
- Works with both CAN-triggered and periodic-triggered actions

**Phase 1 Requirement:** CAN_SEND_PERIODIC needs to read from ActionDataBuffer before sending

---

## Documentation Created

### 1. `SAMD51_PIN_REFERENCE.md`
Complete pin capability reference:
- Which pins support PWM, I2C, ADC, DAC
- Hardware reserved pins
- SERCOM and TCC mapping
- Pin conflict warnings
- Validation rules

### 2. `MULTI_STEP_ACTIONS_DESIGN.md`
Comprehensive design document:
- Data buffer architecture
- Abstract base class patterns
- Tier 0-3 implementation roadmap
- Action chaining (future)
- Custom commands (future)

### 3. `PHASE1_TODO.md`
Detailed implementation checklist:
- 50+ specific tasks
- Code examples for each component
- Test requirements
- 4-week implementation schedule
- Success criteria

### 4. `PHASE1_SUMMARY.md` (This Document)
Executive summary for quick reference

---

## Implementation Schedule

### Week 1: Foundation
- ActionDataBuffer class
- Pin capability database
- Pin manager
- Error logging system

### Week 2: HAL Interfaces
- I2C abstract interface + SAMD51 impl
- PWM abstract interface + SAMD51 impl
- Add I2C to capabilities

### Week 3: Actions
- PWM_CONFIGURE action
- I2C read/write actions
- Buffer read/send actions
- Action handlers in ActionManager

### Week 4: Testing & Polish
- Unit tests
- Integration tests
- Hardware validation
- Documentation updates

---

## Success Metrics

- ✅ All 27 existing tests still pass
- ✅ New actions appear in `get:actiondefs`
- ✅ Pin validation rejects invalid pins with clear errors
- ✅ Multi-sensor buffer collection works
- ✅ PWM frequency verified with oscilloscope
- ✅ I2C communication tested with real sensor
- ✅ Protocol documentation updated
- ✅ Zero breaking changes

---

## Key Design Decisions

### 1. Data Buffer Instead of Specific Actions
**Old Way:** `GPIO_READ_SEND`, `ADC_READ_SEND`, `I2C_READ_SEND`
**New Way:** `*_READ_BUFFER` + `BUFFER_SEND`
**Why:** Flexible, composable, efficient

### 2. Abstract Interfaces for Portability
**Why:** Easy to add RP2040, ESP32, STM32 later
**Benefit:** Core action logic doesn't change per platform

### 3. Compile-Time Pin Capability Tables
**Why:** No runtime lookup overhead
**Benefit:** Fast validation, small memory footprint

### 4. Serial Error Logging
**Why:** UI needs to show why actions fail
**Format:** `[PIN_ERROR] Pin X: Reason`

### 5. Configurable I2C Pins
**Why:** Users might need alternate SERCOM for pin conflicts
**Benefit:** Maximum flexibility, resolves I2C/SPI conflict

---

## What's NOT in Phase 1

### Action Chaining (Phase 2)
- Sequencing multiple actions from one trigger
- `next_rule_id` field
- Delay between actions

### Conditional Logic (Phase 3)
- If/then/else in actions
- Compare values
- Branch based on sensor readings

### Custom Command Macros (Phase 3)
- User-defined sequences
- Scripting engine
- Complex state machines

**These are documented in design doc for future implementation.**

---

## Getting Started

**Start with:** `docs/PHASE1_TODO.md`

**First Task:** Implement ActionDataBuffer class
- Simple 8-byte buffer
- Slot-based write/read
- Unit tests

**Then:** Pin capability database
- Create SAMD51 pin table
- Implement validation functions

**Follow:** 4-week schedule in TODO

---

## Questions?

**Design Questions:** See `MULTI_STEP_ACTIONS_DESIGN.md`
**Pin Questions:** See `SAMD51_PIN_REFERENCE.md`
**Task Details:** See `PHASE1_TODO.md`

**Ready to implement?** Start with Priority 1 in `PHASE1_TODO.md`!

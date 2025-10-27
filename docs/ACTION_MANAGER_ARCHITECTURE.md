# ActionManager Architecture Design

## Overview

The ActionManager system has been refactored into a clean, embedded-friendly architecture following the Hardware Abstraction Layer (HAL) pattern used throughout the uCAN project. This design enables platform-specific custom commands while maximizing code reuse.

## Architecture Pattern: Abstract Base Class with Platform Implementations

```
ActionManagerBase (abstract)
    |
    +-- SAMD51ActionManager (SAMD51 Feather M4 CAN)
    |
    +-- RP2040ActionManager (Raspberry Pi Pico)
    |
    +-- ESP32ActionManager (future)
    |
    +-- STM32ActionManager (future)
```

## Key Components

### 1. ActionManagerBase (`src/actions/action_manager_base.h/cpp`)

**Purpose:** Contains all platform-agnostic logic for rule management, CAN message matching, and action dispatching.

**Responsibilities:**
- Rule storage in static array (`ActionRule rules_[MAX_ACTION_RULES]`)
- Rule matching against incoming CAN messages
- Action dispatching to platform-specific implementations
- Rule parsing from command strings
- Periodic action execution
- Custom command registry management

**Pure Virtual Methods (Platform-Specific):**
```cpp
virtual bool execute_gpio_action(ActionType type, uint8_t pin) = 0;
virtual bool execute_pwm_action(uint8_t pin, uint8_t duty) = 0;
virtual bool execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) = 0;
virtual bool execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id) = 0;
virtual bool save_rules_impl() = 0;
virtual uint8_t load_rules_impl() = 0;
virtual void register_custom_commands() = 0;
```

**Platform-Agnostic Methods:**
- `execute_can_send_action()` - Uses CANInterface (already abstracted)
- `matches_rule()` - CAN ID and data pattern matching
- `add_rule()`, `remove_rule()`, `set_rule_enabled()` - Rule management
- `update_periodic()` - Periodic CAN message sending

### 2. Platform-Specific Implementations

#### SAMD51ActionManager (`src/capabilities/samd51/samd51_action_manager.h/cpp`)

**Hardware Features:**
- Built-in NeoPixel RGB LED
- 12-bit PWM (native hardware)
- 12-bit ADC with DMA support
- 2x 12-bit DAC channels (A0, A1)
- 2MB QSPI Flash for persistent storage

**Custom Commands:**
1. **neopixel** - Direct RGB LED control
   - Parameters: red (0-255), green (0-255), blue (0-255), brightness (0-255, optional)
   - Example: `custom:neopixel:255:0:0:128` (red at 50% brightness)

2. **dac** - Set DAC output voltage
   - Parameters: channel (0=A0, 1=A1), value (0-4095)
   - Example: `custom:dac:0:2048` (set DAC0 to 1.65V mid-scale)

**Persistence:**
- Uses `samd51_flash_storage.cpp` for rule persistence
- Saves rules to QSPI flash with magic number verification
- Supports up to 64 action rules (MAX_ACTION_RULES)

#### RP2040ActionManager (`src/capabilities/rp2040/rp2040_action_manager.h/cpp`)

**Hardware Features:**
- 30 GPIO pins (programmable)
- 16-bit PWM via hardware slices
- 12-bit ADC (4 channels + temperature sensor)
- No built-in NeoPixel (returns false)
- 2MB Flash (persistence not yet implemented)

**Custom Commands:**
1. **pwm_freq** - Set PWM frequency per pin
   - Parameters: pin (0-29), frequency (1-125000000 Hz)
   - Example: `custom:pwm_freq:15:1000` (GP15 at 1kHz)
   - Uses RP2040's flexible PWM slices

2. **adc_temp** - Read internal temperature sensor
   - Parameters: can_id (hex CAN ID for response)
   - Example: `custom:adc_temp:0x123`
   - Sends temperature in 0.01°C units (int16, big-endian)

3. **gpio_pulse** - Pulse GPIO pin HIGH for duration
   - Parameters: pin (0-29), duration_ms (1-10000)
   - Example: `custom:gpio_pulse:14:500` (pulse GP14 for 500ms)
   - Useful for triggering relays, actuators

**Persistence:**
- TODO: Implement flash-based storage using LittleFS or EEPROM emulation
- Currently returns false (no persistence)
- Supports up to 16 action rules (MAX_ACTION_RULES)

### 3. ActionManagerFactory (`src/actions/action_manager_factory.h`)

**Purpose:** Factory pattern for instantiating the correct platform implementation at compile-time.

**Usage:**
```cpp
ActionManagerBase* action_manager = ActionManagerFactory::create();
action_manager->initialize(can_interface);
```

**Platform Detection:**
- Uses preprocessor macros (PLATFORM_SAMD51, PLATFORM_RP2040, etc.)
- Compile-time selection (zero runtime overhead)
- Returns platform-specific instance via polymorphic pointer

### 4. Custom Command System (`src/actions/custom_command.h/cpp`)

**Purpose:** Extensible command registry allowing platforms to expose unique features to the TUI.

**Key Classes:**
- `CustomCommand` (abstract base) - Defines command interface
- `ParamDef` - Parameter definition with type, range, description
- `CustomCommandRegistry` - Manages command registration and execution

**Supported Parameter Types:**
- Numeric: `uint8`, `uint16`, `uint32`, `int8`, `int16`, `int32`, `float`
- Special: `bool`, `string`, `hex`, `enum`

**UI Auto-Generation:**
The TUI can query `get:commands` to receive JSON describing all available commands:
```json
CUSTOMCMD;{
  "name":"neopixel",
  "description":"Set built-in NeoPixel color and brightness",
  "category":"Visual",
  "parameters":[
    {"name":"red","description":"Red component (0-255)","type":"uint8","required":true,"min":0,"max":255},
    {"name":"green","description":"Green component (0-255)","type":"uint8","required":true,"min":0,"max":255},
    {"name":"blue","description":"Blue component (0-255)","type":"uint8","required":true,"min":0,"max":255},
    {"name":"brightness","description":"Brightness level (0-255)","type":"uint8","required":false,"min":0,"max":255}
  ]
}
```

## Memory Considerations

### Static Allocation Strategy
All platforms use static allocation to avoid heap fragmentation:
- Rules stored in fixed-size array: `ActionRule rules_[MAX_ACTION_RULES]`
- Custom commands registered as static instances
- No dynamic allocation in critical paths (interrupt handlers, main loop)

### Platform-Specific Limits
```cpp
// Platform-specific maximum rules (compile-time constants)
#ifdef PLATFORM_RP2040
    #define MAX_ACTION_RULES 16    // RP2040: 264KB RAM, limited
#elif defined(PLATFORM_SAMD51)
    #define MAX_ACTION_RULES 64    // SAMD51: 192KB RAM, generous
#elif defined(PLATFORM_ESP32)
    #define MAX_ACTION_RULES 32    // ESP32: ~520KB RAM, moderate
#else
    #define MAX_ACTION_RULES 8     // Default/minimal
#endif
```

### Memory Footprint Analysis

**ActionRule Structure Size:**
```
sizeof(ActionRule) = ~64 bytes:
  - CAN matching: 28 bytes (ID, mask, data, data_mask)
  - Action params: 12 bytes (union)
  - Metadata: 24 bytes (ID, enabled, counters, timestamps)
```

**Total Memory Usage:**
- RP2040: 16 rules × 64 bytes = 1KB
- SAMD51: 64 rules × 64 bytes = 4KB
- Plus base class overhead: ~200 bytes
- Plus CustomCommandRegistry: ~100 bytes

**Total Firmware Size Impact:**
- Base class code: ~6KB
- SAMD51 implementation: ~3KB (includes NeoPixel, DAC commands)
- RP2040 implementation: ~2.5KB (includes PWM freq, temp sensor)

## Adding New Platforms

### Step-by-Step Guide

1. **Define Platform Macro** in `src/hal/platform_config.h`:
   ```cpp
   #elif defined(ARDUINO_ARCH_ESP32)
       #define PLATFORM_ESP32
       #define PLATFORM_NAME "ESP32"
   ```

2. **Create Header** `src/capabilities/esp32/esp32_action_manager.h`:
   ```cpp
   #pragma once
   #include "../../actions/action_manager_base.h"

   #ifdef PLATFORM_ESP32
   class ESP32ActionManager : public ActionManagerBase {
   public:
       ESP32ActionManager();
       virtual ~ESP32ActionManager();
   protected:
       bool execute_gpio_action(ActionType type, uint8_t pin) override;
       bool execute_pwm_action(uint8_t pin, uint8_t duty) override;
       bool execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) override;
       bool execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id) override;
       bool save_rules_impl() override;
       uint8_t load_rules_impl() override;
       void register_custom_commands() override;
   };
   #endif
   ```

3. **Implement Platform Methods** in `.cpp`:
   - GPIO: Use ESP32 GPIO APIs
   - PWM: Use `ledcSetup()`, `ledcAttachPin()`, `ledcWrite()`
   - ADC: Use `analogRead()` with proper resolution
   - Persistence: Use SPIFFS or Preferences library
   - Custom commands: WiFi control, BLE commands, etc.

4. **Update Factory** in `src/actions/action_manager_factory.h`:
   ```cpp
   #elif defined(PLATFORM_ESP32)
       return new ESP32ActionManager();
   ```

5. **Update PlatformIO** in `platformio.ini`:
   ```ini
   [env:esp32dev]
   platform = espressif32
   board = esp32dev
   framework = arduino
   build_flags = -DPLATFORM_ESP32
   ```

## Design Trade-offs

### Why Abstract Base Class (Not Templates)?
**Decision:** Abstract base class with virtual methods
**Alternatives Considered:**
1. Templates (CRTP pattern)
2. Function pointers
3. Preprocessor macros

**Rationale:**
- ✅ Clear, readable code (no template complexity)
- ✅ Debugger-friendly (can step through virtual calls)
- ✅ Smaller binary size (one vtable vs template instantiation bloat)
- ✅ Factory pattern works naturally
- ❌ Minor runtime cost (~2-3 CPU cycles per virtual call)
- ❌ Dynamic allocation for manager instance (acceptable: single instance)

**Performance Impact:**
- Virtual method dispatch: ~2-3 cycles on ARM Cortex-M
- Action execution typically takes 100-1000+ cycles (GPIO, SPI, etc.)
- Virtual overhead is <1% of total execution time
- Zero impact on interrupt latency (actions run in main loop)

### Why Static Custom Commands?
**Decision:** Static command instances registered at initialization
**Alternatives Considered:**
1. Dynamic allocation
2. Compile-time template registration

**Rationale:**
- ✅ No heap fragmentation
- ✅ Predictable memory usage
- ✅ Simple registration pattern
- ✅ Fast execution (direct function call)
- ❌ Limited to MAX_CUSTOM_COMMANDS (16, acceptable)

### Why Platform-Specific Persistence?
**Decision:** Each platform implements its own storage backend
**Alternatives Considered:**
1. Generic filesystem abstraction
2. Serialization library (e.g., Protocol Buffers)

**Rationale:**
- ✅ Leverage platform strengths (SAMD51 QSPI, ESP32 SPIFFS)
- ✅ Minimal code size (no generic filesystem layer)
- ✅ Optimal performance (direct flash access)
- ❌ Some code duplication across platforms (acceptable: ~50 lines)

## Protocol Integration

### New Commands

**Query Custom Commands:**
```
> get:commands
< CUSTOMCMD;{"name":"neopixel",...}
< CUSTOMCMD;{"name":"dac",...}
```

**Execute Custom Command:**
```
> custom:neopixel:255:0:0:128
< STATUS;INFO;Custom command executed;neopixel
```

### Backward Compatibility
- All existing action commands (`action:add`, `action:list`, etc.) work unchanged
- Older TUI versions ignore `CUSTOMCMD` responses
- New TUI can detect platform capabilities and show custom command UI

## Testing Strategy

### Unit Testing (Platform-Agnostic)
- Test rule matching logic (mock CAN messages)
- Test add/remove/enable/disable operations
- Test periodic action timing

### Integration Testing (Per-Platform)
- GPIO actions with physical LED
- PWM actions with oscilloscope verification
- ADC read accuracy vs known voltage source
- Custom commands (NeoPixel colors, DAC output)
- Persistence (power cycle test)

### Regression Testing
- Ensure old action rules still work
- Verify protocol compatibility
- Check memory usage doesn't exceed limits

## Future Enhancements

### Conditional Actions
Add conditional logic to rules:
```cpp
struct ActionRule {
    // ...
    ActionCondition condition;  // If ADC > threshold, If GPIO == HIGH, etc.
};
```

### Action Sequences
Chain multiple actions:
```cpp
struct ActionSequence {
    ActionRule steps[8];
    uint16_t delays_ms[8];
};
```

### Remote Custom Commands
Allow custom commands to be triggered remotely via CAN:
```cpp
// CAN message with ID 0x700 executes custom command
// Data[0] = command index, Data[1-7] = parameters
```

### Scripting Support (Advanced)
Embed lightweight scripting (Lua, Wren) for complex logic without firmware reflashing.

## Conclusion

This architecture successfully balances:
- **Code reuse** - 80% of ActionManager code is shared
- **Platform flexibility** - Easy to add new platforms and custom commands
- **Memory efficiency** - Static allocation, predictable footprint
- **Performance** - Virtual call overhead <1% of action execution time
- **Maintainability** - Clear separation of concerns, no preprocessor spaghetti

The design follows embedded best practices:
- No heap allocation in critical paths
- Compile-time platform selection
- Zero-overhead abstractions where possible
- Minimal code duplication

Adding a new platform requires ~200-300 lines of code (header + implementation + 2-3 custom commands), which is acceptable for the flexibility gained.

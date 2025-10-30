# Audit Report: src/main.cpp - Board-Specific Code Analysis

**Status:** CRITICAL VIOLATIONS FOUND
**Date:** 2025-10-30
**Severity:** HIGH - Multiple instances of board-specific code at top level

---

## Executive Summary

`src/main.cpp` violates the board abstraction layer design by containing **board-specific code that should be delegated to `BoardInterface` implementations**. The main violations are:

1. **LED blinking logic** (lines 142-153) - Should be in `BoardInterface::update_periodic()`
2. **Board-specific reset handling** (lines 506-512) - Should be in `BoardInterface`
3. **Default rule loading with platform conditionals** (lines 123-132) - Design debt

All violations break the abstraction: main.cpp should **only call interfaces**, not execute board-specific logic.

---

## Violations Found

### 1. LED Blinking Logic (Lines 142-153) - CRITICAL

**Current Code:**
```cpp
void loop() {
  // Blink LED to show we're alive
  static unsigned long last_blink = 0;
  if (millis() - last_blink > 1000) {
    #ifdef STATUS_LED_PIN
      if (STATUS_LED_PIN != 0) {
        digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
      }
    #elif defined(LED_BUILTIN)
      digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    #endif
    last_blink = millis();
  }
}
```

**Issues:**
- Direct GPIO access (`digitalWrite`) in main loop
- Board-specific conditional compilation (`#ifdef STATUS_LED_PIN`, `#elif defined(LED_BUILTIN)`)
- Hardcoded 1000ms blink interval
- Only works for platforms with Arduino GPIO API

**Why This Violates Abstraction:**
- `main.cpp` should NOT know about GPIO or hardware pins
- LED management is board-specific behavior (some boards have RGB NeoPixels, some have basic LEDs)
- Different boards may blink differently (heartbeat patterns, color coding)
- Prevents platforms without GPIO API (e.g., custom RTOS) from working

**Current Abstraction Layer:**
- `BoardInterface::update_periodic()` exists (line 67 in `board_interface.h`) for exactly this purpose
- This method is already called in `loop()` (line 163): `action_manager->update_periodic()`
- But `BoardInterface` is not being used for LED management

**Impact:**
- ❌ Cannot unit test LED behavior (tied to hardware)
- ❌ Board-specific code scattered in main instead of centralized
- ❌ Adding new board LED types requires modifying main.cpp
- ❌ Code is duplicated across platforms (each platform reimplements blink logic)

---

### 2. LED Setup in setup() (Lines 56-63) - MEDIUM

**Current Code:**
```cpp
void setup() {
  Serial.begin(DEFAULT_SERIAL_BAUD);

  // Setup status LED if available
  #ifdef STATUS_LED_PIN
    if (STATUS_LED_PIN != 0) {
      pinMode(STATUS_LED_PIN, OUTPUT);
    }
  #elif defined(LED_BUILTIN)
    pinMode(LED_BUILTIN, OUTPUT);
  #endif
```

**Issues:**
- Direct GPIO setup in main, not in board initialization
- Should be in `BoardInterface::initialize()`
- Hardcoded to know about STATUS_LED_PIN macro

**Correct Pattern:**
```cpp
// This should be in board implementations ONLY:
bool TCAN485Board::initialize(ActionManagerBase* action_manager) {
    // Initialize NeoPixel for status indication
    neopixel_ = new Adafruit_NeoPixel(...);
    neopixel_->begin();
    set_neopixel_status(0, 255, 0);  // Green: ready
    return true;
}
```

---

### 3. Platform-Specific Reset Handler (Lines 506-512) - HIGH

**Current Code:**
```cpp
void handle_control_command(const char* action) {
  if (strcmp(action, "reset") == 0) {
    send_status("INFO", "Resetting device");
    delay(100);
    // Platform-specific reset
    #ifdef PLATFORM_RP2040
      watchdog_reboot(0, 0, 0);
    #elif defined(PLATFORM_ESP32)
      ESP.restart();
    #else
      NVIC_SystemReset();  // ARM Cortex-M (SAMD51, STM32, etc.)
    #endif
```

**Issues:**
- Platform-specific code in command handler
- Should be delegated to platform layer (action manager) or board implementation
- main.cpp knows too much about platform implementation details

**Better Approach:**
```cpp
// In platform-specific action manager
virtual bool reset() = 0;

// In main:
void handle_control_command(const char* action) {
  if (strcmp(action, "reset") == 0) {
    send_status("INFO", "Resetting device");
    delay(100);
    if (action_manager) {
      action_manager->reset();
    }
  }
}
```

---

### 4. Platform-Specific Default Rules (Lines 123-132) - DESIGN DEBT

**Current Code:**
```cpp
#ifdef PLATFORM_SAMD51
  loaded = load_samd51_default_rules(action_manager);
  if (loaded > 0) {
    // ...
    action_manager->save_rules();
  }
#endif
```

**Issues:**
- Only SAMD51 platform is handled (hard to extend)
- Should use factory pattern: `ActionManagerFactory::load_default_rules()`
- Violates DRY: same logic repeated per platform

**Better Approach:**
```cpp
// In action manager factory
static uint8_t load_platform_default_rules(ActionManagerBase* manager);

// In main:
uint8_t loaded = ActionManagerFactory::load_platform_default_rules(action_manager);
```

---

## Correct Abstraction Pattern

The codebase already has the RIGHT abstraction in place but isn't using it fully:

### Existing BoardInterface (should be extended)
```cpp
class BoardInterface {
    virtual bool initialize(ActionManagerBase* action_manager) = 0;
    virtual void update_periodic() = 0;  // <-- LED blink should go HERE
    virtual const char* get_board_name() const = 0;
};
```

### Flow Should Be:
```
main.cpp (generic)
    ↓
    CANInterface (via Factory) → RP2040CAN, SAMD51CAN, etc.
    ↓
    ActionManagerBase (via Factory) → RP2040ActionManager, SAMD51ActionManager, etc.
    ↓
    BoardInterface (via Factory) → TCAN485Board, TPanelBoard, etc.
        - Handles all board-specific peripherals
        - LED management
        - Display updates
        - RS485 communication
        - SD card operations
        - Power management
        - Custom board commands
```

---

## Required Fixes

### Fix #1: Move LED Blink to BoardInterface (Priority: HIGH)

**Step 1: Extend BoardInterface.update_periodic()**
```cpp
// In board implementations:
void TCAN485Board::update_periodic() {
    // Handle NeoPixel status blinking
    static unsigned long last_blink = 0;
    if (millis() - last_blink > 1000) {
        // Toggle LED color based on CAN activity
        update_status_led();
        last_blink = millis();
    }
}

void TPanelBoard::update_periodic() {
    // Update display with stats
    // Handle touch events
    // Update backlight
}

// Generic boards with no special peripherals:
void DefaultBoard::update_periodic() {
    // Basic LED toggle if available
}
```

**Step 2: Remove from main.cpp**
```cpp
// REMOVE from loop():
#ifdef STATUS_LED_PIN
  if (STATUS_LED_PIN != 0) {
    digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
  }
#elif defined(LED_BUILTIN)
  digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
#endif
```

**Step 3: Call BoardInterface in main (already exists)**
```cpp
// This already calls action_manager->update_periodic()
// but should ALSO call board->update_periodic()
void loop() {
    process_can_messages();
    process_serial_input();

    if (action_manager) {
        action_manager->update_periodic();
    }

    if (board_interface) {  // <-- ADD THIS
        board_interface->update_periodic();
    }

    // Stats, heartbeat, etc.
}
```

---

### Fix #2: Move LED Setup to BoardInterface.initialize()

**In board implementations:**
```cpp
bool TCAN485Board::initialize(ActionManagerBase* action_manager) {
    // Initialize NeoPixel
    neopixel_ = new Adafruit_NeoPixel(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
    neopixel_->begin();
    set_neopixel_status(0, 255, 0);  // Green
    return true;
}
```

**Remove from main.cpp setup():**
```cpp
// REMOVE:
#ifdef STATUS_LED_PIN
  if (STATUS_LED_PIN != 0) {
    pinMode(STATUS_LED_PIN, OUTPUT);
  }
#elif defined(LED_BUILTIN)
  pinMode(LED_BUILTIN, OUTPUT);
#endif
```

---

### Fix #3: Create BoardInterface for Generic Boards

For platforms without special board implementations, create a simple default:

```cpp
// src/boards/default/board_impl.h
#ifndef BOARD_T_CAN485
#ifndef BOARD_T_PANEL
// ... other boards

class DefaultBoard : public BoardInterface {
public:
    bool initialize(ActionManagerBase* action_manager) override;
    void register_custom_commands(CustomCommandRegistry& registry) override;
    void update_periodic() override;
    const char* get_board_name() const override;

private:
    static unsigned long last_blink_;
};

#endif
#endif
```

Update `board_factory.cpp`:
```cpp
BoardInterface* BoardFactory::create() {
    #if defined(BOARD_T_CAN485)
        return new TCAN485Board();
    #elif defined(BOARD_T_PANEL)
        return new TPanelBoard();
    #else
        return new DefaultBoard();  // <-- Return default instead of nullptr
    #endif
}
```

---

### Fix #4: Delegate Reset to ActionManager

**Add to ActionManagerBase:**
```cpp
virtual bool reset() = 0;  // Pure virtual

// In platform implementations:
// RP2040ActionManager
bool reset() override {
    watchdog_reboot(0, 0, 0);
    return true;
}

// SAMD51ActionManager
bool reset() override {
    NVIC_SystemReset();
    return true;
}

// ESP32ActionManager
bool reset() override {
    ESP.restart();
    return true;
}
```

**In main.cpp:**
```cpp
void handle_control_command(const char* action) {
  if (strcmp(action, "reset") == 0) {
    send_status("INFO", "Resetting device");
    delay(100);
    if (action_manager) {
        action_manager->reset();
    }
  }
}
```

---

### Fix #5: Create Factory Method for Default Rules

**In ActionManagerFactory:**
```cpp
class ActionManagerFactory {
public:
    static ActionManagerBase* create();

    // NEW: Platform-specific default rule loader
    static uint8_t load_platform_default_rules(ActionManagerBase* manager) {
        #ifdef PLATFORM_SAMD51
            return load_samd51_default_rules(manager);
        #elif defined(PLATFORM_RP2040)
            return load_rp2040_default_rules(manager);
        #else
            return 0;  // No platform-specific defaults
        #endif
    }
};
```

**In main.cpp:**
```cpp
// Try to load rules from persistent storage first
uint8_t loaded = action_manager->load_rules();
if (loaded == 0) {
    // No saved rules, load platform-specific defaults if available
    loaded = ActionManagerFactory::load_platform_default_rules(action_manager);
    if (loaded > 0) {
        char details[64];
        snprintf(details, sizeof(details), "Loaded %d default rule(s)", loaded);
        send_status("INFO", "Default rules loaded", details);
        action_manager->save_rules();
    }
}
```

---

## Summary of Violations

| Line(s) | Issue | Severity | Fix Location |
|---------|-------|----------|--------------|
| 56-63 | LED setup in setup() | MEDIUM | BoardInterface::initialize() |
| 142-153 | LED blinking in loop() | CRITICAL | BoardInterface::update_periodic() |
| 506-512 | Platform-specific reset | HIGH | ActionManagerBase::reset() |
| 123-132 | Platform-specific rules | MEDIUM | ActionManagerFactory::load_platform_default_rules() |

---

## Architecture Benefits After Fixes

1. **Testability**: LED blinking can be unit tested without hardware
2. **Extensibility**: Add new board types without touching main.cpp
3. **Modularity**: All board-specific code lives in one folder
4. **Maintainability**: Clear separation of concerns
5. **Reusability**: Board implementations usable by other projects
6. **Portability**: Easy to adapt codebase to new platforms

---

## Files to Modify

### Priority 1 (Critical):
- `src/main.cpp` - Remove LED blink logic, add board interface initialization
- `src/boards/board_interface.h` - Ensure update_periodic() is documented for LED management
- `src/boards/t_can485/board_impl.cpp` - Implement LED blink in update_periodic()
- `src/boards/t_panel/board_impl.cpp` - Implement display update in update_periodic()

### Priority 2 (High):
- `src/actions/action_manager_base.h` - Add virtual reset() method
- Platform-specific action managers - Implement reset()

### Priority 3 (Medium):
- `src/actions/action_manager_factory.h` - Add load_platform_default_rules()
- `src/boards/board_factory.cpp` - Return DefaultBoard instead of nullptr

---

## Verification Checklist

After making fixes, verify:

- [ ] No `#ifdef PLATFORM_*` in main.cpp
- [ ] No `#ifdef STATUS_LED_PIN` in main.cpp
- [ ] No `#ifdef LED_BUILTIN` in main.cpp
- [ ] No `#ifdef BOARD_T_*` in main.cpp
- [ ] No direct GPIO calls in main.cpp (pinMode, digitalWrite)
- [ ] BoardInterface::initialize() called in main setup()
- [ ] BoardInterface::update_periodic() called in main loop()
- [ ] All board-specific logic in src/boards/*/board_impl.* files
- [ ] Code compiles for Pico, Feather M4, ESP32
- [ ] LED blinks on T-CAN485 board
- [ ] Display updates on T-Panel board
- [ ] Reset command works on all platforms

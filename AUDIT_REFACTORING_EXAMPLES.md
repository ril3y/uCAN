# Refactoring Examples: From Violations to Clean Architecture

## Overview

This document provides complete before/after code examples for fixing all violations in `src/main.cpp`.

---

## Example 1: LED Blinking - The Critical Violation

### Before (INCORRECT - Lines 142-153 in main.cpp)

```cpp
void loop() {
  // ... other code ...

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

  // ... rest of loop ...
}
```

**Problems with this approach:**
- Direct GPIO manipulation in hot loop
- Platform-specific conditionals (#ifdef)
- Cannot be unit tested
- Only works for simple GPIO LEDs (not NeoPixels)
- LED control scattered across files (no centralization)

---

### After (CORRECT - Delegated to BoardInterface)

#### Step 1: Update src/main.cpp (REMOVE LED code)

```cpp
void loop() {
  // Process CAN messages
  process_can_messages();

  // Handle serial commands
  process_serial_input();

  // Update periodic actions (includes custom commands)
  if (action_manager) {
    action_manager->update_periodic();
  }

  // UPDATE: Call board interface periodic update
  if (board_interface) {
    board_interface->update_periodic();  // All LED/display updates happen here
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
```

**Key changes:**
- Removed LED blinking logic entirely (lines 142-153)
- Added call to `board_interface->update_periodic()`
- main.cpp now has NO GPIO code

#### Step 2: Update src/main.cpp setup() (REMOVE LED setup)

```cpp
void setup() {
  Serial.begin(DEFAULT_SERIAL_BAUD);

  // REMOVED: LED setup code
  // The BoardInterface will handle all LED initialization

  // Wait for serial port to be ready (up to 3 seconds)
  unsigned long start_time = millis();
  while (!Serial && (millis() - start_time) < 3000) {
    delay(10);
  }

  // Create platform-specific CAN interface
  can_interface = CANFactory::create();
  if (!can_interface) {
    send_status("ERROR", "Failed to create CAN interface");
    while (1) delay(1000);
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
    while (1) delay(1000);
  }

  // Create platform-specific action manager
  action_manager = ActionManagerFactory::create();
  if (!action_manager) {
    send_status("ERROR", "Failed to create action manager");
    while (1) delay(1000);
  }

  // Initialize action manager
  if (action_manager->initialize(can_interface)) {
    char details[128];
    snprintf(details, sizeof(details), "%s action manager",
             ActionManagerFactory::get_platform_name());
    send_status("INFO", "Action manager initialized", details);

    // Initialize with default configuration if enabled
#ifdef HAS_DEFAULT_CONFIG
    if (init_default_config(action_manager)) {
      send_status("INFO", "Default configuration initialized");
    } else {
      send_status("WARNING", "Default configuration initialization failed");
    }
#endif

    // Try to load rules from persistent storage first
    uint8_t loaded = action_manager->load_rules();
    if (loaded > 0) {
      char details[64];
      snprintf(details, sizeof(details), "Loaded %d rule(s) from storage", loaded);
      send_status("INFO", "Rules restored", details);
    } else {
      // Use factory method for platform-specific defaults
      loaded = ActionManagerFactory::load_platform_default_rules(action_manager);
      if (loaded > 0) {
        char details[64];
        snprintf(details, sizeof(details), "Loaded %d default rule(s)", loaded);
        send_status("INFO", "Default rules loaded", details);
        action_manager->save_rules();
      }
    }
  } else {
    send_status("WARNING", "Action manager initialization failed");
  }

  // NEW: Create and initialize board-specific implementation
  board_interface = BoardFactory::create();
  if (board_interface) {
    if (board_interface->initialize(action_manager)) {
      char details[64];
      snprintf(details, sizeof(details), "%s board", board_interface->get_board_name());
      send_status("INFO", "Board initialized", details);
    } else {
      send_status("WARNING", "Board initialization failed");
    }
  }

  last_stats_time = millis();
}
```

**Key changes:**
- Removed LED setup (#ifdef STATUS_LED_PIN and #elif defined(LED_BUILTIN))
- Added board interface creation and initialization
- All LED initialization now delegated to BoardInterface

#### Step 3: Create src/boards/t_can485/board_impl.cpp

```cpp
#ifdef BOARD_T_CAN485

#include "board_impl.h"
#include "../../actions/action_manager_base.h"
#include "../../capabilities/esp32/esp32_action_manager.h"
#include <Arduino.h>

// Pin definitions for T-CAN485
#define NEOPIXEL_PIN      35
#define NEOPIXEL_COUNT    1
#define RS485_RX_PIN      16
#define RS485_TX_PIN      17
#define RS485_RE_PIN      15
#define SD_CS_PIN         4
#define SD_MOSI_PIN       13
#define SD_MISO_PIN       12
#define SD_CLK_PIN        14

TCAN485Board::TCAN485Board() : neopixel_(nullptr), sd_available_(false) {}

TCAN485Board::~TCAN485Board() {
  if (neopixel_) {
    delete neopixel_;
  }
}

bool TCAN485Board::initialize(ActionManagerBase* action_manager) {
  // Initialize NeoPixel status LED
  if (!init_neopixel()) {
    return false;
  }

  // Initialize RS485 transceiver
  if (!init_rs485()) {
    // RS485 is optional
  }

  // Initialize SD card
  if (!init_sd_card()) {
    // SD is optional
  }

  // Initialize power management
  if (!init_power_management()) {
    // Power management is optional
  }

  // Set initial status: ready (green)
  set_neopixel_status(0, 255, 0);

  return true;
}

bool TCAN485Board::init_neopixel() {
  if (neopixel_) {
    delete neopixel_;
  }

  neopixel_ = new Adafruit_NeoPixel(
    NEOPIXEL_COUNT,
    NEOPIXEL_PIN,
    NEO_GRB + NEO_KHZ800
  );

  neopixel_->begin();
  return true;
}

bool TCAN485Board::init_rs485() {
  // Initialize RS485 control pins
  pinMode(RS485_RE_PIN, OUTPUT);
  digitalWrite(RS485_RE_PIN, LOW);  // Receiver enabled by default

  // Configure Serial2 for RS485
  // This would be platform-specific configuration
  return true;
}

bool TCAN485Board::init_sd_card() {
  // Initialize SPI for SD card
  // This is platform-specific
  sd_available_ = false;  // Would be set to true if init succeeds
  return true;
}

bool TCAN485Board::init_power_management() {
  // Initialize ME2107 boost converter
  // This is specific to T-CAN485
  return true;
}

void TCAN485Board::set_neopixel_status(uint8_t r, uint8_t g, uint8_t b) {
  if (neopixel_) {
    neopixel_->setPixelColor(0, neopixel_->Color(r, g, b));
    neopixel_->show();
  }
}

void TCAN485Board::update_periodic() {
  // This is called from main loop
  // Update status LED based on device state

  static unsigned long last_blink = 0;
  static bool led_on = false;

  // Simple blink pattern: 500ms on, 500ms off
  if (millis() - last_blink > 500) {
    led_on = !led_on;

    if (led_on) {
      // Green: normal operation
      set_neopixel_status(0, 255, 0);
    } else {
      // LED off
      set_neopixel_status(0, 0, 0);
    }

    last_blink = millis();
  }

  // Could add other periodic tasks:
  // - Read RS485 data
  // - Update SD card logging
  // - Monitor power state
}

void TCAN485Board::register_custom_commands(CustomCommandRegistry& registry) {
  // Register board-specific commands
  // Examples: rs485_send, sd_log, power_monitor
}

const char* TCAN485Board::get_board_name() const {
  return "LilyGo T-CAN485";
}

const char* TCAN485Board::get_board_version() const {
  return "v1.0";
}

#endif  // BOARD_T_CAN485
```

**Key points:**
- ALL LED code is here, not in main.cpp
- `update_periodic()` is called from main loop
- NeoPixel initialized in `initialize()`, not in main `setup()`
- Different LED strategies per board possible
- Easy to test with mock BoardInterface

#### Step 4: Create src/boards/default/board_impl.cpp (for generic boards)

```cpp
// This is NOT conditional - serves as default for boards without special peripherals

#include "board_impl.h"
#include "../../actions/action_manager_base.h"
#include <Arduino.h>

DefaultBoard::DefaultBoard() : led_pin_(0xFF) {}

DefaultBoard::~DefaultBoard() {}

bool DefaultBoard::initialize(ActionManagerBase* action_manager) {
  // Look for LED_BUILTIN if available
  #ifdef LED_BUILTIN
    led_pin_ = LED_BUILTIN;
    pinMode(led_pin_, OUTPUT);
    digitalWrite(led_pin_, LOW);
  #endif

  return true;
}

void DefaultBoard::register_custom_commands(CustomCommandRegistry& registry) {
  // Generic boards have no custom commands
}

void DefaultBoard::update_periodic() {
  // Simple LED blink for generic boards
  if (led_pin_ == 0xFF) {
    return;  // No LED
  }

  static unsigned long last_blink = 0;
  if (millis() - last_blink > 1000) {
    digitalWrite(led_pin_, !digitalRead(led_pin_));
    last_blink = millis();
  }
}

const char* DefaultBoard::get_board_name() const {
  return "Generic Board";
}

const char* DefaultBoard::get_board_version() const {
  return "1.0";
}
```

**Benefits:**
- Pico, Feather M4 CAN, generic ESP32 all use DefaultBoard
- Each board factory call returns non-null (even for generic boards)
- No more GPIO code scattered across main.cpp
- Consistent initialization pattern

#### Step 5: Update src/boards/board_factory.cpp

```cpp
BoardInterface* BoardFactory::create() {
  #if defined(BOARD_T_CAN485)
    return new TCAN485Board();

  #elif defined(BOARD_T_PANEL)
    return new TPanelBoard();

  #else
    // Generic board with optional built-in LED
    return new DefaultBoard();  // Changed from nullptr
  #endif
}
```

**Change:** Return `DefaultBoard()` instead of `nullptr` for consistency.

#### Step 6: Update src/main.cpp global declarations

Add at top of file:
```cpp
// Global board interface instance (optional, but non-null for all boards)
BoardInterface* board_interface = nullptr;
```

---

## Benefits After Refactoring

| Aspect | Before | After |
|--------|--------|-------|
| **LED Code Location** | main.cpp (2 places) | BoardInterface subclass |
| **Testability** | Hardware required | Mock-friendly |
| **Extensibility** | Modify main.cpp for new boards | Create new BoardInterface subclass |
| **Maintainability** | Scattered code, #ifdefs | Centralized per-board |
| **Code Duplication** | LED logic same for all simple boards | Reused by DefaultBoard |
| **Platform Support** | Pico, Feather hardcoded | Factory-based, easy to add |

---

## Example 2: Platform-Specific Reset

### Before (INCORRECT - Lines 506-512 in main.cpp)

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
  }
  // ... other commands ...
}
```

**Problems:**
- Platform implementation details in command handler
- main.cpp must be updated for each new platform
- Cannot unit test without hardware

---

### After (CORRECT - Delegated to ActionManagerBase)

#### Step 1: Update src/actions/action_manager_base.h

```cpp
class ActionManagerBase {
public:
  // ... existing methods ...

  /**
   * Reset the device
   * Platform-specific implementation varies:
   * - RP2040: Uses watchdog
   * - ESP32: Uses ESP.restart()
   * - ARM Cortex-M: Uses NVIC_SystemReset()
   *
   * @return true if reset was initiated, false if not supported
   */
  virtual bool reset() = 0;

  // ... rest of class ...
};
```

#### Step 2: Implement in src/capabilities/rp2040/rp2040_action_manager.cpp

```cpp
#ifdef PLATFORM_RP2040

#include "rp2040_action_manager.h"
#include <hardware/watchdog.h>

bool RP2040ActionManager::reset() {
  // Use RP2040 watchdog to trigger reset
  watchdog_reboot(0, 0, 0);
  return true;  // Will not return if successful
}

#endif
```

#### Step 3: Implement in src/capabilities/esp32/esp32_action_manager.cpp

```cpp
#ifdef PLATFORM_ESP32

#include "esp32_action_manager.h"
#include <esp_system.h>

bool ESP32ActionManager::reset() {
  // Use ESP32 restart function
  ESP.restart();
  return true;  // Will not return if successful
}

#endif
```

#### Step 4: Implement in src/capabilities/samd51/samd51_action_manager.cpp

```cpp
#ifdef PLATFORM_SAMD51

#include "samd51_action_manager.h"

bool SAMD51ActionManager::reset() {
  // Use ARM Cortex-M reset
  NVIC_SystemReset();
  return true;  // Will not return if successful
}

#endif
```

#### Step 5: Update src/main.cpp command handler

```cpp
void handle_control_command(const char* action) {
  if (strcmp(action, "reset") == 0) {
    send_status("INFO", "Resetting device");
    delay(100);
    // Delegate to platform-specific implementation
    if (action_manager) {
      action_manager->reset();
    }
  } else if (strcmp(action, "clear") == 0) {
    // ... rest of commands ...
  }
}
```

**Key changes:**
- Removed all #ifdef PLATFORM_* code
- Single line delegates to action_manager
- Each platform implements its own reset
- NO platform knowledge in main.cpp

---

## Example 3: Platform-Specific Default Rules

### Before (INCORRECT - Lines 123-132 in main.cpp)

```cpp
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
```

**Problems:**
- Only SAMD51 supported
- RP2040 and ESP32 don't get default rules
- Not extensible - must modify main.cpp for each platform
- Logic duplication

---

### After (CORRECT - Using Factory Pattern)

#### Step 1: Create src/actions/action_manager_factory.h

```cpp
#pragma once

#include "action_manager_base.h"

class ActionManagerFactory {
public:
  /**
   * Create platform-specific action manager
   * @return Pointer to platform-specific manager, or nullptr
   */
  static ActionManagerBase* create();

  /**
   * Get platform name
   * @return Human-readable platform name
   */
  static const char* get_platform_name();

  /**
   * Load platform-specific default rules
   *
   * Each platform may have its own default rules. This method
   * loads them if available. The logic for each platform is
   * isolated in its own implementation.
   *
   * @param manager Pointer to initialized action manager
   * @return Number of rules loaded, 0 if none available
   */
  static uint8_t load_platform_default_rules(ActionManagerBase* manager) {
    #ifdef PLATFORM_SAMD51
      return load_samd51_default_rules(manager);
    #elif defined(PLATFORM_RP2040)
      return load_rp2040_default_rules(manager);
    #elif defined(PLATFORM_ESP32)
      return load_esp32_default_rules(manager);
    #else
      return 0;  // No platform-specific defaults
    #endif
  }
};
```

#### Step 2: Create default rule loaders for each platform

**src/capabilities/rp2040/rp2040_default_rules.cpp:**

```cpp
#ifdef PLATFORM_RP2040

#include "rp2040_action_manager.h"

uint8_t load_rp2040_default_rules(ActionManagerBase* manager) {
  // RP2040-specific default rules
  // Example: blink LED on CAN message
  // This would create and add default rules specific to RP2040

  // For now, no defaults
  return 0;
}

#endif
```

**src/capabilities/esp32/esp32_default_rules.cpp:**

```cpp
#ifdef PLATFORM_ESP32

#include "esp32_action_manager.h"

uint8_t load_esp32_default_rules(ActionManagerBase* manager) {
  // ESP32-specific default rules
  // Example: control GPIO, NeoPixel on CAN message

  // For now, no defaults
  return 0;
}

#endif
```

**src/capabilities/samd51/samd51_default_rules.cpp:**

```cpp
#ifdef PLATFORM_SAMD51

#include "samd51_action_manager.h"

uint8_t load_samd51_default_rules(ActionManagerBase* manager) {
  // Existing implementation - unchanged
  // ...
}

#endif
```

#### Step 3: Update src/main.cpp (setup function)

```cpp
void setup() {
  // ... initialization code ...

  // Create platform-specific action manager
  action_manager = ActionManagerFactory::create();
  if (!action_manager) {
    send_status("ERROR", "Failed to create action manager");
    while (1) delay(1000);
  }

  // Initialize action manager
  if (action_manager->initialize(can_interface)) {
    char details[128];
    snprintf(details, sizeof(details), "%s action manager",
             ActionManagerFactory::get_platform_name());
    send_status("INFO", "Action manager initialized", details);

#ifdef HAS_DEFAULT_CONFIG
    if (init_default_config(action_manager)) {
      send_status("INFO", "Default configuration initialized");
    } else {
      send_status("WARNING", "Default configuration initialization failed");
    }
#endif

    // Try to load rules from persistent storage first
    uint8_t loaded = action_manager->load_rules();
    if (loaded > 0) {
      char details[64];
      snprintf(details, sizeof(details), "Loaded %d rule(s) from storage", loaded);
      send_status("INFO", "Rules restored", details);
    } else {
      // Use factory method for platform-specific defaults
      // This replaces the old #ifdef PLATFORM_SAMD51 block
      loaded = ActionManagerFactory::load_platform_default_rules(action_manager);
      if (loaded > 0) {
        char details[64];
        snprintf(details, sizeof(details), "Loaded %d default rule(s)", loaded);
        send_status("INFO", "Default rules loaded", details);
        action_manager->save_rules();
      }
    }
  } else {
    send_status("WARNING", "Action manager initialization failed");
  }

  // ... rest of setup ...
}
```

**Key changes:**
- Replaced `#ifdef PLATFORM_SAMD51` with factory method call
- Factory method has all #ifdefs (ONE place to update)
- Easy to add RP2040 and ESP32 default rules
- Consistent pattern for all platforms

---

## Summary of Refactoring Benefits

### Before Refactoring
```
main.cpp
├─ LED blinking (lines 142-153)
├─ LED setup (lines 56-63)
├─ Platform reset (lines 506-512)
├─ Platform-specific rules (lines 123-132)
└─ 200+ lines of policy/implementation mixing
```

### After Refactoring
```
main.cpp
├─ Serial setup
├─ CAN factory creation
├─ Action manager factory creation
├─ Board factory creation
├─ Main loop coordination
├─ Command parsing
└─ ~180 lines of pure policy (no implementation)

Distributed implementation:
├─ src/boards/t_can485/board_impl.cpp (LED control)
├─ src/boards/t_panel/board_impl.cpp (Display control)
├─ src/boards/default/board_impl.cpp (Generic LED)
├─ src/capabilities/*/[platform]_action_manager.cpp (reset)
└─ src/actions/action_manager_factory.h (factory methods)
```

---

## Verification After Refactoring

### Grep Checks (Should all return 0 results)

```bash
# Should be 0 matches after refactoring
grep -c "digitalWrite\|digitalRead\|pinMode" src/main.cpp
grep -c "^[[:space:]]*#ifdef PLATFORM_" src/main.cpp
grep -c "^[[:space:]]*#ifdef BOARD_" src/main.cpp
grep -c "^[[:space:]]*#ifdef STATUS_LED_PIN" src/main.cpp
grep -c "watchdog_reboot\|ESP\.restart\|NVIC_SystemReset" src/main.cpp
grep -c "load_samd51_default_rules\|load_.*_default" src/main.cpp
```

All should return `0` after refactoring.

### Compilation Test

```bash
# Build for each platform
pio run -e pico
pio run -e feather_m4_can
pio run -e esp32_t_can485
pio run -e esp32_t_panel
```

All should compile without errors.

### Functional Test

```bash
# Test on physical hardware
# 1. LED should blink/show status correctly
# 2. Reset command should work
# 3. Default rules should load on first boot
```

---

## Code Statistics

| Metric | Before | After |
|--------|--------|-------|
| Lines in main.cpp | 759 | ~720 |
| Platform #ifdefs in main.cpp | 6 | 0 |
| Direct GPIO calls in main.cpp | 6 | 0 |
| LED code locations | 2 | 1 (per board) |
| Files needing update for new platform | 6 | 1 (factory) |
| Lines of pure policy in main loop | ~200 | ~180 |

---

This refactoring improves testability, extensibility, and maintainability while keeping the same functionality.

# src/main.cpp Audit Report - Complete Documentation

## Quick Summary

**Status:** CRITICAL VIOLATIONS FOUND (4 violations)

The `src/main.cpp` file violates the board abstraction layer design by containing **board-specific code that should be delegated to `BoardInterface` implementations**.

### Key Violations:

1. **LED blinking logic** in main loop (lines 142-153) - **CRITICAL**
2. **LED setup** in setup function (lines 56-63) - **MEDIUM**
3. **Platform-specific reset** in command handler (lines 506-512) - **HIGH**
4. **Platform-specific default rules** loading (lines 123-132) - **MEDIUM**

---

## Report Files

This audit consists of four detailed documents:

### 1. [AUDIT_SUMMARY.txt](AUDIT_SUMMARY.txt) - START HERE
**Purpose:** Executive summary with key findings and impact analysis

**Contains:**
- Overall status and severity level
- Key findings (1-4) with brief explanations
- Current vs. correct architecture diagrams
- Impact analysis (what problems this causes)
- Priority fix order
- Verification checklist
- Files affected

**Read time:** 5-10 minutes

**Best for:** Quick overview of what's wrong and why

---

### 2. [AUDIT_CODE_VIOLATIONS.txt](AUDIT_CODE_VIOLATIONS.txt) - TECHNICAL DETAILS
**Purpose:** Line-by-line analysis of every violation with code snippets

**Contains:**
- Violation #1: LED Setup (lines 56-63)
  - Problem analysis
  - Correct pattern
  - Impact
- Violation #2: LED Blinking (lines 142-153) - CRITICAL
  - Problem analysis
  - Correct pattern
  - Impact
- Violation #3: Platform-Specific Reset (lines 506-512)
  - Problem analysis
  - Correct pattern
  - Impact
- Violation #4: Platform-Specific Default Rules (lines 123-132)
  - Problem analysis
  - Correct pattern
  - Impact
- Summary table of violations
- What SHOULD be in main.cpp (allowed code)
- Validation commands for grep

**Read time:** 10-15 minutes

**Best for:** Understanding exactly what's wrong, where, and why

---

### 3. [AUDIT_MAIN_CPP.md](AUDIT_MAIN_CPP.md) - COMPREHENSIVE AUDIT
**Purpose:** Complete audit with fixes, architecture, and verification

**Contains:**
- Executive summary
- All 4 violations with detailed analysis
- Correct abstraction pattern explanation
- Step-by-step fixes for all violations
- Summary table of violations
- Architecture benefits after fixes
- Files to modify by priority
- Verification checklist

**Read time:** 15-20 minutes

**Best for:** Complete understanding and planning the fix

---

### 4. [AUDIT_REFACTORING_EXAMPLES.md](AUDIT_REFACTORING_EXAMPLES.md) - IMPLEMENTATION GUIDE
**Purpose:** Complete before/after code examples for fixing violations

**Contains:**
- Example 1: LED Blinking - The Critical Violation
  - Before code (incorrect)
  - After code (correct) with 6 implementation steps
  - Benefits table
- Example 2: Platform-Specific Reset
  - Before code (incorrect)
  - After code (correct) with 5 implementation steps
- Example 3: Platform-Specific Default Rules
  - Before code (incorrect)
  - After code (correct) with 3 implementation steps
- Summary of refactoring benefits
- Verification checklist
- Code statistics

**Read time:** 20-30 minutes

**Best for:** Actually implementing the fixes (copy-paste ready code)

---

## How to Use These Documents

### For Quick Understanding (15 min)
1. Read [AUDIT_SUMMARY.txt](AUDIT_SUMMARY.txt)
2. Look at violation table in [AUDIT_CODE_VIOLATIONS.txt](AUDIT_CODE_VIOLATIONS.txt)

### For Planning the Fix (30 min)
1. Read [AUDIT_SUMMARY.txt](AUDIT_SUMMARY.txt) for overview
2. Read [AUDIT_MAIN_CPP.md](AUDIT_MAIN_CPP.md) for complete analysis
3. Review fix priority order

### For Implementing the Fix (2-3 hours)
1. Read [AUDIT_REFACTORING_EXAMPLES.md](AUDIT_REFACTORING_EXAMPLES.md)
2. Follow step-by-step implementations
3. Use provided code snippets
4. Use verification checklist to confirm

### For Code Review (10-15 min)
1. Read [AUDIT_CODE_VIOLATIONS.txt](AUDIT_CODE_VIOLATIONS.txt)
2. Check against verification checklist in [AUDIT_SUMMARY.txt](AUDIT_SUMMARY.txt)

---

## Violation Breakdown

### Violation #1: LED Setup in setup() - MEDIUM
**Lines:** 56-63 in src/main.cpp
**Violation Type:** Platform-specific GPIO code in main
**Impact:** Cannot test LED setup, adding boards requires modifying main.cpp
**Fix Location:** Move to `BoardInterface::initialize()`

```cpp
// BEFORE (in main.cpp):
#ifdef STATUS_LED_PIN
  if (STATUS_LED_PIN != 0) {
    pinMode(STATUS_LED_PIN, OUTPUT);
  }
#elif defined(LED_BUILTIN)
  pinMode(LED_BUILTIN, OUTPUT);
#endif

// AFTER (in board implementations):
bool TCAN485Board::initialize(ActionManagerBase* action_manager) {
    neopixel_ = new Adafruit_NeoPixel(...);
    neopixel_->begin();
    return true;
}
```

---

### Violation #2: LED Blinking in loop() - CRITICAL
**Lines:** 142-153 in src/main.cpp
**Violation Type:** Board-specific code in hot main loop with platform conditionals
**Impact:** MOST CRITICAL - Direct GPIO in main loop, different LED types can't coexist
**Fix Location:** Move to `BoardInterface::update_periodic()`

```cpp
// BEFORE (in main.cpp loop):
#ifdef STATUS_LED_PIN
  if (STATUS_LED_PIN != 0) {
    digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
  }
#elif defined(LED_BUILTIN)
  digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
#endif

// AFTER (in board implementations):
void TCAN485Board::update_periodic() {
    static unsigned long last_blink = 0;
    if (millis() - last_blink > 1000) {
        neopixel_->setPixelColor(0, get_status_color());
        neopixel_->show();
        last_blink = millis();
    }
}
```

---

### Violation #3: Platform-Specific Reset - HIGH
**Lines:** 506-512 in src/main.cpp
**Violation Type:** Platform implementation details in command handler
**Impact:** Adding new platform requires modifying main.cpp
**Fix Location:** Delegate to `ActionManagerBase::reset()`

```cpp
// BEFORE (in main.cpp):
#ifdef PLATFORM_RP2040
  watchdog_reboot(0, 0, 0);
#elif defined(PLATFORM_ESP32)
  ESP.restart();
#else
  NVIC_SystemReset();
#endif

// AFTER (in main.cpp):
if (action_manager) {
    action_manager->reset();
}

// AFTER (in each platform's action manager):
bool RP2040ActionManager::reset() {
    watchdog_reboot(0, 0, 0);
    return true;
}
```

---

### Violation #4: Platform-Specific Default Rules - MEDIUM
**Lines:** 123-132 in src/main.cpp
**Violation Type:** Non-extensible platform handling (only SAMD51)
**Impact:** RP2040 and ESP32 don't support default rules
**Fix Location:** Use `ActionManagerFactory::load_platform_default_rules()`

```cpp
// BEFORE (in main.cpp):
#ifdef PLATFORM_SAMD51
  loaded = load_samd51_default_rules(action_manager);
#endif

// AFTER (in main.cpp):
loaded = ActionManagerFactory::load_platform_default_rules(action_manager);

// AFTER (in factory):
static uint8_t load_platform_default_rules(ActionManagerBase* manager) {
    #ifdef PLATFORM_SAMD51
        return load_samd51_default_rules(manager);
    #elif defined(PLATFORM_RP2040)
        return load_rp2040_default_rules(manager);
    #elif defined(PLATFORM_ESP32)
        return load_esp32_default_rules(manager);
    #else
        return 0;
    #endif
}
```

---

## Architecture Overview

### Current (Partially Broken) Architecture
```
src/main.cpp
├─ ❌ LED blinking code (should be in BoardInterface)
├─ ❌ LED setup code (should be in BoardInterface)
├─ ❌ Platform-specific reset (should be in ActionManager)
├─ ❌ Platform-specific rules (should be in Factory)
├─ ✅ CAN interface creation (correct - via factory)
├─ ✅ Action manager creation (correct - via factory)
└─ ✅ Command routing (correct - delegates to managers)

BoardInterface (exists but not fully used)
├─ initialize() - used for setup
├─ update_periodic() - exists but not called from main
└─ register_custom_commands() - used
```

### Target (Correct) Architecture
```
src/main.cpp (pure policy, no implementation)
├─ Serial setup
├─ CAN factory creation ✅
├─ Action manager factory creation ✅
├─ Board factory creation (NEW)
└─ Main loop:
   ├─ can_interface (hardware abstraction)
   ├─ action_manager->update_periodic() (actions)
   └─ board_interface->update_periodic() (NEW: board-specific updates)

BoardInterface (fully utilized)
├─ initialize() - all board setup here
├─ update_periodic() - LED blinking, display updates
└─ register_custom_commands() - board-specific commands

ActionManagerBase
└─ reset() - platform-specific reset (NEW virtual method)

ActionManagerFactory
└─ load_platform_default_rules() - extensible rule loading (NEW)
```

---

## Priority Fix Order

### CRITICAL (Do First)
- [ ] Remove LED blink from main loop (line 142-153)
- [ ] Implement `BoardInterface::update_periodic()` for all boards
- [ ] Call `board_interface->update_periodic()` in main loop

### HIGH (Do Second)
- [ ] Add `ActionManagerBase::reset()` virtual method
- [ ] Implement reset() in all platform managers
- [ ] Remove reset #ifdefs from main.cpp

### MEDIUM (Do Third)
- [ ] Create `ActionManagerFactory::load_platform_default_rules()`
- [ ] Remove PLATFORM_SAMD51 #ifdef from main.cpp
- [ ] Create DefaultBoard for generic boards

### NICE-TO-HAVE (Do Last)
- [ ] Add documentation for board interface
- [ ] Create examples for new board implementations

---

## Verification Checklist

After implementing fixes, verify:

```
Automated Checks:
[ ] grep -c "digitalWrite" src/main.cpp  → 0
[ ] grep -c "digitalRead" src/main.cpp   → 0
[ ] grep -c "pinMode" src/main.cpp       → 0
[ ] grep -c "^[[:space:]]*#ifdef PLATFORM_" src/main.cpp  → 0
[ ] grep -c "^[[:space:]]*#ifdef BOARD_" src/main.cpp     → 0
[ ] grep -c "^[[:space:]]*#ifdef STATUS_LED_PIN" src/main.cpp  → 0

Compilation:
[ ] pio run -e pico (compiles)
[ ] pio run -e feather_m4_can (compiles)
[ ] pio run -e esp32_t_can485 (compiles)
[ ] pio run -e esp32_t_panel (compiles)

Functional:
[ ] Upload to Pico → LED blinks correctly
[ ] Upload to Feather M4 CAN → LED blinks correctly
[ ] Upload to T-CAN485 → NeoPixel status shows correctly
[ ] Upload to T-Panel → Display updates correctly
[ ] Reset command works on all platforms
[ ] Default rules load on first boot (SAMD51, RP2040, ESP32)
```

---

## Files to Modify

### Must Modify (Critical Path)
1. **src/main.cpp**
   - Remove LED setup (lines 56-63)
   - Remove LED blinking (lines 142-153)
   - Add board interface initialization
   - Add board interface periodic update
   - Update reset handler
   - Update default rules loading

2. **src/boards/t_can485/board_impl.cpp**
   - Implement `initialize()` with NeoPixel setup
   - Implement `update_periodic()` with LED blink logic

3. **src/boards/t_panel/board_impl.cpp**
   - Implement `initialize()` with display/touch setup
   - Implement `update_periodic()` with display updates

4. **src/actions/action_manager_base.h**
   - Add virtual `reset()` method

5. **src/capabilities/*/[platform]_action_manager.h/cpp**
   - Implement `reset()` for each platform

### Should Create (Extensibility)
1. **src/boards/default/board_impl.h**
   - DefaultBoard class for generic boards

2. **src/boards/default/board_impl.cpp**
   - DefaultBoard implementation with simple LED blink

3. **src/actions/action_manager_factory.h**
   - Add `load_platform_default_rules()` factory method

### No Changes Needed (Already Correct)
- src/boards/board_interface.h
- src/boards/board_factory.cpp
- src/hal/* (all HAL files)
- src/capabilities/*/[platform]_action_manager.h (except adding reset())

---

## Key Design Principles Violated

### Single Responsibility Principle
- main.cpp has too many responsibilities (LED, GPIO, platform-specific logic)
- Should only coordinate, not implement

### Abstraction Inversion
- main.cpp depends on concrete implementations (GPIO, platform APIs)
- Should depend on abstract interfaces (BoardInterface, ActionManagerBase)

### Don't Repeat Yourself (DRY)
- LED blinking logic hardcoded in multiple places
- Default rules loading has platform-specific duplication

### Factory Pattern (Not Fully Utilized)
- BoardFactory exists but not used
- ActionManagerFactory exists but not used for default rules
- Should use factories for all polymorphic creation

---

## Resources

### Code Standards
- See [CLAUDE.md](CLAUDE.md) for project architecture guidelines
- See `src/boards/board_interface.h` for BoardInterface contract

### Examples
- See `src/boards/t_can485/board_impl.h` for reference board implementation
- See `src/boards/t_panel/board_impl.h` for complex board with peripherals

### Testing
- After fix, update mocks to use BoardInterface
- Create unit tests for each BoardInterface implementation
- Mock board interface in main loop tests

---

## Questions?

Refer to:
1. **"What's wrong?"** → [AUDIT_SUMMARY.txt](AUDIT_SUMMARY.txt)
2. **"Where exactly?"** → [AUDIT_CODE_VIOLATIONS.txt](AUDIT_CODE_VIOLATIONS.txt)
3. **"How do I fix it?"** → [AUDIT_MAIN_CPP.md](AUDIT_MAIN_CPP.md)
4. **"Show me the code!"** → [AUDIT_REFACTORING_EXAMPLES.md](AUDIT_REFACTORING_EXAMPLES.md)

---

## Document History

- **Date Created:** 2025-10-30
- **Auditor:** Claude Code (Embedded Systems Architecture)
- **Status:** CRITICAL VIOLATIONS - Action Required
- **Severity:** HIGH
- **Recommendation:** Fix before implementing additional board support

---

**Next Step:** Start with [AUDIT_SUMMARY.txt](AUDIT_SUMMARY.txt) for a quick overview, then review [AUDIT_REFACTORING_EXAMPLES.md](AUDIT_REFACTORING_EXAMPLES.md) for implementation details.

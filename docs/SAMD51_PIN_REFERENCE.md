# SAMD51 Feather M4 CAN - Pin Capabilities Reference

**Board:** Adafruit Feather M4 CAN Express
**MCU:** ATSAMD51J19 (Cortex-M4F @ 120MHz)
**Date:** 2025-01-27

---

## Pin Overview

### Hardware Reserved Pins (Cannot Be Reconfigured)

| Pin | Function | Notes |
|-----|----------|-------|
| PA22 | CAN TX | Hardwired to MCP2562 CAN transceiver |
| PA23 | CAN RX | Hardwired to MCP2562 CAN transceiver |
| PA24 | USB D- | USB peripheral, do not use |
| PA25 | USB D+ | USB peripheral, do not use |
| PA27 | USB Host | USB host mode, typically unused |
| PA28 | USB Host | USB host mode, typically unused |

### NeoPixel (Built-in)

| Pin | Function | Notes |
|-----|----------|-------|
| 8 (PB03) | NeoPixel Data | Built-in RGB LED, can be disabled to free pin |

### Default I2C (Wire) - SERCOM2

| Arduino Pin | SAMD51 Pin | Function | Alt Function |
|-------------|------------|----------|--------------|
| SDA | PA12 | I2C Data | SERCOM2 PAD[0], SERCOM4 PAD[1] (SPI MOSI conflict!) |
| SCL | PA13 | I2C Clock | SERCOM2 PAD[1], SERCOM4 PAD[0] (SPI SCK conflict!) |

**IMPORTANT:** Default I2C and SPI share SERCOM pins! Choose one or reconfigure.

### Analog Inputs (ADC)

| Arduino Pin | SAMD51 Pin | ADC Channel | DAC | Notes |
|-------------|------------|-------------|-----|-------|
| A0 | PA02 | AIN[0] | Yes (DAC0) | 12-bit ADC, 10-bit DAC |
| A1 | PA05 | AIN[5] | Yes (DAC1) | 12-bit ADC, 10-bit DAC |
| A2 | PB08 | AIN[2] | No | 12-bit ADC only |
| A3 | PB09 | AIN[3] | No | 12-bit ADC only |
| A4 | PA04 | AIN[4] | No | 12-bit ADC only |
| A5 | PA06 | AIN[6] | No | 12-bit ADC only |

**Note:** All analog pins can also be used as digital GPIO.

### PWM-Capable Pins (TCC - Timer Counter for Control)

Most digital pins support PWM via TCC0, TCC1, or TCC2:

| TCC Unit | Available Pins | Channels | Max Frequency |
|----------|----------------|----------|---------------|
| TCC0 | Many GPIO | 4 + 4 (8 total) | Up to 48 MHz |
| TCC1 | Many GPIO | 4 + 4 (8 total) | Up to 48 MHz |
| TCC2 | Some GPIO | 2 (limited) | Up to 48 MHz |

**Common PWM Pins:**
- D5, D6, D9, D10, D11, D12, D13 (most reliable)
- A0-A5 (can do PWM if not using ADC)

**PWM Limitations:**
- Pins on same TCC channel share frequency (but can have different duty cycles)
- Maximum practical frequency: ~100 kHz for smooth output
- Resolution decreases at higher frequencies

### I2C Alternate Configurations (SERCOM Flexibility)

SAMD51 has 6 SERCOM modules that can each be configured as I2C, SPI, or UART:

| SERCOM | Possible SDA/SCL Pins | Conflicts | Recommended Use |
|--------|----------------------|-----------|-----------------|
| SERCOM0 | PA08/PA09 | None | Safe alternative I2C |
| SERCOM1 | PA16/PA17 | None | Safe alternative I2C |
| SERCOM2 | PA12/PA13 | **Default I2C, conflicts with SPI!** | Use this OR SPI, not both |
| SERCOM3 | PA20/PA21 | None | Safe alternative I2C |
| SERCOM4 | PA12/PA14 | Conflicts with default I2C | Typically SPI |
| SERCOM5 | PB16/PB17 | None | Safe alternative I2C |

**Recommendation:** Use SERCOM2 (default) unless you need SPI, then use SERCOM0, 1, 3, or 5.

---

## Pin Validation Rules for Firmware

### I2C Pin Validation

```cpp
bool is_valid_i2c_pin(uint8_t pin, bool is_sda) {
    // Check against hardware reserved pins
    if (pin == 22 || pin == 23) return false;  // CAN pins
    if (pin >= 24 && pin <= 28) return false;  // USB pins

    // Check if pin supports SERCOM
    // (This requires SERCOM capability lookup table)
    return check_sercom_capability(pin, is_sda);
}
```

### PWM Pin Validation

```cpp
bool is_valid_pwm_pin(uint8_t pin) {
    // Check against hardware reserved
    if (pin == 22 || pin == 23) return false;  // CAN pins
    if (pin >= 24 && pin <= 28) return false;  // USB pins

    // Check if pin has TCC capability
    return has_tcc_capability(pin);
}
```

### ADC Pin Validation

```cpp
bool is_valid_adc_pin(uint8_t pin) {
    // Only specific pins have ADC
    const uint8_t adc_pins[] = {A0, A1, A2, A3, A4, A5};
    for (uint8_t adc_pin : adc_pins) {
        if (pin == adc_pin) return true;
    }
    return false;
}
```

### Pin Conflict Detection

```cpp
enum PinUsage {
    PIN_UNUSED,
    PIN_GPIO,
    PIN_PWM,
    PIN_ADC,
    PIN_I2C_SDA,
    PIN_I2C_SCL,
    PIN_SPI,
    PIN_CAN
};

// Track what each pin is currently used for
PinUsage pin_usage_map[32];

bool can_use_pin(uint8_t pin, PinUsage intended_use) {
    PinUsage current = pin_usage_map[pin];

    // Check for conflicts
    if (current == PIN_UNUSED) return true;
    if (current == intended_use) return true;  // Already in this mode

    // Some combinations are compatible
    if (current == PIN_GPIO && intended_use == PIN_ADC) return true;

    // Otherwise it's a conflict
    Serial.printf("ERROR: Pin %d already in use as %s\n", pin, usage_to_string(current));
    return false;
}
```

---

## Implementation Recommendations

### 1. Pin Capability Query System

Create a compile-time pin capability table:

```cpp
struct PinCapabilities {
    uint8_t pin_number;
    bool can_gpio;
    bool can_pwm;
    bool can_adc;
    bool can_dac;
    bool can_i2c_sda;
    bool can_i2c_scl;
    uint8_t sercom_pad;  // SERCOM pad number if applicable
    uint8_t tcc_channel; // TCC channel if PWM capable
};

const PinCapabilities SAMD51_PIN_CAPS[] = {
    {A0, true, true, true, true, false, false, 0, 0},
    {A1, true, true, true, true, false, false, 0, 0},
    // ... complete table
};
```

### 2. Error Logging

All pin validation errors should log to Serial:

```cpp
#define LOG_PIN_ERROR(pin, reason) \
    Serial.printf("PIN_ERROR: Pin %d - %s\n", pin, reason)

// Usage examples:
LOG_PIN_ERROR(22, "Cannot use CAN TX pin for GPIO");
LOG_PIN_ERROR(13, "Pin already in use for PWM");
LOG_PIN_ERROR(99, "Invalid pin number (out of range)");
```

### 3. Runtime Pin Allocation

Track pin usage at runtime:

```cpp
class PinManager {
    static PinUsage usage_map_[32];

public:
    static bool allocate_pin(uint8_t pin, PinUsage usage);
    static void free_pin(uint8_t pin);
    static PinUsage get_usage(uint8_t pin);
    static bool is_available(uint8_t pin, PinUsage intended);
};
```

---

## Common Pin Configuration Mistakes

### ❌ Mistake 1: Using CAN pins for GPIO
```cpp
// WRONG: CAN pins are hardwired
pinMode(22, OUTPUT);  // PA22 is CAN TX, will not work!
```

### ❌ Mistake 2: I2C + SPI on default pins
```cpp
// WRONG: Both use same SERCOM
Wire.begin();         // Uses PA12/PA13
SPI.begin();          // Also wants PA12/PA13 → CONFLICT!
```

### ❌ Mistake 3: Assuming all pins support PWM
```cpp
// WRONG: Not all pins have TCC
analogWrite(24, 128);  // PA24 is USB, cannot do PWM!
```

### ✅ Correct: Validate before use
```cpp
if (!pin_manager.is_available(pin, PIN_PWM)) {
    LOG_PIN_ERROR(pin, "Pin does not support PWM");
    return false;
}
analogWrite(pin, duty);
```

---

## Platform-Specific Notes

### SAMD51 Advantages
- ✅ Very flexible pin multiplexing (SERCOM can be reassigned)
- ✅ High-resolution PWM (up to 16-bit)
- ✅ True 12-bit ADC (not oversampled)
- ✅ Hardware DAC on 2 pins

### SAMD51 Limitations
- ❌ I2C and SPI share pins by default (must choose one or reconfigure)
- ❌ CAN pins cannot be repurposed
- ❌ Only 6 SERCOM modules (limits simultaneous peripherals)
- ❌ PWM channels on same TCC share frequency

---

## Quick Reference: Safe Pins for Common Uses

### GPIO Digital I/O (Safe for any use)
- D5, D6, D9, D10, D11, D12, D13

### PWM Output (Confirmed TCC availability)
- D5, D6, D9, D10, D11, D12, D13

### ADC Input (12-bit)
- A0, A1, A2, A3, A4, A5

### DAC Output (10-bit)
- A0 (DAC0), A1 (DAC1)

### I2C (Default, safest)
- SDA (PA12), SCL (PA13)

### Avoid These Pins
- 22, 23 (CAN - hardwired)
- 24, 25, 27, 28 (USB - system use)

---

**Next Steps:**
1. Implement pin capability table
2. Add runtime pin usage tracking
3. Validate all pin numbers in action handlers
4. Log errors to Serial when invalid pins used
5. Document per-platform pin maps in action definitions

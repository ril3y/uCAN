# Phase 1 Implementation TODO

**Goal:** Implement data buffer system + I2C + PWM enhancements + pin validation

**Target:** Production-ready firmware with comprehensive multi-sensor support

---

## Priority 1: Foundation (Data Buffer System)

### Task 1.1: Create Action Data Buffer Class
**File:** `src/actions/action_data_buffer.h`
**File:** `src/actions/action_data_buffer.cpp`

```cpp
class ActionDataBuffer {
private:
    uint8_t buffer_[8];
    bool slot_used_[8];

public:
    bool write(uint8_t slot, const uint8_t* data, uint8_t length);
    const uint8_t* read_all(uint8_t& valid_length);
    void clear();
    uint8_t get_used_length() const;
    bool is_slot_used(uint8_t slot) const;
};
```

**Tests:**
- [ ] Write single byte to buffer
- [ ] Write multi-byte value (uint16, uint32)
- [ ] Write to multiple slots
- [ ] Read buffer with correct length
- [ ] Clear buffer resets all slots
- [ ] Boundary checks (slot >= 8)

---

## Priority 2: Pin Management System

### Task 2.1: Pin Capability Database (SAMD51)
**File:** `src/capabilities/samd51/samd51_pin_caps.h`
**File:** `src/capabilities/samd51/samd51_pin_caps.cpp`

```cpp
struct PinCapabilities {
    uint8_t pin_number;
    bool can_gpio;
    bool can_pwm;
    bool can_adc;
    bool can_dac;
    bool can_i2c_sda;
    bool can_i2c_scl;
    uint8_t sercom_pad;     // SERCOM configuration
    uint8_t tcc_channel;    // TCC channel for PWM
};

const PinCapabilities* get_pin_capabilities(uint8_t pin);
bool validate_pin_for_mode(uint8_t pin, PinMode mode);
```

**Data to populate:**
- [ ] All 23 GPIO pins with capabilities
- [ ] CAN pins marked as reserved (PA22, PA23)
- [ ] USB pins marked as reserved (PA24, PA25)
- [ ] ADC pins (A0-A5)
- [ ] DAC pins (A0, A1)
- [ ] PWM-capable pins with TCC channel mapping
- [ ] I2C-capable pins with SERCOM pad mapping

### Task 2.2: Pin Usage Tracker
**File:** `src/actions/pin_manager.h`
**File:** `src/actions/pin_manager.cpp`

```cpp
enum PinMode {
    PIN_UNUSED,
    PIN_GPIO_INPUT,
    PIN_GPIO_OUTPUT,
    PIN_PWM,
    PIN_ADC,
    PIN_DAC,
    PIN_I2C_SDA,
    PIN_I2C_SCL,
    PIN_RESERVED
};

class PinManager {
private:
    PinMode usage_map_[32];

public:
    bool allocate_pin(uint8_t pin, PinMode mode);
    void free_pin(uint8_t pin);
    PinMode get_usage(uint8_t pin);
    bool is_available(uint8_t pin, PinMode intended_mode);
    void log_pin_status();  // Debug: print all pin allocations
};
```

**Tests:**
- [ ] Allocate pin successfully
- [ ] Reject allocation of reserved pin (CAN, USB)
- [ ] Detect pin conflicts (already in use)
- [ ] Free pin and reallocate
- [ ] Log pin status to Serial

### Task 2.3: Error Logging System
**File:** `src/utils/pin_error_logger.h`

```cpp
#define LOG_PIN_ERROR(pin, reason) \
    Serial.printf("[PIN_ERROR] Pin %d: %s\n", pin, reason)

#define LOG_PIN_WARNING(pin, reason) \
    Serial.printf("[PIN_WARNING] Pin %d: %s\n", pin, reason)

#define LOG_PIN_INFO(pin, reason) \
    Serial.printf("[PIN_INFO] Pin %d: %s\n", pin, reason)
```

**Examples:**
- `LOG_PIN_ERROR(22, "Cannot use CAN TX pin for GPIO");`
- `LOG_PIN_ERROR(13, "Pin already allocated for PWM");`
- `LOG_PIN_WARNING(A0, "Pin shared between ADC and DAC");`

**Tests:**
- [ ] Errors appear on Serial output
- [ ] Format is correct for parsing by UI

---

## Priority 3: Abstract HAL Interfaces

### Task 3.1: I2C Abstract Interface
**File:** `src/hal/i2c_interface.h`

```cpp
class I2CInterface {
public:
    virtual ~I2CInterface() {}
    virtual bool initialize(uint8_t sda_pin, uint8_t scl_pin, uint32_t frequency_hz = 100000) = 0;
    virtual bool write(uint8_t address, uint8_t reg, const uint8_t* data, uint8_t length) = 0;
    virtual bool read(uint8_t address, uint8_t reg, uint8_t* data, uint8_t length) = 0;
    virtual bool is_valid_sda_pin(uint8_t pin) const = 0;
    virtual bool is_valid_scl_pin(uint8_t pin) const = 0;
    virtual const char* get_last_error() const = 0;
};
```

### Task 3.2: SAMD51 I2C Implementation
**File:** `src/hal/samd51_i2c.h`
**File:** `src/hal/samd51_i2c.cpp`

```cpp
class SAMD51_I2C : public I2CInterface {
private:
    uint8_t sda_pin_;
    uint8_t scl_pin_;
    uint8_t sercom_instance_;
    char last_error_[64];

    bool configure_sercom(uint8_t sda, uint8_t scl);

public:
    bool initialize(uint8_t sda_pin, uint8_t scl_pin, uint32_t frequency_hz) override;
    bool write(uint8_t address, uint8_t reg, const uint8_t* data, uint8_t length) override;
    bool read(uint8_t address, uint8_t reg, uint8_t* data, uint8_t length) override;
    bool is_valid_sda_pin(uint8_t pin) const override;
    bool is_valid_scl_pin(uint8_t pin) const override;
    const char* get_last_error() const override;
};
```

**Implementation Notes:**
- Use Arduino Wire library as base
- Map pin numbers to SERCOM instances
- Validate pins against capability database
- Log errors when invalid pins used
- Default to SERCOM2 (PA12/PA13) if no pins specified

**Tests:**
- [ ] Initialize with default pins (PA12/PA13)
- [ ] Initialize with alternate SERCOM pins
- [ ] Reject invalid pins (CAN, USB, non-SERCOM)
- [ ] Write to I2C device (test with real sensor if available)
- [ ] Read from I2C device
- [ ] Handle I2C errors gracefully
- [ ] Error logging appears on Serial

### Task 3.3: PWM Abstract Interface
**File:** `src/hal/pwm_interface.h`

```cpp
class PWMInterface {
public:
    virtual ~PWMInterface() {}
    virtual bool configure(uint8_t pin, uint32_t frequency_hz, uint8_t duty_percent, uint8_t resolution_bits = 8) = 0;
    virtual bool set_duty(uint8_t pin, uint8_t duty_percent) = 0;
    virtual bool stop(uint8_t pin) = 0;
    virtual bool is_valid_pwm_pin(uint8_t pin) const = 0;
    virtual bool get_config(uint8_t pin, uint32_t& freq, uint8_t& duty) const = 0;
};
```

### Task 3.4: SAMD51 PWM Implementation
**File:** `src/hal/samd51_pwm.h`
**File:** `src/hal/samd51_pwm.cpp`

```cpp
class SAMD51_PWM : public PWMInterface {
private:
    struct PWMConfig {
        uint32_t frequency_hz;
        uint8_t duty_percent;
        uint8_t resolution_bits;
        uint8_t tcc_channel;
    };

    PWMConfig configs_[32];  // One per pin

    bool configure_tcc(uint8_t pin, uint32_t freq, uint8_t resolution);

public:
    bool configure(uint8_t pin, uint32_t frequency_hz, uint8_t duty_percent, uint8_t resolution_bits) override;
    bool set_duty(uint8_t pin, uint8_t duty_percent) override;
    bool stop(uint8_t pin) override;
    bool is_valid_pwm_pin(uint8_t pin) const override;
    bool get_config(uint8_t pin, uint32_t& freq, uint8_t& duty) const override;
};
```

**Implementation Notes:**
- Map pins to TCC channels using capability database
- Support frequency range: 1Hz - 100kHz (practical limit)
- Support resolutions: 8, 10, 12, 16 bit
- Warn if pins on same TCC will share frequency
- Log errors when invalid pins used

**Tests:**
- [ ] Configure PWM with frequency
- [ ] Change duty cycle without changing frequency
- [ ] Multiple pins with different duty, same frequency (same TCC)
- [ ] Stop PWM on pin
- [ ] Reject invalid pins (CAN, USB, non-TCC)
- [ ] Resolution validation (8/10/12/16 only)
- [ ] Frequency limits (1Hz - 100kHz)
- [ ] Error logging

---

## Priority 4: New Action Definitions

### Task 4.1: Update Action Types Enum
**File:** `src/actions/action_types.h`

Add new action types:
```cpp
enum ActionType {
    // ... existing actions ...
    ACTION_PWM_CONFIGURE = 20,
    ACTION_I2C_WRITE = 21,
    ACTION_I2C_READ_BUFFER = 22,
    ACTION_GPIO_READ_BUFFER = 23,
    ACTION_ADC_READ_BUFFER = 24,
    ACTION_BUFFER_SEND = 25,
    ACTION_BUFFER_CLEAR = 26,
};
```

### Task 4.2: Create PWM_CONFIGURE Action
**File:** `src/capabilities/samd51/samd51_action_defs.cpp`

```cpp
static const ParamMapping PWM_CONFIGURE_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin", "action_param"},
    {1, 0, 16, PARAM_UINT16, 1, 100000, "freq_hz", "action_param"},  // 2 bytes
    {3, 0, 8, PARAM_UINT8, 0, 100, "duty_percent", "action_param"},
    {4, 0, 8, PARAM_UINT8, 8, 16, "resolution", "action_param"}  // 8, 10, 12, 16
};

static const ActionDefinition PWM_CONFIGURE_DEF = {
    .action = ACTION_PWM_CONFIGURE,
    .name = "PWM_CONFIGURE",
    .description = "Configure PWM with frequency and resolution",
    .category = "GPIO",
    .trigger_type = "can_msg",
    .param_count = 4,
    .param_map = PWM_CONFIGURE_PARAMS
};
```

### Task 4.3: Create I2C Actions
**File:** `src/capabilities/samd51/samd51_action_defs.cpp`

```cpp
// I2C Write
static const ParamMapping I2C_WRITE_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "sda_pin", "action_param"},
    {1, 0, 8, PARAM_UINT8, 0, 255, "scl_pin", "action_param"},
    {2, 0, 7, PARAM_UINT8, 0, 127, "i2c_addr", "action_param"},
    {3, 0, 8, PARAM_UINT8, 0, 255, "reg_addr", "action_param"},
    {4, 0, 8, PARAM_UINT8, 0, 255, "data", "action_param"}
};

// I2C Read → Buffer
static const ParamMapping I2C_READ_BUFFER_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "sda_pin", "action_param"},
    {1, 0, 8, PARAM_UINT8, 0, 255, "scl_pin", "action_param"},
    {2, 0, 7, PARAM_UINT8, 0, 127, "i2c_addr", "action_param"},
    {3, 0, 8, PARAM_UINT8, 0, 255, "reg_addr", "action_param"},
    {4, 0, 8, PARAM_UINT8, 1, 8, "num_bytes", "action_param"},
    {5, 0, 8, PARAM_UINT8, 0, 7, "buffer_slot", "output_param"}
};
```

### Task 4.4: Create Buffer Actions
```cpp
// GPIO Read → Buffer
static const ParamMapping GPIO_READ_BUFFER_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin", "action_param"},
    {1, 0, 8, PARAM_UINT8, 0, 7, "buffer_slot", "output_param"}
};

// ADC Read → Buffer
static const ParamMapping ADC_READ_BUFFER_PARAMS[] = {
    {0, 0, 8, PARAM_UINT8, 0, 255, "pin", "action_param"},
    {1, 0, 8, PARAM_UINT8, 0, 7, "buffer_slot", "output_param"}
};

// Send Buffer
static const ParamMapping BUFFER_SEND_PARAMS[] = {
    {0, 0, 32, PARAM_UINT32, 0, 0x7FF, "can_id", "output_param"},  // 4 bytes
    {4, 0, 8, PARAM_UINT8, 1, 8, "length", "output_param"},
    {5, 0, 1, PARAM_BOOL, 0, 1, "clear_after", "output_param"}
};
```

### Task 4.5: Implement Action Handlers
**File:** `src/actions/action_manager.cpp`

For each new action, implement handler:

```cpp
bool ActionManager::execute_action(ActionType type, const uint8_t* params) {
    switch (type) {
        case ACTION_PWM_CONFIGURE: {
            uint8_t pin = params[0];
            uint16_t freq = (params[2] << 8) | params[1];
            uint8_t duty = params[3];
            uint8_t resolution = params[4];

            // Validate pin
            if (!pwm_interface->is_valid_pwm_pin(pin)) {
                LOG_PIN_ERROR(pin, "Pin does not support PWM");
                return false;
            }

            // Configure PWM
            return pwm_interface->configure(pin, freq, duty, resolution);
        }

        case ACTION_I2C_READ_BUFFER: {
            uint8_t sda = params[0];
            uint8_t scl = params[1];
            uint8_t addr = params[2];
            uint8_t reg = params[3];
            uint8_t num_bytes = params[4];
            uint8_t slot = params[5];

            // Validate pins
            if (!i2c_interface->is_valid_sda_pin(sda)) {
                LOG_PIN_ERROR(sda, "Invalid SDA pin");
                return false;
            }

            // Initialize I2C
            if (!i2c_interface->initialize(sda, scl)) {
                Serial.println(i2c_interface->get_last_error());
                return false;
            }

            // Read data
            uint8_t data[8];
            if (!i2c_interface->read(addr, reg, data, num_bytes)) {
                Serial.println(i2c_interface->get_last_error());
                return false;
            }

            // Store in buffer
            return action_buffer.write(slot, data, num_bytes);
        }

        // ... implement others
    }
}
```

---

## Priority 5: Update Capabilities

### Task 5.1: Add I2C Capability Flag
**File:** `src/capabilities/board_capabilities.h`

```cpp
enum PlatformCapability {
    // ... existing ...
    CAP_I2C = (1 << 10),   // I2C communication (not I2S!)
};
```

### Task 5.2: Enable I2C Capability for SAMD51
**File:** `src/capabilities/samd51_capabilities.cpp`

```cpp
const BoardCapabilities platform_capabilities = {
    // ... existing fields ...
    .capability_flags = CAP_GPIO_DIGITAL | CAP_GPIO_PWM | CAP_GPIO_ANALOG |
                        CAP_GPIO_DAC | CAP_NEOPIXEL | CAP_CAN_SEND |
                        CAP_FLASH_STORAGE | CAP_I2C,  // ← ADD THIS
    // ...
};
```

### Task 5.3: Update Capability Query
**File:** `src/capabilities/capability_query.cpp`

```cpp
void send_capabilities_json() {
    // ... existing code ...

    if (platform_capabilities.has_capability(CAP_I2C)) {
        features.add("I2C");  // ← ADD THIS (not "I2S"!)
    }

    // ...
}
```

---

## Priority 6: Testing & Validation

### Task 6.1: Unit Tests
- [ ] ActionDataBuffer class tests
- [ ] Pin capability lookup tests
- [ ] Pin manager allocation tests
- [ ] I2C interface tests (with mock device)
- [ ] PWM interface tests
- [ ] Action definition parsing tests

### Task 6.2: Integration Tests
- [ ] Read GPIO + ADC + I2C → buffer → send as CAN
- [ ] Configure PWM with various frequencies
- [ ] Detect pin conflicts (try to use CAN pins)
- [ ] Error logging works correctly
- [ ] All action definitions appear in `get:actiondefs`

### Task 6.3: Hardware Tests (with real board)
- [ ] PWM output on oscilloscope (verify frequency)
- [ ] I2C communication with real sensor (e.g., MPU6050)
- [ ] ADC reading from potentiometer
- [ ] Multi-sensor data collection and CAN send
- [ ] Pin validation rejects invalid pins

---

## Priority 7: Documentation Updates

### Task 7.1: Update PROTOCOL.md
- [ ] Document new action definitions (PWM_CONFIGURE, I2C_*, BUFFER_*)
- [ ] Add examples of buffer-based multi-sensor reading
- [ ] Document pin validation errors
- [ ] Update capabilities response to include I2C

### Task 7.2: Create Examples
**File:** `examples/multi_sensor_read.md`
- Example: Read 3 sensors and send in one CAN message

**File:** `examples/pwm_motor_control.md`
- Example: Variable frequency PWM for motor control

**File:** `examples/i2c_sensor_monitoring.md`
- Example: Read I2C temperature sensor periodically

### Task 7.3: Update Test Documentation
- [ ] Update test suite documentation
- [ ] Add hardware test procedures
- [ ] Document required test equipment

---

## Implementation Order

**Week 1: Foundation**
1. ActionDataBuffer class
2. Pin capability database
3. Pin manager
4. Error logging

**Week 2: HAL Interfaces**
5. I2C abstract interface + SAMD51 implementation
6. PWM abstract interface + SAMD51 implementation
7. Add I2C capability flag

**Week 3: Actions**
8. PWM_CONFIGURE action
9. I2C action definitions
10. Buffer read/send actions
11. Action handlers

**Week 4: Testing & Polish**
12. Unit tests
13. Integration tests
14. Hardware validation
15. Documentation updates
16. Protocol spec updates

---

## Success Criteria

- ✅ All 27 existing tests still pass
- ✅ New actions appear in `get:actiondefs`
- ✅ Pin validation rejects invalid pins with error messages
- ✅ Multi-sensor collection and buffer send works
- ✅ PWM frequency control verified with oscilloscope
- ✅ I2C communication with real sensor successful
- ✅ Documentation complete and accurate
- ✅ No breaking changes to existing protocol

---

## Notes

- Keep all changes backward compatible
- Log errors to Serial for debugging
- Use abstract interfaces for portability
- Validate ALL pin numbers before use
- Test with real hardware, not just simulation

**Ready to start? Begin with Priority 1: ActionDataBuffer class!**

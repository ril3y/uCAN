# Test Organization

## Test Categories

The uCAN test suite follows standard testing terminology:

### 1. Integration Tests (Loopback Mode)

**Marker:** `@pytest.mark.integration`

These tests use CAN loopback mode where messages sent by the firmware are immediately received back. No external CAN devices are required.

**Suitable for:**
- Continuous Integration (GitHub Actions, Jenkins, etc.)
- Automated testing
- Rapid development cycles
- Firmware validation before hardware testing

**What can be tested:**
- Protocol commands (get:*, config:*, etc.)
- Rule management (add, remove, list, edit)
- Message formatting and parsing
- Action triggering via loopback messages
- Error handling
- ACTIONDEF and CAPS responses

**What cannot be tested:**
- Actual hardware I/O (GPIO, NeoPixel, PWM, I2C)
- CAN bus electrical characteristics
- Multi-device CAN interactions
- Real-world timing and performance

**Run integration tests:**
```bash
pytest tests/ -m integration --port COM21
```

### 2. System Tests (Physical CAN Network)

**Marker:** `@pytest.mark.system`

These tests require actual CAN devices on the bus sending real traffic.

**Suitable for:**
- Manual hardware validation
- Integration testing with real devices
- Visual confirmation (NeoPixel colors, GPIO states)
- End-to-end system testing

**What can be tested:**
- All CI/CD tests PLUS:
- GPIO output control
- NeoPixel visual feedback
- PWM generation
- I2C communication with real sensors
- Multi-device CAN interactions
- Real CAN traffic handling

**Run system tests:**
```bash
pytest tests/ -m system --port COM21
```

## Test Execution Modes

### Mode 1: All Tests (Default)
```bash
pytest tests/ --port COM21
```
Runs all tests including both integration and system tests.

### Mode 2: CI/CD Only (Integration Tests)
```bash
pytest tests/ -m integration --port COM21
```
Runs only integration tests with loopback mode. **Ideal for CI/CD pipelines.**

### Mode 3: System Only (End-to-End)
```bash
pytest tests/ -m system --port COM21
```
Runs only system tests requiring physical CAN devices and hardware I/O.

### Mode 4: Non-System (Integration + Protocol)
```bash
pytest tests/ -m "not system" --port COM21
```
Runs all tests that don't require external physical devices.

## Enabling Loopback Mode

### In Firmware

Add `config:mode:loopback` command to enable internal CAN loopback:

```cpp
// SAMD51 CAN Controller
void enable_loopback_mode() {
    CAN0->CCCR.bit.TEST = 1;   // Enable test mode
    CAN0->TEST.bit.LBCK = 1;   // Enable internal loopback
}

void disable_loopback_mode() {
    CAN0->TEST.bit.LBCK = 0;   // Disable loopback
    CAN0->CCCR.bit.TEST = 0;   // Disable test mode
}
```

### In Tests

```python
@pytest.mark.loopback
def test_action_triggering(ser, send_command, read_responses):
    """Test that actions trigger correctly via loopback"""
    # Enable loopback mode
    send_command("config:mode:loopback")

    # Clear any existing rules
    send_command("action:clear")
    time.sleep(0.2)

    # Add a rule
    send_command("action:add:0:0x123:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
    time.sleep(0.2)

    # Send message - will loop back and trigger rule
    send_command("send:0x123:01,02,03")
    time.sleep(0.5)

    # Read responses
    responses = read_responses()

    # Verify looped message received
    can_rx = [r for r in responses if r.startswith("CAN_RX;0x123")]
    assert len(can_rx) >= 1, "Message should be looped back"

    # Verify action executed
    actions = [r for r in responses if r.startswith("ACTION;")]
    assert len(actions) >= 1, "Action should execute on looped message"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: uCAN Firmware Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r tests/requirements.txt

      - name: Build firmware
        run: pio run -e feather_m4_can

      - name: Flash firmware (requires hardware runner)
        run: pio run -e feather_m4_can --target upload

      - name: Run CI/CD tests (loopback only)
        run: pytest tests/ -m loopback --port ${{ secrets.TEST_PORT }} -v
```

## Current Test Coverage

### Integration Tests (CI/CD Compatible)
- ✅ test_basic_commands.py (most tests)
- ✅ test_rule_management.py (all tests)
- ✅ test_can_messaging.py (all tests)
- ✅ test_action_definitions.py (all tests)
- ✅ test_error_handling.py (all tests)
- ✅ test_data_matching.py (most tests)
- ⚠️ test_action_reporting.py (needs loopback support)

### System Tests (Hardware Required)
- ❌ test_gpio_actions.py (requires GPIO visual/electrical verification)
- ❌ test_neopixel.py (requires visual NeoPixel verification)
- ❌ test_pwm_actions.py (requires oscilloscope/PWM meter)
- ❌ test_phase1_i2c.py (requires I2C devices)
- ❌ test_phase1_buffer.py (requires sensors)
- ❌ test_action_execution_reporting.py (currently uses live CAN traffic)

## Migration Path

To convert system tests to integration tests:

1. **Add integration marker:**
```python
@pytest.mark.integration
def test_something(...):
```

2. **Enable loopback at test start:**
```python
send_command("config:mode:loopback")
```

3. **Send message instead of waiting for traffic:**
```python
# Old: Wait for live CAN traffic
time.sleep(2.0)  # Wait for bus activity

# New: Send loopback message
send_command("send:0x123:01,02,03")
time.sleep(0.2)
```

4. **Adjust expectations:**
- System tests check physical outputs (LED colors, pin voltages)
- Integration tests check protocol responses (ACTION messages, STATUS)

## Best Practices

1. **Always clear rules:** Every test should start with `action:clear`
2. **Use integration tests for protocol validation:** Test command parsing, response formats
3. **Use system tests for I/O validation:** Test actual GPIO, NeoPixel, PWM outputs
4. **Tag tests appropriately:** Use `@pytest.mark.integration` or `@pytest.mark.system`
5. **Document requirements:** Note if test needs specific hardware (sensors, CAN devices)

## Future Enhancements

- **Mock GPIO outputs:** Capture GPIO state changes without physical verification
- **Virtual I2C devices:** Simulate I2C sensor responses
- **CAN traffic simulation:** Pre-recorded CAN traffic playback
- **Hardware-in-the-loop:** Automated hardware testing with USB-controlled relay boards

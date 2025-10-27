# uCAN Protocol v2.0 Integration Tests

Comprehensive pytest test suite for validating uCAN firmware Protocol v2.0 implementation against the specification in `docs/PROTOCOL.md`.

## Hardware Requirements

- **Board**: Adafruit Feather M4 CAN (SAMD51)
- **Connection**: USB serial port (e.g., COM21 on Windows, /dev/ttyACM0 on Linux)
- **Baud Rate**: 115200
- **CAN Bus**: Live CAN traffic on IDs 0x100, 0x200, 0x300 (required for some tests)

## Installation

```bash
# Install pytest and dependencies
pip install pytest pytest-timeout pyserial

# Or install from project requirements
pip install -e .
```

## Running Tests

### All Tests

```bash
# Auto-detect serial port
pytest tests/ --port COM21

# Or let pytest auto-discover the port
pytest tests/
```

### Specific Test Files

```bash
pytest tests/test_basic_commands.py --port COM21 -v
pytest tests/test_rule_management.py --port COM21 -v
pytest tests/test_can_messaging.py --port COM21 -v
pytest tests/test_action_definitions.py --port COM21 -v
pytest tests/test_gpio_actions.py --port COM21 -v
pytest tests/test_neopixel.py --port COM21 -v
pytest tests/test_pwm_actions.py --port COM21 -v
pytest tests/test_phase1_i2c.py --port COM21 -v
pytest tests/test_phase1_buffer.py --port COM21 -v
pytest tests/test_data_matching.py --port COM21 -v
pytest tests/test_action_reporting.py --port COM21 -v
pytest tests/test_error_handling.py --port COM21 -v
```

### Platform-Specific

```bash
# Windows
pytest tests/ --port COM21

# Linux
pytest tests/ --port /dev/ttyACM0

# macOS
pytest tests/ --port /dev/tty.usbmodem14201
```

### Custom Options

```bash
# Custom baud rate
pytest tests/ --port COM21 --baud 230400

# Custom timeout
pytest tests/ --port COM21 --timeout 5.0

# Specific test
pytest tests/test_basic_commands.py::TestBasicCommands::test_get_version --port COM21 -v
```

## Test Coverage Summary

### ✅ test_basic_commands.py (12 tests)
- get:version, get:status, get:stats
- get:capabilities (JSON validation, CAN/GPIO objects, features array)
- get:actiondefs (returns multiple, validates schema)
- get:pins
- Protocol version 2.0 validation
- Case-sensitive commands

### ✅ test_rule_management.py (14 tests)
- action:add (fixed and candata parameters)
- action:list format validation
- action:remove (specific rules and non-existent)
- action:edit (update parameters, action type, CAN ID)
- action:clear (remove all rules)
- Auto-assign rule IDs (ID=0)
- PARAM_SOURCE required (v2.0 breaking change)
- Multiple rules on same CAN ID
- Multi-parameter rules (NEOPIXEL RGB)

### ✅ test_can_messaging.py (14 tests)
- send command basic operation
- 8-byte maximum, empty data, single byte
- Extended CAN IDs (29-bit)
- CAN_TX message format (4 fields)
- Timestamp validation and monotonicity
- Hex data case insensitivity
- CAN ID range validation (0x000-0x7FF)
- Error handling for invalid format
- Byte order preservation
- Multiple sends in sequence
- Zero-padded hex bytes

### ✅ test_action_definitions.py (15 tests)
- Unique action IDs and names
- Valid categories (GPIO, PWM, Display, Communication, I2C, Analog, Buffer)
- Meaningful descriptions
- Parameter byte index uniqueness
- Parameter range format (min-max)
- Optional label and hint fields
- Core actions exist (GPIO_SET, CLEAR, TOGGLE, NEOPIXEL)
- Phase 1 actions exist (I2C_WRITE, I2C_READ_BUFFER, PWM_CONFIGURE, buffer system)
- Parameter type/size validation
- Valid JSON in all ACTIONDEFs
- Sequential action IDs

### ✅ test_gpio_actions.py (7 tests)
- GPIO_SET with fixed and candata parameters
- GPIO_CLEAR with fixed parameters
- GPIO_TOGGLE with fixed and candata parameters
- Different pins control
- Rule format validation

### ✅ test_neopixel.py (8 tests)
- Fixed colors (red, green, blue, yellow, purple, cyan)
- candata extraction from live CAN traffic
- Rule format with 4 parameters (R, G, B, brightness)
- Different brightness levels

### ✅ test_pwm_actions.py (4 tests)
- PWM_SET basic command
- PWM_CONFIGURE with fixed parameters (pin, duty, frequency)
- Rule format validation
- Different frequencies (100Hz - 10kHz)

### ✅ test_phase1_i2c.py (4 tests)
- I2C_WRITE command format (addr, reg, value)
- I2C_READ_BUFFER command format (addr, reg, len, slot)
- Parameter validation
- Different read lengths (1-8 bytes)

### ✅ test_phase1_buffer.py (6 tests)
- GPIO_READ_BUFFER command format
- ADC_READ_BUFFER command format
- BUFFER_SEND command format (sends buffer as CAN message)
- BUFFER_CLEAR command format
- Multi-sensor collection workflow
- Buffer slot range validation (0-7)

### ✅ test_data_matching.py (9 tests)
- DATA_LEN filtering by message length
- DATA pattern matching (single and multi-byte)
- DATA_MASK don't care bits
- Wildcard CAN ID (0x000:0x000)
- CAN ID mask range matching
- Combined DATA and DATA_LEN filtering
- Rule format storage validation
- Empty data matching fields

### ✅ test_action_reporting.py (6 tests)
- ACTION message format (5 fields: RULE_ID, ACTION_TYPE, TRIGGER_CAN_ID, STATUS)
- ACTION includes correct CAN ID
- ACTION includes rule ID
- ACTION includes action type
- ACTION status (OK or FAIL)
- Multiple rules generate multiple ACTIONs

### ✅ test_error_handling.py (10 tests)
- Invalid command returns error
- Malformed action:add missing fields
- Missing PARAM_SOURCE fails (v2.0 requirement)
- action:remove non-existent rule
- Invalid CAN ID format
- Invalid hex data bytes
- action:edit non-existent rule
- Invalid parameter values
- Send with too many data bytes (>8)
- Empty command and extra delimiters

## Test Patterns

### Rule Cleanup Pattern

**CRITICAL**: Every test that creates rules MUST follow this pattern to ensure isolation:

```python
def test_something(send_command, read_responses):
    # ALWAYS clear rules first
    send_command("action:clear")
    time.sleep(0.2)

    # Your test logic here
    send_command("action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:candata")
    # ... test assertions ...

    # Optional: Clean up at end too
    send_command("action:clear")
    time.sleep(0.2)
```

### Live Traffic Pattern

Tests requiring CAN traffic use pytest.skip when no traffic is detected:

```python
responses = read_responses(max_lines=100, line_timeout=0.6)
can_rx_messages = [r for r in responses if r.startswith('CAN_RX;')]

if len(can_rx_messages) == 0:
    pytest.skip("No CAN traffic detected - test requires active CAN bus")
```

## Fixtures (from conftest.py)

### Session-Scoped
- `serial_port` - Auto-detects or uses --port argument
- `baud_rate` - Uses --baud argument (default 115200)
- `serial_timeout` - Uses --timeout argument (default 2.0s)

### Function-Scoped
- `ser` - Serial connection (opens/closes per test)
- `send_command(cmd)` - Send command to device
- `read_response()` - Read single line
- `read_responses(max_lines, line_timeout)` - Read multiple lines
- `wait_for_response(prefix, timeout)` - Wait for specific message type
- `parse_json_response(response)` - Parse JSON from protocol messages
- `flush_serial()` - Clear serial buffers
- `get_action_definitions()` - Get all ACTIONDEFs
- `verify_status_ok(substring, timeout)` - Verify STATUS response
- `clear_rules()` - Clear all rules (IDs 1-30)

## Expected Results

### With Live CAN Traffic
All tests should pass. Tests requiring CAN traffic will execute and validate ACTION messages.

### Without Live CAN Traffic
- Basic command tests: ✅ PASS
- Rule management tests: ✅ PASS
- CAN messaging tests: ✅ PASS
- Action definition tests: ✅ PASS
- GPIO/PWM/I2C/Buffer tests: ✅ PASS (command validation only)
- Data matching tests: ✅ PASS (rule format validation)
- Action reporting tests: ⏭️ SKIP (requires live CAN traffic)
- Error handling tests: ✅ PASS

### Expected Skips
```
tests/test_action_reporting.py::...::test_action_message_format SKIPPED (No CAN traffic)
tests/test_gpio_actions.py::...::test_gpio_set_with_candata_parameter SKIPPED (No CAN traffic)
tests/test_neopixel.py::...::test_neopixel_with_candata_extraction SKIPPED (No CAN traffic)
```

## Troubleshooting

### Port Connection Issues

**Problem:** `SerialException: could not open port`

**Solutions:**
- Verify board is connected: `ls /dev/ttyACM*` (Linux) or check Device Manager (Windows)
- Close other programs using the port (TUI, serial monitor)
- Try different USB cable or port
- Run with `--port` explicitly specified

### Test Failures

**Problem:** Tests fail with timeout

**Solutions:**
- Increase timeout: `pytest tests/ --timeout 5.0`
- Check CAN bus connection and termination
- Verify firmware is running (send `get:version` manually)
- Reset board and retry

**Problem:** "No CAN traffic detected" skips

**Solutions:**
- This is expected behavior without live CAN traffic
- Connect to active CAN bus with messages on 0x100, 0x200, 0x300
- Or run generator: `python scripts/can_traffic_generator.py`

### Firmware Issues

**Problem:** Commands not recognized

**Solutions:**
- Verify Protocol v2.0 firmware: `get:version` should return "Protocol: 2.0"
- Re-flash firmware: `pio run -e feather_m4_can --target upload`
- Check for serial buffer corruption (reset board)

### Linux Permissions

**Problem:** Permission denied on /dev/ttyACM0

**Solution:**
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

## Test Statistics

- **Total Test Files**: 12
- **Total Test Cases**: ~110+
- **Coverage**: All major Protocol v2.0 features
- **Execution Time**: ~2-5 minutes (with live CAN traffic)
- **Execution Time**: ~1-2 minutes (without CAN traffic, some skips)

## Continuous Integration

### GitHub Actions Example

```yaml
name: Hardware Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: self-hosted  # Requires self-hosted runner with hardware
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install pytest pyserial
      - name: Run hardware tests
        run: pytest tests/ --port /dev/ttyACM0 -v
```

## Contributing

When adding new tests:

1. Follow existing test structure and naming conventions
2. Use descriptive test names: `test_{what}_{expected_result}`
3. Add docstrings explaining what is being tested
4. Clear rules at the start of each test (`action:clear`)
5. Use `pytest.skip()` when hardware/traffic requirements not met
6. Update this README with new test coverage

## References

- **Protocol Specification**: `docs/PROTOCOL.md`
- **Firmware Source**: `src/`
- **Test Fixtures**: `tests/conftest.py`
- **Existing Tests**: `tests/test_action_execution_reporting.py`

## License

Same as uCAN project (see top-level LICENSE file).

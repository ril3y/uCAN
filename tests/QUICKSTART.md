# Quick Start Guide - uCAN Test Suite

Fast reference for running the uCAN firmware test suite.

## Prerequisites

```bash
# Install dependencies
pip install pytest pyserial

# Or install from project
pip install -e .
```

## Quick Commands

### Run All Tests
```bash
# Auto-detect port
pytest tests/ -v

# Specific port
pytest tests/ -v --port COM21              # Windows
pytest tests/ -v --port /dev/ttyACM0       # Linux
pytest tests/ -v --port /dev/cu.usbmodem*  # macOS
```

### Run Specific Test Categories
```bash
# Action definitions only
pytest tests/test_action_definitions.py -v --port COM21

# Rule management only
pytest tests/test_rule_management.py -v --port COM21

# CAN data extraction only (visual verification needed)
pytest tests/test_can_data_extraction.py -v --port COM21

# Protocol compliance only
pytest tests/test_protocol_v2_compliance.py -v --port COM21

# Edge cases only
pytest tests/test_edge_cases.py -v --port COM21
```

### Run Specific Test Classes
```bash
# NeoPixel tests only
pytest tests/test_can_data_extraction.py::TestNeoPixelDataExtraction -v --port COM21

# Rule addition tests only
pytest tests/test_rule_management.py::TestRuleAddition -v --port COM21

# Protocol compliance tests only
pytest tests/test_protocol_v2_compliance.py::TestParamSourceRequired -v --port COM21
```

### Run Single Test
```bash
pytest tests/test_can_data_extraction.py::TestNeoPixelDataExtraction::test_neopixel_red -v --port COM21 -s
```

### Useful Options
```bash
# Show print statements
pytest tests/ -v -s --port COM21

# Stop on first failure
pytest tests/ -v -x --port COM21

# Increase timeout for slow boards
pytest tests/ -v --port COM21 --timeout 5.0

# Run tests matching pattern
pytest tests/ -v -k "neopixel" --port COM21

# Run tests NOT matching pattern
pytest tests/ -v -k "not edge" --port COM21
```

## Recommended Test Order

### 1. Verify Action Definitions
```bash
pytest tests/test_action_definitions.py -v --port COM21
```
**Purpose**: Verify firmware supports Protocol v2.0 and reports action definitions correctly.

### 2. Test Rule Management
```bash
pytest tests/test_rule_management.py -v --port COM21
```
**Purpose**: Verify add/delete/enable/disable operations work.

### 3. Test CAN Data Extraction
```bash
pytest tests/test_can_data_extraction.py -v --port COM21 -s
```
**Purpose**: Verify parameter extraction from CAN messages (requires visual verification).

### 4. Test Protocol Compliance
```bash
pytest tests/test_protocol_v2_compliance.py -v --port COM21
```
**Purpose**: Verify v2.0 breaking changes and PARAM_SOURCE requirement.

### 5. Test Edge Cases
```bash
pytest tests/test_edge_cases.py -v --port COM21
```
**Purpose**: Stress test with boundary conditions and malformed commands.

## Visual Verification Tests

These tests require you to **watch the hardware**:

### NeoPixel Tests (SAMD51 Feather M4 CAN)
```bash
pytest tests/test_can_data_extraction.py::TestNeoPixelDataExtraction -v --port COM21 -s
```
**Watch for**: LED color changes (red, green, blue, yellow, cyan, magenta, white, off)

### GPIO Tests
```bash
pytest tests/test_can_data_extraction.py::TestGPIODataExtraction -v --port COM21 -s
```
**Watch for**: Pin state changes (connect LED to test pin)

### PWM Tests
```bash
pytest tests/test_can_data_extraction.py::TestPWMDataExtraction -v --port COM21 -s
```
**Watch for**: LED brightness changes or use oscilloscope

## Common Issues

### Port Not Found
```
pytest.skip: No serial ports found
```
**Fix**: Specify port explicitly with `--port COM21`

### Permission Denied (Linux)
```
Permission denied: '/dev/ttyACM0'
```
**Fix**:
```bash
sudo usermod -a -G dialout $USER
# Then logout and login
```

### Tests Timeout
```
AssertionError: No response received
```
**Fix**:
- Check USB connection
- Verify firmware is running (LED blinking)
- Increase timeout: `--timeout 5.0`
- Check baud rate: `--baud 115200`

### Firmware Doesn't Respond
1. Power cycle device
2. Reflash firmware
3. Check serial monitor manually
4. Verify firmware has v2.0 support

### Tests Leave Rules Behind
```bash
# Clean up test rules manually
# Connect via serial monitor and send:
action:clear

# Or run cleanup tests
pytest tests/test_rule_management.py::TestRuleCleanup -v --port COM21
pytest tests/test_can_data_extraction.py::TestDataExtractionCleanup -v --port COM21
pytest tests/test_protocol_v2_compliance.py::TestProtocolCleanup -v --port COM21
pytest tests/test_edge_cases.py::TestEdgeCasesCleanup -v --port COM21
```

## CI/CD Quick Setup

### GitHub Actions
```yaml
name: Firmware Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: self-hosted  # Requires hardware connected
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install pytest pyserial
      - run: pytest tests/ -v --port /dev/ttyACM0 --timeout 5.0
```

## Test Development

### Add New Test
```python
# tests/test_my_feature.py
def test_my_feature(send_command, verify_status_ok, flush_serial):
    """Test description."""
    flush_serial()
    send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:13")
    assert verify_status_ok("Rule added", timeout=1.5)
    print("\n✓ Feature works!")
```

### Run During Development
```bash
# Run single test with output
pytest tests/test_my_feature.py::test_my_feature -v -s --port COM21

# Watch mode (requires pytest-watch)
ptw tests/ -- -v --port COM21
```

## Expected Test Duration

- **Action Definitions**: ~5-10 seconds
- **Rule Management**: ~30-60 seconds
- **CAN Data Extraction**: ~2-5 minutes (visual verification)
- **Protocol Compliance**: ~30-60 seconds
- **Edge Cases**: ~3-10 minutes (includes storage limit tests)

**Total Suite**: ~5-15 minutes depending on hardware

## Platform-Specific Notes

### Raspberry Pi Pico (RP2040)
- NeoPixel tests will SKIP (no onboard NeoPixel)
- GPIO tests work
- PWM tests work (limited pins)

### Adafruit Feather M4 CAN (SAMD51)
- All tests supported
- NeoPixel tests require visual verification
- Best platform for full test coverage

### ESP32
- Platform configuration ready
- Implementation depends on HAL completion
- Most tests should work

### STM32
- Platform configuration ready
- Implementation depends on HAL completion
- Built-in CAN peripheral support

## Getting Help

- **Full Documentation**: See `tests/README.md`
- **Protocol Spec**: See `can_tui/PROTOCOL.md`
- **Project README**: See main `README.md`
- **Issues**: https://github.com/yourusername/uCAN/issues

## Quick Reference Summary

```bash
# Most common usage
pytest tests/ -v --port COM21

# With output and stop on fail
pytest tests/ -v -s -x --port COM21

# Specific category
pytest tests/test_action_definitions.py -v --port COM21

# Single test
pytest tests/test_can_data_extraction.py::TestNeoPixelDataExtraction::test_neopixel_red -v --port COM21 -s

# Cleanup after interrupted tests
pytest tests/ -k "Cleanup" -v --port COM21
```

---

**Pro Tip**: Always run `test_action_definitions.py` first to verify your firmware supports Protocol v2.0 before running other tests!

# uCAN Firmware Test Suite

Comprehensive pytest test suite for validating uCAN firmware Protocol v2.0 compliance.

## Overview

This test suite provides complete validation of:
- **Action Definitions** (v2.0): Schema compliance, trigger types, parameter roles, UI builder readiness
- **Rule Management**: Adding, deleting, editing, enabling/disabling rules with fixed and candata parameters
- **CAN Data Extraction**: Dynamic parameter extraction from CAN message data bytes
- **Protocol v2.0 Compliance**: PARAM_SOURCE requirement, breaking changes, command format validation
- **Edge Cases**: Boundary conditions, malformed commands, storage limits, race conditions

## Requirements

```bash
pip install pytest pyserial
```

## Running Tests

### Basic Usage

```bash
# Run all tests with auto-detected serial port
pytest tests/ -v

# Run all tests on specific port
pytest tests/ -v --port COM21

# Run specific test file
pytest tests/test_action_definitions.py -v --port /dev/ttyACM0

# Run specific test class
pytest tests/test_rule_management.py::TestRuleAddition -v --port COM21

# Run specific test
pytest tests/test_can_data_extraction.py::TestNeoPixelDataExtraction::test_neopixel_red -v --port COM21
```

### Command-Line Options

- `--port PORT`: Serial port to use (e.g., COM21, /dev/ttyACM0)
- `--baud RATE`: Baud rate (default: 115200)
- `--timeout SECS`: Serial read timeout (default: 2.0)

### Examples

```bash
# Windows
pytest tests/ -v --port COM21

# Linux
pytest tests/ -v --port /dev/ttyACM0

# macOS
pytest tests/ -v --port /dev/cu.usbmodem14201

# Custom baud rate
pytest tests/ -v --port COM21 --baud 230400

# Run with increased timeout for slower boards
pytest tests/ -v --port COM21 --timeout 5.0

# Run only action definition tests
pytest tests/test_action_definitions.py -v --port COM21

# Run only rule management tests
pytest tests/test_rule_management.py -v --port COM21

# Run only CAN data extraction tests
pytest tests/test_can_data_extraction.py -v --port COM21
```

## Test Modules

### test_action_definitions.py

Validates that the firmware correctly reports action definitions in Protocol v2.0 format.

**Test Classes:**
- `TestActionDefinitionRetrieval`: Basic retrieval and JSON validation
- `TestActionDefinitionSchema`: Required fields, data types
- `TestTriggerTypes`: Trigger type validation ("can_msg", "periodic", "gpio", "manual")
- `TestParameterDefinitions`: Parameter schema validation
- `TestParameterRoles`: Parameter role validation ("action_param", "trigger_param", "output_param")
- `TestUIBuilderReadiness`: Validates UI builders have all needed information

**Key Tests:**
- `test_get_actiondefs_returns_data`: Verifies get:actiondefs command works
- `test_trigger_type_valid`: Validates all trigger types are in spec
- `test_parameter_role_valid`: Validates all parameter roles are in spec
- `test_neopixel_action_complete`: Checks NEOPIXEL has complete UI info

### test_rule_management.py

Tests the firmware's rule management commands.

**Test Classes:**
- `TestRuleAddition`: Adding rules with fixed and candata parameters
- `TestRuleAdditionErrors`: Error handling for invalid commands
- `TestRuleListing`: Listing rules with action:list
- `TestRuleDeletion`: Deleting rules (action:delete and action:remove)
- `TestRuleEnableDisable`: Enabling/disabling rules
- `TestRuleEditing`: Editing existing rules
- `TestRuleEdgeCases`: Duplicate IDs, wildcards, max values
- `TestRuleDisplayFormatting`: Wildcard display as "ANY"
- `TestParameterValidation`: Min/max parameter values

**Key Tests:**
- `test_add_rule_neopixel_candata`: Add rule with candata extraction
- `test_missing_param_source`: Verify v2.0 requires PARAM_SOURCE
- `test_wildcard_can_id`: Test CAN ID 0x000 with mask 0x000
- `test_delete_rule`: Verify rule deletion works

### test_can_data_extraction.py

Validates parameter extraction from CAN message data bytes.

**Test Classes:**
- `TestNeoPixelDataExtraction`: RGB color extraction and display
- `TestGPIODataExtraction`: Pin number extraction for GPIO actions
- `TestPWMDataExtraction`: Pin and duty cycle extraction
- `TestMultiByteParameterTypes`: uint16, uint32 extraction
- `TestBitPackedParameters`: Bit offset and length extraction
- `TestParameterRangeValidation`: Clamping and boundary conditions
- `TestDataLengthValidation`: Short/long/empty data handling
- `TestRapidUpdates`: Rapid message updates
- `TestConcurrentRules`: Multiple rules on same CAN ID

**Key Tests:**
- `test_neopixel_red`: Send red color via CAN, verify NeoPixel
- `test_pwm_50_percent`: Set 50% PWM via CAN data
- `test_neopixel_rapid_color_changes`: Rapid color updates
- `test_multiple_actions_same_message`: Multiple rules triggered by one message

### test_protocol_v2_compliance.py

Tests Protocol v2.0 compliance and breaking changes from v1.x.

**Test Classes:**
- `TestParamSourceRequired`: PARAM_SOURCE field is REQUIRED in v2.0 (breaking change)
- `TestParamSourceAliases`: Aliases for PARAM_SOURCE (fixed/rule, candata/can)
- `TestFixedVsCandata`: Both parameter source modes work correctly
- `TestCommandFormatValidation`: Command format and field validation
- `TestErrorMessages`: Proper error reporting with informative messages
- `TestBackwardCompatibility`: v1.x format NOT required to work (no backward compatibility)
- `TestProtocolVersionQuery`: Version query and capability reporting

**Key Tests:**
- `test_add_rule_without_param_source_fails`: Verify v2.0 requires PARAM_SOURCE
- `test_fixed_mode_uses_explicit_values`: Fixed mode ignores CAN data
- `test_candata_mode_extracts_from_message`: Candata mode extracts from CAN bytes
- `test_invalid_action_type_error`: Proper error messages returned

### test_edge_cases.py

Tests edge cases, boundary conditions, and error handling.

**Test Classes:**
- `TestParameterBoundaries`: Min/max parameter values (0, 255)
- `TestCANIDPatterns`: Wildcard, exact, range, overlapping patterns, extended IDs
- `TestDataPatternMatching`: Exact, partial, empty, multi-byte data patterns
- `TestDLCHandling`: DLC 0, specific, max (8), mismatches
- `TestRuleIDHandling`: Auto-assign (0), min (1), max (255), duplicates
- `TestMalformedCommands`: Empty, too long, invalid, special characters
- `TestRapidCommands`: Rapid add/delete/enable/disable/send sequences
- `TestStorageLimits`: Storage full error handling (up to 64 rules)
- `TestRuleOperationErrors`: Operations on nonexistent rules
- `TestZeroValues`: Zero CAN ID, mask, DLC handling
- `TestPlatformSpecificActions`: Platform availability checks

**Key Tests:**
- `test_neopixel_all_max_values`: All parameters at 255
- `test_wildcard_can_id`: CAN ID 0x000:0x000 matches ANY
- `test_extended_can_id`: 29-bit extended CAN IDs
- `test_rapid_rule_addition`: Add 10 rules in 200ms
- `test_add_many_rules`: Test storage limit (64 rules max)

## Test Fixtures

The `conftest.py` module provides pytest fixtures:

- `serial_port`: Auto-detected or command-line specified port
- `ser`: Serial connection (function scope, clean per test)
- `send_command(cmd)`: Send command to device
- `read_response()`: Read single response line
- `read_responses()`: Read multiple response lines
- `wait_for_response(prefix)`: Wait for specific response type
- `parse_json_response(resp)`: Parse JSON from protocol response
- `flush_serial()`: Clear serial buffers
- `get_action_definitions()`: High-level fixture to get all action defs
- `verify_status_ok(substring)`: Verify STATUS response

## Hardware Requirements

- uCAN-compatible device (Feather M4 CAN, RP2040 with MCP2551, etc.)
- USB connection to test machine
- Firmware compiled with Protocol v2.0 support

## Visual Verification

Some tests require **visual verification** (especially CAN data extraction tests):

- **NeoPixel tests**: Check onboard LED color matches expected
- **GPIO tests**: Use logic analyzer or LED to verify pin states
- **PWM tests**: Use oscilloscope or LED dimming to verify duty cycle

The test output will indicate what to verify visually.

## Troubleshooting

### Port Not Found
```
pytest.skip: No serial ports found. Use --port to specify manually.
```
**Solution**: Specify port explicitly with `--port COM21`

### Timeout Errors
```
AssertionError: No response received
```
**Solution**:
- Increase timeout with `--timeout 5.0`
- Check serial connection and baud rate
- Verify firmware is running

### Permission Denied (Linux)
```
serial.serialutil.SerialException: [Errno 13] Permission denied: '/dev/ttyACM0'
```
**Solution**: Add user to dialout group
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Tests Fail After Firmware Changes
- Rebuild and flash firmware: `wsl pio run -e feather_m4_can --target upload`
- Clear any lingering rules: Connect via serial monitor and manually delete test rules
- Power cycle the device

## Development

### Adding New Tests

1. Add test class to appropriate test file
2. Use existing fixtures from `conftest.py`
3. Follow naming convention: `test_<what_is_being_tested>`
4. Add docstrings explaining what's validated
5. Use assertions with helpful error messages

### Running Tests During Development

```bash
# Run tests in watch mode (requires pytest-watch)
ptw tests/ -- -v --port COM21

# Run specific test during development
pytest tests/test_rule_management.py::TestRuleAddition::test_add_rule_neopixel_candata -v --port COM21 -s
```

## CI/CD Integration

These tests can be integrated into CI/CD pipelines with hardware-in-the-loop:

```yaml
# Example GitHub Actions
- name: Run Firmware Tests
  run: pytest tests/ -v --port ${{ secrets.TEST_PORT }} --timeout 5.0
```

## Test Statistics

**Total Test Files**: 5
- `test_action_definitions.py` - 20+ tests
- `test_rule_management.py` - 30+ tests
- `test_can_data_extraction.py` - 40+ tests
- `test_protocol_v2_compliance.py` - 20+ tests
- `test_edge_cases.py` - 50+ tests

**Test Coverage**: ~160+ tests total

### Coverage Areas

✅ **Fully Tested**:
- Action definition schema validation (all required fields)
- Trigger types (can_msg, periodic, gpio, manual)
- Parameter roles (action_param, trigger_param, output_param)
- Rule addition (fixed and candata modes)
- Rule deletion and listing
- Rule enable/disable operations
- NeoPixel RGB extraction (10 colors + brightness)
- GPIO pin extraction (toggle, set, clear)
- PWM duty cycle extraction (0%, 25%, 50%, 75%, 100%)
- Protocol v2.0 PARAM_SOURCE requirement
- Command format validation
- Error message validation
- Wildcard CAN ID patterns
- Parameter boundary values (0, 255)
- DLC handling (0, specific, 8, mismatches)
- Rule ID handling (auto-assign, duplicates, min, max)
- Malformed command rejection
- Rapid command sequences
- Storage limit detection

⏳ **Partially Tested**:
- Rule editing (tests exist, firmware support varies)
- Multi-byte parameter types (uint16, uint32 - tests exist, awaiting actions that use them)
- Bit-packed parameters (tests exist, awaiting actions that use them)
- Extended 29-bit CAN IDs (tested, support platform-dependent)

🔄 **Platform-Dependent**:
- NeoPixel actions (SAMD51 Feather M4 CAN only)
- PWM actions (SAMD51, ESP32, some STM32)
- Specific GPIO pins (varies by board)

## Version History

- **v2.0.0**: Protocol v2.0 with trigger types and parameter roles
- **v1.0.0**: Initial protocol implementation

## License

Same license as uCAN project.

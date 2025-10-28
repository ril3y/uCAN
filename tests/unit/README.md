# uCAN Firmware Protocol Unit Tests

This directory contains **hardware-independent unit tests** for the uCAN firmware protocol implementation. These tests validate protocol parsing, command validation, and message formatting **without requiring physical hardware**.

## Overview

The unit tests are designed to:

- ✅ Run in CI/CD environments without hardware
- ✅ Validate protocol compliance with `docs/PROTOCOL.md`
- ✅ Test parsing of messages FROM the device (CAN_RX, STATUS, STATS, etc.)
- ✅ Test validation of commands TO the device (send, config, get, etc.)
- ✅ Test formatting of protocol messages
- ✅ Catch protocol bugs early in development

## Test Structure

```
tests/unit/
├── README.md                      # This file
├── __init__.py                    # Package initialization
├── protocol_helpers.py            # Protocol parsing/validation functions
├── test_protocol_parsing.py       # Tests for parsing device messages
├── test_command_validation.py     # Tests for validating host commands
└── test_message_formatting.py     # Tests for formatting protocol messages
```

## Running the Tests

### Run All Unit Tests

```bash
# Run all unit tests (no hardware required)
pytest tests/unit/ -v

# Or use the marker
pytest -m unit -v
```

### Run Specific Test Files

```bash
# Protocol parsing tests only
pytest tests/unit/test_protocol_parsing.py -v

# Command validation tests only
pytest tests/unit/test_command_validation.py -v

# Message formatting tests only
pytest tests/unit/test_message_formatting.py -v
```

### Run Specific Test Classes

```bash
# Test CAN_RX parsing only
pytest tests/unit/test_protocol_parsing.py::TestCANRXParsing -v

# Test send command validation only
pytest tests/unit/test_command_validation.py::TestSendCommandValidation -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest tests/unit/ --cov=tests.unit.protocol_helpers --cov-report=html

# Open coverage report
# Windows: start htmlcov\index.html
# Linux/Mac: open htmlcov/index.html
```

## Test Categories

### 1. Protocol Parsing Tests (`test_protocol_parsing.py`)

Tests for parsing messages **FROM the device TO the host**:

- **CAN_RX Messages**: `CAN_RX;0x123;01,02,03;1234567`
- **CAN_TX Messages**: `CAN_TX;0x100;FF,00;1234580`
- **CAN_ERR Messages**: `CAN_ERR;TX_FAILED;Arbitration lost;1234590`
- **STATUS Messages**: `STATUS;INFO;Configuration;CAN bitrate changed`
- **STATS Messages**: `STATS;1234;567;2;45;1234567`

**Test classes:**
- `TestCANRXParsing` - CAN receive message parsing
- `TestCANTXParsing` - CAN transmit message parsing
- `TestCANERRParsing` - CAN error message parsing
- `TestSTATUSParsing` - Status message parsing
- `TestSTATSParsing` - Statistics message parsing
- `TestEdgeCases` - Boundary conditions and edge cases

**Coverage:**
- ✅ Valid message formats
- ✅ Invalid message formats (should raise errors)
- ✅ Edge cases (empty data, max values, etc.)
- ✅ Whitespace tolerance
- ✅ Case sensitivity

### 2. Command Validation Tests (`test_command_validation.py`)

Tests for validating commands **FROM the host TO the device**:

- **Send Commands**: `send:0x123:01,02,03`
- **Config Commands**: `config:baudrate:500000`, `config:mode:loopback`
- **Get Commands**: `get:version`, `get:capabilities`

**Test classes:**
- `TestSendCommandValidation` - Send command validation
- `TestConfigCommandValidation` - Config command validation
- `TestGetCommandValidation` - Get command validation
- `TestCommandCaseSensitivity` - Case sensitivity tests
- `TestEdgeCasesAndBoundaries` - Boundary conditions
- `TestRealWorldCommandExamples` - Real usage examples

**Coverage:**
- ✅ Valid command formats
- ✅ Invalid command formats (should raise errors)
- ✅ Parameter validation (baudrate, mode, etc.)
- ✅ CAN ID range validation
- ✅ Data byte validation
- ✅ Case sensitivity

### 3. Message Formatting Tests (`test_message_formatting.py`)

Tests for formatting/constructing protocol messages:

- **Format CAN_RX/TX Messages**: Build protocol strings from data
- **Format STATUS Messages**: Build status messages
- **Format STATS Messages**: Build statistics messages
- **Round-trip Testing**: Format → Parse → Format consistency

**Test classes:**
- `TestCANRXFormatting` - CAN RX message formatting
- `TestCANTXFormatting` - CAN TX message formatting
- `TestSTATUSFormatting` - Status message formatting
- `TestSTATSFormatting` - Statistics message formatting
- `TestRoundTripFormatAndParse` - Round-trip consistency
- `TestEdgeCasesFormatting` - Edge cases
- `TestRealWorldFormatting` - Real-world examples

**Coverage:**
- ✅ Correct protocol string generation
- ✅ Hex formatting (uppercase/lowercase)
- ✅ Zero-padding for data bytes
- ✅ Round-trip consistency (format → parse → format)
- ✅ Invalid parameter handling

## Protocol Helper Functions

The `protocol_helpers.py` module provides reusable functions:

### Parsing Functions

```python
from tests.unit.protocol_helpers import (
    parse_can_rx, parse_can_tx, parse_can_err,
    parse_status, parse_stats
)

# Parse CAN_RX message
message = parse_can_rx("CAN_RX;0x123;01,02,03;1234567")
print(f"CAN ID: {message.can_id:#x}")
print(f"Data: {message.data}")
print(f"Timestamp: {message.timestamp}")
```

### Validation Functions

```python
from tests.unit.protocol_helpers import (
    validate_send_command,
    validate_config_command,
    validate_get_command
)

# Validate send command
can_id, data = validate_send_command("send:0x123:01,02,03")

# Validate config command
param, value = validate_config_command("config:baudrate:500000")

# Validate get command
param = validate_get_command("get:version")
```

### Formatting Functions

```python
from tests.unit.protocol_helpers import (
    format_can_rx_message,
    format_status_message,
    format_stats_message
)

# Format CAN_RX message
msg = format_can_rx_message(0x123, [0x01, 0x02, 0x03], 1234567)
# Returns: "CAN_RX;0x123;01,02,03;1234567"

# Format STATUS message
status = format_status_message("INFO", "Configuration", "CAN bitrate changed")
# Returns: "STATUS;INFO;Configuration;CAN bitrate changed"
```

## Test Coverage Summary

### Protocol Messages Covered

| Message Type | Parsing | Formatting | Validation |
|-------------|---------|------------|------------|
| CAN_RX      | ✅      | ✅         | ✅         |
| CAN_TX      | ✅      | ✅         | ✅         |
| CAN_ERR     | ✅      | ❌         | ✅         |
| STATUS      | ✅      | ✅         | ✅         |
| STATS       | ✅      | ✅         | ✅         |

### Commands Covered

| Command | Validation | Examples |
|---------|-----------|----------|
| send    | ✅        | ✅       |
| config  | ✅        | ✅       |
| get     | ✅        | ✅       |

### Test Statistics

- **Total test cases**: 150+
- **Parametrized tests**: 100+
- **Edge case tests**: 50+
- **Real-world examples**: 20+

## Adding New Tests

### Adding a Parsing Test

```python
@pytest.mark.unit
class TestNewMessageType:
    """Test NEW_MSG message parsing."""

    @pytest.mark.parametrize("message,expected_field", [
        ("NEW_MSG;value1;value2", "expected_value"),
        # Add more test cases
    ])
    def test_parse_valid_new_messages(self, message, expected_field):
        """Test parsing valid NEW_MSG messages."""
        result = parse_new_msg(message)
        assert result["field"] == expected_field
```

### Adding a Validation Test

```python
@pytest.mark.unit
class TestNewCommandValidation:
    """Test new: command validation."""

    def test_validate_valid_new_commands(self):
        """Test validation of valid new commands."""
        result = validate_new_command("new:param:value")
        assert result == expected_result
```

## CI/CD Integration

These tests are designed to run in GitHub Actions without hardware:

```yaml
# .github/workflows/test.yml
- name: Run unit tests
  run: pytest -m unit -v
```

The unit tests:
- ✅ Run on every commit
- ✅ Require no special setup
- ✅ Complete in seconds
- ✅ Catch protocol bugs early

## Differences from Integration Tests

| Aspect | Unit Tests (`tests/unit/`) | Integration Tests (`tests/`) |
|--------|---------------------------|------------------------------|
| Hardware | ❌ Not required | ✅ Required |
| Speed | ⚡ Fast (<5 seconds) | 🐌 Slower (varies) |
| Scope | Protocol parsing/validation | Full device communication |
| CI/CD | ✅ Always runs | ⚠️ Skipped without hardware |
| Marker | `@pytest.mark.unit` | `@pytest.mark.hardware` |

## Troubleshooting

### Import Errors

If you see import errors when running tests:

```bash
# Make sure you're running from the project root
cd /path/to/uCAN

# Install pytest if not already installed
pip install pytest

# Run tests with Python path
PYTHONPATH=. pytest tests/unit/ -v
```

### Protocol Helpers Not Found

The `protocol_helpers.py` module is in `tests/unit/`. Make sure to import correctly:

```python
# Correct import (from tests/unit/)
from protocol_helpers import parse_can_rx

# If running from project root, you may need:
from tests.unit.protocol_helpers import parse_can_rx
```

### Tests Failing After Protocol Changes

If you've modified the protocol specification (`docs/PROTOCOL.md`):

1. Update the helper functions in `protocol_helpers.py`
2. Update the test cases to match new protocol format
3. Add new test cases for new features
4. Run all tests to ensure nothing broke: `pytest tests/unit/ -v`

## Contributing

When adding new protocol features:

1. **Update protocol helpers** in `protocol_helpers.py`
2. **Add parsing tests** in `test_protocol_parsing.py`
3. **Add validation tests** in `test_command_validation.py`
4. **Add formatting tests** in `test_message_formatting.py`
5. **Run all tests**: `pytest tests/unit/ -v`
6. **Verify coverage**: `pytest tests/unit/ --cov=tests.unit.protocol_helpers`

## References

- **Protocol Specification**: `docs/PROTOCOL.md`
- **Integration Tests**: `tests/` (hardware-dependent)
- **Pytest Documentation**: https://docs.pytest.org/
- **GitHub Actions**: `.github/workflows/`

## License

These tests are part of the uCAN project. See the project LICENSE file for details.

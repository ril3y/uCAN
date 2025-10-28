"""
Unit tests for uCAN protocol command validation.

Tests validation of commands sent TO the device (send, config, get, etc.)
without requiring hardware.

Run with: pytest tests/unit/test_command_validation.py -v
Run unit tests only: pytest -m unit
"""

import pytest
from .protocol_helpers import (
    validate_send_command, validate_config_command, validate_get_command,
    CommandValidationError
)


@pytest.mark.unit
class TestSendCommandValidation:
    """Test send: command validation."""

    @pytest.mark.parametrize("command,expected_id,expected_data", [
        # Standard format
        ("send:0x123:01,02,03,04", 0x123, [0x01, 0x02, 0x03, 0x04]),
        # Different CAN IDs
        ("send:0x500:FF,00,00,C8", 0x500, [0xFF, 0x00, 0x00, 0xC8]),
        ("send:0x7FF:AA,BB,CC,DD,EE,FF", 0x7FF, [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF]),
        # Extended CAN ID
        ("send:0x1FFFFFFF:01,02", 0x1FFFFFFF, [0x01, 0x02]),
        ("send:0x800:12,34", 0x800, [0x12, 0x34]),
        # Empty data (valid)
        ("send:0x100:", 0x100, []),
        # Single byte
        ("send:0x200:FF", 0x200, [0xFF]),
        # Full 8 bytes
        ("send:0x300:00,11,22,33,44,55,66,77", 0x300,
         [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]),
        # Lowercase hex
        ("send:0x123:ab,cd,ef", 0x123, [0xAB, 0xCD, 0xEF]),
        # Mixed case
        ("send:0x456:Aa,Bb,Cc", 0x456, [0xAA, 0xBB, 0xCC]),
        # No 0x prefix (should parse as hex)
        ("send:123:01,02", 0x123, [0x01, 0x02]),
        # Whitespace tolerance
        ("send: 0x123 : 01,02,03 ", 0x123, [0x01, 0x02, 0x03]),
    ])
    def test_validate_valid_send_commands(self, command, expected_id, expected_data):
        """Test validation of valid send commands."""
        can_id, data = validate_send_command(command)

        assert can_id == expected_id
        assert data == expected_data

    @pytest.mark.parametrize("command,error_match", [
        # Missing prefix
        ("0x123:01,02", "must start with 'send:'"),
        ("config:0x123:01,02", "must start with 'send:'"),
        # Missing CAN ID
        ("send::01,02", "Missing CAN ID"),
        ("send:", "Missing CAN ID"),
        # Missing data separator
        ("send:0x123", "Missing CAN ID or data"),
        # Invalid CAN ID format
        ("send:INVALID:01,02", "Invalid CAN ID format"),
        ("send:0xGGG:01,02", "Invalid CAN ID format"),
        ("send:not_hex:01,02", "Invalid CAN ID format"),
        # CAN ID out of range
        ("send:0x20000000:01,02", "CAN ID out of range"),
        ("send:0xFFFFFFFF:01,02", "CAN ID out of range"),
        # Invalid data bytes
        ("send:0x123:01,GG", "Invalid hex data"),
        ("send:0x123:01,02,INVALID", "Invalid hex data"),
        ("send:0x123:ZZ", "Invalid hex data"),
        # Data byte out of range
        ("send:0x123:0x100", "Data byte out of range"),
        ("send:0x123:01,FF,100", "Data byte out of range"),
        # Too many data bytes
        ("send:0x123:01,02,03,04,05,06,07,08,09", "Too many data bytes"),
        ("send:0x123:00,11,22,33,44,55,66,77,88,99,AA", "Too many data bytes"),
    ])
    def test_validate_invalid_send_commands(self, command, error_match):
        """Test that invalid send commands raise appropriate errors."""
        with pytest.raises(CommandValidationError, match=error_match):
            validate_send_command(command)

    def test_send_command_max_data_length(self):
        """Test send command with exactly 8 bytes (maximum allowed)."""
        command = "send:0x123:00,11,22,33,44,55,66,77"
        can_id, data = validate_send_command(command)

        assert len(data) == 8
        assert data == [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]

    def test_send_command_max_standard_id(self):
        """Test send command with maximum standard CAN ID (0x7FF)."""
        command = "send:0x7FF:01,02"
        can_id, data = validate_send_command(command)

        assert can_id == 0x7FF

    def test_send_command_min_extended_id(self):
        """Test send command with minimum extended CAN ID (0x800)."""
        command = "send:0x800:01,02"
        can_id, data = validate_send_command(command)

        assert can_id == 0x800

    def test_send_command_max_extended_id(self):
        """Test send command with maximum extended CAN ID (0x1FFFFFFF)."""
        command = "send:0x1FFFFFFF:FF"
        can_id, data = validate_send_command(command)

        assert can_id == 0x1FFFFFFF


@pytest.mark.unit
class TestConfigCommandValidation:
    """Test config: command validation."""

    @pytest.mark.parametrize("command,expected_param,expected_value", [
        # Baudrate configurations
        ("config:baudrate:125000", "baudrate", "125000"),
        ("config:baudrate:250000", "baudrate", "250000"),
        ("config:baudrate:500000", "baudrate", "500000"),
        ("config:baudrate:1000000", "baudrate", "1000000"),
        # Filter configurations
        ("config:filter:0x123", "filter", "0x123"),
        ("config:filter:0x7FF", "filter", "0x7FF"),
        ("config:filter:0x1FFFFFFF", "filter", "0x1FFFFFFF"),
        # Mode configurations
        ("config:mode:normal", "mode", "normal"),
        ("config:mode:loopback", "mode", "loopback"),
        ("config:mode:listen", "mode", "listen"),
        # Timestamp configurations
        ("config:timestamp:on", "timestamp", "on"),
        ("config:timestamp:off", "timestamp", "off"),
        # Whitespace tolerance
        ("config: baudrate : 500000 ", "baudrate", "500000"),
    ])
    def test_validate_valid_config_commands(self, command, expected_param, expected_value):
        """Test validation of valid config commands."""
        param, value = validate_config_command(command)

        assert param == expected_param
        assert value == expected_value

    @pytest.mark.parametrize("command,error_match", [
        # Missing prefix
        ("baudrate:500000", "must start with 'config:'"),
        ("send:baudrate:500000", "must start with 'config:'"),
        # Missing parameter or value
        ("config:baudrate", "Missing parameter or value"),
        ("config:", "Missing parameter or value"),
        ("config:baudrate:", "Missing value"),
        ("config::500000", "Missing parameter"),
        # Invalid parameter name
        ("config:invalid:500000", "Invalid config parameter"),
        ("config:bitrate:500000", "Invalid config parameter"),
        ("config:speed:500000", "Invalid config parameter"),
        # Invalid baudrate values
        ("config:baudrate:100000", "Invalid baudrate"),
        ("config:baudrate:9600", "Invalid baudrate"),
        ("config:baudrate:2000000", "Invalid baudrate"),
        ("config:baudrate:INVALID", "Baudrate must be numeric"),
        ("config:baudrate:500k", "Baudrate must be numeric"),
        # Invalid mode values
        ("config:mode:invalid", "Invalid mode"),
        ("config:mode:silent", "Invalid mode"),
        ("config:mode:test", "Invalid mode"),
        # Invalid timestamp values
        ("config:timestamp:enabled", "Invalid timestamp value"),
        ("config:timestamp:1", "Invalid timestamp value"),
        ("config:timestamp:yes", "Invalid timestamp value"),
        # Invalid filter values
        ("config:filter:INVALID", "Filter must be hex value"),
        ("config:filter:0xGGG", "Filter must be hex value"),
        ("config:filter:0x20000000", "Filter value out of range"),
    ])
    def test_validate_invalid_config_commands(self, command, error_match):
        """Test that invalid config commands raise appropriate errors."""
        with pytest.raises(CommandValidationError, match=error_match):
            validate_config_command(command)

    def test_config_all_valid_baudrates(self):
        """Test all valid baudrate values."""
        valid_baudrates = [125000, 250000, 500000, 1000000]

        for baudrate in valid_baudrates:
            command = f"config:baudrate:{baudrate}"
            param, value = validate_config_command(command)
            assert param == "baudrate"
            assert value == str(baudrate)

    def test_config_all_valid_modes(self):
        """Test all valid mode values."""
        valid_modes = ["normal", "loopback", "listen"]

        for mode in valid_modes:
            command = f"config:mode:{mode}"
            param, value = validate_config_command(command)
            assert param == "mode"
            assert value == mode


@pytest.mark.unit
class TestGetCommandValidation:
    """Test get: command validation."""

    @pytest.mark.parametrize("command,expected_param", [
        ("get:version", "version"),
        ("get:status", "status"),
        ("get:stats", "stats"),
        ("get:capabilities", "capabilities"),
        ("get:pins", "pins"),
        ("get:actions", "actions"),
        ("get:actiondefs", "actiondefs"),
        # Whitespace tolerance
        ("get: version ", "version"),
        ("get:  capabilities  ", "capabilities"),
    ])
    def test_validate_valid_get_commands(self, command, expected_param):
        """Test validation of valid get commands."""
        param = validate_get_command(command)

        assert param == expected_param

    @pytest.mark.parametrize("command,error_match", [
        # Missing prefix
        ("version", "must start with 'get:'"),
        ("send:version", "must start with 'get:'"),
        # Missing parameter
        ("get:", "Missing parameter"),
        ("get", "must start with 'get:'"),
        # Invalid parameter
        ("get:invalid", "Invalid get parameter"),
        ("get:state", "Invalid get parameter"),
        ("get:info", "Invalid get parameter"),
        ("get:config", "Invalid get parameter"),
    ])
    def test_validate_invalid_get_commands(self, command, error_match):
        """Test that invalid get commands raise appropriate errors."""
        with pytest.raises(CommandValidationError, match=error_match):
            validate_get_command(command)

    def test_get_all_valid_parameters(self):
        """Test all valid get parameters."""
        valid_params = ["version", "status", "stats", "capabilities", "pins", "actions", "actiondefs"]

        for param in valid_params:
            command = f"get:{param}"
            result = validate_get_command(command)
            assert result == param


@pytest.mark.unit
class TestCommandCaseSensitivity:
    """Test that commands are case-sensitive."""

    def test_send_command_case_sensitive(self):
        """Test that SEND: (uppercase) is invalid."""
        with pytest.raises(CommandValidationError, match="must start with 'send:'"):
            validate_send_command("SEND:0x123:01,02")

    def test_config_command_case_sensitive(self):
        """Test that CONFIG: (uppercase) is invalid."""
        with pytest.raises(CommandValidationError, match="must start with 'config:'"):
            validate_config_command("CONFIG:baudrate:500000")

    def test_get_command_case_sensitive(self):
        """Test that GET: (uppercase) is invalid."""
        with pytest.raises(CommandValidationError, match="must start with 'get:'"):
            validate_get_command("GET:version")

    def test_config_parameter_case_sensitive(self):
        """Test that config parameters are case-sensitive."""
        with pytest.raises(CommandValidationError, match="Invalid config parameter"):
            validate_config_command("config:BAUDRATE:500000")

    def test_config_mode_value_case_sensitive(self):
        """Test that mode values are case-sensitive."""
        with pytest.raises(CommandValidationError, match="Invalid mode"):
            validate_config_command("config:mode:NORMAL")

    def test_get_parameter_case_sensitive(self):
        """Test that get parameters are case-sensitive."""
        with pytest.raises(CommandValidationError, match="Invalid get parameter"):
            validate_get_command("get:VERSION")


@pytest.mark.unit
class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions for command validation."""

    def test_send_zero_can_id(self):
        """Test send command with CAN ID 0x000."""
        can_id, data = validate_send_command("send:0x000:01")
        assert can_id == 0x000

    def test_send_max_standard_can_id(self):
        """Test send command with maximum standard CAN ID."""
        can_id, data = validate_send_command("send:0x7FF:01")
        assert can_id == 0x7FF

    def test_send_min_extended_can_id(self):
        """Test send command with minimum extended CAN ID."""
        can_id, data = validate_send_command("send:0x800:01")
        assert can_id == 0x800

    def test_send_max_extended_can_id(self):
        """Test send command with maximum extended CAN ID."""
        can_id, data = validate_send_command("send:0x1FFFFFFF:01")
        assert can_id == 0x1FFFFFFF

    def test_send_empty_data(self):
        """Test send command with empty data (valid for remote frames)."""
        can_id, data = validate_send_command("send:0x123:")
        assert can_id == 0x123
        assert data == []

    def test_send_single_byte(self):
        """Test send command with single data byte."""
        can_id, data = validate_send_command("send:0x123:FF")
        assert data == [0xFF]

    def test_send_max_data_bytes(self):
        """Test send command with exactly 8 bytes."""
        can_id, data = validate_send_command("send:0x123:00,11,22,33,44,55,66,77")
        assert len(data) == 8

    def test_config_filter_max_value(self):
        """Test config filter with maximum CAN ID."""
        param, value = validate_config_command("config:filter:0x1FFFFFFF")
        assert param == "filter"
        assert value == "0x1FFFFFFF"

    def test_config_filter_zero(self):
        """Test config filter with zero value."""
        param, value = validate_config_command("config:filter:0x000")
        assert param == "filter"
        assert value == "0x000"

    def test_whitespace_in_data_bytes(self):
        """Test that whitespace in data bytes is handled."""
        can_id, data = validate_send_command("send:0x123: 01 , 02 , 03 ")
        assert data == [0x01, 0x02, 0x03]

    def test_leading_zeros_in_can_id(self):
        """Test CAN ID with leading zeros."""
        can_id, data = validate_send_command("send:0x00123:01")
        assert can_id == 0x123

    def test_leading_zeros_in_data_bytes(self):
        """Test data bytes with leading zeros."""
        can_id, data = validate_send_command("send:0x123:001,002,003")
        assert data == [0x01, 0x02, 0x03]


@pytest.mark.unit
class TestRealWorldCommandExamples:
    """Test real-world command examples from actual usage."""

    def test_throttle_control_send(self):
        """Test real-world throttle control send command."""
        can_id, data = validate_send_command("send:0x500:FF,00,00,C8")
        assert can_id == 0x500
        assert data == [0xFF, 0x00, 0x00, 0xC8]

    def test_neopixel_color_send(self):
        """Test real-world NeoPixel color send command."""
        can_id, data = validate_send_command("send:0x400:FF,00,80")
        assert can_id == 0x400
        assert data == [0xFF, 0x00, 0x80]  # Red, Green, Blue

    def test_switch_panel_send(self):
        """Test real-world switch panel send command."""
        can_id, data = validate_send_command("send:0x300:0F")
        assert can_id == 0x300
        assert data == [0x0F]  # 4 switches on

    def test_standard_500k_baudrate_config(self):
        """Test standard 500kbps baudrate configuration."""
        param, value = validate_config_command("config:baudrate:500000")
        assert param == "baudrate"
        assert value == "500000"

    def test_loopback_test_mode(self):
        """Test loopback mode for testing."""
        param, value = validate_config_command("config:mode:loopback")
        assert param == "mode"
        assert value == "loopback"

    def test_standard_id_filter(self):
        """Test standard ID filter configuration."""
        param, value = validate_config_command("config:filter:0x7FF")
        assert param == "filter"
        assert value == "0x7FF"

    def test_capability_query(self):
        """Test capability discovery query."""
        param = validate_get_command("get:capabilities")
        assert param == "capabilities"

    def test_action_definitions_query(self):
        """Test action definitions query."""
        param = validate_get_command("get:actiondefs")
        assert param == "actiondefs"

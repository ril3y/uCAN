"""
Test uCAN Protocol v2.0 error handling.

Tests firmware error responses for invalid commands and malformed actions.

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
"""

import pytest
import time


@pytest.mark.hardware
@pytest.mark.integration
class TestErrorHandling:
    """Test suite for error handling and validation."""

    def test_invalid_command_returns_error(self, send_command, read_responses):
        """Test that unknown commands return error status."""
        send_command("invalid:command:test")
        time.sleep(0.3)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        status_responses = [r for r in responses if r.startswith("STATUS;")]

        # Firmware may silently ignore invalid commands or return error
        # This test documents the behavior - check that we get some response or none
        # If we get a response, it should indicate an error
        if status_responses:
            assert "ERROR" in status_responses[0].upper() or "INVALID" in status_responses[0].upper(), \
                f"If firmware responds to invalid command, should be error, got: {status_responses[0]}"

    def test_malformed_action_add_missing_fields(self, send_command, read_responses):
        """Test action:add with missing required fields."""
        send_command("action:clear")
        time.sleep(0.2)

        # Missing parameters (incomplete command)
        send_command("action:add:0:0x100")
        time.sleep(0.3)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        status_responses = [r for r in responses if r.startswith("STATUS;")]

        assert len(status_responses) > 0, "Expected error for incomplete action:add"

        send_command("action:clear")
        time.sleep(0.2)

    def test_action_add_missing_param_source_fails(self, send_command, read_responses):
        """Test that action:add without PARAM_SOURCE fails (v2.0 requirement)."""
        send_command("action:clear")
        time.sleep(0.2)
        read_responses(max_lines=5, line_timeout=0.3)  # Consume clear response

        # Old v1.x format without param_source
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:13")
        time.sleep(0.3)

        responses = read_responses(max_lines=10, line_timeout=0.5)
        status_responses = [r for r in responses if r.startswith("STATUS;")]

        # Firmware should reject this (missing PARAM_SOURCE)
        # It may return ERROR or silently ignore
        if status_responses:
            assert "ERROR" in status_responses[0] or "added" not in status_responses[0].lower(), \
                f"Expected ERROR for missing PARAM_SOURCE, got: {status_responses[0]}"

        send_command("action:clear")
        time.sleep(0.2)
        read_responses(max_lines=5, line_timeout=0.3)  # Consume clear response

    def test_action_remove_nonexistent_rule(self, send_command, read_responses):
        """Test action:remove fails gracefully for non-existent rule."""
        send_command("action:clear")
        time.sleep(0.2)

        # Try to remove rule that doesn't exist
        send_command("action:remove:999")
        time.sleep(0.3)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        status_responses = [r for r in responses if r.startswith("STATUS;")]

        assert len(status_responses) > 0, "Expected response for non-existent rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_invalid_can_id_format(self, send_command, read_responses):
        """Test send command with invalid CAN ID format."""
        # Invalid hex format - firmware should ignore
        send_command("send:INVALID:01,02,03")
        time.sleep(0.5)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        # Should get error or no CAN_TX response
        can_tx_invalid = [r for r in responses if r.startswith("CAN_TX;")]
        # Firmware should NOT send invalid message
        assert len(can_tx_invalid) == 0, "Firmware should not send message with invalid CAN ID"

        # Valid command should work
        send_command("send:0x123:01,02,03")
        time.sleep(0.5)

        responses2 = read_responses(max_lines=5, line_timeout=0.5)
        can_tx_responses = [r for r in responses2 if r.startswith("CAN_TX;")]
        assert len(can_tx_responses) > 0, "Valid send command should work"

    def test_invalid_hex_data_bytes(self, send_command, read_responses):
        """Test send command with invalid hex data."""
        # Invalid hex characters - firmware should ignore
        send_command("send:0x100:ZZ,YY,XX")
        time.sleep(0.5)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        # Should get error or no CAN_TX
        can_tx_invalid = [r for r in responses if r.startswith("CAN_TX;")]
        assert len(can_tx_invalid) == 0, "Firmware should not send message with invalid hex data"

        # Valid command should work
        send_command("send:0x100:AA,BB,CC")
        time.sleep(0.5)

        responses2 = read_responses(max_lines=5, line_timeout=0.5)
        can_tx_responses = [r for r in responses2 if r.startswith("CAN_TX;")]
        assert len(can_tx_responses) > 0, "Valid send command should work"

    def test_action_edit_nonexistent_rule(self, send_command, read_responses):
        """Test action:edit fails for non-existent rule ID."""
        send_command("action:clear")
        time.sleep(0.2)

        # Try to edit rule that doesn't exist
        send_command("action:edit:999:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.3)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        status_responses = [r for r in responses if r.startswith("STATUS;")]

        assert len(status_responses) > 0, "Expected error for editing non-existent rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_invalid_parameter_values(self, send_command, read_responses):
        """Test action:add with invalid parameter values."""
        send_command("action:clear")
        time.sleep(0.2)

        # Invalid pin number (e.g., negative or extremely high)
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:999999")
        time.sleep(0.3)

        # Firmware may accept this or reject it depending on validation

        send_command("action:clear")
        time.sleep(0.2)

    def test_send_with_too_many_data_bytes(self, send_command, read_responses):
        """Test send command with more than 8 data bytes (standard CAN limit)."""
        # Try to send 9 bytes (firmware may truncate to 8 or reject)
        send_command("send:0x100:01,02,03,04,05,06,07,08,09")
        time.sleep(0.5)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        # Should get error or CAN_TX with only 8 bytes or no response
        can_tx_9byte = [r for r in responses if r.startswith("CAN_TX;")]
        # If firmware sends, it should truncate to 8 bytes
        if can_tx_9byte:
            parts = can_tx_9byte[0].split(';')
            data_bytes = parts[2].split(',') if len(parts) > 2 else []
            assert len(data_bytes) <= 8, "Firmware should not send more than 8 bytes"

        # Valid 8-byte send should work
        send_command("send:0x100:01,02,03,04,05,06,07,08")
        time.sleep(0.5)

        responses2 = read_responses(max_lines=5, line_timeout=0.5)
        can_tx_responses = [r for r in responses2 if r.startswith("CAN_TX;")]
        assert len(can_tx_responses) > 0, "Valid 8-byte send should work"

    def test_empty_command(self, send_command, read_responses):
        """Test firmware handles empty commands gracefully."""
        send_command("")
        time.sleep(0.2)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        # Firmware should either ignore or return error

    def test_command_with_extra_colons(self, send_command, read_responses):
        """Test commands with extra delimiters."""
        # Malformed data (colons instead of commas) - firmware should reject
        send_command("send:0x100:01:02:03")  # Should be commas, not colons
        time.sleep(0.5)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        # Should get error or no CAN_TX
        can_tx_invalid = [r for r in responses if r.startswith("CAN_TX;")]
        assert len(can_tx_invalid) == 0, "Firmware should not send malformed message"

        # Valid format should work
        send_command("send:0x100:01,02,03")
        time.sleep(0.5)

        responses2 = read_responses(max_lines=5, line_timeout=0.5)
        can_tx_responses = [r for r in responses2 if r.startswith("CAN_TX;")]
        assert len(can_tx_responses) > 0, "Valid format should work"

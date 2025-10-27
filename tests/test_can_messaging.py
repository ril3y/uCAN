"""
Test uCAN Protocol v2.0 CAN messaging commands.

This module tests CAN message transmission and format validation:
- send command with various data formats
- CAN_TX message format validation
- Extended CAN ID support
- Empty data messages
- Timestamp validation

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
- CAN bus connection (or loopback mode if supported)
"""

import pytest
import time


@pytest.mark.hardware
@pytest.mark.integration
class TestCANMessaging:
    """Test suite for CAN message transmission."""

    def test_send_basic_message(self, send_command, wait_for_response):
        """Test send command transmits CAN message successfully."""
        # Send a basic CAN message
        send_command("send:0x123:01,02,03,04")

        # Should get CAN_TX confirmation
        response = wait_for_response("CAN_TX;", timeout=1.0)

        assert response is not None, "No CAN_TX response received for send command"
        assert response.startswith("CAN_TX;"), f"Expected CAN_TX; prefix, got: {response}"

        # Parse CAN_TX format: CAN_TX;{CAN_ID};{DATA};{TIMESTAMP}
        parts = response.split(';')
        assert len(parts) == 4, f"CAN_TX should have 4 parts, got {len(parts)}: {response}"

        can_id = parts[1]
        data = parts[2]
        timestamp = parts[3]

        # Verify CAN ID matches what we sent
        assert can_id.upper() == "0x123".upper(), f"Expected CAN ID 0x123, got: {can_id}"

        # Verify data matches what we sent
        assert data.upper() == "01,02,03,04".upper(), f"Expected data 01,02,03,04, got: {data}"

        # Verify timestamp is numeric
        assert timestamp.isdigit(), f"Timestamp should be numeric, got: {timestamp}"

    def test_send_with_8_bytes(self, send_command, wait_for_response):
        """Test send command with maximum standard CAN data (8 bytes)."""
        # Send 8-byte message
        send_command("send:0x200:11,22,33,44,55,66,77,88")

        response = wait_for_response("CAN_TX;", timeout=1.0)

        assert response is not None, "No CAN_TX response received"

        parts = response.split(';')
        can_id = parts[1]
        data = parts[2]

        assert can_id.upper() == "0x200".upper(), f"Expected CAN ID 0x200, got: {can_id}"

        # Count data bytes
        data_bytes = data.split(',')
        assert len(data_bytes) == 8, f"Expected 8 data bytes, got {len(data_bytes)}: {data}"

        # Verify data matches
        expected_data = "11,22,33,44,55,66,77,88"
        assert data.upper() == expected_data.upper(), f"Expected {expected_data}, got: {data}"

    def test_send_with_empty_data(self, send_command, wait_for_response):
        """Test send command with no data bytes (0-length CAN message)."""
        # Send message with no data
        send_command("send:0x300:")

        response = wait_for_response("CAN_TX;", timeout=1.0)

        assert response is not None, "No CAN_TX response received for empty data"

        parts = response.split(';')
        can_id = parts[1]
        data = parts[2]

        assert can_id.upper() == "0x300".upper(), f"Expected CAN ID 0x300, got: {can_id}"

        # Data field should be empty
        assert data == "", f"Expected empty data field, got: {data}"

    def test_send_with_single_byte(self, send_command, wait_for_response):
        """Test send command with single data byte."""
        send_command("send:0x400:AA")

        response = wait_for_response("CAN_TX;", timeout=1.0)

        assert response is not None, "No CAN_TX response received"

        parts = response.split(';')
        can_id = parts[1]
        data = parts[2]

        assert can_id.upper() == "0x400".upper(), f"Expected CAN ID 0x400, got: {can_id}"
        assert data.upper() == "AA", f"Expected data AA, got: {data}"

    def test_extended_can_id_format(self, send_command, wait_for_response):
        """Test send command with extended CAN ID (29-bit)."""
        # Extended CAN ID is detected by value > 0x7FF
        extended_id = "0x12345678"

        send_command(f"send:{extended_id}:01,02")

        response = wait_for_response("CAN_TX;", timeout=1.0)

        # Note: Some hardware may not support extended IDs, so we check for either success or error
        if response is None:
            # Check for error message
            pytest.skip("No response - hardware may not support extended CAN IDs")

        if response.startswith("STATUS;ERROR"):
            # Extended IDs not supported on this hardware
            pytest.skip(f"Hardware does not support extended CAN IDs: {response}")

        # If we got CAN_TX, verify the ID
        assert response.startswith("CAN_TX;"), f"Expected CAN_TX or error, got: {response}"

        parts = response.split(';')
        returned_id = parts[1]

        # Verify the extended ID is preserved (case-insensitive hex comparison)
        assert returned_id.upper() == extended_id.upper(), \
            f"Expected extended ID {extended_id}, got: {returned_id}"

    def test_can_tx_message_format(self, send_command, wait_for_response):
        """Test that CAN_TX message format matches protocol specification exactly."""
        send_command("send:0x500:FF,00,AA,55")

        response = wait_for_response("CAN_TX;", timeout=1.0)

        assert response is not None, "No CAN_TX response received"

        # Protocol spec: CAN_TX;{CAN_ID};{DATA};{TIMESTAMP}
        parts = response.split(';')

        # Must have exactly 4 semicolon-separated parts
        assert len(parts) == 4, f"CAN_TX should have 4 parts, got {len(parts)}: {response}"

        # Part 0: "CAN_TX"
        assert parts[0] == "CAN_TX", f"First part should be CAN_TX, got: {parts[0]}"

        # Part 1: CAN_ID (hex with 0x prefix)
        assert parts[1].startswith('0x') or parts[1].startswith('0X'), \
            f"CAN ID should have 0x prefix, got: {parts[1]}"
        int(parts[1], 16)  # Should be valid hex

        # Part 2: DATA (comma-separated hex bytes or empty)
        if parts[2]:  # If not empty
            data_bytes = parts[2].split(',')
            for byte in data_bytes:
                int(byte, 16)  # Each should be valid hex

        # Part 3: TIMESTAMP (numeric milliseconds since boot)
        assert parts[3].isdigit(), f"Timestamp should be numeric, got: {parts[3]}"
        timestamp_ms = int(parts[3])
        assert timestamp_ms >= 0, f"Timestamp should be non-negative, got: {timestamp_ms}"

    def test_can_tx_includes_timestamp(self, send_command, wait_for_response):
        """Test that CAN_TX messages include monotonically increasing timestamps."""
        # Send first message
        send_command("send:0x600:01")
        response1 = wait_for_response("CAN_TX;", timeout=1.0)

        assert response1 is not None, "No CAN_TX response for first message"
        timestamp1 = int(response1.split(';')[3])

        # Wait a bit
        time.sleep(0.1)

        # Send second message
        send_command("send:0x600:02")
        response2 = wait_for_response("CAN_TX;", timeout=1.0)

        assert response2 is not None, "No CAN_TX response for second message"
        timestamp2 = int(response2.split(';')[3])

        # Second timestamp should be greater than first
        assert timestamp2 > timestamp1, \
            f"Timestamps should be monotonically increasing: {timestamp1} -> {timestamp2}"

    def test_send_with_hex_data_various_cases(self, send_command, wait_for_response):
        """Test send command accepts hex data in various formats."""
        # Lowercase hex
        send_command("send:0x700:aa,bb,cc")
        response = wait_for_response("CAN_TX;", timeout=1.0)
        assert response is not None, "Should accept lowercase hex data"

        # Uppercase hex
        send_command("send:0x700:DD,EE,FF")
        response = wait_for_response("CAN_TX;", timeout=1.0)
        assert response is not None, "Should accept uppercase hex data"

        # Mixed case hex
        send_command("send:0x700:aA,Bb,Cc")
        response = wait_for_response("CAN_TX;", timeout=1.0)
        assert response is not None, "Should accept mixed case hex data"

    def test_send_with_various_can_ids(self, send_command, wait_for_response):
        """Test send command with various valid CAN IDs."""
        # Minimum standard CAN ID
        send_command("send:0x000:01")
        response = wait_for_response("CAN_TX;", timeout=1.0)
        assert response is not None, "Should accept CAN ID 0x000"

        # Maximum standard CAN ID
        send_command("send:0x7FF:01")
        response = wait_for_response("CAN_TX;", timeout=1.0)
        assert response is not None, "Should accept CAN ID 0x7FF"

        # Common IDs
        for can_id in ["0x100", "0x200", "0x500", "0x600"]:
            send_command(f"send:{can_id}:01")
            response = wait_for_response("CAN_TX;", timeout=1.0)
            assert response is not None, f"Should accept CAN ID {can_id}"

    def test_send_returns_error_for_invalid_format(self, send_command, read_responses):
        """Test send command returns error for malformed messages."""
        # Missing CAN ID
        send_command("send::01,02,03")
        time.sleep(0.3)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        status_responses = [r for r in responses if r.startswith("STATUS;")]

        # Should get an error response
        assert len(status_responses) > 0, "Expected error response for missing CAN ID"
        assert "ERROR" in status_responses[0], \
            f"Expected ERROR status, got: {status_responses[0]}"

    def test_send_data_byte_order_preserved(self, send_command, wait_for_response):
        """Test that data byte order is preserved in transmission."""
        # Send message with specific byte pattern
        send_command("send:0x111:12,34,56,78,9A,BC,DE,F0")

        response = wait_for_response("CAN_TX;", timeout=1.0)

        assert response is not None, "No CAN_TX response received"

        parts = response.split(';')
        data = parts[2]

        # Verify exact byte order (case-insensitive)
        expected = "12,34,56,78,9A,BC,DE,F0"
        assert data.upper() == expected.upper(), \
            f"Expected data {expected}, got: {data}"

    def test_multiple_sends_in_sequence(self, send_command, read_responses):
        """Test sending multiple CAN messages in rapid sequence."""
        # Send multiple messages quickly
        for i in range(5):
            send_command(f"send:0x{100 + i:03X}:{i:02X}")
            time.sleep(0.05)  # Small delay between sends

        time.sleep(0.3)  # Wait for all responses

        responses = read_responses(max_lines=10, line_timeout=0.5)
        can_tx_responses = [r for r in responses if r.startswith("CAN_TX;")]

        # Should get at least some CAN_TX responses
        assert len(can_tx_responses) >= 3, \
            f"Expected at least 3 CAN_TX responses, got {len(can_tx_responses)}"

    def test_can_id_format_consistency(self, send_command, wait_for_response):
        """Test that CAN IDs are returned in consistent format."""
        # Send with lowercase x
        send_command("send:0x123:01")
        response1 = wait_for_response("CAN_TX;", timeout=1.0)

        # Send with uppercase X
        send_command("send:0X456:01")
        response2 = wait_for_response("CAN_TX;", timeout=1.0)

        assert response1 is not None and response2 is not None, \
            "Should receive responses for both formats"

        # Both should return IDs with consistent format (0x prefix)
        id1 = response1.split(';')[1]
        id2 = response2.split(';')[1]

        # Both should have 0x or 0X prefix
        assert id1.startswith('0x') or id1.startswith('0X'), \
            f"ID should have 0x prefix, got: {id1}"
        assert id2.startswith('0x') or id2.startswith('0X'), \
            f"ID should have 0x prefix, got: {id2}"

    def test_send_zero_padded_hex_bytes(self, send_command, wait_for_response):
        """Test send command with zero-padded hex bytes."""
        # Send with leading zeros
        send_command("send:0x200:00,01,02,03,04,05,06,07")

        response = wait_for_response("CAN_TX;", timeout=1.0)

        assert response is not None, "No CAN_TX response received"

        parts = response.split(';')
        data = parts[2]

        # Verify zeros are preserved
        data_bytes = data.split(',')
        assert data_bytes[0].upper() == "00", f"First byte should be 00, got: {data_bytes[0]}"

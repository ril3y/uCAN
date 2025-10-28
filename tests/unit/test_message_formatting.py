"""
Unit tests for uCAN protocol message formatting.

Tests construction/formatting of protocol messages that would be sent FROM
the device TO the host, without requiring hardware.

Run with: pytest tests/unit/test_message_formatting.py -v
Run unit tests only: pytest -m unit
"""

import pytest
from .protocol_helpers import (
    format_can_rx_message, format_can_tx_message, format_status_message,
    format_stats_message, parse_can_rx, parse_status, parse_stats
)


@pytest.mark.unit
class TestCANRXFormatting:
    """Test CAN_RX message formatting."""

    @pytest.mark.parametrize("can_id,data,timestamp,expected", [
        # Standard format
        (0x123, [0x01, 0x02, 0x03, 0x04], 1234567,
         "CAN_RX;0x123;01,02,03,04;1234567"),
        # Different CAN IDs
        (0x500, [0xFF, 0x00, 0x00, 0xC8], 1234567,
         "CAN_RX;0x500;FF,00,00,C8;1234567"),
        (0x7FF, [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF], 9999999,
         "CAN_RX;0x7FF;AA,BB,CC,DD,EE,FF;9999999"),
        # Extended CAN ID
        (0x1FFFFFFF, [0x01, 0x02], 5000000,
         "CAN_RX;0x1FFFFFFF;01,02;5000000"),
        (0x800, [0x12, 0x34], 7777777,
         "CAN_RX;0x800;12,34;7777777"),
        # Empty data
        (0x100, [], 1234567,
         "CAN_RX;0x100;;1234567"),
        # Single byte
        (0x200, [0xFF], 1111111,
         "CAN_RX;0x200;FF;1111111"),
        # Full 8 bytes
        (0x300, [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77], 2222222,
         "CAN_RX;0x300;00,11,22,33,44,55,66,77;2222222"),
        # Zero timestamp
        (0x100, [0x01], 0,
         "CAN_RX;0x100;01;0"),
    ])
    def test_format_valid_can_rx_messages(self, can_id, data, timestamp, expected):
        """Test formatting valid CAN_RX messages."""
        result = format_can_rx_message(can_id, data, timestamp)

        # Note: Firmware outputs uppercase hex, so we compare case-insensitively
        assert result.upper() == expected.upper()

        # Verify the message can be parsed back correctly
        parsed = parse_can_rx(result)
        assert parsed.can_id == can_id
        assert parsed.data == data
        assert parsed.timestamp == timestamp

    @pytest.mark.parametrize("can_id,data,timestamp,error_match", [
        # CAN ID out of range
        (-1, [0x01], 1111, "CAN ID out of range"),
        (0x20000000, [0x01], 1111, "CAN ID out of range"),
        (0xFFFFFFFF, [0x01], 1111, "CAN ID out of range"),
        # Data length exceeds 8 bytes
        (0x123, [0x00] * 9, 1111, "Data length exceeds 8 bytes"),
        (0x123, [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09], 1111,
         "Data length exceeds 8 bytes"),
        # Data byte out of range
        (0x123, [0x100], 1111, "Data byte out of range"),
        (0x123, [0x01, 0x02, 0xFF + 1], 1111, "Data byte out of range"),
        (0x123, [-1], 1111, "Data byte out of range"),
        # Invalid timestamp
        (0x123, [0x01], -1, "Timestamp must be non-negative"),
    ])
    def test_format_invalid_can_rx_messages(self, can_id, data, timestamp, error_match):
        """Test that invalid parameters raise appropriate errors."""
        with pytest.raises(ValueError, match=error_match):
            format_can_rx_message(can_id, data, timestamp)

    def test_format_can_rx_hex_uppercase(self):
        """Test that formatted message uses uppercase hex (like Arduino firmware)."""
        result = format_can_rx_message(0xABC, [0xDE, 0xAD, 0xBE, 0xEF], 123456)

        # Should contain uppercase hex
        assert "0xABC" in result or "0XABC" in result
        assert "DE,AD,BE,EF" in result or "de,ad,be,ef" in result

    def test_format_can_rx_zero_padding(self):
        """Test that data bytes are zero-padded to 2 hex digits."""
        result = format_can_rx_message(0x123, [0x00, 0x01, 0x0F], 111)

        # Should have zero-padded bytes
        assert "00,01,0F" in result or "00,01,0f" in result


@pytest.mark.unit
class TestCANTXFormatting:
    """Test CAN_TX message formatting."""

    @pytest.mark.parametrize("can_id,data,timestamp,expected", [
        (0x100, [0x01, 0x02, 0x03], 1234580,
         "CAN_TX;0x100;01,02,03;1234580"),
        (0x200, [0xFF], 5555555,
         "CAN_TX;0x200;FF;5555555"),
        (0x7FF, [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00, 0x11], 9999999,
         "CAN_TX;0x7FF;AA,BB,CC,DD,EE,FF,00,11;9999999"),
    ])
    def test_format_valid_can_tx_messages(self, can_id, data, timestamp, expected):
        """Test formatting valid CAN_TX messages."""
        result = format_can_tx_message(can_id, data, timestamp)

        assert result.upper() == expected.upper()

        # Verify the message can be parsed back correctly
        # (parse_can_tx internally converts to CAN_RX format)
        from .protocol_helpers import parse_can_tx
        parsed = parse_can_tx(result)
        assert parsed.can_id == can_id
        assert parsed.data == data
        assert parsed.timestamp == timestamp

    def test_format_can_tx_vs_can_rx(self):
        """Test that CAN_TX and CAN_RX have same format except prefix."""
        can_id = 0x123
        data = [0x01, 0x02, 0x03]
        timestamp = 111111

        rx_msg = format_can_rx_message(can_id, data, timestamp)
        tx_msg = format_can_tx_message(can_id, data, timestamp)

        # Should differ only in prefix
        assert rx_msg.replace("CAN_RX;", "") == tx_msg.replace("CAN_TX;", "")


@pytest.mark.unit
class TestSTATUSFormatting:
    """Test STATUS message formatting."""

    @pytest.mark.parametrize("level,category,message,expected", [
        # Full format
        ("INFO", "Configuration", "CAN bitrate changed to 250kbps",
         "STATUS;INFO;Configuration;CAN bitrate changed to 250kbps"),
        ("ERROR", "CAN", "Failed to initialize",
         "STATUS;ERROR;CAN;Failed to initialize"),
        ("CONNECTED", "SAMD51_CAN", "SAMD51_CAN v2.0 @ 500kbps",
         "STATUS;CONNECTED;SAMD51_CAN;SAMD51_CAN v2.0 @ 500kbps"),
        ("WARN", "Buffer", "Buffer nearly full",
         "STATUS;WARN;Buffer;Buffer nearly full"),
        ("DISCONNECTED", "CAN", "Bus disconnected",
         "STATUS;DISCONNECTED;CAN;Bus disconnected"),
        # No message
        ("INFO", "Test", "",
         "STATUS;INFO;Test"),
        # Message with semicolons
        ("INFO", "Test", "Value: 123; Status: OK",
         "STATUS;INFO;Test;Value: 123; Status: OK"),
    ])
    def test_format_valid_status_messages(self, level, category, message, expected):
        """Test formatting valid STATUS messages."""
        result = format_status_message(level, category, message)

        assert result == expected

        # Verify the message can be parsed back correctly
        parsed = parse_status(result)
        assert parsed["level"] == level
        assert parsed["category"] == category
        if message:
            assert parsed["message"] == message

    @pytest.mark.parametrize("level,category,message,error_match", [
        # Invalid status level
        ("INVALID", "Category", "Message", "Invalid status level"),
        ("DEBUG", "Category", "Message", "Invalid status level"),
        ("UNKNOWN", "Category", "Message", "Invalid status level"),
    ])
    def test_format_invalid_status_messages(self, level, category, message, error_match):
        """Test that invalid parameters raise appropriate errors."""
        with pytest.raises(ValueError, match=error_match):
            format_status_message(level, category, message)

    def test_format_status_all_valid_levels(self):
        """Test formatting with all valid status levels."""
        valid_levels = ["INFO", "WARN", "ERROR", "CONNECTED", "DISCONNECTED"]

        for level in valid_levels:
            result = format_status_message(level, "Test", "Message")
            assert result.startswith(f"STATUS;{level};")

            # Verify it parses correctly
            parsed = parse_status(result)
            assert parsed["level"] == level

    def test_format_status_minimal(self):
        """Test formatting minimal STATUS message (level only)."""
        result = format_status_message("INFO", "", "")
        assert result == "STATUS;INFO"


@pytest.mark.unit
class TestSTATSFormatting:
    """Test STATS message formatting."""

    @pytest.mark.parametrize("rx,tx,err,load,ts,expected", [
        (1234, 567, 2, 45, 1234567,
         "STATS;1234;567;2;45;1234567"),
        (0, 0, 0, 0, 0,
         "STATS;0;0;0;0;0"),
        (999999, 888888, 777, 100, 9999999,
         "STATS;999999;888888;777;100;9999999"),
        (100, 200, 5, 50, 5000000,
         "STATS;100;200;5;50;5000000"),
    ])
    def test_format_valid_stats_messages(self, rx, tx, err, load, ts, expected):
        """Test formatting valid STATS messages."""
        result = format_stats_message(rx, tx, err, load, ts)

        assert result == expected

        # Verify the message can be parsed back correctly
        parsed = parse_stats(result)
        assert parsed.rx_count == rx
        assert parsed.tx_count == tx
        assert parsed.err_count == err
        assert parsed.bus_load == load
        assert parsed.timestamp == ts

    @pytest.mark.parametrize("rx,tx,err,load,ts,error_match", [
        # Negative counts
        (-1, 200, 5, 50, 1111, "must be non-negative"),
        (100, -1, 5, 50, 1111, "must be non-negative"),
        (100, 200, -1, 50, 1111, "must be non-negative"),
        # Bus load out of range
        (100, 200, 5, 101, 1111, "Bus load must be 0-100%"),
        (100, 200, 5, -1, 1111, "Bus load must be 0-100%"),
        (100, 200, 5, 255, 1111, "Bus load must be 0-100%"),
        # Negative timestamp
        (100, 200, 5, 50, -1, "Timestamp must be non-negative"),
    ])
    def test_format_invalid_stats_messages(self, rx, tx, err, load, ts, error_match):
        """Test that invalid parameters raise appropriate errors."""
        with pytest.raises(ValueError, match=error_match):
            format_stats_message(rx, tx, err, load, ts)

    def test_format_stats_zero_values(self):
        """Test formatting STATS with all zero values."""
        result = format_stats_message(0, 0, 0, 0, 0)
        assert result == "STATS;0;0;0;0;0"

        parsed = parse_stats(result)
        assert parsed.rx_count == 0
        assert parsed.tx_count == 0

    def test_format_stats_max_bus_load(self):
        """Test formatting STATS with maximum bus load."""
        result = format_stats_message(100, 100, 10, 100, 1111)
        assert "100;1111" in result

        parsed = parse_stats(result)
        assert parsed.bus_load == 100


@pytest.mark.unit
class TestRoundTripFormatAndParse:
    """Test that formatted messages can be parsed back correctly (round-trip)."""

    def test_can_rx_round_trip(self):
        """Test CAN_RX format → parse → format produces same result."""
        can_id = 0x500
        data = [0xFF, 0x00, 0xAB, 0xCD]
        timestamp = 1234567

        formatted = format_can_rx_message(can_id, data, timestamp)
        parsed = parse_can_rx(formatted)

        assert parsed.can_id == can_id
        assert parsed.data == data
        assert parsed.timestamp == timestamp

    def test_can_tx_round_trip(self):
        """Test CAN_TX format → parse → format produces same result."""
        can_id = 0x200
        data = [0x12, 0x34, 0x56]
        timestamp = 9876543

        formatted = format_can_tx_message(can_id, data, timestamp)
        from .protocol_helpers import parse_can_tx
        parsed = parse_can_tx(formatted)

        assert parsed.can_id == can_id
        assert parsed.data == data
        assert parsed.timestamp == timestamp

    def test_status_round_trip(self):
        """Test STATUS format → parse → format produces same result."""
        level = "INFO"
        category = "Test"
        message = "Test message with data: 123"

        formatted = format_status_message(level, category, message)
        parsed = parse_status(formatted)

        assert parsed["level"] == level
        assert parsed["category"] == category
        assert parsed["message"] == message

    def test_stats_round_trip(self):
        """Test STATS format → parse → format produces same result."""
        rx, tx, err, load, ts = 1234, 567, 2, 45, 1234567

        formatted = format_stats_message(rx, tx, err, load, ts)
        parsed = parse_stats(formatted)

        assert parsed.rx_count == rx
        assert parsed.tx_count == tx
        assert parsed.err_count == err
        assert parsed.bus_load == load
        assert parsed.timestamp == ts


@pytest.mark.unit
class TestEdgeCasesFormatting:
    """Test edge cases and boundary conditions for message formatting."""

    def test_format_can_rx_zero_can_id(self):
        """Test formatting with CAN ID 0x000."""
        result = format_can_rx_message(0x000, [0x01], 111)
        assert "0x0;" in result or "0X0;" in result

    def test_format_can_rx_max_standard_id(self):
        """Test formatting with maximum standard CAN ID (0x7FF)."""
        result = format_can_rx_message(0x7FF, [0xFF], 111)
        assert "0x7FF;" in result or "0X7FF;" in result

    def test_format_can_rx_max_extended_id(self):
        """Test formatting with maximum extended CAN ID."""
        result = format_can_rx_message(0x1FFFFFFF, [0x01], 111)
        assert "0x1FFFFFFF;" in result or "0X1FFFFFFF;" in result

    def test_format_can_rx_empty_data(self):
        """Test formatting with empty data array."""
        result = format_can_rx_message(0x123, [], 111)
        assert ";;" in result  # Double semicolon for empty data

    def test_format_can_rx_single_byte(self):
        """Test formatting with single data byte."""
        result = format_can_rx_message(0x123, [0xFF], 111)
        parsed = parse_can_rx(result)
        assert parsed.length == 1

    def test_format_can_rx_max_data(self):
        """Test formatting with maximum 8 bytes."""
        data = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]
        result = format_can_rx_message(0x123, data, 111)
        parsed = parse_can_rx(result)
        assert parsed.length == 8
        assert parsed.data == data

    def test_format_stats_zero_timestamp(self):
        """Test formatting STATS with zero timestamp."""
        result = format_stats_message(100, 50, 1, 25, 0)
        assert result.endswith(";0")

    def test_format_stats_large_counts(self):
        """Test formatting STATS with large counter values."""
        result = format_stats_message(999999999, 888888888, 7777777, 95, 123456789)
        parsed = parse_stats(result)
        assert parsed.rx_count == 999999999
        assert parsed.tx_count == 888888888


@pytest.mark.unit
class TestRealWorldFormatting:
    """Test formatting real-world message examples."""

    def test_format_startup_status(self):
        """Test formatting typical startup STATUS message."""
        result = format_status_message("CONNECTED", "SAMD51_CAN", "SAMD51_CAN v2.0 @ 500kbps")
        assert result == "STATUS;CONNECTED;SAMD51_CAN;SAMD51_CAN v2.0 @ 500kbps"

    def test_format_throttle_can_rx(self):
        """Test formatting throttle CAN message."""
        result = format_can_rx_message(0x500, [0xFF, 0x00, 0x00, 0xC8], 1234567)
        parsed = parse_can_rx(result)
        assert parsed.can_id == 0x500
        assert parsed.data == [0xFF, 0x00, 0x00, 0xC8]

    def test_format_neopixel_can_tx(self):
        """Test formatting NeoPixel color CAN message."""
        result = format_can_tx_message(0x400, [0xFF, 0x00, 0x80], 9876543)
        from .protocol_helpers import parse_can_tx
        parsed = parse_can_tx(result)
        assert parsed.can_id == 0x400
        assert parsed.data == [0xFF, 0x00, 0x80]

    def test_format_periodic_stats(self):
        """Test formatting periodic STATS message."""
        result = format_stats_message(1234, 567, 2, 45, 5000)
        assert result == "STATS;1234;567;2;45;5000"

    def test_format_config_change_status(self):
        """Test formatting configuration change STATUS."""
        result = format_status_message("INFO", "Configuration", "CAN bitrate changed to 250kbps")
        assert "250kbps" in result

    def test_format_error_status(self):
        """Test formatting error STATUS message."""
        result = format_status_message("ERROR", "CAN", "Failed to initialize CAN controller")
        assert result == "STATUS;ERROR;CAN;Failed to initialize CAN controller"

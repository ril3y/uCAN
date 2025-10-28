"""
Unit tests for uCAN protocol message parsing.

Tests parsing of protocol messages received FROM the device (CAN_RX, CAN_TX,
STATUS, STATS, etc.) without requiring hardware.

Run with: pytest tests/unit/test_protocol_parsing.py -v
Run unit tests only: pytest -m unit
"""

import pytest
import json
from .protocol_helpers import (
    parse_can_rx, parse_can_tx, parse_can_err, parse_status, parse_stats,
    ProtocolParseError, CANMessage, StatsMessage
)


@pytest.mark.unit
class TestCANRXParsing:
    """Test CAN_RX message parsing."""

    @pytest.mark.parametrize("message,expected_id,expected_data,expected_ts", [
        # Standard format with timestamp
        ("CAN_RX;0x123;01,02,03,04;1234567", 0x123, [0x01, 0x02, 0x03, 0x04], 1234567),
        # Different CAN IDs
        ("CAN_RX;0x500;FF,00,00,C8;1234567", 0x500, [0xFF, 0x00, 0x00, 0xC8], 1234567),
        ("CAN_RX;0x7FF;AA,BB,CC,DD,EE,FF;9999999", 0x7FF, [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF], 9999999),
        # Extended CAN ID (>0x7FF)
        ("CAN_RX;0x1FFFFFFF;01,02;5000000", 0x1FFFFFFF, [0x01, 0x02], 5000000),
        ("CAN_RX;0x800;12,34;7777777", 0x800, [0x12, 0x34], 7777777),
        # Empty data (valid)
        ("CAN_RX;0x100;;1234567", 0x100, [], 1234567),
        # Single byte
        ("CAN_RX;0x200;FF;1111111", 0x200, [0xFF], 1111111),
        # Full 8 bytes
        ("CAN_RX;0x300;00,11,22,33,44,55,66,77;2222222", 0x300,
         [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77], 2222222),
        # Lowercase hex (should work)
        ("CAN_RX;0x123;ab,cd,ef;3333333", 0x123, [0xAB, 0xCD, 0xEF], 3333333),
        # Mixed case hex
        ("CAN_RX;0x456;Aa,Bb,Cc;4444444", 0x456, [0xAA, 0xBB, 0xCC], 4444444),
        # No 0x prefix on ID (should still parse as hex per spec)
        ("CAN_RX;123;01,02;5555555", 0x123, [0x01, 0x02], 5555555),
    ])
    def test_parse_valid_can_rx_messages(self, message, expected_id, expected_data, expected_ts):
        """Test parsing valid CAN_RX messages."""
        result = parse_can_rx(message)

        assert isinstance(result, CANMessage)
        assert result.can_id == expected_id
        assert result.data == expected_data
        assert result.timestamp == expected_ts
        assert result.length == len(expected_data)

        # Check extended flag
        if expected_id > 0x7FF:
            assert result.extended is True
        else:
            assert result.extended is False

    @pytest.mark.parametrize("message,expected_id,expected_data", [
        # No timestamp (optional)
        ("CAN_RX;0x123;01,02,03", 0x123, [0x01, 0x02, 0x03]),
        ("CAN_RX;0x100;;", 0x100, []),
    ])
    def test_parse_can_rx_without_timestamp(self, message, expected_id, expected_data):
        """Test parsing CAN_RX messages without timestamp (optional field)."""
        result = parse_can_rx(message)

        assert result.can_id == expected_id
        assert result.data == expected_data
        assert result.timestamp is None

    @pytest.mark.parametrize("message,error_match", [
        # Wrong prefix
        ("CAN_TX;0x123;01,02;1111", "Expected CAN_RX prefix"),
        ("STATUS;0x123;01,02;1111", "Expected CAN_RX prefix"),
        # Too few fields
        ("CAN_RX;0x123", "at least 3 fields"),
        ("CAN_RX", "at least 3 fields"),
        # Invalid CAN ID format
        ("CAN_RX;INVALID;01,02;1111", "Invalid CAN ID format"),
        ("CAN_RX;0xGGG;01,02;1111", "Invalid CAN ID format"),
        ("CAN_RX;;01,02;1111", "Invalid CAN ID format"),
        # CAN ID out of range (>29-bit)
        ("CAN_RX;0x20000000;01,02;1111", "CAN ID out of range"),
        ("CAN_RX;0xFFFFFFFF;01,02;1111", "CAN ID out of range"),
        # Invalid data bytes
        ("CAN_RX;0x123;01,GG;1111", "Invalid data byte format"),
        ("CAN_RX;0x123;01,02,INVALID;1111", "Invalid data byte format"),
        ("CAN_RX;0x123;0x100;1111", "Data byte out of range"),  # >0xFF
        # Too many data bytes (>8)
        ("CAN_RX;0x123;01,02,03,04,05,06,07,08,09;1111", "exceeds 8 bytes"),
        # Invalid timestamp
        ("CAN_RX;0x123;01,02;NOTANUMBER", "Invalid timestamp format"),
        ("CAN_RX;0x123;01,02;12.34", "Invalid timestamp format"),
    ])
    def test_parse_invalid_can_rx_messages(self, message, error_match):
        """Test that invalid CAN_RX messages raise appropriate errors."""
        with pytest.raises(ProtocolParseError, match=error_match):
            parse_can_rx(message)

    def test_parse_can_rx_whitespace_tolerance(self):
        """Test that parser handles whitespace in fields."""
        # Extra spaces should be tolerated
        message = "CAN_RX; 0x123 ; 01,02,03 ; 1234567 "
        result = parse_can_rx(message)

        assert result.can_id == 0x123
        assert result.data == [0x01, 0x02, 0x03]
        assert result.timestamp == 1234567


@pytest.mark.unit
class TestCANTXParsing:
    """Test CAN_TX message parsing."""

    @pytest.mark.parametrize("message,expected_id,expected_data,expected_ts", [
        ("CAN_TX;0x100;01,02,03;1234580", 0x100, [0x01, 0x02, 0x03], 1234580),
        ("CAN_TX;0x200;FF;5555555", 0x200, [0xFF], 5555555),
        ("CAN_TX;0x7FF;AA,BB,CC,DD,EE,FF,00,11;9999999", 0x7FF,
         [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00, 0x11], 9999999),
    ])
    def test_parse_valid_can_tx_messages(self, message, expected_id, expected_data, expected_ts):
        """Test parsing valid CAN_TX messages."""
        result = parse_can_tx(message)

        assert result.can_id == expected_id
        assert result.data == expected_data
        assert result.timestamp == expected_ts

    @pytest.mark.parametrize("message,error_match", [
        ("CAN_RX;0x123;01,02;1111", "Expected CAN_TX prefix"),
        ("CAN_TX;INVALID;01,02;1111", "Invalid CAN ID format"),
        ("CAN_TX;0x123;01,02,03,04,05,06,07,08,09;1111", "exceeds 8 bytes"),
    ])
    def test_parse_invalid_can_tx_messages(self, message, error_match):
        """Test that invalid CAN_TX messages raise appropriate errors."""
        with pytest.raises(ProtocolParseError, match=error_match):
            parse_can_tx(message)


@pytest.mark.unit
class TestCANERRParsing:
    """Test CAN_ERR message parsing."""

    @pytest.mark.parametrize("message,expected_type,expected_details,expected_ts", [
        ("CAN_ERR;BUS_OFF;Too many errors;1234590", "BUS_OFF", "Too many errors", 1234590),
        ("CAN_ERR;TX_FAILED;Arbitration lost;1234600", "TX_FAILED", "Arbitration lost", 1234600),
        ("CAN_ERR;RX_OVERFLOW;Buffer full;1234610", "RX_OVERFLOW", "Buffer full", 1234610),
        ("CAN_ERR;ERROR_PASSIVE;Error count high;1234620", "ERROR_PASSIVE", "Error count high", 1234620),
        ("CAN_ERR;ERROR_WARNING;Approaching error limit;1234630", "ERROR_WARNING", "Approaching error limit", 1234630),
        ("CAN_ERR;ARBITRATION_LOST;Lost arbitration;1234640", "ARBITRATION_LOST", "Lost arbitration", 1234640),
    ])
    def test_parse_valid_can_err_messages(self, message, expected_type, expected_details, expected_ts):
        """Test parsing valid CAN_ERR messages."""
        result = parse_can_err(message)

        assert result["error_type"] == expected_type
        assert result["details"] == expected_details
        assert result["timestamp"] == expected_ts

    def test_parse_can_err_without_timestamp(self):
        """Test parsing CAN_ERR without timestamp."""
        message = "CAN_ERR;TX_FAILED;Arbitration lost"
        result = parse_can_err(message)

        assert result["error_type"] == "TX_FAILED"
        assert result["details"] == "Arbitration lost"
        assert result["timestamp"] is None

    @pytest.mark.parametrize("message,error_match", [
        ("CAN_ERR;INVALID_ERROR;Details;1111", "Invalid error type"),
        ("CAN_ERR;UNKNOWN;Details;1111", "Invalid error type"),
        ("CAN_ERR", "at least 3 fields"),
        ("CAN_ERR;TX_FAILED", "at least 3 fields"),
        ("STATUS;ERROR;Details;1111", "Expected CAN_ERR prefix"),
    ])
    def test_parse_invalid_can_err_messages(self, message, error_match):
        """Test that invalid CAN_ERR messages raise appropriate errors."""
        with pytest.raises(ProtocolParseError, match=error_match):
            parse_can_err(message)


@pytest.mark.unit
class TestSTATUSParsing:
    """Test STATUS message parsing."""

    @pytest.mark.parametrize("message,expected_level,expected_category,expected_msg", [
        ("STATUS;INFO;Configuration;CAN bitrate changed to 250kbps",
         "INFO", "Configuration", "CAN bitrate changed to 250kbps"),
        ("STATUS;ERROR;CAN;Failed to initialize",
         "ERROR", "CAN", "Failed to initialize"),
        ("STATUS;CONNECTED;SAMD51_CAN;SAMD51_CAN v2.0 @ 500kbps",
         "CONNECTED", "SAMD51_CAN", "SAMD51_CAN v2.0 @ 500kbps"),
        ("STATUS;WARN;Buffer;Buffer nearly full",
         "WARN", "Buffer", "Buffer nearly full"),
        ("STATUS;DISCONNECTED;CAN;Bus disconnected",
         "DISCONNECTED", "CAN", "Bus disconnected"),
        # Message with semicolons (should preserve them)
        ("STATUS;INFO;Test;Message with ; semicolon ; inside",
         "INFO", "Test", "Message with ; semicolon ; inside"),
    ])
    def test_parse_valid_status_messages(self, message, expected_level, expected_category, expected_msg):
        """Test parsing valid STATUS messages."""
        result = parse_status(message)

        assert result["level"] == expected_level
        assert result["category"] == expected_category
        assert result["message"] == expected_msg

    @pytest.mark.parametrize("message,expected_level,expected_category", [
        # Minimal format (level only)
        ("STATUS;INFO", "INFO", ""),
        ("STATUS;ERROR;CAN", "ERROR", "CAN"),
    ])
    def test_parse_status_minimal_format(self, message, expected_level, expected_category):
        """Test parsing STATUS messages with minimal fields."""
        result = parse_status(message)

        assert result["level"] == expected_level
        assert result["category"] == expected_category

    @pytest.mark.parametrize("message,error_match", [
        ("STATUS;INVALID;Category;Message", "Invalid status level"),
        ("STATUS;UNKNOWN", "Invalid status level"),
        ("STATUS", "at least 2 fields"),
        ("CAN_RX;INFO;Message", "Expected STATUS prefix"),
    ])
    def test_parse_invalid_status_messages(self, message, error_match):
        """Test that invalid STATUS messages raise appropriate errors."""
        with pytest.raises(ProtocolParseError, match=error_match):
            parse_status(message)


@pytest.mark.unit
class TestSTATSParsing:
    """Test STATS message parsing."""

    @pytest.mark.parametrize("message,expected_rx,expected_tx,expected_err,expected_load,expected_ts", [
        ("STATS;1234;567;2;45;1234567", 1234, 567, 2, 45, 1234567),
        ("STATS;0;0;0;0;0", 0, 0, 0, 0, 0),
        ("STATS;999999;888888;777;100;9999999", 999999, 888888, 777, 100, 9999999),
        ("STATS;100;200;5;50;5000000", 100, 200, 5, 50, 5000000),
    ])
    def test_parse_valid_stats_messages(self, message, expected_rx, expected_tx,
                                       expected_err, expected_load, expected_ts):
        """Test parsing valid STATS messages."""
        result = parse_stats(message)

        assert isinstance(result, StatsMessage)
        assert result.rx_count == expected_rx
        assert result.tx_count == expected_tx
        assert result.err_count == expected_err
        assert result.bus_load == expected_load
        assert result.timestamp == expected_ts

    @pytest.mark.parametrize("message,error_match", [
        # Wrong number of fields
        ("STATS;100;200;5;50", "exactly 6 fields"),
        ("STATS;100;200;5;50;1111;EXTRA", "exactly 6 fields"),
        ("STATS", "exactly 6 fields"),
        # Invalid numeric values
        ("STATS;ABC;200;5;50;1111", "Invalid numeric field"),
        ("STATS;100;XYZ;5;50;1111", "Invalid numeric field"),
        ("STATS;100;200;ERR;50;1111", "Invalid numeric field"),
        ("STATS;100;200;5;LOAD;1111", "Invalid numeric field"),
        ("STATS;100;200;5;50;TIME", "Invalid numeric field"),
        # Bus load out of range
        ("STATS;100;200;5;101;1111", "Bus load must be 0-100%"),
        ("STATS;100;200;5;-1;1111", "Bus load must be 0-100%"),
        ("STATS;100;200;5;255;1111", "Bus load must be 0-100%"),
        # Negative counts
        ("STATS;-100;200;5;50;1111", "must be non-negative"),
        ("STATS;100;-200;5;50;1111", "must be non-negative"),
        ("STATS;100;200;-5;50;1111", "must be non-negative"),
        # Wrong prefix
        ("STATUS;100;200;5;50;1111", "Expected STATS prefix"),
    ])
    def test_parse_invalid_stats_messages(self, message, error_match):
        """Test that invalid STATS messages raise appropriate errors."""
        with pytest.raises(ProtocolParseError, match=error_match):
            parse_stats(message)


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_parse_can_rx_max_standard_id(self):
        """Test parsing CAN_RX with maximum standard ID (0x7FF)."""
        message = "CAN_RX;0x7FF;01,02;1111"
        result = parse_can_rx(message)

        assert result.can_id == 0x7FF
        assert result.extended is False

    def test_parse_can_rx_min_extended_id(self):
        """Test parsing CAN_RX with minimum extended ID (0x800)."""
        message = "CAN_RX;0x800;01,02;1111"
        result = parse_can_rx(message)

        assert result.can_id == 0x800
        assert result.extended is True

    def test_parse_can_rx_max_extended_id(self):
        """Test parsing CAN_RX with maximum extended ID (0x1FFFFFFF)."""
        message = "CAN_RX;0x1FFFFFFF;FF;1111"
        result = parse_can_rx(message)

        assert result.can_id == 0x1FFFFFFF
        assert result.extended is True

    def test_parse_can_rx_zero_id(self):
        """Test parsing CAN_RX with ID 0x000."""
        message = "CAN_RX;0x000;01;1111"
        result = parse_can_rx(message)

        assert result.can_id == 0x000
        assert result.extended is False

    def test_parse_can_rx_max_data_length(self):
        """Test parsing CAN_RX with exactly 8 bytes (maximum)."""
        message = "CAN_RX;0x123;00,11,22,33,44,55,66,77;1111"
        result = parse_can_rx(message)

        assert result.length == 8
        assert result.data == [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]

    def test_parse_stats_zero_values(self):
        """Test parsing STATS with all zero values."""
        message = "STATS;0;0;0;0;0"
        result = parse_stats(message)

        assert result.rx_count == 0
        assert result.tx_count == 0
        assert result.err_count == 0
        assert result.bus_load == 0
        assert result.timestamp == 0

    def test_parse_stats_max_bus_load(self):
        """Test parsing STATS with maximum bus load (100%)."""
        message = "STATS;100;100;10;100;1111"
        result = parse_stats(message)

        assert result.bus_load == 100

    def test_parse_empty_can_data(self):
        """Test parsing CAN messages with empty data field."""
        message = "CAN_RX;0x123;;1111"
        result = parse_can_rx(message)

        assert result.length == 0
        assert result.data == []

    def test_case_insensitive_hex_parsing(self):
        """Test that hex values are case-insensitive."""
        messages = [
            "CAN_RX;0x123;ab,cd,ef;1111",
            "CAN_RX;0x123;AB,CD,EF;1111",
            "CAN_RX;0x123;Ab,Cd,Ef;1111",
        ]

        for msg in messages:
            result = parse_can_rx(msg)
            assert result.data == [0xAB, 0xCD, 0xEF]

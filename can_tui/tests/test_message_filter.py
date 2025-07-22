#!/usr/bin/env python3
"""
Unit tests for message filtering functionality.
"""

import pytest
from datetime import datetime
from models.can_message import CANMessage, MessageFilter, MessageType


class TestMessageFilter:
    """Test cases for MessageFilter functionality."""
    
    def test_default_filter_shows_all(self):
        """Test that default filter shows all message types."""
        message_filter = MessageFilter()
        
        assert message_filter.show_rx is True
        assert message_filter.show_tx is True
        assert message_filter.show_errors is True
        assert message_filter.show_info is True
    
    def test_filter_rx_messages(self):
        """Test filtering RX messages."""
        message_filter = MessageFilter(show_rx=False)
        
        rx_message = CANMessage(
            type=MessageType.RX,
            can_id=0x123,
            data=[0x01, 0x02, 0x03],
            data_length=3
        )
        
        tx_message = CANMessage(
            type=MessageType.TX,
            can_id=0x456,
            data=[0x04, 0x05, 0x06],
            data_length=3
        )
        
        assert not message_filter.matches(rx_message)
        assert message_filter.matches(tx_message)
    
    def test_filter_tx_messages(self):
        """Test filtering TX messages."""
        message_filter = MessageFilter(show_tx=False)
        
        rx_message = CANMessage(
            type=MessageType.RX,
            can_id=0x123,
            data=[0x01, 0x02, 0x03],
            data_length=3
        )
        
        tx_message = CANMessage(
            type=MessageType.TX,
            can_id=0x456,
            data=[0x04, 0x05, 0x06],
            data_length=3
        )
        
        assert message_filter.matches(rx_message)
        assert not message_filter.matches(tx_message)
    
    def test_filter_error_messages(self):
        """Test filtering error messages."""
        message_filter = MessageFilter(show_errors=False)
        
        error_message = CANMessage(
            type=MessageType.ERROR,
            error_message="Test error",
            success=False
        )
        
        info_message = CANMessage(
            type=MessageType.INFO,
            error_message="Test info",
            success=True
        )
        
        assert not message_filter.matches(error_message)
        assert message_filter.matches(info_message)
    
    def test_filter_info_messages(self):
        """Test filtering info messages."""
        message_filter = MessageFilter(show_info=False)
        
        error_message = CANMessage(
            type=MessageType.ERROR,
            error_message="Test error",
            success=False
        )
        
        info_message = CANMessage(
            type=MessageType.INFO,
            error_message="Test info",
            success=True
        )
        
        assert message_filter.matches(error_message)
        assert not message_filter.matches(info_message)
    
    def test_filter_multiple_types(self):
        """Test filtering multiple message types simultaneously."""
        message_filter = MessageFilter(show_rx=False, show_errors=False)
        
        rx_message = CANMessage(
            type=MessageType.RX,
            can_id=0x123,
            data=[0x01, 0x02, 0x03],
            data_length=3
        )
        
        tx_message = CANMessage(
            type=MessageType.TX,
            can_id=0x456,
            data=[0x04, 0x05, 0x06],
            data_length=3
        )
        
        error_message = CANMessage(
            type=MessageType.ERROR,
            error_message="Test error",
            success=False
        )
        
        info_message = CANMessage(
            type=MessageType.INFO,
            error_message="Test info",
            success=True
        )
        
        assert not message_filter.matches(rx_message)
        assert message_filter.matches(tx_message)
        assert not message_filter.matches(error_message)
        assert message_filter.matches(info_message)
    
    def test_filter_by_can_id_hex(self):
        """Test filtering by CAN ID in hex format."""
        message_filter = MessageFilter(id_filter="0x123")
        
        matching_message = CANMessage(
            type=MessageType.RX,
            can_id=0x123,
            data=[0x01, 0x02],
            data_length=2
        )
        
        non_matching_message = CANMessage(
            type=MessageType.RX,
            can_id=0x456,
            data=[0x01, 0x02],
            data_length=2
        )
        
        assert message_filter.matches(matching_message)
        assert not message_filter.matches(non_matching_message)
    
    def test_filter_by_can_id_decimal(self):
        """Test filtering by CAN ID in decimal format."""
        message_filter = MessageFilter(id_filter="291")  # 0x123 in decimal
        
        matching_message = CANMessage(
            type=MessageType.RX,
            can_id=0x123,
            data=[0x01, 0x02],
            data_length=2
        )
        
        non_matching_message = CANMessage(
            type=MessageType.RX,
            can_id=0x456,
            data=[0x01, 0x02],
            data_length=2
        )
        
        assert message_filter.matches(matching_message)
        assert not message_filter.matches(non_matching_message)
    
    def test_filter_invalid_can_id_format(self):
        """Test that invalid CAN ID filter format is ignored."""
        message_filter = MessageFilter(id_filter="invalid")
        
        message = CANMessage(
            type=MessageType.RX,
            can_id=0x123,
            data=[0x01, 0x02],
            data_length=2
        )
        
        # Should match because invalid filter is ignored
        assert message_filter.matches(message)
    
    def test_filter_message_without_can_id(self):
        """Test filtering messages without CAN ID (like errors/info)."""
        message_filter = MessageFilter(id_filter="0x123")
        
        error_message = CANMessage(
            type=MessageType.ERROR,
            error_message="Test error",
            success=False
        )
        
        # Should match because error message has no CAN ID to filter
        assert message_filter.matches(error_message)
    
    def test_combined_type_and_id_filter(self):
        """Test combining type filtering with ID filtering."""
        message_filter = MessageFilter(show_rx=False, id_filter="0x123")
        
        rx_message_matching_id = CANMessage(
            type=MessageType.RX,
            can_id=0x123,
            data=[0x01, 0x02],
            data_length=2
        )
        
        tx_message_matching_id = CANMessage(
            type=MessageType.TX,
            can_id=0x123,
            data=[0x03, 0x04],
            data_length=2
        )
        
        tx_message_non_matching_id = CANMessage(
            type=MessageType.TX,
            can_id=0x456,
            data=[0x05, 0x06],
            data_length=2
        )
        
        # RX is filtered out even though ID matches
        assert not message_filter.matches(rx_message_matching_id)
        # TX with matching ID should pass
        assert message_filter.matches(tx_message_matching_id)
        # TX with non-matching ID should not pass
        assert not message_filter.matches(tx_message_non_matching_id)


if __name__ == "__main__":
    pytest.main([__file__])
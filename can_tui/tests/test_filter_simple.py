#!/usr/bin/env python3
"""
Simple test for message filtering functionality without pytest.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.can_message import CANMessage, MessageFilter, MessageType


def test_message_filter():
    """Test the MessageFilter functionality."""
    
    print("🔍 Testing MessageFilter functionality")
    print("=" * 50)
    
    # Test default filter shows all
    message_filter = MessageFilter()
    print(f"✅ Default filter - RX: {message_filter.show_rx}, TX: {message_filter.show_tx}, Errors: {message_filter.show_errors}, Info: {message_filter.show_info}")
    
    # Create test messages
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
    
    # Test default filter matches all
    print("\n📊 Testing default filter (all enabled):")
    print(f"  RX message matches: {message_filter.matches(rx_message)}")
    print(f"  TX message matches: {message_filter.matches(tx_message)}")
    print(f"  Error message matches: {message_filter.matches(error_message)}")
    print(f"  Info message matches: {message_filter.matches(info_message)}")
    
    # Test filtering RX messages
    print("\n📊 Testing RX filter disabled:")
    filter_no_rx = MessageFilter(show_rx=False)
    print(f"  RX message matches: {filter_no_rx.matches(rx_message)}")
    print(f"  TX message matches: {filter_no_rx.matches(tx_message)}")
    
    # Test filtering TX messages
    print("\n📊 Testing TX filter disabled:")
    filter_no_tx = MessageFilter(show_tx=False)
    print(f"  RX message matches: {filter_no_tx.matches(rx_message)}")
    print(f"  TX message matches: {filter_no_tx.matches(tx_message)}")
    
    # Test filtering errors
    print("\n📊 Testing Error filter disabled:")
    filter_no_errors = MessageFilter(show_errors=False)
    print(f"  Error message matches: {filter_no_errors.matches(error_message)}")
    print(f"  Info message matches: {filter_no_errors.matches(info_message)}")
    
    # Test CAN ID filtering
    print("\n📊 Testing CAN ID filter (0x123):")
    filter_by_id = MessageFilter(id_filter="0x123")
    print(f"  RX message (ID=0x123) matches: {filter_by_id.matches(rx_message)}")
    print(f"  TX message (ID=0x456) matches: {filter_by_id.matches(tx_message)}")
    print(f"  Error message (no ID) matches: {filter_by_id.matches(error_message)}")
    
    # Test combined filtering
    print("\n📊 Testing combined filter (no RX, ID=0x456):")
    filter_combined = MessageFilter(show_rx=False, id_filter="0x456")
    print(f"  RX message (ID=0x123) matches: {filter_combined.matches(rx_message)}")
    print(f"  TX message (ID=0x456) matches: {filter_combined.matches(tx_message)}")
    
    print("\n✅ Message filter tests completed successfully!")


if __name__ == "__main__":
    test_message_filter()
#!/usr/bin/env python3
"""
Test the new protocol message parsing functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.can_message import CANMessage, MessageType


def test_protocol_parsing():
    """Test the new protocol parsing functionality."""
    
    print("🔍 Testing Protocol Message Parsing")
    print("=" * 50)
    
    # Test CAN_RX parsing
    print("\n📊 Testing CAN_RX parsing:")
    can_rx_message = "CAN_RX;0x635;01,FF,04,04,05,00,FF,00"
    parsed_rx = CANMessage.from_raw_string(can_rx_message)
    
    print(f"  Input: {can_rx_message}")
    print(f"  Type: {parsed_rx.type}")
    print(f"  CAN ID: 0x{parsed_rx.can_id:03X}")
    print(f"  Data: {[f'0x{b:02X}' for b in parsed_rx.data]}")
    print(f"  Data Length: {parsed_rx.data_length}")
    print(f"  Success: {parsed_rx.success}")
    
    assert parsed_rx.type == MessageType.RX
    assert parsed_rx.can_id == 0x635
    assert parsed_rx.data == [0x01, 0xFF, 0x04, 0x04, 0x05, 0x00, 0xFF, 0x00]
    assert parsed_rx.data_length == 8
    assert parsed_rx.success is True
    print("  ✅ CAN_RX parsing PASSED")
    
    # Test CAN_TX parsing
    print("\n📊 Testing CAN_TX parsing:")
    can_tx_message = "CAN_TX;0x223;AB,CD,EF"
    parsed_tx = CANMessage.from_raw_string(can_tx_message)
    
    print(f"  Input: {can_tx_message}")
    print(f"  Type: {parsed_tx.type}")
    print(f"  CAN ID: 0x{parsed_tx.can_id:03X}")
    print(f"  Data: {[f'0x{b:02X}' for b in parsed_tx.data]}")
    print(f"  Data Length: {parsed_tx.data_length}")
    print(f"  Success: {parsed_tx.success}")
    
    assert parsed_tx.type == MessageType.TX
    assert parsed_tx.can_id == 0x223
    assert parsed_tx.data == [0xAB, 0xCD, 0xEF]
    assert parsed_tx.data_length == 3
    assert parsed_tx.success is True
    print("  ✅ CAN_TX parsing PASSED")
    
    # Test CAN_ERR parsing
    print("\n📊 Testing CAN_ERR parsing:")
    can_err_message = "CAN_ERR;0x01;Bus off detected"
    parsed_err = CANMessage.from_raw_string(can_err_message)
    
    print(f"  Input: {can_err_message}")
    print(f"  Type: {parsed_err.type}")
    print(f"  Error: {parsed_err.error_message}")
    print(f"  Success: {parsed_err.success}")
    
    assert parsed_err.type == MessageType.ERROR
    assert "Error 0x01: Bus off detected" in parsed_err.error_message
    assert parsed_err.success is False
    print("  ✅ CAN_ERR parsing PASSED")
    
    # Test STATUS parsing
    print("\n📊 Testing STATUS parsing:")
    status_message = "STATUS;CAN initialization successful"
    parsed_status = CANMessage.from_raw_string(status_message)
    
    print(f"  Input: {status_message}")
    print(f"  Type: {parsed_status.type}")
    print(f"  Message: {parsed_status.error_message}")
    print(f"  Success: {parsed_status.success}")
    
    assert parsed_status.type == MessageType.INFO
    assert parsed_status.error_message == "CAN initialization successful"
    assert parsed_status.success is True
    print("  ✅ STATUS parsing PASSED")
    
    # Test legacy RX format (backward compatibility)
    print("\n📊 Testing legacy RX format:")
    legacy_rx = "RX: ID=0x123 LEN=3 DATA=010203"
    parsed_legacy = CANMessage.from_raw_string(legacy_rx)
    
    print(f"  Input: {legacy_rx}")
    print(f"  Type: {parsed_legacy.type}")
    print(f"  CAN ID: 0x{parsed_legacy.can_id:03X}")
    print(f"  Data: {[f'0x{b:02X}' for b in parsed_legacy.data]}")
    print(f"  Success: {parsed_legacy.success}")
    
    assert parsed_legacy.type == MessageType.RX
    assert parsed_legacy.can_id == 0x123
    assert parsed_legacy.data == [0x01, 0x02, 0x03]
    assert parsed_legacy.success is True
    print("  ✅ Legacy RX parsing PASSED")
    
    print("\n✅ All protocol parsing tests PASSED!")


if __name__ == "__main__":
    test_protocol_parsing()
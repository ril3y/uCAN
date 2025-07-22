#!/usr/bin/env python3
"""
Simple test for the wiring harness parser without TUI dependencies.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'can_tui'))

# Import only the parser classes
from parsers.base import ProtocolParser, ParsedMessage, ParsedField, FieldType, ValidationStatus
from parsers.custom.wiring_harness import WiringHarnessParser

def test_wiring_harness_parser():
    """Test the wiring harness parser with sample data."""
    
    print("🚗 Testing STM32F103 Wiring Harness Parser")
    print("=" * 50)
    
    # Create parser
    parser = WiringHarnessParser()
    
    # Test data: Forward switch on, foot switch on, 50% throttle, no brake
    test_data = bytes([
        0x01,  # Byte 0: FWD_SW_IN = 1
        0x01,  # Byte 1: FOOT_SW_UC = 1  
        50,    # Byte 2: Throttle = 50%
        0,     # Byte 3: Brake = 0%
        42,    # Byte 4: Sequence = 42
        0x00,  # Byte 5: No errors
        0x00,  # Byte 6: CRC8 (will be calculated)
        0xAA   # Byte 7: End marker
    ])
    
    # Calculate correct CRC for the first 6 bytes
    data = bytearray(test_data)
    crc = parser._calculate_crc8(data[0:6])
    data[6] = crc
    
    print(f"📊 Test Data: {' '.join(f'{b:02X}' for b in data)}")
    print(f"📊 CRC8 calculated: 0x{crc:02X}")
    
    # Parse the message
    can_id = 0x410
    parsed = parser.parse(can_id, bytes(data))
    
    print(f"\n✅ Parser: {parsed.parser_name}")
    print(f"✅ Message: {parsed.message_name}")
    print(f"✅ Confidence: {parsed.confidence:.1%}")
    print(f"✅ Valid: {parsed.is_valid()}")
    
    if parsed.errors:
        print(f"❌ Errors: {', '.join(parsed.errors)}")
    if parsed.warnings:
        print(f"⚠️  Warnings: {', '.join(parsed.warnings)}")
    
    print("\n🔍 Parsed Fields:")
    for field in parsed.fields:
        status_symbol = field.get_status_symbol()
        formatted_value = field.format_value()
        unit = f" {field.unit}" if field.unit else ""
        
        print(f"  {status_symbol} {field.name}: {formatted_value}{unit}")
        if field.validation_message:
            print(f"    └─ {field.validation_message}")


def test_crc_calculation():
    """Test CRC8 calculation."""
    
    print("\n\n🔧 Testing CRC8 Calculation")
    print("=" * 30)
    
    parser = WiringHarnessParser()
    
    # Test known data
    test_data = bytes([0x01, 0x01, 50, 0, 42, 0x00])
    crc = parser._calculate_crc8(test_data)
    
    print(f"Data: {' '.join(f'{b:02X}' for b in test_data)}")
    print(f"CRC8: 0x{crc:02X}")
    
    # Test with different data
    test_data2 = bytes([0x06, 0x01, 0, 75, 43, 0x00])
    crc2 = parser._calculate_crc8(test_data2)
    
    print(f"Data: {' '.join(f'{b:02X}' for b in test_data2)}")
    print(f"CRC8: 0x{crc2:02X}")


if __name__ == "__main__":
    test_wiring_harness_parser()
    test_crc_calculation()
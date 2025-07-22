#!/usr/bin/env python3
"""
Test script for the wiring harness parser.
Demonstrates parsing of STM32F103 wiring harness CAN messages.
"""

import sys
sys.path.insert(0, '.')

from can_tui.parsers import WiringHarnessParser, ParserRegistry, RawDataParser

def test_wiring_harness_parser():
    """Test the wiring harness parser with sample data."""
    
    # Create parser
    parser = WiringHarnessParser()
    
    print("🚗 Testing STM32F103 Wiring Harness Parser")
    print("=" * 50)
    
    # Test data examples
    test_cases = [
        {
            "name": "Normal Operation - Forward, Throttle 50%",
            "data": bytes([
                0x01,  # Byte 0: FWD_SW_IN = 1
                0x01,  # Byte 1: FOOT_SW_UC = 1  
                50,    # Byte 2: Throttle = 50%
                0,     # Byte 3: Brake = 0%
                42,    # Byte 4: Sequence = 42
                0x00,  # Byte 5: No errors
                0x00,  # Byte 6: CRC8 (will be calculated)
                0xAA   # Byte 7: End marker
            ])
        },
        {
            "name": "Braking - Reverse, Eco Mode",
            "data": bytes([
                0x06,  # Byte 0: REV_SW_UC=1, ECO_SW_UC=1
                0x01,  # Byte 1: FOOT_SW_UC = 1
                0,     # Byte 2: Throttle = 0%  
                75,    # Byte 3: Brake = 75%
                43,    # Byte 4: Sequence = 43
                0x00,  # Byte 5: No errors
                0x00,  # Byte 6: CRC8 (will be calculated)
                0xAA   # Byte 7: End marker
            ])
        },
        {
            "name": "System Error - CAN Error",
            "data": bytes([
                0x00,  # Byte 0: All switches off
                0x00,  # Byte 1: Foot switch off
                0,     # Byte 2: Throttle = 0%
                0,     # Byte 3: Brake = 0%
                44,    # Byte 4: Sequence = 44
                0x80,  # Byte 5: CAN Error = 1
                0x00,  # Byte 6: CRC8 (will be calculated)
                0xAA   # Byte 7: End marker
            ])
        },
        {
            "name": "Invalid End Marker",
            "data": bytes([
                0x01,  # Byte 0: FWD_SW_IN = 1
                0x00,  # Byte 1: No foot switch
                25,    # Byte 2: Throttle = 25%
                0,     # Byte 3: Brake = 0%
                45,    # Byte 4: Sequence = 45
                0x00,  # Byte 5: No errors
                0x00,  # Byte 6: CRC8 (will be calculated)
                0xBB   # Byte 7: Invalid end marker
            ])
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n📋 Test Case {i+1}: {test_case['name']}")
        print("-" * 40)
        
        # Calculate correct CRC for the first 6 bytes
        data = bytearray(test_case['data'])
        crc = parser._calculate_crc8(data[0:6])
        data[6] = crc
        
        # Parse the message
        can_id = 0x410
        parsed = parser.parse(can_id, bytes(data))
        
        print(f"Parser: {parsed.parser_name}")
        print(f"Message: {parsed.message_name}")
        print(f"Confidence: {parsed.confidence:.1%}")
        print(f"Valid: {parsed.is_valid()}")
        
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
        
        print(f"\n📊 Raw Data: {' '.join(f'{b:02X}' for b in data)}")


def test_parser_registry():
    """Test the parser registry system."""
    
    print("\n\n🔧 Testing Parser Registry")
    print("=" * 50)
    
    # Create registry
    registry = ParserRegistry()
    
    # Register parsers
    registry.register_parser(RawDataParser())
    registry.register_parser(WiringHarnessParser())
    
    # Set up mappings
    registry.add_can_id_mapping(0x410, "STM32F103 Wiring Harness v1.0")
    registry.set_default_parser("Raw Data v1.0")
    
    # Test parsing
    test_data = bytes([0x01, 0x01, 50, 0, 42, 0x00, 0x00, 0xAA])
    
    # Calculate CRC
    wh_parser = WiringHarnessParser()
    crc = wh_parser._calculate_crc8(test_data[0:6])
    test_data = test_data[:6] + bytes([crc]) + test_data[7:]
    
    # Parse with registry
    parsed = registry.parse_message(0x410, test_data)
    
    print(f"✅ Registry found parser: {parsed.parser_name if parsed else 'None'}")
    print(f"✅ Message type: {parsed.message_type if parsed else 'None'}")
    
    # Test unknown ID
    unknown_parsed = registry.parse_message(0x999, bytes([0x01, 0x02, 0x03]))
    print(f"✅ Unknown ID parser: {unknown_parsed.parser_name if unknown_parsed else 'None'}")
    
    # Show registry stats
    stats = registry.get_stats()
    print(f"\n📊 Registry Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_wiring_harness_parser()
    test_parser_registry()
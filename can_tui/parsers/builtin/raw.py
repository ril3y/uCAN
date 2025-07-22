"""
Raw data parser - default fallback parser for unknown messages.
"""

from typing import List, Union, Tuple
from ..base import ProtocolParser, ParsedMessage, ParsedField, FieldType, ValidationStatus


class RawDataParser(ProtocolParser):
    """
    Default parser that displays raw hex data with basic byte breakdown.
    Used as fallback when no specific protocol parser is available.
    """
    
    def __init__(self):
        super().__init__("Raw Data", "1.0")
        self.priority = 10  # Lowest priority (fallback)
    
    def can_parse(self, can_id: int, data: bytes) -> bool:
        """Can parse any message (fallback parser)."""
        return True
    
    def parse(self, can_id: int, data: bytes) -> ParsedMessage:
        """Parse message as raw hex data with byte breakdown."""
        message = ParsedMessage(
            parser_name=self.get_name(),
            parser_version=self.get_version(),
            message_type="Raw Data",
            message_name=f"CAN ID 0x{can_id:03X}",
            confidence=1.0
        )
        
        # Add CAN ID field
        message.add_field(ParsedField(
            name="CAN ID",
            value=can_id,
            raw_value=can_id,
            bit_range=(-12, -1),  # Special range for CAN ID
            description="CAN message identifier",
            field_type=FieldType.INTEGER,
            validation_status=ValidationStatus.VALID
        ))
        
        # Add data length field
        message.add_field(ParsedField(
            name="Data Length",
            value=len(data),
            unit="bytes",
            raw_value=len(data),
            bit_range=(-4, -1),  # Special range for DLC
            description="Data Length Code (DLC)",
            field_type=FieldType.INTEGER,
            validation_status=ValidationStatus.VALID if len(data) <= 8 else ValidationStatus.WARNING,
            validation_message="Standard CAN allows max 8 bytes" if len(data) > 8 else ""
        ))
        
        # Add individual byte fields
        for i, byte in enumerate(data):
            start_bit = i * 8
            end_bit = start_bit + 7
            
            # Determine if byte value looks suspicious
            validation_status = ValidationStatus.VALID
            validation_message = ""
            
            # Check for common patterns
            if byte == 0x00:
                validation_message = "Zero value"
            elif byte == 0xFF:
                validation_message = "Maximum value"
            elif byte in [0xAA, 0x55]:
                validation_message = "Test pattern"
            
            message.add_field(ParsedField(
                name=f"Byte {i}",
                value=byte,
                raw_value=byte,
                bit_range=(start_bit, end_bit),
                description=f"Data byte {i} (0x{byte:02X})",
                field_type=FieldType.INTEGER,
                validation_status=validation_status,
                validation_message=validation_message
            ))
        
        # Add full data field
        if data:
            message.add_field(ParsedField(
                name="Full Data",
                value=data,
                raw_value=data,
                bit_range=(0, len(data) * 8 - 1),
                description="Complete message payload",
                field_type=FieldType.BYTES,
                validation_status=ValidationStatus.VALID
            ))
        
        return message
    
    def get_description(self) -> str:
        """Return parser description."""
        return "Default parser for displaying raw hex data with byte breakdown"
    
    def get_supported_ids(self) -> List[Union[int, Tuple[int, int]]]:
        """Supports all CAN IDs (fallback parser)."""
        return [(0x000, 0x7FF)]  # Standard CAN ID range
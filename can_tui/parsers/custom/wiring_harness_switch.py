"""
Wiring Harness Switch State Parser for CAN ID 0x500.

This parser handles the specific 8-byte switch state message structure
with signature validation, switch bitmap decoding, and timestamp extraction.
"""

from typing import List, Union, Tuple, Optional
from ..base import ProtocolParser, ParsedMessage, ParsedField, FieldType, ValidationStatus


class WiringHarnessSwitchParser(ProtocolParser):
    """
    Parser for wiring harness switch state messages.
    
    CAN ID: 0x500 (Switch State Message)
    Data Length: 8 bytes
    
    8-byte packet structure:
    Byte 0: 0x5A          - Message signature (constant)
    Byte 1: Switch bitmap  - Bit field of switch states
    Byte 2: Time LSB       - Timestamp low byte
    Byte 3: Time byte 1    - Timestamp
    Byte 4: Time byte 2    - Timestamp
    Byte 5: Time MSB       - Timestamp high byte
    Byte 6: 0x00          - Reserved
    Byte 7: 0xFF          - End marker (constant)
    
    Switch bitmap (Byte 1) bit definitions:
    Bit 0: Brake Switch
    Bit 1: Accelerator Switch
    Bit 2: Reverse Switch
    Bit 3: Forward Switch
    Bit 4: Horn Switch
    Bit 5: Light Switch
    Bit 6: Turn Signal Left
    Bit 7: Turn Signal Right
    """
    
    SIGNATURE = 0x5A
    END_MARKER = 0xFF
    RESERVED_VALUE = 0x00
    
    SWITCH_NAMES = {
        0: "Brake Switch",      # Bit 0: brake_pressed
        1: "Eco Switch",        # Bit 1: eco_pressed  
        2: "Reverse Switch",    # Bit 2: reverse_pressed
        3: "Foot Switch",       # Bit 3: foot_pressed
        4: "Forward Switch",    # Bit 4: forward_pressed
        5: "Reserved",          # Bit 5: unused
        6: "Reserved",          # Bit 6: unused  
        7: "Reserved"           # Bit 7: unused
    }
    
    def __init__(self):
        super().__init__("Wiring Harness Switch State", "1.0")
        self.priority = 2  # High priority for switch monitoring
        self.last_timestamp = None
        self.message_count = 0
        
    def can_parse(self, can_id: int, data: bytes) -> bool:
        """Can parse switch state messages from CAN ID 0x500."""
        if can_id != 0x500 or len(data) != 8:
            return False
            
        # Quick signature and end marker validation
        return data[0] == self.SIGNATURE and data[7] == self.END_MARKER
    
    def parse(self, can_id: int, data: bytes) -> ParsedMessage:
        """Parse wiring harness switch state message."""
        self.message_count += 1
        
        message = ParsedMessage(
            parser_name=self.get_name(),
            parser_version=self.get_version(),
            message_type="Switch State",
            message_name="Wiring Harness Switches",
            confidence=1.0
        )
        
        # Validate packet structure first
        if not self._validate_packet(data, message):
            return message
        
        # Parse Message Signature (Byte 0)
        signature = data[0]
        message.add_field(ParsedField(
            name="Message Signature",
            value=f"0x{signature:02X}",
            raw_value=signature,
            bit_range=(0, 7),
            description="Message signature (should be 0x5A)",
            field_type=FieldType.INTEGER,
            validation_status=ValidationStatus.VALID if signature == self.SIGNATURE else ValidationStatus.ERROR,
            validation_message="Valid signature" if signature == self.SIGNATURE else f"Invalid signature: expected 0x5A, got 0x{signature:02X}"
        ))
        
        # Parse Switch Bitmap (Byte 1)
        switch_bitmap = data[1]
        
        # Add overall bitmap field
        message.add_field(ParsedField(
            name="Switch Bitmap",
            value=f"0b{switch_bitmap:08b} (0x{switch_bitmap:02X})",
            raw_value=switch_bitmap,
            bit_range=(8, 15),
            description="Switch state bitmap (8 switches)",
            field_type=FieldType.BITMASK,
            validation_status=ValidationStatus.VALID
        ))
        
        # Parse individual switch states
        active_switches = []
        for bit_pos in range(8):
            switch_active = bool(switch_bitmap & (1 << bit_pos))
            switch_name = self.SWITCH_NAMES.get(bit_pos, f"Switch {bit_pos}")
            
            if switch_active:
                active_switches.append(switch_name)
            
            message.add_field(ParsedField(
                name=switch_name,
                value=switch_active,
                raw_value=int(switch_active),
                bit_range=(8 + bit_pos, 8 + bit_pos),
                description=f"State of {switch_name.lower()}",
                field_type=FieldType.BOOLEAN,
                validation_status=ValidationStatus.VALID
            ))
        
        # Parse Timestamp (Bytes 2-5, little-endian)
        timestamp_bytes = data[2:6]
        timestamp = int.from_bytes(timestamp_bytes, byteorder='little')
        
        # Calculate time difference if we have a previous timestamp
        time_diff_ms = None
        if self.last_timestamp is not None:
            # Handle timestamp rollover (assuming 32-bit counter)
            if timestamp >= self.last_timestamp:
                time_diff_ms = timestamp - self.last_timestamp
            else:
                # Rollover occurred
                time_diff_ms = (0xFFFFFFFF - self.last_timestamp) + timestamp + 1
        
        self.last_timestamp = timestamp
        
        message.add_field(ParsedField(
            name="Timestamp",
            value=timestamp,
            raw_value=timestamp,
            bit_range=(16, 47),
            description=f"32-bit timestamp counter (diff: {time_diff_ms if time_diff_ms else 'N/A'}ms)",
            field_type=FieldType.INTEGER,
            validation_status=ValidationStatus.VALID,
            min_value=0,
            max_value=0xFFFFFFFF
        ))
        
        # Add timestamp difference as separate field if available
        if time_diff_ms is not None:
            message.add_field(ParsedField(
                name="Time Delta",
                value=time_diff_ms,
                unit="ms",
                raw_value=time_diff_ms,
                bit_range=(16, 47),  # Same range as timestamp
                description="Time since last message",
                field_type=FieldType.INTEGER,
                validation_status=ValidationStatus.VALID if time_diff_ms < 1000 else ValidationStatus.WARNING,
                validation_message=f"Long gap: {time_diff_ms}ms" if time_diff_ms >= 1000 else "Normal timing"
            ))
        
        # Parse Reserved byte (Byte 6)
        reserved = data[6]
        message.add_field(ParsedField(
            name="Reserved",
            value=f"0x{reserved:02X}",
            raw_value=reserved,
            bit_range=(48, 55),
            description="Reserved byte (should be 0x00)",
            field_type=FieldType.INTEGER,
            validation_status=ValidationStatus.VALID if reserved == self.RESERVED_VALUE else ValidationStatus.WARNING,
            validation_message="Reserved byte valid" if reserved == self.RESERVED_VALUE else f"Reserved byte non-zero: 0x{reserved:02X}"
        ))
        
        # Parse End Marker (Byte 7)
        end_marker = data[7]
        message.add_field(ParsedField(
            name="End Marker",
            value=f"0x{end_marker:02X}",
            raw_value=end_marker,
            bit_range=(56, 63),
            description="End marker (should be 0xFF)",
            field_type=FieldType.INTEGER,
            validation_status=ValidationStatus.VALID if end_marker == self.END_MARKER else ValidationStatus.ERROR,
            validation_message="Valid end marker" if end_marker == self.END_MARKER else f"Invalid end marker: expected 0xFF, got 0x{end_marker:02X}"
        ))
        
        # Add switch state summary
        self._add_switch_summary(message, active_switches, switch_bitmap)
        
        # Add validation errors
        if signature != self.SIGNATURE:
            message.add_error("Invalid message signature")
        if end_marker != self.END_MARKER:
            message.add_error("Invalid end marker")
        if reserved != self.RESERVED_VALUE:
            message.add_warning("Reserved byte not zero")
        
        return message
    
    def _validate_packet(self, data: bytes, message: ParsedMessage) -> bool:
        """Validate basic packet structure."""
        if len(data) != 8:
            message.add_error(f"Invalid packet length: {len(data)} bytes, expected 8")
            return False
        
        # Quick validation of signature and end marker
        if data[0] != self.SIGNATURE:
            message.add_error(f"Invalid signature: 0x{data[0]:02X}, expected 0x{self.SIGNATURE:02X}")
            return False
            
        if data[7] != self.END_MARKER:
            message.add_error(f"Invalid end marker: 0x{data[7]:02X}, expected 0x{self.END_MARKER:02X}")
            return False
        
        return True
    
    def _add_switch_summary(self, message: ParsedMessage, active_switches: List[str], switch_bitmap: int) -> None:
        """Add human-readable switch state summary."""
        if not active_switches:
            summary = "No switches active"
            state = "IDLE"
        else:
            summary = f"Active: {', '.join(active_switches)}"
            
            # Determine operational state based on active switches
            if "Brake Switch" in active_switches:
                state = "BRAKING"
            elif "Forward Switch" in active_switches and "Reverse Switch" in active_switches:
                state = "CONFLICT"  # Both direction switches active
            elif "Forward Switch" in active_switches:
                state = "FORWARD"
            elif "Reverse Switch" in active_switches:
                state = "REVERSE"
            elif "Accelerator Switch" in active_switches:
                state = "ACCELERATING"
            else:
                state = "AUXILIARY"  # Other switches active
        
        # Add switch count
        active_count = bin(switch_bitmap).count('1')
        message.add_field(ParsedField(
            name="Active Switch Count",
            value=active_count,
            raw_value=active_count,
            bit_range=(8, 15),
            description=f"Number of switches currently active",
            field_type=FieldType.INTEGER,
            validation_status=ValidationStatus.VALID,
            min_value=0,
            max_value=8
        ))
        
        # Add operational state
        message.add_field(ParsedField(
            name="Operational State",
            value=state,
            raw_value=0,  # Derived field
            bit_range=(8, 15),
            description=f"Vehicle operational state: {summary}",
            field_type=FieldType.STRING,
            validation_status=ValidationStatus.ERROR if state == "CONFLICT" else ValidationStatus.VALID,
            validation_message="Direction conflict detected" if state == "CONFLICT" else ""
        ))
    
    def get_description(self) -> str:
        """Return parser description."""
        return "Parser for wiring harness switch state messages (CAN ID 0x500)"
    
    def get_supported_ids(self) -> List[Union[int, Tuple[int, int]]]:
        """Return supported CAN IDs."""
        return [0x500]
    
    def get_stats(self) -> dict:
        """Get parser statistics."""
        return {
            "message_count": self.message_count,
            "last_timestamp": self.last_timestamp
        }
    
    def reset_stats(self) -> None:
        """Reset parser statistics."""
        self.message_count = 0
        self.last_timestamp = None
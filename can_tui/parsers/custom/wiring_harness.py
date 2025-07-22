"""
Wiring Harness CAN Packet Parser for STM32F103 Vehicle Control Unit.

This parser handles the specific 8-byte packet structure for CAN ID 0x410
from the STM32F103 wiring harness controller.
"""

from typing import List, Union, Tuple, Optional
from ..base import ProtocolParser, ParsedMessage, ParsedField, FieldType, ValidationStatus


class WiringHarnessParser(ProtocolParser):
    """
    Parser for STM32F103 Vehicle Control Unit wiring harness messages.
    
    CAN ID: 0x410 (Vehicle Control Unit)
    Device ID: 0x410 (STM32F103 device ID)
    
    8-byte packet structure:
    Byte 0: Control Flags (FWD_SW_IN, REV_SW_UC, ECO_SW_UC, BRAKE_12V_UC)
    Byte 1: Secondary Flags (FOOT_SW_UC)
    Byte 2: Throttle Position (0-100%)
    Byte 3: Brake Pressure (0-100%)
    Byte 4: Sequence Counter (0-255, wraps)
    Byte 5: System Status (CAN Error, System Error)
    Byte 6: CRC8 (polynomial 0x07)
    Byte 7: End marker (0xAA)
    """
    
    def __init__(self):
        super().__init__("STM32F103 Wiring Harness", "1.0")
        self.priority = 1  # Highest priority for specific hardware
        self.last_sequence = None  # Track sequence counter
        self.sequence_errors = 0
        
    def can_parse(self, can_id: int, data: bytes) -> bool:
        """Can parse STM32F103 wiring harness messages."""
        return can_id == 0x410 and len(data) == 8
    
    def parse(self, can_id: int, data: bytes) -> ParsedMessage:
        """Parse STM32F103 wiring harness message."""
        message = ParsedMessage(
            parser_name=self.get_name(),
            parser_version=self.get_version(),
            message_type="Vehicle Control Unit",
            message_name="STM32F103 Wiring Harness",
            confidence=1.0
        )
        
        # Validate packet structure first
        if not self._validate_packet(data, message):
            return message
        
        # Parse Control Flags (Byte 0)
        control_flags = data[0]
        
        # Bit 0: FWD_SW_IN
        fwd_switch = bool(control_flags & 0x01)
        message.add_field(ParsedField(
            name="Forward Switch",
            value=fwd_switch,
            raw_value=int(fwd_switch),
            bit_range=(0, 0),
            description="Forward direction switch input",
            field_type=FieldType.BOOLEAN,
            validation_status=ValidationStatus.VALID
        ))
        
        # Bit 1: REV_SW_UC
        rev_switch = bool(control_flags & 0x02)
        message.add_field(ParsedField(
            name="Reverse Switch",
            value=rev_switch,
            raw_value=int(rev_switch),
            bit_range=(1, 1),
            description="Reverse direction switch (under control)",
            field_type=FieldType.BOOLEAN,
            validation_status=ValidationStatus.VALID
        ))
        
        # Bit 2: ECO_SW_UC
        eco_switch = bool(control_flags & 0x04)
        message.add_field(ParsedField(
            name="Eco Switch",
            value=eco_switch,
            raw_value=int(eco_switch),
            bit_range=(2, 2),
            description="Economy mode switch (under control)",
            field_type=FieldType.BOOLEAN,
            validation_status=ValidationStatus.VALID
        ))
        
        # Bit 3: BRAKE_12V_UC
        brake_12v = bool(control_flags & 0x08)
        message.add_field(ParsedField(
            name="Brake 12V",
            value=brake_12v,
            raw_value=int(brake_12v),
            bit_range=(3, 3),
            description="12V brake signal (under control)",
            field_type=FieldType.BOOLEAN,
            validation_status=ValidationStatus.VALID
        ))
        
        # Bits 4-7: Reserved
        reserved_bits = (control_flags & 0xF0) >> 4
        if reserved_bits != 0:
            message.add_field(ParsedField(
                name="Control Reserved",
                value=reserved_bits,
                raw_value=reserved_bits,
                bit_range=(4, 7),
                description="Reserved bits (should be 0)",
                field_type=FieldType.INTEGER,
                validation_status=ValidationStatus.WARNING,
                validation_message=f"Reserved bits not zero: 0x{reserved_bits:X}"
            ))
        
        # Parse Secondary Flags (Byte 1)
        secondary_flags = data[1]
        
        # Bit 0: FOOT_SW_UC
        foot_switch = bool(secondary_flags & 0x01)
        message.add_field(ParsedField(
            name="Foot Switch",
            value=foot_switch,
            raw_value=int(foot_switch),
            bit_range=(8, 8),
            description="Foot switch (under control)",
            field_type=FieldType.BOOLEAN,
            validation_status=ValidationStatus.VALID
        ))
        
        # Bits 1-7: Reserved
        reserved_secondary = (secondary_flags & 0xFE) >> 1
        if reserved_secondary != 0:
            message.add_field(ParsedField(
                name="Secondary Reserved",
                value=reserved_secondary,
                raw_value=reserved_secondary,
                bit_range=(9, 15),
                description="Reserved bits (should be 0)",
                field_type=FieldType.INTEGER,
                validation_status=ValidationStatus.WARNING,
                validation_message=f"Reserved bits not zero: 0x{reserved_secondary:02X}"
            ))
        
        # Parse Throttle Position (Byte 2)
        throttle_raw = data[2]
        throttle_percent = min(100.0, throttle_raw)  # Clamp to 100%
        
        message.add_field(ParsedField(
            name="Throttle Position",
            value=throttle_percent,
            unit="%",
            raw_value=throttle_raw,
            bit_range=(16, 23),
            description="Throttle pedal position percentage",
            field_type=FieldType.FLOAT,
            validation_status=ValidationStatus.VALID if throttle_raw <= 100 else ValidationStatus.WARNING,
            validation_message=f"Throttle value {throttle_raw} exceeds 100%" if throttle_raw > 100 else "",
            min_value=0.0,
            max_value=100.0
        ))
        
        # Parse Brake Pressure (Byte 3)
        brake_raw = data[3]
        brake_percent = min(100.0, brake_raw)  # Clamp to 100%
        
        message.add_field(ParsedField(
            name="Brake Pressure",
            value=brake_percent,
            unit="%",
            raw_value=brake_raw,
            bit_range=(24, 31),
            description="Brake system pressure percentage",
            field_type=FieldType.FLOAT,
            validation_status=ValidationStatus.VALID if brake_raw <= 100 else ValidationStatus.WARNING,
            validation_message=f"Brake value {brake_raw} exceeds 100%" if brake_raw > 100 else "",
            min_value=0.0,
            max_value=100.0
        ))
        
        # Parse Sequence Counter (Byte 4)
        sequence = data[4]
        sequence_status = self._validate_sequence(sequence)
        
        message.add_field(ParsedField(
            name="Sequence Counter",
            value=sequence,
            raw_value=sequence,
            bit_range=(32, 39),
            description="Packet sequence counter (0-255, wraps)",
            field_type=FieldType.INTEGER,
            validation_status=sequence_status[0],
            validation_message=sequence_status[1],
            min_value=0,
            max_value=255
        ))
        
        # Parse System Status (Byte 5)
        system_status = data[5]
        
        # Bit 7: CAN Error
        can_error = bool(system_status & 0x80)
        message.add_field(ParsedField(
            name="CAN Error",
            value=can_error,
            raw_value=int(can_error),
            bit_range=(47, 47),
            description="CAN bus error flag",
            field_type=FieldType.BOOLEAN,
            validation_status=ValidationStatus.ERROR if can_error else ValidationStatus.VALID,
            validation_message="CAN bus error detected" if can_error else ""
        ))
        
        # Bit 6: System Error
        system_error = bool(system_status & 0x40)
        message.add_field(ParsedField(
            name="System Error",
            value=system_error,
            raw_value=int(system_error),
            bit_range=(46, 46),
            description="System error flag",
            field_type=FieldType.BOOLEAN,
            validation_status=ValidationStatus.ERROR if system_error else ValidationStatus.VALID,
            validation_message="System error detected" if system_error else ""
        ))
        
        # Bits 5-0: Reserved
        status_reserved = system_status & 0x3F
        if status_reserved != 0:
            message.add_field(ParsedField(
                name="Status Reserved",
                value=status_reserved,
                raw_value=status_reserved,
                bit_range=(40, 45),
                description="Reserved status bits (should be 0)",
                field_type=FieldType.INTEGER,
                validation_status=ValidationStatus.WARNING,
                validation_message=f"Reserved status bits not zero: 0x{status_reserved:02X}"
            ))
        
        # Parse CRC8 (Byte 6)
        received_crc = data[6]
        calculated_crc = self._calculate_crc8(data[0:6])
        crc_valid = received_crc == calculated_crc
        
        message.add_field(ParsedField(
            name="CRC8",
            value=f"0x{received_crc:02X}",
            raw_value=received_crc,
            bit_range=(48, 55),
            description=f"CRC8 checksum (calculated: 0x{calculated_crc:02X})",
            field_type=FieldType.INTEGER,
            validation_status=ValidationStatus.VALID if crc_valid else ValidationStatus.ERROR,
            validation_message="CRC8 checksum valid" if crc_valid else f"CRC8 mismatch: got 0x{received_crc:02X}, expected 0x{calculated_crc:02X}"
        ))
        
        # Parse End Marker (Byte 7)
        end_marker = data[7]
        marker_valid = end_marker == 0xAA
        
        message.add_field(ParsedField(
            name="End Marker",
            value=f"0x{end_marker:02X}",
            raw_value=end_marker,
            bit_range=(56, 63),
            description="Packet end marker (should be 0xAA)",
            field_type=FieldType.INTEGER,
            validation_status=ValidationStatus.VALID if marker_valid else ValidationStatus.ERROR,
            validation_message="End marker valid" if marker_valid else f"Invalid end marker: 0x{end_marker:02X}, expected 0xAA"
        ))
        
        # Add vehicle state summary
        self._add_vehicle_state_summary(message, fwd_switch, rev_switch, eco_switch, 
                                       brake_12v, foot_switch, throttle_percent, brake_percent)
        
        # Add any system-level errors
        if can_error:
            message.add_error("CAN bus error detected")
        if system_error:
            message.add_error("System error detected")
        if not crc_valid:
            message.add_error("CRC8 checksum validation failed")
        if not marker_valid:
            message.add_error("Invalid end marker")
        
        return message
    
    def _validate_packet(self, data: bytes, message: ParsedMessage) -> bool:
        """Validate basic packet structure."""
        if len(data) != 8:
            message.add_error(f"Invalid packet length: {len(data)} bytes, expected 8")
            return False
        
        # Check end marker first for quick validation
        if data[7] != 0xAA:
            message.add_warning(f"Invalid end marker: 0x{data[7]:02X}, expected 0xAA")
        
        return True
    
    def _validate_sequence(self, sequence: int) -> Tuple[ValidationStatus, str]:
        """Validate sequence counter for continuity."""
        if self.last_sequence is None:
            self.last_sequence = sequence
            return ValidationStatus.VALID, "Initial sequence"
        
        expected = (self.last_sequence + 1) % 256
        if sequence == expected:
            self.last_sequence = sequence
            return ValidationStatus.VALID, "Sequence valid"
        else:
            self.sequence_errors += 1
            gap = (sequence - expected) % 256
            self.last_sequence = sequence
            return ValidationStatus.WARNING, f"Sequence gap: expected {expected}, got {sequence} (gap: {gap})"
    
    def _calculate_crc8(self, data: bytes) -> int:
        """Calculate CRC8 with polynomial 0x07."""
        crc = 0x00
        polynomial = 0x07
        
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc = crc << 1
                crc &= 0xFF
        
        return crc
    
    def _add_vehicle_state_summary(self, message: ParsedMessage, fwd_switch: bool, rev_switch: bool, 
                                  eco_switch: bool, brake_12v: bool, foot_switch: bool, 
                                  throttle_percent: float, brake_percent: float) -> None:
        """Add a human-readable vehicle state summary."""
        # Determine direction
        if fwd_switch and not rev_switch:
            direction = "FORWARD"
        elif rev_switch and not fwd_switch:
            direction = "REVERSE"
        elif fwd_switch and rev_switch:
            direction = "CONFLICT"
        else:
            direction = "NEUTRAL"
        
        # Determine mode
        mode = "ECO" if eco_switch else "NORMAL"
        
        # Determine overall state
        if brake_percent > 10 or brake_12v:
            state = "BRAKING"
        elif throttle_percent > 5:
            state = "ACCELERATING"
        elif foot_switch:
            state = "READY"
        else:
            state = "IDLE"
        
        # Add summary fields
        direction_raw = int(fwd_switch) | (int(rev_switch) << 1)
        message.add_field(ParsedField(
            name="Direction",
            value=direction_raw,  # Use raw value for enum validation
            raw_value=direction_raw,
            bit_range=(0, 1),
            description=f"Vehicle direction setting ({direction})",
            field_type=FieldType.ENUM,
            enum_values={
                0: "NEUTRAL",
                1: "FORWARD", 
                2: "REVERSE",
                3: "CONFLICT"
            },
            validation_status=ValidationStatus.ERROR if direction == "CONFLICT" else ValidationStatus.VALID,
            validation_message="Forward and reverse switches both active" if direction == "CONFLICT" else ""
        ))
        
        message.add_field(ParsedField(
            name="Drive Mode",
            value=int(eco_switch),  # Use raw value for enum validation
            raw_value=int(eco_switch),
            bit_range=(2, 2),
            description=f"Vehicle drive mode ({mode})",
            field_type=FieldType.ENUM,
            enum_values={0: "NORMAL", 1: "ECO"},
            validation_status=ValidationStatus.VALID
        ))
        
        message.add_field(ParsedField(
            name="Vehicle State",
            value=state,
            raw_value=0,  # Derived field
            bit_range=(0, 63),
            description="Overall vehicle operational state",
            field_type=FieldType.STRING,
            validation_status=ValidationStatus.VALID
        ))
    
    def get_description(self) -> str:
        """Return parser description."""
        return "Parser for STM32F103 Vehicle Control Unit wiring harness messages (CAN ID 0x410)"
    
    def get_supported_ids(self) -> List[Union[int, Tuple[int, int]]]:
        """Return supported CAN IDs."""
        return [0x410]  # Only supports CAN ID 0x410
    
    def get_stats(self) -> dict:
        """Get parser statistics."""
        return {
            "sequence_errors": self.sequence_errors,
            "last_sequence": self.last_sequence
        }
    
    def reset_stats(self) -> None:
        """Reset parser statistics."""
        self.sequence_errors = 0
        self.last_sequence = None
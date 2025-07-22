"""
Example sensor parser for golf cart brake system.
Simple example showing how to parse custom CAN messages.
"""

from typing import List, Union, Tuple
from ..base import ProtocolParser, ParsedMessage, ParsedField, FieldType, ValidationStatus


class ExampleSensorParser(ProtocolParser):
    """
    Example parser for golf cart brake sensor messages.
    
    Message format for CAN ID 0x100:
    - Byte 0: Sensor ID (0x22 = brake sensor)
    - Byte 1: Brake status (0x00 = released, 0x01 = pressed)
    - Byte 2: Reserved/unused
    """
    
    def __init__(self):
        super().__init__("Golf Cart Brake Sensor", "1.0")
        self.priority = 2  # High priority for specific messages
    
    def can_parse(self, can_id: int, data: bytes) -> bool:
        """Can parse golf cart brake messages."""
        # Only handle CAN ID 0x100 with at least 2 bytes of data
        return can_id == 0x100 and len(data) >= 2
    
    def parse(self, can_id: int, data: bytes) -> ParsedMessage:
        """Parse golf cart brake sensor message."""
        message = ParsedMessage(
            parser_name=self.get_name(),
            parser_version=self.get_version(),
            message_type="Golf Cart Sensor",
            message_name="Brake Status",
            confidence=1.0
        )
        
        # Parse sensor ID (first byte)
        sensor_id = data[0]
        is_brake_sensor = sensor_id == 0x22
        
        message.add_field(ParsedField(
            name="Sensor ID",
            value=sensor_id,
            raw_value=sensor_id,
            bit_range=(0, 7),
            description="Sensor type identifier",
            field_type=FieldType.ENUM,
            enum_values={
                0x22: "Brake Sensor",
                0x23: "Throttle Sensor", 
                0x24: "Steering Sensor"
            },
            validation_status=ValidationStatus.VALID if is_brake_sensor else ValidationStatus.WARNING,
            validation_message="Expected brake sensor (0x22)" if not is_brake_sensor else ""
        ))
        
        # Parse brake status (second byte)
        brake_status = data[1]
        brake_pressed = brake_status == 0x01
        
        message.add_field(ParsedField(
            name="Brake Status",
            value=brake_pressed,
            raw_value=brake_status,
            bit_range=(8, 15),
            description="Brake pedal position",
            field_type=FieldType.BOOLEAN,
            validation_status=ValidationStatus.VALID if brake_status in [0x00, 0x01] else ValidationStatus.ERROR,
            validation_message="Invalid brake status value" if brake_status not in [0x00, 0x01] else ""
        ))
        
        # Add human-readable brake state
        message.add_field(ParsedField(
            name="Brake State",
            value="PRESSED" if brake_pressed else "RELEASED",
            raw_value=brake_status,
            bit_range=(8, 15),
            description="Current brake pedal state",
            field_type=FieldType.STRING,
            validation_status=ValidationStatus.VALID
        ))
        
        # Parse reserved byte if present
        if len(data) >= 3:
            reserved = data[2]
            message.add_field(ParsedField(
                name="Reserved",
                value=reserved,
                raw_value=reserved,
                bit_range=(16, 23),
                description="Reserved byte (should be 0x00)",
                field_type=FieldType.INTEGER,
                validation_status=ValidationStatus.VALID if reserved == 0x00 else ValidationStatus.WARNING,
                validation_message="Reserved byte should be 0x00" if reserved != 0x00 else ""
            ))
        
        # Add any additional validation
        if not is_brake_sensor:
            message.add_warning("Message may not be from brake sensor")
        
        if brake_status not in [0x00, 0x01]:
            message.add_error(f"Invalid brake status: 0x{brake_status:02X}")
        
        return message
    
    def get_description(self) -> str:
        """Return parser description."""
        return "Parser for golf cart brake sensor messages (CAN ID 0x100)"
    
    def get_supported_ids(self) -> List[Union[int, Tuple[int, int]]]:
        """Return supported CAN IDs."""
        return [0x100]  # Only supports CAN ID 0x100


class GolfCartThrottleParser(ProtocolParser):
    """
    Example parser for golf cart throttle sensor messages.
    
    Message format for CAN ID 0x101:
    - Byte 0: Sensor ID (0x23 = throttle sensor)
    - Byte 1: Throttle position (0x00-0xFF = 0-100%)
    - Byte 2: Reserved/unused
    """
    
    def __init__(self):
        super().__init__("Golf Cart Throttle Sensor", "1.0")
        self.priority = 2  # High priority for specific messages
    
    def can_parse(self, can_id: int, data: bytes) -> bool:
        """Can parse golf cart throttle messages."""
        return can_id == 0x101 and len(data) >= 2
    
    def parse(self, can_id: int, data: bytes) -> ParsedMessage:
        """Parse golf cart throttle sensor message."""
        message = ParsedMessage(
            parser_name=self.get_name(),
            parser_version=self.get_version(),
            message_type="Golf Cart Sensor",
            message_name="Throttle Position",
            confidence=1.0
        )
        
        # Parse sensor ID (first byte)
        sensor_id = data[0]
        is_throttle_sensor = sensor_id == 0x23
        
        message.add_field(ParsedField(
            name="Sensor ID",
            value=sensor_id,
            raw_value=sensor_id,
            bit_range=(0, 7),
            description="Sensor type identifier",
            field_type=FieldType.ENUM,
            enum_values={
                0x22: "Brake Sensor",
                0x23: "Throttle Sensor", 
                0x24: "Steering Sensor"
            },
            validation_status=ValidationStatus.VALID if is_throttle_sensor else ValidationStatus.WARNING,
            validation_message="Expected throttle sensor (0x23)" if not is_throttle_sensor else ""
        ))
        
        # Parse throttle position (second byte)
        throttle_raw = data[1]
        throttle_percent = (throttle_raw / 255.0) * 100.0
        
        message.add_field(ParsedField(
            name="Throttle Position",
            value=round(throttle_percent, 1),
            unit="%",
            raw_value=throttle_raw,
            bit_range=(8, 15),
            description="Throttle pedal position",
            field_type=FieldType.FLOAT,
            validation_status=ValidationStatus.VALID,
            min_value=0.0,
            max_value=100.0,
            scale_factor=100.0/255.0
        ))
        
        # Add throttle state description
        if throttle_percent == 0:
            state = "IDLE"
        elif throttle_percent < 25:
            state = "LOW"
        elif throttle_percent < 75:
            state = "MEDIUM"
        else:
            state = "HIGH"
        
        message.add_field(ParsedField(
            name="Throttle State",
            value=state,
            raw_value=throttle_raw,
            bit_range=(8, 15),
            description="Throttle position category",
            field_type=FieldType.STRING,
            validation_status=ValidationStatus.VALID
        ))
        
        return message
    
    def get_description(self) -> str:
        """Return parser description."""
        return "Parser for golf cart throttle sensor messages (CAN ID 0x101)"
    
    def get_supported_ids(self) -> List[Union[int, Tuple[int, int]]]:
        """Return supported CAN IDs."""
        return [0x101]  # Only supports CAN ID 0x101
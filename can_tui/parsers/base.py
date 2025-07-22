"""
Base classes and data structures for protocol parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple, Union
from enum import Enum


class FieldType(Enum):
    """Types of parsed fields."""
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"
    ENUM = "enum"
    BITMASK = "bitmask"
    BYTES = "bytes"


class ValidationStatus(Enum):
    """Validation status for parsed fields."""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ParsedField:
    """Represents a single parsed field from a CAN message."""
    name: str                           # Field name (e.g., "Brake Pressure")
    value: Any                          # Parsed value (e.g., 45.2)
    unit: str = ""                      # Unit (e.g., "PSI", "RPM", "°C")
    raw_value: Union[int, bytes] = 0    # Raw binary value
    bit_range: Tuple[int, int] = (0, 0) # (start_bit, end_bit) for highlighting
    description: str = ""               # Field description
    field_type: FieldType = FieldType.INTEGER
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    validation_message: str = ""        # Validation details
    enum_values: Optional[dict] = None  # For enum fields: {value: description}
    min_value: Optional[float] = None   # Minimum valid value
    max_value: Optional[float] = None   # Maximum valid value
    scale_factor: float = 1.0          # Scaling factor applied to raw value
    offset: float = 0.0                # Offset applied to raw value
    
    def __post_init__(self):
        """Validate field after initialization."""
        if self.enum_values and self.field_type == FieldType.ENUM:
            # Validate enum value
            if self.value in self.enum_values:
                self.validation_status = ValidationStatus.VALID
            else:
                self.validation_status = ValidationStatus.ERROR
                self.validation_message = f"Invalid enum value: {self.value}"
        
        elif self.field_type in [FieldType.INTEGER, FieldType.FLOAT]:
            # Validate numeric ranges
            if self.min_value is not None and self.value < self.min_value:
                self.validation_status = ValidationStatus.ERROR
                self.validation_message = f"Value {self.value} below minimum {self.min_value}"
            elif self.max_value is not None and self.value > self.max_value:
                self.validation_status = ValidationStatus.ERROR  
                self.validation_message = f"Value {self.value} above maximum {self.max_value}"
            else:
                self.validation_status = ValidationStatus.VALID
    
    def format_value(self) -> str:
        """Format the value for display."""
        if self.field_type == FieldType.BOOLEAN:
            return "ON" if self.value else "OFF"
        elif self.field_type == FieldType.ENUM and self.enum_values:
            return self.enum_values.get(self.value, f"Unknown ({self.value})")
        elif self.field_type == FieldType.FLOAT:
            return f"{self.value:.2f}"
        elif self.field_type == FieldType.BYTES:
            if isinstance(self.value, bytes):
                return " ".join(f"{b:02X}" for b in self.value)
            return str(self.value)
        else:
            return str(self.value)
    
    def get_status_symbol(self) -> str:
        """Get status symbol for display."""
        return {
            ValidationStatus.VALID: "✓",
            ValidationStatus.WARNING: "⚠",
            ValidationStatus.ERROR: "❌",
            ValidationStatus.UNKNOWN: "?",
        }[self.validation_status]
    
    def get_status_color(self) -> str:
        """Get color for status display."""
        return {
            ValidationStatus.VALID: "green",
            ValidationStatus.WARNING: "yellow", 
            ValidationStatus.ERROR: "red",
            ValidationStatus.UNKNOWN: "dim",
        }[self.validation_status]


@dataclass
class ParsedMessage:
    """Represents a fully parsed CAN message."""
    parser_name: str                    # Name of parser used
    parser_version: str = "1.0"         # Parser version
    message_type: str = "Unknown"       # Type of message (e.g., "Sensor Data")
    message_name: str = ""              # Specific message name
    fields: List[ParsedField] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)     # Parse errors/warnings
    warnings: List[str] = field(default_factory=list)   # Parse warnings
    confidence: float = 1.0             # Parse confidence (0.0-1.0)
    protocol_info: dict = field(default_factory=dict)   # Protocol-specific info
    timestamp: Optional[float] = None   # Parse timestamp
    
    def add_field(self, field: ParsedField) -> None:
        """Add a parsed field to the message."""
        self.fields.append(field)
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        # Reduce confidence when errors occur
        self.confidence = max(0.0, self.confidence - 0.1)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        # Slightly reduce confidence for warnings
        self.confidence = max(0.0, self.confidence - 0.05)
    
    def is_valid(self) -> bool:
        """Check if the message parsed successfully."""
        return len(self.errors) == 0 and self.confidence > 0.5
    
    def get_field_by_name(self, name: str) -> Optional[ParsedField]:
        """Get a field by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None
    
    def get_fields_by_bit_range(self, start_bit: int, end_bit: int) -> List[ParsedField]:
        """Get fields that overlap with the given bit range."""
        overlapping_fields = []
        for field in self.fields:
            field_start, field_end = field.bit_range
            if not (field_end < start_bit or field_start > end_bit):
                overlapping_fields.append(field)
        return overlapping_fields


class ProtocolParser(ABC):
    """Abstract base class for all protocol parsers."""
    
    def __init__(self, name: str, version: str = "1.0"):
        self.name = name
        self.version = version
        self.enabled = True
        self.priority = 5  # Default priority (1=highest, 10=lowest)
        self.config = {}   # Parser-specific configuration
    
    @abstractmethod
    def can_parse(self, can_id: int, data: bytes) -> bool:
        """
        Check if this parser can handle the given CAN message.
        
        Args:
            can_id: CAN message ID
            data: Raw message data bytes
            
        Returns:
            True if this parser can parse the message, False otherwise
        """
        pass
    
    @abstractmethod
    def parse(self, can_id: int, data: bytes) -> ParsedMessage:
        """
        Parse the CAN message and return structured data.
        
        Args:
            can_id: CAN message ID
            data: Raw message data bytes
            
        Returns:
            ParsedMessage containing the parsed fields and metadata
        """
        pass
    
    def get_name(self) -> str:
        """Return parser name for UI display."""
        return self.name
    
    def get_version(self) -> str:
        """Return parser version."""
        return self.version
    
    def get_full_name(self) -> str:
        """Return full parser name with version."""
        return f"{self.name} v{self.version}"
    
    @abstractmethod
    def get_description(self) -> str:
        """Return parser description for UI display."""
        pass
    
    def get_supported_ids(self) -> List[Union[int, Tuple[int, int]]]:
        """
        Return list of supported CAN IDs or ID ranges.
        
        Returns:
            List of CAN IDs (int) or ID ranges (tuple of start, end)
        """
        return []
    
    def configure(self, config: dict) -> None:
        """Configure the parser with custom settings."""
        self.config.update(config)
    
    def get_config(self) -> dict:
        """Get current parser configuration."""
        return self.config.copy()
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the parser."""
        self.enabled = enabled
    
    def is_enabled(self) -> bool:
        """Check if parser is enabled."""
        return self.enabled
    
    def set_priority(self, priority: int) -> None:
        """Set parser priority (1=highest, 10=lowest)."""
        self.priority = max(1, min(10, priority))
    
    def get_priority(self) -> int:
        """Get parser priority."""
        return self.priority
    
    def validate_data(self, data: bytes, min_length: int = 0) -> bool:
        """
        Validate basic data requirements.
        
        Args:
            data: Raw message data
            min_length: Minimum required data length
            
        Returns:
            True if data is valid, False otherwise
        """
        return len(data) >= min_length
    
    def extract_bits(self, data: bytes, start_bit: int, num_bits: int) -> int:
        """
        Extract bits from data bytes.
        
        Args:
            data: Raw data bytes
            start_bit: Starting bit position (0-based)
            num_bits: Number of bits to extract
            
        Returns:
            Extracted value as integer
        """
        if start_bit + num_bits > len(data) * 8:
            raise ValueError(f"Bit range {start_bit}:{start_bit+num_bits} exceeds data length")
        
        # Convert bytes to bit array
        bit_array = []
        for byte in data:
            for i in range(8):
                bit_array.append((byte >> (7 - i)) & 1)
        
        # Extract requested bits
        result = 0
        for i in range(num_bits):
            if start_bit + i < len(bit_array):
                result = (result << 1) | bit_array[start_bit + i]
        
        return result
    
    def scale_value(self, raw_value: int, scale: float, offset: float = 0.0) -> float:
        """
        Scale a raw value with factor and offset.
        
        Args:
            raw_value: Raw integer value
            scale: Scale factor
            offset: Offset value
            
        Returns:
            Scaled value
        """
        return (raw_value * scale) + offset
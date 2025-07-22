"""
RPICAN Protocol Parsers

This module provides a modular system for parsing and interpreting CAN message payloads
according to different protocols. It includes:

- Abstract base classes for protocol parsers
- Data structures for parsed messages and fields
- Registry system for managing parsers
- Built-in parsers for common protocols
- Support for custom user-defined parsers
"""

from .base import ProtocolParser, ParsedMessage, ParsedField, FieldType, ValidationStatus
from .registry import ParserRegistry

# Import built-in parsers
from .builtin.raw import RawDataParser

# Import custom parsers
from .custom.example_sensor import ExampleSensorParser, GolfCartThrottleParser
from .custom.wiring_harness import WiringHarnessParser
from .custom.wiring_harness_switch import WiringHarnessSwitchParser

__all__ = [
    "ProtocolParser",
    "ParsedMessage", 
    "ParsedField",
    "FieldType",
    "ValidationStatus",
    "ParserRegistry",
    "RawDataParser",
    "ExampleSensorParser",
    "GolfCartThrottleParser",
    "WiringHarnessParser",
    "WiringHarnessSwitchParser",
]
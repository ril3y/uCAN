"""
Custom user-defined protocol parsers.

This module contains custom parsers for specific applications:
- Example sensor parser (template)
- STM32F103 wiring harness parser
- User-defined protocol parsers
"""

from .example_sensor import ExampleSensorParser, GolfCartThrottleParser
from .wiring_harness import WiringHarnessParser

__all__ = [
    "ExampleSensorParser",
    "GolfCartThrottleParser", 
    "WiringHarnessParser",
]
"""
Built-in protocol parsers.

This module contains parsers for common CAN protocols:
- Raw data parser (default fallback)
- J1939 automotive protocol
- OBD-II diagnostic protocol
"""

from .raw import RawDataParser

__all__ = [
    "RawDataParser",
]
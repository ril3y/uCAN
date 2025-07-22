"""
CAN Bridge TUI - Terminal User Interface for USB-to-CAN Bridge

A modern, feature-rich terminal interface for monitoring and controlling
the Raspberry Pi Pico CAN bridge device.
"""

__version__ = "1.0.0"
__author__ = "CAN Bridge TUI Team"
__description__ = "Terminal User Interface for USB-to-CAN Bridge"

from .app import CANBridgeApp, run_app
from .models.can_message import CANMessage, MessageType, MessageFilter, MessageStats
from .services.serial_service import SerialService

__all__ = [
    "CANBridgeApp",
    "run_app", 
    "CANMessage",
    "MessageType",
    "MessageFilter",
    "MessageStats",
    "SerialService"
]
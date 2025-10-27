"""
uCAN Firmware Test Suite

This package contains comprehensive tests for the uCAN firmware protocol v2.0.

Test modules:
- test_action_definitions.py: Validates action definition format and schema
- test_rule_management.py: Tests rule add/delete/edit/enable/disable commands
- test_can_data_extraction.py: Validates parameter extraction from CAN data

Usage:
    pytest tests/ -v --port COM21
    pytest tests/test_action_definitions.py -v --port /dev/ttyACM0
"""

__version__ = "2.0.0"

"""
Unit tests for uCAN firmware protocol.

This package contains hardware-independent unit tests that validate protocol
parsing, command validation, and message formatting without requiring physical
hardware.

Test modules:
    - test_protocol_parsing: Tests for parsing messages FROM the device
    - test_command_validation: Tests for validating commands TO the device
    - test_message_formatting: Tests for formatting protocol messages

Helper modules:
    - protocol_helpers: Protocol parsing and validation functions
"""

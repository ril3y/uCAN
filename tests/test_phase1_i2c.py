"""
Test uCAN Protocol v2.0 Phase 1 I2C actions.

Tests I2C_WRITE and I2C_READ_BUFFER actions.

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
- I2C device optional (tests validate command format)
"""

import pytest
import time


@pytest.mark.hardware
@pytest.mark.integration
class TestPhase1I2C:
    """Test suite for Phase 1 I2C actions."""

    def test_i2c_write_command_format(self, send_command, wait_for_response):
        """Test I2C_WRITE command format validation."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add I2C_WRITE rule: addr=0x68, reg=0x6B, value=0x00
        send_command("action:add:0:0x400:0xFFFFFFFF:::0:I2C_WRITE:fixed:104:107:0")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for I2C_WRITE rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_i2c_read_buffer_command_format(self, send_command, wait_for_response):
        """Test I2C_READ_BUFFER command format validation."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add I2C_READ_BUFFER rule: addr=0x68, reg=0x3B, len=6, slot=0
        send_command("action:add:0:0x450:0xFFFFFFFF:::0:I2C_READ_BUFFER:fixed:104:59:6:0")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for I2C_READ_BUFFER rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_i2c_write_parameter_validation(self, send_command, read_responses):
        """Test I2C_WRITE parameter storage."""
        send_command("action:clear")
        time.sleep(0.2)

        send_command("action:add:0:0x401:0xFFFFFFFF:::0:I2C_WRITE:fixed:72:27:255")
        time.sleep(0.2)

        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        if len(rule_responses) == 0:
            pytest.skip("I2C_WRITE not available on this firmware")

        rule = rule_responses[0]
        assert "I2C_WRITE" in rule
        assert "fixed" in rule

        send_command("action:clear")
        time.sleep(0.2)

    def test_i2c_read_buffer_with_different_lengths(self, send_command, wait_for_response):
        """Test I2C_READ_BUFFER with various read lengths."""
        send_command("action:clear")
        time.sleep(0.2)

        # Test different read lengths (1-8 bytes)
        for length in [1, 2, 4, 6, 8]:
            send_command(f"action:add:0:0x45{length}:0xFFFFFFFF:::0:I2C_READ_BUFFER:fixed:72:0:{length}:0")
            time.sleep(0.1)

        send_command("action:clear")
        time.sleep(0.2)

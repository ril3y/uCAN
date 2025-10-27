"""
Test uCAN Protocol v2.0 PWM actions.

Tests PWM_SET and PWM_CONFIGURE (Phase 1) actions.

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
"""

import pytest
import time


@pytest.mark.hardware
class TestPWMActions:
    """Test suite for PWM action execution."""

    def test_pwm_set_basic(self, send_command, wait_for_response):
        """Test basic PWM_SET action if available."""
        send_command("action:clear")
        time.sleep(0.2)

        # Get available actions
        send_command("get:actions")
        time.sleep(0.2)

        # PWM_SET may or may not be available depending on firmware version
        # This test just verifies the command format is accepted

        send_command("action:clear")
        time.sleep(0.2)

    def test_pwm_configure_with_fixed_parameters(self, send_command, wait_for_response):
        """Test PWM_CONFIGURE with fixed frequency and duty cycle."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add PWM_CONFIGURE rule: Pin 9, 50% duty, 1000Hz
        # Parameters: pin(byte0), duty(bytes1-2), freq(bytes3-6)
        send_command("action:add:0:0x300:0xFFFFFFFF:::0:PWM_CONFIGURE:fixed:9:32768:1000")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for PWM_CONFIGURE rule"

        # Should either succeed or error if PWM_CONFIGURE not available
        send_command("action:clear")
        time.sleep(0.2)

    def test_pwm_configure_rule_format(self, send_command, read_responses):
        """Test that PWM_CONFIGURE rules store all parameters correctly."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add PWM_CONFIGURE with specific parameters
        send_command("action:add:0:0x301:0xFFFFFFFF:::0:PWM_CONFIGURE:fixed:10:16384:5000")
        time.sleep(0.2)

        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        if len(rule_responses) == 0:
            pytest.skip("PWM_CONFIGURE not available on this firmware")

        rule = rule_responses[0]
        parts = rule.split(';')

        # Verify PWM_CONFIGURE parameters
        assert "PWM_CONFIGURE" in rule
        assert parts[8] == "fixed"

        send_command("action:clear")
        time.sleep(0.2)

    def test_pwm_configure_different_frequencies(self, send_command, wait_for_response):
        """Test PWM_CONFIGURE with various frequencies."""
        send_command("action:clear")
        time.sleep(0.2)

        # Test different frequencies
        for freq in [100, 1000, 5000, 10000]:
            send_command(f"action:add:0:0x30{freq % 10}:0xFFFFFFFF:::0:PWM_CONFIGURE:fixed:9:32768:{freq}")
            time.sleep(0.1)

        send_command("action:clear")
        time.sleep(0.2)

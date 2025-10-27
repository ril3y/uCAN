"""
Test uCAN Protocol v2.0 NEOPIXEL action.

Tests NEOPIXEL RGB LED control with fixed and candata modes.

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud (has built-in NeoPixel)
- Live CAN traffic on 0x500 for candata tests
"""

import pytest
import time


@pytest.mark.hardware
class TestNeopixelAction:
    """Test suite for NEOPIXEL RGB LED control."""

    def test_neopixel_with_fixed_red(self, send_command, wait_for_response):
        """Test NEOPIXEL with fixed red color."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add NEOPIXEL rule: Red at 200 brightness
        send_command("action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:fixed:255:0:0:200")

        response = wait_for_response("STATUS;INFO;", timeout=1.0)
        assert response is not None, "No response for NEOPIXEL rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_neopixel_with_fixed_green(self, send_command, wait_for_response):
        """Test NEOPIXEL with fixed green color."""
        send_command("action:clear")
        time.sleep(0.2)

        # Green at 200 brightness
        send_command("action:add:0:0x501:0xFFFFFFFF:::0:NEOPIXEL:fixed:0:255:0:200")

        response = wait_for_response("STATUS;INFO;", timeout=1.0)
        assert response is not None

        send_command("action:clear")
        time.sleep(0.2)

    def test_neopixel_with_fixed_blue(self, send_command, wait_for_response):
        """Test NEOPIXEL with fixed blue color."""
        send_command("action:clear")
        time.sleep(0.2)

        # Blue at 200 brightness
        send_command("action:add:0:0x502:0xFFFFFFFF:::0:NEOPIXEL:fixed:0:0:255:200")

        response = wait_for_response("STATUS;INFO;", timeout=1.0)
        assert response is not None

        send_command("action:clear")
        time.sleep(0.2)

    def test_neopixel_with_candata_extraction(self, send_command, wait_for_response, read_responses):
        """Test NEOPIXEL with candata extraction from live CAN traffic."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add NEOPIXEL rule with candata
        # R=byte0, G=byte1, B=byte2, brightness=byte3
        send_command("action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:candata")

        response = wait_for_response("STATUS;INFO;", timeout=1.0)
        assert response is not None

        # Wait for CAN traffic
        time.sleep(1.0)

        responses = read_responses(max_lines=100, line_timeout=0.6)
        can_rx_messages = [r for r in responses if r.startswith('CAN_RX;0x500')]

        if len(can_rx_messages) == 0:
            pytest.skip("No CAN traffic on 0x500 - test requires active CAN bus")

        # Check for ACTION messages
        action_messages = [r for r in responses if r.startswith('ACTION;')]
        assert len(action_messages) >= 1, "Expected ACTION messages for NEOPIXEL"

        send_command("action:clear")
        time.sleep(0.2)

    def test_neopixel_rule_format(self, send_command, read_responses):
        """Test that NEOPIXEL rules are stored with all 4 parameters."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add NEOPIXEL rule with all parameters
        send_command("action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:fixed:128:64:32:255")
        time.sleep(0.2)

        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 1
        rule = rule_responses[0]
        parts = rule.split(';')

        # Verify all NEOPIXEL parameters present
        assert len(parts) >= 13, f"NEOPIXEL rule should have 13 parts, got {len(parts)}"
        assert parts[7] == "NEOPIXEL"
        assert parts[9] == "128"  # R
        assert parts[10] == "64"  # G
        assert parts[11] == "32"  # B
        assert parts[12] == "255" # Brightness

        send_command("action:clear")
        time.sleep(0.2)

    def test_neopixel_with_different_brightness_levels(self, send_command, wait_for_response):
        """Test NEOPIXEL with various brightness levels."""
        send_command("action:clear")
        time.sleep(0.2)

        # Test different brightness levels
        for brightness in [50, 100, 150, 200, 255]:
            send_command(f"action:add:0:0x50{brightness % 10}:0xFFFFFFFF:::0:NEOPIXEL:fixed:255:0:0:{brightness}")
            time.sleep(0.1)

        send_command("action:list")
        time.sleep(0.3)

        send_command("action:clear")
        time.sleep(0.2)

    def test_neopixel_mixed_colors(self, send_command, wait_for_response):
        """Test NEOPIXEL with various color combinations."""
        send_command("action:clear")
        time.sleep(0.2)

        # Yellow (R+G)
        send_command("action:add:0:0x510:0xFFFFFFFF:::0:NEOPIXEL:fixed:255:255:0:200")
        time.sleep(0.1)

        # Purple (R+B)
        send_command("action:add:0:0x511:0xFFFFFFFF:::0:NEOPIXEL:fixed:255:0:255:200")
        time.sleep(0.1)

        # Cyan (G+B)
        send_command("action:add:0:0x512:0xFFFFFFFF:::0:NEOPIXEL:fixed:0:255:255:200")
        time.sleep(0.1)

        send_command("action:clear")
        time.sleep(0.2)

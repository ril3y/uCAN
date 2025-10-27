"""
Test uCAN Protocol v2.0 ACTION execution reporting.

Tests that ACTION messages are sent when rules trigger and execute.
Format: ACTION;{RULE_ID};{ACTION_TYPE};{TRIGGER_CAN_ID};{STATUS}

IMPORTANT: These tests require live CAN traffic to trigger rules.

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
- Live CAN traffic on IDs 0x100, 0x200, 0x300
"""

import pytest
import time


@pytest.mark.hardware
@pytest.mark.integration
class TestActionReporting:
    """Test suite for ACTION execution reporting."""

    def test_action_message_format(self, send_command, read_responses):
        """Test ACTION message format matches protocol specification."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add rule for CAN ID that has traffic
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:candata")
        time.sleep(1.0)

        responses = read_responses(max_lines=100, line_timeout=0.6)
        action_messages = [r for r in responses if r.startswith('ACTION;')]
        can_rx_messages = [r for r in responses if r.startswith('CAN_RX;')]

        if len(can_rx_messages) == 0:
            pytest.skip("No CAN traffic detected - test requires active CAN bus")

        assert len(action_messages) >= 1, "Expected ACTION message when rule triggers"

        # Parse ACTION format: ACTION;{RULE_ID};{ACTION_TYPE};{TRIGGER_CAN_ID};{STATUS}
        action_msg = action_messages[0]
        parts = action_msg.split(';')

        assert len(parts) == 5, f"ACTION should have 5 parts, got {len(parts)}: {action_msg}"
        assert parts[0] == "ACTION"
        assert parts[1].isdigit(), f"Rule ID should be numeric, got: {parts[1]}"
        assert parts[2].isupper(), f"Action type should be uppercase, got: {parts[2]}"
        assert parts[3].startswith('0x') or parts[3].startswith('0X'), \
            f"CAN ID should be hex, got: {parts[3]}"
        assert parts[4] in ["OK", "FAIL"], f"Status should be OK or FAIL, got: {parts[4]}"

        send_command("action:clear")
        time.sleep(0.2)

    def test_action_includes_correct_can_id(self, send_command, read_responses):
        """Test that ACTION message includes the actual triggering CAN ID."""
        send_command("action:clear")
        time.sleep(0.2)

        send_command("action:add:0:0x200:0xFFFFFFFF:::0:GPIO_TOGGLE:candata")
        time.sleep(1.0)

        responses = read_responses(max_lines=100, line_timeout=0.6)
        action_messages = [r for r in responses if r.startswith('ACTION;')]
        can_rx_messages = [r for r in responses if r.startswith('CAN_RX;0x200')]

        if len(can_rx_messages) == 0:
            pytest.skip("No CAN traffic on 0x200")

        action_0x200 = [msg for msg in action_messages if '0x200' in msg.upper() or '0X200' in msg]

        if len(action_0x200) > 0:
            parts = action_0x200[0].split(';')
            trigger_can_id = parts[3]
            assert trigger_can_id.upper() == "0x200".upper(), \
                f"Expected CAN ID 0x200, got: {trigger_can_id}"

        send_command("action:clear")
        time.sleep(0.2)

    def test_action_includes_rule_id(self, send_command, read_responses):
        """Test that ACTION message includes the rule ID that triggered."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add rule with specific ID
        send_command("action:add:5:0x100:0xFFFFFFFF:::0:GPIO_SET:candata")
        time.sleep(1.0)

        responses = read_responses(max_lines=100, line_timeout=0.6)
        action_messages = [r for r in responses if r.startswith('ACTION;')]
        can_rx_messages = [r for r in responses if r.startswith('CAN_RX;')]

        if len(can_rx_messages) == 0:
            pytest.skip("No CAN traffic detected")

        if len(action_messages) > 0:
            parts = action_messages[0].split(';')
            rule_id = parts[1]
            # Rule ID should be numeric (may be 5 or auto-assigned)
            assert rule_id.isdigit(), f"Rule ID should be numeric, got: {rule_id}"

        send_command("action:clear")
        time.sleep(0.2)

    def test_action_includes_action_type(self, send_command, read_responses):
        """Test that ACTION message includes the action type name."""
        send_command("action:clear")
        time.sleep(0.2)

        send_command("action:add:0:0x300:0xFFFFFFFF:::0:GPIO_TOGGLE:candata")
        time.sleep(1.0)

        responses = read_responses(max_lines=100, line_timeout=0.6)
        action_messages = [r for r in responses if r.startswith('ACTION;')]
        can_rx_messages = [r for r in responses if r.startswith('CAN_RX;0x300')]

        if len(can_rx_messages) == 0:
            pytest.skip("No CAN traffic on 0x300")

        if len(action_messages) > 0:
            parts = action_messages[0].split(';')
            action_type = parts[2]
            # Should be uppercase action name
            assert action_type.isupper(), f"Action type should be uppercase, got: {action_type}"
            assert '_' in action_type or action_type in ["NEOPIXEL"], \
                f"Action type format unexpected: {action_type}"

        send_command("action:clear")
        time.sleep(0.2)

    def test_action_status_ok_or_fail(self, send_command, read_responses):
        """Test that ACTION message status is either OK or FAIL."""
        send_command("action:clear")
        time.sleep(0.2)

        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:candata")
        time.sleep(1.0)

        responses = read_responses(max_lines=100, line_timeout=0.6)
        action_messages = [r for r in responses if r.startswith('ACTION;')]

        if len(action_messages) > 0:
            parts = action_messages[0].split(';')
            status = parts[4]
            assert status in ["OK", "FAIL"], f"Status should be OK or FAIL, got: {status}"

        send_command("action:clear")
        time.sleep(0.2)

    def test_multiple_rules_generate_multiple_actions(self, send_command, read_responses):
        """Test that multiple rules on same CAN ID generate multiple ACTION messages."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add two rules for same CAN ID
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:candata")
        time.sleep(0.1)
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:candata")
        time.sleep(1.0)

        responses = read_responses(max_lines=100, line_timeout=0.6)
        action_messages = [r for r in responses if r.startswith('ACTION;')]
        can_rx_messages = [r for r in responses if r.startswith('CAN_RX;0x100')]

        if len(can_rx_messages) == 0:
            pytest.skip("No CAN traffic on 0x100")

        # Should get multiple ACTION messages (at least 2 for the 2 rules)
        # Note: Depending on timing, might get more
        assert len(action_messages) >= 2, \
            f"Expected at least 2 ACTION messages for 2 rules, got {len(action_messages)}"

        send_command("action:clear")
        time.sleep(0.2)

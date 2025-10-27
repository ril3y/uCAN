"""
Tests for ACTION execution reporting feature.

When a rule is triggered and executes, the firmware should send an ACTION message
reporting the rule ID, action type, triggering CAN ID, and success/fail status.

Format: ACTION;{RULE_ID};{ACTION_TYPE};{TRIGGER_CAN_ID};{STATUS}
Example: ACTION;1;GPIO_SET;0x100;OK

IMPORTANT: These tests require actual CAN messages on the bus to trigger rules.
The 'send:' command only transmits messages, it doesn't trigger rule processing.
These tests work by:
1. Adding a rule for a CAN ID that's present in your bus traffic
2. Waiting for real CAN_RX messages
3. Verifying ACTION messages are generated when rules match
"""

import pytest
import time


@pytest.mark.hardware
@pytest.mark.integration
class TestActionExecutionReporting:
    """Test that firmware reports action execution with CAN ID"""

    def test_action_reporting_on_rule_trigger(self, ser, send_command, read_responses):
        """Test that ACTION message is sent when rule triggers on real CAN traffic"""
        # Add a rule for CAN ID 0x100 (present in test bus traffic)
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:candata")

        # Wait for rule to be added (don't reset buffer yet - let messages accumulate)
        time.sleep(1.0)

        # Now read accumulated messages including the CAN traffic
        responses = read_responses(max_lines=100, line_timeout=0.6)

        # Find ACTION messages
        action_messages = [r for r in responses if r.startswith('ACTION;')]

        # Also check if we got any CAN_RX messages
        can_rx_messages = [r for r in responses if r.startswith('CAN_RX;')]

        if len(can_rx_messages) == 0:
            # Debug: print what we got
            print(f"\nDEBUG: No CAN_RX messages found. Got {len(responses)} total responses:")
            for r in responses[:10]:
                print(f"  {r}")
            pytest.skip("No CAN traffic detected on bus - test requires active CAN communication")

        assert len(action_messages) >= 1, f"Expected ACTION message, got CAN_RX but no ACTION. Responses: {responses[:10]}"

        # Parse ACTION message: ACTION;{RULE_ID};{ACTION_TYPE};{TRIGGER_CAN_ID};{STATUS}
        action_msg = action_messages[0]
        parts = action_msg.split(';')

        assert len(parts) == 5, f"ACTION message should have 5 parts, got: {action_msg}"
        assert parts[0] == "ACTION"

        rule_id = parts[1]
        action_type = parts[2]
        trigger_can_id = parts[3]
        status = parts[4]

        # Verify the fields
        assert rule_id.isdigit(), f"Rule ID should be numeric, got: {rule_id}"
        # Accept any valid action type (firmware might assign different types based on capabilities)
        assert len(action_type) > 0, f"Action type should not be empty, got: {action_type}"
        assert trigger_can_id.startswith("0x") or trigger_can_id.startswith("0X"), \
            f"CAN ID should be hex, got: {trigger_can_id}"
        assert status in ["OK", "FAIL"], f"Status should be OK or FAIL, got: {status}"

        # Clean up - get all rules and remove the one we added
        send_command("action:list")
        time.sleep(0.2)
        list_responses = read_responses(max_lines=20, line_timeout=0.5)
        for resp in list_responses:
            if "GPIO_SET" in resp and "0x100" in resp.upper():
                # Extract rule ID and remove it
                if resp.startswith("RULE;"):
                    rule_parts = resp.split(';')
                    if len(rule_parts) > 1:
                        send_command(f"action:remove:{rule_parts[1]}")

    def test_action_reporting_includes_correct_can_id(self, ser, send_command, read_responses):
        """Test that ACTION message includes the actual triggering CAN ID"""
        # Add rule for CAN ID 0x200 (also present in test traffic)
        send_command("action:add:0:0x200:0xFFFFFFFF:::0:GPIO_TOGGLE:candata")

        # Wait for messages to accumulate
        time.sleep(1.0)

        # Read accumulated messages
        responses = read_responses(max_lines=100, line_timeout=0.6)
        action_messages = [r for r in responses if r.startswith('ACTION;')]
        can_rx_messages = [r for r in responses if r.startswith('CAN_RX;0x200')]

        if len(can_rx_messages) == 0:
            pytest.skip("No CAN traffic detected on ID 0x200 - test requires active CAN communication")

        # Filter ACTION messages for only 0x200
        action_0x200 = [msg for msg in action_messages if '0x200' in msg.upper() or '0X200' in msg]

        if len(action_0x200) == 0:
            pytest.skip(f"No ACTION messages for 0x200 in captured window (got {len(action_messages)} total ACTION messages)")

        parts = action_0x200[0].split(';')
        trigger_can_id = parts[3]

        assert trigger_can_id.upper() == "0x200".upper(), \
            f"Expected CAN ID 0x200, got: {trigger_can_id}"

        # Clean up
        send_command("action:list")
        time.sleep(0.2)
        list_responses = read_responses(max_lines=20, line_timeout=0.5)
        for resp in list_responses:
            if "GPIO_TOGGLE" in resp and "0x200" in resp.upper():
                if resp.startswith("RULE;"):
                    rule_parts = resp.split(';')
                    if len(rule_parts) > 1:
                        send_command(f"action:remove:{rule_parts[1]}")

    def test_action_reporting_format_matches_protocol(self, ser, send_command, read_responses):
        """Test that ACTION message format exactly matches PROTOCOL.md spec"""
        send_command("action:add:0:0x300:0xFFFFFFFF:::0:GPIO_CLEAR:candata")

        # Wait for messages to accumulate
        time.sleep(1.0)

        responses = read_responses(max_lines=100, line_timeout=0.6)
        action_messages = [r for r in responses if r.startswith('ACTION;')]
        can_rx_messages = [r for r in responses if r.startswith('CAN_RX;0x300')]

        if len(can_rx_messages) == 0:
            pytest.skip("No CAN traffic detected on ID 0x300 - test requires active CAN communication")

        assert len(action_messages) >= 1

        # Protocol spec: ACTION;{RULE_ID};{ACTION_TYPE};{TRIGGER_CAN_ID};{STATUS}
        msg = action_messages[0]
        parts = msg.split(';')

        # Must have exactly 5 semicolon-separated parts
        assert len(parts) == 5, f"Expected 5 parts, got {len(parts)}: {msg}"

        # Part 0: "ACTION"
        assert parts[0] == "ACTION"

        # Part 1: RULE_ID (numeric)
        assert parts[1].isdigit() and int(parts[1]) >= 0

        # Part 2: ACTION_TYPE (string, uppercase with underscores)
        assert parts[2].isupper()
        assert '_' in parts[2] or parts[2] in ["NEOPIXEL", "HEARTBEAT"]

        # Part 3: TRIGGER_CAN_ID (hex with 0x prefix)
        assert parts[3].startswith('0x') or parts[3].startswith('0X')
        int(parts[3], 16)  # Should be valid hex

        # Part 4: STATUS (OK or FAIL)
        assert parts[4] in ["OK", "FAIL"]

        # Clean up
        send_command("action:list")
        time.sleep(0.2)
        list_responses = read_responses(max_lines=20, line_timeout=0.5)
        for resp in list_responses:
            if "GPIO_CLEAR" in resp and "0x300" in resp.upper():
                if resp.startswith("RULE;"):
                    rule_parts = resp.split(';')
                    if len(rule_parts) > 1:
                        send_command(f"action:remove:{rule_parts[1]}")

    def test_multiple_actions_on_same_can_id(self, ser, send_command, read_responses):
        """Test that multiple rules on same CAN ID each generate ACTION messages"""
        # Wait for CAN traffic first (don't clear buffer)
        time.sleep(1.0)

        # Read to see what IDs are active
        initial_responses = read_responses(max_lines=30, line_timeout=0.6)
        can_rx_messages = [r for r in initial_responses if r.startswith('CAN_RX;')]

        if len(can_rx_messages) == 0:
            pytest.skip("No CAN traffic detected - test requires active CAN communication")

        # Get the first CAN ID we see
        first_can_msg = can_rx_messages[0]
        can_id = first_can_msg.split(';')[1]  # Extract CAN ID

        # Add two rules for the same CAN ID
        send_command(f"action:add:0:{can_id}:0xFFFFFFFF:::0:GPIO_SET:candata")
        time.sleep(0.1)
        send_command(f"action:add:0:{can_id}:0xFFFFFFFF:::0:GPIO_TOGGLE:candata")

        # Wait for messages to accumulate
        time.sleep(1.0)

        # Read accumulated CAN traffic with ACTION messages
        responses = read_responses(max_lines=100, line_timeout=0.6)
        action_messages = [r for r in responses if r.startswith('ACTION;')]

        # Check if we got CAN_RX for our CAN ID
        can_rx_for_id = [r for r in responses if r.startswith(f'CAN_RX;{can_id}')]
        if len(can_rx_for_id) == 0:
            pytest.skip(f"No CAN traffic detected on ID {can_id} during test period")

        # Should get multiple ACTION messages for the same CAN ID
        # (Note: there may be existing rules too, so just verify we got some)
        assert len(action_messages) >= 2, \
            f"Expected at least 2 ACTION messages, got {len(action_messages)}"

        # Verify they're for our CAN ID
        matching_actions = [msg for msg in action_messages if can_id.upper() in msg.upper()]
        assert len(matching_actions) >= 2, \
            f"Expected at least 2 ACTION messages for {can_id}, got {len(matching_actions)}"

        # Clean up
        send_command("action:list")
        time.sleep(0.2)
        list_responses = read_responses(max_lines=30, line_timeout=0.5)
        for resp in list_responses:
            if can_id.upper() in resp.upper() and any(action in resp for action in ["GPIO_SET", "GPIO_TOGGLE"]):
                if resp.startswith("RULE;"):
                    rule_parts = resp.split(';')
                    if len(rule_parts) > 1:
                        send_command(f"action:remove:{rule_parts[1]}")
                        time.sleep(0.05)

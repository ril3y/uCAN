"""
Test uCAN Protocol v2.0 rule management commands.

This module tests the complete rule lifecycle:
- action:add - Create new rules with fixed and candata parameters
- action:list - List all configured rules
- action:remove - Delete specific rules
- action:edit - Update existing rules
- action:clear - Remove all rules at once

IMPORTANT: Each test clears all rules BEFORE adding new ones to ensure isolation.

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
- No active CAN traffic required for basic rule management
"""

import pytest
import time


@pytest.mark.hardware
@pytest.mark.integration
class TestRuleManagement:
    """Test suite for action rule management commands."""

    def test_action_clear_removes_all_rules(self, send_command, wait_for_response, read_responses):
        """Test action:clear removes all configured rules."""
        # First, add some rules
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.2)
        read_responses(max_lines=5, line_timeout=0.3)  # Consume add response

        send_command("action:add:0:0x200:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:14")
        time.sleep(0.2)
        read_responses(max_lines=5, line_timeout=0.3)  # Consume add response

        # Clear all rules
        send_command("action:clear")
        time.sleep(0.2)

        response = wait_for_response("STATUS;INFO;", timeout=1.0)
        assert response is not None, "No response received for action:clear"
        assert "cleared" in response.lower() or "clear" in response.lower(), \
            f"Expected 'cleared' in response, got: {response}"

        # Verify rules are gone
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 0, \
            f"Expected no rules after clear, but got {len(rule_responses)}: {rule_responses}"

    def test_action_add_with_fixed_parameters(self, send_command, wait_for_response, read_responses):
        """Test action:add creates rule with fixed parameters."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.5)
        read_responses(max_lines=5, line_timeout=0.5)  # Consume clear response

        # Add rule with fixed parameter
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.3)

        response = wait_for_response("STATUS;INFO;", timeout=1.0)
        assert response is not None, "No response received for action:add"
        assert "added" in response.lower() or "ID:" in response, \
            f"Expected 'added' or 'ID:' in response, got: {response}"

        # Verify rule was added
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 1, \
            f"Expected 1 rule after add, got {len(rule_responses)}: {rule_responses}"

        # Parse rule format: RULE;{ID};{CAN_ID};{CAN_MASK};{DATA};{DATA_MASK};{DATA_LEN};{ACTION};{PARAM_SOURCE};{PARAMS...}
        rule = rule_responses[0]
        parts = rule.split(';')

        assert len(parts) >= 9, f"Rule should have at least 9 parts, got {len(parts)}: {rule}"
        assert parts[0] == "RULE"
        assert parts[2].upper() == "0x100".upper(), f"Expected CAN ID 0x100, got: {parts[2]}"
        assert parts[7] == "GPIO_SET", f"Expected GPIO_SET action, got: {parts[7]}"
        assert parts[8] == "fixed", f"Expected 'fixed' param source, got: {parts[8]}"
        assert parts[9] == "13", f"Expected parameter '13', got: {parts[9]}"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

    def test_action_add_with_candata_parameters(self, send_command, wait_for_response, read_responses):
        """Test action:add creates rule with candata parameter extraction."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.5)
        read_responses(max_lines=5, line_timeout=0.5)  # Consume clear response

        # Add rule with candata extraction
        send_command("action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:candata")
        time.sleep(0.3)

        response = wait_for_response("STATUS;INFO;", timeout=1.0)
        assert response is not None, "No response received for action:add"
        assert "added" in response.lower() or "ID:" in response, \
            f"Expected success response, got: {response}"

        # Verify rule was added
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 1, \
            f"Expected 1 rule after add, got {len(rule_responses)}: {rule_responses}"

        rule = rule_responses[0]
        parts = rule.split(';')

        assert len(parts) >= 9, f"Rule should have at least 9 parts, got {len(parts)}: {rule}"
        assert parts[2].upper() == "0x500".upper(), f"Expected CAN ID 0x500, got: {parts[2]}"
        assert parts[7] == "NEOPIXEL", f"Expected NEOPIXEL action, got: {parts[7]}"
        assert parts[8] == "candata", f"Expected 'candata' param source, got: {parts[8]}"

        # With candata, there should be no additional parameter fields
        assert len(parts) == 9, \
            f"candata rules should have exactly 9 parts (no params), got {len(parts)}: {rule}"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

    def test_action_add_auto_assigns_rule_id(self, send_command, read_responses):
        """Test that action:add with ID=0 auto-assigns next available ID."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.2)

        # Add first rule with ID=0 (auto-assign)
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.2)

        # Add second rule with ID=0 (should get different ID)
        send_command("action:add:0:0x200:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:14")
        time.sleep(0.2)

        # List rules
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 2, \
            f"Expected 2 rules, got {len(rule_responses)}: {rule_responses}"

        # Extract rule IDs
        rule_ids = []
        for rule in rule_responses:
            parts = rule.split(';')
            rule_id = parts[1]
            assert rule_id.isdigit(), f"Rule ID should be numeric, got: {rule_id}"
            rule_ids.append(int(rule_id))

        # Verify IDs are unique
        assert len(set(rule_ids)) == 2, f"Rule IDs should be unique, got: {rule_ids}"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

    def test_action_list_format(self, send_command, read_responses):
        """Test action:list returns rules in correct format."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.2)

        # Add a rule with all fields populated
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.2)

        # List rules
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) > 0, "No rules returned by action:list"

        # Parse first rule
        rule = rule_responses[0]
        parts = rule.split(';')

        # RULE format: RULE;{ID};{CAN_ID};{CAN_MASK};{DATA};{DATA_MASK};{DATA_LEN};{ACTION};{PARAM_SOURCE};{PARAMS...}
        assert len(parts) >= 9, f"RULE should have at least 9 parts, got {len(parts)}: {rule}"

        assert parts[0] == "RULE", f"First part should be 'RULE', got: {parts[0]}"
        assert parts[1].isdigit(), f"Rule ID should be numeric, got: {parts[1]}"
        assert parts[2].startswith("0x") or parts[2].startswith("0X"), \
            f"CAN ID should be hex with 0x prefix, got: {parts[2]}"
        assert parts[3].startswith("0x") or parts[3].startswith("0X"), \
            f"CAN mask should be hex with 0x prefix, got: {parts[3]}"
        # parts[4] = DATA (can be empty)
        # parts[5] = DATA_MASK (can be empty)
        assert parts[6].isdigit(), f"DATA_LEN should be numeric, got: {parts[6]}"
        assert parts[7].isupper(), f"ACTION should be uppercase, got: {parts[7]}"
        assert parts[8] in ["fixed", "candata"], \
            f"PARAM_SOURCE should be 'fixed' or 'candata', got: {parts[8]}"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

    def test_action_remove_deletes_specific_rule(self, send_command, wait_for_response, read_responses):
        """Test action:remove deletes a specific rule by ID."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.5)
        read_responses(max_lines=5, line_timeout=0.5)  # Consume clear response

        # Add two rules
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.5)
        read_responses(max_lines=5, line_timeout=0.5)  # Consume add response
        send_command("action:add:0:0x200:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:14")
        time.sleep(0.5)
        read_responses(max_lines=5, line_timeout=0.5)  # Consume add response

        # Get rule IDs
        send_command("action:list")
        time.sleep(0.5)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 2, f"Expected 2 rules, got {len(rule_responses)}"

        # Extract first rule ID
        first_rule_id = rule_responses[0].split(';')[1]

        # Remove first rule
        send_command(f"action:remove:{first_rule_id}")

        response = wait_for_response("STATUS;INFO;", timeout=1.0)
        assert response is not None, "No response received for action:remove"
        assert "removed" in response.lower() or first_rule_id in response, \
            f"Expected 'removed' or rule ID in response, got: {response}"

        # Verify only one rule remains
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 1, \
            f"Expected 1 rule after remove, got {len(rule_responses)}: {rule_responses}"

        # Verify the remaining rule is NOT the one we removed
        remaining_rule_id = rule_responses[0].split(';')[1]
        assert remaining_rule_id != first_rule_id, \
            f"Removed rule {first_rule_id} still present"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

    def test_action_remove_nonexistent_rule_fails(self, send_command, read_responses):
        """Test action:remove fails gracefully for non-existent rule ID."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.5)
        read_responses(max_lines=5, line_timeout=0.5)  # Consume clear response

        # Try to remove a rule that doesn't exist
        send_command("action:remove:99")
        time.sleep(0.5)

        responses = read_responses(max_lines=10, line_timeout=0.5)

        # Should get an error or info message
        status_responses = [r for r in responses if r.startswith("STATUS;")]

        # We expect either an ERROR or INFO message about the non-existent rule
        assert len(status_responses) > 0, "Expected STATUS response for non-existent rule"

        # The response might be ERROR or just an INFO saying "not found"
        # (firmware implementation may vary)
        status_msg = status_responses[0]
        assert "ERROR" in status_msg or "not found" in status_msg.lower(), \
            f"Expected error or 'not found' for non-existent rule, got: {status_msg}"

    def test_action_edit_updates_existing_rule(self, send_command, wait_for_response, read_responses):
        """Test action:edit updates an existing rule's parameters."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.5)
        read_responses(max_lines=5, line_timeout=0.5)  # Consume clear response

        # Add initial rule
        send_command("action:add:1:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.5)
        read_responses(max_lines=5, line_timeout=0.5)  # Consume add response

        # Verify initial rule
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]
        assert len(rule_responses) == 1, "Expected 1 rule after add"

        initial_rule = rule_responses[0]
        assert ";13" in initial_rule, "Initial rule should have parameter 13"

        # Edit the rule to change parameter
        send_command("action:edit:1:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:14")

        response = wait_for_response("STATUS;INFO;", timeout=1.0)
        assert response is not None, "No response received for action:edit"
        assert "updated" in response.lower() or "edit" in response.lower() or "ID:" in response, \
            f"Expected success response for edit, got: {response}"

        # Verify rule was updated
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 1, \
            f"Expected 1 rule after edit, got {len(rule_responses)}: {rule_responses}"

        updated_rule = rule_responses[0]
        assert ";14" in updated_rule, f"Updated rule should have parameter 14, got: {updated_rule}"
        assert ";13" not in updated_rule, f"Updated rule should not have old parameter 13, got: {updated_rule}"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

    def test_action_edit_can_change_action_type(self, send_command, read_responses):
        """Test action:edit can change the action type completely."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.2)

        # Add initial rule with GPIO_SET
        send_command("action:add:1:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.2)

        # Edit to change action type to GPIO_TOGGLE
        send_command("action:edit:1:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:13")
        time.sleep(0.3)

        # Verify action type changed
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 1, "Expected 1 rule after edit"

        updated_rule = rule_responses[0]
        assert "GPIO_TOGGLE" in updated_rule, \
            f"Rule should have GPIO_TOGGLE action, got: {updated_rule}"
        assert "GPIO_SET" not in updated_rule, \
            f"Rule should not have old GPIO_SET action, got: {updated_rule}"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

    def test_action_edit_can_change_can_id(self, send_command, read_responses):
        """Test action:edit can change the triggering CAN ID."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.2)

        # Add initial rule with CAN ID 0x100
        send_command("action:add:1:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.2)

        # Edit to change CAN ID to 0x200
        send_command("action:edit:1:0x200:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.3)

        # Verify CAN ID changed
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 1, "Expected 1 rule after edit"

        updated_rule = rule_responses[0]
        assert "0x200" in updated_rule or "0X200" in updated_rule, \
            f"Rule should have CAN ID 0x200, got: {updated_rule}"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

    def test_param_source_is_required(self, send_command, read_responses):
        """Test that PARAM_SOURCE field is required in action:add (breaking change from v1.x)."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.5)
        read_responses(max_lines=5, line_timeout=0.5)  # Consume clear response

        # Try to add rule WITHOUT param_source (should fail)
        # Old v1.x format: action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:13
        # New v2.0 format: action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:13")
        time.sleep(0.5)

        responses = read_responses(max_lines=10, line_timeout=0.5)

        # Should get an error response
        status_responses = [r for r in responses if r.startswith("STATUS;")]

        # Firmware should reject this command
        assert len(status_responses) > 0, \
            "Expected STATUS response for command missing PARAM_SOURCE"

        # Should be an error (not a success)
        status_msg = status_responses[0]
        assert "ERROR" in status_msg, \
            f"Expected ERROR for missing PARAM_SOURCE, got: {status_msg}"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

    def test_multiple_rules_on_same_can_id(self, send_command, read_responses):
        """Test that multiple rules can be added for the same CAN ID."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.2)

        # Add two rules for the same CAN ID
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13")
        time.sleep(0.2)
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:14")
        time.sleep(0.2)

        # List rules
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 2, \
            f"Expected 2 rules for same CAN ID, got {len(rule_responses)}: {rule_responses}"

        # Verify both rules have CAN ID 0x100 (case-insensitive hex matching)
        for rule in rule_responses:
            assert "0x100" in rule.lower(), f"Rule should have CAN ID 0x100, got: {rule}"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

    def test_rule_with_multi_byte_fixed_parameters(self, send_command, read_responses):
        """Test rule creation with multiple fixed parameters (e.g., NEOPIXEL RGB)."""
        # Clear rules first
        send_command("action:clear")
        time.sleep(0.2)

        # Add NEOPIXEL rule with fixed RGB values
        # NEOPIXEL has 4 parameters: R, G, B, brightness
        send_command("action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:fixed:255:128:0:200")
        time.sleep(0.2)

        # Verify rule was added
        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 1, f"Expected 1 rule, got {len(rule_responses)}"

        rule = rule_responses[0]
        parts = rule.split(';')

        # Verify all parameters are present
        # RULE;{ID};{CAN_ID};{CAN_MASK};{DATA};{DATA_MASK};{DATA_LEN};{ACTION};{PARAM_SOURCE};{R};{G};{B};{BRIGHTNESS}
        assert len(parts) >= 13, f"NEOPIXEL rule should have at least 13 parts, got {len(parts)}: {rule}"
        assert parts[7] == "NEOPIXEL", f"Action should be NEOPIXEL, got: {parts[7]}"
        assert parts[8] == "fixed", f"Param source should be 'fixed', got: {parts[8]}"
        assert parts[9] == "255", f"R should be 255, got: {parts[9]}"
        assert parts[10] == "128", f"G should be 128, got: {parts[10]}"
        assert parts[11] == "0", f"B should be 0, got: {parts[11]}"
        assert parts[12] == "200", f"Brightness should be 200, got: {parts[12]}"

        # Cleanup
        send_command("action:clear")
        time.sleep(0.2)

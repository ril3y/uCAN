"""
Test uCAN Protocol v2.0 CAN data pattern matching.

Tests DATA, DATA_MASK, and DATA_LEN filtering for conditional rule triggering.

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
- Live CAN traffic for testing data matching
"""

import pytest
import time


@pytest.mark.hardware
class TestDataMatching:
    """Test suite for CAN data pattern matching."""

    def test_data_length_filtering(self, send_command, wait_for_response):
        """Test DATA_LEN parameter filters by message length."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add rule that only triggers on 4-byte messages
        # Format: action:add:ID:CAN_ID:CAN_MASK:DATA:DATA_MASK:DATA_LEN:ACTION:PARAM_SOURCE:PARAMS
        send_command("action:add:0:0x100:0xFFFFFFFF:::4:GPIO_TOGGLE:fixed:13")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for DATA_LEN rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_data_pattern_matching_single_byte(self, send_command, wait_for_response):
        """Test DATA and DATA_MASK for single byte matching."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add rule that only triggers when byte 0 = 0xFF
        send_command("action:add:0:0x100:0xFFFFFFFF:FF:FF:0:GPIO_TOGGLE:fixed:13")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for data pattern rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_data_pattern_matching_multi_byte(self, send_command, wait_for_response):
        """Test DATA and DATA_MASK for multi-byte pattern."""
        send_command("action:clear")
        time.sleep(0.2)

        # Match: byte 0 = 0xFF, byte 1 = 0x00
        send_command("action:add:0:0x200:0xFFFFFFFF:FF,00:FF,FF:0:GPIO_TOGGLE:fixed:13")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for multi-byte pattern rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_data_mask_dont_care_bits(self, send_command, wait_for_response):
        """Test DATA_MASK with don't care bits (0x00)."""
        send_command("action:clear")
        time.sleep(0.2)

        # Match byte 0, don't care about byte 1
        send_command("action:add:0:0x300:0xFFFFFFFF:FF,00:FF,00:0:GPIO_TOGGLE:fixed:13")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for masked pattern rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_wildcard_can_id(self, send_command, wait_for_response):
        """Test wildcard CAN ID matching (0x000:0x000)."""
        send_command("action:clear")
        time.sleep(0.2)

        # Match any CAN ID
        send_command("action:add:0:0x000:0x000:::0:GPIO_TOGGLE:fixed:13")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for wildcard CAN ID rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_can_id_mask_range(self, send_command, wait_for_response):
        """Test CAN ID mask for range matching."""
        send_command("action:clear")
        time.sleep(0.2)

        # Match CAN IDs 0x100-0x1FF (mask 0xFFFFFF00)
        send_command("action:add:0:0x100:0xFFFFFF00:::0:GPIO_TOGGLE:fixed:13")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for CAN ID mask rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_combined_data_and_length_filtering(self, send_command, wait_for_response):
        """Test combination of DATA pattern and DATA_LEN."""
        send_command("action:clear")
        time.sleep(0.2)

        # Match: byte 0 = 0x80 AND exactly 4 bytes
        send_command("action:add:0:0x100:0xFFFFFFFF:80:FF:4:GPIO_TOGGLE:fixed:13")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for combined filter rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_data_matching_rule_format(self, send_command, read_responses):
        """Test that data matching rules are stored correctly."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add rule with data matching
        send_command("action:add:0:0x100:0xFFFFFFFF:FF,00:FF,FF:2:GPIO_TOGGLE:fixed:13")
        time.sleep(0.2)

        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 1

        rule = rule_responses[0]
        parts = rule.split(';')

        # Verify data matching fields
        # RULE;{ID};{CAN_ID};{CAN_MASK};{DATA};{DATA_MASK};{DATA_LEN};...
        assert parts[4].upper() == "FF,00", f"Expected DATA 'FF,00', got: {parts[4]}"
        assert parts[5].upper() == "FF,FF", f"Expected DATA_MASK 'FF,FF', got: {parts[5]}"
        assert parts[6] == "2", f"Expected DATA_LEN '2', got: {parts[6]}"

        send_command("action:clear")
        time.sleep(0.2)

    def test_empty_data_matching_fields(self, send_command, read_responses):
        """Test rules with empty DATA and DATA_MASK fields (no data filtering)."""
        send_command("action:clear")
        time.sleep(0.2)

        # Add rule with no data filtering
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:13")
        time.sleep(0.2)

        send_command("action:list")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.5)
        rule_responses = [r for r in responses if r.startswith("RULE;")]

        assert len(rule_responses) == 1

        rule = rule_responses[0]
        parts = rule.split(';')

        # DATA and DATA_MASK fields should be empty
        assert parts[4] == "", f"Expected empty DATA field, got: {parts[4]}"
        assert parts[5] == "", f"Expected empty DATA_MASK field, got: {parts[5]}"
        assert parts[6] == "0", f"Expected DATA_LEN '0' (any length), got: {parts[6]}"

        send_command("action:clear")
        time.sleep(0.2)

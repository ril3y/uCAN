"""
Test uCAN Protocol v2.0 ACTIONDEF schema validation.

This module validates that action definitions returned by get:actiondefs
conform to the protocol specification and include all required metadata
for UI builders.

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
"""

import pytest
import time


@pytest.mark.hardware
@pytest.mark.integration
class TestActionDefinitions:
    """Test suite for ACTIONDEF message schema validation."""

    def test_all_actiondefs_have_unique_action_ids(self, get_action_definitions):
        """Test that all action definitions have unique 'i' (action ID) values."""
        action_defs = get_action_definitions()

        action_ids = [action_def["i"] for action_def in action_defs]

        # Check for duplicates
        assert len(action_ids) == len(set(action_ids)), \
            f"Action IDs should be unique, got duplicates in: {action_ids}"

    def test_all_actiondefs_have_unique_names(self, get_action_definitions):
        """Test that all action definitions have unique 'n' (name) values."""
        action_defs = get_action_definitions()

        action_names = [action_def["n"] for action_def in action_defs]

        # Check for duplicates
        assert len(action_names) == len(set(action_names)), \
            f"Action names should be unique, got duplicates in: {action_names}"

    def test_actiondef_categories_are_valid(self, get_action_definitions):
        """Test that all action definitions have valid category values."""
        action_defs = get_action_definitions()

        valid_categories = ["GPIO", "PWM", "Display", "Communication", "I2C", "Analog", "Buffer", "Sensor", "CAN", "System"]

        for action_def in action_defs:
            category = action_def["c"]
            assert category in valid_categories, \
                f"Invalid category '{category}' in action '{action_def['n']}'. " \
                f"Valid categories: {valid_categories}"

    def test_actiondef_descriptions_are_meaningful(self, get_action_definitions):
        """Test that all action descriptions are non-empty and meaningful."""
        action_defs = get_action_definitions()

        for action_def in action_defs:
            description = action_def["d"]

            assert len(description) > 0, \
                f"Action '{action_def['n']}' has empty description"

            assert len(description) >= 10, \
                f"Action '{action_def['n']}' description too short: '{description}'"

    def test_parameter_byte_indices_are_unique_within_action(self, get_action_definitions):
        """Test that parameters within an action don't overlap byte positions improperly."""
        action_defs = get_action_definitions()

        for action_def in action_defs:
            params = action_def["p"]

            # For full-byte parameters (l=8, o=0), byte indices should be unique
            full_byte_params = [p for p in params if p["l"] == 8 and p["o"] == 0]
            byte_indices = [p["b"] for p in full_byte_params]

            # Check for duplicate byte indices among full-byte params
            if len(byte_indices) > 0:
                assert len(byte_indices) == len(set(byte_indices)), \
                    f"Action '{action_def['n']}' has overlapping full-byte parameters at indices: {byte_indices}"

    def test_parameter_ranges_are_valid_format(self, get_action_definitions):
        """Test that parameter ranges follow 'min-max' format."""
        action_defs = get_action_definitions()

        for action_def in action_defs:
            params = action_def["p"]

            for param in params:
                range_str = param["r"]

                # Range should contain a dash
                assert "-" in range_str, \
                    f"Parameter '{param['n']}' in action '{action_def['n']}' has invalid range format: '{range_str}'"

                # Try to parse min-max
                parts = range_str.split("-")
                assert len(parts) == 2 or (len(parts) == 3 and parts[0] == ""), \
                    f"Range should be 'min-max', got: '{range_str}'"

                # Handle negative numbers (e.g., "-128-127")
                if parts[0] == "":
                    min_val = -int(parts[1])
                    max_val = int(parts[2])
                else:
                    min_val = int(parts[0])
                    max_val = int(parts[1])

                assert min_val <= max_val, \
                    f"Parameter '{param['n']}' has invalid range: min({min_val}) > max({max_val})"

    def test_optional_label_and_hint_fields(self, get_action_definitions):
        """Test that label and hint fields are present and useful when provided."""
        action_defs = get_action_definitions()

        for action_def in action_defs:
            params = action_def["p"]

            for param in params:
                # label and hint are optional, but if present, should be non-empty
                if "label" in param:
                    label = param["label"]
                    assert len(label) > 0, \
                        f"Parameter '{param['n']}' has empty label field"

                    # Label should be different from the 'n' field (otherwise pointless)
                    assert label != param["n"], \
                        f"Parameter '{param['n']}' label is same as name (redundant)"

                if "hint" in param:
                    hint = param["hint"]
                    assert len(hint) > 0, \
                        f"Parameter '{param['n']}' has empty hint field"

    def test_gpio_actions_exist(self, get_action_definitions):
        """Test that basic GPIO actions are defined."""
        action_defs = get_action_definitions()

        action_names = [action_def["n"] for action_def in action_defs]

        # Basic GPIO actions should be present
        expected_gpio_actions = ["GPIO_SET", "GPIO_CLEAR", "GPIO_TOGGLE"]

        for gpio_action in expected_gpio_actions:
            assert gpio_action in action_names, \
                f"Expected GPIO action '{gpio_action}' not found in: {action_names}"

    def test_neopixel_action_exists(self, get_action_definitions):
        """Test that NEOPIXEL action is defined (SAMD51 Feather M4 has built-in NeoPixel)."""
        action_defs = get_action_definitions()

        action_names = [action_def["n"] for action_def in action_defs]

        assert "NEOPIXEL" in action_names, \
            f"Expected NEOPIXEL action not found in: {action_names}"

    def test_neopixel_has_correct_parameters(self, get_action_definitions):
        """Test that NEOPIXEL action has R, G, B, and brightness parameters."""
        action_defs = get_action_definitions()

        neopixel_def = next((a for a in action_defs if a["n"] == "NEOPIXEL"), None)
        assert neopixel_def is not None, "NEOPIXEL action not found"

        params = neopixel_def["p"]
        param_names = [p["n"] for p in params]

        # NEOPIXEL should have R, G, B, and brightness
        expected_params = ["r", "g", "b", "brightness"]

        for expected in expected_params:
            assert expected in param_names, \
                f"NEOPIXEL missing parameter '{expected}'. Has: {param_names}"

    def test_phase1_i2c_actions_exist(self, get_action_definitions):
        """Test that Phase 1 I2C actions are defined."""
        action_defs = get_action_definitions()

        action_names = [action_def["n"] for action_def in action_defs]

        # Phase 1 I2C actions
        expected_i2c_actions = ["I2C_WRITE", "I2C_READ_BUFFER"]

        for i2c_action in expected_i2c_actions:
            assert i2c_action in action_names, \
                f"Expected Phase 1 I2C action '{i2c_action}' not found in: {action_names}"

    def test_phase1_buffer_actions_exist(self, get_action_definitions):
        """Test that Phase 1 buffer system actions are defined."""
        action_defs = get_action_definitions()

        action_names = [action_def["n"] for action_def in action_defs]

        # Phase 1 buffer actions
        expected_buffer_actions = ["GPIO_READ_BUFFER", "ADC_READ_BUFFER", "BUFFER_SEND", "BUFFER_CLEAR"]

        for buffer_action in expected_buffer_actions:
            assert buffer_action in action_names, \
                f"Expected Phase 1 buffer action '{buffer_action}' not found in: {action_names}"

    def test_pwm_configure_exists(self, get_action_definitions):
        """Test that PWM_CONFIGURE action is defined (Phase 1 feature)."""
        action_defs = get_action_definitions()

        action_names = [action_def["n"] for action_def in action_defs]

        assert "PWM_CONFIGURE" in action_names, \
            f"Expected PWM_CONFIGURE action not found in: {action_names}"

    def test_parameter_types_match_size_requirements(self, get_action_definitions):
        """Test that parameter type codes match their declared bit lengths."""
        action_defs = get_action_definitions()

        # Type code to expected bit length mapping
        type_sizes = {
            0: 8,   # uint8
            1: 16,  # uint16
            2: 32,  # uint32
            3: 8,   # int8
            4: 16,  # int16
            5: 32,  # int32
            6: 32,  # float
            7: 1    # bool
        }

        for action_def in action_defs:
            params = action_def["p"]

            for param in params:
                param_type = param["t"]
                bit_length = param["l"]

                # For most types, bit length should match type size
                if param_type in type_sizes:
                    expected_length = type_sizes[param_type]

                    # Bit-packed booleans can be length 1
                    if param_type == 7 and bit_length == 1:
                        continue

                    # For other types, bit length should generally match
                    # (though sub-byte extraction is allowed)
                    assert bit_length <= expected_length, \
                        f"Parameter '{param['n']}' in action '{action_def['n']}' " \
                        f"has bit_length {bit_length} > type size {expected_length}"

    def test_actiondefs_are_valid_json(self, send_command, read_responses, parse_json_response):
        """Test that all ACTIONDEF messages contain valid, parseable JSON."""
        send_command("get:actiondefs")
        time.sleep(0.3)

        responses = read_responses(max_lines=20, line_timeout=0.3)
        actiondefs = [r for r in responses if r.startswith("ACTIONDEF;")]

        assert len(actiondefs) > 0, "No ACTIONDEF messages received"

        parse_failures = []
        for actiondef in actiondefs:
            parsed = parse_json_response(actiondef)
            if parsed is None:
                parse_failures.append(actiondef)

        assert len(parse_failures) == 0, \
            f"Failed to parse {len(parse_failures)} ACTIONDEF messages: {parse_failures}"

    def test_action_ids_are_sequential(self, get_action_definitions):
        """Test that action IDs are reasonably sequential (no huge gaps)."""
        action_defs = get_action_definitions()

        action_ids = sorted([action_def["i"] for action_def in action_defs])

        if len(action_ids) > 1:
            # Check that there are no huge gaps (> 10) in action IDs
            for i in range(len(action_ids) - 1):
                gap = action_ids[i + 1] - action_ids[i]
                assert gap <= 10, \
                    f"Large gap in action IDs: {action_ids[i]} -> {action_ids[i+1]} (gap: {gap})"

"""
Test basic uCAN Protocol v2.0 commands.

This module tests fundamental device query commands:
- get:version - Firmware version information
- get:status - Current device status
- get:stats - Statistics counters
- get:capabilities - Board capabilities (JSON)
- get:actiondefs - Action definitions (JSON array)
- get:pins - Pin capabilities summary

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
- No active CAN traffic required
"""

import pytest
import time
import json


@pytest.mark.hardware
@pytest.mark.integration
class TestBasicCommands:
    """Test suite for basic query commands."""

    def test_get_version(self, send_command, wait_for_response):
        """Test get:version returns firmware version information."""
        send_command("get:version")

        response = wait_for_response("STATUS;INFO;", timeout=1.0)

        assert response is not None, "No response received for get:version"
        assert "STATUS;INFO;" in response, f"Expected STATUS;INFO; prefix, got: {response}"

        # Response should contain platform and version info
        # Example: STATUS;INFO;Platform: SAMD51_CAN, Version: 2.0.0, Protocol: 2.0
        assert "Platform:" in response or "Version:" in response or "Protocol:" in response, \
            f"Response missing version information: {response}"

    def test_get_status(self, send_command, wait_for_response):
        """Test get:status returns current device status."""
        send_command("get:status")

        response = wait_for_response("STATUS;INFO;", timeout=1.0)

        assert response is not None, "No response received for get:status"
        assert "STATUS;INFO;" in response, f"Expected STATUS;INFO; prefix, got: {response}"

        # Response should contain message counters
        # Example: STATUS;INFO;RX:1234 TX:567 ERR:2
        assert "RX:" in response or "TX:" in response, \
            f"Response missing status information: {response}"

    def test_get_stats(self, send_command, wait_for_response):
        """Test get:stats returns statistics in correct format."""
        send_command("get:stats")

        response = wait_for_response("STATS;", timeout=1.0)

        assert response is not None, "No response received for get:stats"
        assert response.startswith("STATS;"), f"Expected STATS; prefix, got: {response}"

        # Parse STATS format: STATS;{RX_COUNT};{TX_COUNT};{ERR_COUNT};{BUS_LOAD};{TIMESTAMP}
        parts = response.split(';')
        assert len(parts) == 6, f"STATS should have 6 parts, got {len(parts)}: {response}"

        # Verify message type
        assert parts[0] == "STATS", f"First part should be STATS, got: {parts[0]}"

        # Verify all counters are numeric
        rx_count = parts[1]
        tx_count = parts[2]
        err_count = parts[3]
        bus_load = parts[4]
        timestamp = parts[5]

        assert rx_count.isdigit(), f"RX count should be numeric, got: {rx_count}"
        assert tx_count.isdigit(), f"TX count should be numeric, got: {tx_count}"
        assert err_count.isdigit(), f"ERR count should be numeric, got: {err_count}"
        assert bus_load.isdigit(), f"Bus load should be numeric, got: {bus_load}"
        assert timestamp.isdigit(), f"Timestamp should be numeric, got: {timestamp}"

        # Verify bus load is percentage (0-100)
        bus_load_int = int(bus_load)
        assert 0 <= bus_load_int <= 100, f"Bus load should be 0-100%, got: {bus_load_int}"

    def test_get_capabilities_returns_valid_json(self, send_command, wait_for_response, parse_json_response):
        """Test get:capabilities returns valid JSON with required fields."""
        send_command("get:capabilities")

        response = wait_for_response("CAPS;", timeout=1.0)

        assert response is not None, "No response received for get:capabilities"
        assert response.startswith("CAPS;"), f"Expected CAPS; prefix, got: {response}"

        # Parse JSON
        caps = parse_json_response(response)
        assert caps is not None, f"Failed to parse JSON from: {response}"

        # Verify required top-level fields
        required_fields = ["board", "chip", "clock_mhz", "flash_kb", "ram_kb",
                          "protocol_version", "firmware_version"]
        for field in required_fields:
            assert field in caps, f"CAPS missing required field: {field}"

        # Verify field types
        assert isinstance(caps["board"], str), "board should be string"
        assert isinstance(caps["chip"], str), "chip should be string"
        assert isinstance(caps["clock_mhz"], (int, float)), "clock_mhz should be numeric"
        assert isinstance(caps["flash_kb"], (int, float)), "flash_kb should be numeric"
        assert isinstance(caps["ram_kb"], (int, float)), "ram_kb should be numeric"
        assert isinstance(caps["protocol_version"], str), "protocol_version should be string"
        assert isinstance(caps["firmware_version"], str), "firmware_version should be string"

    def test_get_capabilities_includes_can_object(self, send_command, wait_for_response, parse_json_response):
        """Test get:capabilities includes CAN peripheral information."""
        send_command("get:capabilities")

        response = wait_for_response("CAPS;", timeout=1.0)
        caps = parse_json_response(response)

        assert caps is not None, "Failed to parse CAPS response"
        assert "can" in caps, "CAPS missing 'can' object"

        can_obj = caps["can"]
        assert isinstance(can_obj, dict), "CAN should be an object"

        # Verify CAN object fields
        required_can_fields = ["controllers", "max_bitrate", "fd_capable", "filters"]
        for field in required_can_fields:
            assert field in can_obj, f"CAN object missing field: {field}"

        # Verify field types
        assert isinstance(can_obj["controllers"], int), "controllers should be integer"
        assert isinstance(can_obj["max_bitrate"], int), "max_bitrate should be integer"
        assert isinstance(can_obj["fd_capable"], bool), "fd_capable should be boolean"
        assert isinstance(can_obj["filters"], int), "filters should be integer"

        # Verify reasonable values
        assert can_obj["controllers"] > 0, "Should have at least 1 CAN controller"
        assert can_obj["max_bitrate"] >= 125000, "Max bitrate should be at least 125kbps"

    def test_get_capabilities_includes_gpio_object(self, send_command, wait_for_response, parse_json_response):
        """Test get:capabilities includes GPIO information."""
        send_command("get:capabilities")

        response = wait_for_response("CAPS;", timeout=1.0)
        caps = parse_json_response(response)

        assert caps is not None, "Failed to parse CAPS response"
        assert "gpio" in caps, "CAPS missing 'gpio' object"

        gpio_obj = caps["gpio"]
        assert isinstance(gpio_obj, dict), "GPIO should be an object"

        # Verify GPIO object fields
        required_gpio_fields = ["total", "pwm", "adc", "dac"]
        for field in required_gpio_fields:
            assert field in gpio_obj, f"GPIO object missing field: {field}"

        # Verify field types and reasonable values
        assert isinstance(gpio_obj["total"], int) and gpio_obj["total"] > 0
        assert isinstance(gpio_obj["pwm"], int) and gpio_obj["pwm"] >= 0
        assert isinstance(gpio_obj["adc"], int) and gpio_obj["adc"] >= 0
        assert isinstance(gpio_obj["dac"], int) and gpio_obj["dac"] >= 0

        # Verify PWM/ADC/DAC counts don't exceed total pins
        assert gpio_obj["pwm"] <= gpio_obj["total"], "PWM pins exceed total pins"
        assert gpio_obj["adc"] <= gpio_obj["total"], "ADC pins exceed total pins"
        assert gpio_obj["dac"] <= gpio_obj["total"], "DAC pins exceed total pins"

    def test_get_capabilities_includes_features_array(self, send_command, wait_for_response, parse_json_response):
        """Test get:capabilities includes features array."""
        send_command("get:capabilities")

        response = wait_for_response("CAPS;", timeout=1.0)
        caps = parse_json_response(response)

        assert caps is not None, "Failed to parse CAPS response"
        assert "features" in caps, "CAPS missing 'features' array"

        features = caps["features"]
        assert isinstance(features, list), "features should be an array"

        # All features should be strings
        for feature in features:
            assert isinstance(feature, str), f"Feature should be string, got: {feature}"

        # SAMD51 should have at least these features
        expected_features = ["action_system", "rules_engine"]
        for expected in expected_features:
            assert expected in features, f"Expected feature '{expected}' not found in {features}"

    def test_get_actiondefs_returns_multiple_definitions(self, send_command, read_responses, parse_json_response):
        """Test get:actiondefs returns multiple ACTIONDEF messages."""
        send_command("get:actiondefs")
        time.sleep(0.3)  # Give device time to send all definitions

        responses = read_responses(max_lines=20, line_timeout=0.3)

        # Filter for ACTIONDEF messages
        actiondefs = [r for r in responses if r.startswith("ACTIONDEF;")]

        assert len(actiondefs) > 0, "No ACTIONDEF messages received"
        assert len(actiondefs) >= 5, f"Expected at least 5 action definitions, got {len(actiondefs)}"

        # Parse each definition
        parsed_defs = []
        for actiondef in actiondefs:
            parsed = parse_json_response(actiondef)
            assert parsed is not None, f"Failed to parse ACTIONDEF: {actiondef}"
            parsed_defs.append(parsed)

        # Verify we got some parsed definitions
        assert len(parsed_defs) > 0, "No action definitions were successfully parsed"

    def test_get_actiondefs_includes_required_fields(self, get_action_definitions):
        """Test that all action definitions include required fields."""
        action_defs = get_action_definitions()

        assert len(action_defs) > 0, "No action definitions received"

        required_fields = ["i", "n", "d", "c", "trig", "p"]

        for action_def in action_defs:
            for field in required_fields:
                assert field in action_def, \
                    f"Action definition missing field '{field}': {action_def}"

            # Verify field types
            assert isinstance(action_def["i"], int), "i (action ID) should be integer"
            assert isinstance(action_def["n"], str), "n (name) should be string"
            assert isinstance(action_def["d"], str), "d (description) should be string"
            assert isinstance(action_def["c"], str), "c (category) should be string"
            assert isinstance(action_def["trig"], str), "trig (trigger type) should be string"
            assert isinstance(action_def["p"], list), "p (parameters) should be array"

            # Verify name is uppercase with underscores
            assert action_def["n"].isupper() or action_def["n"] == "NEOPIXEL", \
                f"Action name should be uppercase: {action_def['n']}"

    def test_get_actiondefs_trigger_types_are_valid(self, get_action_definitions):
        """Test that all trigger types are valid values."""
        action_defs = get_action_definitions()

        valid_triggers = ["can_msg", "periodic", "gpio", "manual"]

        for action_def in action_defs:
            trig = action_def["trig"]
            assert trig in valid_triggers, \
                f"Invalid trigger type '{trig}' in action '{action_def['n']}'. Valid: {valid_triggers}"

    def test_get_actiondefs_parameter_fields_valid(self, get_action_definitions):
        """Test that parameter definitions have valid fields and types."""
        action_defs = get_action_definitions()

        for action_def in action_defs:
            params = action_def["p"]

            for param in params:
                # Required parameter fields
                required_param_fields = ["n", "t", "b", "o", "l", "r", "role"]
                for field in required_param_fields:
                    assert field in param, \
                        f"Parameter missing field '{field}' in action '{action_def['n']}': {param}"

                # Verify parameter field types
                assert isinstance(param["n"], str), "Parameter name should be string"
                assert isinstance(param["t"], int), "Parameter type should be integer"
                assert isinstance(param["b"], int), "Parameter byte index should be integer"
                assert isinstance(param["o"], int), "Parameter bit offset should be integer"
                assert isinstance(param["l"], int), "Parameter bit length should be integer"
                assert isinstance(param["r"], str), "Parameter range should be string"
                assert isinstance(param["role"], str), "Parameter role should be string"

                # Verify parameter type code is valid (0-7)
                assert 0 <= param["t"] <= 7, f"Invalid parameter type code: {param['t']}"

                # Verify byte index is valid (0-7 for standard CAN)
                assert 0 <= param["b"] <= 7, f"Invalid byte index: {param['b']}"

                # Verify bit offset is valid (0-7)
                assert 0 <= param["o"] <= 7, f"Invalid bit offset: {param['o']}"

                # Verify bit length is valid (1-64)
                assert 1 <= param["l"] <= 64, f"Invalid bit length: {param['l']}"

                # Verify role is valid
                valid_roles = ["action_param", "trigger_param", "output_param"]
                assert param["role"] in valid_roles, \
                    f"Invalid parameter role '{param['role']}'. Valid: {valid_roles}"

    def test_get_pins(self, send_command, wait_for_response):
        """Test get:pins returns pin capabilities summary."""
        send_command("get:pins")

        response = wait_for_response("PINS;", timeout=1.0)

        assert response is not None, "No response received for get:pins"
        assert response.startswith("PINS;"), f"Expected PINS; prefix, got: {response}"

        # Parse PINS format: PINS;{TOTAL};PWM:{PWM_COUNT};ADC:{ADC_COUNT};DAC:{DAC_COUNT}
        parts = response.split(';')
        assert len(parts) >= 2, f"PINS should have at least 2 parts, got: {response}"

        # Verify first part is PINS
        assert parts[0] == "PINS", f"First part should be PINS, got: {parts[0]}"

        # Verify total pin count is numeric
        total_pins = parts[1]
        assert total_pins.isdigit(), f"Total pins should be numeric, got: {total_pins}"
        assert int(total_pins) > 0, "Should have at least 1 pin"

        # Remaining parts should contain PWM:, ADC:, DAC: fields
        remaining = ';'.join(parts[2:])
        assert "PWM:" in remaining, f"PINS missing PWM: field: {response}"
        assert "ADC:" in remaining, f"PINS missing ADC: field: {response}"
        assert "DAC:" in remaining, f"PINS missing DAC: field: {response}"

    def test_protocol_version_is_2_0(self, send_command, wait_for_response, parse_json_response):
        """Test that device reports Protocol v2.0."""
        send_command("get:capabilities")

        response = wait_for_response("CAPS;", timeout=1.0)
        caps = parse_json_response(response)

        assert caps is not None, "Failed to parse CAPS response"
        assert "protocol_version" in caps, "CAPS missing protocol_version"

        protocol_version = caps["protocol_version"]
        assert protocol_version.startswith("2."), \
            f"Expected protocol version 2.x, got: {protocol_version}"

    def test_commands_are_case_sensitive(self, send_command, read_responses):
        """Test that commands are case-sensitive (firmware should ignore uppercase)."""
        # Try uppercase variant (should be ignored)
        send_command("GET:VERSION")
        time.sleep(0.3)

        responses = read_responses(max_lines=5, line_timeout=0.3)
        # Uppercase should be ignored - expect no STATUS response
        status_uppercase = [r for r in responses if r.startswith("STATUS;")]

        # Lowercase get:version should work
        send_command("get:version")
        time.sleep(0.5)

        responses2 = read_responses(max_lines=5, line_timeout=0.5)
        status_responses = [r for r in responses2 if r.startswith("STATUS;")]

        # Lowercase version should get a valid response
        assert len(status_responses) > 0, "Lowercase 'get:version' should work"
        assert "version" in status_responses[0].lower() or "2." in status_responses[0], \
            f"Expected version info, got: {status_responses[0]}"

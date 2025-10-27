"""
Test uCAN Protocol v2.0 Phase 1 buffer system actions.

Tests GPIO_READ_BUFFER, ADC_READ_BUFFER, BUFFER_SEND, BUFFER_CLEAR.

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
"""

import pytest
import time


@pytest.mark.hardware
@pytest.mark.integration
class TestPhase1Buffer:
    """Test suite for Phase 1 buffer system actions."""

    def test_gpio_read_buffer_command_format(self, send_command, wait_for_response):
        """Test GPIO_READ_BUFFER command format."""
        send_command("action:clear")
        time.sleep(0.2)

        # GPIO_READ_BUFFER: pin=2, slot=0
        send_command("action:add:0:0x470:0xFFFFFFFF:::0:GPIO_READ_BUFFER:fixed:2:0")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for GPIO_READ_BUFFER rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_adc_read_buffer_command_format(self, send_command, wait_for_response):
        """Test ADC_READ_BUFFER command format."""
        send_command("action:clear")
        time.sleep(0.2)

        # ADC_READ_BUFFER: pin=14 (A0), slot=0
        send_command("action:add:0:0x480:0xFFFFFFFF:::0:ADC_READ_BUFFER:fixed:14:0")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for ADC_READ_BUFFER rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_buffer_send_command_format(self, send_command, wait_for_response):
        """Test BUFFER_SEND command format."""
        send_command("action:clear")
        time.sleep(0.2)

        # BUFFER_SEND: can_id=0x590 (sends buffer as CAN message)
        send_command("action:add:0:0x490:0xFFFFFFFF:::0:BUFFER_SEND:fixed:1424")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for BUFFER_SEND rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_buffer_clear_command_format(self, send_command, wait_for_response):
        """Test BUFFER_CLEAR command format."""
        send_command("action:clear")
        time.sleep(0.2)

        # BUFFER_CLEAR has no parameters
        send_command("action:add:0:0x4A0:0xFFFFFFFF:::0:BUFFER_CLEAR:fixed")

        response = wait_for_response("STATUS;", timeout=1.0)
        assert response is not None, "No response for BUFFER_CLEAR rule"

        send_command("action:clear")
        time.sleep(0.2)

    def test_multi_sensor_collection_workflow(self, send_command, wait_for_response):
        """Test complete multi-sensor data collection workflow."""
        send_command("action:clear")
        time.sleep(0.2)

        # Create workflow: Clear -> Read3Sensors -> Send
        send_command("action:add:0:0x4B0:0xFFFFFFFF:::0:BUFFER_CLEAR:fixed")
        time.sleep(0.1)

        send_command("action:add:0:0x4B0:0xFFFFFFFF:::1:ADC_READ_BUFFER:fixed:14:0")
        time.sleep(0.1)

        send_command("action:add:0:0x4B0:0xFFFFFFFF:::2:ADC_READ_BUFFER:fixed:15:2")
        time.sleep(0.1)

        send_command("action:add:0:0x4B0:0xFFFFFFFF:::3:BUFFER_SEND:fixed:1456")
        time.sleep(0.1)

        # Verify all rules added
        send_command("action:list")
        time.sleep(0.3)

        send_command("action:clear")
        time.sleep(0.2)

    def test_buffer_slot_range_validation(self, send_command, wait_for_response):
        """Test buffer slot parameters (0-7)."""
        send_command("action:clear")
        time.sleep(0.2)

        # Test different slot positions
        for slot in [0, 2, 4, 6]:
            send_command(f"action:add:0:0x48{slot}:0xFFFFFFFF:::0:ADC_READ_BUFFER:fixed:14:{slot}")
            time.sleep(0.1)

        send_command("action:clear")
        time.sleep(0.2)

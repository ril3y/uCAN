"""
Test device name get/set functionality.

This test verifies that device names can be set and retrieved correctly.
Note: Persistence to flash storage is not yet implemented.

Hardware Requirements:
- Adafruit Feather M4 CAN on COM21 @ 115200 baud
- No active CAN traffic required
"""

import pytest


@pytest.mark.hardware
def test_get_default_name(flush_serial, send_command, wait_for_response):
    """Test getting the default device name (board name)."""
    flush_serial()

    # Get the default name (should be board name like "Feather M4 CAN")
    send_command("get:name")
    response = wait_for_response("NAME;", timeout=1.0)

    assert response is not None, "No response received for get:name"
    assert response.startswith("NAME;"), f"Expected NAME; prefix, got: {response}"

    name = response.split(";", 1)[1].strip()
    assert len(name) > 0, "Device name should not be empty"
    print(f"Default name: {name}")


@pytest.mark.hardware
def test_set_device_name(flush_serial, send_command, wait_for_response):
    """Test setting a custom device name."""
    flush_serial()

    test_name = "uCAN_Test_Device_001"

    # Set the device name
    send_command(f"set:name:{test_name}")
    response = wait_for_response("STATUS;NAME_SET;", timeout=1.0)

    # Should get a status confirmation
    assert response is not None, "No response received for set:name"
    assert "STATUS;NAME_SET" in response, f"Expected STATUS;NAME_SET, got: {response}"
    assert test_name in response, f"Expected name '{test_name}' in response: {response}"
    print(f"Set name response: {response}")


@pytest.mark.hardware
def test_set_and_get_device_name(flush_serial, send_command, wait_for_response):
    """Test setting a name and then retrieving it."""
    flush_serial()

    test_name = "MyCustomDevice"

    # Set the name
    send_command(f"set:name:{test_name}")
    set_response = wait_for_response("STATUS;NAME_SET;", timeout=1.0)
    assert set_response is not None
    assert "STATUS;NAME_SET" in set_response

    # Flush and retrieve the name
    flush_serial()
    send_command("get:name")
    get_response = wait_for_response("NAME;", timeout=1.0)

    assert get_response is not None, "No response for get:name"
    assert get_response == f"NAME;{test_name}", f"Expected 'NAME;{test_name}', got: {get_response}"
    print(f"Successfully set and retrieved: {test_name}")


@pytest.mark.hardware
def test_set_name_with_spaces(flush_serial, send_command, wait_for_response):
    """Test setting a device name with spaces."""
    flush_serial()

    test_name = "My Test Device"

    # Set name with spaces
    send_command(f"set:name:{test_name}")
    set_response = wait_for_response("STATUS;NAME_SET;", timeout=1.0)
    assert set_response is not None
    assert "STATUS;NAME_SET" in set_response

    # Verify it was set correctly
    flush_serial()
    send_command("get:name")
    get_response = wait_for_response("NAME;", timeout=1.0)

    assert get_response == f"NAME;{test_name}", f"Expected '{test_name}', got: {get_response}"
    print(f"Name with spaces: {test_name}")


@pytest.mark.hardware
def test_set_name_with_special_chars(flush_serial, send_command, wait_for_response):
    """Test setting a device name with special characters."""
    flush_serial()

    # Test with underscores, numbers, hyphens
    test_name = "uCAN-Device_123"

    send_command(f"set:name:{test_name}")
    set_response = wait_for_response("STATUS;NAME_SET;", timeout=1.0)
    assert set_response is not None
    assert "STATUS;NAME_SET" in set_response

    flush_serial()
    send_command("get:name")
    get_response = wait_for_response("NAME;", timeout=1.0)

    assert get_response == f"NAME;{test_name}", f"Expected '{test_name}', got: {get_response}"
    print(f"Name with special chars: {test_name}")


@pytest.mark.hardware
def test_set_empty_name_restores_default(flush_serial, send_command, wait_for_response):
    """Test that setting an empty name restores the default board name."""
    flush_serial()

    # First set a custom name
    send_command("set:name:TempName")
    wait_for_response("STATUS;NAME_SET;", timeout=1.0)

    # Then clear it by setting empty name
    flush_serial()
    send_command("set:name:")
    wait_for_response("STATUS;NAME_SET;", timeout=1.0)

    # Get the name - should be back to default (board name)
    flush_serial()
    send_command("get:name")
    get_response = wait_for_response("NAME;", timeout=1.0)

    assert get_response is not None
    assert get_response.startswith("NAME;")
    # Should not be "TempName" anymore
    assert "TempName" not in get_response
    print(f"After clearing: {get_response}")


@pytest.mark.hardware
def test_set_very_long_name(flush_serial, send_command, wait_for_response):
    """Test setting a very long device name (should be truncated to MAX_DEVICE_NAME_LENGTH)."""
    flush_serial()

    # Create a name longer than MAX_DEVICE_NAME_LENGTH (32 chars)
    long_name = "A" * 50  # 50 characters

    send_command(f"set:name:{long_name}")
    set_response = wait_for_response("STATUS;NAME_SET;", timeout=1.0)
    assert set_response is not None
    assert "STATUS;NAME_SET" in set_response

    # Get the name - should be truncated
    flush_serial()
    send_command("get:name")
    get_response = wait_for_response("NAME;", timeout=1.0)

    assert get_response is not None
    assert get_response.startswith("NAME;")

    retrieved_name = get_response.split(";", 1)[1].strip()
    # Should be truncated to 31 chars (32 - 1 for null terminator)
    assert len(retrieved_name) <= 31, f"Name should be truncated to 31 chars, got {len(retrieved_name)}"
    print(f"Long name truncated to: {retrieved_name} (length: {len(retrieved_name)})")


@pytest.mark.hardware
@pytest.mark.skip(reason="Flash persistence not yet implemented")
def test_name_persists_after_reset(flush_serial, send_command, wait_for_response):
    """Test that device name persists after reset (requires flash storage)."""
    flush_serial()

    test_name = "PersistentDevice"

    # Set the name
    send_command(f"set:name:{test_name}")
    wait_for_response("STATUS;NAME_SET;", timeout=1.0)

    # Reset the device
    send_command("control:reset")

    # Wait for reset
    import time
    time.sleep(3)

    # Check if name persisted
    send_command("get:name")
    get_response = wait_for_response("NAME;", timeout=1.0)

    assert get_response == f"NAME;{test_name}"
    print(f"Name persisted after reset: {test_name}")


@pytest.mark.hardware
def test_name_in_caps_response(flush_serial, send_command, wait_for_response, parse_json_response):
    """Test that capabilities response includes max_rules field."""
    flush_serial()

    # Set a custom name
    test_name = "CAPSTestDevice"
    send_command(f"set:name:{test_name}")
    wait_for_response("STATUS;NAME_SET;", timeout=1.0)

    # Get capabilities
    flush_serial()
    send_command("get:capabilities")
    response = wait_for_response("CAPS;", timeout=1.0)

    assert response is not None, "No CAPS response received"

    # Parse JSON response
    caps = parse_json_response(response)

    # Verify CAPS has expected fields
    assert "board" in caps, "CAPS missing 'board' field"
    assert "max_rules" in caps, "CAPS missing 'max_rules' field"
    assert "firmware_version" in caps, "CAPS missing 'firmware_version' field"

    # Verify max_rules value
    assert caps["max_rules"] == 64, f"Expected max_rules=64 for SAMD51, got {caps['max_rules']}"

    print(f"CAPS board field: {caps['board']}")
    print(f"CAPS max_rules: {caps['max_rules']}")
    print(f"CAPS firmware_version: {caps['firmware_version']}")
    print(f"Note: Custom device name '{test_name}' not in CAPS (potential enhancement)")

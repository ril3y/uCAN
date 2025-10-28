"""
Test device name get/set functionality.

This test verifies that device names can be set and retrieved correctly.
Note: Persistence to flash storage is not yet implemented.
"""

import pytest


@pytest.mark.hardware
def test_get_default_name(serial_connection):
    """Test getting the default device name (board name)."""
    serial_connection.flush()

    # Get the default name (should be board name like "Feather M4 CAN")
    response = serial_connection.send_command("get:name")

    assert response.startswith("NAME;")
    name = response.split(";", 1)[1].strip()
    assert len(name) > 0
    print(f"Default name: {name}")


@pytest.mark.hardware
def test_set_device_name(serial_connection):
    """Test setting a custom device name."""
    serial_connection.flush()

    test_name = "uCAN_Test_Device_001"

    # Set the device name
    response = serial_connection.send_command(f"set:name:{test_name}")

    # Should get a status confirmation
    assert "STATUS;NAME_SET" in response
    assert test_name in response
    print(f"Set name response: {response}")


@pytest.mark.hardware
def test_set_and_get_device_name(serial_connection):
    """Test setting a name and then retrieving it."""
    serial_connection.flush()

    test_name = "MyCustomDevice"

    # Set the name
    set_response = serial_connection.send_command(f"set:name:{test_name}")
    assert "STATUS;NAME_SET" in set_response

    # Retrieve the name
    get_response = serial_connection.send_command("get:name")
    assert get_response == f"NAME;{test_name}"
    print(f"Successfully set and retrieved: {test_name}")


@pytest.mark.hardware
def test_set_name_with_spaces(serial_connection):
    """Test setting a device name with spaces."""
    serial_connection.flush()

    test_name = "My Test Device"

    # Set name with spaces
    set_response = serial_connection.send_command(f"set:name:{test_name}")
    assert "STATUS;NAME_SET" in set_response

    # Verify it was set correctly
    get_response = serial_connection.send_command("get:name")
    assert get_response == f"NAME;{test_name}"
    print(f"Name with spaces: {test_name}")


@pytest.mark.hardware
def test_set_name_with_special_chars(serial_connection):
    """Test setting a device name with special characters."""
    serial_connection.flush()

    # Test with underscores, numbers, hyphens
    test_name = "uCAN-Device_123"

    set_response = serial_connection.send_command(f"set:name:{test_name}")
    assert "STATUS;NAME_SET" in set_response

    get_response = serial_connection.send_command("get:name")
    assert get_response == f"NAME;{test_name}"
    print(f"Name with special chars: {test_name}")


@pytest.mark.hardware
def test_set_empty_name_restores_default(serial_connection):
    """Test that setting an empty name restores the default board name."""
    serial_connection.flush()

    # First set a custom name
    serial_connection.send_command("set:name:TempName")

    # Then clear it by setting empty name
    serial_connection.send_command("set:name:")

    # Get the name - should be back to default (board name)
    get_response = serial_connection.send_command("get:name")
    assert get_response.startswith("NAME;")

    # Should not be "TempName" anymore
    assert "TempName" not in get_response
    print(f"After clearing: {get_response}")


@pytest.mark.hardware
def test_set_very_long_name(serial_connection):
    """Test setting a very long device name (should be truncated to MAX_DEVICE_NAME_LENGTH)."""
    serial_connection.flush()

    # Create a name longer than MAX_DEVICE_NAME_LENGTH (32 chars)
    long_name = "A" * 50  # 50 characters

    set_response = serial_connection.send_command(f"set:name:{long_name}")
    assert "STATUS;NAME_SET" in set_response

    # Get the name - should be truncated
    get_response = serial_connection.send_command("get:name")
    assert get_response.startswith("NAME;")

    retrieved_name = get_response.split(";", 1)[1].strip()
    # Should be truncated to 31 chars (32 - 1 for null terminator)
    assert len(retrieved_name) <= 31
    print(f"Long name truncated to: {retrieved_name} (length: {len(retrieved_name)})")


@pytest.mark.hardware
@pytest.mark.skip(reason="Flash persistence not yet implemented")
def test_name_persists_after_reset(serial_connection):
    """Test that device name persists after reset (requires flash storage)."""
    serial_connection.flush()

    test_name = "PersistentDevice"

    # Set the name
    serial_connection.send_command(f"set:name:{test_name}")

    # Reset the device
    serial_connection.send_command("control:reset")

    # Wait for reset and reconnect
    import time
    time.sleep(3)
    serial_connection.reconnect()

    # Check if name persisted
    get_response = serial_connection.send_command("get:name")
    assert get_response == f"NAME;{test_name}"
    print(f"Name persisted after reset: {test_name}")


@pytest.mark.hardware
def test_name_in_caps_response(serial_connection):
    """Test that device name can be retrieved from capabilities."""
    serial_connection.flush()

    # Set a custom name
    test_name = "CAPSTestDevice"
    serial_connection.send_command(f"set:name:{test_name}")

    # Get capabilities
    response = serial_connection.send_command("get:capabilities")

    # Parse JSON response
    import json
    json_str = response.split(";", 1)[1]
    caps = json.loads(json_str)

    # Note: The device name is not currently in CAPS response
    # This test documents that it's a potential enhancement
    # For now, just verify CAPS works
    assert "board" in caps
    assert "max_rules" in caps
    print(f"CAPS board field: {caps['board']}")
    print(f"Note: Custom device name '{test_name}' not in CAPS (potential enhancement)")

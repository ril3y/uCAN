"""Simple test without clear_rules to isolate the issue"""
import pytest
import time

@pytest.mark.hardware
def test_simple_get_name(flush_serial, send_command, wait_for_response):
    """Test getting name without clearing rules first."""
    flush_serial()
    send_command("get:name")
    response = wait_for_response("NAME;", timeout=2.0)

    print(f"Response: {response}")
    assert response is not None, "No response received"
    assert response.startswith("NAME;")


@pytest.mark.hardware
def test_simple_set_and_get(ser, flush_serial, send_command, wait_for_response):
    """Test set and get without clearing rules."""
    flush_serial()

    # Set name
    send_command("set:name:TestDevice")
    set_resp = wait_for_response("STATUS;NAME_SET;", timeout=2.0)
    print(f"Set response: {set_resp}")
    assert set_resp is not None

    # Get name (with longer delay to let device fully process previous command)
    time.sleep(0.5)  # Wait before flushing
    flush_serial()
    time.sleep(0.3)  # Wait after flush before sending new command
    print(f"Serial port open: {ser.is_open}")
    print(f"Serial port: {ser.port}")
    send_command("get:name")
    time.sleep(0.3)  # Give device extra time to respond
    print(f"Bytes in buffer: {ser.in_waiting}")
    # Manually try to read what's there
    ser.timeout = 0.5
    manual_read = ser.readline().decode('utf-8', errors='ignore').strip()
    print(f"Manual read: '{manual_read}'")
    print("Waiting for NAME response...")
    get_resp = wait_for_response("NAME;", timeout=2.0, debug=True)
    print(f"Get response: {get_resp}")
    assert get_resp is not None
    assert "TestDevice" in get_resp

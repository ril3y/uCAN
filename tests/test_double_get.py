"""Test sending get:name twice to isolate the issue"""
import pytest

@pytest.mark.hardware
def test_double_get_name(ser, flush_serial, send_command, wait_for_response):
    """Test getting name twice in a row."""
    # First get:name
    flush_serial()
    print("=== First get:name ===")
    send_command("get:name", debug=True)
    resp1 = wait_for_response("NAME;", timeout=2.0, debug=True)
    print(f"First response: {resp1}")
    assert resp1 is not None

    # Second get:name (WITH flush)
    print("\n=== Second get:name (with flush) ===")
    flush_serial()
    print(f"Bytes in buffer AFTER flush: {ser.in_waiting}")
    send_command("get:name", debug=True)
    # No extra delay - send_command already waits 0.05s
    print(f"Bytes in buffer AFTER send: {ser.in_waiting}")
    resp2 = wait_for_response("NAME;", timeout=2.0, debug=True)
    print(f"Second response: {resp2}")
    assert resp2 is not None

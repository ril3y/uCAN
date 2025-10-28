"""Test if changing timeout is causing the issue"""
import pytest
import time

@pytest.mark.hardware
def test_get_name_without_changing_timeout(ser):
    """Test using fixed timeout throughout - no fixtures."""
    # Set timeout once and never change it
    ser.timeout = 0.3

    # First get:name
    ser.reset_input_buffer()
    time.sleep(0.1)
    print("=== First get:name ===")
    ser.write(b'get:name\n')
    ser.flush()
    time.sleep(0.1)

    # Read without fixture
    for i in range(10):
        line = ser.readline()
        if line:
            decoded = line.decode('utf-8', errors='ignore').strip()
            print(f"  Line {i+1}: {decoded}")
            if 'NAME;' in decoded:
                break

    # Second get:name
    print("\n=== Second get:name ===")
    print(f"Buffer before: {ser.in_waiting}")
    ser.write(b'get:name\n')
    ser.flush()
    time.sleep(0.1)
    print(f"Buffer after: {ser.in_waiting}")

    # Read without fixture
    lines = []
    for i in range(10):
        line = ser.readline()
        if line:
            decoded = line.decode('utf-8', errors='ignore').strip()
            lines.append(decoded)
            print(f"  Line {i+1}: {decoded}")
            if 'NAME;' in decoded:
                break

    assert len(lines) > 0, "No response to second command!"
    assert any('NAME;' in l for l in lines), "No NAME response found!"

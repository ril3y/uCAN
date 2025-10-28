"""Test if reopening the port fixes the issue"""
import pytest
import serial
import time

@pytest.mark.hardware
def test_close_and_reopen(ser):
    """Close the pytest port and open our own."""
    port_name = ser.port
    baud = ser.baudrate

    # Close pytest's port
    ser.close()
    time.sleep(0.5)

    # Open our own
    s = serial.Serial(port_name, baud, timeout=0.3, dsrdtr=False, rtscts=False)
    s.dtr = False
    s.rts = False
    time.sleep(0.5)
    s.reset_input_buffer()

    print("=== First get:name ===")
    s.write(b'get:name\n')
    s.flush()
    time.sleep(0.2)
    print(f"Buffer: {s.in_waiting} bytes")

    line = s.readline()
    if line:
        decoded = line.decode('utf-8', errors='ignore').strip()
        print(f"Response: {decoded}")
        assert 'NAME;' in decoded
    else:
        print("NO RESPONSE")
        assert False, "No response received"

    s.close()

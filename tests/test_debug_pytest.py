"""Debug test to see what's happening with wait_for_response"""
import pytest
import time

@pytest.mark.hardware
def test_debug_name_response(ser, flush_serial, send_command):
    """Debug test to see what responses we get."""
    print("\n=== Starting debug test ===")

    # Clear any old data
    flush_serial()
    print("Buffer flushed")

    # Send get:name command
    print("Sending: get:name")
    send_command("get:name")

    # Read all responses for 1 second
    print("Reading responses...")
    ser.timeout = 0.1
    lines = []
    start = time.time()
    while time.time() - start < 1.5:
        line = ser.readline()
        if line:
            decoded = line.decode('utf-8', errors='ignore').strip()
            lines.append(decoded)
            print(f"  Received: {decoded}")
            if 'NAME;' in decoded:
                print(f"  *** Found NAME response! ***")
                break

    print(f"\nTotal lines read: {len(lines)}")
    print(f"Lines with NAME: {[l for l in lines if 'NAME' in l]}")
    print(f"Lines with STATUS: {[l for l in lines if 'STATUS' in l]}")

    # Now test wait_for_response function
    print("\n=== Testing wait_for_response ===")
    flush_serial()
    send_command("get:name")

    # Manually implement wait_for_response with debug output
    timeout = 1.0
    max_attempts = 50
    ser.timeout = timeout / max_attempts
    print(f"Timeout per attempt: {ser.timeout}s")

    for attempt in range(max_attempts):
        line = ser.readline()
        if not line:
            continue
        decoded = line.decode('utf-8', errors='ignore').strip()
        print(f"  Attempt {attempt+1}: {decoded[:50]}")
        if decoded.startswith("NAME;"):
            print(f"  *** Found NAME at attempt {attempt+1}! ***")
            assert True
            return

    print(f"  !!! No NAME response found after {max_attempts} attempts")
    assert False, "wait_for_response logic didn't find NAME"

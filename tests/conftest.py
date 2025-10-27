"""
Pytest configuration and fixtures for uCAN firmware testing.

This module provides shared fixtures for serial communication testing.
Tests communicate with the firmware over serial to validate protocol compliance.
"""

import pytest
import serial
import time
import json
from typing import Generator, Optional, List


def pytest_addoption(parser):
    """Add command-line options for pytest."""
    parser.addoption(
        "--port",
        action="store",
        default=None,
        help="Serial port to use for testing (e.g., COM21, /dev/ttyACM0)"
    )
    parser.addoption(
        "--baud",
        action="store",
        default=115200,
        type=int,
        help="Baud rate for serial communication (default: 115200)"
    )
    parser.addoption(
        "--timeout",
        action="store",
        default=2.0,
        type=float,
        help="Serial read timeout in seconds (default: 2.0)"
    )


@pytest.fixture(scope="session")
def serial_port(request) -> str:
    """Get the serial port from command line or auto-detect."""
    port = request.config.getoption("--port")

    if port is None:
        # Auto-detect serial port
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())

        if not ports:
            pytest.skip("No serial ports found. Use --port to specify manually.")

        # Try to find uCAN device
        for p in ports:
            # Look for common uCAN identifiers
            if any(keyword in (p.description or "").lower() for keyword in ["feather", "samd51", "can", "pico"]):
                port = p.device
                print(f"\nAuto-detected port: {port} ({p.description})")
                break

        if port is None:
            # Just use the first available port
            port = ports[0].device
            print(f"\nUsing first available port: {port} ({ports[0].description})")

    return port


@pytest.fixture(scope="session")
def baud_rate(request) -> int:
    """Get the baud rate from command line."""
    return request.config.getoption("--baud")


@pytest.fixture(scope="session")
def serial_timeout(request) -> float:
    """Get the serial timeout from command line."""
    return request.config.getoption("--timeout")


@pytest.fixture(scope="function")
def ser(serial_port: str, baud_rate: int, serial_timeout: float) -> Generator[serial.Serial, None, None]:
    """
    Create a serial connection for testing.

    This fixture:
    - Opens the serial port
    - Flushes buffers before each test
    - Closes the port after the test
    - Has function scope so each test gets a clean connection
    """
    # Create serial connection with DTR/RTS control to prevent board reset
    # IMPORTANT: Must explicitly disable DTR/RTS to prevent Arduino auto-reset
    connection = serial.Serial(
        port=serial_port,
        baudrate=baud_rate,
        timeout=serial_timeout,
        write_timeout=serial_timeout,
        dsrdtr=False,  # Disable DTR/DSR handshaking
        rtscts=False   # Disable RTS/CTS handshaking
    )

    # Also explicitly set signals low after opening
    connection.dtr = False
    connection.rts = False

    # Give the device time to settle after opening
    time.sleep(0.5)

    # Simple buffer reset - don't do aggressive draining
    # Aggressive draining can cause the board to stop responding
    connection.reset_input_buffer()
    connection.reset_output_buffer()

    try:
        yield connection
    finally:
        # Cleanup - always close even if test fails
        try:
            connection.reset_input_buffer()
            connection.reset_output_buffer()
        except:
            pass
        try:
            connection.close()
        except:
            pass
        # Give OS time to release the port
        time.sleep(0.2)


@pytest.fixture
def send_command(ser: serial.Serial):
    """
    Fixture that returns a function to send commands to the device.

    Usage:
        send_command("get:status")
        send_command("action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:13")
    """
    def _send(command: str) -> None:
        """Send a command to the device."""
        ser.write(f"{command}\n".encode('utf-8'))
        ser.flush()
        time.sleep(0.05)  # Small delay for command processing

    return _send


@pytest.fixture
def read_response(ser: serial.Serial):
    """
    Fixture that returns a function to read a single response line.

    Returns None if timeout occurs.
    """
    def _read(timeout: Optional[float] = None) -> Optional[str]:
        """Read a single line from the device."""
        old_timeout = ser.timeout
        if timeout is not None:
            ser.timeout = timeout

        try:
            line = ser.readline()
            if line:
                return line.decode('utf-8', errors='ignore').strip()
            return None
        finally:
            ser.timeout = old_timeout

    return _read


@pytest.fixture
def read_responses(ser: serial.Serial):
    """
    Fixture that returns a function to read multiple response lines.

    Reads until timeout or max_lines is reached.
    """
    def _read(max_lines: int = 100, line_timeout: float = 0.5) -> List[str]:
        """Read multiple lines from the device."""
        responses = []
        old_timeout = ser.timeout
        ser.timeout = line_timeout

        try:
            for _ in range(max_lines):
                line = ser.readline()
                if not line:
                    break  # Timeout reached

                decoded = line.decode('utf-8', errors='ignore').strip()
                if decoded:
                    responses.append(decoded)
        finally:
            ser.timeout = old_timeout

        return responses

    return _read


@pytest.fixture
def wait_for_response(ser: serial.Serial):
    """
    Fixture that returns a function to wait for a specific response prefix.

    Useful for waiting for specific message types like "STATUS;", "ACTIONDEF;", etc.
    """
    def _wait(prefix: str, timeout: float = 2.0, max_attempts: int = 50) -> Optional[str]:
        """Wait for a response starting with the given prefix."""
        old_timeout = ser.timeout
        ser.timeout = timeout / max_attempts  # Divide timeout among attempts

        try:
            for _ in range(max_attempts):
                line = ser.readline()
                if not line:
                    continue

                decoded = line.decode('utf-8', errors='ignore').strip()
                if decoded.startswith(prefix):
                    return decoded

            return None  # Timeout - prefix not found
        finally:
            ser.timeout = old_timeout

    return _wait


@pytest.fixture
def parse_json_response():
    """
    Fixture that returns a function to parse JSON from protocol responses.

    Handles responses like:
        ACTIONDEF;{"i":1,"n":"NEOPIXEL",...}
        CAPS;{"board":"Feather M4 CAN",...}
    """
    def _parse(response: str) -> Optional[dict]:
        """Parse JSON from a protocol response."""
        if ';' not in response:
            return None

        parts = response.split(';', 1)
        if len(parts) < 2:
            return None

        try:
            return json.loads(parts[1])
        except json.JSONDecodeError:
            return None

    return _parse


@pytest.fixture
def flush_serial(ser: serial.Serial):
    """
    Fixture that returns a function to flush serial buffers.

    Useful when you want to clear buffers mid-test.
    """
    def _flush():
        """Flush both input and output buffers."""
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)

    return _flush


@pytest.fixture
def get_action_definitions(send_command, read_responses, parse_json_response):
    """
    High-level fixture to retrieve all action definitions from the device.

    Returns a list of parsed JSON objects.
    """
    def _get() -> List[dict]:
        """Get all action definitions."""
        send_command("get:actiondefs")
        time.sleep(0.2)  # Give device time to send all definitions

        responses = read_responses(max_lines=20, line_timeout=0.3)

        action_defs = []
        for response in responses:
            if response.startswith("ACTIONDEF;"):
                parsed = parse_json_response(response)
                if parsed:
                    action_defs.append(parsed)

        return action_defs

    return _get


@pytest.fixture
def verify_status_ok(wait_for_response):
    """
    Fixture that returns a function to verify STATUS;INFO or STATUS;OK response.

    Useful after sending commands that should succeed.
    """
    def _verify(expected_substring: Optional[str] = None, timeout: float = 1.0) -> bool:
        """
        Verify that a STATUS response was received.

        Args:
            expected_substring: Optional substring to check in the status message
            timeout: How long to wait for the status message

        Returns:
            True if status was OK, False otherwise
        """
        response = wait_for_response("STATUS;", timeout=timeout)

        if not response:
            return False

        # Check for error status
        if "STATUS;ERROR" in response:
            return False

        # If we have an expected substring, check for it
        if expected_substring:
            return expected_substring in response

        # Otherwise, just verify we got any non-error status
        return True

    return _verify


@pytest.fixture(autouse=True)
def test_separator():
    """Print separator between tests for easier reading."""
    print("\n" + "=" * 80)
    yield
    print("=" * 80)

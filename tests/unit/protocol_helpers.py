"""
Protocol parsing and validation helper functions for uCAN firmware testing.

This module provides hardware-independent protocol parsing and validation
functions that mirror the firmware's protocol implementation. These are used
by unit tests to verify protocol compliance without requiring physical hardware.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class MessageType(Enum):
    """Protocol message types."""
    CAN_RX = "CAN_RX"
    CAN_TX = "CAN_TX"
    CAN_ERR = "CAN_ERR"
    STATUS = "STATUS"
    STATS = "STATS"
    CAPS = "CAPS"
    PINS = "PINS"
    ACTIONS = "ACTIONS"
    ACTIONDEF = "ACTIONDEF"


class ErrorType(Enum):
    """CAN error types."""
    BUS_OFF = "BUS_OFF"
    ERROR_PASSIVE = "ERROR_PASSIVE"
    ERROR_WARNING = "ERROR_WARNING"
    TX_FAILED = "TX_FAILED"
    RX_OVERFLOW = "RX_OVERFLOW"
    ARBITRATION_LOST = "ARBITRATION_LOST"


class StatusLevel(Enum):
    """Status message levels."""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"


@dataclass
class CANMessage:
    """Represents a parsed CAN message."""
    can_id: int
    data: List[int]
    timestamp: Optional[int] = None
    extended: bool = False
    remote: bool = False

    @property
    def length(self) -> int:
        """Return the data length."""
        return len(self.data)


@dataclass
class StatsMessage:
    """Represents parsed STATS message."""
    rx_count: int
    tx_count: int
    err_count: int
    bus_load: int
    timestamp: int


class ProtocolParseError(Exception):
    """Raised when protocol parsing fails."""
    pass


class CommandValidationError(Exception):
    """Raised when command validation fails."""
    pass


def parse_can_rx(message: str) -> CANMessage:
    """
    Parse CAN_RX message format.

    Format: CAN_RX;{CAN_ID};{DATA};{TIMESTAMP}
    Example: CAN_RX;0x123;01,02,03,04;1234567

    Args:
        message: Raw protocol message string

    Returns:
        CANMessage object with parsed data

    Raises:
        ProtocolParseError: If message format is invalid
    """
    parts = message.split(';')

    if len(parts) < 3:
        raise ProtocolParseError(f"CAN_RX requires at least 3 fields, got {len(parts)}")

    if parts[0] != "CAN_RX":
        raise ProtocolParseError(f"Expected CAN_RX prefix, got {parts[0]}")

    # Parse CAN ID (hex format)
    can_id_str = parts[1].strip()
    try:
        can_id = int(can_id_str, 16)
    except ValueError:
        raise ProtocolParseError(f"Invalid CAN ID format: {can_id_str}")

    # Validate CAN ID range
    if can_id > 0x1FFFFFFF:
        raise ProtocolParseError(f"CAN ID out of range: {can_id_str}")

    extended = can_id > 0x7FF

    # Parse data bytes
    data_str = parts[2].strip()
    data = []

    if data_str:  # Empty data is valid
        data_bytes = data_str.split(',')
        for byte_str in data_bytes:
            try:
                byte_val = int(byte_str.strip(), 16)
                if byte_val > 0xFF:
                    raise ProtocolParseError(f"Data byte out of range: {byte_str}")
                data.append(byte_val)
            except ValueError:
                raise ProtocolParseError(f"Invalid data byte format: {byte_str}")

    # Validate data length
    if len(data) > 8:
        raise ProtocolParseError(f"CAN data length exceeds 8 bytes: {len(data)}")

    # Parse timestamp (optional)
    timestamp = None
    if len(parts) >= 4 and parts[3].strip():
        try:
            timestamp = int(parts[3].strip())
        except ValueError:
            raise ProtocolParseError(f"Invalid timestamp format: {parts[3]}")

    return CANMessage(can_id=can_id, data=data, timestamp=timestamp, extended=extended)


def parse_can_tx(message: str) -> CANMessage:
    """
    Parse CAN_TX message format (same as CAN_RX).

    Format: CAN_TX;{CAN_ID};{DATA};{TIMESTAMP}
    Example: CAN_TX;0x100;01,02,03;1234580
    """
    # Replace prefix and reuse CAN_RX parser
    if not message.startswith("CAN_TX;"):
        raise ProtocolParseError(f"Expected CAN_TX prefix")

    can_rx_message = "CAN_RX;" + message[7:]
    return parse_can_rx(can_rx_message)


def parse_can_err(message: str) -> Dict[str, Any]:
    """
    Parse CAN_ERR message format.

    Format: CAN_ERR;{ERROR_TYPE};{DETAILS};{TIMESTAMP}
    Example: CAN_ERR;TX_FAILED;Arbitration lost;1234590
    """
    parts = message.split(';')

    if len(parts) < 3:
        raise ProtocolParseError(f"CAN_ERR requires at least 3 fields, got {len(parts)}")

    if parts[0] != "CAN_ERR":
        raise ProtocolParseError(f"Expected CAN_ERR prefix, got {parts[0]}")

    error_type = parts[1].strip()

    # Validate error type
    valid_errors = [e.value for e in ErrorType]
    if error_type not in valid_errors:
        raise ProtocolParseError(f"Invalid error type: {error_type}. Valid: {valid_errors}")

    details = parts[2].strip() if len(parts) > 2 else ""

    timestamp = None
    if len(parts) >= 4 and parts[3].strip():
        try:
            timestamp = int(parts[3].strip())
        except ValueError:
            raise ProtocolParseError(f"Invalid timestamp format: {parts[3]}")

    return {
        "error_type": error_type,
        "details": details,
        "timestamp": timestamp
    }


def parse_status(message: str) -> Dict[str, str]:
    """
    Parse STATUS message format.

    Format: STATUS;{LEVEL};{CATEGORY};{MESSAGE}
    Example: STATUS;INFO;Configuration;CAN bitrate changed to 250kbps
    """
    parts = message.split(';', 3)  # Split on first 3 semicolons only

    if len(parts) < 2:
        raise ProtocolParseError(f"STATUS requires at least 2 fields, got {len(parts)}")

    if parts[0] != "STATUS":
        raise ProtocolParseError(f"Expected STATUS prefix, got {parts[0]}")

    level = parts[1].strip()

    # Validate status level
    valid_levels = [s.value for s in StatusLevel]
    if level not in valid_levels:
        raise ProtocolParseError(f"Invalid status level: {level}. Valid: {valid_levels}")

    category = parts[2].strip() if len(parts) > 2 else ""
    message_text = parts[3].strip() if len(parts) > 3 else ""

    return {
        "level": level,
        "category": category,
        "message": message_text
    }


def parse_stats(message: str) -> StatsMessage:
    """
    Parse STATS message format.

    Format: STATS;{RX_COUNT};{TX_COUNT};{ERR_COUNT};{BUS_LOAD};{TIMESTAMP}
    Example: STATS;1234;567;2;45;1234567
    """
    parts = message.split(';')

    if len(parts) != 6:
        raise ProtocolParseError(f"STATS requires exactly 6 fields, got {len(parts)}")

    if parts[0] != "STATS":
        raise ProtocolParseError(f"Expected STATS prefix, got {parts[0]}")

    try:
        rx_count = int(parts[1].strip())
        tx_count = int(parts[2].strip())
        err_count = int(parts[3].strip())
        bus_load = int(parts[4].strip())
        timestamp = int(parts[5].strip())
    except ValueError as e:
        raise ProtocolParseError(f"Invalid numeric field in STATS: {e}")

    # Validate bus load percentage
    if bus_load < 0 or bus_load > 100:
        raise ProtocolParseError(f"Bus load must be 0-100%, got {bus_load}")

    # Validate counts are non-negative
    if rx_count < 0 or tx_count < 0 or err_count < 0:
        raise ProtocolParseError(f"Message counts must be non-negative")

    return StatsMessage(
        rx_count=rx_count,
        tx_count=tx_count,
        err_count=err_count,
        bus_load=bus_load,
        timestamp=timestamp
    )


def validate_send_command(command: str) -> Tuple[int, List[int]]:
    """
    Validate send command format and extract CAN ID and data.

    Format: send:{CAN_ID}:{DATA}
    Example: send:0x123:01,02,03,04

    Returns:
        Tuple of (can_id, data_bytes)

    Raises:
        CommandValidationError: If command format is invalid
    """
    if not command.startswith("send:"):
        raise CommandValidationError("Command must start with 'send:'")

    parts = command[5:].split(':', 1)

    if len(parts) < 2:
        raise CommandValidationError("Missing CAN ID or data in send command")

    can_id_str = parts[0].strip()
    data_str = parts[1].strip()

    # Validate and parse CAN ID
    if not can_id_str:
        raise CommandValidationError("Missing CAN ID in send command")

    try:
        can_id = int(can_id_str, 16)
    except ValueError:
        raise CommandValidationError(f"Invalid CAN ID format: {can_id_str}")

    if can_id > 0x1FFFFFFF:
        raise CommandValidationError(f"CAN ID out of range: {can_id_str}")

    # Parse data bytes
    data = []
    if data_str:
        data_bytes = data_str.split(',')
        for byte_str in data_bytes:
            try:
                byte_val = int(byte_str.strip(), 16)
                if byte_val > 0xFF:
                    raise CommandValidationError(f"Data byte out of range (0-FF): {byte_str}")
                data.append(byte_val)
            except ValueError:
                raise CommandValidationError(f"Invalid hex data: {byte_str}")

    # Validate data length
    if len(data) > 8:
        raise CommandValidationError(f"Too many data bytes (max 8), got {len(data)}")

    return can_id, data


def validate_config_command(command: str) -> Tuple[str, str]:
    """
    Validate config command format and extract parameter and value.

    Format: config:{PARAMETER}:{VALUE}
    Examples:
        config:baudrate:250000
        config:filter:0x123
        config:mode:loopback

    Returns:
        Tuple of (parameter, value)

    Raises:
        CommandValidationError: If command format is invalid
    """
    if not command.startswith("config:"):
        raise CommandValidationError("Command must start with 'config:'")

    parts = command[7:].split(':', 1)

    if len(parts) < 2:
        raise CommandValidationError("Missing parameter or value in config command")

    parameter = parts[0].strip()
    value = parts[1].strip()

    if not parameter:
        raise CommandValidationError("Missing parameter in config command")

    if not value:
        raise CommandValidationError("Missing value in config command")

    # Validate specific config parameters
    valid_params = ["baudrate", "filter", "mode", "timestamp"]
    if parameter not in valid_params:
        raise CommandValidationError(f"Invalid config parameter: {parameter}. Valid: {valid_params}")

    # Validate parameter-specific values
    if parameter == "baudrate":
        try:
            baudrate = int(value)
            valid_baudrates = [125000, 250000, 500000, 1000000]
            if baudrate not in valid_baudrates:
                raise CommandValidationError(f"Invalid baudrate: {baudrate}. Valid: {valid_baudrates}")
        except ValueError:
            raise CommandValidationError(f"Baudrate must be numeric: {value}")

    elif parameter == "mode":
        valid_modes = ["normal", "loopback", "listen"]
        if value not in valid_modes:
            raise CommandValidationError(f"Invalid mode: {value}. Valid: {valid_modes}")

    elif parameter == "timestamp":
        valid_timestamp = ["on", "off"]
        if value not in valid_timestamp:
            raise CommandValidationError(f"Invalid timestamp value: {value}. Valid: {valid_timestamp}")

    elif parameter == "filter":
        try:
            filter_val = int(value, 16)
            if filter_val > 0x1FFFFFFF:
                raise CommandValidationError(f"Filter value out of range: {value}")
        except ValueError:
            raise CommandValidationError(f"Filter must be hex value: {value}")

    return parameter, value


def validate_get_command(command: str) -> str:
    """
    Validate get command format and extract parameter.

    Format: get:{PARAMETER}
    Examples:
        get:version
        get:status
        get:capabilities

    Returns:
        Parameter name

    Raises:
        CommandValidationError: If command format is invalid
    """
    if not command.startswith("get:"):
        raise CommandValidationError("Command must start with 'get:'")

    parameter = command[4:].strip()

    if not parameter:
        raise CommandValidationError("Missing parameter in get command")

    # Validate parameter
    valid_params = ["version", "status", "stats", "capabilities", "pins", "actions", "actiondefs"]
    if parameter not in valid_params:
        raise CommandValidationError(f"Invalid get parameter: {parameter}. Valid: {valid_params}")

    return parameter


def format_can_rx_message(can_id: int, data: List[int], timestamp: int) -> str:
    """
    Format a CAN_RX message according to protocol spec.

    Args:
        can_id: CAN identifier (0x000-0x7FF standard, 0x00000000-0x1FFFFFFF extended)
        data: List of data bytes (0-8 bytes)
        timestamp: Milliseconds since boot

    Returns:
        Formatted protocol message string

    Raises:
        ValueError: If parameters are invalid
    """
    if can_id < 0 or can_id > 0x1FFFFFFF:
        raise ValueError(f"CAN ID out of range: {can_id}")

    if len(data) > 8:
        raise ValueError(f"Data length exceeds 8 bytes: {len(data)}")

    for byte in data:
        if byte < 0 or byte > 0xFF:
            raise ValueError(f"Data byte out of range: {byte}")

    if timestamp < 0:
        raise ValueError(f"Timestamp must be non-negative: {timestamp}")

    # Format data bytes as comma-separated hex
    data_str = ','.join(f"{byte:02X}" for byte in data)

    # Format complete message
    return f"CAN_RX;0x{can_id:X};{data_str};{timestamp}"


def format_can_tx_message(can_id: int, data: List[int], timestamp: int) -> str:
    """
    Format a CAN_TX message according to protocol spec.

    Same format as CAN_RX but with CAN_TX prefix.
    """
    message = format_can_rx_message(can_id, data, timestamp)
    return message.replace("CAN_RX;", "CAN_TX;", 1)


def format_status_message(level: str, category: str, message: str = "") -> str:
    """
    Format a STATUS message according to protocol spec.

    Args:
        level: Status level (INFO, WARN, ERROR, CONNECTED, DISCONNECTED)
        category: Category or subsystem name
        message: Optional message text

    Returns:
        Formatted protocol message string

    Raises:
        ValueError: If parameters are invalid
    """
    valid_levels = [s.value for s in StatusLevel]
    if level not in valid_levels:
        raise ValueError(f"Invalid status level: {level}. Valid: {valid_levels}")

    if message:
        return f"STATUS;{level};{category};{message}"
    elif category:
        return f"STATUS;{level};{category}"
    else:
        return f"STATUS;{level}"


def format_stats_message(rx_count: int, tx_count: int, err_count: int,
                         bus_load: int, timestamp: int) -> str:
    """
    Format a STATS message according to protocol spec.

    Args:
        rx_count: Total received messages
        tx_count: Total transmitted messages
        err_count: Total error events
        bus_load: Bus load percentage (0-100)
        timestamp: Milliseconds since boot

    Returns:
        Formatted protocol message string

    Raises:
        ValueError: If parameters are invalid
    """
    if rx_count < 0 or tx_count < 0 or err_count < 0:
        raise ValueError("Message counts must be non-negative")

    if bus_load < 0 or bus_load > 100:
        raise ValueError(f"Bus load must be 0-100%, got {bus_load}")

    if timestamp < 0:
        raise ValueError(f"Timestamp must be non-negative: {timestamp}")

    return f"STATS;{rx_count};{tx_count};{err_count};{bus_load};{timestamp}"


def is_valid_hex_format(value: str) -> bool:
    """Check if string is valid hexadecimal format (with or without 0x prefix)."""
    hex_pattern = re.compile(r'^(0x)?[0-9A-Fa-f]+$')
    return bool(hex_pattern.match(value))


def normalize_can_id(can_id_str: str) -> int:
    """
    Normalize CAN ID string to integer, handling various formats.

    Accepts: 0x123, 0X123, 123 (all interpreted as hex)
    """
    can_id_str = can_id_str.strip()

    if can_id_str.lower().startswith('0x'):
        return int(can_id_str, 16)
    else:
        # Assume hex even without prefix
        return int(can_id_str, 16)

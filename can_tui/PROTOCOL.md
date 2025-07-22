# CAN TUI Serial Protocol Specification

Version: 1.0  
Status: Draft

## Overview

This document specifies the serial communication protocol between the CAN TUI Monitor and CAN-enabled hardware devices. The protocol is designed to be simple, human-readable, and easy to implement on resource-constrained microcontrollers.

## Design Principles

1. **Text-based**: All communication uses ASCII text for easy debugging
2. **Line-oriented**: Each message is a single line terminated by `\n`
3. **Stateless**: Each message is self-contained
4. **Extensible**: New message types can be added without breaking compatibility

## Message Format

### General Structure

```
<MESSAGE_TYPE>;<FIELD1>;<FIELD2>;...;<FIELDN>
```

- Fields are separated by semicolons (`;`)
- No spaces around separators
- Lines terminated with newline (`\n`)
- Maximum line length: 256 characters

### Data Encoding

- **CAN IDs**: Hexadecimal with `0x` prefix (e.g., `0x123`, `0x1FFFFFFF`)
- **Data bytes**: Hexadecimal pairs, comma-separated (e.g., `01,02,03,FF`)
- **Timestamps**: ISO 8601 format or milliseconds since epoch
- **Text**: UTF-8 encoded, no semicolons allowed

## Message Types (Device to TUI)

### CAN_RX - Received CAN Message

Indicates a CAN message was received from the bus.

```
CAN_RX;<CAN_ID>;<DATA>[;<TIMESTAMP>]
```

**Fields:**
- `CAN_ID`: Message identifier (11-bit or 29-bit)
- `DATA`: 0-8 data bytes
- `TIMESTAMP`: Optional timestamp

**Examples:**
```
CAN_RX;0x123;01,02,03,04,05,06,07,08
CAN_RX;0x1FFFFFFF;AA,BB,CC,DD;1635360000000
CAN_RX;0x7FF;  # Empty data frame
```

### CAN_TX - Transmitted CAN Message

Confirms a CAN message was transmitted to the bus.

```
CAN_TX;<CAN_ID>;<DATA>[;<TIMESTAMP>]
```

Same format as CAN_RX but indicates transmission.

### CAN_ERR - CAN Error

Reports CAN bus errors or device errors.

```
CAN_ERR;<ERROR_CODE>;<ERROR_DESCRIPTION>[;<DETAILS>]
```

**Error Codes:**
- `0x01`: Bus off
- `0x02`: Error passive
- `0x03`: Error warning
- `0x04`: Arbitration lost
- `0x05`: Bit error
- `0x06`: CRC error
- `0x07`: Form error
- `0x08`: Stuff error
- `0x09`: Other error
- `0x10`: Buffer overflow
- `0x11`: Configuration error

**Examples:**
```
CAN_ERR;0x01;Bus off detected
CAN_ERR;0x10;RX buffer overflow;Lost 5 messages
```

### STATUS - Device Status

Reports device status and state changes.

```
STATUS;<STATUS_TYPE>;<STATUS_MESSAGE>[;<DETAILS>]
```

**Status Types:**
- `CONNECTED`: Device ready
- `DISCONNECTED`: Device disconnecting
- `CONFIG`: Configuration change
- `INFO`: Informational message
- `WARNING`: Warning condition
- `ERROR`: Error condition

**Examples:**
```
STATUS;CONNECTED;Device ready;CAN 500kbps
STATUS;CONFIG;Baudrate changed;500000
STATUS;WARNING;High bus load;85% utilization
```

### STATS - Statistics

Periodic statistics updates.

```
STATS;<RX_COUNT>;<TX_COUNT>;<ERROR_COUNT>;<BUS_LOAD>[;<TIMESTAMP>]
```

**Fields:**
- `RX_COUNT`: Messages received
- `TX_COUNT`: Messages transmitted  
- `ERROR_COUNT`: Errors encountered
- `BUS_LOAD`: Bus utilization percentage (0-100)

**Example:**
```
STATS;1523;847;12;45;1635360000000
```

## Commands (TUI to Device)

### send - Transmit CAN Message

```
send:<CAN_ID>:<DATA>
```

**Examples:**
```
send:0x123:01,02,03,04,05,06,07,08
send:0x7FF:
send:0x1FFFFFFF:AA,BB,CC,DD
```

### config - Configuration Commands

```
config:<PARAMETER>:<VALUE>
```

**Parameters:**
- `baudrate`: CAN bus speed in bps
- `mode`: normal, listen, loopback
- `filter`: Set acceptance filter
- `mask`: Set acceptance mask
- `termination`: Enable/disable termination
- `timestamp`: Enable/disable timestamps

**Examples:**
```
config:baudrate:500000
config:mode:listen
config:filter:0x100
config:termination:on
```

### get - Query Device

```
get:<PARAMETER>
```

**Parameters:**
- `status`: Current device status
- `stats`: Current statistics
- `config`: Current configuration
- `version`: Firmware version

**Examples:**
```
get:status
get:version
```

### control - Device Control

```
control:<ACTION>
```

**Actions:**
- `reset`: Reset device
- `clear`: Clear buffers/counters
- `start`: Start CAN operation
- `stop`: Stop CAN operation

## Implementation Guidelines

### For Hardware Developers

1. **Startup Sequence**
   ```
   STATUS;CONNECTED;MyDevice v1.0;CAN ready
   ```

2. **Error Handling**
   - Report all CAN errors via CAN_ERR
   - Use STATUS for non-CAN errors
   - Never silently drop messages

3. **Buffering**
   - Implement TX/RX buffers if possible
   - Report buffer overflows
   - Consider flow control for high-speed buses

4. **Timing**
   - Process serial commands promptly
   - Prioritize CAN traffic over serial
   - Add timestamps if accurate timing available

### For TUI Developers

1. **Parsing**
   - Be tolerant of extra fields (forward compatibility)
   - Validate message format but don't crash
   - Handle partial messages gracefully

2. **Error Recovery**
   - Reconnect on connection loss
   - Clear partial data on errors
   - Provide clear error messages

3. **Performance**
   - Buffer writes to serial port
   - Process messages asynchronously
   - Update UI at reasonable rate (10-30 Hz)

## Example Communication Session

```
# Device startup
> STATUS;CONNECTED;RPICAN v1.0;Ready
> STATUS;CONFIG;CAN initialized;500kbps

# TUI configures device
< config:timestamp:on
> STATUS;CONFIG;Timestamps enabled

# Normal operation
> CAN_RX;0x123;01,02,03,04;1635360000100
> CAN_RX;0x456;AA,BB,CC,DD,EE,FF;1635360000150
< send:0x789:11,22,33
> CAN_TX;0x789;11,22,33;1635360000200

# Error condition
> CAN_ERR;0x02;Error passive mode
> STATUS;WARNING;High error rate

# Query stats
< get:stats
> STATS;1000;500;25;30;1635360001000
```

## Version History

- **1.0** (2024-01): Initial specification

## Future Extensions

Potential additions for v2.0:
- Binary protocol mode for efficiency
- CAN FD support
- ISO-TP (ISO 15765-2) support
- J1939 specific messages
- Compression for high-volume data
- Bidirectional flow control
# uCAN Protocol Specification

**Version:** 2.0
**Status:** ✅ Current - Documents Implemented Features
**Last Updated:** 2025-01-27
**Firmware Compatibility:** v2.0+

**Phase 1 Integrated (2025-01-27):**
- ✅ I2C actions (I2C_WRITE, I2C_READ_BUFFER)
- ✅ PWM_CONFIGURE (frequency/resolution control)
- ✅ Data buffer system (8-byte multi-sensor buffer)
- ✅ Enhanced GPIO/ADC read actions (GPIO_READ_BUFFER, ADC_READ_BUFFER)
- ✅ Buffer management (BUFFER_SEND, BUFFER_CLEAR)
- ✅ Enhanced pin validation with runtime allocation tracking

---

## Table of Contents

1. [Overview](#overview)
2. [Connection Setup](#connection-setup)
3. [Message Format](#message-format)
4. [Device → Host Messages](#device--host-messages)
5. [Host → Device Commands](#host--device-commands)
6. [Action Definition System](#action-definition-system)
7. [CAN Message Handling](#can-message-handling)
8. [Error Handling](#error-handling)
9. [Complete Command Reference](#complete-command-reference)

---

## Overview

The uCAN protocol is a text-based, line-oriented serial protocol for USB-to-CAN bridge communication. It provides:

- Real-time CAN message transmission and reception
- Dynamic capability discovery
- Configurable action-based automation
- Hardware-agnostic design (works with RP2040, SAMD51, ESP32, STM32)

**Key Design Principles:**
- Human-readable text format (not binary)
- Line-oriented (newline-terminated messages)
- Semicolon-delimited fields
- JSON for complex structured data
- Self-describing via capability queries

**Hexadecimal Format Convention:**
- Hexadecimal values use `0x` prefix
- Examples in this document show lowercase hex (e.g., `0x100`, `0xff`)
- **Implementations MAY output uppercase or lowercase** (case-insensitive)
- Parsers MUST accept both uppercase and lowercase hex values
- Arduino firmware outputs uppercase (e.g., `0x100` becomes `0X100`)

---

## Connection Setup

### Serial Parameters

```
Baud Rate: 115200 (default)
Data Bits: 8
Parity: None
Stop Bits: 1
Flow Control: None (IMPORTANT!)
```

### Opening the Connection

**Important:** When opening the serial port, you MUST disable DTR/RTS handshaking to prevent the board from entering a reset loop or partial reset state.

**Example (Web Serial API):**
```javascript
await port.open({
  baudRate: 115200,
  flowControl: 'none'  // Critical!
});

// Explicitly disable control signals
await port.setSignals({
  dataTerminalReady: false,
  requestToSend: false
});
```

**Example (Python pySerial):**
```python
import serial

ser = serial.Serial(
    port='/dev/ttyACM0',
    baudrate=115200,
    timeout=1,
    dsrdtr=False,  # Disable DTR
    rtscts=False   # Disable RTS
)
```

### Connection Sequence

When the board powers on or resets, it automatically:

1. **Initializes CAN bus** in normal mode (not listen-only)
2. **Starts with default bitrate** (typically 500kbps, platform-dependent)
3. **Enables timestamps** on all messages
4. **Sends startup STATUS message**

**You DO NOT need to send:** `config:mode:normal`, `config:timestamp:on` - these happen automatically!

### Recommended Startup Commands

After connection, send these commands to discover board capabilities:

```
get:capabilities
get:actiondefs
```

**Example Startup Sequence:**
```
→ Host connects to /dev/ttyACM0 @ 115200
← STATUS;CONNECTED;SAMD51_CAN;SAMD51_CAN v2.0 @ 500kbps

→ get:capabilities
← CAPS;{"board":"Adafruit Feather M4 CAN","chip":"SAMD51",...}

→ get:actiondefs
← ACTIONDEF;{"i":1,"n":"GPIO_SET",...}
← ACTIONDEF;{"i":2,"n":"GPIO_CLEAR",...}
← ACTIONDEF;{"i":3,"n":"GPIO_TOGGLE",...}
... (more action definitions)
```

---

## Message Format

All messages are **line-oriented** and **semicolon-delimited**.

### General Structure

```
MESSAGE_TYPE;FIELD1;FIELD2;FIELD3;...
```

- Each message ends with `\n` (newline)
- Fields are separated by `;` (semicolon)
- No spaces around delimiters (unless part of field value)
- Case-sensitive message types

### Timestamps

CAN messages include timestamps in milliseconds since boot:

```
CAN_RX;0x123;01,02,03,04;1234567
       ^^^^^ ^^^^^^^^^^^^ ^^^^^^^
       CAN ID  Data bytes  Timestamp (ms)
```

---

## Device → Host Messages

These are messages sent FROM the uCAN device TO the host computer.

### CAN_RX - Received CAN Message

Format: `CAN_RX;{CAN_ID};{DATA};{TIMESTAMP}`

**Example:**
```
CAN_RX;0x500;FF,00,00,C8;1234567
```

**Fields:**
- `CAN_ID`: Hexadecimal CAN identifier (0x000 - 0x7FF for standard, 0x00000000 - 0x1FFFFFFF for extended)
- `DATA`: Comma-separated hexadecimal bytes (up to 8 bytes for standard CAN, up to 64 for CAN FD)
- `TIMESTAMP`: Milliseconds since boot (32-bit unsigned)

**Empty Data:**
```
CAN_RX;0x123;;1234567
```

### CAN_TX - Transmitted CAN Message

Format: `CAN_TX;{CAN_ID};{DATA};{TIMESTAMP}`

Sent when the device successfully transmits a message to the CAN bus.

**Example:**
```
CAN_TX;0x100;01,02,03;1234580
```

### CAN_ERR - CAN Bus Error

Format: `CAN_ERR;{ERROR_TYPE};{DETAILS};{TIMESTAMP}`

**Error Types:**
- `BUS_OFF` - Bus-off state (too many errors)
- `ERROR_PASSIVE` - Error passive state
- `ERROR_WARNING` - Error warning state
- `TX_FAILED` - Transmission failed
- `RX_OVERFLOW` - Receive buffer overflow
- `ARBITRATION_LOST` - Lost arbitration during transmission

**Example:**
```
CAN_ERR;TX_FAILED;Arbitration lost;1234590
CAN_ERR;RX_OVERFLOW;Buffer full;1234600
```

### STATUS - Device Status Update

Format: `STATUS;{LEVEL};{CATEGORY};{MESSAGE}`

**Levels:**
- `INFO` - Informational message
- `WARN` - Warning (non-critical)
- `ERROR` - Error condition
- `CONNECTED` - Device connected/initialized
- `DISCONNECTED` - Device disconnected

**Examples:**
```
STATUS;CONNECTED;SAMD51_CAN;SAMD51_CAN v2.0 @ 500kbps
STATUS;INFO;Configuration;CAN bitrate changed to 250kbps
STATUS;ERROR;CAN;Failed to initialize CAN controller
STATUS;INFO;Rule added;ID: 1
```

### STATS - Statistics Report

Format: `STATS;{RX_COUNT};{TX_COUNT};{ERR_COUNT};{BUS_LOAD};{TIMESTAMP}`

Sent periodically (typically every 1000ms) or on request via `get:stats`.

**Example:**
```
STATS;1234;567;2;45;1234567
      ^^^^ ^^^ ^ ^^ ^^^^^^^
      RX   TX  Err Load% Time
```

**Fields:**
- `RX_COUNT`: Total received messages since boot
- `TX_COUNT`: Total transmitted messages since boot
- `ERR_COUNT`: Total error events since boot
- `BUS_LOAD`: Estimated bus load percentage (0-100)
- `TIMESTAMP`: Milliseconds since boot

### CAPS - Capabilities Report

Format: `CAPS;{JSON}`

Sent in response to `get:capabilities`. Provides complete board information.

**Example:**
```json
CAPS;{
  "board": "Adafruit Feather M4 CAN",
  "chip": "SAMD51",
  "clock_mhz": 120,
  "flash_kb": 512,
  "ram_kb": 192,
  "can": {
    "controllers": 1,
    "max_bitrate": 1000000,
    "fd_capable": false,
    "filters": 32
  },
  "gpio": {
    "total": 23,
    "pwm": 16,
    "adc": 8,
    "dac": 2
  },
  "max_rules": 64,
  "features": ["neopixel", "action_system", "rules_engine"],
  "protocol_version": "2.0",
  "firmware_version": "2.0.0"
}
```

**Field Descriptions:**

**Top-Level:**
- `board` (string): Human-readable board name
- `chip` (string): Microcontroller family (SAMD51, RP2040, ESP32, STM32)
- `clock_mhz` (number): CPU clock speed in MHz
- `flash_kb` (number): Flash memory size in kilobytes
- `ram_kb` (number): RAM size in kilobytes
- `max_rules` (number): Maximum number of action rules supported (platform-specific: RP2040=16, SAMD51=64, ESP32=32)
- `protocol_version` (string): Protocol version (e.g., "2.0")
- `firmware_version` (string): Firmware version (e.g., "2.0.0")

**CAN Object:**
- `controllers` (number): Number of CAN peripherals
- `max_bitrate` (number): Maximum supported bitrate in bps
- `fd_capable` (boolean): CAN FD support
- `filters` (number): Number of hardware CAN ID filters

**GPIO Object:**
- `total` (number): Total GPIO pins available
- `pwm` (number): PWM-capable pins
- `adc` (number): Analog input pins
- `dac` (number): Digital-to-analog converter pins

**Features Array:**
Common features: `"neopixel"`, `"action_system"`, `"rules_engine"`, `"flash_storage"`, `"I2C"`, `"wifi"`, `"bluetooth"`

### PINS - Pin Capabilities

Format: `PINS;{TOTAL};PWM:{PWM_COUNT};ADC:{ADC_COUNT};DAC:{DAC_COUNT}`

**Example:**
```
PINS;23;PWM:16;ADC:8;DAC:2
```

### ACTIONS - Available Actions

Format: `ACTIONS;{ACTION1},{ACTION2},{ACTION3},...`

Comma-separated list of action names supported by this board.

**Example (Phase 1 firmware):**
```
ACTIONS;GPIO_SET,GPIO_CLEAR,GPIO_TOGGLE,PWM_SET,NEOPIXEL,CAN_SEND,CAN_SEND_PERIODIC,PWM_CONFIGURE,I2C_WRITE,I2C_READ_BUFFER,GPIO_READ_BUFFER,ADC_READ_BUFFER,BUFFER_SEND,BUFFER_CLEAR
```

### ACTIONDEF - Action Definition (Detailed)

Format: `ACTIONDEF;{JSON}`

This is the **most important message type for UI builders**. Each ACTIONDEF describes one available action and how to configure it.

**Complete Example:**
```json
ACTIONDEF;{
  "i": 1,
  "n": "GPIO_SET",
  "d": "Set GPIO pin HIGH",
  "c": "GPIO",
  "trig": "can_msg",
  "p": [
    {
      "n": "pin",
      "t": 0,
      "b": 0,
      "o": 0,
      "l": 8,
      "r": "0-255",
      "role": "action_param",
      "label": "GPIO Pin Number",
      "hint": "Pin to control (e.g., 13 for onboard LED)"
    }
  ]
}
```

**Field-by-Field Explanation:**

#### Action-Level Fields

| Field | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `i` | number | Action ID (unique identifier, matches enum) | `1`, `7`, `15` |
| `n` | string | Action name (uppercase, used in commands) | `"GPIO_SET"`, `"NEOPIXEL"`, `"PWM_SET"` |
| `d` | string | Human-readable description | `"Set GPIO pin HIGH"` |
| `c` | string | Category for UI grouping | `"GPIO"`, `"Display"`, `"Communication"`, `"Sensor"` |
| `trig` | string | Trigger type (how rule is activated) | `"can_msg"`, `"periodic"`, `"gpio"`, `"manual"` |
| `p` | array | Parameters array (can be empty) | See parameter fields below |

#### Trigger Types Explained

The `trig` field tells you **how a rule using this action is triggered**:

- **`"can_msg"`** (Most Common)
  - Rule triggers when a specific CAN message is received
  - UI should show: "CAN ID to Match: [____]"
  - Example: "When CAN ID 0x500 is received, set NeoPixel color"

- **`"periodic"`**
  - Rule triggers on a timer
  - UI should show: "Interval (ms): [____]" (from trigger_param)
  - CAN ID field may be used for OUTPUT (what to send)
  - Example: "Every 100ms, send CAN message with ID 0x600"

- **`"gpio"`**
  - Rule triggers when a GPIO pin changes state
  - UI should show: "Trigger Pin: [____]" and "Edge: [RISING/FALLING/BOTH]"
  - Example: "When button on pin 13 is pressed, send CAN message"

- **`"manual"`**
  - Rule only executes when explicitly commanded
  - No automatic trigger
  - Example: "Run calibration routine when user clicks 'Calibrate' button"

#### Parameter-Level Fields

Each parameter in the `p` array has these fields:

| Field | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `n` | string | Parameter name (for UI labels) | `"r"`, `"g"`, `"b"`, `"pin"`, `"duty"` |
| `t` | number | Data type (see type table below) | `0` (uint8), `1` (uint16), `6` (float) |
| `b` | number | CAN data byte index (0-7) | `0`, `1`, `2`, ... `7` |
| `o` | number | Bit offset within byte (0-7) | `0`, `4` (for bit-packed data) |
| `l` | number | Bit length (1-8 bits) | `8` (full byte), `1` (single bit) |
| `r` | string | Valid range (min-max) | `"0-255"`, `"0-65535"`, `"-128-127"` |
| `role` | string | Parameter role (see role table below) | `"action_param"`, `"trigger_param"`, `"output_param"` |
| `label` | string (optional) | Human-friendly parameter name for UI display | `"GPIO Pin Number"`, `"Red"`, `"PWM Duty Cycle"` |
| `hint` | string (optional) | Help text/example for UI tooltips | `"Pin to control (e.g., 13)"`, `"0=off, 128=50%, 255=full"` |

**Note:** The `label` and `hint` fields are optional (v2.0+). If not present, UIs should fall back to using the `n` field for display. These fields significantly improve user experience by providing context-specific guidance.

#### Parameter Type Codes (`t` field)

| Code | Type | Description | Size |
|------|------|-------------|------|
| `0` | uint8 | Unsigned 8-bit integer | 1 byte |
| `1` | uint16 | Unsigned 16-bit integer (little-endian) | 2 bytes |
| `2` | uint32 | Unsigned 32-bit integer (little-endian) | 4 bytes |
| `3` | int8 | Signed 8-bit integer | 1 byte |
| `4` | int16 | Signed 16-bit integer (little-endian) | 2 bytes |
| `5` | int32 | Signed 32-bit integer (little-endian) | 4 bytes |
| `6` | float | IEEE 754 32-bit float (little-endian) | 4 bytes |
| `7` | bool | Boolean (single bit) | 1 bit |

#### Parameter Roles (`role` field)

The `role` field categorizes what the parameter is used for:

| Role | Purpose | UI Display | Examples |
|------|---------|------------|----------|
| `"action_param"` | Input to the action itself | In "Action Parameters" section | RGB values, pin numbers, duty cycle |
| `"trigger_param"` | Configures the trigger condition | In "Trigger Configuration" section | Timer interval, GPIO edge type |
| `"output_param"` | Configures the output/response | In "Output Configuration" section | CAN ID to send, response data |

**UI Layout Based on Roles:**

```
┌─────────────────────────────────────┐
│ Trigger Configuration               │
│ • CAN ID to Match: [0x500]          │ ← Always shown for "can_msg" trigger
│ • (trigger_param fields here)       │
├─────────────────────────────────────┤
│ Action Parameters                   │
│ • R (0-255): [__]                   │ ← action_param fields
│ • G (0-255): [__]                   │
│ • B (0-255): [__]                   │
├─────────────────────────────────────┤
│ Output Configuration                │
│ • (output_param fields here)        │ ← Only if present
└─────────────────────────────────────┘
```

### Real-World ACTIONDEF Examples

#### Example 1: GPIO_SET (Simple Action)

```json
{
  "i": 1,
  "n": "GPIO_SET",
  "d": "Set GPIO pin HIGH",
  "c": "GPIO",
  "trig": "can_msg",
  "p": [
    {
      "n": "pin",
      "t": 0,
      "b": 0,
      "o": 0,
      "l": 8,
      "r": "0-255",
      "role": "action_param"
    }
  ]
}
```

**What this means:**
- Action ID 1, name "GPIO_SET", category "GPIO"
- Triggered by incoming CAN messages (`"can_msg"`)
- Has 1 parameter: `pin`
  - Type: uint8 (`t: 0`)
  - Located in CAN data byte 0 (`b: 0`)
  - Uses full byte (`o: 0`, `l: 8`)
  - Valid range: 0-255
  - Used as action parameter (the pin to set HIGH)

**UI should show:**
```
CAN ID to Match: [____]
Pin Number (0-255): [____]
Parameter Source: ○ Fixed  ⦿ From CAN Data
```

**If "Fixed" selected:** User enters pin number (e.g., 13)
**If "From CAN Data" selected:** Pin number comes from byte 0 of received CAN message

#### Example 2: NEOPIXEL (Multi-Parameter Action)

```json
{
  "i": 7,
  "n": "NEOPIXEL",
  "d": "Control onboard NeoPixel RGB LED",
  "c": "Display",
  "trig": "can_msg",
  "p": [
    {"n": "r", "t": 0, "b": 0, "o": 0, "l": 8, "r": "0-255", "role": "action_param"},
    {"n": "g", "t": 0, "b": 1, "o": 0, "l": 8, "r": "0-255", "role": "action_param"},
    {"n": "b", "t": 0, "b": 2, "o": 0, "l": 8, "r": "0-255", "role": "action_param"},
    {"n": "brightness", "t": 0, "b": 3, "o": 0, "l": 8, "r": "0-255", "role": "action_param"}
  ]
}
```

**What this means:**
- 4 parameters: R, G, B, brightness
- All are uint8 type
- Extracted from bytes 0, 1, 2, 3 of CAN data
- All are action parameters (all control the LED)

**With "From CAN Data" mode, one rule can control infinite colors:**
```
Rule: CAN ID 0x500 → NEOPIXEL (candata)

Send: 0x500:FF,00,00,C8  → Red at 200 brightness
Send: 0x500:00,FF,00,C8  → Green at 200 brightness
Send: 0x500:FF,FF,00,C8  → Yellow at 200 brightness
Send: 0x500:80,00,80,FF  → Purple at full brightness
```

#### Example 3: CAN_SEND_PERIODIC (Periodic Trigger)

```json
{
  "i": 15,
  "n": "CAN_SEND_PERIODIC",
  "d": "Send CAN message periodically",
  "c": "Communication",
  "trig": "periodic",
  "p": [
    {"n": "can_id", "t": 1, "b": 0, "o": 0, "l": 16, "r": "0-2047", "role": "output_param"},
    {"n": "interval_ms", "t": 1, "b": 2, "o": 0, "l": 16, "r": "10-60000", "role": "trigger_param"},
    {"n": "data0", "t": 0, "b": 4, "o": 0, "l": 8, "r": "0-255", "role": "output_param"},
    {"n": "data1", "t": 0, "b": 5, "o": 0, "l": 8, "r": "0-255", "role": "output_param"}
  ]
}
```

**What this means:**
- Trigger type is `"periodic"` - NOT triggered by CAN messages!
- Triggered by timer at specified interval
- `interval_ms` (trigger_param): How often to send (in milliseconds)
- `can_id` (output_param): What CAN ID to transmit
- `data0`, `data1` (output_param): What data bytes to send

**UI should show:**
```
Send Interval (ms): [100]        ← trigger_param
CAN ID to Send: [0x600]          ← output_param (NOT "to match"!)
Data Byte 0: [0x12]              ← output_param
Data Byte 1: [0x34]              ← output_param
```

**This creates a rule that sends "0x600:12,34" every 100ms automatically.**

### NAME - Device Name

Format: `NAME;{DEVICE_NAME}`

**Example:**
```
NAME;uCAN_Feather_001
```

### ACTION - Action Execution Report

Format: `ACTION;{RULE_ID};{ACTION_TYPE};{TRIGGER_CAN_ID};{STATUS}`

Sent automatically when a rule is triggered and its action executes.

**Fields:**
- `RULE_ID` (number): The ID of the rule that was triggered
- `ACTION_TYPE` (string): Name of the action that executed (e.g., "GPIO_SET", "NEOPIXEL")
- `TRIGGER_CAN_ID` (hex): The CAN message ID that triggered this rule
- `STATUS` (string): Either "OK" (success) or "FAIL" (error)

**Examples:**
```
ACTION;1;GPIO_SET;0x100;OK
ACTION;5;NEOPIXEL;0x500;OK
ACTION;3;PWM_SET;0x200;FAIL
```

**Use Cases:**
- Debugging: See which rules are actually firing
- UI feedback: Show real-time action execution
- Error detection: Identify failing actions
- Performance monitoring: Track action execution frequency

---

## Host → Device Commands

These are commands sent FROM the host computer TO the uCAN device.

All commands are **case-sensitive** and **colon-delimited**.

### send - Send CAN Message

Format: `send:{CAN_ID}:{DATA}`

Transmits a CAN message immediately.

**Examples:**
```
send:0x123:01,02,03,04
send:0x500:FF,00,00,C8
send:0x100:
```

**Response:**
```
CAN_TX;0x123;01,02,03,04;1234567
```

**Or on error:**
```
STATUS;ERROR;CAN;TX failed
```

### config - Configure Device

#### config:baudrate - Change CAN Bitrate

Format: `config:baudrate:{BITRATE}`

**Supported bitrates:** 125000, 250000, 500000, 1000000 (in bps)

**Example:**
```
config:baudrate:250000
```

**Response:**
```
STATUS;INFO;Configuration;CAN bitrate changed to 250kbps
```

#### config:filter - Set CAN ID Filter

Format: `config:filter:{FILTER_ID}:{MASK}`

Configure hardware CAN ID filtering (reduces CPU load by filtering unwanted messages in hardware).

**Example:**
```
config:filter:0x500:0x700
```

**Response:**
```
STATUS;INFO;Configuration;CAN filter set
```

**Note:** Filter behavior is platform-specific. Check your board's datasheet for exact filter logic.

### get - Query Information

#### get:status - Get Current Status

Format: `get:status`

**Response:**
```
STATUS;INFO;RX:1234 TX:567 ERR:2
```

#### get:version - Get Firmware Version

Format: `get:version`

**Response:**
```
STATUS;INFO;Platform: SAMD51_CAN, Version: 2.0.0, Protocol: 2.0
```

#### get:stats - Get Statistics

Format: `get:stats`

**Response:**
```
STATS;1234;567;2;45;1234567
```

#### get:capabilities - Get Board Capabilities

Format: `get:capabilities`

**Response:** (see CAPS message format above)
```json
CAPS;{
  "board": "Adafruit Feather M4 CAN",
  ...
}
```

#### get:pins - Get Pin Capabilities

Format: `get:pins`

**Response:**
```
PINS;23;PWM:16;ADC:8;DAC:2
```

#### get:actions - Get Action List

Format: `get:actions`

**Response:**
```
ACTIONS;GPIO_SET,GPIO_CLEAR,GPIO_TOGGLE,PWM_SET,NEOPIXEL,CAN_SEND,CAN_SEND_PERIODIC
```

#### get:name - Get Device Name

Format: `get:name`

**Response:**
```
NAME;uCAN_Feather_001
```

#### get:actiondefs - Get All Action Definitions

Format: `get:actiondefs`

**Response:** (multiple ACTIONDEF lines)
```
ACTIONDEF;{"i":1,"n":"GPIO_SET",...}
ACTIONDEF;{"i":2,"n":"GPIO_CLEAR",...}
ACTIONDEF;{"i":3,"n":"GPIO_TOGGLE",...}
...
```

#### get:actiondef - Get Specific Action Definition

Format: `get:actiondef:{ACTION_ID}`

**Example:**
```
get:actiondef:7
```

**Response:**
```
ACTIONDEF;{"i":7,"n":"NEOPIXEL",...}
```

### action:add - Add Action Rule

Format: `action:add:{ID}:{CAN_ID}:{CAN_MASK}:{DATA}:{DATA_MASK}:{DATA_LEN}:{ACTION}:{PARAM_SOURCE}:{PARAMS...}`

This is the **most complex command**. It creates a rule that triggers an action when conditions are met.

**Field Descriptions:**

| Position | Field | Description | Example |
|----------|-------|-------------|---------|
| 0 | Command | Always `action:add` | `action:add` |
| 1 | ID | Rule ID (0 = auto-assign) | `0`, `1`, `2` |
| 2 | CAN_ID | CAN ID to match (hex) | `0x500`, `0x100` |
| 3 | CAN_MASK | CAN ID mask (hex, 0x000 = match any) | `0xFFFFFFFF`, `0x000` |
| 4 | DATA | CAN data pattern to match (hex, comma-separated) | `FF,00`, `` |
| 5 | DATA_MASK | CAN data mask (hex, comma-separated) | `FF,FF`, `` |
| 6 | DATA_LEN | Required CAN data length (0 = any length) | `0`, `4`, `8` |
| 7 | ACTION | Action type name | `GPIO_SET`, `NEOPIXEL` |
| 8 | PARAM_SOURCE | **REQUIRED:** `fixed` or `candata` | `fixed`, `candata` |
| 9+ | PARAMS | Parameter values (only if PARAM_SOURCE = `fixed`) | `13`, `255,128,0,200` |

**CAN Data Matching Fields (DATA, DATA_MASK, DATA_LEN):**

These fields enable **conditional triggering** based on CAN message content, not just CAN ID.

- **DATA**: Expected data pattern (hex bytes, comma-separated)
- **DATA_MASK**: Mask for data comparison (FF = must match, 00 = don't care)
- **DATA_LEN**: Required message length (0 = any length accepted)

**Examples of Data Matching:**
```
DATA:      FF,00
DATA_MASK: FF,FF
Meaning: "Byte 0 must be 0xFF, Byte 1 must be 0x00"

DATA:      80
DATA_MASK: FF
DATA_LEN:  4
Meaning: "Byte 0 must be 0x80, message must be exactly 4 bytes long"

DATA:
DATA_MASK:
DATA_LEN:  0
Meaning: "Match any data (no content filtering)"
```

**PARAM_SOURCE Explained:**

- **`fixed`**: Parameters are specified in the command (positions 9+)
  - Use when you want the same values every time
  - Example: Always set pin 13 HIGH when CAN ID 0x100 is received

- **`candata`**: Parameters are extracted from CAN message data bytes
  - Use when you want dynamic values from the CAN bus
  - Example: Set NeoPixel color based on bytes in CAN message
  - NO parameters after PARAM_SOURCE (extraction defined in ACTIONDEF)

**Examples:**

**Simple Rule (No Data Filtering):**
```
action:add:0:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:13
```
**Meaning:** "When CAN ID 0x100 is received (any data), set GPIO pin 13 HIGH"

**CAN Data Extraction:**
```
action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:candata
```
**Meaning:** "When CAN ID 0x500 is received, set NeoPixel using R=byte0, G=byte1, B=byte2, brightness=byte3"

**Then send:** `send:0x500:FF,00,00,C8` → Red LED at 200 brightness

**Conditional Rule (Data Pattern Match):**
```
action:add:0:0x100:0xFFFFFFFF:FF:FF:1:GPIO_SET:fixed:13
```
**Meaning:** "When CAN ID 0x100 is received AND byte 0 equals 0xFF, set GPIO pin 13 HIGH"

**Multi-Parameter Fixed:**
```
action:add:0:0x600:0xFFFFFFFF:::0:NEOPIXEL:fixed:255:128:0:200
```
**Meaning:** "When CAN ID 0x600 is received, set NeoPixel to orange (255,128,0) at 200 brightness"

**Response:**
```
STATUS;INFO;Rule added;ID: 1
```

### action:remove - Remove Action Rule

Format: `action:remove:{RULE_ID}`

**Example:**
```
action:remove:1
```

**Response:**
```
STATUS;INFO;Rule removed;ID: 1
```

**Aliases:** `action:delete:{RULE_ID}` (same functionality)

### action:edit - Update Existing Rule

Format: `action:edit:{ID}:{CAN_ID}:{CAN_MASK}:{DATA}:{DATA_MASK}:{DATA_LEN}:{ACTION}:{PARAM_SOURCE}:{PARAMS...}`

Updates an existing rule by removing it and adding a new one with the same ID. This preserves the rule ID while allowing parameter changes.

**Field Descriptions:** (Same as `action:add` - see above)

**Examples:**

**Update GPIO pin:**
```
action:edit:1:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:14
```
Changes rule 1 to control pin 14 instead of its previous pin.

**Update NeoPixel color mode:**
```
action:edit:2:0x500:0xFFFFFFFF:::0:NEOPIXEL:fixed:255:0:0:200
```
Changes rule 2 from `candata` mode to fixed red color.

**Update trigger CAN ID:**
```
action:edit:3:0x200:0xFFFFFFFF:::0:GPIO_TOGGLE:candata
```
Changes rule 3 to trigger on CAN ID 0x200 instead of previous ID.

**Response:**
```
STATUS;INFO;Rule updated;ID: 1
```

**Error Cases:**
```
STATUS;ERROR;Rule not found          (if RULE_ID doesn't exist)
STATUS;ERROR;Failed to update rule   (if new rule parameters are invalid)
```

**Important Notes:**
- Rule ID must already exist (use `action:add` for new rules)
- All rule parameters must be provided (same format as `action:add`)
- Atomically removes old rule and adds new one
- If update fails, the old rule is already removed

### action:list - List All Rules

Format: `action:list`

**Response Format:**
```
RULE;{ID};{CAN_ID};{CAN_MASK};{DATA};{DATA_MASK};{DATA_LEN};{ACTION};{PARAM_SOURCE};{PARAMS...}
```

**Field Descriptions:**

| Field | Description |
|-------|-------------|
| ID | Rule ID number |
| CAN_ID | CAN ID to match (hex with 0x prefix) |
| CAN_MASK | CAN ID mask (hex with 0x prefix) |
| DATA | CAN data pattern (hex, comma-separated, empty if no pattern) |
| DATA_MASK | CAN data mask (hex, comma-separated, empty if no mask) |
| DATA_LEN | Required data length (0 = any length) |
| ACTION | Action type name |
| PARAM_SOURCE | Parameter source: `fixed` or `candata` |
| PARAMS | Parameter values (only present if PARAM_SOURCE = `fixed`) |

**Examples:**
```
RULE;1;0x500;0xFFFFFFFF;;;0;NEOPIXEL;candata
RULE;2;0x100;0xFFFFFFFF;;;0;GPIO_SET;fixed;13
RULE;3;0x200;0xFFFFFFFF;FF;FF;1;GPIO_TOGGLE;fixed;14
```

**Explanation:**
- Rule 1: CAN ID 0x500, NeoPixel with data extraction, no data filtering
- Rule 2: CAN ID 0x100, GPIO pin 13, fixed parameter, no data filtering
- Rule 3: CAN ID 0x200, GPIO pin 14, triggers only if byte 0 = 0xFF

### action:clear - Remove All Rules

Format: `action:clear`

**Response:**
```
STATUS;INFO;All rules cleared
```

---

## Action Definition System

### Overview

The action system allows you to program the uCAN board to **automatically respond to CAN messages** without host intervention.

**Key Concepts:**

1. **Actions** - Things the board can do (set GPIO, control NeoPixel, send CAN message, etc.)
2. **Rules** - Conditions that trigger actions (when CAN ID X is received, do action Y)
3. **Parameter Sources** - Where action parameters come from (fixed values or CAN data bytes)

### Parameter Source Modes

#### Fixed Mode (`fixed`)

Parameters are **hardcoded** in the rule.

**Pros:**
- Simple and predictable
- No need to format CAN data specially
- Fast execution

**Cons:**
- Need separate rules for different values
- Less flexible

**Example:** Blink LED on specific pins
```
action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:13
action:add:0:0x200:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:14
action:add:0:0x300:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:15
```

#### CAN Data Mode (`candata`)

Parameters are **extracted from CAN message data bytes**.

**Pros:**
- One rule handles infinite parameter combinations
- Very flexible
- Efficient use of rules

**Cons:**
- Must understand parameter mapping (from ACTIONDEF)
- Sender must format CAN data correctly

**Example:** Dynamic RGB LED control
```
action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:candata

# Now control with any color:
send:0x500:FF,00,00,FF  → Red at full brightness
send:0x500:00,FF,00,80  → Green at 50% brightness
send:0x500:FF,FF,00,FF  → Yellow at full brightness
```

### How Parameter Extraction Works

The `ACTIONDEF` tells you exactly how to format CAN data:

```json
{
  "n": "NEOPIXEL",
  "p": [
    {"n": "r", "b": 0, ...},         // Red from byte 0
    {"n": "g", "b": 1, ...},         // Green from byte 1
    {"n": "b", "b": 2, ...},         // Blue from byte 2
    {"n": "brightness", "b": 3, ...} // Brightness from byte 3
  ]
}
```

**CAN Data Format:**
```
Byte:  0    1    2    3    4    5    6    7
      [R ] [G ] [B ] [Br] [--] [--] [--] [--]
```

**Example:**
```
send:0x500:80,FF,00,C8
            ││ ││ ││ ││
            ││ ││ ││ └└─ Brightness = 0xC8 (200)
            ││ ││ └└─── Blue = 0x00 (0)
            ││ └└───── Green = 0xFF (255)
            └└─────── Red = 0x80 (128)

Result: Orange-ish LED at 200/255 brightness
```

### Bit-Packed Parameters

Some actions use **bit-level extraction** to pack multiple parameters in one byte.

**Example:** 8 boolean switches in 1 byte

```json
{
  "n": "SWITCH_BANK",
  "p": [
    {"n": "sw0", "b": 0, "o": 0, "l": 1, ...},  // Bit 0 of byte 0
    {"n": "sw1", "b": 0, "o": 1, "l": 1, ...},  // Bit 1 of byte 0
    {"n": "sw2", "b": 0, "o": 2, "l": 1, ...},  // Bit 2 of byte 0
    ...
  ]
}
```

**CAN Data:**
```
Byte 0: 0b10101010 = 0xAA
        ││││││││
        │││││││└─ sw0 = 0
        ││││││└── sw1 = 1
        │││││└─── sw2 = 0
        ││││└──── sw3 = 1
        ...
```

---

## Phase 1 Action Reference

This section documents the Phase 1 actions integrated in v2.0. These actions extend the original capabilities with I2C communication, advanced PWM control, and a data buffer system for multi-sensor applications.

### Overview

**Phase 1 introduces 7 new actions:**

| Action | Category | Description | Use Case |
|--------|----------|-------------|----------|
| PWM_CONFIGURE | PWM | Configure PWM with frequency/resolution | Motor control, servo control |
| I2C_WRITE | I2C | Write single byte to I2C device | Set sensor registers |
| I2C_READ_BUFFER | I2C | Read multiple bytes into buffer | Read sensor data |
| GPIO_READ_BUFFER | GPIO | Read digital pin state into buffer | Multi-switch status |
| ADC_READ_BUFFER | Analog | Read analog value (16-bit) into buffer | Multi-sensor data collection |
| BUFFER_SEND | Communication | Send buffer contents as CAN message | Transmit collected data |
| BUFFER_CLEAR | Buffer | Clear data buffer manually | Reset between collection cycles |

**Key Concepts:**

1. **Data Buffer System**: 8-byte shared buffer for collecting data from multiple sensors before transmission
2. **Slot-Based Addressing**: Buffer slots 0-7 for flexible data organization
3. **Chained Actions**: Multiple read actions → BUFFER_SEND creates complex data collection workflows
4. **I2C Integration**: Direct I2C communication for sensor interfacing
5. **Enhanced PWM**: Full control over frequency (1Hz-100kHz) and resolution (8-16 bits)

### PWM_CONFIGURE

Configure PWM output with precise frequency and resolution control.

**Action Definition:**
```json
{
  "i": 8,
  "n": "PWM_CONFIGURE",
  "d": "Configure PWM with frequency and resolution",
  "c": "PWM",
  "trig": "can_msg",
  "p": [
    {
      "n": "pin",
      "t": 0,
      "b": 0,
      "r": "0-255",
      "role": "action_param",
      "label": "PWM Pin Number",
      "hint": "Pin to configure for PWM output"
    },
    {
      "n": "duty",
      "t": 1,
      "b": 1,
      "r": "0-65535",
      "role": "action_param",
      "label": "Duty Cycle",
      "hint": "16-bit duty cycle value (0=0%, 65535=100%)"
    },
    {
      "n": "freq",
      "t": 2,
      "b": 3,
      "r": "1-100000",
      "role": "action_param",
      "label": "Frequency (Hz)",
      "hint": "PWM frequency in Hz (1-100000)"
    }
  ]
}
```

**Parameters:**
- `pin` (uint8, byte 0): PWM-capable pin number
- `duty` (uint16, bytes 1-2): Duty cycle (0-65535, where 65535 = 100%)
- `freq` (uint32, bytes 3-6): Frequency in Hz (1-100,000)

**CAN Data Format:**
```
Byte:  0      1-2        3-6
      [Pin] [Duty_LSB] [Freq_LSB]
            [Duty_MSB] [Freq_MSB]
```

**Examples:**

**Fixed 1kHz servo control:**
```
action:add:0:0x300:0xFFFFFFFF:::0:PWM_CONFIGURE:fixed:9:32768:1000
                                                        ^  ^^^^^  ^^^^
                                                       pin  50%   1kHz
```

**Dynamic motor control:**
```
action:add:0:0x300:0xFFFFFFFF:::0:PWM_CONFIGURE:candata

# Send different speeds:
send:0x300:09,00,40,E8,03,00,00   → Pin 9, 25% duty, 1000Hz
send:0x300:09,00,80,88,13,00,00   → Pin 9, 50% duty, 5000Hz
send:0x300:09,00,C0,40,1F,00,00   → Pin 9, 75% duty, 8000Hz
```

**Use Cases:**
- Precise motor speed control
- Servo positioning
- LED dimming with specific frequencies
- Audio tone generation

### I2C_WRITE

Write a single byte to an I2C device register.

**Action Definition:**
```json
{
  "i": 9,
  "n": "I2C_WRITE",
  "d": "Write byte to I2C device",
  "c": "I2C",
  "trig": "can_msg",
  "p": [
    {
      "n": "addr",
      "t": 0,
      "b": 0,
      "r": "0-127",
      "role": "action_param",
      "label": "I2C Address",
      "hint": "7-bit I2C device address"
    },
    {
      "n": "reg",
      "t": 0,
      "b": 1,
      "r": "0-255",
      "role": "action_param",
      "label": "Register Address",
      "hint": "Device register to write to"
    },
    {
      "n": "value",
      "t": 0,
      "b": 2,
      "r": "0-255",
      "role": "action_param",
      "label": "Value",
      "hint": "Byte value to write"
    }
  ]
}
```

**Parameters:**
- `addr` (uint8, byte 0): 7-bit I2C device address (0-127)
- `reg` (uint8, byte 1): Register address within device
- `value` (uint8, byte 2): Byte value to write

**CAN Data Format:**
```
Byte:  0      1      2
      [Addr] [Reg] [Value]
```

**Examples:**

**Configure sensor (fixed):**
```
action:add:0:0x400:0xFFFFFFFF:::0:I2C_WRITE:fixed:0x68:0x6B:0x00
                                                    ^^^^  ^^^^  ^^^^
                                                    addr  reg   value
```
Writes 0x00 to register 0x6B of I2C device at address 0x68 (typical MPU6050 initialization).

**Dynamic sensor control:**
```
action:add:0:0x400:0xFFFFFFFF:::0:I2C_WRITE:candata

# Control different registers dynamically:
send:0x400:68,6B,00   → MPU6050: Wake up (PWR_MGMT_1 = 0)
send:0x400:68,1C,10   → MPU6050: Set accel range (ACCEL_CONFIG = ±8g)
send:0x400:3C,00,FF   → Different device at 0x3C
```

**Use Cases:**
- Sensor initialization and configuration
- Setting device operating modes
- Writing calibration values
- Controlling I2C peripherals (displays, motor drivers)

### I2C_READ_BUFFER

Read multiple bytes from I2C device into the data buffer.

**Action Definition:**
```json
{
  "i": 10,
  "n": "I2C_READ_BUFFER",
  "d": "Read I2C data into buffer",
  "c": "I2C",
  "trig": "can_msg",
  "p": [
    {
      "n": "addr",
      "t": 0,
      "b": 0,
      "r": "0-127",
      "role": "action_param",
      "label": "I2C Address",
      "hint": "7-bit I2C device address"
    },
    {
      "n": "reg",
      "t": 0,
      "b": 1,
      "r": "0-255",
      "role": "action_param",
      "label": "Register Address",
      "hint": "Starting register to read from"
    },
    {
      "n": "len",
      "t": 0,
      "b": 2,
      "r": "1-8",
      "role": "action_param",
      "label": "Length",
      "hint": "Number of bytes to read (1-8)"
    },
    {
      "n": "slot",
      "t": 0,
      "b": 3,
      "r": "0-7",
      "role": "action_param",
      "label": "Buffer Slot",
      "hint": "Starting buffer slot (0-7)"
    }
  ]
}
```

**Parameters:**
- `addr` (uint8, byte 0): 7-bit I2C device address
- `reg` (uint8, byte 1): Starting register address
- `len` (uint8, byte 2): Number of bytes to read (1-8)
- `slot` (uint8, byte 3): Starting buffer slot (0-7)

**CAN Data Format:**
```
Byte:  0      1      2      3
      [Addr] [Reg] [Len] [Slot]
```

**Examples:**

**Read 6-axis sensor data:**
```
# Rule 1: Read accelerometer X,Y,Z (6 bytes starting at reg 0x3B into slots 0-5)
action:add:0:0x450:0xFFFFFFFF:::0:I2C_READ_BUFFER:fixed:0x68:0x3B:6:0

# Rule 2: Send buffer after read
action:add:0:0x450:0xFFFFFFFF:::1:BUFFER_SEND:fixed:0x500
```

**Multi-sensor workflow:**
```
# Read temperature sensor (2 bytes)
action:add:0:0x460:0xFFFFFFFF:::0:I2C_READ_BUFFER:fixed:0x48:0x00:2:0

# Read humidity sensor (2 bytes)
action:add:0:0x460:0xFFFFFFFF:::1:I2C_READ_BUFFER:fixed:0x40:0x00:2:2

# Send combined data
action:add:0:0x460:0xFFFFFFFF:::2:BUFFER_SEND:fixed:0x550
```

**Use Cases:**
- Reading multi-byte sensor values
- Collecting data from multiple I2C devices
- IMU data acquisition
- Building custom sensor packets

### GPIO_READ_BUFFER

Read digital pin state into buffer.

**Action Definition:**
```json
{
  "i": 11,
  "n": "GPIO_READ_BUFFER",
  "d": "Read GPIO state into buffer",
  "c": "GPIO",
  "trig": "can_msg",
  "p": [
    {
      "n": "pin",
      "t": 0,
      "b": 0,
      "r": "0-255",
      "role": "action_param",
      "label": "GPIO Pin",
      "hint": "Pin to read"
    },
    {
      "n": "slot",
      "t": 0,
      "b": 1,
      "r": "0-7",
      "role": "action_param",
      "label": "Buffer Slot",
      "hint": "Buffer slot to write (0-7)"
    }
  ]
}
```

**Parameters:**
- `pin` (uint8, byte 0): GPIO pin number to read
- `slot` (uint8, byte 1): Buffer slot (0-7) to store result (0x00 = LOW, 0x01 = HIGH)

**CAN Data Format:**
```
Byte:  0      1
      [Pin] [Slot]
```

**Examples:**

**Read 4 switches into buffer:**
```
# Read switch 1 (pin 2) → slot 0
action:add:0:0x470:0xFFFFFFFF:::0:GPIO_READ_BUFFER:fixed:2:0

# Read switch 2 (pin 3) → slot 1
action:add:0:0x470:0xFFFFFFFF:::1:GPIO_READ_BUFFER:fixed:3:1

# Read switch 3 (pin 4) → slot 2
action:add:0:0x470:0xFFFFFFFF:::2:GPIO_READ_BUFFER:fixed:4:2

# Read switch 4 (pin 5) → slot 3
action:add:0:0x470:0xFFFFFFFF:::3:GPIO_READ_BUFFER:fixed:5:3

# Send buffer with all switch states
action:add:0:0x470:0xFFFFFFFF:::4:BUFFER_SEND:fixed:0x570

# Result CAN message 0x570:
# Byte 0: Switch 1 (0x00=off, 0x01=on)
# Byte 1: Switch 2
# Byte 2: Switch 3
# Byte 3: Switch 4
```

**Use Cases:**
- Reading multiple buttons/switches
- Monitoring digital sensor states
- Creating switch panels
- Reading limit switches

### ADC_READ_BUFFER

Read analog pin value (16-bit) into buffer.

**Action Definition:**
```json
{
  "i": 12,
  "n": "ADC_READ_BUFFER",
  "d": "Read ADC value into buffer",
  "c": "Analog",
  "trig": "can_msg",
  "p": [
    {
      "n": "pin",
      "t": 0,
      "b": 0,
      "r": "0-255",
      "role": "action_param",
      "label": "ADC Pin",
      "hint": "Analog pin to read"
    },
    {
      "n": "slot",
      "t": 0,
      "b": 1,
      "r": "0-6",
      "role": "action_param",
      "label": "Buffer Slot",
      "hint": "Starting buffer slot (0-6, uses 2 slots)"
    }
  ]
}
```

**Parameters:**
- `pin` (uint8, byte 0): Analog pin number
- `slot` (uint8, byte 1): Starting buffer slot (0-6), uses 2 consecutive slots for 16-bit value

**CAN Data Format:**
```
Byte:  0      1
      [Pin] [Slot]
```

**Buffer Storage (16-bit little-endian):**
```
Slot N:   ADC_LSB
Slot N+1: ADC_MSB
```

**Examples:**

**Read 3 analog sensors:**
```
# Read potentiometer (pin A0) → slots 0-1
action:add:0:0x480:0xFFFFFFFF:::0:ADC_READ_BUFFER:fixed:14:0

# Read light sensor (pin A1) → slots 2-3
action:add:0:0x480:0xFFFFFFFF:::1:ADC_READ_BUFFER:fixed:15:2

# Read temperature sensor (pin A2) → slots 4-5
action:add:0:0x480:0xFFFFFFFF:::2:ADC_READ_BUFFER:fixed:16:4

# Send all sensor data
action:add:0:0x480:0xFFFFFFFF:::3:BUFFER_SEND:fixed:0x580

# Result CAN message 0x580:
# Bytes 0-1: Potentiometer (16-bit)
# Bytes 2-3: Light sensor (16-bit)
# Bytes 4-5: Temperature (16-bit)
# Bytes 6-7: Unused
```

**Use Cases:**
- Multi-sensor analog data acquisition
- Reading potentiometers/joysticks
- Monitoring analog sensor arrays
- Battery voltage monitoring

### BUFFER_SEND

Send buffer contents as a CAN message.

**Action Definition:**
```json
{
  "i": 13,
  "n": "BUFFER_SEND",
  "d": "Send buffer as CAN message",
  "c": "Communication",
  "trig": "can_msg",
  "p": [
    {
      "n": "can_id",
      "t": 1,
      "b": 0,
      "r": "0-2047",
      "role": "action_param",
      "label": "CAN ID",
      "hint": "CAN ID to transmit with"
    }
  ]
}
```

**Parameters:**
- `can_id` (uint16, bytes 0-1): CAN message ID to transmit buffer with

**CAN Data Format:**
```
Byte:  0-1
      [CAN_ID_LSB]
      [CAN_ID_MSB]
```

**Examples:**

**Complete sensor collection workflow:**
```
# Trigger CAN ID: 0x490

# Read sensor 1
action:add:0:0x490:0xFFFFFFFF:::0:ADC_READ_BUFFER:fixed:14:0

# Read sensor 2
action:add:0:0x490:0xFFFFFFFF:::1:ADC_READ_BUFFER:fixed:15:2

# Read sensor 3
action:add:0:0x490:0xFFFFFFFF:::2:ADC_READ_BUFFER:fixed:16:4

# Send all data
action:add:0:0x490:0xFFFFFFFF:::3:BUFFER_SEND:fixed:0x590

# Trigger: send:0x490:
# Result:  CAN_TX;0x590;[8 bytes of sensor data];timestamp
```

**Automatic periodic collection:**
```
# Periodic trigger (every 100ms) - collect and send sensor data
action:add:0:0x000:0x00000000:::0:ADC_READ_BUFFER:fixed:14:0
action:add:0:0x000:0x00000000:::1:ADC_READ_BUFFER:fixed:15:2
action:add:0:0x000:0x00000000:::2:BUFFER_SEND:fixed:0x5A0
```

**Use Cases:**
- Transmitting collected sensor data
- Creating custom CAN message formats
- Multi-sensor data aggregation
- Periodic telemetry transmission

### BUFFER_CLEAR

Clear the data buffer manually.

**Action Definition:**
```json
{
  "i": 14,
  "n": "BUFFER_CLEAR",
  "d": "Clear data buffer",
  "c": "Buffer",
  "trig": "can_msg",
  "p": []
}
```

**Parameters:** None

**Examples:**

**Reset between collection cycles:**
```
# Clear buffer before new collection
action:add:0:0x4A0:0xFFFFFFFF:::0:BUFFER_CLEAR:fixed

# Collect new data
action:add:0:0x4A0:0xFFFFFFFF:::1:ADC_READ_BUFFER:fixed:14:0
action:add:0:0x4A0:0xFFFFFFFF:::2:ADC_READ_BUFFER:fixed:15:2
action:add:0:0x4A0:0xFFFFFFFF:::3:BUFFER_SEND:fixed:0x5B0
```

**Use Cases:**
- Resetting buffer between data collection cycles
- Ensuring clean slate for new measurements
- Debugging buffer state

### Phase 1 Usage Patterns

**Pattern 1: Simple Multi-Sensor Collection**
```
Trigger → Read Sensor 1 → Read Sensor 2 → Read Sensor 3 → Send Buffer
```

**Pattern 2: Mixed Sensor Types**
```
Trigger → Read I2C (6 bytes) → Read ADC (2 bytes) → Send Buffer
```

**Pattern 3: Periodic Telemetry**
```
Timer (100ms) → Clear Buffer → Read All Sensors → Send Buffer → Repeat
```

**Pattern 4: On-Demand Sensor Query**
```
CAN Request (0x400) → Read Sensors → Send Response (0x500)
```

---

## CAN Message Handling

### Standard vs Extended IDs

**Standard CAN IDs:** 11-bit (0x000 - 0x7FF)
```
send:0x123:01,02,03
```

**Extended CAN IDs:** 29-bit (0x00000000 - 0x1FFFFFFF)
```
send:0x12345678:01,02,03
```

The firmware automatically detects extended IDs based on value range.

### Data Length

**Standard CAN:** 0-8 bytes
**CAN FD:** 0-64 bytes (if hardware supports it - check CAPS response)

### Byte Order

All multi-byte values are **little-endian** (LSB first).

**Example:** uint16 value 0x1234
```
Byte 0: 0x34  (low byte)
Byte 1: 0x12  (high byte)
```

---

## Error Handling

### Command Errors

If a command is invalid, you'll receive:

```
STATUS;ERROR;Command;Invalid format
STATUS;ERROR;Command;Unknown command
STATUS;ERROR;Command;Invalid parameter
```

### CAN Errors

```
CAN_ERR;BUS_OFF;Too many errors;1234567
CAN_ERR;TX_FAILED;Arbitration lost;1234567
CAN_ERR;RX_OVERFLOW;Buffer full;1234567
```

**Recovery:**

- **BUS_OFF:** Automatic recovery after 128 * 11 bit times
- **TX_FAILED:** Retry or check bus connection
- **RX_OVERFLOW:** Reduce message rate or increase processing speed

---

## Complete Command Reference

### Quick Reference Table

| Command | Purpose | Example |
|---------|---------|---------|
| `send:{ID}:{DATA}` | Send CAN message | `send:0x123:01,02,03` |
| `config:baudrate:{RATE}` | Change CAN speed | `config:baudrate:250000` |
| `config:filter:{ID}:{MASK}` | Set ID filter | `config:filter:0x500:0x700` |
| `get:status` | Get status | `get:status` |
| `get:version` | Get version | `get:version` |
| `get:stats` | Get statistics | `get:stats` |
| `get:capabilities` | Get board info | `get:capabilities` |
| `get:actiondefs` | Get action defs | `get:actiondefs` |
| `get:actiondef:{ID}` | Get specific def | `get:actiondef:7` |
| `action:add:...` | Add rule | `action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:candata` |
| `action:edit:...` | Update rule | `action:edit:1:0x100:0xFFFFFFFF:::0:GPIO_SET:fixed:14` |
| `action:remove:{ID}` | Remove rule | `action:remove:1` |
| `action:list` | List rules | `action:list` |
| `action:clear` | Clear all rules | `action:clear` |

---

## Example UI Connection Flow

```javascript
// 1. Open serial port
const port = await navigator.serial.requestPort();
await port.open({
  baudRate: 115200,
  flowControl: 'none'
});
await port.setSignals({
  dataTerminalReady: false,
  requestToSend: false
});

// 2. Read startup message
// ← STATUS;CONNECTED;SAMD51_CAN;SAMD51_CAN v2.0 @ 500kbps

// 3. Query capabilities
await sendCommand("get:capabilities");
// ← CAPS;{...}

// 4. Query action definitions
await sendCommand("get:actiondefs");
// ← ACTIONDEF;{...}
// ← ACTIONDEF;{...}
// ... (8 definitions for SAMD51)

// 5. Build UI dynamically from action definitions
actions.forEach(actionDef => {
  buildActionForm(actionDef);
});

// 6. User creates a rule
await sendCommand("action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:candata");
// ← STATUS;INFO;Rule added;ID: 1

// 7. Test the rule
await sendCommand("send:0x500:FF,00,00,C8");
// ← CAN_TX;0x500;FF,00,00,C8;1234567
// (NeoPixel turns red)

// 8. Monitor incoming CAN messages
reader.read().then(({ value }) => {
  const line = decoder.decode(value);
  // CAN_RX;0x123;01,02,03;1234567
  displayMessage(line);
});
```

---

## Appendix: Platform-Specific Notes

### SAMD51 (Adafruit Feather M4 CAN)

- **CAN Controller:** Built-in CAN peripheral
- **Default Bitrate:** 500kbps
- **Supported Bitrates:** 125k, 250k, 500k, 1000k
- **CAN FD:** Not supported
- **NeoPixel:** Built-in on pin 8
- **Visual Feedback:** Green (TX), Yellow (RX), Red (Error)

### RP2040 (Raspberry Pi Pico)

- **CAN Controller:** External MCP2515 or MCP2517FD via SPI
- **Default Bitrate:** 500kbps
- **Supported Bitrates:** Depends on external chip
- **CAN FD:** Yes (if using MCP2517FD)
- **NeoPixel:** Optional external
- **Visual Feedback:** None by default

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-01-27 | Complete rewrite based on actual firmware implementation |
| 1.x | 2024 | Legacy protocol (deprecated) |

---

**End of Protocol Specification**

This is a living document. As new features are implemented in firmware, this specification will be updated to match.

For implementation details and design rationale, see [PROTOCOL_V2_DECISIONS.md](PROTOCOL_V2_DECISIONS.md).

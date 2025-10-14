# CAN TUI Monitor

A universal Terminal User Interface (TUI) for monitoring and controlling CAN bus devices over serial/USB connections. This tool works with any CAN-enabled microcontroller board that implements the simple text-based protocol described below.

## Features

- **Universal Compatibility**: Works with any board that implements the protocol (Raspberry Pi Pico, Adafruit CAN Feather M4, etc.)
- **Real-time Monitoring**: Live display of CAN messages with color coding
- **Extensible Parser System**: Easily add custom parsers for your specific protocols
- **Message Filtering**: Filter messages by ID, type, or content
- **Statistics Tracking**: Message rates, error counts, and more
- **Export Capabilities**: Save captured messages to CSV format
- **Command Interface**: Send CAN messages directly from the terminal

## Installation

```bash
pip install can-tui-monitor
```

Or install from source:

```bash
git clone https://github.com/yourusername/can-tui-monitor.git
cd can-tui-monitor
pip install -e .
```

## Quick Start

```bash
# Connect to your CAN device on /dev/ttyACM0
can-tui /dev/ttyACM0

# Specify custom baud rate
can-tui /dev/ttyACM0 --baud 115200

# Enable debug logging
can-tui /dev/ttyACM0 --debug
```

## Serial Protocol Specification

The CAN TUI Monitor communicates with hardware devices using a simple text-based protocol over serial/USB. Any board that implements this protocol can be used with the TUI.

### Protocol Format

All messages are text-based and terminated with a newline (`\n`). The general format is:

```
<MESSAGE_TYPE>;<CAN_ID>;<DATA>
```

### Message Types

#### 1. CAN_RX (CAN Message Received)
```
CAN_RX;0x123;01,02,03,04,05,06,07,08
```
- `CAN_RX`: Message type indicating a received CAN message
- `0x123`: CAN ID in hexadecimal (11-bit or 29-bit)
- `01,02,03,04,05,06,07,08`: Data bytes in hexadecimal, comma-separated

#### 2. CAN_TX (CAN Message Transmitted)
```
CAN_TX;0x456;AA,BB,CC,DD
```
- Same format as CAN_RX but indicates a transmitted message

#### 3. CAN_ERR (CAN Error)
```
CAN_ERR;ERROR_CODE;Description of error
```
- `ERROR_CODE`: Numeric error code
- `Description`: Human-readable error description

#### 4. STATUS (Device Status)
```
STATUS;CONNECTED;Bus speed: 500kbps
```
- Status updates from the device

### Commands (TUI to Device)

#### Send CAN Message
```
send:0x123:01,02,03,04,05,06,07,08
```
- Sends a CAN message with ID 0x123 and specified data bytes

#### Configuration Commands
```
config:speed:500000
config:filter:0x100,0x200,0x300
```

## Board Implementation Examples

### Raspberry Pi Pico with MCP2551

```cpp
void setup() {
    Serial.begin(115200);
    // Initialize CAN at 500kbps
    Serial.println("STATUS;CONNECTED;UCAN Ready");
}

void loop() {
    if (canMessageAvailable()) {
        CANMessage msg = readCANMessage();
        Serial.print("CAN_RX;0x");
        Serial.print(msg.id, HEX);
        Serial.print(";");
        for (int i = 0; i < msg.length; i++) {
            if (i > 0) Serial.print(",");
            Serial.print(msg.data[i], HEX);
        }
        Serial.println();
    }
}
```

### Adafruit CAN Feather M4

```cpp
#include <CAN.h>

void setup() {
    Serial.begin(115200);
    if (CAN.begin(500E3)) {
        Serial.println("STATUS;CONNECTED;CAN Feather Ready");
    }
}

void onReceive(int packetSize) {
    Serial.print("CAN_RX;0x");
    Serial.print(CAN.packetId(), HEX);
    Serial.print(";");
    
    for (int i = 0; i < packetSize; i++) {
        if (i > 0) Serial.print(",");
        Serial.print(CAN.read(), HEX);
    }
    Serial.println();
}
```

## Custom Parser Development

Create custom parsers to interpret your CAN messages:

```python
from can_tui.parsers.base import BaseParser
from can_tui.models.can_message import CANMessage

class MyCustomParser(BaseParser):
    """Parser for my custom protocol"""
    
    name = "My Custom Protocol"
    description = "Parses custom sensor data"
    
    def can_parse(self, message: CANMessage) -> bool:
        # Return True if this parser can handle the message
        return message.id in [0x100, 0x101, 0x102]
    
    def parse(self, message: CANMessage) -> str:
        if message.id == 0x100:
            temp = (message.data[0] << 8 | message.data[1]) / 10.0
            return f"Temperature: {temp}°C"
        elif message.id == 0x101:
            voltage = message.data[0] / 10.0
            return f"Battery: {voltage}V"
        return f"Unknown sensor: {message.data.hex()}"
```

Register your parser in `config/parsers.yaml`:

```yaml
parsers:
  - module: can_tui.parsers.custom.my_custom_parser
    class: MyCustomParser
    priority: 100
    can_ids:
      - 0x100
      - 0x101
      - 0x102
```

## Configuration

The TUI can be configured via YAML files in the `config/` directory:

### parsers.yaml
Configure which parsers to load and their priorities:

```yaml
parsers:
  # Built-in parsers
  - module: can_tui.parsers.builtin.raw
    class: RawParser
    priority: 0  # Lowest priority, fallback parser
    
  # Custom parsers
  - module: can_tui.parsers.custom.j1939
    class: J1939Parser
    priority: 100
    can_ids: [0x18FEEE00, 0x18FEEF00]
```

## Keyboard Shortcuts

- `q` or `Ctrl+C`: Quit application
- `c`: Clear message log
- `f`: Toggle message filtering
- `s`: Export messages to CSV
- `p`: Pause/resume message capture
- `Tab`: Switch between message log and command input
- `↑`/`↓`: Navigate command history

## Development

### Setting up development environment

```bash
# Clone the repository
git clone https://github.com/yourusername/can-tui-monitor.git
cd can-tui-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run with test hardware
can-tui /dev/ttyACM0 --debug
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=can_tui

# Run specific test file
pytest tests/test_parsers.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual) - An excellent TUI framework
- Inspired by various CAN analysis tools and the need for a universal, extensible solution
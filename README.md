# uCAN - Universal USB-to-CAN Bridge

Multi-platform USB-to-CAN bridge system with hardware abstraction layer supporting multiple microcontroller platforms (RP2040, SAMD51, ESP32, STM32) and a feature-rich Python TUI for real-time CAN bus monitoring, message parsing, and custom visualization.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-RP2040%20%7C%20SAMD51%20%7C%20ESP32%20%7C%20STM32-orange.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

## Features

### Multi-Platform Firmware
- **Hardware Abstraction Layer (HAL)** - Platform-agnostic CAN interface
- **Multiple MCU Support** - RP2040, SAMD51, ESP32, STM32
- **Unified Protocol** - Text-based serial protocol (115200 baud default)
- **Auto-Detection** - Compile-time platform detection
- **PlatformIO Build System** - Multi-environment configuration
- **Dynamic Capability Discovery** - Query board features at runtime
- **Action System** - Rule-based hardware responses to CAN messages
- **Periodic Transmission** - Configurable periodic CAN message sending

### Python TUI Application
- **Real-time Monitoring** - Live CAN message display with color coding
- **Extensible Parser System** - Custom message interpreters with YAML configuration
- **Custom Views** - Pluggable visualization widgets for specific CAN IDs
- **Message Filtering** - Interactive filtering by type, ID, or content
- **Statistics Tracking** - Message rates, error counts, data rates
- **CSV Export** - Save captured messages with timestamps
- **Command Interface** - Send CAN messages directly from terminal
- **Cross-Platform** - Windows, Linux, macOS support
- **Smart Port Detection** - Automatic device discovery
- **Interactive Configuration** - Runtime port/baud settings

## Quick Start

### Hardware Setup

#### Raspberry Pi Pico + MCP2551 Transceiver
```
Pico GP4 (CAN TX) → MCP2551 TXD
Pico GP5 (CAN RX) → MCP2551 RXD
3.3V, GND → MCP2551
CANH/CANL → CAN Bus (with 120Ω termination)
```

#### Adafruit Feather M4 CAN
- Built-in CAN transceiver (no external components needed)
- Connect CANH/CANL to CAN bus
- NeoPixel provides visual feedback (Green=TX, Yellow=RX, Red=Error)

### Firmware Installation

```bash
# Install PlatformIO
pip install platformio

# Build for Raspberry Pi Pico
pio run -e pico

# Build for Adafruit Feather M4 CAN
pio run -e feather_m4_can

# Upload to board
pio run -e pico --target upload

# Monitor serial output
pio device monitor -b 115200
```

### TUI Installation

```bash
# Clone repository
git clone https://github.com/ril3y/uCAN.git
cd uCAN

# Install Python dependencies
pip install -e .

# Run TUI (interactive port selection)
python -m can_tui.main

# Or connect directly to specific port
python -m can_tui.main -p /dev/ttyACM0
```

## Usage

### TUI Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F1` | Clear message log |
| `F2` | Save messages to CSV |
| `F3` | Pause/Resume monitoring |
| `F4` | Show help dialog |
| `F5` | Settings (port/baud configuration) |
| `Ctrl+C` | Quit application |
| `Ctrl+R` | Reconnect to device |
| `Esc` | Close modal dialogs |

### Sending CAN Messages

Type commands in the bottom input field:

```
# Send a single CAN message
send:0x123:01,02,03,04,05,06,07,08

# Configure CAN bus
config:speed:500000
config:filter:0x100,0x200,0x300

# Query capabilities
get:capabilities
get:actions
get:pins

# Manage action rules
action:add:1:0x100:::::GPIO_TOGGLE:13
action:list
action:remove:1
```

## Action System

UCAN includes a powerful rule-based action system that allows CAN messages to trigger hardware responses automatically, without host intervention.

### Supported Actions

| Action Type | Description | Platforms |
|------------|-------------|-----------|
| `GPIO_SET` | Set pin HIGH | All |
| `GPIO_CLEAR` | Set pin LOW | All |
| `GPIO_TOGGLE` | Toggle pin state | All |
| `CAN_SEND` | Send CAN message once | All |
| `CAN_SEND_PERIODIC` | Send CAN message at interval | All |
| `PWM_SET` | Set PWM duty cycle | SAMD51, ESP32 |
| `NEOPIXEL_COLOR` | Set NeoPixel RGB color | SAMD51 |
| `ADC_READ_SEND` | Read ADC and send via CAN | All with ADC |

### Example Usage

```bash
# Toggle GPIO pin 13 when receiving CAN ID 0x100
action:add:1:0x100:::::GPIO_TOGGLE:13

# Send periodic heartbeat every 1000ms
action:add:2:0x000:::::CAN_SEND_PERIODIC:0x123:01,02,03,04:1000

# Set NeoPixel to red on CAN ID 0x500
action:add:3:0x500:::::NEOPIXEL_COLOR:255,0,0,128

# List all active rules
action:list

# Disable a rule
action:disable:1

# Remove a rule
action:remove:1
```

### Capability Discovery

Query board capabilities to determine available actions:

```bash
# Get full JSON capabilities
get:capabilities
# Returns: CAPS;{"board":"Feather M4 CAN","chip":"ATSAME51",...}

# Get supported actions
get:actions
# Returns: ACTIONS;GPIO_SET,GPIO_CLEAR,GPIO_TOGGLE,CAN_SEND,CAN_SEND_PERIODIC,PWM_SET,NEOPIXEL_COLOR,...

# Get pin information
get:pins
# Returns: PINS;26;PWM:16;ADC:6;DAC:2;NEO:8
```

## Supported Hardware

| Platform | Status | MCU | CAN Controller | Notes |
|----------|--------|-----|----------------|-------|
| **Raspberry Pi Pico** | ✅ Implemented | RP2040 | External MCP2551 | Uses can2040 library |
| **Adafruit Feather M4 CAN** | ✅ Implemented | SAMD51 | Built-in CAN | Integrated transceiver |
| **ESP32** | 🚧 Planned | ESP32 | External transceiver | HAL ready, impl needed |
| **STM32** | 🚧 Planned | STM32F4 | Built-in bxCAN | HAL ready, impl needed |

## Architecture

```
uCAN/
├── src/                      # Embedded firmware (C++)
│   ├── hal/                  # Hardware Abstraction Layer
│   │   ├── can_interface.h   # Abstract CAN interface
│   │   ├── can_factory.h     # Platform factory
│   │   ├── rp2040_can.cpp    # RP2040 implementation
│   │   └── samd51_can.cpp    # SAMD51 implementation
│   ├── capabilities/         # Platform capability discovery
│   │   ├── board_capabilities.h   # Capability definitions
│   │   ├── capability_query.cpp   # JSON query responses
│   │   ├── rp2040_capabilities.cpp
│   │   └── samd51_capabilities.cpp
│   ├── actions/              # Rule-based action system
│   │   ├── action_types.h    # Action definitions
│   │   ├── action_manager.h  # Action manager class
│   │   └── action_manager.cpp
│   └── main.cpp              # Main firmware entry point
│
├── can_tui/                  # Python TUI application
│   ├── app.py                # Main Textual application
│   ├── views/                # Custom view system
│   │   ├── base_view.py      # Base view class
│   │   └── view_*.py         # Auto-discovered views
│   ├── widgets/              # UI components
│   ├── parsers/              # Message parsers
│   ├── services/             # Serial communication
│   └── models/               # Data models
│
├── docs/                     # Documentation
│   └── UCAN_WEB_API_GUIDE.md # Web developer integration guide
│
├── platformio.ini            # PlatformIO build config
├── parser_config.yaml        # Parser configuration
└── pyproject.toml            # Python package config
```

## Protocol Specification

uCAN uses a simple text-based protocol over USB serial. See [can_tui/PROTOCOL.md](can_tui/PROTOCOL.md) for full details.

### Example Messages

```
# Device to TUI
CAN_RX;0x123;01,02,03,04,05,06,07,08
CAN_TX;0x456;AA,BB,CC,DD
CAN_ERR;BUS_OFF;CAN bus entered bus-off state
STATUS;CONNECTED;uCAN v1.0 Ready
CAPS;{"board":"Feather M4 CAN","chip":"ATSAME51",...}
ACTIONS;GPIO_SET,GPIO_CLEAR,GPIO_TOGGLE,CAN_SEND,CAN_SEND_PERIODIC,...

# TUI to Device
send:0x123:01,02,03,04
config:speed:500000
get:status
get:capabilities
get:actions
action:add:1:0x100:::::GPIO_TOGGLE:13
action:list
control:reset
```

## Development

For detailed development information, see [docs/DEVELOPER.md](docs/DEVELOPER.md).

### Quick Development Setup

```bash
# Firmware development
pio run -e pico --target upload
pio device monitor -b 115200

# TUI development
pip install -e ".[dev]"
pytest tests/
python -m can_tui.main -p /dev/ttyACM0
```

## Custom Parsers and Views

### Creating a Custom Parser

```python
# can_tui/parsers/my_parser.py
from can_tui.parsers.base import BaseParser

class MyParser(BaseParser):
    def can_parse(self, message):
        return message.can_id == 0x100

    def parse(self, message):
        temp = (message.data[0] << 8 | message.data[1]) / 10.0
        return f"Temperature: {temp}°C"
```

Register in `parser_config.yaml`:
```yaml
parsers:
  - name: my_parser
    class: MyParser
    can_ids: [0x100]
    confidence: 90
```

### Creating a Custom View

```python
# can_tui/views/view_mywidget.py
from can_tui.views.base_view import BaseView

class MyWidgetView(BaseView):
    def get_view_name(self):
        return "My Custom View"

    def get_supported_can_ids(self):
        return [0x100, 0x101]

    def create_widget(self, **kwargs):
        return MyCustomWidget()
```

Views are automatically discovered and available in TUI settings.

## Examples

See the [examples/](examples/) directory for:
- Custom parser implementations
- Hardware wiring diagrams
- Sample CAN message configurations
- Custom view widgets

## Contributing

Contributions are welcome! Please see [docs/DEVELOPER.md](docs/DEVELOPER.md) for:
- Development environment setup
- Architecture details
- Coding standards
- Testing requirements
- Pull request process

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual) - Excellent Python TUI framework
- [PlatformIO](https://platformio.org/) - Cross-platform embedded development
- can2040 library for RP2040 CAN support
- Adafruit CAN library for SAMD51 support

## Links

- **Documentation**: [docs/DEVELOPER.md](docs/DEVELOPER.md)
- **Protocol v2.0**: [can_tui/PROTOCOL.md](can_tui/PROTOCOL.md)
- **Protocol Summary**: [docs/PROTOCOL_V2_SUMMARY.md](docs/PROTOCOL_V2_SUMMARY.md)
- **Web API Guide**: [docs/UCAN_WEB_API_GUIDE.md](docs/UCAN_WEB_API_GUIDE.md)
- **TUI Guide**: [can_tui/README.md](can_tui/README.md)
- **CAN FD Analysis**: [docs/CAN_FD_ANALYSIS.md](docs/CAN_FD_ANALYSIS.md)
- **Issues**: [GitHub Issues](https://github.com/ril3y/uCAN/issues)

## Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review the protocol specification

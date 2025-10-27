# uCAN Developer Guide

Comprehensive development guide for contributing to uCAN firmware and TUI application.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Architecture Overview](#architecture-overview)
- [Firmware Development](#firmware-development)
- [TUI Development](#tui-development)
- [Testing](#testing)
- [Contributing Guidelines](#contributing-guidelines)

## Development Environment Setup

### Prerequisites

**Firmware Development:**
- Python 3.8 or higher
- PlatformIO CLI or IDE
- USB drivers for your target board
- Git

**TUI Development:**
- Python 3.8 or higher
- pip or pipenv
- Virtual environment (recommended)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/ril3y/uCAN.git
cd uCAN

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install PlatformIO
pip install platformio

# Verify installation
pio --version
pytest --version
```

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    uCAN System                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────────┐         ┌──────────────────┐      │
│  │   Firmware     │  USB    │   Python TUI     │      │
│  │   (C++/HAL)    │◄───────►│   (Textual)      │      │
│  └────────────────┘  Serial └──────────────────┘      │
│         │                            │                 │
│         ▼                            ▼                 │
│  ┌────────────────┐         ┌──────────────────┐      │
│  │  CAN Bus       │         │  User Interface  │      │
│  │  (CANH/CANL)   │         │  (Terminal)      │      │
│  └────────────────┘         └──────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Protocol Flow

```
Device → TUI:  CAN_RX;0x123;01,02,03,04
               CAN_TX;0x456;AA,BB
               STATUS;CONNECTED;Ready
               CAN_ERR;BUS_OFF;Error description

TUI → Device:  send:0x123:01,02,03,04
               config:speed:500000
               get:status
               control:reset
```

## Firmware Development

### Hardware Abstraction Layer (HAL)

The HAL provides platform-independent CAN operations through a common interface.

#### Adding a New Platform

**Step 1: Platform Detection**

Edit `src/hal/platform_config.h`:

```cpp
// Add platform detection
#if defined(YOUR_PLATFORM_DEFINE)
    #define PLATFORM_YOUR_PLATFORM
    #define PLATFORM_NAME "YourPlatform"
#endif
```

**Step 2: Implement CANInterface**

Create `src/hal/your_platform_can.h`:

```cpp
#pragma once
#include "can_interface.h"

class YourPlatformCAN : public CANInterface {
public:
    bool begin(uint32_t baudrate) override;
    bool end() override;
    bool sendMessage(uint32_t id, const uint8_t* data, uint8_t len) override;
    bool receiveMessage(uint32_t& id, uint8_t* data, uint8_t& len) override;
    bool available() override;
    uint32_t getErrorCount() override;
    bool setFilter(uint32_t mask, uint32_t filter) override;
};
```

Create `src/hal/your_platform_can.cpp`:

```cpp
#include "your_platform_can.h"

bool YourPlatformCAN::begin(uint32_t baudrate) {
    // Initialize CAN peripheral
    // Configure pins
    // Set baudrate
    return true;
}

bool YourPlatformCAN::sendMessage(uint32_t id, const uint8_t* data, uint8_t len) {
    // Transmit CAN message
    // Return success status
    return true;
}

// Implement other methods...
```

**Step 3: Register in Factory**

Edit `src/hal/can_factory.h`:

```cpp
#elif defined(PLATFORM_YOUR_PLATFORM)
    #include "your_platform_can.h"
    static CANInterface* createCANInterface() {
        return new YourPlatformCAN();
    }
#endif
```

**Step 4: PlatformIO Configuration**

Edit `platformio.ini`:

```ini
[env:your_platform]
platform = your_platform_name
board = your_board
framework = arduino
lib_deps =
    your_can_library
build_flags =
    -DYOUR_PLATFORM_DEFINE
    -DBAUD_RATE=115200
```

**Step 5: Test**

```bash
# Build
pio run -e your_platform

# Upload
pio run -e your_platform --target upload

# Monitor
pio device monitor -b 115200
```

### Current Platform Implementations

#### RP2040 (Raspberry Pi Pico)

- **CAN Controller**: External MCP2551 transceiver
- **Library**: can2040 (direct integration)
- **Pins**: GP4 (TX), GP5 (RX)
- **Features**: Software CAN implementation using PIO
- **Limitations**: Max 1 Mbps baudrate

Key files:
- `src/hal/rp2040_can.cpp`
- `src/hal/rp2040_can.h`

#### SAMD51 (Adafruit Feather M4 CAN)

- **CAN Controller**: Built-in CAN peripheral
- **Library**: Adafruit CAN
- **Transceiver**: Integrated
- **Features**: Hardware CAN with DMA support
- **NeoPixel**: Visual feedback (TX/RX/Error)

Key files:
- `src/hal/samd51_can.cpp`
- `src/hal/samd51_can.h`

### Protocol Implementation

The firmware implements the text-based protocol defined in `can_tui/PROTOCOL.md`.

**Sending Messages to TUI:**

```cpp
void sendCANRX(uint32_t id, const uint8_t* data, uint8_t len) {
    Serial.print("CAN_RX;0x");
    Serial.print(id, HEX);
    Serial.print(";");
    for (uint8_t i = 0; i < len; i++) {
        if (i > 0) Serial.print(",");
        Serial.print(data[i], HEX);
    }
    Serial.println();
}
```

**Receiving Commands from TUI:**

```cpp
void handleCommand(String cmd) {
    if (cmd.startsWith("send:")) {
        // Parse: send:0x123:01,02,03,04
        // Extract ID and data
        // Call can->sendMessage()
    } else if (cmd.startsWith("config:")) {
        // Handle configuration
    }
}
```

### Build System

**Build Commands:**

```bash
# Build all environments
pio run

# Build specific platform
pio run -e pico
pio run -e feather_m4_can

# Upload firmware
pio run -e pico --target upload

# Clean build
pio run --target clean

# Monitor serial
pio device monitor -b 115200

# List devices
pio device list
```

**Build Flags:**

```ini
build_flags =
    -DPLATFORM_RP2040        # Platform selection
    -DBAUD_RATE=115200       # Serial baudrate
    -DCAN_BAUDRATE=500000    # CAN baudrate
    -DDEBUG_SERIAL           # Enable debug output
```

## TUI Development

### Application Architecture

```
can_tui/
├── app.py              # Main Textual application
├── models/             # Data models
│   └── can_message.py  # CANMessage, MessageStats, MessageFilter
├── services/           # Background services
│   └── serial_service.py  # Async serial communication
├── widgets/            # UI components
│   ├── message_log.py  # Message display widget
│   ├── command_input.py # Command input widget
│   ├── status_bar.py   # Status bar widget
│   └── ...
├── views/              # Custom view system
│   ├── base_view.py    # Base view class
│   ├── discovery.py    # Auto-discovery
│   ├── modern_registry.py # View registry
│   └── view_*.py       # Custom views (auto-discovered)
└── parsers/            # Message parsers
    ├── base.py         # Base parser class
    └── ...             # Custom parsers
```

### Creating Custom Views

Custom views provide specialized visualizations for specific CAN IDs.

**1. Create View Class**

Create `can_tui/views/view_mywidget.py`:

```python
from typing import List, Optional
from can_tui.views.base_view import BaseView, ViewParsedMessage
from can_tui.models.can_message import CANMessage

class MyWidgetView(BaseView):
    """Custom view for my protocol."""

    def get_view_name(self) -> str:
        return "My Custom View"

    def get_description(self) -> str:
        return "Displays my custom CAN data"

    def get_supported_can_ids(self) -> List[int]:
        return [0x100, 0x101, 0x102]

    def create_widget(self, send_command_callback=None, **kwargs):
        from can_tui.widgets.my_widget import MyCustomWidget
        widget = MyCustomWidget()
        self.widget = widget
        return widget

    def parse_message(self, can_message: CANMessage) -> Optional[ViewParsedMessage]:
        """Parse message using view-specific logic."""
        if can_message.can_id not in self.get_supported_can_ids():
            return None

        parsed = ViewParsedMessage(can_message.can_id, can_message.data)

        if can_message.can_id == 0x100:
            # Parse temperature sensor
            if len(can_message.data) >= 2:
                temp = (can_message.data[0] << 8 | can_message.data[1]) / 10.0
                parsed.add_field("Temperature", temp, "float")
                parsed.add_field("Unit", "°C", "string")

        return parsed
```

**2. Create Widget**

Create `can_tui/widgets/my_widget.py`:

```python
from textual.widget import Widget
from textual.containers import Container, Vertical
from rich.text import Text

class MyCustomWidget(Widget):
    """Widget for displaying custom data."""

    def compose(self):
        yield Container(
            Vertical(
                Static("Temperature: --"),
                id="temp_display"
            )
        )

    def update_message_data(self, can_message, parsed_data):
        """Called when new CAN message arrives."""
        if parsed_data:
            temp_field = parsed_data.get_field_by_name("Temperature")
            if temp_field:
                temp_display = self.query_one("#temp_display", Static)
                temp_display.update(f"Temperature: {temp_field.value}°C")
```

**3. View Auto-Discovery**

Views following the naming pattern `view_*.py` in `can_tui/views/` are automatically discovered and registered. No manual registration needed!

### Creating Custom Parsers

Parsers interpret raw CAN message data into human-readable formats.

**1. Create Parser Class**

Create `can_tui/parsers/my_parser.py`:

```python
from typing import Optional
from can_tui.parsers.base import BaseParser, ParsedMessage
from can_tui.models.can_message import CANMessage

class MyCustomParser(BaseParser):
    """Parser for my custom protocol."""

    def get_name(self) -> str:
        return "My Custom Parser"

    def get_description(self) -> str:
        return "Parses my custom CAN protocol"

    def can_parse(self, message: CANMessage) -> int:
        """Return confidence level (0-100) for parsing this message."""
        if message.can_id in [0x100, 0x101]:
            return 90  # High confidence
        return 0

    def parse(self, message: CANMessage) -> Optional[ParsedMessage]:
        """Parse the message and return structured data."""
        parsed = ParsedMessage(message.can_id, message.data)

        if message.can_id == 0x100:
            # Temperature sensor
            temp = (message.data[0] << 8 | message.data[1]) / 10.0
            parsed.add_field("temperature", temp, "°C")
            parsed.interpretation = f"Temperature: {temp}°C"

        elif message.can_id == 0x101:
            # Voltage sensor
            voltage = message.data[0] / 10.0
            parsed.add_field("voltage", voltage, "V")
            parsed.interpretation = f"Battery: {voltage}V"

        return parsed
```

**2. Register Parser**

Edit `parser_config.yaml`:

```yaml
parsers:
  - name: my_custom_parser
    module: can_tui.parsers.my_parser
    class: MyCustomParser
    can_ids:
      - 0x100
      - 0x101
    confidence: 90
    enabled: true
```

### Message Routing System

The TUI routes messages through several layers:

1. **Serial Service** → Receives raw protocol messages
2. **Message Parser** → Parses protocol into CANMessage objects
3. **Parser Registry** → Finds best parser for message
4. **View Registry** → Routes to custom views (if applicable)
5. **Widget Update** → Updates UI components

**Direct CAN ID Routing:**

```python
# Register widget for specific CAN ID
app.register_can_id_handler(0x100, my_widget)

# Messages with ID 0x100 automatically routed to my_widget
```

### Widgets and UI Components

**Built-in Widgets:**

- `MessageLogWidget` - Scrolling message log with syntax highlighting
- `CommandInputWidget` - Command input with history
- `StatsWidget` - Connection and message statistics
- `StatusBarWidget` - Application status bar
- `SettingsModal` - Port/baud configuration dialog
- `HelpModal` - Keyboard shortcuts and help

**Creating Custom Widgets:**

```python
from textual.widget import Widget
from textual.reactive import reactive

class MyWidget(Widget):
    """Custom widget example."""

    # Reactive state
    value = reactive(0)

    def compose(self):
        """Compose child widgets."""
        yield Static(f"Value: {self.value}")

    def watch_value(self, new_value):
        """Called when reactive value changes."""
        self.query_one(Static).update(f"Value: {new_value}")
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=can_tui tests/

# Run specific test file
pytest tests/test_parsers.py

# Run with verbose output
pytest -v

# Run and show print statements
pytest -s
```

### Test Structure

```
tests/
├── test_parsers.py           # Parser tests
├── test_message_filter.py    # Filter tests
├── test_views.py             # View tests
└── test_serial_service.py    # Service tests
```

### Writing Tests

**Parser Tests:**

```python
import pytest
from can_tui.parsers.my_parser import MyCustomParser
from can_tui.models.can_message import CANMessage

def test_my_parser():
    parser = MyCustomParser()
    message = CANMessage(
        timestamp=0,
        type="CAN_RX",
        can_id=0x100,
        data=[0x01, 0x2C]  # 30.0°C
    )

    assert parser.can_parse(message) == 90

    parsed = parser.parse(message)
    assert parsed is not None
    assert parsed.get_field_by_name("temperature").value == 30.0
```

**View Tests:**

```python
def test_my_view():
    view = MyWidgetView()

    assert view.get_view_name() == "My Custom View"
    assert 0x100 in view.get_supported_can_ids()

    message = CANMessage(0, "CAN_RX", 0x100, [0x01, 0x2C])
    parsed = view.parse_message(message)

    assert parsed is not None
    assert parsed.is_valid()
```

### Integration Testing

```bash
# Hardware-in-loop test script
./test_runner.sh

# Manual testing with debug logging
python -m can_tui.main -p /dev/ttyACM0 --debug
```

## Contributing Guidelines

### Code Style

**Python:**
- Follow PEP 8
- Use `black` for formatting
- Use `isort` for import sorting
- Use type hints
- Docstrings for public functions

```bash
# Format code
black can_tui/ tests/
isort can_tui/ tests/

# Type checking
mypy can_tui/

# Linting
flake8 can_tui/
```

**C++:**
- Follow Google C++ Style Guide
- Use meaningful variable names
- Comment complex logic
- Keep functions focused and small

### Git Workflow

1. **Fork** the repository
2. **Create** a feature branch
   ```bash
   git checkout -b feature/my-feature
   ```
3. **Make** your changes
4. **Test** thoroughly
   ```bash
   pytest
   pio run -e pico
   ```
5. **Commit** with clear messages
   ```bash
   git commit -m "Add feature: description"
   ```
6. **Push** to your fork
   ```bash
   git push origin feature/my-feature
   ```
7. **Open** a Pull Request

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build/tooling changes

**Example:**
```
feat: Add ESP32 CAN support

Implement CANInterface for ESP32 platform using TWAI driver.
Adds ESP32 HAL implementation with support for standard and
extended CAN IDs.

Closes #42
```

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] Branch is up to date with main
- [ ] No merge conflicts
- [ ] Tested on target hardware (if firmware changes)

## Debugging

### Firmware Debugging

```cpp
// Enable debug output
#define DEBUG_SERIAL

// Add debug prints
#ifdef DEBUG_SERIAL
    Serial.print("DEBUG: Message ID=");
    Serial.println(id, HEX);
#endif
```

**Serial Monitor:**
```bash
# Monitor with filters
pio device monitor -b 115200 --filter send_on_enter

# Monitor with timestamps
pio device monitor -b 115200 --filter time
```

### TUI Debugging

```python
import logging

# Enable debug logging
logger = logging.getLogger('can_tui')
logger.setLevel(logging.DEBUG)

# Add file handler
handler = logging.FileHandler('can_tui_debug.log')
logger.addHandler(handler)

# Debug specific module
logger.error(f"DEBUG: message={message}")
```

**Run with debug flag:**
```bash
python -m can_tui.main -p /dev/ttyACM0 --debug
```

## Resources

- **Textual Documentation**: https://textual.textualize.io/
- **PlatformIO Documentation**: https://docs.platformio.org/
- **CAN Bus Basics**: https://en.wikipedia.org/wiki/CAN_bus
- **Protocol Specification**: [can_tui/PROTOCOL.md](can_tui/PROTOCOL.md)
- **Project Board**: [GitHub Projects](https://github.com/ril3y/uCAN/projects)

## Getting Help

- Open an issue on GitHub
- Check existing documentation
- Review example implementations
- Ask in discussions

## License

MIT License - see [LICENSE](LICENSE) for details.

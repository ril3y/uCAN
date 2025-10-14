# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UCAN is a hardware-agnostic USB-to-CAN bridge system supporting multiple microcontroller platforms. It provides both embedded firmware and a standalone Python-based Terminal User Interface (TUI) for CAN bus communication and monitoring.

The system consists of two main components:
1. **Embedded Firmware**: Multi-platform C++ firmware with Hardware Abstraction Layer (HAL)
2. **Python TUI Application**: Cross-platform monitoring and control interface with advanced message parsing

## Multi-Platform Architecture

### Supported Hardware
- **Raspberry Pi Pico (RP2040)** with external MCP2551 CAN transceiver
- **Adafruit Feather M4 CAN (SAMD51)** with built-in CAN peripheral
- **ESP32** with external CAN transceiver (future)
- **STM32** with built-in CAN peripheral (future)

### Firmware Architecture (src/*)
- **Hardware Abstraction Layer (HAL)**: `src/hal/` provides platform-agnostic CAN interface
- **Platform Detection**: Automatic detection based on compile-time defines
- **Unified Protocol**: Implements full PROTOCOL.md specification
- **Multi-Environment Build**: PlatformIO configuration for all supported boards

### TUI Application (can_tui/*)
- **Standalone Python Package**: Independent of hardware implementation built with Textual framework
- **Universal Protocol Support**: Works with any board implementing the protocol
- **Modular Parser System**: Extensible message interpretation with CAN ID mapping and YAML configuration
- **Hardware Agnostic**: Communicates via serial only (115200 baud default)
- **Cross-Platform**: Supports Windows (COM ports), Linux (/dev/ttyUSB*, /dev/ttyACM*), and macOS
- **Real-time Monitoring**: Live message display with filtering, statistics, and CSV export capabilities
- **Smart Port Detection**: Automatically filters to show only connected devices
- **Interactive Configuration**: Modal settings dialog for runtime port/baud configuration

## Essential Commands

### Multi-Platform Firmware Development
```bash
# Build for Raspberry Pi Pico (default)
pio run -e pico

# Build for Adafruit Feather M4 CAN
pio run -e feather_m4_can

# Build for ESP32 (future)
pio run -e esp32

# Upload to specific board
pio run -e pico --target upload
pio run -e feather_m4_can --target upload

# Monitor serial output (all platforms use 115200 baud)
pio device monitor -b 115200

# Clean all environments
pio run --target clean
```

### TUI Development
```bash
# Install dependencies (requires Python 3.8+)
pip install -e .

# Run TUI application with port auto-selection
python -m can_tui.main

# Run TUI application with specific port
python -m can_tui.main -p /dev/ttyACM0

# Run with specific baud rate
python -m can_tui.main -p /dev/ttyACM0 -b 230400

# Run tests
pytest tests/

# Type checking
mypy can_tui/

# Code formatting
black can_tui/ tests/
isort can_tui/ tests/
```

## Hardware Abstraction Layer

### Adding New Platforms
1. **Platform Detection**: Add defines to `src/hal/platform_config.h`
2. **HAL Implementation**: Create platform-specific class inheriting from `CANInterface`
3. **Factory Registration**: Add to `src/hal/can_factory.h`
4. **PlatformIO Environment**: Add build configuration to `platformio.ini`

### Current Platform Status
- **RP2040**: ✅ Implemented using direct can2040 integration (bypasses ACAN2040 issues)
- **SAMD51**: ✅ Implemented using Adafruit CAN library
- **ESP32**: 🚧 Platform configuration ready, implementation needed
- **STM32**: 🚧 Platform configuration ready, implementation needed

## Protocol Implementation

The firmware implements the full protocol specification from `can_tui/PROTOCOL.md`:
- **CAN_RX/CAN_TX**: Message transmission with timestamps
- **CAN_ERR**: Comprehensive error reporting
- **STATUS**: Device status and configuration changes
- **STATS**: Periodic statistics reporting
- **Commands**: send, config, get, control

## Key Development Areas

### Parser System
- New parsers inherit from `BaseParser` in `can_tui/parsers/base.py`
- Register parsers in `parser_config.yaml` with CAN ID mappings
- Built-in parsers: RawDataParser, ExampleSensorParser, GolfCartThrottleParser, WiringHarnessParser
- Test parsers in `tests/test_parsers.py`

### Custom View System
- **BaseView Architecture**: `can_tui/views/base_view.py` - Abstract base class for custom visualizations
- **Auto-Discovery**: Views placed in `can_tui/views/view_*.py` are automatically discovered and registered
- **CAN ID Subscription**: Views declare supported CAN IDs via `get_supported_can_ids()`
- **Message Routing**: `ModernViewRegistry` routes messages to views based on CAN ID and priority
- **Widget Integration**: Each view associates with a Textual widget for UI rendering
- **Example Implementation**: `HarnessSwitchView` subscribes to CAN ID 0x500 and displays switch states

#### Creating Custom Views
1. Create `view_yourname.py` in `can_tui/views/` inheriting from `BaseView`
2. Implement required methods: `get_view_name()`, `get_supported_can_ids()`, `get_widget_class()`, etc.
3. Create corresponding widget in `can_tui/widgets/` using Textual components
4. View is automatically discovered and available in TUI settings

### Protocol Extensions
- Current: Text-based protocol over USB serial (115200 baud)
- Implemented: CAN_RX, CAN_TX, CAN_ERR, STATUS commands
- Planned: Binary protocol for efficiency, extended CAN ID support

### TUI Features and Architecture
- **Main Application**: `can_tui/app.py` - Core Textual app with async message handling
- **Custom Widgets**: 
  - `MessageLogWidget`: Real-time scrolling message display with syntax highlighting
  - `CommandInputWidget`: CAN command input with validation and history
  - `SettingsModal`: Port/baud rate configuration with device detection (Escape to close)
  - `HelpModal`: Comprehensive help dialog with keyboard shortcuts and command reference (F4 or Escape to close)
  - `CustomHeader`: Application header with menu button
  - `SwitchViewWidget`: Example custom view widget showing switch states for CAN ID 0x500
- **Interactive Filtering**: Real-time message type filtering with clickable ON/OFF controls in sidebar
- **Services**: `SerialService` handles async serial I/O and reconnection logic
- **Message Processing**: Full CAN message parsing with protocol-specific interpreters
- **View System**: Modular architecture for custom CAN ID-specific visualizations
- **Keyboard Shortcuts**: 
  - F1: Clear messages, F2: Save log, F3: Pause/Resume, F4: Help modal, F5: Settings
  - Ctrl+C: Quit, Ctrl+R: Reconnect, Escape: Close modals

## Testing Approach

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_parsers.py

# Run message filter tests
pytest tests/test_message_filter.py

# Run simple filter tests (no pytest dependency)
python3 can_tui/tests/test_filter_simple.py

# Run with coverage
pytest --cov=can_tui tests/
```

## Configuration

- **Parser mappings**: `parser_config.yaml` - CAN ID to parser mappings with confidence thresholds
- **Logging**: Dual logging to console and `can.log` file with different levels
- **Serial settings**: Default 115200 baud, configurable via GUI or command line

## TUI Application Usage

### Startup Options
- **Interactive mode**: `python -m can_tui.main` - Shows port selection dialog
- **Direct connect**: `python -m can_tui.main -p /dev/ttyACM0` - Connects directly to specified port
- **Custom baud**: `python -m can_tui.main -p /dev/ttyACM0 -b 230400`

### Key Features
- **Real-time Message Display**: Color-coded CAN RX/TX messages with timestamps
- **Command Interface**: Send CAN messages directly via bottom input field
- **Statistics Panel**: Live connection status, message counts, and data rates
- **Export Functionality**: Save message logs as CSV files with timestamps
- **Interactive Message Filtering**: Click checkboxes to toggle display of RX, TX, error, and info messages in real-time
- **Smart Reconnection**: Automatic reconnection with exponential backoff
- **Cross-Platform Serial**: Works with USB, UART, and virtual COM ports

### Hardware Setup Examples

#### Raspberry Pi Pico + MCP2551
- Connections: GP4 (CAN TX) → MCP2551 TXD, GP5 (CAN RX) → MCP2551 RXD
- Power: 3.3V and GND to MCP2551
- CAN bus: CANH/CANL to bus with 120Ω termination

#### Adafruit Feather M4 CAN
- Built-in CAN peripheral with integrated transceiver
- NeoPixel visual feedback: Green (TX), Yellow (RX), Red (Error)
- USB power and programming interface
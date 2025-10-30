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
- **LilyGo T-CAN485 (ESP32)** with built-in TWAI + RS485 + SD card + WS2812
- **LilyGo T-Panel (ESP32-S3)** with built-in TWAI + 480x480 touchscreen + SD card
- **STM32** with built-in CAN peripheral (future)

### Firmware Architecture (src/*)

**Three-Layer Architecture** for maximum code reuse:

1. **Platform Layer** (`src/capabilities/<chip>/`) - Chip-level APIs shared by all boards using the same MCU
   - GPIO, PWM, ADC, CAN/TWAI controller access
   - Platform-specific action managers (ESP32ActionManager, RP2040ActionManager, SAMD51ActionManager)
   - Examples: `src/capabilities/esp32/`, `src/capabilities/rp2040/`, `src/capabilities/samd51/`

2. **Board Layer** (`src/boards/<product>/`) - Product-specific peripherals and features
   - Each physical board product gets its own folder named by product (not chip)
   - Handles unique peripherals (RS485, displays, SD cards, power management)
   - Implements `BoardInterface` for initialization, custom commands, periodic tasks
   - Examples: `src/boards/t_can485/` (RS485+SD), `src/boards/t_panel/` (touchscreen+display)

3. **Application Layer** (`src/main.cpp`) - Hardware-agnostic application logic
   - Protocol handling, action system, rule engine
   - Zero platform/board-specific code via abstraction layers

**Additional Architecture:**
- **Hardware Abstraction Layer (HAL)**: `src/hal/` provides platform-agnostic CAN interface
- **Platform Detection**: Automatic detection based on compile-time defines
- **Unified Protocol**: Implements full PROTOCOL.md specification
- **Multi-Environment Build**: PlatformIO configuration for all supported boards

### Key Architecture Patterns

**Factory Pattern (Firmware)**
- `CANFactory::create()` in `src/hal/can_factory.h` instantiates the correct platform-specific CAN implementation
- Compile-time platform detection via `platform_config.h` selects RP2040CAN, SAMD51CAN, etc.
- All implementations inherit from abstract `CANInterface` base class

**Registry Pattern (TUI)**
- `ModernViewRegistry` routes CAN messages to appropriate custom views based on CAN ID
- `ParserRegistry` manages message parsers with priority-based selection
- Both use priority systems to handle overlapping CAN ID ranges

**Auto-Discovery Pattern (TUI)**
- Views in `can_tui/views/view_*.py` are automatically discovered at startup
- No manual registration needed - just create file following naming convention
- Each view declares supported CAN IDs via `get_supported_can_ids()`

### Message Flow Architecture

**Firmware → TUI Flow:**
1. `CANInterface` receives message from hardware CAN controller
2. Firmware formats as protocol message (e.g., `CAN_RX;0x123;01,02,03,04`)
3. Sent over USB serial to TUI

**TUI Message Processing Flow:**
1. `SerialService` receives raw serial line
2. Protocol parser converts to `CANMessage` object
3. `ModernViewRegistry` checks if any view handles this CAN ID (by priority)
4. If view found: View's `parse_message()` called → widget updated
5. If no view: `ParserRegistry` finds best parser (by confidence) → log updated
6. `MessageLogWidget` always receives message for display

**TUI → Firmware Flow:**
1. User types command in `CommandInputWidget` (e.g., `send:0x123:01,02,03`)
2. Command validated and sent to `SerialService`
3. Firmware receives command via serial
4. Firmware parses and executes (e.g., calls `send_message()` on `CANInterface`)
5. Firmware sends `CAN_TX` confirmation back to TUI

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

**Note**: Use WSL on Windows for best compatibility with Linux toolchains.

```bash
# Build for Raspberry Pi Pico (default)
pio run -e pico

# Build for Adafruit Feather M4 CAN
pio run -e feather_m4_can

# Build variants for Feather M4 CAN
pio run -e feather_m4_can_debug        # Debug build with verbose output
pio run -e feather_m4_can_250k         # 250kbps CAN bitrate
pio run -e feather_m4_can_1m           # 1Mbps CAN bitrate
pio run -e feather_m4_can_no_neopixel  # Disable NeoPixel for power savings

# Build for ESP32 boards
pio run -e esp32_t_can485              # LilyGo T-CAN485 (CAN + RS485 + SD)
pio run -e esp32_t_panel               # LilyGo T-Panel (touchscreen + CAN)

# Upload to specific board
pio run -e pico --target upload
pio run -e feather_m4_can --target upload
pio run -e esp32_t_can485 --target upload
pio run -e esp32_t_panel --target upload

# Monitor serial output (all platforms use 115200 baud)
pio device monitor -b 115200

# Clean all environments
pio run --target clean
```

### VSCode Integration

The project includes PlatformIO integration. Use the PlatformIO extension for VSCode:
- **PlatformIO: Build** - Build current environment
- **PlatformIO: Upload** - Flash firmware to connected board
- **PlatformIO: Monitor** - Open serial monitor
- **PlatformIO: Clean** - Clean build artifacts

Or use command line (recommended for multi-board development):
```bash
# Build and upload in one command
pio run -e <board> --target upload

# Example: Build and flash T-CAN485
pio run -e esp32_t_can485 --target upload
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
- **RP2040**: ✅ Fully implemented using direct can2040 integration (Raspberry Pi Pico)
- **SAMD51**: ✅ Fully implemented using Adafruit CAN library (Feather M4 CAN)
- **ESP32**: ✅ Fully implemented using TWAI controller (T-CAN485, T-Panel)
  - T-CAN485: RS485, SD card, WS2812 RGB LED support
  - T-Panel: 480x480 touchscreen, SD card, LCD backlight control
- **STM32**: 🚧 Platform configuration ready, implementation needed

### Board-Specific Implementations

**Raspberry Pi Pico** (`src/boards/rpi_pico/`)
- Simple GPIO LED blinking on pin 25
- Minimal board implementation demonstrating the pattern

**Adafruit Feather M4 CAN** (`src/boards/feather_m4_can/`)
- NeoPixel RGB status indication
- Custom NeoPixel color control commands
- 6-color cycling status display

**LilyGo T-CAN485** (`src/boards/t_can485/`)
- RS485 transceiver with automatic direction control
- SD card logging with timestamp support
- WS2812 RGB LED with 4-color cycling
- ME2107 power management

**LilyGo T-Panel** (`src/boards/t_panel/`)
- 480x480 ST7701S touchscreen display
- CST3240 capacitive touch controller
- LCD backlight PWM control with smooth pulsing
- SD card storage support

### Adafruit Feather M4 CAN Build Variants

The Feather M4 CAN has several pre-configured build environments:

| Environment | CAN Bitrate | Features | Use Case |
|------------|-------------|----------|----------|
| `feather_m4_can` | 500kbps | Standard build with NeoPixel | General purpose |
| `feather_m4_can_debug` | 500kbps | Debug symbols, verbose output | Development/debugging |
| `feather_m4_can_250k` | 250kbps | Standard build | Lower-speed CAN networks |
| `feather_m4_can_1m` | 1Mbps | Standard build | High-speed CAN networks |
| `feather_m4_can_no_neopixel` | 500kbps | NeoPixel disabled | Power-sensitive applications |

**Build Defines Available:**
- `DEFAULT_CAN_BITRATE` - Sets default CAN bus speed (125000, 250000, 500000, 1000000)
- `DEBUG_SERIAL` - Enable verbose serial debug output
- `DEBUG_CAN` - Enable CAN-specific debug messages
- `DISABLE_NEOPIXEL` - Disable NeoPixel visual feedback for power savings

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
- **Widget Integration**: Each view associates with a Textual widget for UI rendering via `create_widget()`
- **Self-Contained Parsing**: Views implement their own `parse_message()` method, making them independent of external parsers
- **Example Implementation**: `HarnessSwitchView` subscribes to CAN ID 0x500 and displays switch states

#### View vs Parser Distinction
- **Views**: CAN ID-specific visualizations with integrated parsing logic (e.g., gauge, switch panel)
- **Parsers**: General-purpose message interpreters registered in `parser_config.yaml`
- Views take priority over parsers for their declared CAN IDs
- Views are self-contained: parsing + visualization in one module

#### Creating Custom Views
1. Create `view_yourname.py` in `can_tui/views/` inheriting from `BaseView`
2. Implement required methods: `get_view_name()`, `get_supported_can_ids()`, `create_widget()`, `parse_message()`
3. Create corresponding widget in `can_tui/widgets/` using Textual components (or compose inline)
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

#### LilyGo T-CAN485
- Built-in TWAI (CAN) controller with transceiver (GPIO27 TX, GPIO26 RX)
- RS485 transceiver (GPIO22 TX, GPIO21 RX, GPIO17 enable)
- WS2812 RGB LED on GPIO4
- SD card slot (CS=GPIO13)
- ME2107 power enable on GPIO16
- All peripherals pre-wired - just connect CANH/CANL and RS485 A/B

#### LilyGo T-Panel
- Built-in TWAI (CAN) controller (requires external transceiver)
- 480x480 ST7701S touchscreen display
- CST3240 capacitive touch (I2C)
- LCD backlight control on GPIO33
- SD card slot (CS=GPIO34)
- USB-C power and programming
# CAN Bridge TUI Design Plan

## Overview
A modern, intuitive Terminal User Interface (TUI) for interacting with the USB-to-CAN bridge, replacing the basic screen terminal with a feature-rich, color-coded interface for real-time CAN message monitoring and transmission.

## Framework Selection
**Choice: Rich/Textual**
- ✅ Modern Python TUI framework with excellent layout system
- ✅ Built-in color support, widgets, and responsive design
- ✅ Easy to implement complex layouts with panels
- ✅ Great documentation and active development
- ✅ Supports async operations for real-time updates

**Alternatives considered:**
- `curses`: Too low-level, complex color/layout management
- `prompt_toolkit`: Good for input but limited layout capabilities

## Layout Design

### Primary Layout (Split Screen)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAN Bridge Monitor v1.0                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─── RX Messages (75% width) ────────┐  ┌─── Controls (25% width) ───┐    │
│  │ 🟢 RX: ID=0x123 LEN=8             │  │ 📊 Statistics              │    │
│  │    DATA: 01 02 03 04 05 06 07 08  │  │ ├─ RX Count: 1,234         │    │
│  │    TIME: 14:32:15.123             │  │ ├─ TX Count: 567           │    │
│  │                                   │  │ ├─ Error Count: 2          │    │
│  │ 🔵 TX: ID=0x456 LEN=4             │  │ └─ Rate: 15.2 msg/s        │    │
│  │    DATA: DE AD BE EF              │  │                            │    │
│  │    TIME: 14:32:16.001 ✓          │  │ 🎛️  Quick Actions           │    │
│  │                                   │  │ ├─ [F1] Clear Messages     │    │
│  │ ❌ ERROR: Failed to send 0x789    │  │ ├─ [F2] Save Log           │    │
│  │    TIME: 14:32:17.500             │  │ ├─ [F3] Pause/Resume       │    │
│  │                                   │  │ └─ [F4] Filters            │    │
│  │ 🟢 RX: ID=0x234 LEN=6             │  │                            │    │
│  │    DATA: AA BB CC DD EE FF        │  │ 🔍 Message Filters          │    │
│  │    TIME: 14:32:18.750             │  │ ├─ Show RX: ☑              │    │
│  │                                   │  │ ├─ Show TX: ☑              │    │
│  │ [Scroll: ↑↓] [Search: /]          │  │ ├─ Show Errors: ☑          │    │
│  └───────────────────────────────────┘  │ └─ ID Filter: [___]        │    │
│                                         │                            │    │
│  ┌─── Command Input ───────────────────────────────────────────────────────┐ │
│  │ Command: send:123:DEADBEEF                                          _   │ │
│  │                                                                         │ │
│  │ [Enter] Send  [Tab] Autocomplete  [↑↓] History  [Ctrl+C] Quit          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Alternative Compact Layout (Single Panel)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CAN Monitor │ 🟢 Connected │ 500kbps │ RX:1234 TX:567 ERR:2 │ 15.2 msg/s   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🟢 14:32:15.123 RX ID=0x123 [8] 01 02 03 04 05 06 07 08                   │
│ 🔵 14:32:16.001 TX ID=0x456 [4] DE AD BE EF ✓                             │
│ ❌ 14:32:17.500 ERR Failed to send ID=0x789                                 │
│ 🟢 14:32:18.750 RX ID=0x234 [6] AA BB CC DD EE FF                         │
│ 🟢 14:32:19.100 RX ID=0x345 [8] 11 22 33 44 55 66 77 88                   │
│                                                                             │
│ [1000+ more messages...]                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ > send:123:DEADBEEF_                                                        │
│ [Enter] Send [↑↓] History [F1] Help [F2] Clear [Ctrl+C] Quit              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Color Scheme

### Message Types
- 🟢 **RX Messages**: Bright Green (`#00FF7F`)
- 🔵 **TX Messages**: Bright Blue (`#1E90FF`)
- ❌ **Errors**: Bright Red (`#FF4444`)
- ⚠️ **Warnings**: Orange (`#FF8C00`)
- ℹ️ **Info**: Cyan (`#00FFFF`)

### Interface Elements
- **Background**: Dark Gray (`#1E1E1E`)
- **Panel Borders**: Light Gray (`#666666`)
- **Text**: White (`#FFFFFF`)
- **Highlights**: Yellow (`#FFFF00`)
- **Input Field**: Dark Blue background (`#003366`)
- **Status Bar**: Dark Green (`#006600`)

### Data Formatting
- **CAN ID**: Bold, colored by message type
- **Data Bytes**: Monospace, alternating light/dark gray for readability
- **Timestamps**: Dim gray
- **Success Indicators**: Green checkmarks ✓
- **Error Indicators**: Red X ❌

## Core Features

### 1. Real-time Message Display
- **Auto-scrolling message log** with newest messages at bottom
- **Timestamp** for each message (HH:MM:SS.mmm format)
- **Message parsing** from firmware format: `RX: ID=0x123 LEN=8 DATA=0102030405060708`
- **Smooth scrolling** without flicker
- **Message buffering** (configurable, default 10,000 messages)

### 2. Command Input System
- **Smart command input** with validation
- **Auto-completion** for `send:` commands
- **Command history** (up/down arrows)
- **Input validation** before sending
- **Error feedback** for malformed commands

### 3. Serial Communication
- **Auto-detection** of CAN bridge device
- **Robust connection handling** with reconnection
- **Non-blocking I/O** to prevent UI freezing
- **Connection status indicator**
- **Configurable baud rate** (default 115200)

### 4. Message Management
- **Message filtering** by type (RX/TX/Errors)
- **ID-based filtering** (show only specific CAN IDs)
- **Search functionality** (Ctrl+F)
- **Message copying** to clipboard
- **Export to file** (CSV, JSON, raw text)

### 5. Statistics Tracking
- **Real-time counters**: RX, TX, Error counts
- **Message rate calculation** (messages per second)
- **Session duration tracking**
- **Bus utilization estimation**

## Nice-to-Have Features

### Phase 2 Enhancements
1. **Message Inspector Panel**
   - Click message to see detailed breakdown
   - Binary/hex/ASCII data views
   - CAN frame format visualization
   - Message timing analysis

2. **Advanced Filtering**
   - Regular expression filters
   - Time-range filtering
   - Message content filtering
   - Save/load filter presets

3. **Bookmarks & Quick Actions**
   - Bookmark frequently used CAN IDs
   - Quick-send buttons for common messages
   - Message templates/macros
   - Keyboard shortcuts for everything

4. **Enhanced Input Features**
   - **Tab completion** for CAN IDs from message history
   - **Input validation** with real-time feedback
   - **Command aliases** for complex messages
   - **Multi-message sequences**

5. **Data Analysis Tools**
   - **Message frequency analysis** (histogram view)
   - **Bus timing analysis**
   - **Error pattern detection**
   - **Message correlation analysis**

### Phase 3 Advanced Features
1. **Session Management**
   - Save/restore entire sessions
   - Session comparison tools
   - Automated session logging
   - Session replay functionality

2. **Protocol Analysis**
   - **DBC file support** for message decoding
   - **Known protocol detection** (OBD-II, J1939, etc.)
   - **Signal extraction** and visualization
   - **Message sequence analysis**

3. **Integration Features**
   - **Web API** for remote monitoring
   - **Plugin system** for custom analyzers
   - **Export to other tools** (Wireshark, CANalyzer)
   - **MQTT/REST integration**

4. **UI Enhancements**
   - **Multiple themes** (dark, light, high contrast)
   - **Configurable layouts**
   - **Resizable panels**
   - **Full-screen message view**

## Technical Implementation

### Dependencies
```python
# Core requirements
textual>=0.45.0      # Modern TUI framework
pyserial>=3.5        # Serial communication
rich>=13.0.0         # Text formatting and colors

# Optional enhancements
click>=8.0.0         # CLI argument parsing
pydantic>=2.0.0      # Configuration validation
tomli>=2.0.0         # TOML config files
```

### File Structure
```
can_tui/
├── __init__.py
├── main.py              # Entry point and CLI
├── app.py               # Main TUI application class
├── widgets/
│   ├── __init__.py
│   ├── message_log.py   # Message display widget
│   ├── command_input.py # Command input widget
│   ├── statistics.py    # Stats panel widget
│   └── filters.py       # Filter controls widget
├── models/
│   ├── __init__.py
│   ├── can_message.py   # CAN message data models
│   └── config.py        # Configuration models
├── services/
│   ├── __init__.py
│   ├── serial_service.py # Serial communication
│   ├── message_parser.py # Parse CAN messages
│   └── export_service.py # Data export functionality
├── utils/
│   ├── __init__.py
│   ├── formatters.py    # Message formatting utilities
│   └── validators.py    # Input validation
└── config/
    ├── default.toml     # Default configuration
    └── keybindings.toml # Keyboard shortcuts
```

### Configuration System
```toml
# ~/.can_tui/config.toml
[connection]
port = "/dev/ttyACM0"
baudrate = 115200
timeout = 1.0
auto_reconnect = true

[display]
theme = "dark"
max_messages = 10000
timestamp_format = "HH:MM:SS.mmm"
show_raw_data = false

[filters]
default_show_rx = true
default_show_tx = true
default_show_errors = true

[export]
default_format = "csv"
include_timestamps = true
auto_save_session = false

[keybindings]
quit = "ctrl+c"
clear = "f1"
save = "f2"
pause = "f3"
filters = "f4"
search = "ctrl+f"
```

### Performance Considerations
- **Async message handling** to prevent UI blocking
- **Efficient message storage** with circular buffer
- **Lazy rendering** for large message lists
- **Debounced updates** for high-frequency messages
- **Memory management** with automatic cleanup

### Error Handling
- **Graceful connection failures** with retry logic
- **Invalid message handling** without crashes
- **Serial port error recovery**
- **User-friendly error messages**
- **Comprehensive logging** for debugging

## User Experience

### Startup Flow
1. **Auto-detect** CAN bridge device
2. **Show connection status** in real-time
3. **Display welcome message** with help hints
4. **Begin message monitoring** immediately
5. **Ready for user commands**

### Keyboard Shortcuts
- `Enter`: Send command
- `Ctrl+C`: Quit application
- `F1`: Clear message log
- `F2`: Save session to file
- `F3`: Pause/resume message capture
- `F4`: Toggle filter panel
- `Ctrl+F`: Search messages
- `↑↓`: Navigate command history
- `Tab`: Auto-complete commands
- `PgUp/PgDn`: Scroll message log
- `Ctrl+L`: Refresh/redraw screen

### Help System
- **Contextual help** hints in each panel
- **F1 help overlay** with all shortcuts
- **Command syntax help** in input field
- **Status line** with current mode/action

## Implementation Phases

### Phase 1: Core TUI (MVP)
- ✅ Basic layout with message log and input
- ✅ Serial communication with CAN bridge
- ✅ Message parsing and display
- ✅ Command input with basic validation
- ✅ Color-coded message types
- ✅ Real-time message updates

### Phase 2: Enhanced Features
- ✅ Statistics panel with counters
- ✅ Message filtering capabilities
- ✅ Command history and auto-completion
- ✅ Export functionality
- ✅ Search within messages
- ✅ Configuration file support

### Phase 3: Advanced Features
- ✅ Message inspector panel
- ✅ Advanced filtering options
- ✅ Session management
- ✅ Performance optimizations
- ✅ Plugin system foundation

## Success Metrics
- **Usability**: Can send/receive CAN messages intuitively
- **Performance**: Handle 1000+ messages/second without lag
- **Reliability**: No crashes during extended use
- **User Satisfaction**: Prefer TUI over basic terminal
- **Feature Completeness**: Covers 90% of common CAN debugging tasks

## Future Extensions
- **Mobile app** for remote monitoring
- **Web dashboard** version
- **Hardware integration** with other CAN tools
- **AI-powered** message analysis
- **Multi-bus support** for complex systems

---

**This TUI will transform the CAN debugging experience from a basic command-line tool into a professional, feature-rich monitoring solution that rivals commercial CAN analysis tools.**
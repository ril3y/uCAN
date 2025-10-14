# USB-to-CAN Bridge Project Status

## Project Overview
Building a USB-to-CAN adapter using Raspberry Pi Pico with PIO-based CAN implementation and MCP2551 transceiver.

## ✅ Completed Tasks

### Hardware Setup
- [x] Raspberry Pi Pico identified (Bus 001 Device 028: ID 2e8a:000a)
- [x] MCP2551 transceiver pinout defined (GP4=CTX, GP5=CRX)
- [x] Hardware connection plan confirmed

### Development Environment
- [x] PlatformIO installed and configured
- [x] Project structure created in `/home/ril3y/RPICAN/UCAN/`
- [x] Arduino framework with earlephilhower core configured
- [x] Udev rules installed for device permissions
- [x] Build pipeline working (firmware.uf2 generation successful)
- [x] Upload process working (via BOOTSEL mode)

### Basic Firmware
- [x] Simple test firmware created and uploaded
- [x] USB serial communication working (115200 baud)
- [x] Command parsing functional (`test` command works)
- [x] LED blinking as heartbeat indicator

### Research & Library Analysis
- [x] Found can2040 - PIO-based CAN implementation for RP2040
- [x] Identified ACAN2040 as Arduino wrapper for can2040
- [x] Discovered compatibility issues with current framework versions
- [x] API documentation reviewed for both libraries

## ❌ Pending Tasks

### CAN Implementation
- [ ] Resolve ACAN2040 compatibility issues OR find alternative
- [ ] Implement working CAN initialization (500kbps)
- [ ] Set up CAN message receive functionality
- [ ] Set up CAN message transmit functionality
- [ ] Test basic CAN loopback

### USB-to-CAN Bridge Protocol
- [ ] Implement CAN → USB message forwarding
  - Format: `C:ID:LEN:DATA` (e.g., `C:123:8:0102030405060708`)
- [ ] Implement USB → CAN message sending
  - Format: `S:ID:LEN:DATA` (e.g., `S:123:8:0102030405060708`)
- [ ] Add error handling and status responses
- [ ] Add message validation and bounds checking

### Advanced Features
- [ ] Support for extended CAN IDs (29-bit)
- [ ] Timestamp support for received messages
- [ ] CAN bus statistics and error reporting
- [ ] Configuration commands (bitrate, filters, etc.)
- [ ] Binary output mode option

### Testing & Validation
- [ ] Test with actual CAN bus hardware
- [ ] Validate message timing and throughput
- [ ] Test error conditions and recovery
- [ ] Integration testing with receiving board

## 🔧 Current Technical Status

### Working Components
- **Hardware**: Raspberry Pi Pico + MCP2551 transceiver
- **Firmware**: Basic Arduino framework with USB serial
- **Build System**: PlatformIO with earlephilhower core
- **Communication**: USB CDC serial at 115200 baud

### Known Issues
- **ACAN2040 Library**: Compatibility issues with current Arduino framework
  - Error: `struct pio_sm_hw` type conflicts
  - Error: API method mismatches
- **Alternative Needed**: Direct can2040 integration or different library

### Next Steps Priority
1. **HIGH**: Find working CAN library or implement direct can2040 integration
2. **HIGH**: Get basic CAN send/receive working
3. **MEDIUM**: Implement USB-to-CAN protocol
4. **LOW**: Add advanced features and testing

## 📁 File Structure
```
/home/ril3y/RPICAN/UCAN/
├── platformio.ini          # PlatformIO configuration
├── src/main.cpp            # Main firmware (currently test version)
├── include/                # Header files
├── lib/                    # Project libraries
├── test/                   # Unit tests
└── .pio/build/pico/        # Build output
    └── firmware.uf2        # Flashable firmware
```

## 🔗 Hardware Connections
- **GP4** → MCP2551 CTX (CAN TX)
- **GP5** → MCP2551 CRX (CAN RX)
- **MCP2551 VCC** → 3.3V or 5V
- **MCP2551 GND** → Ground
- **MCP2551 CANH/CANL** → CAN bus lines
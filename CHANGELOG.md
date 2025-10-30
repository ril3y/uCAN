# Changelog

All notable changes to the uCAN firmware project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2025-01-28

### Added - RP2040 Platform Parity
- **RP2040 Flash Persistence**: Complete flash storage implementation for Raspberry Pi Pico
  - Device names now persist across power cycles (saved to flash at 0x101FF000)
  - Action rules persist in flash alongside device name in unified FlashHeader
  - Uses pico-sdk `hardware_flash` API with proper XIP interrupt handling
  - 4KB flash sector at end of 2MB flash (last sector before EEPROM)
  - See [docs/RP2040_FLASH_STORAGE.md](docs/RP2040_FLASH_STORAGE.md) for technical details

- **Hardware Information in CAPS Response**: Platform-specific hardware details now included
  - RP2040: Exposes `can_tx_pin` (GP4), `can_rx_pin` (GP5), transceiver type, and CAN implementation
  - SAMD51: Exposes CAN controller, peripheral type, and transceiver info
  - Queryable via `get:capabilities` command for runtime hardware discovery

- **RP2040 Hardware Documentation**: Comprehensive wiring and setup guide
  - Pin mapping diagrams for RP2040 + MCP2551 CAN transceiver
  - Hardware connection tables with physical pin numbers
  - CAN bus termination and bitrate configuration instructions
  - Troubleshooting guide for common hardware issues
  - See [docs/RP2040_HARDWARE.md](docs/RP2040_HARDWARE.md)

### Changed
- RP2040 now has full feature parity with SAMD51 (where hardware permits)
  - Flash storage: ✅ Implemented
  - Device name persistence: ✅ Implemented
  - Hardware documentation: ✅ Complete
  - Action rules persist: ✅ Works across reboots

### Technical Details
- Added `rp2040_flash_storage.cpp` with complete flash read/write/erase implementation
- Updated `rp2040_action_manager.cpp` to integrate flash storage
- Added `CAP_FLASH_STORAGE` flag to `rp2040_capabilities.cpp`
- Enhanced platform_config.h with detailed MCP2551 pin documentation
- Modified `capability_query.cpp` to include hardware-specific information in CAPS JSON

## [2.1.1] - 2025-01-28

### Fixed
- CAPS response now correctly returns custom device name set via `set:name` command
  - Previously always returned the default board name from platform capabilities
  - Now uses `get_device_name()` which returns custom name if set, otherwise default
  - This fixes the issue where device name appeared to revert after querying capabilities

## [2.1.0] - 2025-01-28

### Added
- Device name management commands: `set:name` and `get:name`
  - Set custom device name that persists during runtime (volatile RAM storage)
  - Get current device name (returns custom name or default board name)
  - Maximum name length: 31 characters (auto-truncated if longer)
  - Empty name (`set:name:`) restores default board name
- `max_rules` field in CAPS response showing platform-specific action rule limits
  - SAMD51 (Feather M4 CAN): 64 rules
  - RP2040 (Raspberry Pi Pico): 16 rules
  - ESP32: 32 rules (when implemented)

### Changed
- Improved test reliability with better serial port timeout handling
- Increased serial port settle time to 2.0s for device stability

### Known Limitations
- Device name persistence to flash storage not yet implemented
- Name resets to default after power cycle or reset

## [2.0.0] - 2025-01-27

### Added
- Initial Protocol v2.0 implementation
- Multi-platform support (SAMD51, RP2040)
- Hardware-independent unit tests (269 tests)
- GitHub Actions CI/CD workflow for automated builds
- UF2 firmware releases for drag-and-drop installation

### Changed
- Complete protocol rewrite from v1.0
- JSON-based capabilities and action definitions
- Improved error handling and validation

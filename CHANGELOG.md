# Changelog

All notable changes to the uCAN firmware project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

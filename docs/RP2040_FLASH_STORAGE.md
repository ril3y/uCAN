# RP2040 Flash Storage Implementation

## Overview

This document describes the flash persistence system implemented for the RP2040 platform, which provides non-volatile storage for action rules and device names. The implementation mirrors the SAMD51 flash storage design but uses the RP2040's built-in 2MB flash memory instead of external SPI flash.

## Architecture

### Flash Layout

The RP2040 flash storage uses the **last 4KB sector** of the 2MB flash memory to store persistent data:

```
Flash Memory Map (2MB total):
├─ 0x10000000 - 0x101FEFFF: Firmware code and data
└─ 0x101FF000 - 0x101FFFFF: Persistent storage sector (4KB)
   ├─ FlashHeader (variable size)
   └─ ActionRule array (up to 16 rules)
```

**Key Addresses:**
- Flash base address (XIP_BASE): `0x10000000`
- Storage sector offset: `0x001FF000` (last 4KB)
- Storage memory-mapped address: `0x101FF000`

### Data Structures

#### FlashHeader

Stored at the beginning of the storage sector:

```cpp
struct FlashHeader {
    uint32_t magic;           // 0x55434154 ("UCAN" in hex)
    uint8_t version;          // Storage format version (currently 1)
    uint8_t rule_count;       // Number of stored rules (0-16)
    uint8_t reserved[2];      // Reserved for future use
    char device_name[32];     // User-configurable device name
};
```

#### Storage Layout

```
[FlashHeader]
├─ Magic number (4 bytes): Validates data integrity
├─ Version (1 byte): Format compatibility check
├─ Rule count (1 byte): Number of valid rules
├─ Reserved (2 bytes): Future expansion
└─ Device name (32 bytes): Custom device identifier

[ActionRule Array]
├─ ActionRule[0] (variable size)
├─ ActionRule[1]
├─ ...
└─ ActionRule[15] (max 16 rules on RP2040)
```

## Implementation Details

### File: `src/capabilities/rp2040_flash_storage.cpp`

This file contains the complete flash storage implementation:

#### Key Functions

1. **`init_flash_storage()`**
   - Validates flash parameters and storage area accessibility
   - Verifies sector alignment
   - Returns true if storage is ready

2. **`save_rules_to_flash(rules, count)`**
   - Prepares a 4KB sector buffer in RAM
   - Writes FlashHeader with device name
   - Copies action rules after header
   - **Critical section**: Disables interrupts during flash operations
   - Erases the storage sector (required before write)
   - Programs the entire sector in one operation
   - Verifies write success by reading back magic number
   - Returns true on success

3. **`load_rules_from_flash(rules, max_count)`**
   - Reads FlashHeader from memory-mapped flash
   - Validates magic number and version
   - Loads device name into global variable
   - Copies rules to provided array
   - Returns number of rules loaded (0 if empty)

4. **`erase_flash_storage()`**
   - Erases the storage sector (sets all bytes to 0xFF)
   - **Critical section**: Disables interrupts briefly
   - Verifies erase by checking magic number is gone
   - Returns true on success

5. **`get_flash_storage_stats(used_bytes, total_bytes, rule_capacity)`**
   - Returns flash usage statistics
   - Calculates current usage based on rule count
   - Provides total capacity information
   - Useful for diagnostics and monitoring

### Hardware Considerations

#### RP2040 Flash Specifications

- **Flash size**: 2MB (2,097,152 bytes)
- **Sector size**: 4KB (4,096 bytes)
- **Page size**: 256 bytes
- **Erase cycles**: ~100,000 per sector
- **Write granularity**: 256-byte pages

#### Critical Sections

Flash operations on the RP2040 **require disabling interrupts** because:
1. Flash is memory-mapped for execution (XIP - Execute In Place)
2. Writing to flash requires brief cache invalidation
3. Any attempt to execute code from flash during write will crash
4. This includes USB interrupts, CAN interrupts, and timers

**Impact**: Flash operations pause all interrupts for ~100ms during erase/write.

**Mitigation**:
- Flash operations are only performed on explicit user commands (save)
- Not used in time-critical paths
- USB and CAN will recover automatically after operation completes

### Wear Leveling Strategy

#### Current Implementation (Basic)

- **Write-only-on-change**: Rules are only saved when explicitly commanded
- **No background writes**: Eliminates unnecessary wear
- **Manual trigger**: User must send `action:save` command

#### Future Enhancements (If Needed)

If write frequency becomes an issue (>100 writes/day), consider:

1. **Multi-sector rotation**: Use multiple 4KB sectors, rotate on each write
2. **Wear tracking**: Store write count in header, warn at 80% of cycle limit
3. **Differential writes**: Only update changed rules instead of entire sector

**Current assessment**: With typical usage (<10 saves per day), the sector will last **>27 years**.

## Integration Points

### 1. RP2040 Action Manager

**File**: `src/capabilities/rp2040/rp2040_action_manager.cpp`

```cpp
bool RP2040ActionManager::save_rules_impl() {
    // Triggers flash write with all active rules and device name
    return save_rules_to_flash(rules_, get_rule_count());
}

uint8_t RP2040ActionManager::load_rules_impl() {
    // Loads rules and device name on startup
    return load_rules_from_flash(rules_, MAX_ACTION_RULES);
}
```

**Behavior**:
- `save_rules_impl()` is called when user sends `action:save` command
- `load_rules_impl()` is called once during firmware startup
- Device name is automatically saved/loaded alongside rules

### 2. Board Capabilities

**File**: `src/capabilities/board_capabilities.h`

Added RP2040 flash function declarations:

```cpp
#ifdef PLATFORM_RP2040
bool init_flash_storage();
bool save_rules_to_flash(const ActionRule* rules, uint8_t count);
uint8_t load_rules_from_flash(ActionRule* rules, uint8_t max_count);
bool erase_flash_storage();
bool get_flash_storage_stats(uint32_t* used_bytes, uint32_t* total_bytes,
                             uint8_t* rule_capacity);
#endif
```

### 3. Device Name Persistence

**File**: `src/capabilities/capability_query.cpp`

```cpp
bool save_device_name() {
    #elif defined(PLATFORM_RP2040)
        // RP2040: Device name saved in FlashHeader alongside rules
        return action_manager->save_rules();
    #endif
}
```

**Behavior**:
- Device name changes trigger full rule save
- Name is stored in FlashHeader
- Loaded automatically with rules on startup

### 4. Platform Capabilities

**File**: `src/capabilities/rp2040_capabilities.cpp`

Added `CAP_FLASH_STORAGE` flag:

```cpp
.capability_flags = CAP_GPIO_DIGITAL |
                   CAP_GPIO_PWM |
                   CAP_GPIO_ANALOG |
                   CAP_CAN_SEND |
                   CAP_FLASH_STORAGE,  // NEW
```

**Effect**:
- TUI now shows "FLASH" in features list for RP2040
- `get caps` command reports flash storage capability
- Action save/load commands are enabled

## User Commands

### Save Rules and Device Name

```
action:save
```

**Response**:
```
STATUS;SAVE;Rules saved to flash: 3 rules
```

### Load Rules (Automatic on Startup)

Rules are loaded automatically during firmware initialization. Manual load not exposed to users.

### Set Device Name (Auto-saves)

```
set_name:MyCanBridge
```

**Response**:
```
STATUS;NAME_SET;Device name set to: MyCanBridge (saved to flash)
```

### Query Capabilities

```
get caps
```

**Response includes**:
```json
{
  "features": ["action_system", "rules_engine", "GPIO", "PWM", "ADC", "CAN_SEND", "FLASH"],
  "max_rules": 16,
  ...
}
```

## Testing Recommendations

### 1. Basic Functionality Test

```python
# Test sequence via Python TUI or serial terminal
1. Send "action:save" → Verify success response
2. Power cycle device
3. Send "action:list" → Verify rules persist
4. Send "set_name:TestDevice" → Verify name saved
5. Power cycle device
6. Send "get caps" → Verify device name is "TestDevice"
```

### 2. Boundary Condition Tests

```python
# Test maximum capacity
1. Add 16 rules (max for RP2040)
2. Send "action:save"
3. Verify all rules persist after power cycle

# Test empty flash
1. Flash fresh firmware
2. Send "action:list" → Should return 0 rules
3. Device name should be default "Raspberry Pi Pico"
```

### 3. Wear Test (Optional)

```python
# Verify flash endurance (only if concerned about wear)
for i in range(1000):
    send("action:save")
    time.sleep(0.5)
# All saves should succeed, no flash errors
```

### 4. Interrupt Recovery Test

```python
# Verify USB/CAN recover after flash operations
1. Start continuous CAN message stream
2. Send "action:save" during stream
3. Verify CAN messages resume after ~100ms pause
4. Verify no USB serial corruption
```

## Memory Usage

### Flash Storage Sector

- **Total available**: 4,096 bytes
- **FlashHeader size**: 40 bytes
- **ActionRule size**: ~60 bytes (structure-dependent)
- **Max rules (RP2040)**: 16
- **Total usage**: 40 + (16 × 60) = 1,000 bytes
- **Remaining space**: 3,096 bytes (75% unused, reserved for future expansion)

### RAM Usage

- **Sector buffer**: 4,096 bytes (allocated during save operation only)
- **Rules array**: 16 × 60 = 960 bytes (persistent in ActionManagerBase)
- **Total**: ~5KB RAM during save, ~1KB persistent

## Comparison with SAMD51

| Feature | RP2040 | SAMD51 |
|---------|--------|--------|
| Storage type | Internal flash | External SPI flash (2MB) |
| Storage location | Last 4KB sector | Start of SPI flash |
| Max rules | 16 | 64 |
| Flash size | 2MB (built-in) | 2MB (external) |
| Sector size | 4KB | 4KB |
| Erase cycles | ~100,000 | ~100,000 |
| Critical section | Yes (interrupts disabled) | No (independent flash) |
| Initialization | Auto (memory-mapped) | Required (SPI bus init) |
| API | Pico SDK hardware_flash | Adafruit_SPIFlash |

## Troubleshooting

### Symptom: Flash save fails silently

**Cause**: Flash storage offset not sector-aligned

**Solution**: Verify `FLASH_STORAGE_OFFSET % 4096 == 0` in `rp2040_flash_storage.cpp`

### Symptom: Device hangs during save

**Cause**: Interrupt conflict during flash operation

**Solution**: Ensure no high-priority interrupts are misconfigured. Flash operations automatically disable all interrupts.

### Symptom: Rules don't persist after power cycle

**Cause**: Magic number not written correctly

**Solution**: Check for build errors. Verify `save_rules_to_flash()` returns true. Use verbose mode to see flash write status.

### Symptom: Corrupted device name after save

**Cause**: Buffer overflow or null termination issue

**Solution**: Verify device name is always null-terminated before save. Max length is 31 chars + null terminator.

## Future Enhancements

### Planned Features

1. **Flash statistics command**: Expose `get_flash_storage_stats()` to users
2. **Wear monitoring**: Track write count, warn at 80% lifetime
3. **Backup/restore**: Export rules to CSV via serial, reimport later
4. **Multi-sector rotation**: If heavy write usage detected

### Protocol Extensions

Consider adding these commands:

```
flash_stats        → Returns usage and wear information
flash_erase        → Factory reset (clear all rules)
flash_test         → Verify flash integrity
```

## References

- [RP2040 Datasheet](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf) - Section 2.6 (Flash)
- [Pico SDK Documentation](https://www.raspberrypi.com/documentation/pico-sdk/) - hardware_flash API
- Arduino-Pico Framework: Uses Pico SDK flash functions directly
- UCAN Protocol: See `can_tui/PROTOCOL.md` for action system commands

## Change Log

- **2025-10-28**: Initial implementation by ril3y
  - Created `rp2040_flash_storage.cpp` with full persistence
  - Integrated with `RP2040ActionManager`
  - Added `CAP_FLASH_STORAGE` capability
  - Enabled device name persistence
  - Documented architecture and usage

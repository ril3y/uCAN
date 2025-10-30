# Configuration-Driven Firmware System

The uCAN firmware supports configuration-driven builds where default CAN rules can be pre-loaded from compile-time configuration headers. This is useful for creating simulation environments, test fixtures, or application-specific CAN devices.

## Architecture

### Configuration Headers (`src/configs/`)
Pure data configuration files that define:
- Default CAN messages to transmit
- Message intervals and data patterns
- GPIO pin assignments for reset buttons
- Configuration name and identity

### Platform Loaders (`src/capabilities/{platform}/`)
Platform-specific implementations that:
- Read configuration headers at compile-time
- Check flash for existing rules
- Write default rules to flash on first boot
- Provide reset-to-defaults functionality

### Build Variants (`platformio.ini`)
PlatformIO environments that enable configurations:
- `pico_golf_simulator` - RP2040 with golf cart CAN messages
- Add more variants for different configs or platforms

## Example: Golf Cart Simulator

### Configuration File
`src/configs/golf_cart_config.h` defines 10 realistic golf cart CAN messages:

```cpp
#define DEFAULT_CONFIG_NAME "Golf Cart Simulator"
#define DEFAULT_CONFIG_RESET_PIN 22  // GP22

static const DefaultRuleConfig default_rules[] = {
    // 10Hz telemetry messages (100ms interval)
    {0x500, 100, {0x00, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x03}, "Switch states"},
    {0x610, 100, {0x05, 0xDC, 0x32, 0x3C, 0x4B, 0x00, 0x00, 0x9E}, "Motor 1 telemetry"},
    {0x620, 100, {0x02, 0x00, 0xFE, 0xD4, 0x4B, 0x00, 0x00, 0x1D}, "BMS pack data"},
    // ... 10 messages total
};
```

### Build and Upload

```bash
# Build for RP2040 with golf cart configuration
pio run -e pico_golf_simulator

# Upload to Raspberry Pi Pico
pio run -e pico_golf_simulator --target upload

# Monitor serial output
pio device monitor -b 115200
```

### First Boot Behavior

On first boot (or with empty flash):
```
========================================
Configuration: Golf Cart Simulator
========================================
Platform: RP2040 @ 133 MHz
Reset Pin: GP22

Status: Initialized with default configuration rules

Configured Messages:
-------------------
  0x500 @ 100ms - Switch states (brake/throttle/direction)
  0x610 @ 100ms - Motor 1 telemetry (RPM/current/temp)
  0x612 @ 100ms - Motor 2 telemetry (RPM/current/temp)
  0x620 @ 100ms - BMS pack (voltage/current/SOC)
  0x630 @ 100ms - Solar controller (voltage/current/power)
  0x600 @ 1000ms - Wiring harness heartbeat
  0x601 @ 1000ms - Motor controller 1 heartbeat
  0x602 @ 1000ms - Motor controller 2 heartbeat
  0x611 @ 1000ms - Motor 1 status/faults
  0x613 @ 1000ms - Motor 2 status/faults

Total: 10 rules (6 slots free for custom rules)

To reset to defaults:
  Hold button on GP22 during boot
========================================
```

The device immediately starts transmitting all configured CAN messages at their specified intervals.

### Runtime Behavior

Once initialized, the configuration rules are stored in flash and behave like normal action rules:

**View rules:**
```
get:rules
```

**Modify a rule:**
```
set:rule:1:enabled:0      # Disable rule 1 (switches)
set:rule:3:interval:200   # Change motor 2 to 200ms (5Hz)
```

**Add custom rules:**
```
add:rule:11:timer:500:can_tx:0x700:AA,BB,CC,DD  # Add new message
```

**Delete rules:**
```
delete:rule:5   # Remove solar controller message
```

**Save changes:**
```
save:rules
```

### Reset to Defaults

To restore the original configuration:
1. Connect a button between GP22 and GND
2. Hold button during power-on/reset
3. Device will detect button press and rewrite defaults
4. Release button after serial output confirms reset

## Creating New Configurations

### 1. Create Config Header

Create `src/configs/your_config_name_config.h`:

```cpp
#pragma once
#include <stdint.h>

#define DEFAULT_CONFIG_NAME "Your Config Name"
#define DEFAULT_CONFIG_RESET_PIN 22  // Or your preferred GPIO
#define DEFAULT_NUM_RULES 5

struct DefaultRuleConfig {
    uint32_t can_id;
    uint32_t interval_ms;
    uint8_t data[8];
    const char* description;
};

static const DefaultRuleConfig default_rules[DEFAULT_NUM_RULES] = {
    {0x100, 1000, {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08}, "Test message 1"},
    {0x200, 500,  {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00, 0x11}, "Test message 2"},
    // ... add your messages
};
```

### 2. Update Config Loader

Edit `src/capabilities/rp2040/rp2040_config_loader.cpp`:

```cpp
// Change the include to your new config
#ifdef HAS_DEFAULT_CONFIG
#include "../../configs/your_config_name_config.h"
#endif
```

### 3. Create Build Variant

Add to `platformio.ini`:

```ini
[env:pico_your_config]
extends = env:pico
build_flags =
    ${env:pico.build_flags}
    -D HAS_DEFAULT_CONFIG
build_src_filter =
    ${env:pico.build_src_filter}
    +<configs/>
```

### 4. Build and Test

```bash
pio run -e pico_your_config --target upload
pio device monitor
```

## Platform Support

### RP2040 (Raspberry Pi Pico)
✅ **Fully Supported**
- Config loader: `src/capabilities/rp2040/rp2040_config_loader.cpp`
- Flash storage: 4KB at 0x101FF000
- Max rules: 16
- Reset button: Any GPIO with internal pull-up

### SAMD51 (Feather M4 CAN)
🚧 **Ready for Implementation**
- Create: `src/capabilities/samd51/samd51_config_loader.cpp`
- Flash storage: Already exists (external SPI flash)
- Max rules: 64
- Same config header format works

### Adding New Platforms
1. Create `{platform}_config_loader.cpp` in platform folder
2. Implement `init_default_config()` and `print_config_status()`
3. Follow RP2040 implementation as template
4. Use platform-specific flash APIs

## Best Practices

### CRC Calculation
If your protocol requires CRC/checksums:

```cpp
inline uint8_t calc_crc8(const uint8_t* data, uint8_t len = 7) {
    uint8_t crc = 0x00;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            crc = (crc & 0x80) ? ((crc << 1) ^ 0x07) : (crc << 1);
        }
    }
    return crc;
}

// Pre-calculate and add to data array
{0x500, 100, {0x00, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, calc_crc8({0x00, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00})}, "Message"}
```

### Testing Configurations
1. Use realistic data patterns from actual devices
2. Include heartbeat messages for liveness detection
3. Vary message rates to simulate real bus loading
4. Test with receiving devices to validate format
5. Use CAN analyzers to verify timing and data

### Rule Limits
- RP2040: Max 16 rules (RAM limited)
- SAMD51: Max 64 rules (more RAM)
- Leave some rule slots free for runtime additions
- Periodic rules use `ACTION_CAN_SEND_PERIODIC` internally

## Troubleshooting

**Rules not loading on boot:**
- Check serial output for initialization messages
- Verify flash magic number: `0x55434154` ("UCAN")
- Try erasing flash: Hold reset button during boot
- Check `HAS_DEFAULT_CONFIG` build flag is set

**Config loader not compiling:**
- Ensure both `PLATFORM_RP2040` and `HAS_DEFAULT_CONFIG` defined
- Check `build_src_filter` includes `+<configs/>`
- Verify config header path in loader

**CAN messages not transmitting:**
- Rules must be enabled: `rule.enabled = true`
- Check CAN interface initialized successfully
- Verify `update_periodic()` called in main loop
- Use `get:rules` to check loaded rules

**Reset button not working:**
- Check GPIO pin number matches config header
- Verify button wired: GPIO → Button → GND
- Internal pull-up enabled automatically
- Debounce delay is 10ms
- Must be pressed during boot/power-on

## See Also

- [RP2040_FLASH_STORAGE.md](RP2040_FLASH_STORAGE.md) - Flash implementation details
- [RP2040_HARDWARE.md](RP2040_HARDWARE.md) - Pin connections and wiring
- [PROTOCOL.md](../can_tui/PROTOCOL.md) - uCAN serial protocol
- Golf cart protocol: https://github.com/ril3y/drive-control-hub/blob/dev/PROTOCOL.md

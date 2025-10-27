# PROTOCOL.md Corrections Needed

## Critical Protocol Mismatch Fixed

The PROTOCOL.md documentation did NOT match the actual firmware implementation in `action_manager_base.cpp`.

### What Was Wrong

**PROTOCOL.md Documented (INCORRECT):**
```
action:add:{RULE_ID}:{CAN_ID}:{MASK}:{EXTENDED}:{PRIORITY}:{INDEX}:{ACTION_NAME}:{PARAM_SOURCE}:{PARAMS...}
```

**Firmware Actually Implements (CORRECT):**
```
action:add:{RULE_ID}:{CAN_ID}:{MASK}:{DATA}:{DATA_MASK}:{DATA_LEN}:{ACTION_NAME}:{PARAM_SOURCE}:{PARAMS...}
```

### Field Differences

| Position | PROTOCOL.md Said | Firmware Actually Uses |
|----------|------------------|------------------------|
| 4 | EXTENDED (extended CAN ID flag) | DATA (data pattern to match) |
| 5 | PRIORITY (rule priority) | DATA_MASK (data byte masks) |
| 6 | INDEX (rule index) | DATA_LEN (number of bytes to match) |

### What Was Fixed

1. **`print_rules()` function** (X:/Projects/embedded/uCAN/src/actions/action_manager_base.cpp:361-479)
   - Changed output format from `ACTION;...` to `RULE;...`
   - Output now matches input format that `parse_and_add_rule()` expects
   - Format: `RULE;{ID};{CAN_ID};{MASK};{DATA};{DATA_MASK};{DATA_LEN};{ACTION};{PARAM_SOURCE};{PARAMS...}`
   - This allows copy/paste of `action:list` output back as `action:add` input

2. **PROTOCOL.md Updates Needed** (X:/Projects/embedded/uCAN/docs/PROTOCOL.md)
   - Line ~764: Change action:add format definition
   - Line ~770-781: Update field descriptions table
   - Line ~797-828: Update examples to match actual format
   - Line ~848: Update action:edit format (same as action:add)
   - Line ~895-899: Update action:list response format from `RULE;...` to match

### Correct Format Examples

**Simple GPIO Rule (fixed parameter):**
```
action:add:0:0x100:0x7FF:::0:GPIO_SET:fixed:13
           │ │      │    │││ │ │        │     │
           │ │      │    │││ │ │        │     └─ Pin 13
           │ │      │    │││ │ │        └─────── Fixed params
           │ │      │    │││ │ └──────────────── GPIO_SET action
           │ │      │    │││ └────────────────── DATA_LEN = 0 (ignore data)
           │ │      │    ││└──────────────────── DATA_MASK (empty)
           │ │      │    │└───────────────────── DATA (empty)
           │ │      │    └────────────────────── CAN ID mask 0x7FF (exact match)
           │ │      └─────────────────────────── CAN ID 0x100
           │ └────────────────────────────────── RULE_ID (0 = auto-assign)
           └──────────────────────────────────── command
```

**NeoPixel with CAN Data Extraction:**
```
action:add:0:0x500:0x7FF:::0:NEOPIXEL:candata
```
- When CAN ID 0x500 received, extract R,G,B,brightness from bytes 0-3 of CAN message
- Extraction mapping defined in ACTIONDEF for NEOPIXEL

**NeoPixel with Fixed Color:**
```
action:add:0:0x600:0x7FF:::0:NEOPIXEL:fixed:255:128:0:200
                                                R   G  B bright
```

**action:list Response:**
```
RULE;1;0x500;0x7FF;;;0;NEOPIXEL;candata
RULE;2;0x100;0x7FF;;;0;GPIO_SET;fixed;13
RULE;3;0x600;0x7FF;;;0;NEOPIXEL;fixed;255;128;0;200
```

### Why DATA/DATA_MASK/DATA_LEN Exist

These fields allow matching specific data patterns in CAN messages:

**Example: Only trigger when byte 0 = 0xFF**
```
action:add:0:0x200:0x7FF:FF:FF:1:GPIO_TOGGLE:fixed:13
                         ^^  ^^ ^
                         │   │  └─ Match 1 byte
                         │   └──── Must match exactly (0xFF mask)
                         └──────── Byte 0 must be 0xFF
```

This rule only fires when CAN ID 0x200 is received AND the first data byte is 0xFF.

**Use Cases for Data Matching:**
- Differentiate between messages with same CAN ID but different meanings
- Filter out noise/invalid messages
- Trigger on specific sensor values (e.g., only if temperature > threshold)
- Implement state machines (different actions for different data values)

### Implementation Details

From `action_manager_base.cpp`:

```cpp
// Parse format: ID:CAN_ID:CAN_MASK:DATA:DATA_MASK:DATA_LEN:ACTION_TYPE:PARAM_SOURCE:PARAM1:PARAM2:...
uint8_t ActionManagerBase::parse_and_add_rule(const char* command_str)
{
    // Lines 151-294: Parser expects this exact format
    // Line 177: Requires at least 7 tokens (ID through ACTION_TYPE)
    // Line 211: Requires token 7 to be PARAM_SOURCE ("fixed" or "candata")
    // Lines 228-290: Parse action-specific parameters
}
```

From `action_manager_base.h`:

```cpp
struct ActionRule {
    uint8_t id;                // Rule ID
    bool enabled;              // Rule active
    uint32_t can_id;           // CAN ID to match
    uint32_t can_id_mask;      // CAN ID mask
    uint8_t data[8];           // Data pattern to match  ← THESE EXIST
    uint8_t data_mask[8];      // Data mask              ← IN FIRMWARE
    uint8_t data_length;       // Number of bytes        ← NOT IN DOCS
    ActionType action;         // Action to execute
    ActionParams params;       // Action parameters
    ParamSource param_source;  // PARAM_FROM_RULE or PARAM_FROM_CAN_DATA
    uint8_t param_data_offset; // Offset for CAN data extraction
    ...
};
```

### Testing Checklist

After updating PROTOCOL.md:

1. Build firmware for Feather M4 CAN: `pio run -e feather_m4_can`
2. Flash to board: `pio run -e feather_m4_can --target upload`
3. Connect serial monitor: `pio device monitor -b 115200`
4. Test commands:
   ```
   action:add:0:0x100:0x7FF:::0:GPIO_SET:fixed:13
   action:list
   send:0x100:
   action:remove:1
   action:list
   ```
5. Verify `action:list` output can be copy/pasted as `action:add` input
6. Test candata extraction with NeoPixel

### Files Modified

- ✅ `src/actions/action_manager_base.cpp` - Fixed `print_rules()` format
- ⏳ `docs/PROTOCOL.md` - Needs update (lines ~762-899)
- ⏳ `can_tui/PROTOCOL.md` - May also need update (if separate copy exists)

### Author

Fixes by ril3y - January 2025

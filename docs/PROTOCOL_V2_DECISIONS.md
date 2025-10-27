# Protocol v2.0 Implementation Decisions

**Date:** 2025-01-26
**Author:** ril3y
**Status:** FINAL - Implemented in Firmware

---

## Executive Summary

This document records the **definitive decisions** for uCAN Protocol v2.0 implementation. These are NOT recommendations - they are the implemented reality.

---

## Decision 1: JSON is THE Format ✅

**From DESIGN_ACTION_PARAMETER_MAPPING.md:**
- ~~Option A: Compact JSON (RECOMMENDED)~~ ❌ OLD
- ~~Option B: Enumerated Protocol (Ultra-Compact)~~ ❌ REJECTED

**FINAL DECISION:**
- **JSON IS THE ONLY FORMAT** for action definitions
- Firmware outputs JSON (IMPLEMENTED)
- UI builders MUST parse JSON
- No alternative formats supported

**JSON Schema (Canonical):**
```json
{
  "i": <number>,              // Action ID (unique identifier)
  "n": "<string>",            // Action name (e.g., "NEOPIXEL")
  "d": "<string>",            // Description
  "c": "<string>",            // Category (e.g., "Display", "GPIO")
  "trig": "<string>",         // Trigger type (REQUIRED v2.0)
  "p": [                      // Parameters array
    {
      "n": "<string>",        // Parameter name
      "t": <number>,          // Type code (0=uint8, 1=uint16, etc.)
      "b": <number>,          // CAN data byte index (0-7)
      "o": <number>,          // Bit offset within byte (0-7)
      "l": <number>,          // Bit length (1-8)
      "r": "<min>-<max>",     // Range string
      "role": "<string>"      // Parameter role (REQUIRED v2.0)
    }
  ]
}
```

**Firmware Evidence:**
- `src/actions/param_mapping.cpp:84-86` - outputs "trig"
- `src/actions/param_mapping.cpp:133-135` - outputs "role"

---

## Decision 2: NO Backward Compatibility with v1.x ✅

**BREAKING CHANGE:**
- v1.x commands without PARAM_SOURCE **will be REJECTED**
- No implicit defaults
- No guessing
- Fail fast with clear error

**Firmware Evidence:**
```cpp
// src/actions/action_manager_base.cpp:195-211
// v2.0: PARAM_SOURCE is REQUIRED (no backward compatibility)
if (token_count < 8) {
    // Missing PARAM_SOURCE field - error
    return 0;
}

if (strcmp(tokens[7], "candata") == 0 || strcmp(tokens[7], "can") == 0) {
    rule.param_source = PARAM_FROM_CAN_DATA;
} else if (strcmp(tokens[7], "fixed") == 0 || strcmp(tokens[7], "rule") == 0) {
    rule.param_source = PARAM_FROM_RULE;
} else {
    // Invalid PARAM_SOURCE value - error
    return 0;
}
```

**Migration Path:**
- Old: `action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:13` ❌ REJECTED
- New: `action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:13` ✅ REQUIRED

---

## Decision 3: Trigger Types & Parameter Roles are REQUIRED ✅

**New in v2.0:**

**Trigger Types (`trig` field):**
| Value | Meaning | CAN ID Usage | UI Label |
|-------|---------|--------------|----------|
| `"can_msg"` | Triggered by incoming CAN | CAN ID to **match** | "CAN ID to Match" |
| `"periodic"` | Triggered by timer | Ignored (use 0x000) | "Timer Interval (ms)" |
| `"gpio"` | Triggered by pin change | Ignored (use 0x000) | "GPIO Pin to Monitor" |
| `"manual"` | Manual execution only | Ignored (use 0x000) | (no CAN ID field) |

**Parameter Roles (`role` field):**
| Value | Meaning | Example |
|-------|---------|---------|
| `"action_param"` | Input to the action | R, G, B for NeoPixel |
| `"trigger_param"` | Trigger configuration | interval_ms for periodic |
| `"output_param"` | Output destination | CAN ID to send to |

**Why This Matters:**
- **For can_msg**: UI shows "CAN ID to Match" (which message triggers this?)
- **For periodic**: UI shows "Interval (ms)" and hides CAN ID match field
- **For gpio**: UI shows "Pin to Monitor" instead of CAN ID

**UI Implementation:**
```javascript
if (actionDef.trig === "can_msg") {
    showField("CAN ID to Match", "Which CAN message triggers this?");
} else if (actionDef.trig === "periodic") {
    // Don't show "CAN ID to Match" - it's not relevant!
    const intervalParam = actionDef.p.find(p => p.role === "trigger_param");
    showField(intervalParam.n, "How often to trigger?");
}
```

---

## Decision 4: PROTOCOL.md is the Single Source of Truth ✅

**Documentation Hierarchy:**
1. **PROTOCOL.md** = THE specification (v2.0 ONLY, no v1.x)
   - Complete command reference
   - Complete JSON schema
   - UI builder workflow guide
   - Canonical examples

2. **PROTOCOL_V2_SUMMARY.md** = Quick reference
   - Migration guide for v1.x users
   - Summary of v2.0 changes
   - Points to PROTOCOL.md for details

3. **DESIGN_ACTION_PARAMETER_MAPPING.md** = Historical context
   - Design rationale (for developers)
   - Implementation notes
   - NOT for UI builders

**Action Items:**
- [x] Firmware enforces v2.0 strictly
- [ ] Update PROTOCOL.md to remove all v1.x compatibility language
- [ ] Update DESIGN_ACTION_PARAMETER_MAPPING.md status to "IMPLEMENTED"
- [ ] Ensure PROTOCOL_V2_SUMMARY.md points to PROTOCOL.md as canonical

---

## Decision 5: PARAM_SOURCE Values are Strict ✅

**Accepted values:**
- `"fixed"` or `"rule"` = Use fixed parameters from command
- `"candata"` or `"can"` = Extract parameters from CAN data bytes

**Validation:**
- Firmware rejects any other value
- Case-sensitive
- No default if missing

**Examples:**
```bash
# Fixed parameters - all parameters specified in command
action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:fixed:255:128:0:200

# CAN data parameters - extracted from received message data bytes
action:add:0:0x500:0xFFFFFFFF:::4:NEOPIXEL:candata
```

---

## For UI Builders: Implementation Checklist

### Phase 1: Startup (REQUIRED)
```javascript
// 1. Query all action definitions
send("get:actiondefs\n");

// 2. Parse ACTIONDEF responses
const actionDefs = [];
while (line = readline()) {
    if (line.startsWith("ACTIONDEF;")) {
        const json = line.split(";")[1];
        actionDefs.push(JSON.parse(json));
    }
}

// 3. Validate v2.0 fields exist
for (const def of actionDefs) {
    assert(def.trig !== undefined, "Missing 'trig' field - not v2.0 compliant");
    for (const param of def.p) {
        assert(param.role !== undefined, "Missing 'role' field - not v2.0 compliant");
    }
}
```

### Phase 2: Build Dynamic Forms
```javascript
function buildRuleForm(actionDef) {
    // Step 1: Check trigger type to determine UI layout
    if (actionDef.trig === "can_msg") {
        showField("CAN ID to Match", "hex");
    } else if (actionDef.trig === "periodic") {
        const intervalParam = actionDef.p.find(p => p.role === "trigger_param");
        showField(intervalParam.n, "number", intervalParam.r);
    }

    // Step 2: Show parameter source radio buttons
    showRadioGroup("Parameter Source", ["Fixed Values", "Extract from CAN Data"]);

    // Step 3: Build parameter fields
    for (const param of actionDef.p.filter(p => p.role === "action_param")) {
        if (paramSource === "fixed") {
            showInputField(param.n, param.t, param.r);
        } else {
            showReadOnlyInfo(`Byte ${param.b} → ${param.n} (${param.r})`);
        }
    }
}
```

### Phase 3: Generate Commands
```javascript
function generateCommand(ruleId, canId, actionName, paramSource, params) {
    let cmd = `action:add:${ruleId}:${canId}:0xFFFFFFFF:::0:${actionName}:${paramSource}`;

    if (paramSource === "fixed") {
        cmd += ":" + params.join(":");
    }
    // For "candata", no parameters after PARAM_SOURCE

    return cmd + "\n";
}

// Example usage:
const cmd1 = generateCommand(0, "0x500", "NEOPIXEL", "fixed", [255, 128, 0, 200]);
// → "action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:fixed:255:128:0:200\n"

const cmd2 = generateCommand(0, "0x500", "NEOPIXEL", "candata", []);
// → "action:add:0:0x500:0xFFFFFFFF:::0:NEOPIXEL:candata\n"
```

### Phase 4: Error Handling
```javascript
send(cmd);
const response = readline();

if (response.includes("STATUS;ERROR")) {
    if (response.includes("Invalid CAN ID")) {
        showError("CAN ID must be in hex format (e.g., 0x500)");
    } else if (response.includes("Invalid PARAM_SOURCE")) {
        showError("PARAM_SOURCE must be 'fixed' or 'candata'");
    } else if (response.includes("Missing PARAM_SOURCE")) {
        showError("PARAM_SOURCE is required in Protocol v2.0");
    }
} else if (response.includes("STATUS;INFO;Rule added")) {
    showSuccess("Rule added successfully");
}
```

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Treating JSON as "recommended"
**Wrong:** "I'll support both JSON and enumerated format"
**Right:** "JSON is the ONLY format supported"

### ❌ Mistake 2: Making PARAM_SOURCE optional
**Wrong:** `action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:13`
**Right:** `action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:13`

### ❌ Mistake 3: Ignoring trigger types
**Wrong:** Always show "CAN ID to Match" field
**Right:** Check `trig` field and show appropriate UI

### ❌ Mistake 4: Ignoring parameter roles
**Wrong:** Treat all parameters the same
**Right:** Group by role, handle trigger_param specially

### ❌ Mistake 5: Supporting v1.x commands
**Wrong:** "Let me add backward compatibility just in case"
**Right:** "v2.0 only - firmware will reject v1.x anyway"

---

## Version History

- **2025-01-26**: Created - FINAL decisions for v2.0 implementation
- **Status**: IMPLEMENTED in firmware, documentation updates pending

---

## Questions?

**"Can I support v1.x for compatibility?"**
NO. Firmware rejects v1.x commands. You'll just create confusion.

**"Can I use a different format instead of JSON?"**
NO. Firmware outputs JSON only.

**"Is PARAM_SOURCE really required?"**
YES. Firmware returns error if missing.

**"What if I don't check the 'trig' field?"**
Your UI will show wrong labels (e.g., "CAN ID to Match" for periodic actions that don't match CAN IDs).

**"What if I don't check the 'role' field?"**
You won't know which parameters control the trigger vs the action itself.

---

**Status: FINAL - These decisions are IMPLEMENTED and ENFORCED by firmware.**

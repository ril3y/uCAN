# uCAN Documentation Strategy for Protocol v2.0

**Date:** 2025-01-26
**Status:** COMPLETE

---

## Ultra-Thinking Analysis: Documentation & Firmware Alignment

### The Problem You Identified

1. **Documentation fragmentation** - Multiple docs (PROTOCOL.md, PROTOCOL_V2_SUMMARY.md, DESIGN_ACTION_PARAMETER_MAPPING.md) with unclear roles
2. **Ambiguous language** - "RECOMMENDED" vs "IMPLEMENTED", v1.x vs v2.0
3. **No legacy support wanted** - You explicitly said "i dont want to support the legacy rule format"
4. **JSON format unclear** - Design doc discussed options but didn't definitively pick one
5. **UI builder confusion** - Which doc to read? What's required vs optional?

---

## Firmware Reality Check ✅

**I verified the firmware code. Here's what's actually implemented:**

### 1. PARAM_SOURCE Enforcement (STRICT v2.0)
**File:** `src/actions/action_manager_base.cpp:195-211`

```cpp
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

**Verdict:** ✅ Firmware REJECTS v1.x commands without PARAM_SOURCE

### 2. JSON Output with v2.0 Fields
**File:** `src/actions/param_mapping.cpp`

- Line 84-86: Outputs `"trig"` (trigger type)
- Line 133-135: Outputs `"role"` (parameter role)

**Verdict:** ✅ Firmware outputs full v2.0 JSON with trigger types and parameter roles

---

## Solution Implemented

### Document Hierarchy (FINAL)

```
┌─────────────────────────────────────────────────────────────┐
│  can_tui/PROTOCOL.md                                        │
│  - THE canonical specification                              │
│  - v2.0 ONLY (no v1.x)                                     │
│  - Complete command reference                               │
│  - Complete JSON schema                                     │
│  - UI builder workflow guide                                │
│  ✅ UPDATED: Added v2.0 breaking changes notice            │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ points to
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PROTOCOL_V2_SUMMARY.md                                     │
│  - Quick reference & migration guide                        │
│  - Supplementary to PROTOCOL.md                             │
│  - For v1.x users migrating                                │
│  ✅ UPDATED: Points to PROTOCOL.md as canonical            │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ historical context
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  DESIGN_ACTION_PARAMETER_MAPPING.md                         │
│  - Design rationale (for firmware developers)               │
│  - NOT for UI builders                                      │
│  ✅ UPDATED: Status = "IMPLEMENTED"                        │
│  ✅ UPDATED: JSON is "THE format" not "recommended"        │
│  ✅ UPDATED: Removed "Option B" to eliminate confusion     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ decisions summary
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PROTOCOL_V2_DECISIONS.md (NEW)                             │
│  - Definitive decisions for v2.0                            │
│  - "This is what we're doing" (not "options")               │
│  - UI builder checklist                                     │
│  - Common mistakes to avoid                                 │
│  ✅ CREATED: Single page with all decisions                │
└─────────────────────────────────────────────────────────────┘
```

---

## For UI Builders: Start Here

**PROTOCOL.md is your bible.** Everything you need is there:
- Lines 9-21: v2.0 breaking changes warning
- Lines 188-212: `get:actiondefs` command (how to query capabilities)
- Lines 214-243: Action definition JSON schema (complete field reference)
- Lines 269-359: `action:add` command with PARAM_SOURCE (required format)
- Lines 360-644: UI Builder Guide (complete workflow with code examples)
- Lines 430-443: Trigger types table (can_msg vs periodic vs gpio vs manual)
- Lines 438-444: Parameter roles table (action_param vs trigger_param vs output_param)

---

## Definitive Decisions (NO AMBIGUITY)

### 1. JSON is THE Format ✅
**NOT "recommended" - it's THE ONLY FORMAT supported.**

Firmware outputs JSON. UI builders parse JSON. No alternatives.

### 2. PARAM_SOURCE is REQUIRED ✅
**NO backward compatibility with v1.x.**

Old: `action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:13` → ❌ REJECTED by firmware
New: `action:add:0:0x100:0xFFFFFFFF:::0:GPIO_TOGGLE:fixed:13` → ✅ REQUIRED

### 3. Trigger Types (`trig`) and Parameter Roles (`role`) are REQUIRED ✅
**Every action definition includes these fields.**

UI builders MUST check `trig` to know how to display the form:
- `"can_msg"` → Show "CAN ID to Match"
- `"periodic"` → Show "Interval (ms)", hide CAN ID match
- `"gpio"` → Show "Pin to Monitor"
- `"manual"` → No trigger fields

### 4. NO Legacy Support ✅
**Firmware rejects v1.x commands. Period.**

UI builders should NOT implement v1.x fallback. Firmware will just reject it anyway.

---

## Changes Made to Documentation

### 1. can_tui/PROTOCOL.md
**Added (lines 9-21):**
```markdown
## ⚠️ IMPORTANT: Protocol v2.0 Breaking Changes

**This specification describes Protocol v2.0, which is NOT backward compatible with v1.x.**

**Key Changes from v1.x:**
1. **PARAM_SOURCE is REQUIRED** in `action:add` commands - firmware rejects commands without it
2. **Trigger types (`trig`) and parameter roles (`role`) are REQUIRED** in action definitions
3. **JSON is THE format** for action definitions (not optional)
4. **No implicit defaults** - firmware validates strictly

**For UI builders:** If you're implementing a new client, start here. This is the canonical specification.
```

### 2. PROTOCOL_V2_SUMMARY.md
**Added (lines 10-14):**
```markdown
## 📘 For UI Builders

**Building a new client?** Read [can_tui/PROTOCOL.md](can_tui/PROTOCOL.md) - that's the complete, canonical specification.

**This document** is a quick reference and migration guide for v1.x users. For complete details, see PROTOCOL.md.
```

### 3. DESIGN_ACTION_PARAMETER_MAPPING.md
**Changed:**
- Line 6: Status = ~~"Design Proposal"~~ → **"✅ IMPLEMENTED (Firmware & Protocol v2.0)"**
- Line 427: ~~"Option A: Compact JSON (RECOMMENDED)"~~ → **"Compact JSON Format (IMPLEMENTED ✅)"**
- Line 429: Added **"Decision: JSON is THE format used in Protocol v2.0. No alternative formats are supported."**
- Lines 476-504: Removed entire "Option B" section, added note about rejected alternative

### 4. PROTOCOL_V2_DECISIONS.md (NEW)
**Created comprehensive decision document with:**
- Definitive statements (not options)
- UI builder implementation checklist
- Common mistakes to avoid
- "Questions?" section addressing typical concerns

---

## Verification: Firmware vs Documentation Alignment

| Feature | Documentation | Firmware Implementation | Status |
|---------|---------------|-------------------------|--------|
| PARAM_SOURCE required | PROTOCOL.md line 288 | action_manager_base.cpp:199-211 | ✅ ALIGNED |
| JSON is THE format | PROTOCOL.md line 16 | param_mapping.cpp (entire file) | ✅ ALIGNED |
| "trig" field output | PROTOCOL.md line 415 | param_mapping.cpp:84-86 | ✅ ALIGNED |
| "role" field output | PROTOCOL.md line 424 | param_mapping.cpp:133-135 | ✅ ALIGNED |
| No v1.x support | PROTOCOL.md line 14 | action_manager_base.cpp:195 | ✅ ALIGNED |

**Verdict:** Documentation and firmware are 100% aligned on v2.0 requirements.

---

## UI Builder Quick Start

### Step 1: Read PROTOCOL.md
Start at line 1. Read to line 644 (UI Builder Guide section).

### Step 2: Query Capabilities on Startup
```javascript
send("get:actiondefs\n");
// Parse ACTIONDEF;{...} responses
```

### Step 3: Validate v2.0 Compliance
```javascript
for (const def of actionDefs) {
    assert(def.trig !== undefined, "Missing 'trig' - not v2.0!");
    assert(def.p.every(p => p.role !== undefined), "Missing 'role' - not v2.0!");
}
```

### Step 4: Build Forms Based on Trigger Type
```javascript
if (def.trig === "can_msg") {
    showField("CAN ID to Match");
} else if (def.trig === "periodic") {
    showField("Interval (ms)");
}
```

### Step 5: Generate Commands with PARAM_SOURCE
```javascript
// ALWAYS include PARAM_SOURCE (no default!)
const cmd = `action:add:${id}:${canId}:0xFFFFFFFF:::0:${action}:${paramSource}`;
if (paramSource === "fixed") {
    cmd += ":" + params.join(":");
}
```

---

## Common Mistakes Prevented

### ❌ Mistake 1: "I'll support both v1.x and v2.0 for compatibility"
**Why it's wrong:** Firmware REJECTS v1.x. You're wasting effort on dead code.

### ❌ Mistake 2: "I'll make PARAM_SOURCE optional with a default"
**Why it's wrong:** Firmware requires it. Your command will fail.

### ❌ Mistake 3: "I'll treat JSON as 'recommended' and try to parse other formats"
**Why it's wrong:** Firmware ONLY outputs JSON. There are no other formats.

### ❌ Mistake 4: "I don't need to check the 'trig' field"
**Why it's wrong:** You'll show "CAN ID to Match" for periodic actions that don't match CAN IDs.

### ❌ Mistake 5: "I'll read PROTOCOL_V2_SUMMARY.md and skip PROTOCOL.md"
**Why it's wrong:** PROTOCOL_V2_SUMMARY.md is a quick reference, not complete. PROTOCOL.md has all the details.

---

## Summary

**Problem:** Fragmented docs, ambiguous language, unclear what's required vs recommended

**Solution:**
1. **PROTOCOL.md** = Single source of truth for UI builders
2. **PROTOCOL_V2_SUMMARY.md** = Quick reference pointing to PROTOCOL.md
3. **DESIGN_ACTION_PARAMETER_MAPPING.md** = Design context for developers
4. **PROTOCOL_V2_DECISIONS.md** = Definitive decision summary

**Firmware Status:** ✅ Fully v2.0 compliant, strict validation, NO v1.x support

**Documentation Status:** ✅ Updated, aligned, no ambiguity

**Ready for:** UI builders to implement v2.0 clients with confidence

---

## Next Steps

**For you:**
1. Review PROTOCOL_V2_DECISIONS.md - make sure decisions match your vision
2. Share can_tui/PROTOCOL.md with UI builder as THE spec

**For UI builder:**
1. Read can_tui/PROTOCOL.md (complete spec)
2. Reference PROTOCOL_V2_SUMMARY.md for quick lookups
3. Reference PROTOCOL_V2_DECISIONS.md for implementation checklist

**No more ambiguity. No more "recommended vs implemented". It's all definitive now.**

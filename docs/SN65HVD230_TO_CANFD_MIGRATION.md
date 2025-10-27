# SN65HVD230DR to CAN FD Migration Guide

**Date:** 2025-01-26
**Your Situation:** Custom board with SN65HVD230DR, want CAN FD for larger data sizes (64 bytes)
**Question:** Is there a drop-in pin-compatible CAN FD replacement?

---

## TL;DR - Quick Answer

**❌ NO** - There is NO perfect pin-compatible drop-in replacement for SN65HVD230DR that supports CAN FD.

**Why:** CAN FD transceivers have different pinouts due to:
1. Additional features (fault detection, wake-up, etc.)
2. Different power requirements (5V vs 3.3V)
3. Signal improvement capabilities for higher data rates

**Your Options:**
1. **PCB redesign** with CAN FD transceiver (TCAN334, TCAN3403-Q1)
2. **Adapter board** (not ideal but possible)
3. **External CAN FD module** (easiest but bulky)

---

## SN65HVD230DR Pinout (SOIC-8)

**Current chip on your board:**

| Pin | Function | Description |
|-----|----------|-------------|
| 1 | TXD | Transmit Data Input (from MCU) |
| 2 | GND | Ground |
| 3 | VCC | 3.3V Supply |
| 4 | RXD | Receive Data Output (to MCU) |
| 5 | VREF | Reference Voltage Output (VCC/2) |
| 6 | CANL | CAN Low |
| 7 | CANH | CAN High |
| 8 | RS | Slope Control / Standby Mode Select |

**Key Characteristics:**
- **Supply:** 3.3V only
- **Max Speed:** 1 Mbps (classical CAN)
- **CAN FD:** ❌ NO
- **Package:** SOIC-8 (D package)

---

## CAN FD Transceiver Options (3.3V Logic)

### Option 1: TCAN334 / TCAN337 (TI 3.3V CAN FD)

**Pinout (SOIC-8):**

| Pin | TCAN334 | TCAN337 | SN65HVD230 | Match? |
|-----|---------|---------|------------|--------|
| 1 | TXD | TXD | TXD | ✅ |
| 2 | GND | GND | GND | ✅ |
| 3 | VCC | VCC | VCC | ✅ |
| 4 | RXD | RXD | RXD | ✅ |
| 5 | WAKE | FAULT | VREF | ❌ |
| 6 | CANL | CANL | CANL | ✅ |
| 7 | CANH | CANH | CANH | ✅ |
| 8 | STB | STB | RS | ⚠️ Similar |

**Compatibility Analysis:**

**✅ Compatible Pins (6/8):**
- Pins 1-4: Perfect match (TXD, GND, VCC, RXD)
- Pins 6-7: Perfect match (CANL, CANH)

**❌ Incompatible Pins (2/8):**
- **Pin 5:** WAKE/FAULT vs VREF
  - SN65HVD230: Outputs VCC/2 reference voltage
  - TCAN334/337: Input for wake/fault detection
  - **Impact:** If your design uses VREF, this breaks

- **Pin 8:** STB vs RS
  - SN65HVD230: RS (slope control resistor connection)
  - TCAN334/337: STB (active-low standby input)
  - **Impact:** Logic levels are inverted, functionality differs

**Specs:**
- **Supply:** 3.3V
- **Max Speed:** 5-8 Mbps (CAN FD)
- **Data Payload:** Up to 64 bytes ✅
- **Classical CAN:** ✅ Backward compatible

**Part Numbers:**
- **TCAN334D** - SOIC-8, basic variant
- **TCAN334GD** - SOIC-8, 5 Mbps variant
- **TCAN337D** - SOIC-8, with fault detection

### Option 2: TCAN3403-Q1 / TCAN3404-Q1 (Newer TI CAN FD)

**TI's Marketing:** "Footprint compatibility with standard 5V CAN transceivers"

**Reality:** This means SOIC-8 package, NOT exact pin-for-pin compatibility.

**Pinout (SOIC-8):**

| Pin | TCAN3403-Q1 | TCAN3404-Q1 | SN65HVD230 | Match? |
|-----|-------------|-------------|------------|--------|
| 1 | TXD | TXD | TXD | ✅ |
| 2 | GND | GND | GND | ✅ |
| 3 | VIO/VCC | VCC | VCC | ⚠️ |
| 4 | RXD | RXD | RXD | ✅ |
| 5 | nFAULT | nFAULT | VREF | ❌ |
| 6 | CANL | CANL | CANL | ✅ |
| 7 | CANH | CANH | CANH | ✅ |
| 8 | nSTB | nSTB | RS | ❌ |

**Compatibility Analysis:**

**✅ Compatible Pins (5/8):**
- Pins 1, 2, 4, 6, 7: Direct matches

**⚠️ Partially Compatible:**
- **Pin 3:** VIO vs VCC
  - TCAN3403: VIO (1.8-3.3V I/O level shifter)
  - TCAN3404: VCC (3.3V supply, logic also 3.3V)
  - SN65HVD230: VCC (3.3V supply)
  - **Use TCAN3404-Q1** if replacing SN65HVD230

**❌ Incompatible Pins:**
- **Pin 5:** nFAULT (output) vs VREF (output)
- **Pin 8:** nSTB (active-low input) vs RS (analog input)

**Specs:**
- **Supply:** 3.3V (TCAN3404) or 1.8-3.3V logic (TCAN3403)
- **Max Speed:** 5 Mbps CAN FD
- **Data Payload:** Up to 64 bytes ✅
- **Automotive:** AEC-Q100 qualified
- **Shutdown Current:** <5µA

**Part Numbers:**
- **TCAN3403-Q1** - With VIO for 1.8V/2.5V/3.3V logic
- **TCAN3404-Q1** - Fixed 3.3V logic (closest to SN65HVD230)

### Option 3: TCAN1051 (5V Supply with 3.3V Logic Option)

**NOT RECOMMENDED for drop-in replacement**

**Pinout (SOIC-8):**

| Pin | TCAN1051HV | SN65HVD230 | Match? |
|-----|------------|------------|--------|
| 1 | TXD | TXD | ✅ |
| 2 | GND | GND | ✅ |
| 3 | VCC (5V) | VCC (3.3V) | ❌ |
| 4 | RXD | RXD | ✅ |
| 5 | VIO (on -V variants) | VREF | ❌ |
| 6 | CANL | CANL | ✅ |
| 7 | CANH | CANH | ✅ |
| 8 | S (silent mode) | RS | ❌ |

**Why NOT Recommended:**
- Requires **5V supply** (your board supplies 3.3V)
- Pin 5 is VIO input (not VREF output)
- Would require board redesign anyway

---

## Pin 5 Problem: VREF vs WAKE/FAULT

**This is the critical incompatibility.**

### SN65HVD230 Pin 5 (VREF)

**Function:** Outputs a stable VCC/2 voltage (1.65V @ 3.3V supply)

**Common Uses:**
1. **MCU ADC reference** - Some designs use VREF for analog measurements
2. **Split termination** - 60Ω to CANH + 60Ω to CANL + 4.7nF from VREF to GND
3. **Unused** - Left floating (many designs don't use it)

**If your board uses VREF:**
- CAN FD transceivers don't have this output
- You'll need an external voltage divider or reference IC
- **Check your schematic** to see if VREF is connected

### TCAN334/337 Pin 5 (WAKE/FAULT)

**Function:** Input or output for status/control

**TCAN334:** WAKE input (detects bus activity to wake from sleep)
**TCAN337:** FAULT output (indicates bus fault condition)

**Workaround if VREF needed:**
```
Add external voltage divider:
VCC (3.3V) ---[10kΩ]--- VREF_NEW (1.65V) ---[10kΩ]--- GND
                            │
                          [100nF to GND]
```

---

## Pin 8 Problem: RS vs STB

### SN65HVD230 Pin 8 (RS)

**Function:** Slope control resistor + mode select

**Modes:**
- **Connect to GND:** High-speed mode (fastest edges)
- **Connect via resistor to GND:** Slope control (EMI reduction)
- **Float or connect to VCC:** Low-power standby mode

**Typical Circuit:**
```
RS pin --- [10kΩ-100kΩ] --- GND  (slope control)
OR
RS pin --- GND  (high-speed mode)
```

### TCAN334/337 Pin 8 (STB - Standby)

**Function:** Active-low standby input

**Modes:**
- **STB = LOW (0V):** Standby mode (low power)
- **STB = HIGH (3.3V):** Normal operation

**Typical Circuit:**
```
STB pin --- pull-up to VCC  (normal operation)
OR
STB pin --- MCU GPIO  (software control)
```

**Workaround:**
If your SN65HVD230 design has RS connected to GND (high-speed mode):
- **Connect TCAN STB to VCC** (normal operation)
- Board will work but no low-power mode

If your design uses RS for slope control:
- **You lose slope control** with TCAN transceivers
- May need external series resistors on CANH/CANL (not ideal)

---

## Migration Strategies

### Strategy 1: PCB Redesign (RECOMMENDED)

**Best Option for Production:**

**Use:** TCAN3404-Q1 or TCAN334G

**Changes Required:**
1. **Pin 5:** Remove VREF connections
   - If VREF was used: Add external voltage divider
   - If unused: Connect nFAULT to MCU GPIO or leave floating
2. **Pin 8:** Change from RS resistor to STB pull-up
   - Remove slope control resistor
   - Add 10kΩ pull-up to VCC or connect to MCU GPIO
3. **Verify VCC is 3.3V** (should already be for SN65HVD230)

**Schematic Changes:**
```
OLD (SN65HVD230):
Pin 5 (VREF) --- [No connection or to ADC]
Pin 8 (RS) --- [10kΩ] --- GND

NEW (TCAN3404-Q1):
Pin 5 (nFAULT) --- [10kΩ pull-up] --- VCC  (or to MCU GPIO)
Pin 8 (nSTB) --- VCC  (or [10kΩ pull-up] to VCC)
```

**PCB Changes:**
- Same footprint (SOIC-8)
- Change two trace routings (pins 5 and 8)
- **No board redesign needed**, just different connections

**Benefits:**
- ✅ Up to 64 bytes per CAN message
- ✅ Up to 5 Mbps (TCAN3404-Q1) or 8 Mbps (TCAN334G)
- ✅ Backward compatible with classical CAN
- ✅ Automotive qualified (TCAN3404-Q1)

### Strategy 2: Adapter Board (HACK)

**For prototyping only, not recommended for production**

**Concept:** Create a small adapter PCB that:
1. Has SN65HVD230 footprint on bottom (connects to your board)
2. Has TCAN334/3404 footprint on top
3. Handles pin 5 and pin 8 differences

**Adapter Board Design:**

```
Bottom (to your board):        Top (CAN FD chip):
Pin 1 (TXD) ──────────────── Pin 1 (TXD)
Pin 2 (GND) ──────────────── Pin 2 (GND)
Pin 3 (VCC) ──────────────── Pin 3 (VCC)
Pin 4 (RXD) ──────────────── Pin 4 (RXD)
Pin 5 (VREF) ─ [not connected]
                 ┌─ VCC
                 │
            [10kΩ] (pull-up)
                 │
Pin 5 (nFAULT) ──┘
Pin 6 (CANL) ──────────────── Pin 6 (CANL)
Pin 7 (CANH) ──────────────── Pin 7 (CANH)
Pin 8 (RS) ──── [not connected]
                 ┌─ VCC
                 │
            [10kΩ] (pull-up)
                 │
Pin 8 (nSTB) ────┘
```

**Challenges:**
- Requires custom PCB design
- Adds height (stacking two chips)
- Potential signal integrity issues
- Not cost-effective for production

### Strategy 3: External CAN FD Module (EASIEST)

**Use a pre-made CAN FD breakout board**

**Recommended Modules:**
1. **Longan CAN FD Breakout** - TCAN334 or MCP2562FD based
2. **Waveshare CAN FD Board** - Various chips available
3. **Adafruit CAN FD Breakout** (if they make one)

**Connection:**
```
Your Board                  External Module
(SN65HVD230 removed)

MCU TXD ───────────────────> TXD
MCU RXD <───────────────────  RXD
3.3V ───────────────────────> VCC
GND ────────────────────────> GND

CANH ◄──────────────────────┘ (from module to bus)
CANL ◄──────────────────────┘
```

**Benefits:**
- ✅ No PCB changes needed
- ✅ Quick prototyping
- ✅ Easy to test CAN FD

**Drawbacks:**
- ❌ Bulky (two boards)
- ❌ Extra wiring
- ❌ Not production-suitable

---

## Detailed Comparison Table

| Aspect | SN65HVD230DR | TCAN334G | TCAN3404-Q1 | TCAN1051HV |
|--------|--------------|----------|-------------|------------|
| **CAN FD Support** | ❌ | ✅ | ✅ | ✅ |
| **Max Speed** | 1 Mbps | 8 Mbps | 5 Mbps | 2-5 Mbps |
| **Supply Voltage** | 3.3V | 3.3V | 3.3V | 5V |
| **Logic Levels** | 3.3V | 3.3V | 3.3V | 5V (or VIO) |
| **Package** | SOIC-8 | SOIC-8 | SOIC-8 | SOIC-8 |
| **Pin 1-4 Match** | - | ✅ | ✅ | ✅ |
| **Pin 5 (VREF)** | Output | ❌ WAKE Input | ❌ nFAULT | ❌ VIO Input |
| **Pin 6-7 Match** | - | ✅ | ✅ | ✅ |
| **Pin 8 (RS)** | Analog | ❌ STB Digital | ❌ nSTB Digital | ❌ S Digital |
| **Drop-in Compatible** | - | ❌ | ❌ | ❌ |
| **Minor Changes** | - | ⚠️ Pins 5,8 | ⚠️ Pins 5,8 | ❌ Many |
| **Cost (approx)** | $0.50 | $1.50 | $2.00 | $1.80 |
| **Availability** | High | Medium | High | High |
| **Auto Qualified** | No | No | ✅ AEC-Q100 | ✅ AEC-Q100 |

---

## Recommendation

### For Your Custom Board

**Best Choice:** **TCAN3404-Q1** (Automotive CAN FD, 3.3V, 5 Mbps)

**Why:**
1. ✅ Same package (SOIC-8)
2. ✅ Same supply voltage (3.3V)
3. ✅ 6 out of 8 pins compatible
4. ✅ Up to 64-byte payloads (your requirement)
5. ✅ 5 Mbps is plenty for larger data sizes
6. ✅ Automotive qualified (AEC-Q100)
7. ✅ Low-power standby (<5µA)

**Required Changes:**
```
Pin 5: Remove VREF connection, add pull-up for nFAULT
Pin 8: Remove RS resistor, add pull-up for nSTB
```

**If you don't need automotive qualification:**
Use **TCAN334G** instead (similar, slightly cheaper)

---

## PCB Design Checklist

### Before Ordering New Boards

- [ ] Verify your current design doesn't use VREF (pin 5)
  - Check if VREF goes to MCU ADC
  - Check if VREF is used for split termination
  - Check if VREF is floating (no connection)

- [ ] Check RS (pin 8) configuration
  - Is RS connected to GND? (high-speed mode)
  - Is RS connected via resistor? (slope control)
  - Is RS floating? (standby mode)

- [ ] Add new components for TCAN3404-Q1
  - [ ] 10kΩ resistor: Pin 5 (nFAULT) to VCC
  - [ ] 10kΩ resistor: Pin 8 (nSTB) to VCC (or to MCU GPIO for power control)
  - [ ] Optional: Test points on pins 5 and 8 for debugging

- [ ] Verify power supply
  - [ ] VCC is clean 3.3V with <100mV ripple
  - [ ] 100nF decoupling capacitor near VCC pin
  - [ ] 10µF bulk capacitor near transceiver

- [ ] Update BOM
  - [ ] Replace SN65HVD230DR with TCAN3404DQ1 (or TCAN334GD)
  - [ ] Add pull-up resistors
  - [ ] Update datasheets reference

### Testing Plan

1. **Visual Inspection**
   - Verify correct chip orientation
   - Check solder joints on pins 5 and 8

2. **Power-On Test**
   - Measure VCC = 3.3V
   - Measure nFAULT = 3.3V (pulled high)
   - Measure nSTB = 3.3V (pulled high)

3. **Classical CAN Test** (before trying CAN FD)
   - Send 8-byte CAN message at 500 kbps
   - Verify communication with existing CAN 2.0B nodes
   - Confirm backward compatibility

4. **CAN FD Test** (with another CAN FD node)
   - Send 12-byte message
   - Send 32-byte message
   - Send 64-byte message
   - Verify all sizes work correctly

---

## Cost Analysis

### Per-Unit Cost Comparison

| Item | Current (SN65HVD230) | New (TCAN3404-Q1) | Difference |
|------|---------------------|-------------------|------------|
| Transceiver IC | $0.50 | $2.00 | +$1.50 |
| Pull-up resistors (2×) | $0.00 | $0.02 | +$0.02 |
| **Total** | **$0.50** | **$2.02** | **+$1.52** |

**PCB Changes:** $0 (same footprint, trace routing only)

**NRE Cost (one-time):**
- Schematic update: 1 hour
- PCB layout update: 2 hours
- Prototype build & test: 1 day
- **Total: ~$500-1000** depending on your setup

---

## Firmware Considerations

**Good news:** Your ATSAME51 MCU already has CAN FD hardware support!

**No firmware changes needed for initial testing** - TCAN3404-Q1 will work in classical CAN mode with existing firmware.

**To enable CAN FD:**
1. Switch to ACANFD_FeatherM4CAN library (or equivalent)
2. Update CANMessage structure to support 9-64 byte payloads
3. Update protocol to handle variable-length messages
4. See `CAN_FD_ANALYSIS.md` for full migration guide

---

## Alternative: Keep Classical CAN

**If CAN FD seems too complex right now:**

You could add more CAN controllers instead of upgrading to CAN FD:

**Option:** Use ATSAME51's **dual CAN controllers**
- CAN0: 8-byte classical messages
- CAN1: 8-byte classical messages
- **Total:** 16 bytes per transmission across two messages

**Pros:**
- No hardware changes needed
- Keep existing SN65HVD230DR
- Just use both CAN peripherals

**Cons:**
- ❌ Still limited to 8 bytes per message
- ❌ More complex message coordination
- ❌ Doesn't solve your "larger data sizes" requirement

**Verdict:** CAN FD is better for your use case.

---

## Summary

### Quick Decision Matrix

**Do you need 64-byte payloads?**
- ✅ YES → Go with CAN FD upgrade (TCAN3404-Q1)
- ❌ NO → Keep SN65HVD230DR and optimize protocol

**Can you redesign the PCB?**
- ✅ YES → Use TCAN3404-Q1, change pins 5 & 8 routing
- ❌ NO → Use external CAN FD module for prototyping

**Is this a production board?**
- ✅ YES → PCB redesign with TCAN3404-Q1 (best solution)
- ❌ NO (prototype) → External module or adapter board

**Does your design use VREF (pin 5)?**
- ✅ YES → Add external voltage divider after migration
- ❌ NO → Easy migration (just change pin 5 connection)

---

## Conclusion

**Unfortunately, there is NO pin-compatible drop-in replacement** for the SN65HVD230DR that supports CAN FD.

**However, migration is not difficult:**
- Same footprint (SOIC-8)
- Only 2 pins need different connections (pins 5 and 8)
- ~$1.50 per-unit cost increase
- ~1-2 days of engineering time

**Best path forward:**
1. **Check your schematic** - Is VREF (pin 5) used?
2. **Order TCAN3404-Q1 samples** from TI (free samples available)
3. **Test on breadboard** with your ATSAME51 board
4. **Update PCB design** with new pin 5/8 routing
5. **Order new boards** and validate

**For prototyping RIGHT NOW:**
Use an **external CAN FD breakout board** connected to your MCU directly, bypassing the SN65HVD230DR on your custom board.

---

## References

- [TI TCAN3404-Q1 Datasheet](https://www.ti.com/lit/ds/symlink/tcan3404-q1.pdf)
- [TI TCAN334 Datasheet](https://www.ti.com/lit/ds/symlink/tcan334.pdf)
- [TI SN65HVD230 Datasheet](https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf)
- [CAN FD Analysis Document](CAN_FD_ANALYSIS.md)
- [CAN Transceiver Comparison](CAN_TRANSCEIVER_COMPARISON.md)

---

**Need help?** Open an issue with your schematic (especially pins 5 and 8 connections) and I can provide specific migration guidance.

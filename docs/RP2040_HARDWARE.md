# RP2040 Hardware Configuration

This document describes the hardware setup for the Raspberry Pi Pico (RP2040) platform in the uCAN firmware.

## Overview

The RP2040 platform requires an external CAN transceiver since it lacks a built-in CAN peripheral. The firmware uses the **can2040** library, which implements CAN protocol entirely in software using the RP2040's Programmable I/O (PIO) state machines.

## Required Hardware

1. **Raspberry Pi Pico** (RP2040)
2. **MCP2551 CAN Transceiver** (3.3V compatible)
3. **CAN Bus** with 120Ω termination resistors at each end

## Pin Connections

### RP2040 to MCP2551 Wiring

```
┌─────────────────┐              ┌──────────────────┐
│  Raspberry Pi   │              │    MCP2551       │
│      Pico       │              │  CAN Transceiver │
├─────────────────┤              ├──────────────────┤
│                 │              │                  │
│ GP4 (Pin 6)  ───┼─────────────►│ 1  TXD (CTX)     │
│                 │              │                  │
│ GP5 (Pin 7)  ◄──┼──────────────│ 4  RXD (CRX)     │
│                 │              │                  │
│ 3.3V (Pin 36)───┼─────────────►│ 3  VDD           │
│                 │              │                  │
│ GND (Pin 38) ───┼─────────────►│ 2  VSS           │
│                 │              │                  │
└─────────────────┘              │ 8  Rs     ───┐   │
                                 │              │   │
                                 │ 5  Vref      │   │
                                 │              GND │
                                 │ 7  CANH   ───────┼───► CAN High
                                 │              │   │
                                 │ 6  CANL   ───────┼───► CAN Low
                                 │              │   │
                                 └──────────────┼───┘
                                                │
                                              120Ω termination
                                           (if bus end node)
```

### Pin Mapping Table

| RP2040 Pin | GPIO | Function     | MCP2551 Pin | Description           |
|------------|------|--------------|-------------|-----------------------|
| Pin 6      | GP4  | CAN TX       | Pin 1 (TXD) | Transmit data to CAN  |
| Pin 7      | GP5  | CAN RX       | Pin 4 (RXD) | Receive data from CAN |
| Pin 36     | 3.3V | Power        | Pin 3 (VDD) | 3.3V power supply     |
| Pin 38     | GND  | Ground       | Pin 2 (VSS) | Ground reference      |

### MCP2551 CAN Bus Connections

| MCP2551 Pin | Function | Connection                           |
|-------------|----------|--------------------------------------|
| Pin 6       | CANL     | CAN Bus Low (twisted pair)           |
| Pin 7       | CANH     | CAN Bus High (twisted pair)          |
| Pin 8       | Rs       | GND for high-speed mode (optional)   |
| Pin 5       | Vref     | Reference voltage (leave floating)   |

## Configuration

### CAN Bitrates

The can2040 implementation supports the following bitrates:

- 125 kbps
- 250 kbps
- **500 kbps** (default)
- 1 Mbps

Change bitrate using the `config:bitrate:XXXXX` command (e.g., `config:bitrate:250000`).

### High-Speed Mode

For optimal high-speed operation (500 kbps and 1 Mbps):

1. Connect **MCP2551 Pin 8 (Rs)** to **GND**
2. This sets the transceiver to high-speed mode
3. If left floating, the transceiver operates in slope-control mode

### CAN Bus Termination

CAN bus requires **120Ω termination resistors** at **both ends** of the bus:

```
                     120Ω                                      120Ω
    ┌──────────────[====]──────────────────────────────[====]──────────────┐
    │                                                                        │
   Node 1                          Node 2                               Node 3
(RP2040+MCP2551)                                                     (RP2040+MCP2551)
```

## Platform Capabilities

The RP2040 platform capabilities are queryable via the `get:capabilities` command, which returns JSON including:

```json
{
  "board": "Raspberry Pi Pico",
  "chip": "RP2040",
  "clock_mhz": 133,
  "flash_kb": 2048,
  "ram_kb": 264,
  "gpio": {
    "total": 26,
    "pwm": 16,
    "adc": 3,
    "dac": 0
  },
  "hardware": {
    "can_tx_pin": 4,
    "can_rx_pin": 5,
    "transceiver": "MCP2551",
    "can_implementation": "can2040 (PIO)"
  },
  "can": {
    "controllers": 1,
    "max_bitrate": 1000000,
    "fd_capable": false,
    "filters": 0
  },
  "max_rules": 16,
  "features": ["GPIO", "PWM", "ADC", "CAN_SEND", "FLASH"]
}
```

## Resource Limits

Due to the RP2040's 264KB RAM, the following limits are enforced:

| Resource           | Limit | Notes                                    |
|--------------------|-------|------------------------------------------|
| Action Rules       | 16    | Compared to 64 on SAMD51                 |
| CAN RX Buffer      | 32    | Messages buffered for processing         |
| CAN TX Buffer      | 16    | Messages queued for transmission         |
| Flash Storage      | 4KB   | Last sector at 0x101FF000                |

## Hardware Differences vs SAMD51

| Feature              | RP2040 (Pico)         | SAMD51 (Feather M4 CAN) |
|----------------------|-----------------------|-------------------------|
| CAN Implementation   | Software (can2040/PIO)| Hardware CAN0 peripheral|
| CAN Transceiver      | External MCP2551      | Built-in                |
| Max Action Rules     | 16                    | 64                      |
| DAC Support          | No                    | Yes (2 channels)        |
| NeoPixel             | No (standard Pico)    | Yes (built-in)          |
| Flash Storage        | 2MB internal          | 2MB external SPI flash  |
| Clock Speed          | 133 MHz               | 120 MHz                 |

## Troubleshooting

### CAN Communication Issues

1. **Verify wiring** - Double-check GP4→TXD, GP5→RXD connections
2. **Check termination** - Ensure 120Ω resistors at bus ends
3. **Test bitrate** - Try different bitrates: `config:bitrate:125000`
4. **Measure voltage** - MCP2551 VDD should be 3.3V

### PIO Resource Conflicts

The can2040 library uses PIO0 state machine 0. If you encounter PIO resource conflicts:

- Modify `platform_config.h` lines 48-49 to use PIO1 or different state machine
- Rebuild firmware: `pio run -e pico`

### Flash Storage Issues

If device name or rules don't persist:

1. Check flash initialization: Look for "Flash initialized" in serial output
2. Verify write operations: STATUS messages show "(saved to flash)" on success
3. Test with minimal rule: `add:rule:1:can:0x123:can_tx:0x456:01,02`
4. Reboot and verify: `get:rule:1` should return the rule

## See Also

- [RP2040_FLASH_STORAGE.md](RP2040_FLASH_STORAGE.md) - Flash persistence implementation details
- [PROTOCOL.md](PROTOCOL.md) - uCAN serial protocol specification
- [CAN_TRANSCEIVER_COMPARISON.md](CAN_TRANSCEIVER_COMPARISON.md) - Transceiver selection guide
- [DEVELOPER.md](DEVELOPER.md) - Development and build instructions

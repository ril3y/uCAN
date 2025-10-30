/**
 * Battery & Solar Monitoring Configuration
 *
 * Action rules for monitoring battery cell voltages and solar panel status.
 * Responds to CAN messages from BMS and solar controller.
 *
 * Based on the drive-control-hub protocol:
 * - 0x620: BMS Pack Data (voltage, current, SOC)
 * - 0x621: Cell Summary (min/max voltages)
 * - 0x623: BMS Power Status (cell count)
 * - 0x626-0x629: Individual Cell Voltages (rotating banks)
 * - 0x630: Solar Controller (voltage, current, power)
 *
 * @file battery_solar_config.h
 * @author ril3y
 * @date 2025-10-28
 */

#pragma once

#include <stdint.h>

// ============================================================================
// Configuration Identity
// ============================================================================

#define DEFAULT_CONFIG_NAME "Battery & Solar Monitor"
#define DEFAULT_CONFIG_RESET_PIN 22  // GP22 - Button to GND to reset to defaults

// ============================================================================
// Action Rule Structure (simplified for readability)
// ============================================================================

/**
 * Action rule configuration
 * Platform loaders convert this to platform-specific ActionRule format
 */
struct BatterySolarRule {
    uint32_t can_id;          // CAN message ID to trigger on
    uint32_t can_id_mask;     // Mask for CAN ID matching (0 = exact match)
    uint8_t data_byte_index;  // Which data byte to check (0-7)
    uint8_t data_value;       // Expected data value
    uint8_t data_mask;        // Mask for data byte (0xFF = exact match, 0x00 = ignore)
    const char* action_type;  // Action to perform: "GPIO_SET", "GPIO_CLEAR", "NEOPIXEL"
    uint8_t action_param1;    // Parameter 1 (e.g., GPIO pin number, R value)
    uint8_t action_param2;    // Parameter 2 (e.g., G value)
    uint8_t action_param3;    // Parameter 3 (e.g., B value)
    const char* description;  // Human-readable description
};

// ============================================================================
// Battery & Solar Monitoring Rules
// ============================================================================

/**
 * Example action rules for battery and solar monitoring
 *
 * Rule Examples:
 *
 * 1. Low Battery Warning (< 48V)
 *    - Trigger: 0x620 byte 0-1 (pack voltage) < 480 (48.0V in 0.1V units)
 *    - Action: Set GPIO pin HIGH (warning LED)
 *
 * 2. High Battery Voltage (> 58V)
 *    - Trigger: 0x620 byte 0-1 (pack voltage) > 580 (58.0V)
 *    - Action: Set GPIO pin HIGH (overvoltage warning)
 *
 * 3. Cell Voltage Imbalance Alert
 *    - Trigger: 0x621 byte 4 (cell voltage difference) > 100mV
 *    - Action: Flash NeoPixel red
 *
 * 4. Solar Power Available
 *    - Trigger: 0x630 byte 2-3 (solar current) > 50 (5.0A in 0.1A units)
 *    - Action: Set GPIO pin HIGH (charging indicator)
 *
 * 5. Battery Charging Status
 *    - Trigger: 0x620 byte 2-3 (pack current) > 0 (positive = charging)
 *    - Action: Flash NeoPixel green
 *
 * Note: For voltage/current comparisons, you'll need to implement threshold
 * checking in the action manager. These examples show the structure.
 */

#define DEFAULT_NUM_RULES 8

static const BatterySolarRule default_rules[DEFAULT_NUM_RULES] = {
    // Battery Pack Monitoring (0x620)
    {
        0x620,              // CAN ID: BMS Pack Data
        0x7FF,              // Mask: Exact ID match
        4,                  // Byte 4: SOC percentage
        20,                 // Value: 20% SOC or below
        0xFF,               // Mask: Check if SOC <= 20%
        "GPIO_SET",         // Action: Turn on low battery LED
        13,                 // Pin 13 (or your LED pin)
        0,                  // Unused
        0,                  // Unused
        "Low battery warning (SOC <= 20%)"
    },
    {
        0x620,              // CAN ID: BMS Pack Data
        0x7FF,              // Mask: Exact ID match
        4,                  // Byte 4: SOC percentage
        80,                 // Value: 80% SOC or above
        0xFF,               // Mask: Check if SOC >= 80%
        "GPIO_CLEAR",       // Action: Turn off low battery LED
        13,                 // Pin 13
        0,                  // Unused
        0,                  // Unused
        "Battery OK (SOC > 20%)"
    },

    // Cell Voltage Monitoring (0x621 - Cell Summary)
    {
        0x621,              // CAN ID: Cell Summary
        0x7FF,              // Mask: Exact ID match
        4,                  // Byte 4: Cell voltage difference (mV)
        100,                // Value: > 100mV difference
        0xFF,               // Mask: Check imbalance
        "NEOPIXEL",         // Action: Flash red for imbalance
        255,                // R: 255 (red)
        0,                  // G: 0
        0,                  // B: 0
        "Cell imbalance warning (>100mV)"
    },
    {
        0x621,              // CAN ID: Cell Summary
        0x7FF,              // Mask: Exact ID match
        4,                  // Byte 4: Cell voltage difference
        50,                 // Value: <= 50mV (balanced)
        0xFF,               // Mask
        "NEOPIXEL",         // Action: Green for balanced
        0,                  // R: 0
        255,                // G: 255 (green)
        0,                  // B: 0
        "Cells balanced (<=50mV difference)"
    },

    // Individual Cell Monitoring (0x626-0x629)
    {
        0x626,              // CAN ID: Cell Bank 0 (cells 0-1)
        0x7FC,              // Mask: Match 0x626-0x629 (any cell bank)
        0,                  // Byte 0: Bank index
        0,                  // Value: Bank 0
        0xFF,               // Mask: Exact match
        "NEOPIXEL",         // Action: Blue pulse during cell scan
        0,                  // R: 0
        0,                  // G: 0
        128,                // B: 128 (dim blue)
        "Cell voltage scan active (Bank 0)"
    },

    // Solar Panel Monitoring (0x630)
    {
        0x630,              // CAN ID: Solar Controller
        0x7FF,              // Mask: Exact ID match
        2,                  // Byte 2-3: Solar current (0.1A units)
        50,                 // Value: > 5.0A
        0xFF,               // Mask
        "GPIO_SET",         // Action: Turn on charging LED
        14,                 // Pin 14 (charging indicator)
        0,                  // Unused
        0,                  // Unused
        "Solar charging active (>5A)"
    },
    {
        0x630,              // CAN ID: Solar Controller
        0x7FF,              // Mask: Exact ID match
        2,                  // Byte 2-3: Solar current
        10,                 // Value: < 1.0A
        0xFF,               // Mask
        "GPIO_CLEAR",       // Action: Turn off charging LED
        14,                 // Pin 14
        0,                  // Unused
        0,                  // Unused
        "Solar charging low (<1A)"
    },

    // BMS Power Status (0x623)
    {
        0x623,              // CAN ID: BMS Power Status
        0x7FF,              // Mask: Exact ID match
        3,                  // Byte 3: Number of cells
        16,                 // Value: 16 cells (16S battery)
        0xFF,               // Mask: Exact match
        "NEOPIXEL",         // Action: Cyan to indicate 16S detected
        0,                  // R: 0
        255,                // G: 255 (cyan)
        255,                // B: 255
        "16S battery detected"
    }
};

/**
 * Notes on Implementation:
 *
 * These rules demonstrate structure but have limitations:
 * 1. Threshold comparisons (>, <, >=, <=) need action manager support
 * 2. Multi-byte value checks (voltage, current) need special handling
 * 3. NeoPixel actions may need duration/brightness control
 *
 * For full functionality, consider:
 * - Adding PARAM_SOURCE_DATA to extract values from CAN data
 * - Implementing comparison operators in matches_rule()
 * - Adding timer-based NeoPixel effects (flash, pulse)
 */

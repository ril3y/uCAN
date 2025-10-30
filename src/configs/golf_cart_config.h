/**
 * Golf Cart CAN Bus Configuration
 *
 * Pure configuration data for simulating a golf cart CAN bus environment.
 * Based on the drive-control-hub protocol specification.
 *
 * This file contains ONLY configuration data - no platform-specific implementation.
 * Platform-specific loaders (rp2040_config_loader.cpp, samd51_config_loader.cpp, etc.)
 * read this config and implement the appropriate initialization logic.
 *
 * Protocol Reference:
 * - All messages: 8 bytes with CRC8 in byte 7 (polynomial 0x07, init 0x00)
 * - Bitrate: 500 kbps
 * - Frame format: Standard 11-bit CAN IDs
 *
 * @file golf_cart_config.h
 * @author ril3y
 * @date 2025-10-28
 */

#pragma once

#include <stdint.h>

// ============================================================================
// Configuration Identity
// ============================================================================

#define DEFAULT_CONFIG_NAME "Golf Cart Simulator"
#define DEFAULT_CONFIG_RESET_PIN 22  // GP22 - Button to GND to reset to defaults

// ============================================================================
// CRC8 Helper (for data validation/calculation)
// ============================================================================

/**
 * Calculate CRC8 for golf cart CAN protocol
 * Polynomial: 0x07, Initial: 0x00, calculated over bytes 0-6
 */
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

// ============================================================================
// Configuration Rule Structure
// ============================================================================

/**
 * Simple rule configuration structure
 * Platform loaders convert this to platform-specific ActionRule format
 */
struct DefaultRuleConfig {
    uint32_t can_id;          // CAN message ID
    uint32_t interval_ms;     // Transmit interval in milliseconds
    uint8_t data[8];          // Message data (byte 7 = CRC8)
    const char* description;  // Human-readable description
};

// ============================================================================
// Default Rule Definitions
// ============================================================================

/**
 * Pre-calculated CAN message data for golf cart simulation
 *
 * Message Details:
 *
 * 0x500 (10Hz): Switch States
 *   Byte 0: 0x00 = Brake released
 *   Byte 1: 0x01 = Throttle pressed
 *   Byte 2: 0x01 = Forward selected
 *   Bytes 3-6: Reserved
 *   Byte 7: CRC8
 *
 * 0x610/0x612 (10Hz): Motor Telemetry
 *   Bytes 0-1: 0x05DC = 1500 RPM (big-endian uint16)
 *   Byte 2: 0x32 = 50A current
 *   Byte 3: 0x3C = 60°C temperature
 *   Byte 4: 0x4B = 75% throttle
 *   Bytes 5-6: Reserved
 *   Byte 7: CRC8
 *
 * 0x620 (10Hz): BMS Pack Data
 *   Bytes 0-1: 0x0200 = 512 = 51.2V (big-endian uint16, 0.1V units)
 *   Bytes 2-3: 0xFED4 = -300 = -30A discharge (big-endian int16, 0.1A units)
 *   Byte 4: 0x4B = 75% SOC
 *   Bytes 5-6: Reserved
 *   Byte 7: CRC8
 *
 * 0x630 (10Hz): Solar Controller
 *   Bytes 0-1: 0x0208 = 520 = 52.0V (big-endian uint16, 0.1V units)
 *   Bytes 2-3: 0x0064 = 100 = 10A charging (big-endian uint16, 0.1A units)
 *   Bytes 4-5: 0x0064 = 100W power (big-endian uint16)
 *   Byte 6: Reserved
 *   Byte 7: CRC8
 *
 * 0x600/0x601/0x602 (1Hz): Heartbeat Messages
 *   Bytes 0-3: 0x00000000 = Uptime counter (big-endian uint32, seconds)
 *   Bytes 4-6: Reserved
 *   Byte 7: CRC8
 *
 * 0x611/0x613 (1Hz): Motor Status/Faults
 *   Byte 0: 0x03 = Enabled + Ready (bits 0-1)
 *   Byte 1: 0x00 = No fault code
 *   Bytes 2-6: Reserved
 *   Byte 7: CRC8
 */

#define DEFAULT_NUM_RULES 20

static const DefaultRuleConfig default_rules[DEFAULT_NUM_RULES] = {
    // Critical 10Hz telemetry messages (100ms interval)
    {0x500, 100, {0x00, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x03}, "Switch states (brake/throttle/direction)"},
    {0x610, 100, {0x05, 0xDC, 0x32, 0x3C, 0x4B, 0x00, 0x00, 0x9E}, "Motor 1 telemetry (RPM/current/temp)"},
    {0x612, 100, {0x05, 0xDC, 0x32, 0x3C, 0x4B, 0x00, 0x00, 0x9C}, "Motor 2 telemetry (RPM/current/temp)"},
    {0x620, 100, {0x02, 0x00, 0xFE, 0xD4, 0x4B, 0x00, 0x00, 0x1D}, "BMS pack (voltage/current/SOC)"},
    {0x630, 100, {0x02, 0x08, 0x00, 0x64, 0x00, 0x64, 0x00, 0xEC}, "Solar controller (voltage/current/power)"},

    // Battery cell monitoring - 1Hz (1000ms interval)
    {0x621, 1000, {0x42, 0x0E, 0x40, 0x0E, 0x06, 0x00, 0x00, 0xA5}, "Cell summary (min=3648mV, max=3650mV, diff=6mV)"},
    {0x623, 5000, {0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0x10}, "BMS power status (16S battery)"},

    // Cell voltage banks - 0.1Hz (10000ms = 10 seconds per message) - Bank 0 (cells 0-7)
    {0x626, 10000, {0x00, 0x42, 0x0E, 0x44, 0x0E, 0x00, 0x00, 0x94}, "Cell Bank 0/0 (Cell 0=3650mV, Cell 1=3652mV)"},
    {0x627, 10000, {0x00, 0x40, 0x0E, 0x43, 0x0E, 0x00, 0x00, 0x91}, "Cell Bank 0/1 (Cell 2=3648mV, Cell 3=3651mV)"},
    {0x628, 10000, {0x00, 0x41, 0x0E, 0x42, 0x0E, 0x00, 0x00, 0x8B}, "Cell Bank 0/2 (Cell 4=3649mV, Cell 5=3650mV)"},
    {0x629, 10000, {0x00, 0x45, 0x0E, 0x3F, 0x0E, 0x00, 0x00, 0x99}, "Cell Bank 0/3 (Cell 6=3653mV, Cell 7=3647mV)"},

    // Cell voltage banks - Bank 1 (cells 8-15)
    {0x626, 10000, {0x01, 0x42, 0x0E, 0x43, 0x0E, 0x00, 0x00, 0x94}, "Cell Bank 1/0 (Cell 8=3650mV, Cell 9=3651mV)"},
    {0x627, 10000, {0x01, 0x44, 0x0E, 0x41, 0x0E, 0x00, 0x00, 0x94}, "Cell Bank 1/1 (Cell 10=3652mV, Cell 11=3649mV)"},
    {0x628, 10000, {0x01, 0x40, 0x0E, 0x42, 0x0E, 0x00, 0x00, 0x8B}, "Cell Bank 1/2 (Cell 12=3648mV, Cell 13=3650mV)"},
    {0x629, 10000, {0x01, 0x43, 0x0E, 0x42, 0x0E, 0x00, 0x00, 0x88}, "Cell Bank 1/3 (Cell 14=3651mV, Cell 15=3650mV)"},

    // System heartbeat messages 1Hz (1000ms interval)
    {0x600, 1000, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, "Wiring harness heartbeat"},
    {0x601, 1000, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, "Motor controller 1 heartbeat"},
    {0x602, 1000, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, "Motor controller 2 heartbeat"},
    {0x611, 1000, {0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03}, "Motor 1 status/faults"},
    {0x613, 1000, {0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01}, "Motor 2 status/faults"},
};

/**
 * Validate CRC8 in all default rules (optional compile-time check)
 * Platform loaders can call this during initialization
 */
inline bool validate_default_rules_crc() {
    for (uint8_t i = 0; i < DEFAULT_NUM_RULES; i++) {
        uint8_t expected_crc = default_rules[i].data[7];
        uint8_t calculated_crc = calc_crc8(default_rules[i].data, 7);
        if (expected_crc != calculated_crc) {
            return false;
        }
    }
    return true;
}

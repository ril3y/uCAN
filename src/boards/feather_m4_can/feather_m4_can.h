#pragma once

/**
 * @file feather_m4_can.h
 * @brief Adafruit Feather M4 CAN board configuration
 *
 * Complete board definition for the Adafruit Feather M4 CAN Express.
 * All board-specific configuration is consolidated in this single file.
 *
 * Hardware:
 * - MCU: ATSAME51J19A Cortex-M4F @ 120MHz
 * - Flash: 496KB internal, 2MB external SPI flash
 * - RAM: 192KB
 * - CAN: Built-in CAN controller with integrated transceiver
 * - NeoPixel: Built-in RGB LED on pin 8 (with power control on pin 17)
 * - Pins: 21 GPIO
 * - PWM: 16 channels via TCC (Timer/Counter for Control)
 * - ADC: 6 channels (dual 12-bit 1MSPS ADCs)
 * - DAC: 2 channels (true 12-bit DACs on A0 and A1)
 * - Features: Hardware crypto, RTC, I2S audio, I2C, SPI
 *
 * CAN Interface:
 * - Built-in CAN0 peripheral (no external transceiver needed)
 * - Supports 125kbps to 1Mbps bitrates
 * - 28 hardware message filters
 * - Integrated transceiver
 *
 * NeoPixel Visual Feedback:
 * - Green: CAN TX
 * - Yellow: CAN RX
 * - Red: CAN Error
 * - Power control via pin 17
 */

#include "../board_config.h"

// Pin configuration for Adafruit Feather M4 CAN
// Note: PIN_CAN_TX and PIN_CAN_RX are defined in variant.h and used by Adafruit CAN library
// We don't override them here - they're used directly by the library
const BoardPinConfig feather_m4_can_pins = {
    // CAN interface pins (built-in CAN peripheral)
    // The Adafruit CAN library uses PIN_CAN_TX and PIN_CAN_RX from variant.h directly
    // These pin config values are for documentation/caps response only
    .can_tx_pin = 22,             // PA22 (CAN0_TX) - defined as PIN_CAN_TX in variant.h
    .can_rx_pin = 23,             // PA23 (CAN0_RX) - defined as PIN_CAN_RX in variant.h
    .can_standby_pin = PIN_NOT_AVAILABLE,
    .can_speed_mode_pin = PIN_NOT_AVAILABLE,

    // No external power control needed
    .power_enable_pin = PIN_NOT_AVAILABLE,

    // NeoPixel on pin 8 with power control on pin 17
    .neopixel_pin = 8,
    .neopixel_power_pin = 17,
    .status_led_pin = 8,          // NeoPixel doubles as status LED

    // No SD card on Feather M4 CAN
    .sd_cs_pin = PIN_NOT_AVAILABLE,
    .sd_miso_pin = PIN_NOT_AVAILABLE,
    .sd_mosi_pin = PIN_NOT_AVAILABLE,
    .sd_sclk_pin = PIN_NOT_AVAILABLE,

    // No RS485 on Feather M4 CAN
    .rs485_tx_pin = PIN_NOT_AVAILABLE,
    .rs485_rx_pin = PIN_NOT_AVAILABLE,
    .rs485_enable_pin = PIN_NOT_AVAILABLE,
};

// Memory configuration for Feather M4 CAN
const BoardMemoryConfig feather_m4_can_memory = {
    .flash_size = 507904,         // 496KB internal flash
    .ram_size = 196608,           // 192KB SRAM
    .storage_size = 2097152,      // 2MB external SPI flash (W25Q16JV)
    .eeprom_size = 0,             // No EEPROM (uses SPI flash for storage)
};

// CAN configuration for Feather M4 CAN
const BoardCANConfig feather_m4_can_can = {
    .hardware_can = true,         // Hardware CAN peripheral (CAN0)
    .controller_type = "SAME51 CAN0",
    .transceiver_type = "Built-in",
    .controller_count = 1,
    .max_bitrate = 1000000,       // 1Mbps max
    .hardware_filters = 28,       // 28 programmable message filters
    .supports_extended = true,    // 29-bit extended IDs supported
    .supports_fd = false,         // No CAN-FD support
};

// Resource limits for Feather M4 CAN
const BoardResourceLimits feather_m4_can_resources = {
    .max_action_rules = 64,       // More RAM available (192KB)
    .gpio_count = 21,             // 21 GPIO pins available (some shared with peripherals)
    .pwm_channels = 16,           // 16 PWM outputs via TCC timers
    .adc_channels = 6,            // 6 ADC inputs (dual 12-bit 1MSPS ADCs)
    .dac_channels = 2,            // 2 true 12-bit DACs (A0 and A1)
    .i2c_buses = 2,               // 2 I2C peripherals (SERCOM)
    .spi_buses = 2,               // 2 SPI peripherals (SERCOM)
    .uart_ports = 6,              // 6 SERCOM peripherals (can be configured as UART)
};

// Complete board configuration for Adafruit Feather M4 CAN
BOARD_DEFINE(FEATHER_M4_CAN,
    // Identification
    .board_name = "Adafruit Feather M4 CAN",
    .manufacturer = "Adafruit Industries",
    .chip_name = "ATSAME51J19A",
    .platform = "SAMD51",

    // Hardware configuration
    .pins = feather_m4_can_pins,
    .memory = feather_m4_can_memory,
    .can = feather_m4_can_can,
    .resources = feather_m4_can_resources,

    // Feature flags (very feature-rich board)
    .features = FEATURE_GPIO_DIGITAL |
                FEATURE_GPIO_PWM |
                FEATURE_GPIO_ADC |
                FEATURE_GPIO_DAC |
                FEATURE_NEOPIXEL |
                FEATURE_CAN_BUS |
                FEATURE_FLASH_STORAGE |
                FEATURE_CRYPTO |
                FEATURE_RTC |
                FEATURE_I2S,

    // Default configurations
    .default_can_bitrate = 500000,    // 500kbps default
    .default_serial_baud = 115200,
    .can_rx_buffer_size = 64,         // Larger buffers with more RAM
    .can_tx_buffer_size = 32,
)

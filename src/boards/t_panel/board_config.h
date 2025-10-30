#pragma once

/**
 * @file t_panel.h
 * @brief LilyGo T-Panel board configuration
 *
 * Complete board definition for the LilyGo T-Panel, an ESP32-S3-based
 * smart display panel with touchscreen, CAN bus, and ESP32-H2 co-processor.
 *
 * Hardware:
 * - Primary MCU: ESP32-S3 dual-core Xtensa LX7 @ 240MHz
 * - Flash: 16MB
 * - PSRAM: 8MB
 * - Secondary MCU: ESP32-H2 (BLE/Thread/Zigbee)
 * - Display: 3.95" 480x480 IPS touchscreen (ST7701S driver)
 * - Touch: CST3240 capacitive touch controller
 * - CAN: Available on V1.2+ (shared with RS485 module socket)
 * - IO Expansion: XL9535 I2C GPIO expander
 * - Storage: SD card slot
 * - WiFi: 2.4/5 GHz 802.11 b/g/n
 * - Bluetooth: BLE 5.0
 *
 * Pin Configuration (V1.2+):
 * - CAN/RS485 TX: GPIO 16
 * - CAN/RS485 RX: GPIO 15
 * - Display: RGB parallel interface (many pins)
 * - Touch I2C: SDA=GPIO17, SCL=GPIO18, INT=GPIO21
 * - SD Card: CS=GPIO38, SCLK=GPIO36, MOSI=GPIO35, MISO=GPIO37
 * - XL9535 I2C: Same bus as touch
 * - ESP32-H2 UART: TX=GPIO47, RX=GPIO48
 * - ESP32-H2 Control: BOOT=GPIO33, RST=GPIO34
 *
 * Features:
 * - Large touchscreen display for rich UI
 * - Dual MCU architecture (S3 + H2)
 * - CAN bus for vehicle/industrial communication
 * - SD card for data logging
 * - WiFi/BLE for connectivity
 * - IO expansion via XL9535
 *
 * Purchase: https://www.lilygo.cc/products/t-panel-s3
 */

#include "../board_config.h"

// LilyGo T-Panel pin configuration
// Based on official T-Panel pinmap
// Note: This board has an optional RS485/CAN module connector
const BoardPinConfig t_panel_pins = {
    // CAN interface pins (V1.2+ optional module)
    // Connected via high-speed isolation transceiver module (D_GND, A, B, S_GND)
    // The README indicates V1.2+ uses GPIO 15/16 for CAN/RS485
    .can_tx_pin = 16,             // GPIO16 -> CAN/RS485 TX (via optional module)
    .can_rx_pin = 15,             // GPIO15 -> CAN/RS485 RX (via optional module)
    .can_standby_pin = PIN_NOT_AVAILABLE,
    .can_speed_mode_pin = PIN_NOT_AVAILABLE,

    // No external power control (powered via USB-C, 7-24V DC)
    .power_enable_pin = PIN_NOT_AVAILABLE,

    // No NeoPixel, but has LCD backlight control
    .neopixel_pin = PIN_NOT_AVAILABLE,
    .neopixel_power_pin = PIN_NOT_AVAILABLE,
    .status_led_pin = 33,         // LCD_BL on GPIO33 (backlight can indicate status)

    // SD card interface (verified from pinmap)
    .sd_cs_pin = 34,              // IO34 -> SD CS (corrected from pinmap)
    .sd_miso_pin = 37,            // IO37 -> SD MISO
    .sd_mosi_pin = 35,            // IO35 -> SD MOSI
    .sd_sclk_pin = 36,            // IO36 -> SD SCLK

    // RS485 interface (optional module, shares pins with CAN)
    // Connected via RS485_CON (IO07) on V1.2+
    .rs485_tx_pin = 16,           // Shared with CAN (via optional module)
    .rs485_rx_pin = 15,           // Shared with CAN (via optional module)
    .rs485_enable_pin = 7,        // IO07 -> RS485_CON control
};

// T-Panel memory configuration
const BoardMemoryConfig t_panel_memory = {
    .flash_size = 16777216,       // 16MB flash
    .ram_size = 520192,           // 520KB internal SRAM
    .storage_size = 8388608,      // 8MB PSRAM (external)
    .eeprom_size = 4096,          // Emulated EEPROM via Preferences
};

// T-Panel CAN configuration
const BoardCANConfig t_panel_can = {
    .hardware_can = true,         // Hardware TWAI controller
    .controller_type = "ESP32-S3 TWAI",
    .transceiver_type = "TD501MCANFD (optional module)",
    .controller_count = 1,
    .max_bitrate = 1000000,       // 1Mbps max (5Mbps with CAN-FD module)
    .hardware_filters = 0,        // Software filtering via TWAI
    .supports_extended = true,    // 29-bit extended IDs
    .supports_fd = false,         // CAN-FD possible with TD501MCANFD module
};

// T-Panel resource limits
const BoardResourceLimits t_panel_resources = {
    .max_action_rules = 64,       // Lots of RAM with PSRAM
    .gpio_count = 45,             // ESP32-S3 has more GPIOs (many used by display)
    .pwm_channels = 8,            // Limited by display usage
    .adc_channels = 10,           // Reduced from 20 (some pins used by display)
    .dac_channels = 0,            // No DAC on ESP32-S3
    .i2c_buses = 2,
    .spi_buses = 3,
    .uart_ports = 3,
};

// Complete board configuration for LilyGo T-Panel
BOARD_DEFINE(LILYGO_T_PANEL,
    // Identification
    .board_name = "LilyGo T-Panel",
    .manufacturer = "LilyGo",
    .chip_name = "ESP32-S3",
    .platform = "ESP32",

    // Hardware configuration
    .pins = t_panel_pins,
    .memory = t_panel_memory,
    .can = t_panel_can,
    .resources = t_panel_resources,

    // Feature flags (display-focused board)
    .features = FEATURE_GPIO_DIGITAL |
                FEATURE_GPIO_PWM |
                FEATURE_GPIO_ADC |
                FEATURE_CAN_BUS |
                FEATURE_FLASH_STORAGE |
                FEATURE_SD_CARD |
                FEATURE_WIFI |
                FEATURE_BLUETOOTH |
                FEATURE_DISPLAY |
                FEATURE_TOUCHSCREEN |
                FEATURE_RS485 |
                FEATURE_CRYPTO |
                FEATURE_RTC,

    // Default configurations
    .default_can_bitrate = 500000,    // 500kbps default
    .default_serial_baud = 115200,
    .can_rx_buffer_size = 64,
    .can_tx_buffer_size = 32,
)

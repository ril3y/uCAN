#pragma once

/**
 * @file t_can485.h
 * @brief LilyGo T-CAN485 board configuration
 *
 * Complete board definition for the LilyGo T-CAN485, an ESP32-based
 * industrial CAN and RS485 communication board.
 *
 * Hardware:
 * - MCU: ESP32 single-core @ 240MHz
 * - Flash: 4MB
 * - RAM: 520KB SRAM
 * - CAN: SN65HVD231 transceiver (TWAI controller)
 * - RS485: MAX13487EESA+ transceiver
 * - LED: WS2812 RGB NeoPixel (GPIO 4)
 * - Power: ME2107 boost converter (5-12V input)
 * - Storage: SD card slot
 * - WiFi: 2.4 GHz 802.11 b/g/n
 * - Bluetooth: Classic + BLE 4.2
 *
 * Pin Configuration:
 * - CAN TX: GPIO (configurable via TWAI)
 * - CAN RX: GPIO (configurable via TWAI)
 * - CAN Speed Mode: GPIO (for SN65HVD231 slope control)
 * - RS485 TX: GPIO 22
 * - RS485 RX: GPIO 21
 * - RS485 EN: GPIO 9
 * - RS485 Callback: GPIO 17
 * - WS2812 Data: GPIO 4
 * - ME2107 Enable: GPIO 16
 * - SD Card: GPIO 13 (CS), GPIO 15 (MOSI), GPIO 2 (MISO), GPIO 14 (SCLK)
 *
 * Features:
 * - Industrial voltage input (5-12V via ME2107 boost converter)
 * - Dual communication interfaces (CAN + RS485)
 * - Visual feedback via WS2812 RGB LED
 * - Data logging via SD card
 * - WiFi/BT for remote monitoring
 *
 * Purchase: https://pt.aliexpress.com/item/1005003624034092.html
 */

#include "../board_config.h"

// LilyGo T-CAN485 pin configuration
// Based on official pinmap: https://github.com/ril3y/T-CAN485
const BoardPinConfig t_can485_pins = {
    // CAN interface pins (TWAI + SN65HVD231 transceiver)
    // Verified from official T-CAN485 pinmap
    .can_tx_pin = 27,             // IO27 -> CAN TX (TWAI TX)
    .can_rx_pin = 26,             // IO26 -> CAN RX (TWAI RX)
    .can_standby_pin = 23,        // IO23 -> CAN_SE (SN65HVD231 standby/slope)
    .can_speed_mode_pin = 23,     // Same as standby (CAN_SE controls slope/standby)

    // ME2107 boost converter enable pin
    .power_enable_pin = 16,       // GPIO16 -> ME2107 EN (assumed from docs)

    // WS2812 RGB NeoPixel LED
    .neopixel_pin = 4,            // IO04 -> WS2812 Data
    .neopixel_power_pin = PIN_NOT_AVAILABLE,  // No separate power control
    .status_led_pin = 4,          // WS2812 doubles as status LED

    // SD card interface (SPI)
    .sd_cs_pin = 13,              // IO13 -> SD_CS
    .sd_miso_pin = 2,             // IO02 -> SD_MISO
    .sd_mosi_pin = 15,            // IO15 -> SD_MOSI
    .sd_sclk_pin = 14,            // IO14 -> SD_SCLK

    // RS485 interface (MAX13487EESA+)
    .rs485_tx_pin = 22,           // IO22 -> RS485_TX
    .rs485_rx_pin = 21,           // IO21 -> RS485_RX
    .rs485_enable_pin = 17,       // IO17 -> RS485_EN (DE/RE control)
    // Note: IO19 is RS485_SE (speed/enable select)
};

// T-CAN485 memory configuration
const BoardMemoryConfig t_can485_memory = {
    .flash_size = 4194304,        // 4MB flash
    .ram_size = 520192,           // 520KB internal SRAM
    .storage_size = 0,            // SD card (variable size, not counted here)
    .eeprom_size = 4096,          // Emulated EEPROM via Preferences
};

// T-CAN485 CAN configuration
const BoardCANConfig t_can485_can = {
    .hardware_can = true,         // Hardware TWAI controller
    .controller_type = "ESP32 TWAI",
    .transceiver_type = "SN65HVD231",
    .controller_count = 1,
    .max_bitrate = 1000000,       // 1Mbps max
    .hardware_filters = 0,        // Software filtering via TWAI acceptance filters
    .supports_extended = true,    // 29-bit extended IDs supported
    .supports_fd = false,         // No CAN-FD support
};

// T-CAN485 resource limits
const BoardResourceLimits t_can485_resources = {
    .max_action_rules = 48,       // Good amount of RAM
    .gpio_count = 34,             // ESP32 standard (some pins used by peripherals)
    .pwm_channels = 16,           // 16 LEDC PWM channels
    .adc_channels = 18,           // 18 ADC channels
    .dac_channels = 2,            // 2 8-bit DACs
    .i2c_buses = 2,
    .spi_buses = 3,               // SPI (SD card uses VSPI)
    .uart_ports = 3,              // UART0 (USB), UART1 (RS485), UART2 (available)
};

// Complete board configuration for LilyGo T-CAN485
BOARD_DEFINE(LILYGO_T_CAN485,
    // Identification
    .board_name = "LilyGo T-CAN485",
    .manufacturer = "LilyGo",
    .chip_name = "ESP32",
    .platform = "ESP32",

    // Hardware configuration
    .pins = t_can485_pins,
    .memory = t_can485_memory,
    .can = t_can485_can,
    .resources = t_can485_resources,

    // Feature flags (very feature-rich industrial board)
    .features = FEATURE_GPIO_DIGITAL |
                FEATURE_GPIO_PWM |
                FEATURE_GPIO_ADC |
                FEATURE_GPIO_DAC |
                FEATURE_NEOPIXEL |
                FEATURE_CAN_BUS |
                FEATURE_FLASH_STORAGE |
                FEATURE_SD_CARD |
                FEATURE_WIFI |
                FEATURE_BLUETOOTH |
                FEATURE_RS485 |
                FEATURE_CRYPTO |
                FEATURE_RTC,

    // Default configurations
    .default_can_bitrate = 500000,    // 500kbps default
    .default_serial_baud = 115200,
    .can_rx_buffer_size = 64,
    .can_tx_buffer_size = 32,
)

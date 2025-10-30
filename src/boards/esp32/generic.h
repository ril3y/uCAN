#pragma once

/**
 * @file generic.h
 * @brief Generic ESP32 DevKit board configuration
 *
 * Complete board definition for generic ESP32 development boards.
 * This serves as the base configuration for all ESP32-based boards.
 *
 * Hardware:
 * - MCU: ESP32 dual-core Xtensa LX6 @ 240MHz
 * - Flash: Typically 4MB (configurable)
 * - RAM: 520KB SRAM (+ optional external PSRAM)
 * - CAN: TWAI (Two-Wire Automotive Interface) hardware controller
 * - Transceiver: External (SN65HVD231 or MCP2551 recommended)
 * - WiFi: 2.4 GHz 802.11 b/g/n
 * - Bluetooth: Classic + BLE 4.2
 *
 * Default CAN Pin Configuration:
 * - CAN TX: GPIO 5
 * - CAN RX: GPIO 4
 * Note: Pins are configurable and can be changed via build flags
 *
 * Features:
 * - Hardware CAN controller (TWAI)
 * - WiFi and Bluetooth connectivity
 * - Rich peripheral set (SPI, I2C, UART, PWM, ADC, DAC, etc.)
 * - Flash storage via Preferences API
 */

#include "../board_config.h"

// Generic ESP32 pin configuration
// Note: GPIO5 and GPIO4 are commonly used for CAN but can be changed
const BoardPinConfig esp32_generic_pins = {
    // CAN interface pins (TWAI peripheral)
    .can_tx_pin = 5,              // Default: GPIO5 (TX)
    .can_rx_pin = 4,              // Default: GPIO4 (RX)
    .can_standby_pin = PIN_NOT_AVAILABLE,
    .can_speed_mode_pin = PIN_NOT_AVAILABLE,

    // No power control on generic board
    .power_enable_pin = PIN_NOT_AVAILABLE,

    // No built-in NeoPixel on generic ESP32
    .neopixel_pin = PIN_NOT_AVAILABLE,
    .neopixel_power_pin = PIN_NOT_AVAILABLE,
    .status_led_pin = 2,          // Built-in LED on GPIO2 (common on DevKits)

    // No SD card on generic board
    .sd_cs_pin = PIN_NOT_AVAILABLE,
    .sd_miso_pin = PIN_NOT_AVAILABLE,
    .sd_mosi_pin = PIN_NOT_AVAILABLE,
    .sd_sclk_pin = PIN_NOT_AVAILABLE,

    // No RS485 on generic board
    .rs485_tx_pin = PIN_NOT_AVAILABLE,
    .rs485_rx_pin = PIN_NOT_AVAILABLE,
    .rs485_enable_pin = PIN_NOT_AVAILABLE,
};

// ESP32 memory configuration
const BoardMemoryConfig esp32_generic_memory = {
    .flash_size = 4194304,        // 4MB flash (typical, can be 2MB/8MB/16MB)
    .ram_size = 520192,           // 520KB internal SRAM
    .storage_size = 0,            // No external PSRAM by default
    .eeprom_size = 4096,          // Emulated EEPROM via Preferences (4KB typical)
};

// ESP32 CAN configuration
const BoardCANConfig esp32_generic_can = {
    .hardware_can = true,         // Hardware TWAI controller
    .controller_type = "ESP32 TWAI",
    .transceiver_type = "External (SN65HVD231 recommended)",
    .controller_count = 1,
    .max_bitrate = 1000000,       // 1Mbps max
    .hardware_filters = 0,        // TWAI has acceptance filters (not counted here)
    .supports_extended = true,    // 29-bit extended IDs supported
    .supports_fd = false,         // No CAN-FD support on standard ESP32
};

// ESP32 resource limits
const BoardResourceLimits esp32_generic_resources = {
    .max_action_rules = 48,       // Good amount of RAM available
    .gpio_count = 34,             // GPIO0-GPIO39 (some input-only)
    .pwm_channels = 16,           // 16 independent PWM channels (LEDC)
    .adc_channels = 18,           // 18 ADC channels (2 SAR ADCs)
    .dac_channels = 2,            // 2 8-bit DACs (GPIO25, GPIO26)
    .i2c_buses = 2,               // 2 I2C controllers
    .spi_buses = 4,               // 4 SPI controllers (SPI, HSPI, VSPI, etc.)
    .uart_ports = 3,              // 3 UART controllers
};

// Complete board configuration for generic ESP32
BOARD_DEFINE(ESP32_GENERIC,
    // Identification
    .board_name = "ESP32 DevKit",
    .manufacturer = "Espressif Systems",
    .chip_name = "ESP32",
    .platform = "ESP32",

    // Hardware configuration
    .pins = esp32_generic_pins,
    .memory = esp32_generic_memory,
    .can = esp32_generic_can,
    .resources = esp32_generic_resources,

    // Feature flags
    .features = FEATURE_GPIO_DIGITAL |
                FEATURE_GPIO_PWM |
                FEATURE_GPIO_ADC |
                FEATURE_GPIO_DAC |
                FEATURE_CAN_BUS |
                FEATURE_FLASH_STORAGE |
                FEATURE_WIFI |
                FEATURE_BLUETOOTH |
                FEATURE_CRYPTO |
                FEATURE_RTC,

    // Default configurations
    .default_can_bitrate = 500000,    // 500kbps default
    .default_serial_baud = 115200,
    .can_rx_buffer_size = 64,         // Good-sized buffers
    .can_tx_buffer_size = 32,
)

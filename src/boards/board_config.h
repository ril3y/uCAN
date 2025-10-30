#pragma once

/**
 * @file board_config.h
 * @brief Centralized board configuration system
 *
 * This header provides a unified system for defining board-specific configurations.
 * Each board is defined in its own header file with all relevant information
 * (pins, capabilities, memory specs, features) in one place.
 *
 * Benefits:
 * - Single source of truth for board configurations
 * - Adding new boards requires only 1-2 files instead of 8+
 * - Clear separation between platform code and board-specific config
 * - Compile-time selection with zero runtime overhead
 *
 * Usage:
 * 1. Create board-specific header in src/boards/<platform>/<board_name>.h
 * 2. Use BOARD_DEFINE() macro to declare all board properties
 * 3. Board is automatically available via board_registry.h
 */

#include <stdint.h>
#include <stdbool.h>

/**
 * Board Pin Configuration
 * Defines all hardware pin assignments for a board
 */
struct BoardPinConfig {
    // CAN interface pins
    uint8_t can_tx_pin;
    uint8_t can_rx_pin;

    // Optional CAN control pins
    uint8_t can_standby_pin;      // 0 if not used
    uint8_t can_speed_mode_pin;   // 0 if not used (for boards with mode select)

    // Optional power control
    uint8_t power_enable_pin;     // 0 if not used (e.g., ME2107 boost converter)

    // NeoPixel/LED pins
    uint8_t neopixel_pin;         // 0 if not available
    uint8_t neopixel_power_pin;   // 0 if not used
    uint8_t status_led_pin;       // 0 if not available

    // SD card pins (if available)
    uint8_t sd_cs_pin;            // 0 if not available
    uint8_t sd_miso_pin;
    uint8_t sd_mosi_pin;
    uint8_t sd_sclk_pin;

    // Other communication interfaces
    uint8_t rs485_tx_pin;         // 0 if not available
    uint8_t rs485_rx_pin;
    uint8_t rs485_enable_pin;
};

/**
 * Board Memory Configuration
 */
struct BoardMemoryConfig {
    uint32_t flash_size;          // Internal flash size in bytes
    uint32_t ram_size;            // RAM size in bytes
    uint32_t storage_size;        // External storage (SPI flash, PSRAM, etc.)
    uint32_t eeprom_size;         // EEPROM or emulated EEPROM size
};

/**
 * Board CAN Configuration
 */
struct BoardCANConfig {
    bool hardware_can;            // True if hardware CAN controller, false if PIO/software
    const char* controller_type;  // e.g., "TWAI", "CAN0", "bxCAN", "PIO (can2040)"
    const char* transceiver_type; // e.g., "SN65HVD231", "MCP2551", "Built-in"
    uint8_t controller_count;     // Number of CAN controllers
    uint32_t max_bitrate;         // Maximum supported bitrate
    uint8_t hardware_filters;     // Number of hardware filters (0 if none)
    bool supports_extended;       // Extended (29-bit) CAN ID support
    bool supports_fd;             // CAN-FD support
};

/**
 * Board Feature Flags
 */
enum BoardFeature {
    FEATURE_GPIO_DIGITAL    = (1 << 0),
    FEATURE_GPIO_PWM        = (1 << 1),
    FEATURE_GPIO_ADC        = (1 << 2),
    FEATURE_GPIO_DAC        = (1 << 3),
    FEATURE_NEOPIXEL        = (1 << 4),
    FEATURE_CAN_BUS         = (1 << 5),
    FEATURE_FLASH_STORAGE   = (1 << 6),
    FEATURE_SD_CARD         = (1 << 7),
    FEATURE_WIFI            = (1 << 8),
    FEATURE_BLUETOOTH       = (1 << 9),
    FEATURE_RS485           = (1 << 10),
    FEATURE_DISPLAY         = (1 << 11),
    FEATURE_TOUCHSCREEN     = (1 << 12),
    FEATURE_CRYPTO          = (1 << 13),
    FEATURE_RTC             = (1 << 14),
    FEATURE_I2S             = (1 << 15),
};

/**
 * Board Resource Limits
 */
struct BoardResourceLimits {
    uint8_t max_action_rules;     // Maximum number of action rules
    uint8_t gpio_count;           // Total available GPIO pins
    uint8_t pwm_channels;         // Available PWM channels
    uint8_t adc_channels;         // ADC input channels
    uint8_t dac_channels;         // DAC output channels
    uint8_t i2c_buses;            // I2C bus count
    uint8_t spi_buses;            // SPI bus count
    uint8_t uart_ports;           // UART port count
};

/**
 * Complete Board Configuration
 * This is the main structure that encompasses all board properties
 */
struct BoardConfig {
    // Identification
    const char* board_id;         // Unique board identifier (e.g., "RPI_PICO")
    const char* board_name;       // Human-readable name
    const char* manufacturer;     // Board manufacturer
    const char* chip_name;        // Main MCU chip name
    const char* platform;         // Platform family (RP2040, SAMD51, ESP32, etc.)

    // Hardware configuration
    BoardPinConfig pins;
    BoardMemoryConfig memory;
    BoardCANConfig can;
    BoardResourceLimits resources;

    // Feature flags
    uint32_t features;

    // Default configurations
    uint32_t default_can_bitrate;
    uint32_t default_serial_baud;
    uint16_t can_rx_buffer_size;
    uint16_t can_tx_buffer_size;

    // Helper method
    bool has_feature(BoardFeature feature) const {
        return (features & feature) != 0;
    }
};

/**
 * Macro to help define boards more concisely
 * Usage example in board header file:
 *
 * BOARD_DEFINE(RPI_PICO,
 *     .board_name = "Raspberry Pi Pico",
 *     .manufacturer = "Raspberry Pi Foundation",
 *     ...
 * )
 */
#define BOARD_DEFINE(id, ...) \
    const BoardConfig BOARD_##id = { \
        .board_id = #id, \
        __VA_ARGS__ \
    };

/**
 * Pin helper - returns 0 if pin is not available
 */
#define PIN_NOT_AVAILABLE 0
#define PIN_DEFINED(pin) ((pin) != 0)

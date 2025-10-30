#pragma once

/**
 * @file board_registry.h
 * @brief Compile-time board selection and registry
 *
 * This file automatically includes the correct board configuration based on
 * compile-time defines and provides a unified interface for accessing board
 * configuration throughout the codebase.
 *
 * The board is selected based on PlatformIO environment and Arduino board defines.
 */

#include "board_config.h"

// Platform detection - determine which platform we're building for
#if defined(ARDUINO_RASPBERRY_PI_PICO) || defined(ARDUINO_RASPBERRY_PI_PICO_W)
    #ifndef PLATFORM_RP2040
        #define PLATFORM_RP2040
    #endif
    #define PLATFORM_NAME "RP2040"
#elif defined(ARDUINO_ADAFRUIT_FEATHER_M4_CAN)
    #ifndef PLATFORM_SAMD51
        #define PLATFORM_SAMD51
    #endif
    #define PLATFORM_NAME "SAMD51"
#elif defined(ARDUINO_ARCH_ESP32)
    #ifndef PLATFORM_ESP32
        #define PLATFORM_ESP32
    #endif
    #define PLATFORM_NAME "ESP32"
#elif defined(ARDUINO_ARCH_STM32)
    #ifndef PLATFORM_STM32
        #define PLATFORM_STM32
    #endif
    #define PLATFORM_NAME "STM32"
#else
    #error "Unsupported platform - please add platform detection"
#endif

// Board-specific includes based on platform and board variant
#ifdef PLATFORM_RP2040
    // Currently only Raspberry Pi Pico supported for RP2040
    #include "rpi_pico/rpi_pico.h"
    #define CURRENT_BOARD BOARD_RPI_PICO
#endif

#ifdef PLATFORM_SAMD51
    // Currently only Feather M4 CAN supported for SAMD51
    #include "feather_m4_can/feather_m4_can.h"
    #define CURRENT_BOARD BOARD_FEATHER_M4_CAN
#endif

#ifdef PLATFORM_ESP32
    // ESP32 supports multiple board variants
    #if defined(BOARD_T_CAN485)
        #include "t_can485/board_config.h"
        #define CURRENT_BOARD BOARD_LILYGO_T_CAN485
    #elif defined(BOARD_T_PANEL)
        #include "t_panel/board_config.h"
        #define CURRENT_BOARD BOARD_LILYGO_T_PANEL
    #else
        // Default to generic ESP32 DevKit
        #include "esp32/generic.h"
        #define CURRENT_BOARD BOARD_ESP32_GENERIC
    #endif
#endif

#ifdef PLATFORM_STM32
    // STM32 board variants will go here
    #error "STM32 boards not yet implemented"
#endif

/**
 * Global accessor for current board configuration
 * This is the primary way to access board config throughout the codebase
 */
inline const BoardConfig& get_board_config() {
    return CURRENT_BOARD;
}

/**
 * Convenience macros for accessing common board properties
 */
#define BOARD_NAME          (get_board_config().board_name)
#define BOARD_MANUFACTURER  (get_board_config().manufacturer)
#define BOARD_CHIP          (get_board_config().chip_name)

// Pin access macros
#define CAN_TX_PIN          (get_board_config().pins.can_tx_pin)
#define CAN_RX_PIN          (get_board_config().pins.can_rx_pin)
#define NEOPIXEL_PIN        (get_board_config().pins.neopixel_pin)
#define NEOPIXEL_POWER_PIN  (get_board_config().pins.neopixel_power_pin)
#define STATUS_LED_PIN      (get_board_config().pins.status_led_pin)

// Memory info
#define FLASH_SIZE          (get_board_config().memory.flash_size)
#define RAM_SIZE            (get_board_config().memory.ram_size)

// CAN configuration
#define CAN_HARDWARE        (get_board_config().can.hardware_can)
#define CAN_CONTROLLER      (get_board_config().can.controller_type)
#define CAN_MAX_BITRATE     (get_board_config().can.max_bitrate)

// Resource limits
// MAX_ACTION_RULES must be compile-time constant for array sizing
// We use the maximum across all boards, then check board limit at runtime
#define MAX_ACTION_RULES_COMPILE_TIME 64  // Maximum across all boards (SAMD51)
#define MAX_ACTION_RULES    MAX_ACTION_RULES_COMPILE_TIME
#define GPIO_COUNT          (get_board_config().resources.gpio_count)

// Feature checks
#define HAS_NEOPIXEL        (get_board_config().has_feature(FEATURE_NEOPIXEL))
#define HAS_SD_CARD         (get_board_config().has_feature(FEATURE_SD_CARD))
#define HAS_WIFI            (get_board_config().has_feature(FEATURE_WIFI))
#define HAS_BLUETOOTH       (get_board_config().has_feature(FEATURE_BLUETOOTH))
#define HAS_DISPLAY         (get_board_config().has_feature(FEATURE_DISPLAY))

// Buffer sizes
#define CAN_RX_BUFFER_SIZE  (get_board_config().can_rx_buffer_size)
#define CAN_TX_BUFFER_SIZE  (get_board_config().can_tx_buffer_size)

// Default values
#ifndef DEFAULT_CAN_BITRATE
    #define DEFAULT_CAN_BITRATE (get_board_config().default_can_bitrate)
#endif
#define DEFAULT_SERIAL_BAUD (get_board_config().default_serial_baud)

// LED_BUILTIN compatibility - use status LED pin from board config
// Note: Some platforms define LED_BUILTIN, so we provide STATUS_LED_PIN as alternative
#define STATUS_LED_PIN (get_board_config().pins.status_led_pin)

#pragma once

/**
 * @file platform_config.h
 * @brief Legacy platform configuration header - DEPRECATED
 *
 * This file is deprecated in favor of the centralized board registry system.
 * It now simply includes board_registry.h for backward compatibility.
 *
 * All new code should include "../boards/board_registry.h" directly.
 */

// Include the new centralized board registry
#include "../boards/board_registry.h"

// Legacy compatibility - these are now provided by board_registry.h
// Platform defines: PLATFORM_RP2040, PLATFORM_SAMD51, PLATFORM_ESP32, etc.
// Pin macros: CAN_TX_PIN, CAN_RX_PIN, NEOPIXEL_PIN, etc.
// Default values: DEFAULT_CAN_BITRATE, DEFAULT_SERIAL_BAUD, etc.
// Buffer sizes: CAN_RX_BUFFER_SIZE, CAN_TX_BUFFER_SIZE

// Platform-specific compatibility defines
#ifdef PLATFORM_RP2040
    #define CAN_USES_PIO true
    #define CAN_PIO_INSTANCE pio0
    #define CAN_PIO_SM 0
#endif

#ifdef PLATFORM_SAMD51
    #define CAN_USES_PIO false
    #define CAN_PERIPHERAL CAN0     // Built-in CAN0 peripheral
#endif

#ifdef PLATFORM_ESP32
    #define CAN_USES_PIO false
#endif

#ifdef PLATFORM_STM32
    #define CAN_USES_PIO false
#endif

// Version information
#define FIRMWARE_VERSION "1.0.0"
#define PROTOCOL_VERSION "1.0"
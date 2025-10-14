#pragma once

// Platform detection based on compiler defines
#if defined(ARDUINO_RASPBERRY_PI_PICO) || defined(ARDUINO_RASPBERRY_PI_PICO_W)
    #define PLATFORM_RP2040
    #define PLATFORM_NAME "Raspberry Pi Pico"
#elif defined(ARDUINO_ADAFRUIT_FEATHER_M4_CAN)
    #define PLATFORM_SAMD51
    #define PLATFORM_NAME "Adafruit Feather M4 CAN"
#elif defined(ARDUINO_ARCH_ESP32)
    #define PLATFORM_ESP32
    #define PLATFORM_NAME "ESP32"
#elif defined(ARDUINO_ARCH_STM32)
    #define PLATFORM_STM32
    #define PLATFORM_NAME "STM32"
#else
    #error "Unsupported platform - please add platform detection"
#endif

// Platform-specific pin configurations
#ifdef PLATFORM_RP2040
    // RP2040 with MCP2551 transceiver
    #define CAN_TX_PIN 4    // GP4 -> MCP2551 CTX
    #define CAN_RX_PIN 5    // GP5 -> MCP2551 CRX
    #define CAN_USES_PIO true
    #define CAN_PIO_INSTANCE pio0
    #define CAN_PIO_SM 0
#endif

#ifdef PLATFORM_SAMD51
    // SAMD51 built-in CAN peripheral
    #define CAN_TX_PIN PIN_CAN_TX   // Defined in variant.h
    #define CAN_RX_PIN PIN_CAN_RX   // Defined in variant.h
    #define CAN_USES_PIO false
    #define CAN_PERIPHERAL CAN0     // Built-in CAN0 peripheral
#endif

#ifdef PLATFORM_ESP32
    // ESP32 TWAI (CAN) peripheral
    #define CAN_TX_PIN GPIO_NUM_5
    #define CAN_RX_PIN GPIO_NUM_4
    #define CAN_USES_PIO false
#endif

#ifdef PLATFORM_STM32
    // STM32 bxCAN peripheral
    #define CAN_TX_PIN PB9
    #define CAN_RX_PIN PB8
    #define CAN_USES_PIO false
#endif

// Default CAN configuration
#define DEFAULT_CAN_BITRATE 500000  // 500kbps
#define DEFAULT_SERIAL_BAUD 115200

// Buffer sizes (platform-dependent)
#ifdef PLATFORM_RP2040
    #define CAN_RX_BUFFER_SIZE 32
    #define CAN_TX_BUFFER_SIZE 16
#else
    #define CAN_RX_BUFFER_SIZE 64
    #define CAN_TX_BUFFER_SIZE 32
#endif

// Version information
#define FIRMWARE_VERSION "1.0.0"
#define PROTOCOL_VERSION "1.0"
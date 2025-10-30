#pragma once

/**
 * @file rpi_pico.h
 * @brief Raspberry Pi Pico board configuration
 *
 * Complete board definition for the Raspberry Pi Pico with external MCP2551 CAN transceiver.
 * All board-specific configuration is consolidated in this single file.
 *
 * Hardware:
 * - MCU: RP2040 dual-core Cortex-M0+ @ 133MHz
 * - Flash: 2MB
 * - RAM: 264KB
 * - CAN: External MCP2551 transceiver via PIO (software CAN using can2040)
 * - Pins: 26 GPIO (GP0-GP25)
 * - PWM: 16 channels (8 slices x 2 outputs)
 * - ADC: 3 channels (GP26-GP28)
 * - No NeoPixel, no DAC, no external SPI flash on standard Pico
 *
 * Pin Connections for CAN:
 *   RP2040 GPIO  ->  MCP2551 Pin  ->  Function
 *   -----------      ------------      --------
 *   GP4 (Pin 6)  ->  CTX (Pin 1)   ->  CAN TX Data
 *   GP5 (Pin 7)  ->  CRX (Pin 4)   ->  CAN RX Data
 *   3.3V         ->  VDD (Pin 3)   ->  Power
 *   GND          ->  VSS (Pin 2)   ->  Ground
 *
 * MCP2551 to CAN Bus:
 *   CANH (Pin 7) -> CAN Bus High
 *   CANL (Pin 6) -> CAN Bus Low
 *
 * Notes:
 * - 120Ω termination resistor required at each end of CAN bus
 * - Supports 125kbps to 1Mbps (configurable via commands)
 * - Uses can2040 PIO-based implementation (no hardware CAN peripheral)
 * - Rs pin (Pin 8) can be connected to GND for high-speed mode
 */

#include "../board_config.h"

// Pin configuration for Raspberry Pi Pico
const BoardPinConfig rpi_pico_pins = {
    // CAN interface pins (external MCP2551 transceiver)
    .can_tx_pin = 4,              // GP4 -> MCP2551 CTX (Pin 1)
    .can_rx_pin = 5,              // GP5 -> MCP2551 CRX (Pin 4)
    .can_standby_pin = PIN_NOT_AVAILABLE,
    .can_speed_mode_pin = PIN_NOT_AVAILABLE,

    // No power control on standard Pico
    .power_enable_pin = PIN_NOT_AVAILABLE,

    // No NeoPixel or status LED on standard Pico
    .neopixel_pin = PIN_NOT_AVAILABLE,
    .neopixel_power_pin = PIN_NOT_AVAILABLE,
    .status_led_pin = PIN_NOT_AVAILABLE,

    // No SD card on standard Pico
    .sd_cs_pin = PIN_NOT_AVAILABLE,
    .sd_miso_pin = PIN_NOT_AVAILABLE,
    .sd_mosi_pin = PIN_NOT_AVAILABLE,
    .sd_sclk_pin = PIN_NOT_AVAILABLE,

    // No RS485 on standard Pico
    .rs485_tx_pin = PIN_NOT_AVAILABLE,
    .rs485_rx_pin = PIN_NOT_AVAILABLE,
    .rs485_enable_pin = PIN_NOT_AVAILABLE,
};

// Memory configuration for Raspberry Pi Pico
const BoardMemoryConfig rpi_pico_memory = {
    .flash_size = 2097152,        // 2MB internal flash
    .ram_size = 264192,           // 264KB SRAM
    .storage_size = 0,            // No external SPI flash on standard Pico
    .eeprom_size = 4096,          // Emulated EEPROM in flash (4KB reserved)
};

// CAN configuration for Raspberry Pi Pico
const BoardCANConfig rpi_pico_can = {
    .hardware_can = false,        // Software CAN via PIO
    .controller_type = "can2040 (PIO)",
    .transceiver_type = "MCP2551",
    .controller_count = 1,
    .max_bitrate = 1000000,       // 1Mbps max (can2040 limitation)
    .hardware_filters = 0,        // No hardware filters (software CAN)
    .supports_extended = true,    // 29-bit extended IDs supported
    .supports_fd = false,         // No CAN-FD support
};

// Resource limits for Raspberry Pi Pico
const BoardResourceLimits rpi_pico_resources = {
    .max_action_rules = 16,       // Limited by RAM (264KB total)
    .gpio_count = 26,             // GP0-GP25 (some reserved for CAN/peripherals)
    .pwm_channels = 16,           // 8 PWM slices x 2 channels each
    .adc_channels = 3,            // ADC0-ADC2 (GP26-GP28) + internal temp sensor
    .dac_channels = 0,            // No DAC on RP2040
    .i2c_buses = 2,               // 2 I2C peripherals
    .spi_buses = 2,               // 2 SPI peripherals
    .uart_ports = 2,              // 2 UART peripherals (one used for USB serial)
};

// Complete board configuration for Raspberry Pi Pico
BOARD_DEFINE(RPI_PICO,
    // Identification
    .board_name = "Raspberry Pi Pico",
    .manufacturer = "Raspberry Pi Foundation",
    .chip_name = "RP2040",
    .platform = "RP2040",

    // Hardware configuration
    .pins = rpi_pico_pins,
    .memory = rpi_pico_memory,
    .can = rpi_pico_can,
    .resources = rpi_pico_resources,

    // Feature flags
    .features = FEATURE_GPIO_DIGITAL |
                FEATURE_GPIO_PWM |
                FEATURE_GPIO_ADC |
                FEATURE_CAN_BUS |
                FEATURE_FLASH_STORAGE,

    // Default configurations
    .default_can_bitrate = 500000,    // 500kbps default
    .default_serial_baud = 115200,
    .can_rx_buffer_size = 32,         // Smaller buffers to conserve RAM
    .can_tx_buffer_size = 16,
)

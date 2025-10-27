#pragma once

#include <stdint.h>
#include <stdbool.h>

/**
 * Platform Capability Flags
 *
 * These flags indicate what hardware features and action types
 * are supported by the current platform.
 */
enum PlatformCapability {
    CAP_GPIO_DIGITAL     = (1 << 0),   // Digital GPIO read/write
    CAP_GPIO_PWM         = (1 << 1),   // PWM output
    CAP_GPIO_ANALOG      = (1 << 2),   // Analog input (ADC)
    CAP_GPIO_DAC         = (1 << 3),   // Analog output (DAC)
    CAP_NEOPIXEL         = (1 << 4),   // NeoPixel/WS2812 support
    CAP_CAN_SEND         = (1 << 5),   // Auto CAN response
    CAP_FLASH_STORAGE    = (1 << 6),   // Persistent storage
    CAP_CRYPTO           = (1 << 7),   // Hardware crypto
    CAP_RTC              = (1 << 8),   // Real-time clock
    CAP_I2S              = (1 << 9),   // I2S audio
    CAP_I2C              = (1 << 10),  // I2C communication
};

/**
 * Board Capabilities Structure
 *
 * Contains all platform-specific hardware information and capabilities.
 * This structure is populated at compile-time for each platform.
 */
struct BoardCapabilities {
    // Board identification
    const char* board_name;
    const char* chip_name;
    const char* manufacturer;

    // Capability flags
    uint32_t capability_flags;

    // Resource limits
    uint8_t max_action_rules;      // Maximum number of action rules
    uint8_t gpio_count;            // Total GPIO pins
    uint8_t pwm_channels;          // Available PWM channels
    uint8_t adc_channels;          // ADC input channels
    uint8_t dac_channels;          // DAC output channels

    // Memory information
    uint32_t flash_size;           // Flash memory size in bytes
    uint32_t ram_size;             // RAM size in bytes
    uint32_t storage_size;         // Additional storage (SPI flash, etc.)

    // NeoPixel-specific (if CAP_NEOPIXEL set)
    uint8_t neopixel_pin;          // NeoPixel data pin
    uint8_t neopixel_power_pin;    // NeoPixel power control pin (0 if none)
    bool neopixel_available;       // NeoPixel present on board

    // CAN-specific
    bool can_hardware;             // True if hardware CAN, false if PIO/software
    const char* can_controller;    // CAN controller type

    // Helper methods
    bool has_capability(PlatformCapability cap) const {
        return (capability_flags & cap) != 0;
    }
};

// Global capability structure (defined per-platform)
extern const BoardCapabilities platform_capabilities;

// Device naming
#define MAX_DEVICE_NAME_LENGTH 32
extern char device_name[MAX_DEVICE_NAME_LENGTH];  // User-configurable device name

// Capability query functions
void send_capabilities_json();       // Send JSON formatted capabilities
void send_pin_info();                // Send available pin information
void send_supported_actions();       // Send list of supported action types

// Device name management
void set_device_name(const char* name);  // Set custom device name
const char* get_device_name();           // Get current device name
bool load_device_name();                 // Load name from storage
bool save_device_name();                 // Save name to storage

// Platform-specific default rules
#ifdef PLATFORM_SAMD51
class ActionManagerBase;  // Forward declaration
struct ActionRule;        // Forward declaration
uint8_t load_samd51_default_rules(ActionManagerBase* manager);

// Flash storage functions (SAMD51 only)
bool init_flash_storage();
bool save_rules_to_flash(const ActionRule* rules, uint8_t count);
uint8_t load_rules_from_flash(ActionRule* rules, uint8_t max_count);
bool erase_flash_storage();
#endif

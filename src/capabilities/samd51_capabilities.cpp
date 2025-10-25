#ifdef PLATFORM_SAMD51

#include "board_capabilities.h"
#include "../hal/platform_config.h"

// NeoPixel pin definitions from Feather M4 CAN variant
#ifndef NEOPIXEL_PIN
    #define NEOPIXEL_PIN 8
#endif

#ifndef NEOPIXEL_POWER_PIN
    #define NEOPIXEL_POWER_PIN 17
#endif

/**
 * Adafruit Feather M4 CAN (ATSAME51J19A) Capabilities
 *
 * This board features hardware CAN with built-in transceiver, NeoPixel,
 * dual 12-bit ADCs and DACs, PWM, 2MB SPI Flash, and hardware crypto.
 * It's significantly more capable than the RP2040.
 */
const BoardCapabilities platform_capabilities = {
    // Board identification
    .board_name = PLATFORM_NAME,
    .chip_name = "ATSAME51J19A",
    .manufacturer = "Adafruit Industries",

    // Capability flags - SAMD51 has almost everything
    .capability_flags = CAP_GPIO_DIGITAL |
                       CAP_GPIO_PWM |
                       CAP_GPIO_ANALOG |
                       CAP_GPIO_DAC |
                       CAP_NEOPIXEL |
                       CAP_CAN_SEND |
                       CAP_FLASH_STORAGE |
                       CAP_CRYPTO |
                       CAP_RTC |
                       CAP_I2S,

    // Resource limits
    .max_action_rules = 64,       // Can support 64 rules with available RAM
    .gpio_count = 21,             // 21 GPIO pins available
    .pwm_channels = 16,           // 16 PWM outputs
    .adc_channels = 6,            // Dual 1 MSPS 12-bit ADCs
    .dac_channels = 2,            // True 12-bit DACs on A0 and A1

    // Memory information
    .flash_size = 507904,         // 496KB internal flash
    .ram_size = 196608,           // 192KB RAM
    .storage_size = 2097152,      // 2MB SPI Flash chip

    // NeoPixel - built-in on pin 8
    .neopixel_pin = NEOPIXEL_PIN,
    .neopixel_power_pin = NEOPIXEL_POWER_PIN,
    .neopixel_available = true,

    // CAN-specific
    .can_hardware = true,         // Hardware CAN with built-in transceiver
    .can_controller = "SAME51 CAN",
};

#endif // PLATFORM_SAMD51

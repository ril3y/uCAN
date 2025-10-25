#ifdef PLATFORM_RP2040

#include "board_capabilities.h"
#include "../hal/platform_config.h"

/**
 * Raspberry Pi Pico (RP2040) Capabilities
 *
 * The RP2040 uses software CAN (ACAN2040 via PIO) with an external
 * MCP2551 transceiver. It has basic GPIO and PWM support but lacks
 * NeoPixel, DAC, and advanced peripherals found on the SAMD51.
 */
const BoardCapabilities platform_capabilities = {
    // Board identification
    .board_name = PLATFORM_NAME,
    .chip_name = "RP2040",
    .manufacturer = "Raspberry Pi Foundation",

    // Capability flags - RP2040 has basic digital GPIO, PWM, ADC, and CAN send
    .capability_flags = CAP_GPIO_DIGITAL |
                       CAP_GPIO_PWM |
                       CAP_GPIO_ANALOG |
                       CAP_CAN_SEND,

    // Resource limits
    .max_action_rules = 16,       // Limited to 16 rules to conserve RAM
    .gpio_count = 26,             // GP0-GP25 (some used for CAN)
    .pwm_channels = 16,           // 8 PWM slices x 2 channels
    .adc_channels = 3,            // ADC0, ADC1, ADC2 (GP26-GP28)
    .dac_channels = 0,            // No DAC on RP2040

    // Memory information
    .flash_size = 2097152,        // 2MB Flash
    .ram_size = 264192,           // 264KB RAM
    .storage_size = 0,            // No additional SPI flash on basic Pico

    // NeoPixel - not available on standard Pico
    .neopixel_pin = 0,
    .neopixel_power_pin = 0,
    .neopixel_available = false,

    // CAN-specific
    .can_hardware = false,        // Software CAN via PIO (ACAN2040)
    .can_controller = "ACAN2040 (PIO)",
};

#endif // PLATFORM_RP2040

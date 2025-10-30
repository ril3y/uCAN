#ifdef PLATFORM_ESP32

#include <ArduinoJson.h>
#include "../board_capabilities.h"
#include "../../hal/platform_config.h"

/**
 * ESP32 Platform Capabilities
 *
 * The ESP32 family provides rich features:
 * - Hardware TWAI (CAN) controller
 * - WiFi 2.4GHz (ESP32) or 2.4/5GHz (ESP32-S3)
 * - Bluetooth Classic + BLE
 * - Rich GPIO with PWM, ADC, DAC (varies by chip)
 * - Hardware crypto engine
 * - RTC with deep sleep
 * - Preferences API for non-volatile storage
 *
 * Board-specific features (NeoPixel, SD, RS485) vary by variant.
 */
const BoardCapabilities platform_capabilities = {
    // Board identification - comes from board registry
    .board_name = BOARD_NAME,
    .chip_name = BOARD_CHIP,
    .manufacturer = BOARD_MANUFACTURER,

    // Capability flags - ESP32 has most features
    // Note: NeoPixel capability is determined at runtime via neopixel_available field
    .capability_flags = CAP_GPIO_DIGITAL |
                       CAP_GPIO_PWM |
                       CAP_GPIO_ANALOG |
                       CAP_GPIO_DAC |        // 2x 8-bit DACs (GPIO25, GPIO26)
                       CAP_CAN_SEND |
                       CAP_FLASH_STORAGE |
                       CAP_CRYPTO |          // Hardware AES, SHA, RSA
                       CAP_RTC,              // RTC with deep sleep

    // Resource limits - from board registry
    .max_action_rules = MAX_ACTION_RULES,
    .gpio_count = GPIO_COUNT,
    .pwm_channels = get_board_config().resources.pwm_channels,
    .adc_channels = get_board_config().resources.adc_channels,
    .dac_channels = get_board_config().resources.dac_channels,

    // Memory information - from board registry
    .flash_size = FLASH_SIZE,
    .ram_size = RAM_SIZE,
    .storage_size = get_board_config().memory.storage_size,

    // NeoPixel - from board registry (if available)
    // Note: neopixel_available is determined at runtime via get_board_config()
    .neopixel_pin = NEOPIXEL_PIN,
    .neopixel_power_pin = NEOPIXEL_POWER_PIN,
    .neopixel_available = get_board_config().has_feature(FEATURE_NEOPIXEL),

    // CAN-specific - from board registry
    .can_hardware = CAN_HARDWARE,
    .can_controller = CAN_CONTROLLER,
    .can_controllers = get_board_config().can.controller_count,
    .can_max_bitrate = CAN_MAX_BITRATE,
    .can_filters = get_board_config().can.hardware_filters,
};

/**
 * Add ESP32-specific hardware information to capabilities JSON
 *
 * This function is called by the shared capability query code to add
 * platform-specific hardware details to the CAPS response.
 */
void add_platform_hardware_info(JsonObject& hardware) {
    // ESP32 CAN pins (TWAI peripheral)
    hardware["can_tx_pin"] = CAN_TX_PIN;
    hardware["can_rx_pin"] = CAN_RX_PIN;
    hardware["can_controller"] = CAN_CONTROLLER;
    hardware["transceiver"] = get_board_config().can.transceiver_type;

    // Board-specific features
    if (get_board_config().has_feature(FEATURE_NEOPIXEL)) {
        hardware["neopixel_pin"] = NEOPIXEL_PIN;
    }

    if (get_board_config().has_feature(FEATURE_SD_CARD)) {
        JsonObject sd = hardware["sd_card"].to<JsonObject>();
        sd["cs_pin"] = get_board_config().pins.sd_cs_pin;
        sd["miso_pin"] = get_board_config().pins.sd_miso_pin;
        sd["mosi_pin"] = get_board_config().pins.sd_mosi_pin;
        sd["sclk_pin"] = get_board_config().pins.sd_sclk_pin;
    }

    // RS485 interface (if available)
    if (get_board_config().has_feature(FEATURE_RS485)) {
        JsonObject rs485 = hardware["rs485"].to<JsonObject>();
        rs485["tx_pin"] = get_board_config().pins.rs485_tx_pin;
        rs485["rx_pin"] = get_board_config().pins.rs485_rx_pin;
        rs485["enable_pin"] = get_board_config().pins.rs485_enable_pin;
    }

    // Display (if available)
    if (get_board_config().has_feature(FEATURE_DISPLAY)) {
        JsonObject display = hardware["display"].to<JsonObject>();
        display["backlight_pin"] = get_board_config().pins.status_led_pin;  // LCD backlight
        display["resolution"] = "480x480";  // T-Panel specific
        display["driver"] = "ST7701S";      // T-Panel specific
    }

    // Touchscreen (if available)
    if (get_board_config().has_feature(FEATURE_TOUCHSCREEN)) {
        JsonObject touch = hardware["touchscreen"].to<JsonObject>();
        touch["controller"] = "CST3240";  // T-Panel specific
        touch["interface"] = "I2C";
    }

    // Connectivity
    JsonObject connectivity = hardware["connectivity"].to<JsonObject>();
    connectivity["wifi"] = get_board_config().has_feature(FEATURE_WIFI);
    connectivity["bluetooth"] = get_board_config().has_feature(FEATURE_BLUETOOTH);

    // Power
    if (PIN_DEFINED(get_board_config().pins.power_enable_pin)) {
        hardware["power_enable_pin"] = get_board_config().pins.power_enable_pin;
    }
}

#endif // PLATFORM_ESP32

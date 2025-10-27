#include "samd51_pin_caps.h"
#include "../../actions/pin_manager.h"
#include "../../utils/pin_error_logger.h"
#include <Arduino.h>

/**
 * SAMD51 Feather M4 CAN - Complete Pin Capability Table
 *
 * Based on SAMD51_PIN_REFERENCE.md and Adafruit schematic.
 *
 * Notes:
 * - PA22, PA23: CAN TX/RX (hardwired to MCP2562)
 * - PA24, PA25: USB D-/D+ (system use)
 * - PB03: NeoPixel (can be disabled)
 * - PA12, PA13: Default I2C (conflicts with SPI on SERCOM2/4)
 */
static const PinCapabilities SAMD51_PIN_TABLE[] = {
    // Analog Pins
    {A0,  true, true,  true,  true,  false, false, 0xFF, 0xFF, 0xFF, 0xFF, false, "PA02/A0/DAC0"},
    {A1,  true, true,  true,  true,  false, false, 0xFF, 0xFF, 0xFF, 0xFF, false, "PA05/A1/DAC1"},
    {A2,  true, true,  true,  false, false, false, 0xFF, 0xFF, 0xFF, 0xFF, false, "PB08/A2"},
    {A3,  true, true,  true,  false, false, false, 0xFF, 0xFF, 0xFF, 0xFF, false, "PB09/A3"},
    {A4,  true, true,  true,  false, false, false, 0xFF, 0xFF, 0xFF, 0xFF, false, "PA04/A4"},
    {A5,  true, true,  true,  false, false, false, 0xFF, 0xFF, 0xFF, 0xFF, false, "PA06/A5"},

    // Digital Pins (common PWM-capable pins)
    {5,   true, true,  false, false, false, false, 0xFF, 0xFF, 0,    0,    false, "PA16/D5"},
    {6,   true, true,  false, false, false, false, 0xFF, 0xFF, 0,    1,    false, "PA18/D6"},
    {9,   true, true,  false, false, false, false, 0xFF, 0xFF, 0,    3,    false, "PA19/D9"},
    {10,  true, true,  false, false, false, false, 0xFF, 0xFF, 1,    0,    false, "PA20/D10"},
    {11,  true, true,  false, false, false, false, 0xFF, 0xFF, 1,    1,    false, "PA21/D11"},
    {12,  true, true,  false, false, false, false, 0xFF, 0xFF, 1,    2,    false, "PA22/D12"},
    {13,  true, true,  false, false, false, false, 0xFF, 0xFF, 1,    3,    false, "PA23/D13"},

    // I2C Default Pins (SERCOM2)
    {14,  true, false, false, false, true,  false, 2,    0,    0xFF, 0xFF, false, "PA12/SDA"},  // SERCOM2 PAD[0]
    {15,  true, false, false, false, false, true,  2,    1,    0xFF, 0xFF, false, "PA13/SCL"},  // SERCOM2 PAD[1]

    // Alternate I2C Pins (SERCOM0)
    {16,  true, true,  false, false, true,  false, 0,    0,    0xFF, 0xFF, false, "PA08/D16"},  // SERCOM0 PAD[0]
    {17,  true, true,  false, false, false, true,  0,    1,    0xFF, 0xFF, false, "PA09/D17"},  // SERCOM0 PAD[1]

    // NeoPixel Pin
    {8,   true, false, false, false, false, false, 0xFF, 0xFF, 0xFF, 0xFF, false, "PB03/NEOPIXEL"},

    // Reserved Pins (CANNOT BE USED)
    {22,  false, false, false, false, false, false, 0xFF, 0xFF, 0xFF, 0xFF, true,  "PA22/CAN_TX"},
    {23,  false, false, false, false, false, false, 0xFF, 0xFF, 0xFF, 0xFF, true,  "PA23/CAN_RX"},
    {24,  false, false, false, false, false, false, 0xFF, 0xFF, 0xFF, 0xFF, true,  "PA24/USB_D-"},
    {25,  false, false, false, false, false, false, 0xFF, 0xFF, 0xFF, 0xFF, true,  "PA25/USB_D+"},
};

static constexpr uint8_t PIN_TABLE_SIZE = sizeof(SAMD51_PIN_TABLE) / sizeof(PinCapabilities);

const PinCapabilities* samd51_get_pin_capabilities(uint8_t pin) {
    for (uint8_t i = 0; i < PIN_TABLE_SIZE; i++) {
        if (SAMD51_PIN_TABLE[i].pin_number == pin) {
            return &SAMD51_PIN_TABLE[i];
        }
    }
    return nullptr;
}

bool samd51_validate_pin_for_mode(uint8_t pin, uint8_t mode) {
    const PinCapabilities* caps = samd51_get_pin_capabilities(pin);

    if (!caps) {
        LOG_PIN_ERROR(pin, "Pin not found in capability table");
        return false;
    }

    if (caps->is_reserved) {
        LOG_PIN_ERROR(pin, "Pin reserved by hardware (CAN, USB)");
        return false;
    }

    // Check capability based on mode
    switch (mode) {
        case PINMODE_GPIO_INPUT:
        case PINMODE_GPIO_OUTPUT:
            if (!caps->can_gpio) {
                LOG_PIN_ERROR(pin, "Pin does not support GPIO");
                return false;
            }
            break;

        case PINMODE_PWM:
            if (!caps->can_pwm) {
                LOG_PIN_ERROR(pin, "Pin does not support PWM");
                return false;
            }
            break;

        case PINMODE_ADC:
            if (!caps->can_adc) {
                LOG_PIN_ERROR(pin, "Pin does not support ADC");
                return false;
            }
            break;

        case PINMODE_DAC:
            if (!caps->can_dac) {
                LOG_PIN_ERROR(pin, "Pin does not support DAC");
                return false;
            }
            break;

        case PINMODE_I2C_SDA:
            if (!caps->can_i2c_sda) {
                LOG_PIN_ERROR(pin, "Pin does not support I2C SDA");
                return false;
            }
            break;

        case PINMODE_I2C_SCL:
            if (!caps->can_i2c_scl) {
                LOG_PIN_ERROR(pin, "Pin does not support I2C SCL");
                return false;
            }
            break;

        default:
            LOG_PIN_WARNING(pin, "Unknown pin mode for validation");
            return false;
    }

    return true;
}

bool samd51_is_pin_reserved(uint8_t pin) {
    const PinCapabilities* caps = samd51_get_pin_capabilities(pin);
    return caps && caps->is_reserved;
}

bool samd51_get_i2c_sercom(uint8_t pin, bool is_sda, uint8_t& sercom_out, uint8_t& pad_out) {
    const PinCapabilities* caps = samd51_get_pin_capabilities(pin);

    if (!caps) {
        return false;
    }

    if (is_sda && !caps->can_i2c_sda) {
        return false;
    }

    if (!is_sda && !caps->can_i2c_scl) {
        return false;
    }

    if (caps->sercom_instance == 0xFF) {
        return false;
    }

    sercom_out = caps->sercom_instance;
    pad_out = caps->sercom_pad;
    return true;
}

bool samd51_get_pwm_tcc(uint8_t pin, uint8_t& tcc_out, uint8_t& channel_out) {
    const PinCapabilities* caps = samd51_get_pin_capabilities(pin);

    if (!caps || !caps->can_pwm) {
        return false;
    }

    if (caps->tcc_instance == 0xFF) {
        return false;
    }

    tcc_out = caps->tcc_instance;
    channel_out = caps->tcc_channel;
    return true;
}

void samd51_init_pin_capabilities(PinManager* pin_mgr) {
    if (!pin_mgr) {
        return;
    }

    Serial.println("[PIN_INFO] Initializing SAMD51 pin capabilities");

    // Mark reserved pins
    for (uint8_t i = 0; i < PIN_TABLE_SIZE; i++) {
        if (SAMD51_PIN_TABLE[i].is_reserved) {
            pin_mgr->allocate_pin(SAMD51_PIN_TABLE[i].pin_number, PINMODE_RESERVED);
        }
    }

    Serial.println("[PIN_INFO] SAMD51 pin capabilities initialized");
}

void samd51_log_pin_capabilities(uint8_t pin) {
    const PinCapabilities* caps = samd51_get_pin_capabilities(pin);

    if (!caps) {
        LOG_PIN_ERROR(pin, "Pin not found in capability table");
        return;
    }

    Serial.println("=== Pin Capabilities ===");
    Serial.print("Pin: ");
    Serial.print(pin);
    Serial.print(" (");
    Serial.print(caps->pin_name);
    Serial.println(")");

    if (caps->is_reserved) {
        Serial.println("STATUS: RESERVED (Cannot be used)");
        return;
    }

    Serial.print("GPIO: ");
    Serial.println(caps->can_gpio ? "Yes" : "No");

    Serial.print("PWM: ");
    if (caps->can_pwm) {
        Serial.print("Yes (TCC");
        Serial.print(caps->tcc_instance);
        Serial.print(" CH");
        Serial.print(caps->tcc_channel);
        Serial.println(")");
    } else {
        Serial.println("No");
    }

    Serial.print("ADC: ");
    Serial.println(caps->can_adc ? "Yes" : "No");

    Serial.print("DAC: ");
    Serial.println(caps->can_dac ? "Yes" : "No");

    Serial.print("I2C SDA: ");
    if (caps->can_i2c_sda) {
        Serial.print("Yes (SERCOM");
        Serial.print(caps->sercom_instance);
        Serial.print(" PAD");
        Serial.print(caps->sercom_pad);
        Serial.println(")");
    } else {
        Serial.println("No");
    }

    Serial.print("I2C SCL: ");
    if (caps->can_i2c_scl) {
        Serial.print("Yes (SERCOM");
        Serial.print(caps->sercom_instance);
        Serial.print(" PAD");
        Serial.print(caps->sercom_pad);
        Serial.println(")");
    } else {
        Serial.println("No");
    }

    Serial.println("========================");
}

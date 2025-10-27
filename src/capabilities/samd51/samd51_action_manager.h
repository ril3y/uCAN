#pragma once

#include "../../actions/action_manager_base.h"

#ifdef PLATFORM_SAMD51

// Forward declaration for NeoPixel (avoid including full header)
class Adafruit_NeoPixel;

/**
 * SAMD51ActionManager
 *
 * Platform-specific action manager for Adafruit Feather M4 CAN.
 * Implements SAMD51-specific features:
 * - NeoPixel visual feedback (built-in RGB LED)
 * - 12-bit PWM output
 * - 12-bit DAC output (2 channels)
 * - Flash-based rule persistence
 *
 * Custom commands registered:
 * - neopixel:R:G:B[:BRIGHTNESS] - Direct NeoPixel control
 * - dac:CHANNEL:VALUE - Set DAC output (0-4095)
 */
class SAMD51ActionManager : public ActionManagerBase {
public:
    SAMD51ActionManager();
    virtual ~SAMD51ActionManager();

    bool initialize(CANInterface* can_if) override;

protected:
    // Platform-specific action execution
    bool execute_gpio_action(ActionType type, uint8_t pin) override;
    bool execute_pwm_action(uint8_t pin, uint8_t duty) override;
    bool execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) override;
    bool execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id) override;

    // Platform-specific persistence
    bool save_rules_impl() override;
    uint8_t load_rules_impl() override;

    // Custom command registration
    void register_custom_commands() override;

private:
    Adafruit_NeoPixel* neopixel_;  // Built-in NeoPixel instance
};

#endif // PLATFORM_SAMD51

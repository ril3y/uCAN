#pragma once

#include "../../actions/action_manager_base.h"

#ifdef PLATFORM_RP2040

/**
 * RP2040ActionManager
 *
 * Platform-specific action manager for Raspberry Pi Pico.
 * Implements RP2040-specific features:
 * - Basic GPIO (no NeoPixel support)
 * - 16-bit PWM via PIO or hardware PWM
 * - 12-bit ADC (up to 4 channels + temperature sensor)
 * - Future: Flash-based rule persistence via LittleFS or EEPROM emulation
 *
 * Custom commands registered:
 * - pwm_freq:PIN:FREQUENCY - Set PWM frequency
 * - adc_temp - Read internal temperature sensor
 */
class RP2040ActionManager : public ActionManagerBase {
public:
    RP2040ActionManager();
    virtual ~RP2040ActionManager();

protected:
    // Platform-specific action execution
    bool execute_gpio_action(ActionType type, uint8_t pin) override;
    bool execute_pwm_action(uint8_t pin, uint8_t duty) override;
    bool execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) override;
    bool execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id) override;

    // Platform-specific persistence (stub for now)
    bool save_rules_impl() override;
    uint8_t load_rules_impl() override;

    // Custom command registration
    void register_custom_commands() override;

    // Action definition methods
    const ActionDefinition* get_action_definition(ActionType action) const override;
    const ActionDefinition* const* get_all_action_definitions(uint8_t& count) const override;
};

#endif // PLATFORM_RP2040

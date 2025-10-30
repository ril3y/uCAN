#pragma once

#ifdef PLATFORM_ESP32

#include "../../actions/action_manager_base.h"
#include "../../actions/action_types.h"
#include <Adafruit_NeoPixel.h>

/**
 * ESP32ActionManager
 *
 * ESP32-specific implementation of the action manager.
 * Supports GPIO, PWM (LEDC), ADC, DAC, and optional NeoPixel.
 *
 * Features:
 * - GPIO: Digital I/O on all GPIO pins
 * - PWM: 16 channels via LEDC (LED Control) peripheral
 * - ADC: 18 channels (2x SAR ADCs), 12-bit resolution
 * - DAC: 2 channels (GPIO25, GPIO26), 8-bit resolution
 * - NeoPixel: Optional WS2812 RGB LED (board-dependent)
 * - Flash Storage: Preferences API for non-volatile storage
 */
class ESP32ActionManager : public ActionManagerBase {
public:
    ESP32ActionManager();
    ~ESP32ActionManager() override;

    bool initialize(CANInterface* can_if) override;

protected:
    // Platform-specific action execution
    bool execute_gpio_action(ActionType type, uint8_t pin) override;
    bool execute_pwm_action(uint8_t pin, uint8_t duty) override;
    bool execute_neopixel_action(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) override;
    bool execute_adc_read_send_action(uint8_t adc_pin, uint32_t response_id) override;

    // Persistence
    bool save_rules_impl() override;
    uint8_t load_rules_impl() override;

    // Platform-specific command registration
    void register_custom_commands() override;

    // Action definition queries
    const ActionDefinition* get_action_definition(ActionType action) const override;
    const ActionDefinition* const* get_all_action_definitions(uint8_t& count) const override;

private:
    // NeoPixel support (if board has one)
    Adafruit_NeoPixel* neopixel_;
    bool neopixel_available_;

    // PWM management (LEDC)
    struct PWMChannel {
        uint8_t pin;
        uint8_t channel;    // LEDC channel (0-15)
        bool in_use;
    };
    PWMChannel pwm_channels_[16];  // ESP32 has 16 LEDC channels

    // Helper methods
    void init_neopixel();
    void cleanup_neopixel();
    uint8_t allocate_pwm_channel(uint8_t pin);
    void free_pwm_channel(uint8_t pin);
    bool setup_pwm(uint8_t pin, uint8_t channel);
};

#endif // PLATFORM_ESP32

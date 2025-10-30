#pragma once

#include "../../actions/action_manager_base.h"

#ifdef PLATFORM_SAMD51

// Forward declarations
class BoardInterface;

/**
 * SAMD51ActionManager
 *
 * Platform-specific action manager for SAMD51-based boards (Feather M4 CAN, etc.).
 * Implements SAMD51-specific features:
 * - 12-bit PWM output
 * - 12-bit ADC input (dual 1MSPS ADCs)
 * - 12-bit DAC output (2 channels)
 * - Flash-based rule persistence
 *
 * Custom commands registered:
 * - dac:CHANNEL:VALUE - Set DAC output (0-4095)
 *
 * Note: NeoPixel management is now handled by board-specific implementations
 * (e.g., FeatherM4CANBoard) to keep platform and board concerns separated.
 */
class SAMD51ActionManager : public ActionManagerBase {
public:
    SAMD51ActionManager();
    virtual ~SAMD51ActionManager();

    bool initialize(CANInterface* can_if) override;
    void update_board_periodic() override;

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

    // Action definition methods
    const ActionDefinition* get_action_definition(ActionType action) const override;
    const ActionDefinition* const* get_all_action_definitions(uint8_t& count) const override;

    // Platform reset
    void platform_reset() override;

private:
    // Board-specific implementation (optional)
    BoardInterface* board_impl_;
};

#endif // PLATFORM_SAMD51

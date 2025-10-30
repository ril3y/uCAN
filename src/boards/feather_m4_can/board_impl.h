#pragma once

#ifdef ARDUINO_ADAFRUIT_FEATHER_M4_CAN

#include "../board_interface.h"
#include <Adafruit_NeoPixel.h>

/**
 * FeatherM4CANBoard
 *
 * Board implementation for Adafruit Feather M4 CAN Express
 *
 * Features implemented:
 * - Built-in NeoPixel visual feedback (RGB LED)
 * - Color cycling status indication
 * - Custom NeoPixel command for direct control
 *
 * NeoPixel Pin: GPIO8 with power control on GPIO17
 *
 * All Feather M4 CAN-specific board code lives in this folder.
 * Platform-level features (GPIO, PWM, ADC, DAC, CAN) are provided by SAMD51ActionManager.
 */
class FeatherM4CANBoard : public BoardInterface {
public:
    FeatherM4CANBoard();
    ~FeatherM4CANBoard() override;

    // BoardInterface implementation
    bool initialize(ActionManagerBase* action_manager) override;
    void register_custom_commands(CustomCommandRegistry& registry) override;
    void update_periodic() override;
    const char* get_board_name() const override { return "Adafruit Feather M4 CAN"; }

    // NeoPixel control method (used by SAMD51ActionManager for CAN feedback)
    bool set_neopixel(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness = 0);

private:
    Adafruit_NeoPixel* neopixel_;
    unsigned long last_update_;
    uint8_t color_index_;

    // Predefined colors for status cycling
    static constexpr uint32_t STATUS_COLORS[] = {
        0x001000,  // Dim green
        0x100000,  // Dim red
        0x000010,  // Dim blue
        0x101000,  // Dim yellow
        0x001010,  // Dim cyan
        0x100010,  // Dim magenta
    };
    static constexpr uint8_t NUM_COLORS = sizeof(STATUS_COLORS) / sizeof(STATUS_COLORS[0]);
};

#endif // ARDUINO_ADAFRUIT_FEATHER_M4_CAN

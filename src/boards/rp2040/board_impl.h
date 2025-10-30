#pragma once

#if defined(ARDUINO_RASPBERRY_PI_PICO) || defined(ARDUINO_RASPBERRY_PI_PICO_W)

#include "../board_interface.h"

/**
 * RPiPicoBoard
 *
 * Minimal board implementation for Raspberry Pi Pico
 *
 * Features implemented:
 * - GPIO25 LED blinking (standard Pico LED pin)
 * - Simple periodic update for status indication
 *
 * This is a minimal implementation as the Pico has no special peripherals
 * beyond the external MCP2551 CAN transceiver (handled by platform layer).
 *
 * All RP2040 Pico-specific board code lives in this folder.
 */
class RPiPicoBoard : public BoardInterface {
public:
    RPiPicoBoard();
    ~RPiPicoBoard() override = default;

    // BoardInterface implementation
    bool initialize(ActionManagerBase* action_manager) override;
    void register_custom_commands(CustomCommandRegistry& registry) override;
    void update_periodic() override;
    const char* get_board_name() const override { return "Raspberry Pi Pico"; }

private:
    unsigned long last_blink_;
    bool led_state_;
};

#endif // ARDUINO_RASPBERRY_PI_PICO

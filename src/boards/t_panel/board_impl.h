#pragma once

#ifdef BOARD_T_PANEL

#include "../board_interface.h"

/**
 * TPanelBoard
 *
 * Board implementation for LilyGo T-Panel
 *
 * Features implemented:
 * - 3.95" 480x480 IPS touchscreen display
 * - CST3240 capacitive touch controller
 * - SD card storage
 * - CAN bus via optional RS485/CAN module
 * - XL9535 I2C GPIO expander
 * - ESP32-H2 co-processor control
 *
 * All T-Panel-specific code lives in this folder.
 */
class TPanelBoard : public BoardInterface {
public:
    TPanelBoard();
    ~TPanelBoard() override;

    // BoardInterface implementation
    bool initialize(ActionManagerBase* action_manager) override;
    void register_custom_commands(CustomCommandRegistry& registry) override;
    void update_periodic() override;
    const char* get_board_name() const override;
    const char* get_board_version() const override;

private:
    // Board-specific state
    bool sd_available_;
    bool display_initialized_;

    // Periodic backlight pulse state
    unsigned long last_pulse_;
    uint8_t pulse_direction_;  // 0 = dimming, 1 = brightening
    uint8_t current_brightness_;

    // Helper methods
    bool init_display();
    bool init_touch();
    bool init_sd_card();
    bool init_io_expander();
    void set_backlight(uint8_t brightness);
};

#endif // BOARD_T_PANEL

#pragma once

#ifdef BOARD_T_CAN485

#include "../board_interface.h"
#include <Adafruit_NeoPixel.h>

/**
 * TCAN485Board
 *
 * Board implementation for LilyGo T-CAN485
 *
 * Features implemented:
 * - ME2107 boost converter power management
 * - RS485 transceiver control (MAX13487EESA+)
 * - WS2812 NeoPixel status LED
 * - SD card storage
 * - Custom commands: rs485_send, sd_log
 *
 * All T-CAN485-specific code lives in this folder.
 */
class TCAN485Board : public BoardInterface {
public:
    TCAN485Board();
    ~TCAN485Board() override;

    // BoardInterface implementation
    bool initialize(ActionManagerBase* action_manager) override;
    void register_custom_commands(CustomCommandRegistry& registry) override;
    void update_periodic() override;
    const char* get_board_name() const override;
    const char* get_board_version() const override;

private:
    // Board-specific peripherals
    Adafruit_NeoPixel* neopixel_;
    bool sd_available_;

    // Helper methods
    bool init_power_management();
    bool init_rs485();
    bool init_neopixel();
    bool init_sd_card();
    void set_neopixel_status(uint8_t r, uint8_t g, uint8_t b);
};

#endif // BOARD_T_CAN485

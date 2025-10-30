#ifdef BOARD_T_PANEL

#include "board_impl.h"
#include "board_config.h"
#include "../board_registry.h"
#include "../../actions/action_manager_base.h"
#include <Arduino.h>
#include <SD.h>

// ============================================================================
// T-Panel Custom Commands
// ============================================================================

/**
 * Backlight Control Command
 * Format: backlight:BRIGHTNESS
 * Example: backlight:128
 */
class BacklightCommand : public CustomCommand {
public:
    const char* get_name() const override { return "backlight"; }
    const char* get_description() const override {
        return "Set LCD backlight brightness (0-255)";
    }
    const char* get_category() const override { return "Display"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        static const ParamDef params[] = {
            {"brightness", "Brightness level (0-255)", PARAM_UINT8, 0, 255, nullptr, true}
        };
        count = 1;
        return params;
    }

    bool execute(const char* params) override {
        if (!params) return false;

        int brightness = atoi(params);
        if (brightness < 0 || brightness > 255) {
            Serial.println("ERROR;Brightness must be 0-255");
            return false;
        }

        // Control backlight via PWM on LCD_BL pin
        analogWrite(get_board_config().pins.status_led_pin, brightness);

        Serial.printf("STATUS;INFO;Backlight set to %d\n", brightness);
        return true;
    }
};

/**
 * SD Card Log Command
 * Format: sd_log:MESSAGE
 * Example: sd_log:CAN message received
 */
class SDLogCommand : public CustomCommand {
public:
    const char* get_name() const override { return "sd_log"; }
    const char* get_description() const override {
        return "Append message to SD card log file";
    }
    const char* get_category() const override { return "Storage"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        static const ParamDef params[] = {
            {"message", "Message to log", PARAM_STRING, 0, 0, nullptr, true}
        };
        count = 1;
        return params;
    }

    bool execute(const char* params) override {
        if (!params) return false;

        File logFile = SD.open("/can_log.txt", FILE_APPEND);
        if (!logFile) {
            Serial.println("ERROR;Failed to open SD card log file");
            return false;
        }

        // Write timestamp and message
        logFile.print(millis());
        logFile.print(",");
        logFile.println(params);
        logFile.close();

        Serial.println("STATUS;INFO;Message logged to SD card");
        return true;
    }
};

// ============================================================================
// TPanelBoard Implementation
// ============================================================================

TPanelBoard::TPanelBoard()
    : sd_available_(false)
    , display_initialized_(false) {
}

TPanelBoard::~TPanelBoard() {
    // Turn off backlight
    set_backlight(0);
}

bool TPanelBoard::initialize(ActionManagerBase* action_manager) {
    Serial.println("STATUS;INFO;Initializing LilyGo T-Panel board");

    // Step 1: Display initialization (non-critical for CAN functionality)
    if (!init_display()) {
        Serial.println("WARNING;Display init failed");
    }

    // Step 2: Touch controller (non-critical)
    if (!init_touch()) {
        Serial.println("WARNING;Touch init failed");
    }

    // Step 3: SD card (non-critical)
    if (!init_sd_card()) {
        Serial.println("WARNING;SD card init failed");
    }

    // Step 4: IO expander (non-critical)
    if (!init_io_expander()) {
        Serial.println("WARNING;IO expander init failed");
    }

    // Set backlight to medium brightness = ready
    set_backlight(128);

    Serial.println("STATUS;INFO;T-Panel initialization complete");
    return true;
}

void TPanelBoard::register_custom_commands(CustomCommandRegistry& registry) {
    // Backlight control command
    static BacklightCommand backlight_cmd;
    registry.register_command(&backlight_cmd);

    // SD card logging command (only if SD card is available)
    if (sd_available_) {
        static SDLogCommand sd_log_cmd;
        registry.register_command(&sd_log_cmd);
    }
}

void TPanelBoard::update_periodic() {
    // Optional: Update display with CAN statistics
    // Optional: Handle touch events
}

const char* TPanelBoard::get_board_name() const {
    return "LilyGo T-Panel";
}

const char* TPanelBoard::get_board_version() const {
    return "1.2";
}

// ============================================================================
// Private Helper Methods
// ============================================================================

bool TPanelBoard::init_display() {
    // TODO: Initialize ST7701S display driver
    // This requires a complex initialization sequence
    // For now, just initialize the backlight control

    uint8_t backlight_pin = get_board_config().pins.status_led_pin;
    if (backlight_pin == PIN_NOT_AVAILABLE) {
        return false;
    }

    pinMode(backlight_pin, OUTPUT);
    analogWrite(backlight_pin, 0);  // Start with backlight off

    Serial.println("STATUS;INFO;Display backlight initialized");
    display_initialized_ = true;
    return true;
}

bool TPanelBoard::init_touch() {
    // TODO: Initialize CST3240 touch controller via I2C
    // Touch controller address: 0x5A
    // I2C pins: SDA=17, SCL=18, INT=21

    Serial.println("STATUS;INFO;Touch controller init skipped (not implemented)");
    return false;
}

bool TPanelBoard::init_sd_card() {
    uint8_t sd_cs = get_board_config().pins.sd_cs_pin;

    if (sd_cs == PIN_NOT_AVAILABLE) {
        return false;
    }

    // Try to initialize SD card
    if (!SD.begin(sd_cs)) {
        sd_available_ = false;
        Serial.println("WARNING;SD card mount failed");
        return false;
    }

    sd_available_ = true;

    // Get SD card info
    uint64_t cardSize = SD.cardSize() / (1024 * 1024);
    Serial.printf("STATUS;INFO;SD card initialized: %lluMB\n", cardSize);

    return true;
}

bool TPanelBoard::init_io_expander() {
    // TODO: Initialize XL9535 I2C GPIO expander
    // I2C address: typically 0x20 or 0x21
    // Same I2C bus as touch controller

    Serial.println("STATUS;INFO;IO expander init skipped (not implemented)");
    return false;
}

void TPanelBoard::set_backlight(uint8_t brightness) {
    if (display_initialized_) {
        analogWrite(get_board_config().pins.status_led_pin, brightness);
    }
}

#endif // BOARD_T_PANEL

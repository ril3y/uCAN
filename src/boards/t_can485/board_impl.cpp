#ifdef BOARD_T_CAN485

#include "board_impl.h"
#include "board_config.h"
#include "../board_registry.h"
#include "../../actions/action_manager_base.h"
#include <Arduino.h>
#include <SD.h>

// ============================================================================
// T-CAN485 Custom Commands
// ============================================================================

/**
 * RS485 Send Command
 * Format: rs485_send:MESSAGE
 * Example: rs485_send:Hello World
 */
class RS485SendCommand : public CustomCommand {
public:
    const char* get_name() const override { return "rs485_send"; }
    const char* get_description() const override {
        return "Send message via RS485 bus";
    }
    const char* get_category() const override { return "Communication"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        static const ParamDef params[] = {
            {"message", "Message to send", PARAM_STRING, 0, 0, nullptr, true}
        };
        count = 1;
        return params;
    }

    bool execute(const char* params) override {
        if (!params) return false;

        // Enable RS485 transmit mode
        digitalWrite(get_board_config().pins.rs485_enable_pin, HIGH);
        delayMicroseconds(10);  // Short delay for transceiver switching

        // Send via Serial2 (RS485 UART)
        Serial2.print(params);
        Serial2.flush();

        // Return to receive mode
        digitalWrite(get_board_config().pins.rs485_enable_pin, LOW);

        Serial.println("STATUS;INFO;RS485 message sent");
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
// TCAN485Board Implementation
// ============================================================================

TCAN485Board::TCAN485Board()
    : neopixel_(nullptr)
    , sd_available_(false) {
}

TCAN485Board::~TCAN485Board() {
    if (neopixel_) {
        neopixel_->setPixelColor(0, 0, 0, 0);  // Turn off LED
        neopixel_->show();
        delete neopixel_;
    }
}

bool TCAN485Board::initialize(ActionManagerBase* action_manager) {
    Serial.println("STATUS;INFO;Initializing LilyGo T-CAN485 board");

    // Step 1: Power management (ME2107 boost converter)
    if (!init_power_management()) {
        Serial.println("WARNING;Power management init failed");
    }

    // Step 2: RS485 transceiver
    if (!init_rs485()) {
        Serial.println("ERROR;RS485 init failed");
        return false;
    }

    // Step 3: NeoPixel status LED
    if (!init_neopixel()) {
        Serial.println("WARNING;NeoPixel init failed");
    }

    // Step 4: SD card (non-critical, can fail)
    if (!init_sd_card()) {
        Serial.println("WARNING;SD card init failed");
    }

    // Set NeoPixel to green = ready
    set_neopixel_status(0, 255, 0);

    Serial.println("STATUS;INFO;T-CAN485 initialization complete");
    return true;
}

void TCAN485Board::register_custom_commands(CustomCommandRegistry& registry) {
    // RS485 communication command
    static RS485SendCommand rs485_cmd;
    registry.register_command(&rs485_cmd);

    // SD card logging command (only if SD card is available)
    if (sd_available_) {
        static SDLogCommand sd_log_cmd;
        registry.register_command(&sd_log_cmd);
    }
}

void TCAN485Board::update_periodic() {
    // Optional: Blink NeoPixel based on CAN activity
    // Optional: Check RS485 for incoming messages
}

const char* TCAN485Board::get_board_name() const {
    return "LilyGo T-CAN485";
}

const char* TCAN485Board::get_board_version() const {
    return "1.0";
}

// ============================================================================
// Private Helper Methods
// ============================================================================

bool TCAN485Board::init_power_management() {
    // ME2107 boost converter enable pin
    uint8_t power_pin = get_board_config().pins.power_enable_pin;

    if (power_pin == PIN_NOT_AVAILABLE) {
        return true;  // Board variant without power management
    }

    pinMode(power_pin, OUTPUT);
    digitalWrite(power_pin, HIGH);  // Enable boost converter
    delay(100);  // Wait for power stabilization

    Serial.println("STATUS;INFO;Power management enabled (ME2107)");
    return true;
}

bool TCAN485Board::init_rs485() {
    uint8_t rs485_en = get_board_config().pins.rs485_enable_pin;

    if (rs485_en == PIN_NOT_AVAILABLE) {
        Serial.println("WARNING;RS485 not available on this board variant");
        return false;
    }

    // Configure RS485 enable pin (DE/RE control)
    pinMode(rs485_en, OUTPUT);
    digitalWrite(rs485_en, LOW);  // Start in receive mode

    // Initialize Serial2 for RS485 communication
    Serial2.begin(115200, SERIAL_8N1,
                  get_board_config().pins.rs485_rx_pin,
                  get_board_config().pins.rs485_tx_pin);

    Serial.println("STATUS;INFO;RS485 transceiver initialized");
    return true;
}

bool TCAN485Board::init_neopixel() {
    uint8_t neopixel_pin = get_board_config().pins.neopixel_pin;

    if (neopixel_pin == PIN_NOT_AVAILABLE) {
        return false;
    }

    neopixel_ = new Adafruit_NeoPixel(1, neopixel_pin, NEO_GRB + NEO_KHZ800);
    if (!neopixel_) {
        return false;
    }

    neopixel_->begin();
    neopixel_->setBrightness(50);  // 50% brightness
    neopixel_->setPixelColor(0, 0, 0, 255);  // Blue = initializing
    neopixel_->show();

    Serial.printf("STATUS;INFO;NeoPixel initialized on GPIO%d\n", neopixel_pin);
    return true;
}

bool TCAN485Board::init_sd_card() {
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

void TCAN485Board::set_neopixel_status(uint8_t r, uint8_t g, uint8_t b) {
    if (neopixel_) {
        neopixel_->setPixelColor(0, r, g, b);
        neopixel_->show();
    }
}

#endif // BOARD_T_CAN485

#ifdef ARDUINO_ADAFRUIT_FEATHER_M4_CAN

#include "board_impl.h"
#include "../../actions/custom_command.h"
#include <Arduino.h>

// NeoPixel configuration from feather_m4_can.h board config
#define NEOPIXEL_PIN 8
#define NEOPIXEL_POWER_PIN 17
#define NEOPIXEL_COUNT 1

// Update interval for color cycling (in milliseconds)
#define COLOR_CYCLE_INTERVAL_MS 2000

// ============================================================================
// Custom Command: NeoPixel Control
// ============================================================================

/**
 * NeoPixelCommand
 *
 * Custom command for direct NeoPixel control on Feather M4 CAN.
 * Allows runtime color and brightness adjustment.
 *
 * Format: neopixel:R:G:B[:BRIGHTNESS]
 * Example: neopixel:255:0:0:128 (red at 50% brightness)
 */
class NeoPixelCommand : public CustomCommand {
public:
    NeoPixelCommand(FeatherM4CANBoard* board) : board_(board) {}

    const char* get_name() const override { return "neopixel"; }
    const char* get_description() const override {
        return "Set built-in NeoPixel color and brightness";
    }
    const char* get_category() const override { return "Visual"; }

    const ParamDef* get_parameters(uint8_t& count) const override {
        static const ParamDef params[] = {
            {"red", "Red component (0-255)", PARAM_UINT8, 0, 255, nullptr, true},
            {"green", "Green component (0-255)", PARAM_UINT8, 0, 255, nullptr, true},
            {"blue", "Blue component (0-255)", PARAM_UINT8, 0, 255, nullptr, true},
            {"brightness", "Brightness level (0-255)", PARAM_UINT8, 0, 255, nullptr, false}
        };
        count = 4;
        return params;
    }

    bool execute(const char* params) override {
        if (!board_ || !params) return false;

        // Parse R:G:B[:BRIGHTNESS]
        char buffer[64];
        strncpy(buffer, params, sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\0';

        char* tokens[4];
        uint8_t token_count = 0;
        char* ptr = buffer;

        while (token_count < 4 && ptr && *ptr != '\0') {
            tokens[token_count++] = ptr;
            ptr = strchr(ptr, ':');
            if (ptr) {
                *ptr = '\0';
                ptr++;
            }
        }

        if (token_count < 3) return false;

        uint8_t r = atoi(tokens[0]);
        uint8_t g = atoi(tokens[1]);
        uint8_t b = atoi(tokens[2]);
        uint8_t brightness = (token_count >= 4) ? atoi(tokens[3]) : 0;

        return board_->set_neopixel(r, g, b, brightness);
    }

private:
    FeatherM4CANBoard* board_;
};

// ============================================================================
// FeatherM4CANBoard Implementation
// ============================================================================

constexpr uint32_t FeatherM4CANBoard::STATUS_COLORS[];

FeatherM4CANBoard::FeatherM4CANBoard()
    : neopixel_(nullptr)
    , last_update_(0)
    , color_index_(0)
{
}

FeatherM4CANBoard::~FeatherM4CANBoard() {
    if (neopixel_) {
        neopixel_->clear();
        neopixel_->show();
        delete neopixel_;
        neopixel_ = nullptr;
    }
}

bool FeatherM4CANBoard::initialize(ActionManagerBase* action_manager) {
    // Initialize NeoPixel power control
    pinMode(NEOPIXEL_POWER_PIN, OUTPUT);
    digitalWrite(NEOPIXEL_POWER_PIN, HIGH);  // Enable NeoPixel power
    delay(10);  // Allow power to stabilize

    // Initialize NeoPixel
    neopixel_ = new Adafruit_NeoPixel(NEOPIXEL_COUNT, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);
    if (!neopixel_) {
        return false;
    }

    neopixel_->begin();
    neopixel_->setBrightness(50);  // Default 20% brightness (50/255)
    neopixel_->setPixelColor(0, STATUS_COLORS[0]);  // Start with dim green
    neopixel_->show();

    return true;
}

void FeatherM4CANBoard::register_custom_commands(CustomCommandRegistry& registry) {
    // Register NeoPixel command
    static NeoPixelCommand neopixel_cmd(this);
    registry.register_command(&neopixel_cmd);
}

void FeatherM4CANBoard::update_periodic() {
    if (!neopixel_) return;

    // Cycle through colors to show board is alive
    unsigned long now = millis();

    if (now - last_update_ >= COLOR_CYCLE_INTERVAL_MS) {
        last_update_ = now;
        color_index_ = (color_index_ + 1) % NUM_COLORS;

        neopixel_->setPixelColor(0, STATUS_COLORS[color_index_]);
        neopixel_->show();
    }
}

bool FeatherM4CANBoard::set_neopixel(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
    if (!neopixel_) return false;

    if (brightness > 0 && brightness < 255) {
        neopixel_->setBrightness(brightness);
    }
    neopixel_->setPixelColor(0, neopixel_->Color(r, g, b));
    neopixel_->show();

    return true;
}

#endif // ARDUINO_ADAFRUIT_FEATHER_M4_CAN

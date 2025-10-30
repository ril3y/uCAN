#if defined(ARDUINO_RASPBERRY_PI_PICO) || defined(ARDUINO_RASPBERRY_PI_PICO_W)

#include "board_impl.h"
#include <Arduino.h>

// Standard Pico LED pin
#define PICO_LED_PIN 25

// Blink interval in milliseconds
#define BLINK_INTERVAL_MS 1000

RPiPicoBoard::RPiPicoBoard()
    : last_blink_(0)
    , led_state_(false)
{
}

bool RPiPicoBoard::initialize(ActionManagerBase* action_manager) {
    // Initialize GPIO25 as output for LED
    pinMode(PICO_LED_PIN, OUTPUT);
    digitalWrite(PICO_LED_PIN, LOW);

    return true;
}

void RPiPicoBoard::register_custom_commands(CustomCommandRegistry& registry) {
    // No custom commands needed for standard Pico
    // All functionality is provided by platform layer (GPIO, PWM, ADC, CAN)
}

void RPiPicoBoard::update_periodic() {
    // Blink LED every second to show board is alive
    unsigned long now = millis();

    if (now - last_blink_ >= BLINK_INTERVAL_MS) {
        last_blink_ = now;
        led_state_ = !led_state_;
        digitalWrite(PICO_LED_PIN, led_state_ ? HIGH : LOW);
    }
}

#endif // ARDUINO_RASPBERRY_PI_PICO

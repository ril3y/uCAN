#include "pin_manager.h"

PinManager::PinManager() {
    clear_all();
}

bool PinManager::allocate_pin(uint8_t pin, PinMode mode) {
    // Validate pin number
    if (!is_valid_pin(pin)) {
        LOG_PIN_ERROR(pin, "Invalid pin number (out of range)");
        return false;
    }

    // Check if already allocated
    PinMode current = usage_map_[pin];

    if (current == PINMODE_RESERVED) {
        LOG_PIN_ERROR(pin, "Pin reserved by hardware (CAN, USB, etc)");
        return false;
    }

    if (current != PINMODE_UNUSED && current != mode) {
        // Check if modes are compatible
        if (!are_modes_compatible(current, mode)) {
            Serial.print("[PIN_ERROR] Pin ");
            Serial.print(pin);
            Serial.print(": Already allocated for ");
            Serial.print(mode_to_string(current));
            Serial.print(", cannot use for ");
            Serial.println(mode_to_string(mode));
            return false;
        }
    }

    // Allocate pin
    usage_map_[pin] = mode;

    // Log successful allocation
    LOG_PIN_INFO(pin, mode_to_string(mode));

    return true;
}

void PinManager::free_pin(uint8_t pin) {
    if (!is_valid_pin(pin)) {
        return;
    }

    // Don't free reserved pins
    if (usage_map_[pin] == PINMODE_RESERVED) {
        LOG_PIN_WARNING(pin, "Cannot free hardware-reserved pin");
        return;
    }

    usage_map_[pin] = PINMODE_UNUSED;
}

PinMode PinManager::get_usage(uint8_t pin) const {
    if (!is_valid_pin(pin)) {
        return PINMODE_UNUSED;
    }
    return usage_map_[pin];
}

bool PinManager::is_available(uint8_t pin, PinMode intended_mode) const {
    if (!is_valid_pin(pin)) {
        return false;
    }

    PinMode current = usage_map_[pin];

    // Reserved pins are never available
    if (current == PINMODE_RESERVED) {
        return false;
    }

    // Unused pins are always available
    if (current == PINMODE_UNUSED) {
        return true;
    }

    // Check if same mode or compatible modes
    return (current == intended_mode) || are_modes_compatible(current, intended_mode);
}

bool PinManager::is_allocated(uint8_t pin) const {
    if (!is_valid_pin(pin)) {
        return false;
    }
    return usage_map_[pin] != PINMODE_UNUSED;
}

bool PinManager::are_modes_compatible(PinMode current, PinMode intended) const {
    // Same mode is always compatible
    if (current == intended) {
        return true;
    }

    // GPIO input can become ADC (analog pins are also digital)
    if (current == PINMODE_GPIO_INPUT && intended == PINMODE_ADC) {
        return true;
    }

    // ADC can become GPIO input
    if (current == PINMODE_ADC && intended == PINMODE_GPIO_INPUT) {
        return true;
    }

    // GPIO input can become GPIO output
    if (current == PINMODE_GPIO_INPUT && intended == PINMODE_GPIO_OUTPUT) {
        return true;
    }

    // GPIO output can become GPIO input
    if (current == PINMODE_GPIO_OUTPUT && intended == PINMODE_GPIO_INPUT) {
        return true;
    }

    // Reserved pins are never compatible with anything else
    if (current == PINMODE_RESERVED || intended == PINMODE_RESERVED) {
        return false;
    }

    // All other combinations are incompatible
    return false;
}

void PinManager::clear_all() {
    for (uint8_t i = 0; i < MAX_PINS; i++) {
        usage_map_[i] = PINMODE_UNUSED;
    }
}

void PinManager::log_pin_status() const {
    Serial.println("=== Pin Allocation Status ===");

    uint8_t allocated_count = 0;
    for (uint8_t pin = 0; pin < MAX_PINS; pin++) {
        if (usage_map_[pin] != PINMODE_UNUSED) {
            Serial.print("Pin ");
            Serial.print(pin);
            Serial.print(": ");
            Serial.println(mode_to_string(usage_map_[pin]));
            allocated_count++;
        }
    }

    if (allocated_count == 0) {
        Serial.println("(No pins allocated)");
    } else {
        Serial.print("Total allocated: ");
        Serial.println(allocated_count);
    }

    Serial.println("============================");
}

const char* PinManager::mode_to_string(PinMode mode) {
    switch (mode) {
        case PINMODE_UNUSED:       return "Unused";
        case PINMODE_GPIO_INPUT:   return "GPIO Input";
        case PINMODE_GPIO_OUTPUT:  return "GPIO Output";
        case PINMODE_PWM:          return "PWM";
        case PINMODE_ADC:          return "ADC";
        case PINMODE_DAC:          return "DAC";
        case PINMODE_I2C_SDA:      return "I2C SDA";
        case PINMODE_I2C_SCL:      return "I2C SCL";
        case PINMODE_SPI_MOSI:     return "SPI MOSI";
        case PINMODE_SPI_MISO:     return "SPI MISO";
        case PINMODE_SPI_SCK:      return "SPI SCK";
        case PINMODE_SPI_CS:       return "SPI CS";
        case PINMODE_RESERVED:     return "Reserved (Hardware)";
        default:               return "Unknown";
    }
}

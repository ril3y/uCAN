#include "samd51_i2c.h"
#include "../capabilities/samd51/samd51_pin_caps.h"
#include "../utils/pin_error_logger.h"
#include <string.h>

SAMD51_I2C::SAMD51_I2C()
    : initialized_(false),
      sda_pin_(0),
      scl_pin_(0),
      sercom_instance_(0xFF),
      frequency_hz_(100000) {
    memset(last_error_, 0, sizeof(last_error_));
}

SAMD51_I2C::~SAMD51_I2C() {
    deinitialize();
}

bool SAMD51_I2C::initialize(uint8_t sda_pin, uint8_t scl_pin, uint32_t frequency_hz) {
    // Validate pins
    if (!is_valid_sda_pin(sda_pin)) {
        set_error("Invalid SDA pin");
        LOG_PIN_ERROR(sda_pin, "Pin does not support I2C SDA");
        return false;
    }

    if (!is_valid_scl_pin(scl_pin)) {
        set_error("Invalid SCL pin");
        LOG_PIN_ERROR(scl_pin, "Pin does not support I2C SCL");
        return false;
    }

    // Check if pins are hardware-reserved
    if (samd51_is_pin_reserved(sda_pin) || samd51_is_pin_reserved(scl_pin)) {
        set_error("Pin reserved by hardware");
        return false;
    }

    // Configure SERCOM
    if (!configure_sercom(sda_pin, scl_pin)) {
        set_error("Failed to configure SERCOM for I2C");
        return false;
    }

    // Initialize Wire library
    Wire.begin();
    Wire.setClock(frequency_hz);

    // Store configuration
    sda_pin_ = sda_pin;
    scl_pin_ = scl_pin;
    frequency_hz_ = frequency_hz;
    initialized_ = true;

    LOG_PIN_INFO(sda_pin, "Initialized as I2C SDA");
    LOG_PIN_INFO(scl_pin, "Initialized as I2C SCL");

    return true;
}

bool SAMD51_I2C::write(uint8_t address, uint8_t reg, const uint8_t* data, uint8_t length) {
    if (!initialized_) {
        set_error("I2C not initialized");
        return false;
    }

    if (!data || length == 0) {
        set_error("Invalid data or length");
        return false;
    }

    // Start transmission
    Wire.beginTransmission(address);
    Wire.write(reg);
    Wire.write(data, length);

    // End transmission and check result
    uint8_t result = Wire.endTransmission();

    if (result != 0) {
        snprintf(last_error_, sizeof(last_error_), "I2C write failed (code %d)", result);
        return false;
    }

    return true;
}

bool SAMD51_I2C::write_byte(uint8_t address, uint8_t reg, uint8_t value) {
    return write(address, reg, &value, 1);
}

bool SAMD51_I2C::read(uint8_t address, uint8_t reg, uint8_t* data, uint8_t length) {
    if (!initialized_) {
        set_error("I2C not initialized");
        return false;
    }

    if (!data || length == 0) {
        set_error("Invalid data buffer or length");
        return false;
    }

    // Write register address
    Wire.beginTransmission(address);
    Wire.write(reg);
    uint8_t result = Wire.endTransmission(false);  // Send restart, not stop

    if (result != 0) {
        snprintf(last_error_, sizeof(last_error_), "I2C write reg failed (code %d)", result);
        return false;
    }

    // Read data
    uint8_t bytes_read = Wire.requestFrom(address, length);

    if (bytes_read != length) {
        snprintf(last_error_, sizeof(last_error_), "I2C read failed (got %d, expected %d)", bytes_read, length);
        return false;
    }

    // Copy data from Wire buffer
    for (uint8_t i = 0; i < length; i++) {
        if (Wire.available()) {
            data[i] = Wire.read();
        } else {
            set_error("Wire buffer underrun");
            return false;
        }
    }

    return true;
}

bool SAMD51_I2C::read_byte(uint8_t address, uint8_t reg, uint8_t& value) {
    return read(address, reg, &value, 1);
}

bool SAMD51_I2C::is_valid_sda_pin(uint8_t pin) const {
    const PinCapabilities* caps = samd51_get_pin_capabilities(pin);
    return caps && caps->can_i2c_sda;
}

bool SAMD51_I2C::is_valid_scl_pin(uint8_t pin) const {
    const PinCapabilities* caps = samd51_get_pin_capabilities(pin);
    return caps && caps->can_i2c_scl;
}

const char* SAMD51_I2C::get_last_error() const {
    return last_error_;
}

bool SAMD51_I2C::is_initialized() const {
    return initialized_;
}

void SAMD51_I2C::deinitialize() {
    if (initialized_) {
        Wire.end();
        initialized_ = false;
        LOG_PIN_INFO(sda_pin_, "I2C deinitialized");
    }
}

uint8_t SAMD51_I2C::scan_bus(uint8_t* found_addresses, uint8_t max_addresses) {
    if (!initialized_) {
        set_error("I2C not initialized");
        return 0;
    }

    if (!found_addresses) {
        set_error("Invalid output buffer");
        return 0;
    }

    uint8_t count = 0;

    Serial.println("[I2C] Scanning bus...");

    for (uint8_t addr = 1; addr < 127 && count < max_addresses; addr++) {
        if (probe_address(addr)) {
            found_addresses[count++] = addr;
            Serial.print("[I2C] Found device at 0x");
            Serial.println(addr, HEX);
        }
    }

    Serial.print("[I2C] Scan complete: ");
    Serial.print(count);
    Serial.println(" devices found");

    return count;
}

void SAMD51_I2C::set_error(const char* error) {
    strncpy(last_error_, error, sizeof(last_error_) - 1);
    last_error_[sizeof(last_error_) - 1] = '\0';
}

bool SAMD51_I2C::configure_sercom(uint8_t sda, uint8_t scl) {
    // Get SERCOM info for both pins
    uint8_t sda_sercom, sda_pad;
    uint8_t scl_sercom, scl_pad;

    if (!samd51_get_i2c_sercom(sda, true, sda_sercom, sda_pad)) {
        LOG_PIN_ERROR(sda, "Pin does not have SERCOM for I2C SDA");
        return false;
    }

    if (!samd51_get_i2c_sercom(scl, false, scl_sercom, scl_pad)) {
        LOG_PIN_ERROR(scl, "Pin does not have SERCOM for I2C SCL");
        return false;
    }

    // Verify pins are on same SERCOM
    if (sda_sercom != scl_sercom) {
        Serial.print("[PIN_ERROR] SDA pin ");
        Serial.print(sda);
        Serial.print(" and SCL pin ");
        Serial.print(scl);
        Serial.println(" are not on same SERCOM");
        return false;
    }

    sercom_instance_ = sda_sercom;

    // Note: Current implementation uses default Wire (SERCOM2)
    // Future enhancement: Support Wire1, Wire2 for other SERCOM instances
    if (sercom_instance_ != 2) {
        Serial.print("[PIN_WARNING] Requested SERCOM");
        Serial.print(sercom_instance_);
        Serial.println(" but using default Wire (SERCOM2)");
    }

    return true;
}

bool SAMD51_I2C::probe_address(uint8_t address) {
    Wire.beginTransmission(address);
    return (Wire.endTransmission() == 0);
}

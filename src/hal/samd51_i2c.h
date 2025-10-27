#pragma once

#include "i2c_interface.h"
#include <Wire.h>

/**
 * SAMD51_I2C
 *
 * SAMD51-specific I2C implementation using Arduino Wire library.
 * Supports multiple SERCOM instances for flexible pin mapping.
 *
 * Features:
 * - Configurable SDA/SCL pins via SERCOM
 * - Pin validation using samd51_pin_caps
 * - Default to SERCOM2 (PA12/PA13) if no pins specified
 * - Error reporting for invalid pins or failed operations
 *
 * Limitations:
 * - Currently uses default Wire instance (SERCOM2)
 * - Future: Support Wire1, Wire2 for alternate SERCOM
 * - I2C and SPI share SERCOM2 pins - choose one or reconfigure
 */
class SAMD51_I2C : public I2CInterface {
public:
    SAMD51_I2C();
    ~SAMD51_I2C() override;

    bool initialize(uint8_t sda_pin, uint8_t scl_pin, uint32_t frequency_hz = 100000) override;
    bool write(uint8_t address, uint8_t reg, const uint8_t* data, uint8_t length) override;
    bool write_byte(uint8_t address, uint8_t reg, uint8_t value) override;
    bool read(uint8_t address, uint8_t reg, uint8_t* data, uint8_t length) override;
    bool read_byte(uint8_t address, uint8_t reg, uint8_t& value) override;
    bool is_valid_sda_pin(uint8_t pin) const override;
    bool is_valid_scl_pin(uint8_t pin) const override;
    const char* get_last_error() const override;
    bool is_initialized() const override;
    void deinitialize() override;
    uint8_t scan_bus(uint8_t* found_addresses, uint8_t max_addresses) override;

private:
    bool initialized_;
    uint8_t sda_pin_;
    uint8_t scl_pin_;
    uint8_t sercom_instance_;
    uint32_t frequency_hz_;
    char last_error_[64];

    /**
     * Set error message
     */
    void set_error(const char* error);

    /**
     * Validate and configure SERCOM for I2C pins
     *
     * @param sda SDA pin number
     * @param scl SCL pin number
     * @return true if valid SERCOM configuration found
     */
    bool configure_sercom(uint8_t sda, uint8_t scl);

    /**
     * Check if I2C device responds at address
     *
     * @param address 7-bit I2C address
     * @return true if device ACKs
     */
    bool probe_address(uint8_t address);
};

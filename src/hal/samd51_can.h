#pragma once

#ifdef PLATFORM_SAMD51

#include "can_interface.h"
#include <Arduino.h>
#include <CAN.h>
#include <queue>
#include <Adafruit_NeoPixel.h>

/**
 * SAMD51-specific CAN implementation for Adafruit Feather M4 CAN
 * 
 * Uses the built-in CAN peripheral with the Adafruit CAN library
 */
class SAMD51CAN : public CANInterface {
public:
    SAMD51CAN();
    virtual ~SAMD51CAN();

    // CANInterface implementation
    bool initialize(const CANConfig& config) override;
    void deinitialize() override;
    bool is_ready() override;
    bool send_message(const CANMessage& message) override;
    bool receive_message(CANMessage& message) override;
    uint16_t available() override;
    CANError get_error_status() override;
    bool clear_errors() override;
    void get_statistics(CANStatistics& stats) override;
    void reset_statistics() override;
    bool set_filter(uint32_t filter_id, uint32_t mask) override;
    const char* get_platform_name() override;
    const char* get_version() override;
    bool set_loopback_mode(bool enabled) override;

    // Visual feedback implementation
    void indicate_tx_activity() override;
    void indicate_rx_activity() override;
    void indicate_error(CANError error) override;
    void set_visual_feedback_enabled(bool enabled) override;
    bool is_visual_feedback_enabled() override;

protected:
    uint32_t get_timestamp_ms() override;

private:
    std::queue<CANMessage> rx_queue_;
    
    bool initialized_;
    bool error_state_;
    
    uint32_t acceptance_filter_;
    uint32_t acceptance_mask_;
    
    // Visual feedback (NeoPixel) support
    Adafruit_NeoPixel* neopixel_;
    bool visual_feedback_enabled_;
    uint8_t neopixel_brightness_;
    uint32_t last_activity_time_;
    uint32_t neopixel_clear_time_;  // When to clear the NeoPixel
    
    // Pin definitions for Feather M4 CAN
    static const uint8_t NEOPIXEL_PIN = 8;
    static const uint8_t NEOPIXEL_POWER_PIN = 2; // Based on Adafruit documentation
    
    // Static callback function for CAN library
    static void can_rx_callback(int packet_size);
    
    // Message filtering
    bool passes_filter(uint32_t can_id);
    
    // Error handling
    void handle_error();
    
    // Instance reference for static callback
    static SAMD51CAN* instance_;
    
    // Convert CAN library packet to our format
    bool read_can_packet(CANMessage& message);
    
    // NeoPixel control methods
    void init_neopixel();
    void deinit_neopixel();
    void set_neopixel_color(uint32_t color, uint16_t duration_ms = 150);
    void clear_neopixel();
    void update_neopixel();  // Check if NeoPixel should be cleared
    void neopixel_power_on();
    void neopixel_power_off();
};

#endif // PLATFORM_SAMD51
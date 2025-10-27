#pragma once

#ifdef PLATFORM_RP2040

#include "can_interface.h"
#include <Arduino.h>
#include <ACAN2040.h>
#include <queue>

/**
 * RP2040-specific CAN implementation using ACAN2040 library
 * 
 * This uses the ACAN2040 wrapper around can2040 for easier integration
 */
class RP2040CAN : public CANInterface {
public:
    RP2040CAN();
    virtual ~RP2040CAN();

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

protected:
    uint32_t get_timestamp_ms() override;

private:
    ACAN2040* acan_instance_;
    std::queue<CANMessage> rx_queue_;
    
    bool initialized_;
    bool error_state_;
    
    uint32_t acceptance_filter_;
    uint32_t acceptance_mask_;
    
    // Static callback function for ACAN2040
    static void acan_rx_callback(struct can2040 *cd, uint32_t notify, struct can2040_msg *msg);
    
    // Convert between our message format and ACAN2040 format
    void convert_to_acan(const CANMessage& src, struct can2040_msg& dst);
    void convert_from_acan(const struct can2040_msg& src, CANMessage& dst);
    
    // Message filtering
    bool passes_filter(uint32_t can_id);
    
    // Error handling
    void handle_error(uint32_t notify);
    
    // Instance reference for static callback
    static RP2040CAN* instance_;
};

#endif // PLATFORM_RP2040
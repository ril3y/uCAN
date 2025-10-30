#pragma once

#ifdef PLATFORM_ESP32

#include "can_interface.h"
#include "driver/twai.h"
#include <queue>

/**
 * ESP32 CAN Interface Implementation
 *
 * Uses the ESP32 TWAI (Two-Wire Automotive Interface) hardware peripheral.
 * TWAI is ESP32's implementation of the CAN bus protocol.
 *
 * Features:
 * - Hardware CAN controller with built-in protocol handling
 * - Supports standard (11-bit) and extended (29-bit) identifiers
 * - Configurable bitrates from 25kbps to 1Mbps
 * - Hardware acceptance filters
 * - Error detection and recovery
 * - Alert system for TX/RX events
 *
 * Pin Configuration:
 * - TX/RX pins configurable at initialization
 * - Requires external CAN transceiver (SN65HVD231, MCP2551, etc.)
 *
 * Usage:
 *   ESP32CAN can;
 *   CANConfig config = { .bitrate = 500000 };
 *   can.initialize(config);
 *   can.send_message(message);
 */
class ESP32CAN : public CANInterface {
public:
    ESP32CAN();
    ~ESP32CAN() override;

    // Initialization
    bool initialize(const CANConfig& config) override;
    bool deinitialize() override;

    // Message transmission and reception
    bool send_message(const CANMessage& message) override;
    bool receive_message(CANMessage& message) override;
    uint16_t available() override;

    // Configuration
    bool set_bitrate(uint32_t bitrate) override;
    bool set_mode(CANMode mode) override;
    bool set_filter(uint32_t id, uint32_t mask, bool extended) override;
    bool clear_filters() override;

    // Status and errors
    CANError get_error_status() override;
    CANBusState get_bus_state() override;
    bool is_bus_off() override;
    void reset_error_counts() override;

    // Statistics
    CANStatistics get_statistics() override;
    void reset_statistics() override;

    // Control
    bool enable_loopback(bool enable) override;
    bool enable_listen_only(bool enable) override;
    bool enable_one_shot(bool enable) override;

    // Visual feedback (if NeoPixel or LED available)
    void set_visual_feedback_enabled(bool enabled) override;

private:
    // ESP32 TWAI specific
    bool twai_initialized_;
    twai_general_config_t general_config_;
    twai_timing_config_t timing_config_;
    twai_filter_config_t filter_config_;

    // Message queue for received messages
    std::queue<CANMessage> rx_queue_;

    // Statistics tracking
    CANStatistics stats_;

    // Error tracking
    CANError last_error_;

    // Configuration
    uint32_t current_bitrate_;
    bool loopback_enabled_;
    bool listen_only_enabled_;
    bool visual_feedback_enabled_;

    // Helper methods
    bool configure_bitrate(uint32_t bitrate);
    void convert_to_twai_message(const CANMessage& msg, twai_message_t& twai_msg);
    void convert_from_twai_message(const twai_message_t& twai_msg, CANMessage& msg);
    void handle_twai_alerts();
    void update_error_status();
    CANError map_esp_error(esp_err_t err);

    // Visual feedback
    void indicate_tx();
    void indicate_rx();
    void indicate_error();
};

#endif // PLATFORM_ESP32

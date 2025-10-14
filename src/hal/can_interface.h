#pragma once

#include <stdint.h>
#include <stdbool.h>

// Maximum CAN data length
#define CAN_MAX_DATA_LENGTH 8

// CAN message structure
struct CANMessage {
    uint32_t id;                           // CAN ID (11-bit or 29-bit)
    uint8_t data[CAN_MAX_DATA_LENGTH];     // Data bytes
    uint8_t length;                        // Data length (0-8)
    bool extended;                         // Extended frame (29-bit ID)
    bool remote;                           // Remote transmission request
    uint32_t timestamp;                    // Timestamp (milliseconds)
};

// CAN error codes
enum CANError {
    CAN_ERROR_NONE = 0x00,
    CAN_ERROR_BUS_OFF = 0x01,
    CAN_ERROR_PASSIVE = 0x02,
    CAN_ERROR_WARNING = 0x03,
    CAN_ERROR_ARBITRATION_LOST = 0x04,
    CAN_ERROR_BIT_ERROR = 0x05,
    CAN_ERROR_CRC_ERROR = 0x06,
    CAN_ERROR_FORM_ERROR = 0x07,
    CAN_ERROR_STUFF_ERROR = 0x08,
    CAN_ERROR_OTHER = 0x09,
    CAN_ERROR_BUFFER_OVERFLOW = 0x10,
    CAN_ERROR_CONFIG_ERROR = 0x11
};

// CAN statistics
struct CANStatistics {
    uint32_t rx_count;
    uint32_t tx_count;
    uint32_t error_count;
    uint8_t bus_load_percent;  // 0-100
    uint32_t uptime_ms;
};

// CAN configuration
struct CANConfig {
    uint32_t bitrate;          // CAN bitrate (e.g., 500000 for 500kbps)
    bool loopback_mode;        // Enable loopback for testing
    bool listen_only_mode;     // Listen-only mode (no ACK)
    uint32_t acceptance_filter; // Acceptance filter (0 = accept all)
    uint32_t acceptance_mask;   // Acceptance mask
    bool enable_timestamps;     // Enable hardware timestamps
};

/**
 * Abstract CAN Hardware Abstraction Layer
 * 
 * This interface provides a common API for CAN operations across
 * different hardware platforms (RP2040, SAMD51, ESP32, etc.)
 */
class CANInterface {
public:
    virtual ~CANInterface() = default;

    /**
     * Initialize the CAN interface
     * @param config CAN configuration parameters
     * @return true if initialization successful
     */
    virtual bool initialize(const CANConfig& config) = 0;

    /**
     * Deinitialize the CAN interface
     */
    virtual void deinitialize() = 0;

    /**
     * Check if CAN interface is ready for operation
     * @return true if ready
     */
    virtual bool is_ready() = 0;

    /**
     * Send a CAN message
     * @param message Message to send
     * @return true if message queued successfully
     */
    virtual bool send_message(const CANMessage& message) = 0;

    /**
     * Receive a CAN message (non-blocking)
     * @param message Buffer to store received message
     * @return true if message received
     */
    virtual bool receive_message(CANMessage& message) = 0;

    /**
     * Check if messages are available in receive buffer
     * @return number of messages available
     */
    virtual uint16_t available() = 0;

    /**
     * Get current error status
     * @return Current error code
     */
    virtual CANError get_error_status() = 0;

    /**
     * Clear error status and reset interface if needed
     * @return true if reset successful
     */
    virtual bool clear_errors() = 0;

    /**
     * Get current statistics
     * @param stats Buffer to store statistics
     */
    virtual void get_statistics(CANStatistics& stats) = 0;

    /**
     * Reset statistics counters
     */
    virtual void reset_statistics() = 0;

    /**
     * Set acceptance filter
     * @param filter_id Filter ID
     * @param mask Filter mask
     * @return true if filter set successfully
     */
    virtual bool set_filter(uint32_t filter_id, uint32_t mask) = 0;

    /**
     * Get hardware-specific information
     * @return Platform identifier string
     */
    virtual const char* get_platform_name() = 0;

    /**
     * Get firmware version
     * @return Version string
     */
    virtual const char* get_version() = 0;

    /**
     * Visual feedback for TX activity (optional, platform-specific)
     * Default implementation does nothing for platforms without visual indicators
     */
    virtual void indicate_tx_activity() {}

    /**
     * Visual feedback for RX activity (optional, platform-specific) 
     * Default implementation does nothing for platforms without visual indicators
     */
    virtual void indicate_rx_activity() {}

    /**
     * Visual feedback for CAN errors (optional, platform-specific)
     * @param error The specific CAN error that occurred
     * Default implementation does nothing for platforms without visual indicators
     */
    virtual void indicate_error(CANError error) {}

    /**
     * Enable or disable visual feedback (optional, platform-specific)
     * @param enabled true to enable visual feedback, false to disable
     * Default implementation does nothing for platforms without visual indicators
     */
    virtual void set_visual_feedback_enabled(bool enabled) {}

    /**
     * Get visual feedback enabled status (optional, platform-specific)
     * @return true if visual feedback is enabled, false otherwise
     * Default implementation returns false for platforms without visual indicators
     */
    virtual bool is_visual_feedback_enabled() { return false; }

protected:
    CANConfig config_;
    CANStatistics stats_;
    CANError last_error_;
    uint32_t init_time_ms_;

    /**
     * Update statistics counters
     */
    void update_rx_stats() {
        stats_.rx_count++;
        indicate_rx_activity();
    }

    void update_tx_stats() {
        stats_.tx_count++;
        indicate_tx_activity();
    }

    void update_error_stats(CANError error) {
        stats_.error_count++;
        last_error_ = error;
        indicate_error(error);
    }

    /**
     * Get current timestamp in milliseconds
     */
    virtual uint32_t get_timestamp_ms() = 0;
};
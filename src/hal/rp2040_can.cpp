#ifdef PLATFORM_RP2040

#include "rp2040_can.h"
#include "platform_config.h"

// Static instance pointer for callback
RP2040CAN* RP2040CAN::instance_ = nullptr;

RP2040CAN::RP2040CAN() 
    : acan_instance_(nullptr)
    , initialized_(false)
    , error_state_(false)
    , acceptance_filter_(0)
    , acceptance_mask_(0)
{
    instance_ = this;
    memset(&stats_, 0, sizeof(stats_));
    last_error_ = CAN_ERROR_NONE;
}

RP2040CAN::~RP2040CAN() {
    deinitialize();
    instance_ = nullptr;
}

bool RP2040CAN::initialize(const CANConfig& config) {
    if (initialized_) {
        return true;
    }

    config_ = config;
    init_time_ms_ = millis();

    // Create ACAN2040 instance
    acan_instance_ = new ACAN2040(0, CAN_TX_PIN, CAN_RX_PIN, config.bitrate, F_CPU, acan_rx_callback);

    if (!acan_instance_) {
        last_error_ = CAN_ERROR_CONFIG_ERROR;
        return false;
    }

    // Initialize ACAN2040 (void return type - sets up PIO, IRQ, and starts can2040)
    acan_instance_->begin();

    // Set up acceptance filter
    acceptance_filter_ = config.acceptance_filter;
    acceptance_mask_ = config.acceptance_mask;

    initialized_ = true;
    error_state_ = false;
    last_error_ = CAN_ERROR_NONE;

    return true;
}

void RP2040CAN::deinitialize() {
    if (!initialized_) {
        return;
    }

    if (acan_instance_) {
        // ACAN2040 doesn't have an explicit end() method
        delete acan_instance_;
        acan_instance_ = nullptr;
    }
    
    // Clear queues
    while (!rx_queue_.empty()) {
        rx_queue_.pop();
    }

    initialized_ = false;
}

bool RP2040CAN::is_ready() {
    // Don't block on error_state - allow continuous transmission attempts
    // The error_state flag is purely informational for status reporting
    return initialized_ && acan_instance_;
}

bool RP2040CAN::send_message(const CANMessage& message) {
    if (!initialized_ || !acan_instance_) {
        return false;
    }

    // Don't block on error_state_ - allow recovery attempts
    // The error_state_ flag is informational only

    struct can2040_msg can_msg;
    convert_to_acan(message, can_msg);

    // Check if CAN controller is ready to send
    // Respect this check to avoid flooding the TX queue
    if (!acan_instance_->ok_to_send()) {
        // TX queue full or not synchronized - drop this message silently
        // Don't count as error since this is expected during normal operation
        return false;
    }

    // Attempt transmission
    if (acan_instance_->send_message(&can_msg)) {
        update_tx_stats();
        error_state_ = false;  // Clear error state on successful TX
        return true;
    } else {
        // Failed even though ok_to_send said we were ready - this is an error
        update_error_stats(CAN_ERROR_OTHER);
        error_state_ = true;
        return false;
    }
}

bool RP2040CAN::receive_message(CANMessage& message) {
    if (rx_queue_.empty()) {
        return false;
    }

    message = rx_queue_.front();
    rx_queue_.pop();
    return true;
}

uint16_t RP2040CAN::available() {
    return rx_queue_.size();
}

CANError RP2040CAN::get_error_status() {
    return last_error_;
}

bool RP2040CAN::clear_errors() {
    error_state_ = false;
    last_error_ = CAN_ERROR_NONE;
    return true;
}

void RP2040CAN::get_statistics(CANStatistics& stats) {
    stats = stats_;
    stats.uptime_ms = millis() - init_time_ms_;
    
    // Calculate bus load (simplified estimate)
    uint32_t total_messages = stats_.rx_count + stats_.tx_count;
    if (stats.uptime_ms > 0) {
        // Rough estimate: assume average 64-bit frames at current bitrate
        uint32_t theoretical_max = (config_.bitrate / 64) * (stats.uptime_ms / 1000);
        if (theoretical_max > 0) {
            stats.bus_load_percent = min(100, (total_messages * 100) / theoretical_max);
        }
    }
}

void RP2040CAN::reset_statistics() {
    memset(&stats_, 0, sizeof(stats_));
    init_time_ms_ = millis();
}

bool RP2040CAN::set_filter(uint32_t filter_id, uint32_t mask) {
    acceptance_filter_ = filter_id;
    acceptance_mask_ = mask;
    return true;
}

const char* RP2040CAN::get_platform_name() {
    return PLATFORM_NAME;
}

const char* RP2040CAN::get_version() {
    return FIRMWARE_VERSION " (ACAN2040)";
}

uint32_t RP2040CAN::get_timestamp_ms() {
    return millis();
}

void RP2040CAN::acan_rx_callback(struct can2040 *cd, uint32_t notify, struct can2040_msg *msg) {
    if (!instance_) {
        return;
    }

    if (notify == CAN2040_NOTIFY_RX) {
        CANMessage can_message;
        instance_->convert_from_acan(*msg, can_message);

        // Apply filtering
        if (instance_->passes_filter(can_message.id)) {
            // Add to receive queue if there's space
            if (instance_->rx_queue_.size() < CAN_RX_BUFFER_SIZE) {
                instance_->rx_queue_.push(can_message);
                instance_->update_rx_stats();
            } else {
                instance_->update_error_stats(CAN_ERROR_BUFFER_OVERFLOW);
            }
        }
    } else {
        instance_->handle_error(notify);
    }
}

void RP2040CAN::convert_to_acan(const CANMessage& src, struct can2040_msg& dst) {
    // can2040 uses bit flags in the ID field for extended/RTR frames
    dst.id = src.id & 0x1FFFFFFF;  // Mask to 29 bits (CAN ID portion)

    // Set extended frame flag (bit 31) if needed
    if (src.extended) {
        dst.id |= CAN2040_ID_EFF;  // 0x80000000
    }

    // Set RTR flag (bit 30) if needed
    if (src.remote) {
        dst.id |= CAN2040_ID_RTR;  // 0x40000000
    }

    dst.dlc = src.length;

    // Copy data
    memcpy(dst.data, src.data, min(src.length, (uint8_t)8));
}

void RP2040CAN::convert_from_acan(const struct can2040_msg& src, CANMessage& dst) {
    // Extract CAN ID (bits 0-28) and flags from can2040 format
    dst.id = src.id & 0x1FFFFFFF;  // Mask to 29 bits
    dst.extended = (src.id & CAN2040_ID_EFF) != 0;  // Check bit 31
    dst.remote = (src.id & CAN2040_ID_RTR) != 0;    // Check bit 30
    dst.length = src.dlc;
    dst.timestamp = get_timestamp_ms();

    // Copy data
    memcpy(dst.data, src.data, min(src.dlc, (uint8_t)8));
}

bool RP2040CAN::passes_filter(uint32_t can_id) {
    // If no filter set, accept all messages
    if (acceptance_mask_ == 0) {
        return true;
    }
    
    // Apply acceptance filter
    return (can_id & acceptance_mask_) == (acceptance_filter_ & acceptance_mask_);
}

void RP2040CAN::handle_error(uint32_t notify) {
    switch (notify) {
        case CAN2040_NOTIFY_ERROR:
            error_state_ = true;
            update_error_stats(CAN_ERROR_OTHER);
            break;
        case CAN2040_NOTIFY_TX:
            // TX notification - this is NOT an error, it's a success confirmation
            break;
        default:
            error_state_ = true;
            update_error_stats(CAN_ERROR_OTHER);
            break;
    }
}

bool RP2040CAN::set_loopback_mode(bool enabled) {
    if (!initialized_ || !acan_instance_) {
        return false;
    }

    // TODO: Investigate if ACAN2040/can2040 supports loopback mode
    // The can2040 library may support loopback via configuration
    // but ACAN2040 wrapper might not expose this functionality

    // For now, return false to indicate this feature is not yet implemented
    // This prevents compilation errors and allows the rest of the system to work

    // Note: When implementing, loopback mode would typically be set during
    // initialization via can2040 configuration, not dynamically changed

    config_.loopback_mode = enabled;  // Update config even if not supported
    return false;  // Feature not yet implemented
}

#endif // PLATFORM_RP2040
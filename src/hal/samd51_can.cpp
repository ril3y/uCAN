#ifdef PLATFORM_SAMD51

#include "samd51_can.h"
#include "platform_config.h"

// Static instance pointer for callback
SAMD51CAN* SAMD51CAN::instance_ = nullptr;

SAMD51CAN::SAMD51CAN() 
    : initialized_(false)
    , error_state_(false)
    , acceptance_filter_(0)
    , acceptance_mask_(0)
    , neopixel_(nullptr)
    , visual_feedback_enabled_(true)
    , neopixel_brightness_(64)  // 25% brightness default
    , last_activity_time_(0)
    , neopixel_clear_time_(0)
{
    instance_ = this;
    memset(&stats_, 0, sizeof(stats_));
    last_error_ = CAN_ERROR_NONE;
}

SAMD51CAN::~SAMD51CAN() {
    deinitialize();
    deinit_neopixel();
    instance_ = nullptr;
}

bool SAMD51CAN::initialize(const CANConfig& config) {
    if (initialized_) {
        return true;
    }

    config_ = config;
    init_time_ms_ = millis();
    
    // Initialize CAN library
    if (!CAN.begin(config.bitrate)) {
        last_error_ = CAN_ERROR_CONFIG_ERROR;
        return false;
    }

    // Set up receive callback
    CAN.onReceive(can_rx_callback);

    // Configure loopback mode if requested
    if (config.loopback_mode) {
        // Note: Check if Adafruit CAN library supports loopback
        // This may need platform-specific implementation
    }

    // Set up acceptance filter
    acceptance_filter_ = config.acceptance_filter;
    acceptance_mask_ = config.acceptance_mask;

    // NOTE: NeoPixel visual feedback is now handled by ActionManager
    // HAL no longer initializes or controls NeoPixel
    // init_neopixel();  // DISABLED - ActionManager handles this

    initialized_ = true;
    error_state_ = false;
    last_error_ = CAN_ERROR_NONE;

    return true;
}

void SAMD51CAN::deinitialize() {
    if (!initialized_) {
        return;
    }

    CAN.end();
    
    // Deinitialize NeoPixel
    deinit_neopixel();
    
    // Clear receive queue
    while (!rx_queue_.empty()) {
        rx_queue_.pop();
    }

    initialized_ = false;
}

bool SAMD51CAN::is_ready() {
    // Update NeoPixel timing on frequent calls
    update_neopixel();
    
    return initialized_ && !error_state_;
}

bool SAMD51CAN::send_message(const CANMessage& message) {
    if (!is_ready()) {
        return false;
    }

    // Begin packet with appropriate ID type
    int result;
    if (message.extended) {
        result = CAN.beginExtendedPacket(message.id);
    } else {
        result = CAN.beginPacket(message.id);
    }

    if (!result) {
        update_error_stats(CAN_ERROR_OTHER);
        return false;
    }

    // Write data
    for (uint8_t i = 0; i < message.length; i++) {
        CAN.write(message.data[i]);
    }

    // End packet (send)
    result = CAN.endPacket();
    
    if (result) {
        update_tx_stats();
        return true;
    } else {
        update_error_stats(CAN_ERROR_OTHER);
        return false;
    }
}

bool SAMD51CAN::receive_message(CANMessage& message) {
    if (rx_queue_.empty()) {
        return false;
    }

    message = rx_queue_.front();
    rx_queue_.pop();
    return true;
}

uint16_t SAMD51CAN::available() {
    return rx_queue_.size();
}

CANError SAMD51CAN::get_error_status() {
    return last_error_;
}

bool SAMD51CAN::clear_errors() {
    error_state_ = false;
    last_error_ = CAN_ERROR_NONE;
    return true;
}

void SAMD51CAN::get_statistics(CANStatistics& stats) {
    // Update NeoPixel timing (clear if needed)
    update_neopixel();
    
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

void SAMD51CAN::reset_statistics() {
    memset(&stats_, 0, sizeof(stats_));
    init_time_ms_ = millis();
}

bool SAMD51CAN::set_filter(uint32_t filter_id, uint32_t mask) {
    acceptance_filter_ = filter_id;
    acceptance_mask_ = mask;
    
    // Note: The Adafruit CAN library may support hardware filtering
    // This would need to be implemented based on the library's capabilities
    return true;
}

const char* SAMD51CAN::get_platform_name() {
    return PLATFORM_NAME;
}

const char* SAMD51CAN::get_version() {
    return FIRMWARE_VERSION " (SAMD51)";
}

uint32_t SAMD51CAN::get_timestamp_ms() {
    return millis();
}

void SAMD51CAN::can_rx_callback(int packet_size) {
    if (!instance_ || !instance_->is_ready()) {
        return;
    }

    CANMessage message;
    if (instance_->read_can_packet(message)) {
        // Apply filtering
        if (instance_->passes_filter(message.id)) {
            // Add to receive queue if there's space
            if (instance_->rx_queue_.size() < CAN_RX_BUFFER_SIZE) {
                instance_->rx_queue_.push(message);
                instance_->update_rx_stats();
            } else {
                instance_->update_error_stats(CAN_ERROR_BUFFER_OVERFLOW);
            }
        }
    } else {
        instance_->handle_error();
    }
}

bool SAMD51CAN::read_can_packet(CANMessage& message) {
    // Get packet information
    message.id = CAN.packetId();
    message.extended = CAN.packetExtended();
    message.remote = CAN.packetRtr();
    message.length = 0;
    message.timestamp = get_timestamp_ms();

    // Read data bytes
    while (CAN.available() && message.length < CAN_MAX_DATA_LENGTH) {
        message.data[message.length] = CAN.read();
        message.length++;
    }

    return true;
}

bool SAMD51CAN::passes_filter(uint32_t can_id) {
    // If no filter set, accept all messages
    if (acceptance_mask_ == 0) {
        return true;
    }
    
    // Apply acceptance filter
    return (can_id & acceptance_mask_) == (acceptance_filter_ & acceptance_mask_);
}

void SAMD51CAN::handle_error() {
    error_state_ = true;
    update_error_stats(CAN_ERROR_OTHER);
}

// ============================================================================
// Visual Feedback Implementation (NeoPixel)
// ============================================================================

void SAMD51CAN::indicate_tx_activity() {
    if (visual_feedback_enabled_ && neopixel_) {
        set_neopixel_color(0x00FF00, 50);  // Green flash for TX - 50ms
        last_activity_time_ = millis();
    }
}

void SAMD51CAN::indicate_rx_activity() {
    if (visual_feedback_enabled_ && neopixel_) {
        set_neopixel_color(0xFFFF00, 30);  // Yellow flash for RX - 30ms (very brief)
        last_activity_time_ = millis();
    }
}

void SAMD51CAN::indicate_error(CANError error) {
    if (visual_feedback_enabled_ && neopixel_) {
        set_neopixel_color(0xFF0000, 500);  // Red flash for errors (longer)
        last_activity_time_ = millis();
    }
}

void SAMD51CAN::set_visual_feedback_enabled(bool enabled) {
    visual_feedback_enabled_ = enabled;
    
    if (enabled) {
        init_neopixel();
        // Brief white flash to indicate visual feedback is enabled
        if (neopixel_) {
            set_neopixel_color(0x404040, 200);  // Dim white
        }
    } else {
        clear_neopixel();
        deinit_neopixel();
    }
}

bool SAMD51CAN::is_visual_feedback_enabled() {
    return visual_feedback_enabled_;
}

// ============================================================================
// NeoPixel Control Methods
// ============================================================================

void SAMD51CAN::init_neopixel() {
    if (neopixel_) {
        return;  // Already initialized
    }
    
    // Set up NeoPixel power control pin
    pinMode(NEOPIXEL_POWER_PIN, OUTPUT);
    neopixel_power_on();
    
    // Small delay for power stabilization
    delay(10);
    
    // Initialize NeoPixel (1 pixel, GRB format)
    neopixel_ = new Adafruit_NeoPixel(1, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);
    neopixel_->begin();
    neopixel_->setBrightness(neopixel_brightness_);
    neopixel_->clear();
    neopixel_->show();
}

void SAMD51CAN::deinit_neopixel() {
    if (neopixel_) {
        clear_neopixel();
        delete neopixel_;
        neopixel_ = nullptr;
    }
    
    // Turn off NeoPixel power to save current
    neopixel_power_off();
}

void SAMD51CAN::set_neopixel_color(uint32_t color, uint16_t duration_ms) {
    if (!neopixel_) {
        return;
    }
    
    // Set color and show
    neopixel_->setPixelColor(0, color);
    neopixel_->show();
    
    // Schedule clearing after duration
    neopixel_clear_time_ = millis() + duration_ms;
}

void SAMD51CAN::clear_neopixel() {
    if (neopixel_) {
        neopixel_->clear();
        neopixel_->show();
    }
    neopixel_clear_time_ = 0;  // Cancel any pending clear
}

void SAMD51CAN::update_neopixel() {
    if (neopixel_clear_time_ > 0 && millis() >= neopixel_clear_time_) {
        clear_neopixel();
    }
}

void SAMD51CAN::neopixel_power_on() {
    digitalWrite(NEOPIXEL_POWER_PIN, HIGH);
}

void SAMD51CAN::neopixel_power_off() {
    digitalWrite(NEOPIXEL_POWER_PIN, LOW);
}

bool SAMD51CAN::set_loopback_mode(bool enabled) {
    if (!initialized_) {
        return false;
    }

    // Use the Adafruit CAN library's built-in loopback method
    // This is cleaner than direct register access and ensures
    // proper sequencing of mode changes

    if (enabled) {
        int result = CAN.loopback();
        if (result == 1) {
            config_.loopback_mode = true;
            return true;
        }
        return false;
    } else {
        // Switch back to normal mode
        // Need to reinitialize to exit loopback mode
        CAN.end();
        if (CAN.begin(config_.bitrate)) {
            config_.loopback_mode = false;
            // Re-register the callback
            CAN.onReceive(can_rx_callback);
            return true;
        }
        return false;
    }
}

#endif // PLATFORM_SAMD51
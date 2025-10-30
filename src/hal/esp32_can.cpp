#ifdef PLATFORM_ESP32

#include "esp32_can.h"
#include "../boards/board_registry.h"
#include <Arduino.h>

// TWAI timing configurations for standard bitrates
#define TWAI_TIMING_CONFIG_25KBITS()    {.brp = 128, .tseg_1 = 16, .tseg_2 = 8, .sjw = 3, .triple_sampling = false}
#define TWAI_TIMING_CONFIG_50KBITS()    {.brp = 80, .tseg_1 = 15, .tseg_2 = 4, .sjw = 3, .triple_sampling = false}
#define TWAI_TIMING_CONFIG_100KBITS()   {.brp = 40, .tseg_1 = 15, .tseg_2 = 4, .sjw = 3, .triple_sampling = false}
#define TWAI_TIMING_CONFIG_125KBITS()   {.brp = 32, .tseg_1 = 15, .tseg_2 = 4, .sjw = 3, .triple_sampling = false}
#define TWAI_TIMING_CONFIG_250KBITS()   {.brp = 16, .tseg_1 = 15, .tseg_2 = 4, .sjw = 3, .triple_sampling = false}
#define TWAI_TIMING_CONFIG_500KBITS()   {.brp = 8, .tseg_1 = 15, .tseg_2 = 4, .sjw = 3, .triple_sampling = false}
#define TWAI_TIMING_CONFIG_800KBITS()   {.brp = 4, .tseg_1 = 16, .tseg_2 = 8, .sjw = 3, .triple_sampling = false}
#define TWAI_TIMING_CONFIG_1MBITS()     {.brp = 4, .tseg_1 = 15, .tseg_2 = 4, .sjw = 3, .triple_sampling = false}

ESP32CAN::ESP32CAN()
    : twai_initialized_(false)
    , current_bitrate_(0)
    , loopback_enabled_(false)
    , listen_only_enabled_(false)
    , visual_feedback_enabled_(false) {
    // Initialize base class members
    last_error_ = CAN_ERROR_NONE;
    memset(&stats_, 0, sizeof(stats_));
    init_time_ms_ = 0;
}

ESP32CAN::~ESP32CAN() {
    deinitialize();
}

bool ESP32CAN::initialize(const CANConfig& config) {
    if (twai_initialized_) {
        deinitialize();
    }

    // Store configuration
    config_ = config;

    // Configure bitrate
    if (!configure_bitrate(config.bitrate)) {
        last_error_ = CAN_ERROR_CONFIG_ERROR;
        return false;
    }

    // Configure general settings
    general_config_ = TWAI_GENERAL_CONFIG_DEFAULT(
        (gpio_num_t)CAN_TX_PIN,
        (gpio_num_t)CAN_RX_PIN,
        TWAI_MODE_NORMAL
    );

    // Adjust mode based on configuration
    if (config.listen_only_mode) {
        general_config_.mode = TWAI_MODE_LISTEN_ONLY;
        listen_only_enabled_ = true;
    } else if (config.loopback_mode) {
        general_config_.mode = TWAI_MODE_NO_ACK;  // Self-test mode
        loopback_enabled_ = true;
    }

    // Configure filters
    if (config.acceptance_filter != 0 || config.acceptance_mask != 0) {
        filter_config_.acceptance_code = config.acceptance_filter;
        filter_config_.acceptance_mask = config.acceptance_mask;
        filter_config_.single_filter = true;
    } else {
        // Accept all messages
        filter_config_ = TWAI_FILTER_CONFIG_ACCEPT_ALL();
    }

    // Install TWAI driver
    esp_err_t err = twai_driver_install(&general_config_, &timing_config_, &filter_config_);
    if (err != ESP_OK) {
        last_error_ = map_esp_error(err);
        return false;
    }

    // Start TWAI driver
    err = twai_start();
    if (err != ESP_OK) {
        twai_driver_uninstall();
        last_error_ = map_esp_error(err);
        return false;
    }

    // Configure alerts for TX/RX events
    uint32_t alerts = TWAI_ALERT_TX_IDLE | TWAI_ALERT_TX_SUCCESS | TWAI_ALERT_TX_FAILED |
                      TWAI_ALERT_ERR_PASS | TWAI_ALERT_BUS_ERROR | TWAI_ALERT_RX_DATA |
                      TWAI_ALERT_RX_QUEUE_FULL | TWAI_ALERT_BUS_OFF | TWAI_ALERT_BUS_RECOVERED;

    err = twai_reconfigure_alerts(alerts, NULL);
    if (err != ESP_OK) {
        // Non-fatal, continue anyway
        Serial.printf("TWAI alert configuration warning: %d\n", err);
    }

    twai_initialized_ = true;
    current_bitrate_ = config.bitrate;
    init_time_ms_ = millis();

    // Reset statistics
    reset_statistics();

    return true;
}

void ESP32CAN::deinitialize() {
    if (!twai_initialized_) {
        return;
    }

    // Stop TWAI driver
    esp_err_t err = twai_stop();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        // Continue anyway
    }

    // Uninstall driver
    twai_driver_uninstall();

    twai_initialized_ = false;

    // Clear RX queue
    while (!rx_queue_.empty()) {
        rx_queue_.pop();
    }
}

bool ESP32CAN::is_ready() {
    return twai_initialized_;
}

bool ESP32CAN::send_message(const CANMessage& message) {
    if (!twai_initialized_) {
        last_error_ = CAN_ERROR_OTHER;
        return false;
    }

    // Convert to TWAI message format
    twai_message_t twai_msg;
    convert_to_twai_message(message, twai_msg);

    // Transmit message (with timeout)
    esp_err_t err = twai_transmit(&twai_msg, pdMS_TO_TICKS(100));

    if (err == ESP_OK) {
        update_tx_stats();
        return true;
    } else {
        stats_.error_count++;
        last_error_ = map_esp_error(err);
        return false;
    }
}

bool ESP32CAN::receive_message(CANMessage& message) {
    if (!twai_initialized_) {
        last_error_ = CAN_ERROR_OTHER;
        return false;
    }

    // Check if we have messages in our queue
    if (!rx_queue_.empty()) {
        message = rx_queue_.front();
        rx_queue_.pop();
        return true;
    }

    // Try to receive from TWAI (non-blocking)
    twai_message_t twai_msg;
    esp_err_t err = twai_receive(&twai_msg, 0);  // 0 = non-blocking

    if (err == ESP_OK) {
        convert_from_twai_message(twai_msg, message);
        update_rx_stats();
        return true;
    } else if (err == ESP_ERR_TIMEOUT) {
        // No message available
        return false;
    } else {
        last_error_ = map_esp_error(err);
        return false;
    }
}

uint16_t ESP32CAN::available() {
    if (!twai_initialized_) {
        return 0;
    }

    // Poll for new messages and add to queue
    handle_twai_alerts();

    // Return queue size
    return rx_queue_.size();
}

CANError ESP32CAN::get_error_status() {
    update_error_status();
    return last_error_;
}

bool ESP32CAN::clear_errors() {
    if (!twai_initialized_) {
        return false;
    }

    last_error_ = CAN_ERROR_NONE;

    // Try to recover from bus-off state
    twai_status_info_t status;
    if (twai_get_status_info(&status) == ESP_OK) {
        if (status.state == TWAI_STATE_BUS_OFF) {
            // Initiate recovery
            esp_err_t err = twai_initiate_recovery();
            return (err == ESP_OK);
        }
    }

    return true;
}

void ESP32CAN::get_statistics(CANStatistics& stats) {
    // Update from TWAI status
    if (twai_initialized_) {
        twai_status_info_t status;
        if (twai_get_status_info(&status) == ESP_OK) {
            // TWAI provides error counters we can merge with our stats
            // Note: TWAI counters are hardware counters, not cumulative
        }

        // Update uptime
        stats_.uptime_ms = millis() - init_time_ms_;
    }

    // Copy to output
    stats = stats_;
}

void ESP32CAN::reset_statistics() {
    memset(&stats_, 0, sizeof(stats_));
    init_time_ms_ = millis();
}

bool ESP32CAN::set_filter(uint32_t filter_id, uint32_t mask) {
    // TWAI filters require driver reinstall
    // Store for next initialization
    config_.acceptance_filter = filter_id;
    config_.acceptance_mask = mask;

    // If already initialized, need to reinit to apply filter
    if (twai_initialized_) {
        return initialize(config_);
    }

    return true;
}

const char* ESP32CAN::get_platform_name() {
    return "ESP32-TWAI";
}

const char* ESP32CAN::get_version() {
    return "1.0.0";
}

bool ESP32CAN::set_loopback_mode(bool enabled) {
    loopback_enabled_ = enabled;
    config_.loopback_mode = enabled;

    // Requires reinitialization to change mode
    if (twai_initialized_) {
        return initialize(config_);
    }

    return true;
}

void ESP32CAN::set_visual_feedback_enabled(bool enabled) {
    visual_feedback_enabled_ = enabled;
}

bool ESP32CAN::is_visual_feedback_enabled() {
    return visual_feedback_enabled_;
}

uint32_t ESP32CAN::get_timestamp_ms() {
    return millis();
}

// Private helper methods

bool ESP32CAN::configure_bitrate(uint32_t bitrate) {
    switch (bitrate) {
        case 25000:
            timing_config_ = TWAI_TIMING_CONFIG_25KBITS();
            break;
        case 50000:
            timing_config_ = TWAI_TIMING_CONFIG_50KBITS();
            break;
        case 100000:
            timing_config_ = TWAI_TIMING_CONFIG_100KBITS();
            break;
        case 125000:
            timing_config_ = TWAI_TIMING_CONFIG_125KBITS();
            break;
        case 250000:
            timing_config_ = TWAI_TIMING_CONFIG_250KBITS();
            break;
        case 500000:
            timing_config_ = TWAI_TIMING_CONFIG_500KBITS();
            break;
        case 800000:
            timing_config_ = TWAI_TIMING_CONFIG_800KBITS();
            break;
        case 1000000:
            timing_config_ = TWAI_TIMING_CONFIG_1MBITS();
            break;
        default:
            return false;
    }
    return true;
}

void ESP32CAN::convert_to_twai_message(const CANMessage& msg, twai_message_t& twai_msg) {
    twai_msg.identifier = msg.id;
    twai_msg.data_length_code = msg.length;
    twai_msg.extd = msg.extended ? 1 : 0;
    twai_msg.rtr = msg.remote ? 1 : 0;
    twai_msg.ss = 0;  // Not single shot
    twai_msg.self = 0;  // Not self-reception
    twai_msg.dlc_non_comp = 0;

    // Copy data
    for (uint8_t i = 0; i < msg.length && i < 8; i++) {
        twai_msg.data[i] = msg.data[i];
    }
}

void ESP32CAN::convert_from_twai_message(const twai_message_t& twai_msg, CANMessage& msg) {
    msg.id = twai_msg.identifier;
    msg.length = twai_msg.data_length_code;
    msg.extended = twai_msg.extd ? true : false;
    msg.remote = twai_msg.rtr ? true : false;
    msg.timestamp = get_timestamp_ms();

    // Copy data
    for (uint8_t i = 0; i < msg.length && i < 8; i++) {
        msg.data[i] = twai_msg.data[i];
    }
}

void ESP32CAN::handle_twai_alerts() {
    if (!twai_initialized_) {
        return;
    }

    uint32_t alerts = 0;
    esp_err_t err = twai_read_alerts(&alerts, 0);  // Non-blocking

    if (err != ESP_OK || alerts == 0) {
        return;
    }

    // Handle various alerts
    if (alerts & TWAI_ALERT_RX_DATA) {
        // New data available - try to receive
        twai_message_t twai_msg;
        while (twai_receive(&twai_msg, 0) == ESP_OK) {
            CANMessage msg;
            convert_from_twai_message(twai_msg, msg);
            rx_queue_.push(msg);
            update_rx_stats();
        }
    }

    if (alerts & TWAI_ALERT_TX_SUCCESS) {
        // Transmission successful
    }

    if (alerts & TWAI_ALERT_TX_FAILED) {
        stats_.error_count++;
    }

    if (alerts & TWAI_ALERT_BUS_ERROR) {
        stats_.error_count++;
        last_error_ = CAN_ERROR_OTHER;
        update_error_stats(last_error_);
    }

    if (alerts & TWAI_ALERT_ERR_PASS) {
        last_error_ = CAN_ERROR_PASSIVE;
    }

    if (alerts & TWAI_ALERT_BUS_OFF) {
        last_error_ = CAN_ERROR_BUS_OFF;
        // Attempt recovery
        twai_initiate_recovery();
    }

    if (alerts & TWAI_ALERT_BUS_RECOVERED) {
        last_error_ = CAN_ERROR_NONE;
    }

    if (alerts & TWAI_ALERT_RX_QUEUE_FULL) {
        stats_.error_count++;
    }
}

void ESP32CAN::update_error_status() {
    if (!twai_initialized_) {
        last_error_ = CAN_ERROR_OTHER;
        return;
    }

    handle_twai_alerts();
}

CANError ESP32CAN::map_esp_error(esp_err_t err) {
    switch (err) {
        case ESP_OK:
            return CAN_ERROR_NONE;
        case ESP_ERR_INVALID_STATE:
            return CAN_ERROR_CONFIG_ERROR;
        case ESP_ERR_TIMEOUT:
            return CAN_ERROR_OTHER;
        case ESP_ERR_INVALID_ARG:
            return CAN_ERROR_CONFIG_ERROR;
        case ESP_ERR_NO_MEM:
            return CAN_ERROR_BUFFER_OVERFLOW;
        default:
            return CAN_ERROR_OTHER;
    }
}

void ESP32CAN::indicate_tx() {
    // Visual feedback for TX
    // If board has status LED, blink briefly
    #ifdef STATUS_LED_PIN
        digitalWrite(STATUS_LED_PIN, HIGH);
        delayMicroseconds(100);
        digitalWrite(STATUS_LED_PIN, LOW);
    #endif
}

void ESP32CAN::indicate_rx() {
    // Visual feedback for RX
    #ifdef STATUS_LED_PIN
        digitalWrite(STATUS_LED_PIN, HIGH);
        delayMicroseconds(50);
        digitalWrite(STATUS_LED_PIN, LOW);
    #endif
}

void ESP32CAN::indicate_error() {
    // Visual feedback for errors
    #ifdef STATUS_LED_PIN
        for (int i = 0; i < 3; i++) {
            digitalWrite(STATUS_LED_PIN, HIGH);
            delay(50);
            digitalWrite(STATUS_LED_PIN, LOW);
            delay(50);
        }
    #endif
}

#endif // PLATFORM_ESP32

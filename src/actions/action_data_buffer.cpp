#include "action_data_buffer.h"

ActionDataBuffer::ActionDataBuffer() {
    clear();
}

bool ActionDataBuffer::write(uint8_t slot, const uint8_t* data, uint8_t length) {
    // Validate parameters
    if (!data || !is_valid_access(slot, length)) {
        return false;
    }

    // Copy data to buffer
    memcpy(&buffer_[slot], data, length);

    // Mark slots as used
    for (uint8_t i = 0; i < length; i++) {
        slot_used_[slot + i] = true;
    }

    return true;
}

bool ActionDataBuffer::write_byte(uint8_t slot, uint8_t value) {
    return write(slot, &value, 1);
}

bool ActionDataBuffer::write_uint16(uint8_t slot, uint16_t value) {
    // Little-endian encoding
    uint8_t bytes[2];
    bytes[0] = value & 0xFF;
    bytes[1] = (value >> 8) & 0xFF;
    return write(slot, bytes, 2);
}

bool ActionDataBuffer::write_uint32(uint8_t slot, uint32_t value) {
    // Little-endian encoding
    uint8_t bytes[4];
    bytes[0] = value & 0xFF;
    bytes[1] = (value >> 8) & 0xFF;
    bytes[2] = (value >> 16) & 0xFF;
    bytes[3] = (value >> 24) & 0xFF;
    return write(slot, bytes, 4);
}

const uint8_t* ActionDataBuffer::read_all(uint8_t& valid_length) const {
    valid_length = get_used_length();
    return buffer_;
}

bool ActionDataBuffer::read_byte(uint8_t slot, uint8_t& value) const {
    if (slot >= 8 || !slot_used_[slot]) {
        return false;
    }
    value = buffer_[slot];
    return true;
}

const uint8_t* ActionDataBuffer::get_raw_buffer() const {
    return buffer_;
}

uint8_t ActionDataBuffer::get_used_length() const {
    // Find highest used slot
    // Iterate backwards from slot 7 to find last used slot
    for (int8_t i = 7; i >= 0; i--) {
        if (slot_used_[i]) {
            return i + 1;
        }
    }
    // No slots used
    return 0;
}

bool ActionDataBuffer::is_slot_used(uint8_t slot) const {
    if (slot >= 8) {
        return false;
    }
    return slot_used_[slot];
}

void ActionDataBuffer::clear() {
    memset(buffer_, 0, 8);
    memset(slot_used_, 0, 8);
}

bool ActionDataBuffer::clear_range(uint8_t start_slot, uint8_t length) {
    if (!is_valid_access(start_slot, length)) {
        return false;
    }

    // Clear data and usage markers
    for (uint8_t i = 0; i < length; i++) {
        buffer_[start_slot + i] = 0;
        slot_used_[start_slot + i] = false;
    }

    return true;
}

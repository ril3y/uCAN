#pragma once

#include <Arduino.h>

/**
 * Pin Error Logger
 *
 * Provides macros for logging pin validation errors to Serial.
 * All errors are prefixed with [PIN_ERROR], [PIN_WARNING], or [PIN_INFO]
 * to allow easy parsing by host application.
 *
 * Error Format:
 *   [PIN_ERROR] Pin {pin}: {reason}
 *   [PIN_WARNING] Pin {pin}: {reason}
 *   [PIN_INFO] Pin {pin}: {reason}
 *
 * Example Output:
 *   [PIN_ERROR] Pin 22: Cannot use CAN TX pin for GPIO
 *   [PIN_ERROR] Pin 13: Pin already allocated for PWM
 *   [PIN_WARNING] Pin A0: Pin shared between ADC and DAC
 *   [PIN_INFO] Pin 13: Allocated for PWM output
 *
 * Usage:
 *   LOG_PIN_ERROR(22, "Cannot use CAN TX pin for GPIO");
 *   LOG_PIN_WARNING(A0, "Pin shared between ADC and DAC");
 *   LOG_PIN_INFO(13, "Allocated for PWM output");
 */

/**
 * Log pin error (validation failure, cannot proceed)
 */
#define LOG_PIN_ERROR(pin, reason) \
    Serial.print("[PIN_ERROR] Pin "); \
    Serial.print(pin); \
    Serial.print(": "); \
    Serial.println(reason)

/**
 * Log pin warning (potential issue, but can proceed)
 */
#define LOG_PIN_WARNING(pin, reason) \
    Serial.print("[PIN_WARNING] Pin "); \
    Serial.print(pin); \
    Serial.print(": "); \
    Serial.println(reason)

/**
 * Log pin info (successful allocation or status)
 */
#define LOG_PIN_INFO(pin, reason) \
    Serial.print("[PIN_INFO] Pin "); \
    Serial.print(pin); \
    Serial.print(": "); \
    Serial.println(reason)

/**
 * Log generic action error (not pin-specific)
 */
#define LOG_ACTION_ERROR(action, reason) \
    Serial.print("[ACTION_ERROR] "); \
    Serial.print(action); \
    Serial.print(": "); \
    Serial.println(reason)

/**
 * Log generic action warning
 */
#define LOG_ACTION_WARNING(action, reason) \
    Serial.print("[ACTION_WARNING] "); \
    Serial.print(action); \
    Serial.print(": "); \
    Serial.println(reason)

/**
 * Log generic action info
 */
#define LOG_ACTION_INFO(action, reason) \
    Serial.print("[ACTION_INFO] "); \
    Serial.print(action); \
    Serial.print(": "); \
    Serial.println(reason)

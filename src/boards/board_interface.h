#pragma once

#include <stdint.h>
#include "../actions/custom_command.h"

// Forward declarations
class ActionManagerBase;

/**
 * BoardInterface
 *
 * Abstract base class for board-specific implementations.
 * Each board (T-CAN485, T-Panel, Feather M4, etc.) provides its own
 * implementation that handles board-specific initialization, peripherals,
 * and custom commands.
 *
 * Philosophy:
 * - Platform code (esp32_action_manager, samd51_action_manager) provides
 *   low-level APIs: GPIO, PWM, ADC, CAN
 * - Board implementations handle board-specific features: displays,
 *   RS485, SD cards, sensors, etc.
 * - All code for a specific board lives in one folder: src/boards/<board_name>/
 */
class BoardInterface {
public:
    virtual ~BoardInterface() = default;

    /**
     * Initialize board-specific hardware
     *
     * Called after platform initialization (GPIO/CAN/PWM are ready).
     * Use this to:
     * - Initialize peripherals (displays, SD cards, sensors)
     * - Configure board-specific power management
     * - Setup communication interfaces (RS485, SPI, I2C)
     * - Initialize status indicators (LEDs, NeoPixels)
     *
     * @param action_manager Pointer to action manager for accessing platform APIs
     * @return true if initialization succeeded, false on error
     */
    virtual bool initialize(ActionManagerBase* action_manager) = 0;

    /**
     * Register board-specific custom commands
     *
     * Add custom commands that are unique to this board.
     * Examples:
     * - T-CAN485: "rs485_send", "sd_log"
     * - T-Panel: "display_text", "display_brightness", "touch_calibrate"
     * - Relay Board: "relay_set", "relay_sequence"
     *
     * @param registry Command registry to add commands to
     */
    virtual void register_custom_commands(CustomCommandRegistry& registry) = 0;

    /**
     * Periodic update callback (optional)
     *
     * Called from main loop for periodic board tasks:
     * - Update displays with CAN statistics
     * - Process touch events
     * - Monitor sensor data
     * - Blink status LEDs
     *
     * Keep this fast (<1ms) to avoid blocking CAN message processing.
     */
    virtual void update_periodic() {}

    /**
     * Get board name for identification
     * @return Human-readable board name
     */
    virtual const char* get_board_name() const = 0;

    /**
     * Get board revision/version (optional)
     * @return Board version string (e.g., "v1.2", "Rev B")
     */
    virtual const char* get_board_version() const {
        return "1.0";
    }
};

/**
 * BoardFactory
 *
 * Creates the appropriate board implementation based on compile-time defines.
 * Each board gets compiled with its own define (BOARD_T_CAN485, BOARD_T_PANEL, etc.)
 * set in platformio.ini.
 */
class BoardFactory {
public:
    /**
     * Create board-specific implementation
     * @return Pointer to board implementation, or nullptr if not available
     */
    static BoardInterface* create();
};

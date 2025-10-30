/**
 * @file board_factory.cpp
 * @brief Board factory implementation - instantiates board-specific implementations
 *
 * This factory creates the appropriate board implementation based on compile-time
 * defines set in platformio.ini. Each board variant (T-CAN485, T-Panel, etc.) gets
 * its own define and corresponding implementation class.
 *
 * Architecture Pattern:
 * - Compile-time selection using #ifdef directives (zero runtime overhead)
 * - Returns nullptr for platforms without board-specific implementations
 * - Extensible: adding new boards requires only adding a new #elif block
 * - Single responsibility: factory only creates instances, doesn't manage lifecycle
 *
 * Design Philosophy:
 * - Platform code (ESP32ActionManager, SAMD51ActionManager) provides low-level APIs
 * - Board implementations (TCAN485Board, TPanelBoard) handle board-specific peripherals
 * - Generic boards (Pico, Feather M4 CAN) don't need board implementations
 */

#include "board_interface.h"
#include "board_registry.h"

// ============================================================================
// Board Implementation Headers
// ============================================================================
// Include board-specific implementations based on compile-time defines.
// Only the selected board's header will be included, reducing compilation time.

#ifdef BOARD_T_CAN485
    #include "t_can485/board_impl.h"
#endif

#ifdef BOARD_T_PANEL
    #include "t_panel/board_impl.h"
#endif

#if defined(ARDUINO_RASPBERRY_PI_PICO) || defined(ARDUINO_RASPBERRY_PI_PICO_W)
    #include "rp2040/board_impl.h"
#endif

#ifdef ARDUINO_ADAFRUIT_FEATHER_M4_CAN
    #include "samd51/board_impl.h"
#endif

// Future board implementations:
// Add new boards here following the same pattern
//
// #ifdef BOARD_CUSTOM_RELAY
//     #include "custom/relay_board_impl.h"
// #endif
//
// #ifdef BOARD_CUSTOM_DISPLAY
//     #include "custom/display_board_impl.h"
// #endif

// ============================================================================
// BoardFactory Implementation
// ============================================================================

/**
 * Create board-specific implementation
 *
 * Returns a pointer to the appropriate board implementation based on the
 * compile-time board define. Uses #elif chain for mutually exclusive selection.
 *
 * IMPORTANT: Exactly one BOARD_* define should be set at compile time.
 * The #elif chain ensures only the first match is used.
 *
 * Compile-time defines (set in platformio.ini build_flags):
 * - BOARD_T_CAN485: LilyGo T-CAN485 (ESP32 + CAN + RS485 + SD + WS2812)
 * - BOARD_T_PANEL: LilyGo T-Panel (ESP32-S3 + 480x480 touchscreen + CAN)
 *
 * Return value:
 * - Non-null pointer: Board-specific implementation available
 * - nullptr: Generic board with no special peripherals (valid for Pico, Feather M4)
 *
 * Memory management:
 * - Caller is responsible for deleting the returned pointer
 * - Typical usage: create once in setup(), delete in cleanup (if needed)
 *
 * @return Pointer to board implementation, or nullptr if not available
 */
BoardInterface* BoardFactory::create() {
    // Use #elif chain to ensure only one board is instantiated
    // This provides clear compile-time guarantees about mutually exclusive board selection

    #if defined(BOARD_T_CAN485)
        return new TCAN485Board();

    #elif defined(BOARD_T_PANEL)
        return new TPanelBoard();

    #elif defined(ARDUINO_RASPBERRY_PI_PICO) || defined(ARDUINO_RASPBERRY_PI_PICO_W)
        // Raspberry Pi Pico board implementation
        return new RPiPicoBoard();

    #elif defined(ARDUINO_ADAFRUIT_FEATHER_M4_CAN)
        // Adafruit Feather M4 CAN board implementation
        return new FeatherM4CANBoard();

    // Add future board implementations here using #elif:
    //
    // #elif defined(BOARD_CUSTOM_RELAY)
    //     return new RelayBoard();
    //
    // #elif defined(BOARD_CUSTOM_DISPLAY)
    //     return new DisplayBoard();

    #else
        // No board-specific implementation for this platform configuration
        // This is valid for generic development boards without special peripherals:
        // - Generic ESP32 DevKit (just CAN transceiver)
        // - Generic RP2040 board (just CAN transceiver)
        //
        // Platform action managers still provide GPIO/CAN/PWM functionality
        return nullptr;
    #endif
}

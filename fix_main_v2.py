#!/usr/bin/env python3
"""Fix main.cpp to remove LED code and add board periodic update"""

def fix_main_cpp():
    with open('src/main.cpp', 'r') as f:
        content = f.read()

    # Remove LED setup block (lines 56-63)
    led_setup = """  // Setup status LED if available
  #ifdef STATUS_LED_PIN
    if (STATUS_LED_PIN != 0) {
      pinMode(STATUS_LED_PIN, OUTPUT);
    }
  #elif defined(LED_BUILTIN)
    pinMode(LED_BUILTIN, OUTPUT);
  #endif

  // Wait for serial port"""

    content = content.replace(led_setup, """  // Wait for serial port""")

    # Remove LED blink block
    led_blink = """  // Blink LED to show we're alive
  static unsigned long last_blink = 0;
  if (millis() - last_blink > 1000) {
    #ifdef STATUS_LED_PIN
      if (STATUS_LED_PIN != 0) {
        digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
      }
    #elif defined(LED_BUILTIN)
      digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    #endif
    last_blink = millis();
  }

  // Process CAN messages"""

    content = content.replace(led_blink, """  // Process CAN messages""")

    # Add board periodic update after action_manager->update_periodic()
    old_periodic = """  // Update periodic actions
  if (action_manager) {
    action_manager->update_periodic();
  }

  // Send periodic statistics"""

    new_periodic = """  // Update periodic actions
  if (action_manager) {
    action_manager->update_periodic();
  }

  // Update board-specific periodic tasks (LED blinking, display updates, etc.)
  if (action_manager) {
    action_manager->update_board_periodic();
  }

  // Send periodic statistics"""

    content = content.replace(old_periodic, new_periodic)

    with open('src/main.cpp', 'w') as f:
        f.write(content)

    print("main.cpp fixed successfully")

if __name__ == '__main__':
    fix_main_cpp()

#!/usr/bin/env python3
"""Fix main.cpp to remove LED code and add board periodic update"""

def fix_main_cpp():
    with open('src/main.cpp', 'r') as f:
        lines = f.readlines()

    # Remove LED setup code (lines 56-63, 0-indexed: 55-62)
    # Lines contain: "// Setup status LED if available" through "#endif"
    new_lines = []
    skip_led_setup = False
    skip_led_blink = False
    blink_brace_count = 0

    for i, line in enumerate(lines):
        line_num = i + 1

        # Skip LED setup block (lines 56-63)
        if line_num == 56 and '// Setup status LED' in line:
            skip_led_setup = True
            continue
        if skip_led_setup and line_num <= 63:
            continue
        if line_num == 64:
            skip_led_setup = False

        # Skip LED blink block (lines 142-153)
        if '// Blink LED to show we' in line:
            skip_led_blink = True
            continue
        if skip_led_blink:
            if '{' in line:
                blink_brace_count += 1
            if '}' in line:
                blink_brace_count -= 1
                if blink_brace_count == 0:
                    skip_led_blink = False
                    continue
            continue

        # Add board periodic update after action_manager->update_periodic()
        new_lines.append(line)
        if 'action_manager->update_periodic();' in line and not skip_led_blink:
            new_lines.append('  }\n')
            new_lines.append('\n')
            new_lines.append('  // Update board-specific periodic tasks (LED blinking, display updates, etc.)\n')
            new_lines.append('  if (action_manager) {\n')
            new_lines.append('    action_manager->update_board_periodic();\n')

    with open('src/main.cpp', 'w') as f:
        f.writelines(new_lines)

    print("main.cpp fixed successfully")

if __name__ == '__main__':
    fix_main_cpp()

from textual.widgets import Input
from textual.validation import Validator, ValidationResult
from textual import events
from typing import List, Callable, Optional
import re


class CANCommandValidator(Validator):
    """Validator for CAN commands."""
    
    def validate(self, value: str) -> ValidationResult:
        """Validate CAN command format."""
        if not value:
            return ValidationResult.success()
        
        # Check for send command format: send:ID:DATA
        if value.startswith("send:"):
            parts = value.split(":")
            if len(parts) < 3:
                return ValidationResult.failure("Format: send:ID:DATA (e.g., send:123:DEADBEEF)")
            
            # Validate ID part
            id_part = parts[1]
            if not id_part:
                return ValidationResult.failure("CAN ID required")
            
            try:
                # Support both hex (0x123, 123) and decimal
                if id_part.startswith("0x"):
                    can_id = int(id_part, 16)
                else:
                    can_id = int(id_part, 16)  # Assume hex if no 0x prefix
                
                if can_id < 0 or can_id > 0x7FF:  # Standard CAN ID range
                    return ValidationResult.failure("CAN ID must be 0-0x7FF (11-bit)")
            except ValueError:
                return ValidationResult.failure("Invalid CAN ID format")
            
            # Validate data part
            data_part = parts[2]
            if data_part:
                # Check if it's valid hex
                if not re.match(r'^[0-9A-Fa-f]*$', data_part):
                    return ValidationResult.failure("Data must be hexadecimal")
                
                if len(data_part) % 2 != 0:
                    return ValidationResult.failure("Data must have even number of hex digits")
                
                if len(data_part) > 16:  # 8 bytes max
                    return ValidationResult.failure("Data maximum 8 bytes (16 hex digits)")
        
        elif value not in ["test", "status", "reset", "help"]:
            # Unknown command
            return ValidationResult.failure("Unknown command. Use: send:ID:DATA, test, status, reset, help")
        
        return ValidationResult.success()


class CommandInputWidget(Input):
    """Enhanced input widget for CAN commands with history and validation."""
    
    def __init__(self, **kwargs):
        super().__init__(
            placeholder="Enter command (e.g., send:123:DEADBEEF)",
            validators=[CANCommandValidator()],
            **kwargs
        )
        
        self.command_history: List[str] = []
        self.history_index = -1
        self.command_callback: Optional[Callable[[str], None]] = None
        
        # Autocomplete suggestions
        self.suggestions = [
            "send:123:DEADBEEF",
            "send:456:01020304",
            "send:789:CAFEBABE",
            "test",
            "status",
            "reset",
            "help"
        ]
    
    def set_command_callback(self, callback: Callable[[str], None]):
        """Set callback for when commands are submitted."""
        self.command_callback = callback
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        command = event.value.strip()
        
        if command:
            # Add to history
            if command not in self.command_history:
                self.command_history.append(command)
            
            # Keep history size reasonable
            if len(self.command_history) > 100:
                self.command_history.pop(0)
            
            # Reset history index
            self.history_index = -1
            
            # Execute command
            if self.command_callback:
                # Check if callback is async
                import asyncio
                if asyncio.iscoroutinefunction(self.command_callback):
                    await self.command_callback(command)
                else:
                    self.command_callback(command)
            
            # Clear input
            self.value = ""
    
    def key_up(self) -> None:
        """Navigate up in command history."""
        if self.command_history:
            if self.history_index == -1:
                self.history_index = len(self.command_history) - 1
            elif self.history_index > 0:
                self.history_index -= 1
            
            if 0 <= self.history_index < len(self.command_history):
                self.value = self.command_history[self.history_index]
                self.cursor_position = len(self.value)
    
    def key_down(self) -> None:
        """Navigate down in command history."""
        if self.command_history and self.history_index != -1:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.value = self.command_history[self.history_index]
            else:
                self.history_index = -1
                self.value = ""
            
            self.cursor_position = len(self.value)
    
    async def _on_key(self, event: events.Key) -> None:
        """Handle special key combinations."""
        if event.key == "up":
            self.key_up()
            event.prevent_default()
        elif event.key == "down":
            self.key_down()
            event.prevent_default()
        elif event.key == "tab":
            self.autocomplete()
            event.prevent_default()
        else:
            await super()._on_key(event)
    
    def autocomplete(self) -> None:
        """Provide autocomplete suggestions."""
        current = self.value.lower()
        
        if not current:
            return
        
        # Find matching suggestions
        matches = [s for s in self.suggestions if s.lower().startswith(current)]
        
        # Add recent history matches
        history_matches = [h for h in self.command_history 
                          if h.lower().startswith(current) and h not in matches]
        matches.extend(history_matches[-5:])  # Last 5 history matches
        
        if matches:
            # Use the first match
            self.value = matches[0]
            self.cursor_position = len(self.value)
    
    def add_suggestion(self, suggestion: str):
        """Add a new autocomplete suggestion."""
        if suggestion not in self.suggestions:
            self.suggestions.append(suggestion)
    
    def get_command_help(self) -> str:
        """Get help text for commands."""
        return """Available Commands:
        
🔧 CAN Commands:
  send:ID:DATA    Send CAN message (e.g., send:123:DEADBEEF)
  
🛠️ System Commands:
  test           Send test command to device
  status         Get device status
  reset          Reset device connection
  help           Show this help
  
📝 Command Format:
  - CAN ID: Hexadecimal (123, 0x123)
  - Data: Hexadecimal pairs (DEADBEEF = 4 bytes)
  - Max 8 bytes of data per message
  
⌨️ Shortcuts:
  - ↑↓: Navigate command history
  - Tab: Autocomplete
  - Enter: Send command
  - F1: Clear messages
  - F2: Save log
  - F3: Pause/Resume
  - F4: Show help
  - F5: Toggle detailed view
  - Ctrl+Shift+C: Copy messages
  - Ctrl+Shift+A: Copy all messages
  - Ctrl+R: Reconnect
  - Ctrl+C: Quit
"""
    
    def validate_and_format_command(self, command: str) -> tuple[bool, str]:
        """Validate and format a command for sending."""
        command = command.strip()
        
        if command.startswith("send:"):
            parts = command.split(":")
            if len(parts) >= 3:
                try:
                    # Parse and validate ID
                    id_part = parts[1]
                    if id_part.startswith("0x"):
                        can_id = int(id_part, 16)
                    else:
                        can_id = int(id_part, 16)
                    
                    # Format data
                    data_part = parts[2].upper()
                    
                    # Return formatted command
                    formatted = f"send:{can_id:X}:{data_part}"
                    return True, formatted
                    
                except ValueError:
                    return False, "Invalid CAN ID format"
            else:
                return False, "Invalid command format"
        
        # Other commands pass through
        return True, command
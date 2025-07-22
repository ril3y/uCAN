"""
Switch visualization widget for wiring harness switch states (CAN ID 0x500).

This widget provides a visual dashboard showing the state of individual switches
from the wiring harness, with real-time updates and raw message console.
"""

from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.widgets import Static, Button, RichLog, Label
from textual.reactive import reactive
from textual.binding import Binding
from rich.text import Text
from rich.table import Table
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import asyncio

from ..models.can_message import CANMessage
from ..parsers.base import ParsedMessage

logger = logging.getLogger(__name__)


class SwitchIndicator(Static):
    """Individual switch indicator widget."""
    
    DEFAULT_CSS = """
    SwitchIndicator {
        width: 18;
        height: 8;
        border: thick $primary;
        text-align: center;
        content-align: center middle;
        margin: 1;
    }
    
    SwitchIndicator.switch-off {
        background: $surface-lighten-1;
        color: $text-muted;
        border: thick $surface-lighten-2;
        text-style: dim;
    }
    
    SwitchIndicator.switch-on {
        background: $success;
        color: $text;
        border: thick $success-lighten-1;
        text-style: bold;
    }
    
    SwitchIndicator.switch-error {
        background: $error;
        color: $text;
        border: thick $error-lighten-1;
        text-style: bold;
    }
    """
    
    def __init__(self, switch_name: str, **kwargs):
        super().__init__(**kwargs)
        self.switch_name = switch_name
        self.switch_state = False
        self.error_state = False
        
        
        self.update_display()
    
    def set_state(self, state: bool, error: bool = False):
        """Update the switch state and display."""
        self.switch_state = state
        self.error_state = error
        self.update_display()
    
    def update_display(self):
        """Update the visual display based on current state."""
        if self.error_state:
            self.remove_class("switch-off", "switch-on")
            self.add_class("switch-error")
            status = "ERR"
        elif self.switch_state:
            self.remove_class("switch-off", "switch-error")
            self.add_class("switch-on")
            status = "ON"
        else:
            self.remove_class("switch-on", "switch-error")
            self.add_class("switch-off")
            status = "OFF"
        
        # Update the text content with emoji and better formatting
        emoji = "🟢" if self.switch_state and not self.error_state else "🔴" if self.error_state else "⚫"
        # Split switch name by newlines for multi-line display
        name_lines = self.switch_name.split('\n')
        if len(name_lines) > 1:
            text_content = f"[bold]{name_lines[0]}[/bold]\n[bold]{name_lines[1]}[/bold]\n{emoji} {status}"
        else:
            text_content = f"[bold]{self.switch_name}[/bold]\n{emoji} {status}"
        
        
        self.update(text_content)


class MessageConsole(RichLog):
    """Mini console for displaying raw messages."""
    
    def __init__(self, max_lines: int = 100, **kwargs):
        super().__init__(max_lines=max_lines, **kwargs)
        self.markup = True
        self.highlight = True
        self.auto_scroll = True


class SwitchViewWidget(Container):
    """
    Complete switch visualization widget combining switch display and message console.
    """
    
    DEFAULT_CSS = """
    SwitchViewWidget {
        height: 100%;
        width: 100%;
    }
    
    #switch_dashboard {
        height: 60%;
        border: solid $primary;
        padding: 1;
    }
    
    #control_buttons {
        height: 3;
        margin: 1 0;
        align: center middle;
    }
    
    #query_button {
        width: auto;
        min-width: 20;
    }
    
    #switch_grid {
        grid-size: 3 2;
        grid-gutter: 1 1;
        height: auto;
        min-height: 18;
        margin: 1 0;
    }
    
    #switch_info {
        height: 6;
        border: solid $secondary;
        margin: 1 0;
        padding: 1;
    }
    
    #message_console {
        height: 40%;
        border: solid $accent;
        margin-top: 1;
    }
    
    #console_header {
        height: 1;
        background: $accent;
        text-align: center;
        padding: 0 1;
    }
    
    #console_log {
        height: 1fr;
        padding: 0 1;
    }
    
    .info_table {
        width: 100%;
        height: 100%;
    }
    """
    
    BINDINGS = [
        Binding("f6", "toggle_console", "Toggle Console"),
        Binding("ctrl+l", "clear_console", "Clear Console"),
    ]
    
    # Switch definitions matching the actual protocol specification
    SWITCH_DEFINITIONS = {
        0: "Brake Switch",      # Bit 0: B = Brake (1 = Pressed, 0 = Released)
        1: "Eco Switch",        # Bit 1: E = Eco Mode (1 = Enabled, 0 = Disabled) - Match parser!
        2: "Reverse Switch",    # Bit 2: R = Reverse (1 = Selected, 0 = Not selected)
        3: "Foot Switch",       # Bit 3: S = Foot Switch (1 = Pressed, 0 = Released)
        4: "Forward Switch",    # Bit 4: F = Forward (1 = Selected, 0 = Not selected)
        5: "Reserved",          # Bit 5: Reserved (always 0)
        6: "Reserved",          # Bit 6: Reserved (always 0)
        7: "Reserved"           # Bit 7: Reserved (always 0)
    }
    
    # Descriptive display names for UI matching protocol
    SWITCH_DISPLAY_NAMES = {
        0: "Brake\nSwitch",     # Bit 0: B = Brake (1 = Pressed, 0 = Released)
        1: "Eco\nMode",         # Bit 1: E = Eco Mode (1 = Enabled, 0 = Disabled)  
        2: "Reverse\nGear",     # Bit 2: R = Reverse (1 = Selected, 0 = Not selected)
        3: "Foot\nSwitch",      # Bit 3: S = Foot Switch (1 = Pressed, 0 = Released)
        4: "Forward\nGear",     # Bit 4: F = Forward (1 = Selected, 0 = Not selected)
        5: "Reserved\n#5",      # Bit 5: Reserved (always 0)
        6: "Reserved\n#6",      # Bit 6: Reserved (always 0)
        7: "Reserved\n#7"       # Bit 7: Reserved (always 0)
    }
    
    def __init__(self, supported_can_ids: Optional[List[int]] = None, send_command_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.switch_indicators: Dict[int, SwitchIndicator] = {}
        self.last_message_time: Optional[datetime] = None
        self.message_count = 0
        self.error_count = 0
        self.console_visible = True
        self.last_timestamp = None
        self.operational_state = "UNKNOWN"
        self.supported_can_ids = supported_can_ids or [0x500]  # Default to 0x500 if not provided
        self.send_command_callback = send_command_callback  # Callback to send CAN commands
        
    def compose(self) -> ComposeResult:
        """Compose the switch view widget."""
        # Main dashboard area
        with Container(id="switch_dashboard"):
            yield Static("🔌 Wiring Harness Switch Dashboard", classes="dashboard-title")
            
            # Control buttons
            with Horizontal(id="control_buttons"):
                yield Button("🔄 Query Switch States", id="query_button", variant="primary")
            
            # Switch grid - only show active switches (0-4)
            with Grid(id="switch_grid"):
                for switch_id in range(5):  # Only bits 0-4 are used
                    display_name = self.SWITCH_DISPLAY_NAMES[switch_id]
                    indicator = SwitchIndicator(display_name, id=f"switch_{switch_id}")
                    self.switch_indicators[switch_id] = indicator
                    yield indicator
            
            # Info panel
            with Container(id="switch_info"):
                yield Static("", id="info_display")
        
        # Message console
        with Container(id="message_console"):
            yield Static("📝 Message Console", id="console_header")
            yield MessageConsole(id="console_log")
    
    @staticmethod
    def calculate_crc8(data: List[int]) -> int:
        """
        Calculate CRC8 checksum for the given data.
        
        Args:
            data: List of bytes to calculate CRC for
            
        Returns:
            CRC8 checksum value
        """
        crc = 0
        polynomial = 0x07  # CRC8 polynomial
        
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc = crc << 1
                crc &= 0xFF
        
        return crc
    
    def on_mount(self) -> None:
        """Initialize the widget after mounting."""
        self.update_info_display()
        can_id_list = ', '.join(f"0x{can_id:03X}" for can_id in self.supported_can_ids)
        self.log_console(f"Switch dashboard initialized - Filtering CAN IDs: {can_id_list}", "info")
    
    def update_switch_states(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]):
        """
        Update switch states based on a CAN message.
        
        Args:
            can_message: Raw CAN message
            parsed_message: Parsed message data (if available)
        """
        # Filter out messages not for our supported CAN IDs
        if can_message.can_id not in self.supported_can_ids:
            return
            
        self.message_count += 1
        self.last_message_time = datetime.now()
        
        # Log the raw message
        self.log_console(
            f"CAN RX: ID=0x{can_message.can_id:03X} Data=[{' '.join(f'{b:02X}' for b in can_message.data)}]",
            "rx"
        )
        
        if not parsed_message or not parsed_message.is_valid():
            self.error_count += 1
            self.log_console("❌ Failed to parse message", "error")
            self.update_info_display()
            return
        
        # Extract switch states from parsed message
        switch_states = {}
        has_errors = False
        
        for field in parsed_message.fields:
            # Look for individual switch fields - match against parser's naming convention
            for switch_id, switch_name in self.SWITCH_DEFINITIONS.items():
                if field.name == switch_name and field.field_type.value == "boolean":
                    switch_states[switch_id] = field.value
                    break
        
        # Check for validation errors
        if parsed_message.errors:
            has_errors = True
            for error in parsed_message.errors:
                self.log_console(f"❌ {error}", "error")
        
        # Update switch indicators
        for switch_id, indicator in self.switch_indicators.items():
            if switch_id in switch_states:
                indicator.set_state(switch_states[switch_id], has_errors)
        
        # Extract additional info from parsed message
        timestamp_field = parsed_message.get_field_by_name("Timestamp")
        if timestamp_field:
            self.last_timestamp = timestamp_field.value
        
        operational_field = parsed_message.get_field_by_name("Operational State")
        if operational_field:
            self.operational_state = operational_field.value
        
        # Log parsed info
        active_switches = [self.SWITCH_DISPLAY_NAMES[switch_id] for switch_id in self.SWITCH_DEFINITIONS.keys() 
                          if switch_states.get(switch_id, False)]
        
        if active_switches:
            self.log_console(f"🟢 Active: {', '.join(active_switches)}", "info")
        else:
            self.log_console("⚫ No switches active", "info")
        
        self.update_info_display()
    
    def update_info_display(self):
        """Update the information display panel."""
        info_widget = self.query_one("#info_display", Static)
        
        # Calculate uptime
        uptime_str = "No messages" if self.last_message_time is None else f"{(datetime.now() - self.last_message_time).total_seconds():.1f}s ago"
        
        # Create info table
        table = Table.grid(padding=(0, 2))
        table.add_column("Label", style="bold cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Messages:", str(self.message_count))
        table.add_row("Errors:", str(self.error_count))
        table.add_row("Last Message:", uptime_str)
        table.add_row("State:", self.operational_state)
        
        if self.last_timestamp is not None:
            table.add_row("Timestamp:", f"0x{self.last_timestamp:08X}")
        
        info_widget.update(table)
    
    def log_console(self, message: str, level: str = "info"):
        """Log a message to the console."""
        try:
            console = self.query_one("#console_log", MessageConsole)
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Color coding based on level
            colors = {
                "info": "cyan",
                "rx": "green", 
                "tx": "yellow",
                "error": "red",
                "warning": "orange1"
            }
            
            color = colors.get(level, "white")
            formatted_message = Text.assemble(
                f"[{timestamp}] ",
                (message, color)
            )
            
            console.write(formatted_message)
        except Exception as e:
            logger.error(f"Failed to log console message: {e}")
    
    def action_toggle_console(self) -> None:
        """Toggle message console visibility."""
        console_container = self.query_one("#message_console", Container)
        dashboard_container = self.query_one("#switch_dashboard", Container)
        
        if self.console_visible:
            console_container.display = False
            dashboard_container.styles.height = "100%"
            self.console_visible = False
            self.log_console("Console hidden (F6 to show)", "info")
        else:
            console_container.display = True
            dashboard_container.styles.height = "60%"
            self.console_visible = True
            self.log_console("Console restored", "info")
    
    def action_clear_console(self) -> None:
        """Clear the message console."""
        try:
            console = self.query_one("#console_log", MessageConsole)
            console.clear()
            self.log_console("Console cleared", "info")
        except Exception as e:
            logger.error(f"Failed to clear console: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "query_button":
            self.send_query_packet()
    
    def send_query_packet(self) -> None:
        """Send a query packet to request switch states."""
        # Construct the query packet
        # CAN ID: 0x505
        # Data: [0xA5, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, CRC8]
        query_data = [0xA5, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        crc = self.calculate_crc8(query_data)
        query_data.append(crc)
        
        # Format the command in firmware protocol format: send:ID:DATA
        data_str = ','.join(f'{b:02X}' for b in query_data)
        command = f"send:505:{data_str}"
        
        self.log_console(f"📤 Sending query: {command}", "tx")
        
        # Send via callback if available
        if self.send_command_callback:
            try:
                # If callback is async, schedule it
                if asyncio.iscoroutinefunction(self.send_command_callback):
                    # Get the app instance and use call_later to run async
                    async def handle_query_response():
                        try:
                            await self.send_command_callback(command)
                            self.log_console("✅ Query sent successfully", "info")
                        except Exception as e:
                            self.log_console(f"❌ Failed to send query: {e}", "error")
                    
                    self.app.call_later(handle_query_response)
                else:
                    self.send_command_callback(command)
                    self.log_console("✅ Query sent successfully", "info")
            except Exception as e:
                self.log_console(f"❌ Failed to send query: {e}", "error")
        else:
            self.log_console("⚠️ No command callback available", "warning")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get widget statistics."""
        active_switches = sum(1 for indicator in self.switch_indicators.values() 
                            if indicator.switch_state and not indicator.error_state)
        
        return {
            "message_count": self.message_count,
            "error_count": self.error_count,
            "active_switches": active_switches,
            "operational_state": self.operational_state,
            "console_visible": self.console_visible,
            "last_timestamp": self.last_timestamp
        }
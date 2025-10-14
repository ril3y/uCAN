"""
Self-contained Wiring Harness Switch View.

This view provides a complete visualization for wiring harness switch states (0x500)
and system status/temperature monitoring (0x600) with all parsing, validation,
and UI components in a single file for true self-containment.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import logging
import asyncio

from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.widgets import Static, Button, RichLog
from textual.reactive import reactive
from textual.binding import Binding
from rich.text import Text

from .base_view import BaseView, ViewParsedMessage
from ..models.can_message import CANMessage
from ..parsers.base import ParsedMessage
from .view_console import MessageConsole

logger = logging.getLogger(__name__)
logger.error("HARNESS_VIEW: Module loaded - logger initialized")


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


class HarnessSwitchWidget(Container):
    """Complete self-contained switch visualization widget."""
    
    DEFAULT_CSS = """
    HarnessSwitchWidget {
        height: 100%;
        width: 100%;
    }
    
    #switch_dashboard {
        height: 60%;
        border: solid $primary;
        padding: 1;
    }
    
    #bottom_section {
        height: 40%;
        margin-top: 1;
    }
    
    #control_panel {
        width: 25%;
        border: solid $accent;
        padding: 1;
        margin-left: 1;
    }
    
    #query_button {
        width: 100%;
        height: 3;
        margin-bottom: 1;
    }
    
    #status_display {
        width: 100%;
        height: 3;
        border: solid $accent;
        padding: 0 1;
        text-align: center;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    
    #temperature_display {
        width: 100%;
        height: 4;
        border: solid $accent;
        padding: 0 1;
        text-align: center;
        content-align: center middle;
        text-style: bold;
    }
    
    .temp-normal {
        background: $success;
        color: white;
        text-style: bold;
    }
    
    .temp-warm {
        background: $warning;
        color: black;
        text-style: bold;
    }
    
    .temp-hot {
        background: $error;
        color: white;
        text-style: bold;
    }
    
    .temp-unknown {
        background: $surface;
        color: $text-muted;
        text-style: bold;
    }
    
    .status-ok {
        background: $success;
        color: white;
        text-style: bold;
    }
    
    .status-error {
        background: $error;
        color: white;
        text-style: bold;
    }
    
    .status-unknown {
        background: $surface;
        color: $text-muted;
        text-style: bold;
    }
    
    #switch_grid {
        grid-size: 3 2;
        grid-gutter: 1 1;
        height: auto;
        min-height: 18;
        margin: 1 0;
        align: center middle;
    }
    
    
    
    #message_console {
        width: 75%;
        border: solid $accent;
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
    
    def __init__(self, supported_can_ids: Optional[List[int]] = None, send_command_callback=None, toast_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.switch_indicators: Dict[int, SwitchIndicator] = {}
        self.last_message_time: Optional[datetime] = None
        self.message_count = 0
        self.error_count = 0
        self.console_visible = True
        self.last_timestamp = None
        self.operational_state = "UNKNOWN"
        self.supported_can_ids = supported_can_ids or [0x500, 0x600]  # Support both switch and heartbeat
        self.send_command_callback = send_command_callback  # Callback to send CAN commands
        self.toast_manager = toast_manager  # Toast manager for notifications
        
        # System status from heartbeat (0x600)
        self.system_status = "UNKNOWN"
        self.system_errors = 0
        self.temperature_c = None
        self.last_heartbeat_time: Optional[datetime] = None
        self.console_line_count = 0  # For alternating line colors
        
    def compose(self) -> ComposeResult:
        """Compose the switch view widget."""
        # Main dashboard area
        with Container(id="switch_dashboard"):
            yield Static("🔌 Wiring Harness Switch Dashboard", classes="dashboard-title")
            
            # Switch grid - only show active switches (0-4)
            with Grid(id="switch_grid"):
                for switch_id in range(5):  # Only bits 0-4 are used
                    display_name = self.SWITCH_DISPLAY_NAMES[switch_id]
                    indicator = SwitchIndicator(display_name, id=f"switch_{switch_id}")
                    self.switch_indicators[switch_id] = indicator
                    yield indicator
            
            # Info panel - removed empty blue box
        
        # Bottom section with console and controls
        with Horizontal(id="bottom_section"):
            # Message console
            with Container(id="message_console"):
                yield Static("📝 Message Console", id="console_header")
                yield MessageConsole(id="console_log")
            
            # Control panel on the right
            with Container(id="control_panel"):
                yield Button("🔄 Query Switch States", id="query_button", variant="primary")
                yield Static("", id="status_display")
                yield Static("", id="temperature_display")
    
    def on_mount(self) -> None:
        """Initialize the widget after mounting."""
        self.update_status_display()
        self.update_temperature_display()
        # Initialization complete - console ready for messages
    
    def update_temperature_display(self):
        """Update the temperature display in the control bar."""
        try:
            temp_widget = self.query_one("#temperature_display", Static)
            
            if self.temperature_c is not None:
                # Convert to Fahrenheit
                temp_f = (self.temperature_c * 9/5) + 32
                
                # Create temperature display text
                temp_text = f"🌡️ {self.temperature_c}°C / {temp_f:.1f}°F"
                
                # Remove existing temperature classes
                temp_widget.remove_class("temp-normal", "temp-warm", "temp-hot", "temp-unknown")
                
                # Color coding based on temperature
                if self.temperature_c > 60:  # > 140°F - Hot
                    temp_widget.add_class("temp-hot")
                elif self.temperature_c > 45:  # > 113°F - Warm  
                    temp_widget.add_class("temp-warm")
                elif self.temperature_c >= 0:  # Normal operating range
                    temp_widget.add_class("temp-normal")
                else:  # Below freezing
                    temp_widget.add_class("temp-hot")  # Use hot color for extreme cold too
                
                temp_widget.update(temp_text)
            else:
                # No temperature data
                temp_widget.remove_class("temp-normal", "temp-warm", "temp-hot", "temp-unknown")
                temp_widget.add_class("temp-unknown")
                temp_widget.update("🌡️ No Temperature Data")
                
        except Exception as e:
            logger.error(f"Failed to update temperature display: {e}")
    
    def update_status_display(self):
        """Update the status display in the control bar."""
        try:
            status_widget = self.query_one("#status_display", Static)
            
            if self.system_status != "UNKNOWN":
                # Parse the status value
                if self.system_status == "0x01":
                    status_text = "✅ Status: OK"
                    status_widget.remove_class("status-error", "status-unknown")
                    status_widget.add_class("status-ok")
                elif self.system_status == "0x00":
                    status_text = "❌ Status: ERROR"
                    status_widget.remove_class("status-ok", "status-unknown")
                    status_widget.add_class("status-error")
                else:
                    status_text = f"⚠️ Status: {self.system_status}"
                    status_widget.remove_class("status-ok", "status-error")
                    status_widget.add_class("status-unknown")
                
                status_widget.update(status_text)
            else:
                # No status data
                status_widget.remove_class("status-ok", "status-error", "status-unknown")
                status_widget.add_class("status-unknown")
                status_widget.update("⚠️ Status: Unknown")
                
        except Exception as e:
            logger.error(f"Failed to update status display: {e}")
    
    def update_switch_states(self, can_message: CANMessage, parsed_message: Optional[Union[ViewParsedMessage, ParsedMessage]]):
        """Update switch states based on a CAN message."""
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
            return
        
        # Extract switch states from parsed message
        switch_states = {}
        has_errors = False
        
        for field in parsed_message.fields:
            # Look for individual switch fields - match against parser's naming convention
            for switch_id, switch_name in self.SWITCH_DEFINITIONS.items():
                # Handle both ViewParsedMessage and ParsedMessage field types
                field_type = getattr(field, 'field_type', '')
                if hasattr(field_type, 'value'):
                    field_type = field_type.value
                
                if field.name == switch_name and field_type == "boolean":
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
        
        # Only log active switches, not when none are active (reduces console noise)
        active_switches = [self.SWITCH_DISPLAY_NAMES[switch_id].replace('\n', ' ') for switch_id in self.SWITCH_DEFINITIONS.keys() 
                          if switch_states.get(switch_id, False)]
        
        if active_switches:
            self.log_console(f"🟢 Active: {', '.join(active_switches)}", "info")
    
    def update_system_status(self, can_message: CANMessage, parsed_message: Optional[Union[ViewParsedMessage, ParsedMessage]]):
        """Update system status based on heartbeat message (CAN ID 0x600)."""
        logger.info(f"UPDATE_SYSTEM_STATUS: Called with CAN ID 0x{can_message.can_id:03X}")
        
        # Only process heartbeat messages
        if can_message.can_id != 0x600:
            logger.info(f"UPDATE_SYSTEM_STATUS: Ignoring non-heartbeat message 0x{can_message.can_id:03X}")
            return
            
        self.last_heartbeat_time = datetime.now()
        logger.info(f"UPDATE_SYSTEM_STATUS: Processing heartbeat message")
        
        # Log the raw heartbeat message
        self.log_console(
            f"HEARTBEAT: ID=0x{can_message.can_id:03X} Data=[{' '.join(f'{b:02X}' for b in can_message.data)}]",
            "info"
        )
        
        # Parse heartbeat data directly from raw bytes if no parsed message
        if len(can_message.data) >= 8:
            # Heartbeat format: [0xAA][status][errors][rx_count][temperature][switches][reserved][CRC8]
            signature = can_message.data[0]
            if signature == 0xAA:
                self.system_status = f"0x{can_message.data[1]:02X}"
                self.system_errors = can_message.data[2]
                # Temperature with +40°C offset (example: 73 - 40 = 33°C)
                temp_raw = can_message.data[4]
                self.temperature_c = temp_raw - 40
                
                # Log successful parsing only if there are changes
                pass  # Removed verbose logging
            else:
                self.log_console(f"❌ Invalid heartbeat signature: 0x{signature:02X} (expected 0xAA)", "error")
        else:
            self.log_console(f"❌ Invalid heartbeat length: {len(can_message.data)} (expected 8)", "error")
        
        # Try to extract from parsed message if available
        if parsed_message and parsed_message.is_valid():
            for field in parsed_message.fields:
                if "status" in field.name.lower():
                    self.system_status = str(field.value)
                elif "temperature" in field.name.lower():
                    self.temperature_c = field.value
                elif "error" in field.name.lower():
                    self.system_errors = field.value
        
        self.update_status_display()
        self.update_temperature_display()
    
    
    def log_console(self, message: str, level: str = "info", force: bool = False):
        """Log a message to the console with alternating line colors."""
        try:
            console = self.query_one("#console_log", MessageConsole)
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Skip verbose messages unless forced
            if not force and level == "info" and any(skip in message.lower() for skip in 
                ["no switches active", "switch dashboard initialized", "console"]):
                return
            
            # Increment line counter for alternating colors
            self.console_line_count += 1
            
            # Color coding based on level with alternating background
            colors = {
                "info": "cyan",
                "rx": "green", 
                "tx": "yellow",
                "error": "red",
                "warning": "orange1"
            }
            
            color = colors.get(level, "white")
            
            # Alternating background colors for better readability
            if self.console_line_count % 2 == 0:
                # Even lines - slightly darker background
                bg_style = "on grey11"
            else:
                # Odd lines - normal background
                bg_style = ""
            
            # Combine color and background
            full_style = f"{color} {bg_style}".strip()
            
            formatted_message = Text.assemble(
                (f"[{timestamp}] {message}", full_style)
            )
            
            console.write(formatted_message)
        except Exception as e:
            logger.error(f"Failed to log console message: {e}")
    
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
                            if self.toast_manager:
                                self.toast_manager.success("Switch state query sent")
                        except Exception as e:
                            self.log_console(f"❌ Failed to send query: {e}", "error")
                            if self.toast_manager:
                                self.toast_manager.error(f"Query failed: {e}")
                    
                    self.app.call_later(handle_query_response)
                else:
                    self.send_command_callback(command)
                    self.log_console("✅ Query sent successfully", "info")
                    if self.toast_manager:
                        self.toast_manager.success("Switch state query sent")
            except Exception as e:
                self.log_console(f"❌ Failed to send query: {e}", "error")
                if self.toast_manager:
                    self.toast_manager.error(f"Query failed: {e}")
        else:
            self.log_console("⚠️ No command callback available", "warning")
            if self.toast_manager:
                self.toast_manager.warning("No connection available for sending commands")
    
    @staticmethod
    def calculate_crc8(data: List[int]) -> int:
        """Calculate CRC8 checksum for the given data."""
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
    
    def action_toggle_console(self) -> None:
        """Toggle message console visibility."""
        console_container = self.query_one("#message_console", Container)
        dashboard_container = self.query_one("#switch_dashboard", Container)
        
        if self.console_visible:
            console_container.display = False
            dashboard_container.styles.height = "100%"
            self.console_visible = False
        else:
            console_container.display = True
            dashboard_container.styles.height = "60%"
            self.console_visible = True
    
    def action_clear_console(self) -> None:
        """Clear the message console."""
        try:
            console = self.query_one("#console_log", MessageConsole)
            console.clear()
            self.console_line_count = 0  # Reset line counter for alternating colors
        except Exception as e:
            logger.error(f"Failed to clear console: {e}")
    
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
            "last_timestamp": self.last_timestamp,
            # System status info from heartbeat (0x600)
            "system_status": self.system_status,
            "temperature_c": self.temperature_c,
            "system_errors": self.system_errors,
            "last_heartbeat": self.last_heartbeat_time.isoformat() if self.last_heartbeat_time else None
        }


class HarnessSwitchView(BaseView):
    """
    View for visualizing wiring harness switch states from CAN ID 0x500.
    
    This view displays switch states as visual indicators in a grid layout
    with real-time updates when switch state messages are received.
    """
    
    def __init__(self):
        super().__init__()
        logger.error("HARNESS_VIEW: __init__() called - view instantiated")
    
    def get_view_name(self) -> str:
        """Return the human-readable name of this view."""
        logger.error("HARNESS_VIEW: get_view_name() called")
        return "Harness Switch View"
    
    def get_description(self) -> str:
        """Return a description of what this view displays."""
        return "Visual dashboard showing wiring harness switch states and system status (0x500, 0x600)"
    
    def get_supported_can_ids(self) -> List[int]:
        """Return CAN IDs this view supports."""
        return [0x500, 0x600]
    
    def get_widget_class(self):
        """Return the widget class for this view."""
        return HarnessSwitchWidget
    
    def create_widget(self, send_command_callback=None, toast_manager=None, **kwargs):
        """Create self-contained widget instance."""
        logger.error("HARNESS_VIEW: create_widget() called")
        widget = HarnessSwitchWidget(
            supported_can_ids=self.get_supported_can_ids(), 
            send_command_callback=send_command_callback,
            toast_manager=toast_manager,
            **kwargs
        )
        logger.error("HARNESS_VIEW: widget created successfully")
        return widget
    
    def get_priority(self) -> int:
        """Highest priority for switch messages."""
        logger.error("HARNESS_VIEW: get_priority() called - returning 100")
        return 100
    
    def parse_message(self, can_message: CANMessage) -> Optional[ViewParsedMessage]:
        """
        Parse CAN messages for switch states (0x500) and heartbeat (0x600).
        
        Args:
            can_message: Raw CAN message
            
        Returns:
            ViewParsedMessage with parsed data, or None if not supported
        """
        # Only handle our supported CAN IDs
        if can_message.can_id not in [0x500, 0x600]:
            return None
            
        # Verify message length
        if len(can_message.data) != 8:
            parsed = ViewParsedMessage(can_message.can_id, can_message.data)
            parsed.add_error(f"Invalid message length: {len(can_message.data)} (expected 8)")
            return parsed
        
        if can_message.can_id == 0x500:
            return self._parse_switch_message(can_message)
        elif can_message.can_id == 0x600:
            return self._parse_heartbeat_message(can_message)
        
        return None
    
    def _parse_switch_message(self, can_message: CANMessage) -> ViewParsedMessage:
        """
        Parse switch state message (CAN ID 0x500).
        
        Format: [0x5A][switch bitmap][timestamp 4 bytes][0x00][0xFF]
        """
        parsed = ViewParsedMessage(can_message.can_id, can_message.data)
        parsed.parser_name = "harness_switch_parser"
        
        data = can_message.data
        
        # Verify signature bytes
        if data[0] != 0x5A:
            parsed.add_error(f"Invalid signature: 0x{data[0]:02X} (expected 0x5A)")
        
        if data[7] != 0xFF:
            parsed.add_error(f"Invalid end marker: 0x{data[7]:02X} (expected 0xFF)")
        
        # Parse switch bitmap (byte 1)
        switch_bitmap = data[1]
        
        # Individual switch states based on bit positions
        parsed.add_field("Brake Switch", bool(switch_bitmap & 0x01), "boolean")
        parsed.add_field("Eco Switch", bool(switch_bitmap & 0x02), "boolean") 
        parsed.add_field("Reverse Switch", bool(switch_bitmap & 0x04), "boolean")
        parsed.add_field("Foot Switch", bool(switch_bitmap & 0x08), "boolean")
        parsed.add_field("Forward Switch", bool(switch_bitmap & 0x10), "boolean")
        
        # Parse timestamp (bytes 2-5, little endian)
        timestamp = (data[2] | (data[3] << 8) | (data[4] << 16) | (data[5] << 24))
        parsed.add_field("Timestamp", timestamp, "integer")
        
        # Add raw bitmap for reference
        parsed.add_field("Switch Bitmap", f"0x{switch_bitmap:02X}", "hex")
        parsed.add_field("Operational State", "NORMAL", "string")
        
        return parsed
    
    def _parse_heartbeat_message(self, can_message: CANMessage) -> ViewParsedMessage:
        """
        Parse heartbeat message (CAN ID 0x600).
        
        Format: [0xAA][status][errors][rx_count][temperature][switches][reserved][CRC8]
        """
        parsed = ViewParsedMessage(can_message.can_id, can_message.data)
        parsed.parser_name = "heartbeat_parser"
        
        data = can_message.data
        
        # Verify signature
        if data[0] != 0xAA:
            parsed.add_error(f"Invalid heartbeat signature: 0x{data[0]:02X} (expected 0xAA)")
        
        # Verify CRC8 (last byte)
        message_data = data[0:7]  # All bytes except CRC
        expected_crc = data[7]
        
        if not self.verify_crc8(message_data, expected_crc):
            parsed.add_error(f"CRC8 mismatch: calculated != 0x{expected_crc:02X}")
        
        # Parse fields
        parsed.add_field("System Status", f"0x{data[1]:02X}", "hex")
        parsed.add_field("System Errors", data[2], "integer")
        parsed.add_field("RX Count", data[3], "integer")
        
        # Temperature with -40°C offset
        temperature_c = data[4] - 40
        parsed.add_field("Temperature", temperature_c, "temperature")
        
        # Switch changes (future use)
        parsed.add_field("Switch Changes", data[5], "integer")
        
        # Reserved byte
        parsed.add_field("Reserved", data[6], "integer")
        
        # CRC8 verification result
        parsed.add_field("CRC8 Valid", self.verify_crc8(message_data, expected_crc), "boolean")
        
        return parsed
    
    @staticmethod
    def verify_crc8(data: List[int], expected_crc: int) -> bool:
        """Verify CRC8 checksum for the given data."""
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
        
        return crc == expected_crc

    def can_handle_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> bool:
        """
        Check if this view can handle the message.
        
        This view handles:
        - CAN ID 0x500: Switch state data [0x5A][switch bitmap][timestamp 4 bytes][0x00][0xFF]
        - CAN ID 0x600: Heartbeat data [0xAA][status][errors][rx_count][temperature][switches][reserved][CRC8]
        """
        logger.error(f"VIEW_CHECK: Checking CAN ID {can_message.can_id} (0x{can_message.can_id:03X}) with data {can_message.data}")
        
        # Check CAN ID first  
        if can_message.can_id not in [0x500, 0x600]:
            logger.info(f"VIEW_CHECK: Rejecting CAN ID {can_message.can_id} (0x{can_message.can_id:03X}) - not in supported list [0x500, 0x600]")
            return False
        
        # Verify message has correct length
        if len(can_message.data) != 8:
            logger.info(f"VIEW_CHECK: Rejecting CAN ID 0x{can_message.can_id:03X} (length {len(can_message.data)} != 8)")
            return False
        
        # Check message format based on CAN ID
        if can_message.can_id == 0x500:
            # Switch message: check for expected signature and end marker
            if can_message.data[0] != 0x5A or can_message.data[7] != 0xFF:
                logger.info(f"VIEW_CHECK: Rejecting 0x500 message (invalid signature/marker)")
                return False
        elif can_message.can_id == 0x600:
            # Heartbeat message: check for expected signature (0xAA)
            if can_message.data[0] != 0xAA:
                logger.info(f"VIEW_CHECK: Rejecting 0x600 message (signature 0x{can_message.data[0]:02X} != 0xAA)")
                return False
        
        logger.error(f"VIEW_CHECK: ✅ ACCEPTING CAN ID {can_message.can_id} (0x{can_message.can_id:03X}) - will handle this message")
        
        # If we have parsed data, verify it's from appropriate parser
        if parsed_message:
            parser_name = parsed_message.parser_name.lower()
            if ("switch" in parser_name or "wiring harness" in parser_name or 
                "heartbeat" in parser_name or "system" in parser_name):
                return True
            
            # Check for relevant fields
            for field in parsed_message.fields:
                if ("switch" in field.name.lower() or "temperature" in field.name.lower() or 
                    "status" in field.name.lower()):
                    return True
        
        # If no parsed data, but format matches, we can handle it
        return True
    
    def _forward_to_widget(self, can_message: CANMessage, parsed_data) -> None:
        """Forward message to connected widget with view-specific routing."""
        logger.info(f"WIDGET_FORWARD: Called with CAN ID 0x{can_message.can_id:03X}, widget={self.widget is not None}")
        
        if not self.widget:
            logger.warning(f"WIDGET_FORWARD: No widget available for CAN ID 0x{can_message.can_id:03X}")
            return
            
        try:
            if can_message.can_id == 0x500:
                # Switch state message
                logger.info(f"WIDGET_FORWARD: Forwarding switch message to widget: 0x{can_message.can_id:03X}")
                self.widget.update_switch_states(can_message, parsed_data)
            elif can_message.can_id == 0x600:
                # Heartbeat message  
                logger.info(f"WIDGET_FORWARD: Forwarding heartbeat message to widget: 0x{can_message.can_id:03X}")
                self.widget.update_system_status(can_message, parsed_data)
            else:
                logger.warning(f"WIDGET_FORWARD: Unhandled CAN ID 0x{can_message.can_id:03X}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"WIDGET_FORWARD: Error updating widget: {e}")
            self.error_count += 1
    
    def get_stats(self) -> dict:
        """Get detailed statistics for this view."""
        base_stats = super().get_stats()
        
        # Add widget stats if available
        widget_stats = {}
        if self.widget and hasattr(self.widget, 'get_stats'):
            try:
                widget_stats = self.widget.get_stats()
            except Exception:
                pass
        
        return {
            **base_stats,
            "view_type": "Harness Switch Dashboard",
            "widget_stats": widget_stats,
            "can_message_format": "0x5A + switch_bitmap + timestamp(4) + 0x00 + 0xFF"
        }
    
    def reset(self) -> None:
        """Reset view and widget state."""
        super().reset()
        # Widget will handle its own reset if needed
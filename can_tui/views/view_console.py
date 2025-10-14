"""
Console view - Traditional scrolling message display.

This is the default view that shows all CAN messages in a scrolling console format,
similar to the original message log functionality.
"""

from typing import List, Optional
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, RichLog
from textual.app import ComposeResult
from rich.text import Text

from .base_view import BaseView, ViewParsedMessage
from ..models.can_message import CANMessage, MessageFilter, MessageStats
from ..parsers.base import ParsedMessage
from ..widgets.toast import toast_manager
from ..widgets.sidebar import Sidebar


class MessageConsole(RichLog):
    """Enhanced console widget with filtering and export capabilities."""
    
    DEFAULT_CSS = """
    MessageConsole {
        height: 1fr;
        border: solid $accent;
        padding: 1;
    }
    """
    
    def __init__(self, max_lines: int = 1000, **kwargs):
        super().__init__(max_lines=max_lines, **kwargs)
        self.markup = True
        self.highlight = True
        self.auto_scroll = True


class ConsoleWidget(Container):
    """Main console widget with sidebar integration."""
    
    DEFAULT_CSS = """
    ConsoleWidget {
        height: 100%;
        width: 100%;
    }
    
    #console_layout {
        height: 100%;
        width: 100%;
    }
    
    #console_main {
        height: 100%;
        width: 75%;
    }
    
    #console_header {
        height: 3;
        width: 100%;
        background: $surface;
        text-align: center;
        content-align: center middle;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    #console_sidebar {
        width: 25%;
        height: 100%;
    }
    """
    
    def __init__(self, supported_can_ids: Optional[List[int]] = None, toast_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.supported_can_ids = supported_can_ids or []
        self.message_count = 0
        self.toast_manager = toast_manager
        self.stats = MessageStats()
        
        # Create sidebar with message filter
        self.sidebar = Sidebar()
        self.sidebar.set_filter_changed_callback(self._on_filter_changed)
        
        # Set up action callbacks
        self.sidebar.set_action_callback("clear", self.clear_console)
        self.sidebar.set_action_callback("save", self._save_log)
        self.sidebar.set_action_callback("pause", self._toggle_pause)
        self.sidebar.set_action_callback("settings", self._show_settings)
        self.sidebar.set_action_callback("reconnect", self._reconnect)
        
        self.paused = False
    
    def compose(self) -> ComposeResult:
        """Compose the console widget with sidebar."""
        with Horizontal(id="console_layout"):
            # Main console area (75% width)
            with Container(id="console_main"):
                yield Static("📝 CAN Message Console", id="console_header")
                yield MessageConsole(id="console_log")
            
            # Sidebar on the right (25% width)
            with Container(id="console_sidebar"):
                yield self.sidebar
    
    def _on_filter_changed(self, message_filter: MessageFilter) -> None:
        """Handle filter changes from sidebar."""
        active_filters = message_filter.get_active_filters()
        if active_filters:
            filter_str = ", ".join(active_filters)
            if self.toast_manager:
                self.toast_manager.info(f"Active filters: {filter_str}")
    
    def _save_log(self) -> None:
        """Save console log to file."""
        if self.toast_manager:
            self.toast_manager.info("Log save not yet implemented")
    
    def _toggle_pause(self) -> None:
        """Toggle message display pause."""
        self.paused = not self.paused
        status = "paused" if self.paused else "resumed"
        if self.toast_manager:
            self.toast_manager.info(f"Console {status}")
    
    def _show_settings(self) -> None:
        """Show settings modal."""
        if self.toast_manager:
            self.toast_manager.info("Settings modal not yet implemented")
    
    def _reconnect(self) -> None:
        """Attempt to reconnect to device."""
        if self.toast_manager:
            self.toast_manager.info("Reconnect not yet implemented")
    
    def set_connection_status(self, status: str, port: str = "None", device_info: str = "No device") -> None:
        """Update connection status in sidebar."""
        self.sidebar.set_connection_status(status, port, device_info)
    
    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message to the console."""
        if self.paused:
            return
            
        try:
            console = self.query_one("#console_log", MessageConsole)
            
            # Color coding based on level
            colors = {
                "info": "cyan",
                "rx": "green", 
                "tx": "yellow",
                "error": "red",
                "warning": "orange1"
            }
            
            color = colors.get(level, "white")
            formatted_message = Text(message, style=color)
            console.write(formatted_message)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log console message: {e}")
    
    def update_message_data(self, can_message: CANMessage, parsed_data) -> None:
        """Update console with new message data."""
        self.message_count += 1
        
        # Update statistics
        self.stats.update(can_message)
        self.sidebar.update_stats(self.stats)
        
        # Check if message passes filter
        message_filter = self.sidebar.get_message_filter()
        if not message_filter.matches(can_message):
            return
        
        # Format and display the message
        display_text = can_message.format_for_display()
        level = can_message.type.value.lower()
        self.log_message(display_text, level)
        
        # If we have parsed data, show additional info
        if parsed_data and hasattr(parsed_data, 'fields'):
            for field in parsed_data.fields:
                if field.field_type == "boolean" and field.value:
                    self.log_message(f"  └─ {field.name}: {field.value}", "info")
    
    def clear_console(self) -> None:
        """Clear the console display."""
        try:
            console = self.query_one("#console_log", MessageConsole)
            console.clear()
            self.log_message("Console cleared", "info")
            if self.toast_manager:
                self.toast_manager.success("Console cleared")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to clear console: {e}")
            if self.toast_manager:
                self.toast_manager.error(f"Failed to clear console: {e}")


class ConsoleView(BaseView):
    """
    Console view providing traditional scrolling message display.
    
    This view shows all CAN messages in a console format with filtering
    and basic message information display.
    """
    
    def get_view_name(self) -> str:
        """Return the human-readable name of this view."""
        return "Console View"
    
    def get_description(self) -> str:
        """Return a description of what this view displays."""
        return "Traditional scrolling console display for all CAN messages"
    
    def get_supported_can_ids(self) -> List[int]:
        """Return CAN IDs this view supports (all CAN IDs)."""
        # Return all possible standard 11-bit CAN IDs (0x000 to 0x7FF)
        return list(range(0x000, 0x800))
    
    def create_widget(self, send_command_callback=None, toast_manager=None, **kwargs):
        """Create console widget with sidebar integration."""
        return ConsoleWidget(
            supported_can_ids=self.get_supported_can_ids(),
            toast_manager=toast_manager,
            **kwargs
        )
    
    def get_priority(self) -> int:
        """Low priority - console is a catch-all view."""
        return 1
    
    def can_handle_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> bool:
        """Console view can handle any message."""
        return True
    
    def parse_message(self, can_message: CANMessage) -> Optional[ViewParsedMessage]:
        """
        Console view uses default parsing for all messages.
        
        This provides basic field extraction for any CAN message.
        """
        return self.create_default_parsed_message(can_message)
    
    def _forward_to_widget(self, can_message: CANMessage, parsed_data) -> None:
        """Forward message to console widget."""
        if self.widget and hasattr(self.widget, 'update_message_data'):
            self.widget.update_message_data(can_message, parsed_data)
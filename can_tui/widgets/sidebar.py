"""
Sidebar widget providing connection status, filters, and controls.

This reusable widget combines connection status, message filtering,
statistics display, and common action buttons.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Checkbox, Label, Input
from textual.reactive import reactive
from textual.binding import Binding
from rich.text import Text
from rich.table import Table
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import logging

from ..models.can_message import MessageFilter, MessageStats
from ..widgets.toast import toast_manager

logger = logging.getLogger(__name__)


class ConnectionStatusPanel(Container):
    """Panel showing connection status and device information."""
    
    DEFAULT_CSS = """
    ConnectionStatusPanel {
        height: 6;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }
    
    .status-connected {
        color: $success;
    }
    
    .status-disconnected {
        color: $error;
    }
    
    .status-connecting {
        color: $warning;
    }
    """
    
    connection_status = reactive("Disconnected")
    device_port = reactive("None")
    device_info = reactive("No device")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def compose(self) -> ComposeResult:
        """Compose connection status display."""
        yield Static("🔌 Connection Status", classes="panel-title")
        yield Static("", id="connection_display")
    
    def watch_connection_status(self, status: str) -> None:
        """Update connection status display."""
        self.update_display()
    
    def watch_device_port(self, port: str) -> None:
        """Update device port display."""
        self.update_display()
    
    def watch_device_info(self, info: str) -> None:
        """Update device info display."""
        self.update_display()
    
    def update_display(self) -> None:
        """Update the connection status display."""
        try:
            display = self.query_one("#connection_display", Static)
            
            # Choose status color and emoji
            if self.connection_status == "Connected":
                status_class = "status-connected"
                emoji = "🟢"
            elif self.connection_status == "Connecting":
                status_class = "status-connecting"
                emoji = "🟡"
            else:
                status_class = "status-disconnected"
                emoji = "🔴"
            
            # Create status text
            status_text = Text()
            status_text.append(f"{emoji} ", style="white")
            status_text.append(self.connection_status, style=status_class)
            status_text.append(f"\nPort: {self.device_port}", style="cyan")
            status_text.append(f"\nDevice: {self.device_info}", style="dim")
            
            display.update(status_text)
        except Exception as e:
            logger.error(f"Failed to update connection display: {e}")
    
    def set_status(self, status: str, port: str = "None", device_info: str = "No device") -> None:
        """Set connection status information."""
        self.connection_status = status
        self.device_port = port
        self.device_info = device_info


class MessageFilterPanel(Container):
    """Panel for message type and CAN ID filtering."""
    
    DEFAULT_CSS = """
    MessageFilterPanel {
        height: auto;
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
    }
    
    MessageFilterPanel Checkbox {
        margin: 0 1;
    }
    
    MessageFilterPanel Input {
        margin: 1 0;
        height: 3;
    }
    
    .filter-checkboxes {
        height: auto;
        margin: 1 0;
    }
    
    .id-filter-section {
        height: auto;
        margin: 1 0;
    }
    """
    
    def __init__(self, message_filter: Optional[MessageFilter] = None, **kwargs):
        super().__init__(**kwargs)
        self.message_filter = message_filter or MessageFilter()
        self.filter_changed_callback: Optional[Callable] = None
    
    def compose(self) -> ComposeResult:
        """Compose filter controls."""
        yield Static("🎯 Message Filters", classes="panel-title")
        
        with Container(classes="filter-checkboxes"):
            yield Checkbox("RX Messages", id="filter_rx", value=self.message_filter.show_rx)
            yield Checkbox("TX Messages", id="filter_tx", value=self.message_filter.show_tx)
            yield Checkbox("Error Messages", id="filter_errors", value=self.message_filter.show_errors)
            yield Checkbox("Info Messages", id="filter_info", value=self.message_filter.show_info)
        
        with Container(classes="id-filter-section"):
            yield Static("CAN ID Filter (hex):", classes="input-label")
            yield Input(placeholder="0x500,0x600", id="id_filter_input")
            with Horizontal():
                yield Button("Add", id="add_filter", variant="primary")
                yield Button("Clear", id="clear_filters", variant="warning")
    
    def set_filter_changed_callback(self, callback: Callable) -> None:
        """Set callback for when filters change."""
        self.filter_changed_callback = callback
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle filter checkbox changes."""
        if event.checkbox.id == "filter_rx":
            self.message_filter.show_rx = event.value
        elif event.checkbox.id == "filter_tx":
            self.message_filter.show_tx = event.value
        elif event.checkbox.id == "filter_errors":
            self.message_filter.show_errors = event.value
        elif event.checkbox.id == "filter_info":
            self.message_filter.show_info = event.value
        
        # Notify of filter change
        if self.filter_changed_callback:
            self.filter_changed_callback(self.message_filter)
        
        # Show toast notification
        filter_name = event.checkbox.label.plain if hasattr(event.checkbox.label, 'plain') else str(event.checkbox.id)
        status = "enabled" if event.value else "disabled"
        toast_manager.info(f"Filter {filter_name} {status}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "add_filter":
            self._add_id_filter()
        elif event.button.id == "clear_filters":
            self._clear_all_filters()
    
    def _add_id_filter(self) -> None:
        """Add CAN ID filters from input."""
        try:
            input_widget = self.query_one("#id_filter_input", Input)
            input_text = input_widget.value.strip()
            
            if not input_text:
                toast_manager.warning("Enter CAN IDs to filter (e.g., 0x500,0x600)")
                return
            
            # Parse comma-separated CAN IDs
            added_count = 0
            for id_str in input_text.split(','):
                id_str = id_str.strip()
                if id_str:
                    try:
                        if id_str.startswith('0x'):
                            can_id = int(id_str, 16)
                        else:
                            can_id = int(id_str)
                        
                        if self.message_filter.add_id_filter(can_id):
                            added_count += 1
                    except ValueError:
                        toast_manager.error(f"Invalid CAN ID format: {id_str}")
            
            if added_count > 0:
                # Notify of filter change
                if self.filter_changed_callback:
                    self.filter_changed_callback(self.message_filter)
                
                ids_str = ", ".join(f"0x{id:03X}" for id in self.message_filter.id_filters[-added_count:])
                toast_manager.success(f"Added ID filters: {ids_str}")
                input_widget.value = ""  # Clear input
            else:
                toast_manager.info("No new filters added")
                
        except Exception as e:
            toast_manager.error(f"Failed to add filter: {e}")
    
    def _clear_all_filters(self) -> None:
        """Clear all ID filters."""
        if self.message_filter.has_id_filters():
            self.message_filter.clear_id_filters()
            
            # Notify of filter change
            if self.filter_changed_callback:
                self.filter_changed_callback(self.message_filter)
            
            toast_manager.info("All ID filters cleared")
        else:
            toast_manager.info("No ID filters to clear")


class StatsPanel(Container):
    """Panel showing message statistics."""
    
    DEFAULT_CSS = """
    StatsPanel {
        height: auto;
        border: solid $secondary;
        padding: 1;
        margin-bottom: 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stats = MessageStats()
    
    def compose(self) -> ComposeResult:
        """Compose statistics display."""
        yield Static("📊 Statistics", classes="panel-title")
        yield Static("", id="stats_display")
    
    def update_stats(self, stats: MessageStats) -> None:
        """Update statistics display."""
        self.stats = stats
        self._refresh_display()
    
    def _refresh_display(self) -> None:
        """Refresh the statistics display."""
        try:
            display = self.query_one("#stats_display", Static)
            
            # Create stats table
            table = Table.grid(padding=(0, 1))
            table.add_column("Label", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("RX:", str(self.stats.rx_count))
            table.add_row("TX:", str(self.stats.tx_count))
            table.add_row("Errors:", str(self.stats.error_count))
            table.add_row("Rate:", f"{self.stats.get_rate():.1f}/s")
            
            display.update(table)
        except Exception as e:
            logger.error(f"Failed to update stats display: {e}")


class ActionPanel(Container):
    """Panel with action buttons for save, pause, settings, etc."""
    
    DEFAULT_CSS = """
    ActionPanel {
        height: auto;
        border: solid $success;
        padding: 1;
    }
    
    ActionPanel Button {
        width: 100%;
        margin: 1 0;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.action_callbacks: Dict[str, Callable] = {}
    
    def compose(self) -> ComposeResult:
        """Compose action buttons."""
        yield Static("⚡ Actions", classes="panel-title")
        yield Button("💾 Save Log", id="action_save", variant="success")
        yield Button("⏸️ Pause", id="action_pause", variant="warning")
        yield Button("🗑️ Clear", id="action_clear", variant="error")
        yield Button("⚙️ Settings", id="action_settings", variant="primary")
        yield Button("🔌 Reconnect", id="action_reconnect", variant="default")
    
    def set_action_callback(self, action: str, callback: Callable) -> None:
        """Set callback for an action."""
        self.action_callbacks[action] = callback
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle action button presses."""
        action_map = {
            "action_save": "save",
            "action_pause": "pause", 
            "action_clear": "clear",
            "action_settings": "settings",
            "action_reconnect": "reconnect"
        }
        
        action = action_map.get(event.button.id)
        if action and action in self.action_callbacks:
            try:
                self.action_callbacks[action]()
            except Exception as e:
                toast_manager.error(f"Action {action} failed: {e}")
        elif action:
            toast_manager.info(f"Action '{action}' not implemented")


class Sidebar(Container):
    """
    Complete sidebar widget combining all panels.
    
    This widget provides connection status, message filtering, statistics,
    and action buttons in a unified sidebar layout.
    """
    
    DEFAULT_CSS = """
    Sidebar {
        dock: right;
        width: 40;
        height: 100%;
        background: $surface;
        border-left: solid $primary;
        padding: 1;
    }
    
    Sidebar .panel-title {
        text-style: bold;
        color: $accent;
        text-align: center;
        margin-bottom: 1;
    }
    """
    
    def __init__(self, message_filter: Optional[MessageFilter] = None, **kwargs):
        super().__init__(**kwargs)
        self.message_filter = message_filter or MessageFilter()
        self.stats = MessageStats()
        
        # Create panels
        self.connection_panel = ConnectionStatusPanel()
        self.filter_panel = MessageFilterPanel(self.message_filter)
        self.stats_panel = StatsPanel()
        self.action_panel = ActionPanel()
    
    def compose(self) -> ComposeResult:
        """Compose the complete sidebar."""
        with Vertical():
            yield self.connection_panel
            yield self.filter_panel
            yield self.stats_panel
            yield self.action_panel
    
    def set_connection_status(self, status: str, port: str = "None", device_info: str = "No device") -> None:
        """Update connection status."""
        self.connection_panel.set_status(status, port, device_info)
    
    def update_stats(self, stats: MessageStats) -> None:
        """Update statistics display."""
        self.stats = stats
        self.stats_panel.update_stats(stats)
    
    def set_filter_changed_callback(self, callback: Callable) -> None:
        """Set callback for when filters change."""
        self.filter_panel.set_filter_changed_callback(callback)
    
    def set_action_callback(self, action: str, callback: Callable) -> None:
        """Set callback for an action."""
        self.action_panel.set_action_callback(action, callback)
    
    def get_message_filter(self) -> MessageFilter:
        """Get the current message filter."""
        return self.message_filter
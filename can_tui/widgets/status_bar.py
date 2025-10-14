"""
Custom status bar widget for CAN Bridge TUI.

Displays connection status, message counts, and keyboard shortcuts.
"""

from textual.widgets import Static
from textual.containers import Horizontal
from textual.reactive import reactive
from rich.text import Text
from typing import Optional
from datetime import datetime


class StatusBarWidget(Horizontal):
    """Custom status bar widget replacing the default Footer."""
    
    DEFAULT_CSS = """
    StatusBarWidget {
        height: 1;
        background: $primary-darken-2;
        color: $text;
        dock: bottom;
        padding: 0 1;
    }
    
    StatusBarWidget > Static {
        height: 1;
        background: transparent;
        text-align: center;
        content-align: center middle;
    }
    
    #status_left {
        text-align: left;
        width: 1fr;
    }
    
    #status_center {
        text-align: center;
        width: 2fr;
    }
    
    #status_right {
        text-align: right;
        width: 1fr;
    }
    """
    
    # Reactive properties
    connection_status = reactive("Disconnected", init=False)
    port_name = reactive("", init=False)
    message_count = reactive(0, init=False)
    error_count = reactive(0, init=False)
    last_activity = reactive(None, init=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def compose(self):
        """Compose the status bar layout."""
        yield Static("", id="status_left")
        yield Static("", id="status_center") 
        yield Static("", id="status_right")
    
    def on_mount(self) -> None:
        """Initialize status bar on mount."""
        self.update_display()
    
    def watch_connection_status(self, old_value: str, new_value: str) -> None:
        """React to connection status changes."""
        self.update_display()
    
    def watch_message_count(self, old_value: int, new_value: int) -> None:
        """React to message count changes."""
        self.update_display()
    
    def watch_error_count(self, old_value: int, new_value: int) -> None:
        """React to error count changes."""
        self.update_display()
    
    def update_connection_status(self, status: str, port: Optional[str] = None) -> None:
        """Update connection status."""
        self.connection_status = status
        if port:
            self.port_name = port
        self.update_display()
    
    def update_message_stats(self, messages: int, errors: int = 0) -> None:
        """Update message and error counts."""
        self.message_count = messages
        self.error_count = errors
        self.last_activity = datetime.now()
        self.update_display()
    
    def update_display(self) -> None:
        """Update the status bar display."""
        try:
            # Left section: Connection status
            left_widget = self.query_one("#status_left", Static)
            
            if self.connection_status == "Connected":
                if self.port_name:
                    left_text = f"🟢 {self.port_name}"
                else:
                    left_text = "🟢 Connected"
            elif self.connection_status == "Connecting":
                left_text = "🟡 Connecting..."
            else:
                left_text = "🔴 Disconnected"
            
            left_widget.update(Text(left_text, style="bold"))
            
            # Center section: Message stats
            center_widget = self.query_one("#status_center", Static)
            
            if self.message_count > 0:
                center_text = f"📊 {self.message_count} messages"
                if self.error_count > 0:
                    center_text += f" • ❌ {self.error_count} errors"
                
                # Add activity indicator
                if self.last_activity:
                    time_diff = (datetime.now() - self.last_activity).total_seconds()
                    if time_diff < 2:
                        center_text = f"📡 {center_text}"  # Active indicator
            else:
                center_text = "📊 No messages"
            
            center_widget.update(Text(center_text, style=""))
            
            # Right section: Keyboard shortcuts
            right_widget = self.query_one("#status_right", Static)
            shortcuts_text = "F1:Clear F3:Pause F4:Help F5:Settings"
            right_widget.update(Text(shortcuts_text, style="dim"))
            
        except Exception as e:
            # Silently handle any display errors
            pass
    
    def set_activity_indicator(self, active: bool = True) -> None:
        """Set activity indicator (used for real-time message flow)."""
        if active:
            self.last_activity = datetime.now()
        self.update_display()
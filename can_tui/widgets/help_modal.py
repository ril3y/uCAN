"""Help modal widget for displaying help information."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.binding import Binding


class HelpModal(ModalScreen[bool]):
    """Modal screen for displaying help information."""
    
    CSS = """
    HelpModal {
        align: center middle;
    }
    
    #help_dialog {
        width: 80;
        height: 25;
        border: thick $background 80%;
        background: $surface;
        padding: 1;
    }
    
    #help_content {
        height: 1fr;
        overflow: auto;
        padding: 1;
        background: $background;
        border: solid $primary;
    }
    
    #help_buttons {
        height: 3;
        align: center middle;
        margin: 1 0;
    }
    
    .help_section {
        margin: 1 0;
    }
    
    .help_title {
        color: $accent;
        text-style: bold;
        margin: 1 0 0 0;
    }
    
    .help_text {
        color: $text;
        margin: 0 0 0 2;
    }
    
    .help_key {
        color: $primary;
        text-style: bold;
    }
    """
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the help modal layout."""
        with Vertical(id="help_dialog"):
            yield Static("CAN Bridge Monitor - Help", classes="help_title")
            
            with Vertical(id="help_content"):
                yield Static("🔧 KEYBOARD SHORTCUTS", classes="help_title")
                yield Static("Ctrl+C          Quit application", classes="help_text")
                yield Static("F1              Clear messages", classes="help_text")
                yield Static("F2              Save log to CSV", classes="help_text")
                yield Static("F3              Pause/Resume", classes="help_text")
                yield Static("F4              Show this help", classes="help_text")
                yield Static("F5              Settings", classes="help_text")
                yield Static("Ctrl+R          Reconnect", classes="help_text")
                yield Static("Escape          Close modals", classes="help_text")
                
                yield Static("📡 CAN COMMANDS", classes="help_title")
                yield Static("send <ID> <DATA>    Send CAN message", classes="help_text")
                yield Static("  Example: send 0x123 01,02,03,04", classes="help_text")
                yield Static("config <PARAM>      Configure device", classes="help_text")
                yield Static("  Example: config baudrate 500000", classes="help_text")
                yield Static("get <PARAM>         Get configuration", classes="help_text")
                yield Static("  Example: get status", classes="help_text")
                
                yield Static("🔍 MESSAGE FILTERING", classes="help_title")
                yield Static("Type Filters (click to toggle):", classes="help_text")
                yield Static("• RX: Received CAN messages", classes="help_text")
                yield Static("• TX: Transmitted CAN messages", classes="help_text")
                yield Static("• ERR: Error messages", classes="help_text")
                yield Static("• INF: Info/Status messages", classes="help_text")
                yield Static("ID Filters (show only specific CAN IDs):", classes="help_text")
                yield Static("• Enter CAN ID (hex: 0x500, dec: 1280)", classes="help_text")
                yield Static("• Press Enter or click Add to apply", classes="help_text")
                yield Static("• Multiple IDs supported", classes="help_text")
                yield Static("• Clear All to remove all ID filters", classes="help_text")
                
                yield Static("📊 MESSAGE DISPLAY", classes="help_title")
                yield Static("🟢 RX messages are shown in green", classes="help_text")
                yield Static("🔵 TX messages are shown in blue", classes="help_text")
                yield Static("❌ Error messages are shown in red", classes="help_text")
                yield Static("ℹ️  Info messages are shown in cyan", classes="help_text")
                
                yield Static("💾 LOG EXPORT", classes="help_title")
                yield Static("• F2 or Save Log button exports to CSV", classes="help_text")
                yield Static("• Filename: can_log_YYYYMMDD_HHMMSS.csv", classes="help_text")
                yield Static("• Includes timestamp, type, ID, and data", classes="help_text")
            
            with Vertical(id="help_buttons"):
                yield Button("Close", id="close_btn", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close_btn":
            self.action_close()
    
    def action_close(self) -> None:
        """Close the help modal."""
        self.dismiss(False)
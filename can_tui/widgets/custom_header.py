"""Custom header widget with clickable menu button."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Button
from textual.reactive import reactive
from textual.message import Message


class CustomHeader(Static):
    """Custom header with a clickable menu button."""
    
    DEFAULT_CSS = """
    CustomHeader {
        dock: top;
        height: 3;
        background: #003366;
        color: white;
    }
    """
    
    class MenuClicked(Message):
        """Message sent when the menu button is clicked."""
        pass
    
    def compose(self) -> ComposeResult:
        """Compose the custom header."""
        with Horizontal():
            # Menu button (clickable)
            yield Button("⭘", id="menu_button", classes="header-menu")
            # Title and subtitle area
            yield Static(self.get_title_text(), id="header_title", classes="header-title")
    
    def get_title_text(self) -> str:
        """Get the formatted title text."""
        app = self.app
        title = getattr(app, 'title', 'CAN Bridge Monitor v1.0')
        sub_title = getattr(app, 'sub_title', 'USB-to-CAN Bridge Interface')
        return f"    {title} — {sub_title}     "
    
    def on_mount(self) -> None:
        """Update title when mounted."""
        self.update_title()
    
    def update_title(self) -> None:
        """Update the title display."""
        try:
            title_widget = self.query_one("#header_title", Static)
            title_widget.update(self.get_title_text())
        except:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle menu button press."""
        if event.button.id == "menu_button":
            self.post_message(self.MenuClicked())
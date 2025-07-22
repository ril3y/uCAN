"""ID Filter widget for managing CAN ID filters."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Button, Static, Label
from textual.widget import Widget
from textual.message import Message
from typing import List


class IDFilterWidget(Widget):
    """Widget for managing CAN ID filters."""
    
    class FilterAdded(Message):
        """Message sent when a filter is added."""
        def __init__(self, can_id: int) -> None:
            self.can_id = can_id
            super().__init__()
    
    class FilterRemoved(Message):
        """Message sent when a filter is removed."""
        def __init__(self, can_id: int) -> None:
            self.can_id = can_id
            super().__init__()
    
    class FiltersCleared(Message):
        """Message sent when all filters are cleared."""
        pass
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_filters: List[int] = []
    
    def compose(self) -> ComposeResult:
        """Compose the ID filter widget."""
        yield Static("📋 ID Filters:", classes="filter-section-header")
        
        with Horizontal(classes="id-input-row"):
            yield Input(placeholder="0x500", id="id_input", classes="id-input")
            yield Button("Add", id="add_filter_btn", variant="primary", classes="add-btn")
        
        yield Static("None", id="active_filters_display", classes="active-filters")
        yield Button("Clear Filters", id="clear_filters_btn", variant="warning", classes="clear-btn")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "add_filter_btn":
            self._add_filter()
        elif event.button.id == "clear_filters_btn":
            self._clear_filters()
        elif event.button.id and event.button.id.startswith("remove_"):
            # Extract CAN ID from button ID
            try:
                can_id = int(event.button.id.split("_")[1])
                self._remove_filter(can_id)
            except (ValueError, IndexError):
                pass
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission (Enter key)."""
        if event.input.id == "id_input":
            self._add_filter()
    
    def _add_filter(self):
        """Add a new CAN ID filter."""
        input_widget = self.query_one("#id_input", Input)
        id_text = input_widget.value.strip()
        
        if not id_text:
            return
        
        try:
            # Parse CAN ID (support both hex and decimal)
            if id_text.lower().startswith("0x"):
                can_id = int(id_text, 16)
            else:
                can_id = int(id_text)
            
            # Validate CAN ID range (0x000 to 0x7FF for standard CAN)
            if 0 <= can_id <= 0x7FF:
                if can_id not in self.active_filters:
                    self.active_filters.append(can_id)
                    self.active_filters.sort()  # Keep sorted
                    self._update_display()
                    input_widget.value = ""  # Clear input
                    
                    # DIRECT APPROACH: Get the app directly and apply filter
                    app = self.app
                    if hasattr(app, 'message_filter'):
                        app.message_filter.add_id_filter(can_id)
                        # Try to apply filter to message log if it exists
                        try:
                            message_log = app.query_one("#message_log")
                            message_log.set_filter(app.message_filter)
                        except:
                            # Message log might not exist in custom view mode
                            pass
                        app.notify(f"ID filter added: 0x{can_id:03X}")
        except ValueError:
            pass
    
    def _remove_filter(self, can_id: int):
        """Remove a CAN ID filter."""
        if can_id in self.active_filters:
            self.active_filters.remove(can_id)
            self._update_display()
            self.post_message(self.FilterRemoved(can_id))
    
    def _clear_filters(self):
        """Clear all filters."""
        if self.active_filters:
            self.active_filters.clear()
            self._update_display()
            
            # DIRECT APPROACH: Get the app directly and clear filter
            app = self.app
            if hasattr(app, 'message_filter'):
                app.message_filter.clear_id_filters()
                # Try to apply filter to message log if it exists
                try:
                    message_log = app.query_one("#message_log")
                    message_log.set_filter(app.message_filter)
                except:
                    # Message log might not exist in custom view mode
                    pass
                app.notify("ID filters cleared")
    
    def _update_display(self):
        """Update the active filters display."""
        display_widget = self.query_one("#active_filters_display", Static)
        
        if not self.active_filters:
            display_widget.update("None")
        else:
            # Show filters as clickable items
            filter_text = ", ".join(f"0x{fid:03X}" for fid in self.active_filters)
            display_widget.update(filter_text)
    
    def set_filters(self, filters: List[int]):
        """Set the active filters from external source."""
        self.active_filters = filters.copy()
        self.active_filters.sort()
        self._update_display()
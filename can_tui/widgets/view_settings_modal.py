"""View settings modal widget for configuring custom views and display modes."""

from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static, Switch, Collapsible
from textual.reactive import reactive
from textual.binding import Binding
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ViewSettingsModal(ModalScreen[dict]):
    """Modal screen for configuring view settings and custom visualizations."""
    
    CSS = """
    ViewSettingsModal {
        align: center middle;
    }
    
    #view_settings_dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 90;
        height: 25;
        border: thick $background 80%;
        background: $surface;
    }
    
    #view_settings_content {
        column-span: 2;
        height: 1fr;
        overflow: auto;
    }
    
    .setting_section {
        border: solid $primary;
        margin: 1 0;
        padding: 1;
    }
    
    .setting_row {
        height: 3;
        margin: 1 0;
    }
    
    .setting_label {
        width: 20;
        padding: 1 0;
        text-align: right;
    }
    
    .setting_input {
        width: 1fr;
        margin-left: 2;
    }
    
    .setting_description {
        margin: 0 2;
        color: $text-muted;
        text-style: italic;
    }
    
    #button_bar {
        column-span: 2;
        height: 3;
        align: center middle;
    }
    
    Button {
        margin: 0 2;
    }
    
    .custom_view_item {
        border: solid $secondary;
        margin: 1;
        padding: 1;
    }
    
    .enabled_view {
        background: $success-lighten-3;
    }
    
    .disabled_view {
        background: $error-lighten-3;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, 
                 view_registry=None,
                 current_settings: Optional[Dict[str, Any]] = None,
                 title: str = "View Selector"):
        super().__init__()
        self.view_registry = view_registry
        self.current_settings = current_settings or {}
        self.title = title
        
        # Default settings
        self.default_settings = {
            "view_mode": "message_log",  # message_log, custom_view, split_view
            "auto_switch": True,
            "enabled_views": {},
            "can_id_view_mappings": {}
        }
        
        # Merge with current settings
        self.settings = {**self.default_settings, **self.current_settings}
        
    def compose(self) -> ComposeResult:
        """Compose the view settings modal."""
        with Grid(id="view_settings_dialog"):
            with ScrollableContainer(id="view_settings_content"):
                yield Static(self.title, id="view_settings_title")
                
                # View Selection
                with Vertical(classes="setting_section"):
                    yield Static("📺 Display Mode", classes="section_header")
                    yield Static("Choose how CAN messages are displayed in the main panel", classes="setting_description")
                    
                    with Horizontal(classes="setting_row"):
                        yield Label("View Mode:", classes="setting_label")
                        mode_options = self._get_view_options()
                        yield Select(
                            mode_options,
                            id="view_mode_select",
                            classes="setting_input"
                        )
            
            # Button bar
            with Horizontal(id="button_bar"):
                yield Button("Apply", variant="primary", id="apply")
                yield Button("Cancel", variant="default", id="cancel")
    
    def on_mount(self) -> None:
        """Set initial values after mounting."""
        # Set the initial value for the view mode select
        try:
            view_mode_select = self.query_one("#view_mode_select", Select)
            view_mode_select.value = self.settings["view_mode"]
        except Exception as e:
            logger.debug(f"Failed to set initial view mode value: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "apply":
            # Collect settings from UI
            new_settings = self._collect_settings()
            logger.info(f"Applying view settings: {new_settings}")
            self.dismiss(new_settings)
            
        elif event.button.id == "cancel":
            self.dismiss(None)
    
    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)
    
    def _collect_settings(self) -> dict:
        """Collect current settings from UI elements."""
        try:
            settings = {}
            
            # View mode (only setting we need now)
            view_mode_select = self.query_one("#view_mode_select", Select)
            settings["view_mode"] = view_mode_select.value
            
            # Auto-enable relevant views based on mode
            enabled_views = {}
            if settings["view_mode"] == "custom_view" or settings["view_mode"] == "split_view":
                enabled_views["Switch Dashboard"] = True
            
            settings["enabled_views"] = enabled_views
            settings["auto_switch"] = True  # Always enable auto-switching
            settings["can_id_view_mappings"] = {}  # Keep empty for now
            
            return settings
            
        except Exception as e:
            logger.error(f"Error collecting settings: {e}")
            return self.current_settings
    
    def _update_ui_from_settings(self) -> None:
        """Update UI elements from current settings."""
        try:
            # Update view mode
            try:
                view_mode_select = self.query_one("#view_mode_select", Select)
                view_mode_select.value = self.settings["view_mode"]
            except:
                pass
            
            # Update auto-switch
            try:
                auto_switch = self.query_one("#auto_switch", Switch)
                auto_switch.value = self.settings["auto_switch"]
            except:
                pass
            
            # Update enabled views
            if self.view_registry:
                for view_name in self.view_registry.get_all_views().keys():
                    switch_id = f"view_enabled_{view_name.replace(' ', '_')}"
                    try:
                        switch = self.query_one(f"#{switch_id}", Switch)
                        switch.value = self.settings["enabled_views"].get(view_name, True)
                    except:
                        pass
            
            # Update CAN ID mappings
            for can_id, view_name in self.settings["can_id_view_mappings"].items():
                select_id = f"can_id_mapping_{can_id:03X}"
                try:
                    select = self.query_one(f"#{select_id}", Select)
                    select.value = view_name
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error updating UI from settings: {e}")
    
    def get_current_settings(self) -> dict:
        """Get the current settings."""
        return self.settings.copy()
    
    def _get_view_options(self) -> List[tuple]:
        """Get view options for the dropdown based on available views."""
        if self.view_registry and hasattr(self.view_registry, 'get_view_options_for_settings'):
            try:
                return self.view_registry.get_view_options_for_settings()
            except Exception as e:
                logger.error(f"Error getting view options from registry: {e}")
        
        # Fallback options if registry is not available
        return [
            ("message_log", "Message Log - Traditional scrolling message display"),
            ("harness_switch_view", "Harness Switch View - Visual switch state display for 0x500 messages"),
            ("split_view", "Split View - Both custom view and message log")
        ]
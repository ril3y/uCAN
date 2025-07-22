"""Settings modal widget for configuring serial port and baud rate."""

from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static
from textual.reactive import reactive
from textual.binding import Binding
import serial.tools.list_ports
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class SettingsModal(ModalScreen[dict]):
    """Modal screen for configuring connection settings."""
    
    CSS = """
    SettingsModal {
        align: center middle;
    }
    
    #settings_dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 20;
        border: thick $background 80%;
        background: $surface;
    }
    
    #settings_content {
        column-span: 2;
        height: 1fr;
        overflow: auto;
    }
    
    .setting_row {
        height: 3;
        margin: 1 0;
    }
    
    .setting_label {
        width: 15;
        padding: 1 0;
        text-align: right;
    }
    
    .setting_input {
        width: 1fr;
        margin-left: 2;
    }
    
    #button_bar {
        column-span: 2;
        height: 3;
        align: center middle;
    }
    
    Button {
        margin: 0 2;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, current_port: Optional[str] = None, current_baudrate: int = 115200, title: str = "Connection Settings"):
        super().__init__()
        self.current_port = current_port
        self.current_baudrate = current_baudrate
        self.title = title
        self.available_ports = self._get_available_ports()
        
    def _get_available_ports(self) -> List[Tuple[str, str]]:
        """Get available serial ports with descriptions."""
        ports = []
        
        # Get all available ports with actual devices
        for port in serial.tools.list_ports.comports():
            # Skip ports without a real device connected
            # Check for various indicators of a real device
            include_port = False
            
            # Include USB devices and common Arduino/CAN devices
            if port.device.startswith(("/dev/ttyUSB", "/dev/ttyACM", "COM")):
                include_port = True
            # Include ports with meaningful descriptions
            elif port.description and port.description != "n/a":
                include_port = True
            # Include ports with a manufacturer
            elif hasattr(port, 'manufacturer') and port.manufacturer:
                include_port = True
                
            if include_port:
                # Build a descriptive string
                description = f"{port.device}"
                if port.description and port.description != "n/a":
                    description += f" - {port.description}"
                if hasattr(port, 'manufacturer') and port.manufacturer:
                    description += f" ({port.manufacturer})"
                    
                ports.append((port.device, description))
        
        # If no ports found, add a message (but with empty device path)
        if not ports:
            ports.append(("", "No serial devices found"))
        
        return ports
    
    def compose(self) -> ComposeResult:
        """Compose the settings modal."""
        with Grid(id="settings_dialog"):
            with Vertical(id="settings_content"):
                yield Static(self.title, id="settings_title")
                
                # Serial Port Selection
                with Horizontal(classes="setting_row"):
                    yield Label("Serial Port:", classes="setting_label")
                    # Use device path as the value, descriptions as the display text
                    port_options = [(device, desc) for device, desc in self.available_ports]
                    
                    yield Select(
                        port_options,
                        id="port_select",
                        classes="setting_input"
                    )
                
                # Baud Rate Selection
                with Horizontal(classes="setting_row"):
                    yield Label("Baud Rate:", classes="setting_label")
                    baud_options = [
                        ("9600", "9600"),
                        ("19200", "19200"),
                        ("38400", "38400"),
                        ("57600", "57600"),
                        ("115200", "115200"),
                        ("230400", "230400"),
                        ("460800", "460800"),
                        ("921600", "921600"),
                    ]
                    yield Select(
                        baud_options,
                        value=str(self.current_baudrate),
                        id="baud_select",
                        classes="setting_input"
                    )
                
                # Refresh button for ports
                with Horizontal(classes="setting_row"):
                    yield Label("", classes="setting_label")
                    yield Button("Refresh Ports", id="refresh_ports", classes="setting_input")
            
            # Button bar
            with Horizontal(id="button_bar"):
                yield Button("Connect", variant="primary", id="apply")
                yield Button("Cancel", variant="default", id="cancel")
    
    def on_mount(self) -> None:
        """Set initial values after mounting."""
        # Refresh the available ports list when the modal is mounted
        self.available_ports = self._get_available_ports()
        
        # Update the port select widget with fresh options
        port_select = self.query_one("#port_select", Select)
        port_options = [(device, desc) for device, desc in self.available_ports]
        port_select.set_options(port_options)
        
        # Use call_later to set the value after the widget is fully updated
        self.call_later(self._set_initial_port_value)
    
    def _set_initial_port_value(self) -> None:
        """Set the initial port value after the widget is fully mounted."""
        try:
            port_select = self.query_one("#port_select", Select)
            available_devices = [device for device, desc in self.available_ports if device]
            
            current_value = None
            
            # First try to use current port if it exists in available devices
            if self.current_port and self.current_port in available_devices:
                current_value = self.current_port
            # Otherwise use the first available port (skip empty ones)
            elif available_devices:
                current_value = available_devices[0]
            
            # Set the value if we found a valid one
            if current_value:
                try:
                    port_select.value = current_value
                except Exception as e:
                    # Log the error but don't crash
                    logger.debug(f"Failed to set initial port value {current_value}: {e}")
        except Exception as e:
            # Log initialization errors but don't crash
            logger.debug(f"Error during port value initialization: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "apply":
            # Get current values
            port_select = self.query_one("#port_select", Select)
            baud_select = self.query_one("#baud_select", Select)
            
            # Check if a valid port was selected
            if not port_select.value:
                # Don't proceed if no port selected
                return
                
            selected_port = port_select.value
            
            # Check for the "No serial devices found" case
            if selected_port == "" or selected_port == "No serial devices found":
                return
            
            # Ensure we have a valid device path
            # The Select widget should already contain the device path as the value
            if not selected_port.startswith(('/dev/', 'COM')):
                # This shouldn't happen with correct Select setup, but handle it as fallback
                for device, desc in self.available_ports:
                    if device and (desc == selected_port or device == selected_port):
                        selected_port = device
                        break
                else:
                    # Still no valid port found
                    return
                
            selected_baud = int(baud_select.value)
            
            # Return the settings
            self.dismiss({
                "port": selected_port,
                "baudrate": selected_baud
            })
            
        elif event.button.id == "cancel":
            self.dismiss(None)
            
        elif event.button.id == "refresh_ports":
            self._refresh_ports()
    
    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)
    
    def _refresh_ports(self) -> None:
        """Refresh the available ports list."""
        self.available_ports = self._get_available_ports()
        
        # Update the port select widget
        port_select = self.query_one("#port_select", Select)
        port_options = [(device, desc) for device, desc in self.available_ports]
        
        # Store current selection
        current_value = port_select.value
        
        # Clear and repopulate
        port_select.clear()
        port_select.set_options(port_options)
        
        # Restore selection if it still exists
        if current_value and any(device == current_value for device, desc in self.available_ports if device):
            try:
                port_select.value = current_value
            except Exception:
                pass
        elif self.available_ports and self.available_ports[0][0]:
            # Default to first port if it's not empty
            try:
                port_select.value = self.available_ports[0][0]
            except Exception:
                pass
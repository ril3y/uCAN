from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Static, Button, Switch
from textual.events import Click
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message
from rich.text import Text
import asyncio
import logging
from datetime import datetime
from typing import List

from .widgets.message_log import MessageLogWidget
from .widgets.command_input import CommandInputWidget
from .widgets.settings_modal import SettingsModal
from .widgets.help_modal import HelpModal
from .widgets.custom_header import CustomHeader
from .widgets.id_filter_widget import IDFilterWidget
from .widgets.view_settings_modal import ViewSettingsModal
from .widgets.status_bar import StatusBarWidget
from .services.serial_service import SerialService
from .models.can_message import CANMessage, MessageStats, MessageFilter
from .parsers import (
    ParserRegistry, 
    RawDataParser, 
    ExampleSensorParser,
    GolfCartThrottleParser,
    WiringHarnessParser,
    WiringHarnessSwitchParser
)
from .views.modern_registry import ModernViewRegistry

# Configure logging - only to file, not console to avoid UI interference
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only add file handler if not already added
if not logger.handlers:
    file_handler = logging.FileHandler('/home/ril3y/UCAN/can.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s:%(levelname)s] %(message)s'))
    logger.addHandler(file_handler)
    logger.propagate = False  # Prevent console output

# Configure CAN log file - only to file, not console
can_logger = logging.getLogger('can_logger')
can_logger.setLevel(logging.DEBUG)

# Only add file handler if not already added
if not can_logger.handlers:
    can_file_handler = logging.FileHandler('/home/ril3y/UCAN/can.log')
    can_file_handler.setFormatter(logging.Formatter('%(asctime)s [CAN:%(levelname)s] %(message)s'))
    can_logger.addHandler(can_file_handler)
    can_logger.propagate = False  # Prevent console output

# Disable root logger console output to prevent any logging from appearing in UI
root_logger = logging.getLogger()
root_logger.handlers = []  # Remove all handlers from root logger
root_logger.addHandler(logging.NullHandler())  # Add null handler to prevent warnings


class StatsWidget(Static):
    """Widget to display connection and message statistics."""
    
    def __init__(self, **kwargs):
        super().__init__("", **kwargs)
        self.stats = MessageStats()
        self.connected = False
        self.port = ""
        self.update_timer = None
    
    def update_stats(self, message: CANMessage):
        """Update statistics with a new message."""
        self.stats.update(message)
        self.refresh_display()
    
    def set_connection_status(self, connected: bool, port: str = ""):
        """Update connection status."""
        self.connected = connected
        self.port = port
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the statistics display."""
        if self.connected:
            status_text = Text()
            status_text.append("🟢 Connected", style="green bold")
            status_text.append(f" ({self.port})", style="dim")
        else:
            status_text = Text()
            status_text.append("🔴 Disconnected", style="red bold")
        
        stats_text = Text()
        stats_text.append(f"\n📊 Statistics:\n", style="cyan bold")
        stats_text.append(f"  RX: {self.stats.rx_count:,}\n", style="green")
        stats_text.append(f"  TX: {self.stats.tx_count:,}\n", style="blue")
        stats_text.append(f"  Errors: {self.stats.error_count:,}\n", style="red")
        stats_text.append(f"  Rate: {self.stats.get_rate():.1f} msg/s\n", style="yellow")
        
        elapsed = (datetime.now() - self.stats.start_time).total_seconds()
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        stats_text.append(f"  Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}", style="dim")
        
        combined = Text()
        combined.append_text(status_text)
        combined.append_text(stats_text)
        
        self.update(combined)



class CANBridgeApp(App):
    """Main TUI application for CAN bridge monitoring."""
    
    CSS = """
    Screen {
        background: #1e1e1e;
    }
    
    Header, CustomHeader {
        dock: top;
        height: 3;
        background: #003366;
        color: white;
    }
    
    .header-menu {
        width: 8;
        height: 3;
        margin: 0;
        padding: 0;
        background: #003366;
        color: white;
        border: none;
        text-align: center;
    }
    
    .header-menu:hover {
        background: #004080;
    }
    
    .header-title {
        width: 1fr;
        height: 3;
        content-align: center middle;
        text-align: center;
        background: #003366;
        color: white;
    }
    
    Footer {
        dock: bottom;
        height: 3;
        background: #003366;
        color: white;
    }
    
    #main_container {
        height: 1fr;
        background: #1e1e1e;
    }
    
    #message_panel {
        width: 75%;
        border: solid #666666;
        background: #2a2a2a;
    }
    
    #side_panel {
        width: 25%;
        border: solid #666666;
        background: #2a2a2a;
    }
    
    #command_container {
        height: 5;
        border: solid #666666;
        background: #003366;
    }
    
    MessageLogWidget {
        color: white;
        background: #2a2a2a;
    }
    
    CommandInputWidget {
        background: #003366;
        color: white;
    }
    
    StatsWidget {
        padding: 1;
        color: white;
    }
    
    #controls {
        padding: 1;
        color: white;
        height: 1fr;
        overflow: auto;
    }
    
    Button {
        margin: 1;
        width: 100%;
        min-height: 3;
        content-align: center middle;
        text-align: center;
    }
    
    .filter-header {
        margin-top: 1;
        color: cyan;
        text-style: bold;
    }
    
    .filter-item {
        margin: 0;
        color: cyan;
        background: transparent;
        padding: 0 1;
        text-style: bold;
        height: 1;
    }
    
    .filter-item:hover {
        background: #444444;
        color: cyan;
    }
    
    .filter-item:focus {
        background: #333333;
    }
    
    /* ID Filter Widget Styling */
    IDFilterWidget {
        margin: 1 0;
        padding: 0;
        border: none;
        background: transparent;
        height: auto;
        max-height: 8;
    }
    
    .filter-section-header {
        color: cyan;
        text-style: bold;
        margin: 0 0 0 0;
        height: 1;
    }
    
    .id-input-row {
        height: 3;
        margin: 0 0 0 0;
    }
    
    .id-input {
        width: 2fr;
        margin-right: 1;
    }
    
    .add-btn {
        width: 1fr;
        height: 3;
        content-align: center middle;
        text-align: center;
        align: center middle;
        padding: 0;
        margin: 0;
    }
    
    .active-filters-label {
        color: white;
        margin: 0;
        height: 1;
    }
    
    .active-filters {
        color: yellow;
        margin: 0 0 1 0;
        height: 1;
        background: transparent;
        padding: 0;
        text-style: bold;
    }
    
    IDFilterWidget .clear-btn {
        width: 100%;
        margin: 0 0 1 0 !important;
        height: 3 !important;
        text-align: center;
        content-align: center middle !important;
        align: center middle;
        padding: 0 !important;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("f1", "clear_messages", "Clear"),
        Binding("f2", "save_log", "Save"),
        Binding("f3", "toggle_pause", "Pause"),
        Binding("f4", "show_help", "Help"),
        Binding("f5", "show_settings", "Settings"),
        Binding("f8", "show_view_settings", "View Settings"),
        Binding("ctrl+r", "reconnect", "Reconnect"),
        Binding("escape", "close_modal", "Close Modal"),
    ]
    
    def __init__(self, port: str = None, baudrate: int = 115200):
        super().__init__()
        self.title = "CAN Bridge Monitor v1.0"
        self.sub_title = "USB-to-CAN Bridge Interface"
        
        # Initialize services
        self.serial_service = SerialService(port=port, baudrate=baudrate)
        self.serial_service.set_message_callback(self.on_serial_message)
        self.serial_service.set_connection_callback(self.on_connection_change)
        
        # Initialize parser registry
        self.parser_registry = ParserRegistry()
        self._setup_parsers()
        
        # Initialize modern view system (kept for view discovery only)
        self.view_registry = ModernViewRegistry()  # NOTE: Only used for view discovery, not routing
        
        # Simple CAN ID routing system - direct message delivery
        self.can_id_handlers = {}  # {can_id: active_widget}
        self.active_view_widget = None
        
        # Status bar for connection/message stats
        self.status_bar = None
        
        # State
        self.paused = False
        self.current_view_mode = "message_log"
        self.connecting = False
        self.message_filter = MessageFilter()
    
    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield CustomHeader()
        
        with Container(id="main_container"):
            with Horizontal():
                # Main message panel (75% width) - dynamic content based on view mode
                with Vertical(id="message_panel"):
                    yield from self._compose_main_panel()
                
                # Side panel (25% width)
                with Vertical(id="side_panel"):
                    yield StatsWidget(id="stats")
                    with Vertical(id="controls"):
                        yield Static("🔍 Type Filters:", classes="filter-header")
                        yield Static("RX:  ON", id="filter_rx", classes="filter-item")
                        yield Static("TX:  ON", id="filter_tx", classes="filter-item")
                        yield Static("ERR: ON", id="filter_errors", classes="filter-item")
                        yield Static("INF: ON", id="filter_info", classes="filter-item")
                        yield IDFilterWidget(id="id_filter_widget")
                        yield Button("Clear Messages", id="clear_btn", variant="error")
                        yield Button("Save Log", id="save_btn", variant="success")
                        yield Button("Pause", id="pause_btn", variant="warning")
                        yield Button("Settings", id="settings_btn", variant="primary")
            
            # Command input at bottom
            with Container(id="command_container"):
                yield CommandInputWidget(id="command_input")
        
        # Custom status bar instead of Footer
        yield StatusBarWidget(id="status_bar")
    
    def on_mount(self) -> None:
        """Initialize the application after mounting."""
        # Clear log file for fresh debugging session
        try:
            from pathlib import Path
            log_file = Path("can.log")
            if log_file.exists():
                with open(log_file, 'w') as f:
                    f.write("")
        except:
            pass
            
        can_logger.error("=" * 60)
        can_logger.error("=== NEW SESSION: Simple CAN ID Routing System Active ===")
        can_logger.error("=" * 60)
        
        # Set up command input callback
        command_input = self.query_one("#command_input", CommandInputWidget)
        command_input.set_command_callback(self.on_command_submitted)
        
        # Initialize status bar
        self.status_bar = self.query_one("#status_bar", StatusBarWidget)
        
        # View system is auto-configured during registry initialization
        can_logger.info(f"VIEW_SETUP: Auto-discovered {len(self.view_registry.get_available_view_names())} views")
        
        # Show port selection dialog if no specific port was provided
        if not self.serial_service.port:
            logger.info("No port specified, showing port selection dialog")
            self.call_later(self.show_startup_port_selection)
        else:
            logger.info(f"Port specified: {self.serial_service.port}, connecting directly")
            # Start connection attempt with specified port
            self.call_later(self.connect_to_device)
            
        # Schedule a status refresh after initial connection
        self.set_timer(2, self._refresh_connection_status)
    
    def show_startup_port_selection(self):
        """Show port selection dialog on startup."""
        logger.info("Showing startup port selection dialog")
        
        def handle_startup_result(result):
            if result:  # User clicked Connect
                logger.info(f"User selected port for startup connection: {result}")
                asyncio.create_task(self.apply_settings(result))
            else:
                logger.info("User cancelled startup port selection")
                # Show message that no connection was made
                info_msg = CANMessage(
                    type="INFO",
                    error_message="No port selected - use Settings (F5) to connect",
                    success=True
                )
                message_log = self.query_one("#message_log", MessageLogWidget)
                message_log.add_message(info_msg)
        
        # Show settings modal for port selection with startup title
        modal = SettingsModal(None, 115200, "Select CAN Bridge Port")
        self.push_screen(modal, handle_startup_result)
    
    def _refresh_connection_status(self) -> None:
        """Refresh connection status display."""
        if self.serial_service.is_connected:
            logger.info("Refreshing connection status - connected")
            self.on_connection_change(True)
        else:
            logger.info("Refreshing connection status - disconnected")
            self.on_connection_change(False)
    
    def _setup_parsers(self) -> None:
        """Initialize and configure protocol parsers."""
        can_logger.info("PARSER_SETUP: Setting up protocol parsers")
        
        # Register built-in parsers
        self.parser_registry.register_parser(RawDataParser())
        
        # Register custom parsers
        self.parser_registry.register_parser(ExampleSensorParser())
        self.parser_registry.register_parser(GolfCartThrottleParser())
        self.parser_registry.register_parser(WiringHarnessParser())
        self.parser_registry.register_parser(WiringHarnessSwitchParser())
        
        # Set up default mappings
        self.parser_registry.set_default_parser("Raw Data v1.0")
        
        # Add specific CAN ID mappings
        self.parser_registry.add_can_id_mapping(0x100, "Golf Cart Brake Sensor v1.0")
        self.parser_registry.add_can_id_mapping(0x101, "Golf Cart Throttle Sensor v1.0")
        self.parser_registry.add_can_id_mapping(0x410, "STM32F103 Wiring Harness v1.0")
        self.parser_registry.add_can_id_mapping(0x500, "Wiring Harness Switch State v1.0")
        
        # Try to load configuration from file
        try:
            self.parser_registry.load_config("parser_config.yaml")
            can_logger.info("PARSER_SETUP: Loaded configuration from parser_config.yaml")
        except Exception as e:
            can_logger.warning(f"PARSER_SETUP: Could not load config file: {e}")
        
        # Log registry stats
        stats = self.parser_registry.get_stats()
        can_logger.info(f"PARSER_SETUP: Registered {stats['total_parsers']} parsers, {stats['enabled_parsers']} enabled")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        can_logger.info(f"BUTTON_PRESSED: {event.button.id}")
        
        if event.button.id == "clear_btn":
            self.action_clear_messages()
        elif event.button.id == "save_btn":
            self.action_save_log()
        elif event.button.id == "pause_btn":
            self.action_toggle_pause()
        elif event.button.id == "settings_btn":
            self.action_show_settings()
    
    def on_custom_header_menu_clicked(self, event: CustomHeader.MenuClicked) -> None:
        """Handle menu button click from custom header."""
        self.action_show_settings()
    
    def on_click(self, event: Click) -> None:
        """Handle clicks on filter items."""
        widget_id = event.widget.id
        
        # Toggle filter states
        if widget_id == "filter_rx":
            self.message_filter.show_rx = not self.message_filter.show_rx
            self._update_filter_display("filter_rx", self.message_filter.show_rx, "RX")
        elif widget_id == "filter_tx":
            self.message_filter.show_tx = not self.message_filter.show_tx
            self._update_filter_display("filter_tx", self.message_filter.show_tx, "TX")
        elif widget_id == "filter_errors":
            self.message_filter.show_errors = not self.message_filter.show_errors
            self._update_filter_display("filter_errors", self.message_filter.show_errors, "ERR")
        elif widget_id == "filter_info":
            self.message_filter.show_info = not self.message_filter.show_info
            self._update_filter_display("filter_info", self.message_filter.show_info, "INF")
        
        if widget_id in ["filter_rx", "filter_tx", "filter_errors", "filter_info"]:
            # Apply the filter to message log if it exists
            try:
                if self.current_view_mode in ["message_log", "split_view"]:
                    message_log = self.query_one("#message_log", MessageLogWidget)
                    message_log.set_filter(self.message_filter)
                # Custom views handle their own filtering, so no action needed there
            except Exception as e:
                logger.warning(f"Could not apply filter to message log: {e}")
            
            can_logger.info(f"FILTER_CHANGED: RX={self.message_filter.show_rx}, TX={self.message_filter.show_tx}, Errors={self.message_filter.show_errors}, Info={self.message_filter.show_info}")
    
    
    def _update_filter_display(self, widget_id: str, is_checked: bool, label: str):
        """Update the visual display of a filter."""
        status = "ON" if is_checked else "OFF"
        filter_widget = self.query_one(f"#{widget_id}", Static)
        filter_widget.update(f"{label}: {status}")
    
    async def connect_to_device(self):
        """Attempt to connect to the CAN bridge device."""
        if self.connecting:
            return
        
        self.connecting = True
        stats = self.query_one("#stats", StatsWidget)
        stats.set_connection_status(False, "Connecting...")
        
        success = await self.serial_service.connect()
        
        if success:
            logger.info(f"Connected to CAN bridge at {self.serial_service.port}")
            # Show which port was connected
            connected_msg = CANMessage(
                type="INFO",
                error_message=f"Connected to CAN bridge at {self.serial_service.port}",
                success=True
            )
            
            # Add message to appropriate widget based on view mode
            try:
                if self.current_view_mode in ["message_log", "split_view"]:
                    message_log = self.query_one("#message_log", MessageLogWidget)
                    message_log.add_message(connected_msg)
                elif self.current_view_mode == "custom_view":
                    # Try to add to custom view console if available
                    try:
                        custom_widget = self.query_one("#custom_view_widget")
                        if hasattr(custom_widget, 'log_console'):
                            custom_widget.log_console(f"Connected to CAN bridge at {self.serial_service.port}", "info")
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Could not add connection message to UI: {e}")
            
            # Ensure connection status is updated
            self.on_connection_change(True)
        else:
            logger.error("Failed to connect to CAN bridge")
            # Show error message
            error_msg = CANMessage(
                type="ERROR",
                error_message=f"Failed to connect to CAN bridge at {self.serial_service.port}",
                success=False
            )
            
            # Add error message to appropriate widget based on view mode
            try:
                if self.current_view_mode in ["message_log", "split_view"]:
                    message_log = self.query_one("#message_log", MessageLogWidget)
                    message_log.add_message(error_msg)
                elif self.current_view_mode == "custom_view":
                    # Try to add to custom view console if available
                    try:
                        custom_widget = self.query_one("#custom_view_widget")
                        if hasattr(custom_widget, 'log_console'):
                            custom_widget.log_console(f"Failed to connect to CAN bridge at {self.serial_service.port}", "error")
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Could not add connection error message to UI: {e}")
            
            # Ensure disconnected status is shown
            self.on_connection_change(False)
        
        self.connecting = False
    
    def on_serial_message(self, raw_message: str):
        """Handle incoming messages from the serial port."""
        if self.paused:
            can_logger.info("MESSAGE_PAUSED: Message ignored due to pause state")
            return
            
        can_logger.debug(f"SERIAL_RECEIVED: '{raw_message}'")
        
        try:
            # Parse the message
            message = CANMessage.from_raw_string(raw_message)
            
            # Skip processing if message was suppressed (returns None)
            if message is None:
                can_logger.debug(f"MESSAGE_SUPPRESSED: '{raw_message}'")
                return
                
            can_logger.info(f"MESSAGE_PARSED: type={message.type}, can_id={message.can_id}, data={message.data}")
            
            # Try to parse with protocol parsers if it's a CAN message
            parsed_message = None
            if message.type.value in ["RX", "TX"] and message.can_id is not None and message.data:
                try:
                    parsed_message = self.parser_registry.parse_message(message.can_id, bytes(message.data))
                    if parsed_message:
                        can_logger.info(f"PROTOCOL_PARSED: parser={parsed_message.parser_name}, confidence={parsed_message.confidence:.1%}")
                except Exception as e:
                    can_logger.error(f"PROTOCOL_PARSE_ERROR: {e}")
            
            # Only add to UI and stats if not paused
            if not self.paused:
                # Route message to appropriate widget(s) based on view mode
                self._route_message_to_widgets(message, parsed_message)
                
                # Update statistics
                stats = self.query_one("#stats", StatsWidget)
                stats.update_stats(message)
                
                # Update status bar message counts
                if self.status_bar:
                    stats_data = stats.get_stats()
                    total_messages = stats_data.get("total_messages", 0)
                    total_errors = stats_data.get("total_errors", 0)
                    self.status_bar.update_message_stats(total_messages, total_errors)
            
        except Exception as e:
            can_logger.error(f"MESSAGE_PARSE_ERROR: raw='{raw_message}', error={e}")
            logger.error(f"Error processing message '{raw_message}': {e}")
    
    def on_connection_change(self, connected: bool):
        """Handle connection status changes."""
        port = self.serial_service.port or ""
        can_logger.info(f"CONNECTION_CHANGE: connected={connected}, port='{port}'")
        logger.info(f"CONNECTION_CHANGE: connected={connected}, port='{port}'")
        
        try:
            stats = self.query_one("#stats", StatsWidget)
            logger.info(f"Found stats widget, setting connection status to {connected}")
            stats.set_connection_status(connected, port)
        except Exception as e:
            logger.error(f"Failed to update stats widget: {e}")
        
        # Update custom status bar
        if self.status_bar:
            if connected:
                self.status_bar.update_connection_status("Connected", port)
            else:
                self.status_bar.update_connection_status("Disconnected")
        
        if connected:
            self.sub_title = f"Connected to {port}"
        else:
            self.sub_title = "Disconnected"
        
        # Update custom header title
        try:
            header = self.query_one(CustomHeader)
            header.update_title()
        except:
            pass
    
    async def on_command_submitted(self, command: str):
        """Handle command submission from input widget."""
        can_logger.info(f"USER_COMMAND: '{command}'")
        logger.info(f"Command submitted: '{command}'")
        command_input = self.query_one("#command_input", CommandInputWidget)
        
        # Validate and format command
        valid, formatted_command = command_input.validate_and_format_command(command)
        can_logger.info(f"COMMAND_VALIDATION: valid={valid}, formatted='{formatted_command}'")
        logger.info(f"Command validation: valid={valid}, formatted='{formatted_command}'")
        
        if not valid:
            can_logger.error(f"COMMAND_INVALID: {formatted_command}")
            # Show error in appropriate log
            error_msg = CANMessage(
                type="ERROR",
                error_message=formatted_command,
                success=False
            )
            try:
                if self.current_view_mode in ["message_log", "split_view"]:
                    message_log = self.query_one("#message_log", MessageLogWidget)
                    message_log.add_message(error_msg)
                # For custom views, validation errors will be handled by the view's callback
            except Exception as e:
                logger.warning(f"Could not add validation error to UI: {e}")
            return
        
        # Show command being sent in appropriate log
        tx_msg = CANMessage(
            type="TX",
            error_message=f"Sending: {formatted_command}",
            success=True
        )
        
        # Try to add message to appropriate widget based on view mode
        try:
            if self.current_view_mode in ["message_log", "split_view"]:
                message_log = self.query_one("#message_log", MessageLogWidget)
                message_log.add_message(tx_msg)
            # For custom views, the command came from the view itself, no need to log back
        except Exception as e:
            logger.warning(f"Could not add TX message to UI: {e}")
        
        # Send command to device
        can_logger.info(f"SERIAL_SEND_ATTEMPT: '{formatted_command}'")
        success = await self.serial_service.send_command(formatted_command)
        can_logger.info(f"SERIAL_SEND_RESULT: success={success}")
        logger.info(f"Command send result: success={success}")
        
        if not success:
            can_logger.error(f"SERIAL_SEND_FAILED: {formatted_command}")
            # Show error in appropriate log
            error_msg = CANMessage(
                type="ERROR",
                error_message=f"Failed to send command: {formatted_command}",
                success=False
            )
            try:
                if self.current_view_mode in ["message_log", "split_view"]:
                    message_log = self.query_one("#message_log", MessageLogWidget)
                    message_log.add_message(error_msg)
                # For custom views, the error will be handled by the view's callback
            except Exception as e:
                logger.warning(f"Could not add error message to UI: {e}")
    
    def action_quit(self):
        """Quit the application."""
        self.exit()
    
    def action_clear_messages(self):
        """Clear all messages from the log."""
        can_logger.info("ACTION_CLEAR_MESSAGES: Clearing messages and statistics")
        
        # Try to clear message log if it exists (message_log or split_view modes)
        try:
            message_log = self.query_one("#message_log", MessageLogWidget)
            message_log.clear_messages()
        except Exception:
            # No message log widget (probably in custom view mode)
            pass
        
        # Try to clear custom view consoles if they exist
        try:
            custom_widget = self.query_one("#custom_view_widget")
            if hasattr(custom_widget, 'action_clear_console'):
                custom_widget.action_clear_console()
        except Exception:
            # No custom view widget
            pass
        
        # Reset statistics
        try:
            stats = self.query_one("#stats", StatsWidget)
            stats.stats = MessageStats()
            stats.refresh_display()
        except Exception:
            # No stats widget (shouldn't happen, but handle gracefully)
            pass
        
        can_logger.info("ACTION_CLEAR_MESSAGES: Clear completed")
    
    def action_save_log(self):
        """Save the message log to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"can_log_{timestamp}.csv"
        
        try:
            # Try to get CSV data from message log widget
            csv_data = None
            if self.current_view_mode in ["message_log", "split_view"]:
                try:
                    message_log = self.query_one("#message_log", MessageLogWidget)
                    csv_data = message_log.export_messages("csv")
                except Exception:
                    pass
            
            # If no message log or custom view mode, create a basic export
            if not csv_data:
                csv_data = "timestamp,type,can_id,data,comment\n"
                csv_data += f"{timestamp},INFO,N/A,N/A,Log export from {self.current_view_mode} mode\n"
            
            with open(filename, 'w') as f:
                f.write(csv_data)
            
            # Show success message
            info_msg = CANMessage(
                type="INFO",
                error_message=f"Log saved to {filename}",
                success=True
            )
            
            # Add message to appropriate widget based on view mode
            try:
                if self.current_view_mode in ["message_log", "split_view"]:
                    message_log = self.query_one("#message_log", MessageLogWidget)
                    message_log.add_message(info_msg)
                elif self.current_view_mode == "custom_view":
                    # Try to add to custom view console if available
                    try:
                        custom_widget = self.query_one("#custom_view_widget")
                        if hasattr(custom_widget, 'log_console'):
                            custom_widget.log_console(f"Log saved to {filename}", "info")
                    except Exception:
                        pass
            except Exception:
                pass
            
        except Exception as e:
            # Show error message
            error_msg = CANMessage(
                type="ERROR",
                error_message=f"Failed to save log: {str(e)}",
                success=False
            )
            
            # Add error message to appropriate widget based on view mode
            try:
                if self.current_view_mode in ["message_log", "split_view"]:
                    try:
                        message_log = self.query_one("#message_log", MessageLogWidget)
                        message_log.add_message(error_msg)
                    except Exception:
                        pass
                elif self.current_view_mode == "custom_view":
                    # Try to add to custom view console if available
                    try:
                        custom_widget = self.query_one("#custom_view_widget")
                        if hasattr(custom_widget, 'log_console'):
                            custom_widget.log_console(f"Failed to save log: {str(e)}", "error")
                    except Exception:
                        pass
            except Exception:
                pass
    
    def action_toggle_pause(self):
        """Toggle pause/resume message capture."""
        self.paused = not self.paused
        
        # Update button text if button exists
        try:
            pause_btn = self.query_one("#pause_btn", Button)
            pause_btn.label = "Resume" if self.paused else "Pause"
        except Exception:
            # No pause button (probably in custom view mode)
            pass
        
        status = "paused" if self.paused else "resumed"
        can_logger.info(f"PAUSE_TOGGLE: {status}")
        info_msg = CANMessage(
            type="INFO",
            error_message=f"Message capture {status}",
            success=True
        )
        
        # Try to add message to appropriate widget based on view mode
        try:
            if self.current_view_mode in ["message_log", "split_view"]:
                message_log = self.query_one("#message_log", MessageLogWidget)
                message_log.add_message(info_msg)
            elif self.current_view_mode == "custom_view":
                # Try to add to custom view console if available
                try:
                    custom_widget = self.query_one("#custom_view_widget")
                    if hasattr(custom_widget, 'log_console'):
                        custom_widget.log_console(f"Message capture {status}", "info")
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Could not add pause message to UI: {e}")
    
    def action_show_help(self):
        """Show help information in a modal."""
        help_modal = HelpModal()
        self.push_screen(help_modal)
    
    def action_close_modal(self):
        """Close the currently active modal, or show view settings if no modal is open."""
        # Check if there are any modal screens on the stack
        if len(self.screen_stack) > 1:
            # There's a modal open, let it handle the escape key
            # This will be handled by the modal screens themselves via escape binding
            pass
        else:
            # No modal is open, show the view settings modal
            self.action_show_view_settings()
    
    async def action_reconnect(self):
        """Reconnect to the CAN bridge device."""
        await self.serial_service.disconnect()
        await self.connect_to_device()
    
    def action_show_settings(self):
        """Show the settings modal."""
        current_port = self.serial_service.port
        current_baudrate = self.serial_service.baudrate
        
        def handle_settings_result(result):
            if result:  # User clicked Connect
                asyncio.create_task(self.apply_settings(result))
        
        modal = SettingsModal(current_port, current_baudrate)
        self.push_screen(modal, handle_settings_result)
    
    def action_show_view_settings(self):
        """Show the view selector modal."""
        logger.info(f"Opening view selector modal - current mode: {self.current_view_mode}")
        current_settings = {
            "view_mode": self.current_view_mode,
            "auto_switch": True,  # Default for now
            "enabled_views": {},
            "can_id_view_mappings": {}
        }
        
        def handle_view_settings_result(result):
            logger.info(f"View settings modal result: {result}")
            if result:  # User clicked Apply
                logger.info("User clicked Apply - calling apply_view_settings")
                self.apply_view_settings(result)
            else:
                logger.info("User cancelled view settings")
        
        modal = ViewSettingsModal(
            view_registry=self.view_registry,
            current_settings=current_settings
        )
        self.push_screen(modal, handle_view_settings_result)
    
    def _compose_main_panel(self) -> ComposeResult:
        """Compose the main panel content based on current view mode."""
        if self.current_view_mode == "custom_view":
            # Show custom view (switch dashboard for 0x500 messages)
            # yield SwitchViewWidget(id="switch_view")
            pass  # Temporarily disabled
        elif self.current_view_mode == "split_view":
            # Show both custom view and message log
            with Vertical():
                # yield SwitchViewWidget(id="switch_view")  # Temporarily disabled
                yield MessageLogWidget(id="message_log")
        else:
            # Default: message log only
            yield MessageLogWidget(id="message_log")
    
    def apply_view_settings(self, settings: dict):
        """Apply new view settings."""
        logger.info(f"Applying view settings: {settings}")
        can_logger.info(f"APPLY_VIEW_SETTINGS: {settings}")
        logger.debug(f"Applying view settings: {settings}")
        
        # Update current view mode
        old_view_mode = self.current_view_mode
        self.current_view_mode = settings.get("view_mode", "message_log")
        logger.debug(f"View mode change: '{old_view_mode}' -> '{self.current_view_mode}'")
        logger.debug(f"Settings received: {settings}")
        
        # Create debug logger if it doesn't exist
        debug_logger = logging.getLogger('view_debug')
        if not debug_logger.handlers:
            debug_handler = logging.FileHandler('/home/ril3y/UCAN/view_debug.log')
            debug_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            debug_logger.addHandler(debug_handler)
            debug_logger.setLevel(logging.DEBUG)
            debug_logger.propagate = False  # Prevent propagation to root logger (console output)
        
        debug_logger.info(f"apply_view_settings called")
        debug_logger.info(f"OLD view mode: '{old_view_mode}'")
        debug_logger.info(f"NEW view mode: '{self.current_view_mode}'")
        debug_logger.info(f"Settings: {settings}")
        
        # Auto-enable relevant dashboards for custom view mode
        if self.current_view_mode == "custom_view":
            enabled_views = settings.get("enabled_views", {})
            if "Switch Dashboard" not in enabled_views or not enabled_views["Switch Dashboard"]:
                enabled_views["Switch Dashboard"] = True
                logger.info("Auto-enabled Switch Dashboard for custom view mode")
        
        # Apply enabled/disabled state to views
        enabled_views = settings.get("enabled_views", {})
        for view_name, enabled in enabled_views.items():
            self.view_registry.set_view_enabled(view_name, enabled)
        
        # Apply CAN ID mappings
        can_id_mappings = settings.get("can_id_view_mappings", {})
        for can_id, view_name in can_id_mappings.items():
            if view_name != "Auto (priority based)":
                self.view_registry.add_can_id_mapping(can_id, view_name)
        
        # Log view mode update (no view manager needed anymore)
        logger.info(f"View mode updated to: {self.current_view_mode}")
        
        # Rebuild the UI if view mode changed
        if old_view_mode != self.current_view_mode:
            logger.info(f"View mode changed from {old_view_mode} to {self.current_view_mode} - rebuilding UI")
            logger.debug(f"View mode changed from {old_view_mode} to {self.current_view_mode}")
            self._rebuild_main_panel()
        else:
            logger.info(f"View mode unchanged: {self.current_view_mode}")
            logger.debug(f"View mode unchanged: {self.current_view_mode}")
        
        # Show confirmation message
        info_msg = CANMessage(
            type="INFO",
            error_message=f"View settings applied: Mode={self.current_view_mode}",
            success=True
        )
        # Try to add message to appropriate widget
        try:
            if self.current_view_mode in ["message_log", "split_view"]:
                message_log = self.query_one("#message_log", MessageLogWidget)
                message_log.add_message(info_msg)
            elif self.current_view_mode == "custom_view":
                # Add to switch view console if available
                # switch_view = self.query_one("#switch_view", SwitchViewWidget)
                switch_view.log_console(f"View mode changed to: {self.current_view_mode}", "info")
        except Exception as e:
            logger.warning(f"Could not add confirmation message to UI: {e}")
    
    def _rebuild_main_panel(self):
        """Rebuild the main panel with new view mode layout."""
        try:
            logger.info(f"Starting UI rebuild for view mode: {self.current_view_mode}")
            logger.debug(f"_rebuild_main_panel called with view mode: {self.current_view_mode}")
            
            # Debug logging
            debug_logger = logging.getLogger('view_debug')
            debug_logger.info(f"_rebuild_main_panel called")
            debug_logger.info(f"Current view mode: '{self.current_view_mode}'")
            
            # Control sidebar visibility based on view mode
            side_panel = self.query_one("#side_panel", Vertical)
            message_panel = self.query_one("#message_panel", Vertical)
            
            if self.current_view_mode.endswith("_view") and self.current_view_mode not in ["split_view"]:
                # Hide sidebar for custom views (not split_view)
                side_panel.display = False
                message_panel.styles.width = "100%"
                debug_logger.info("Sidebar hidden for custom view")
            else:
                # Show sidebar for message_log and split_view
                side_panel.display = True
                message_panel.styles.width = "75%"
                debug_logger.info("Sidebar shown for message_log/split_view")
            
            # Clear existing content from message panel
            message_panel.remove_children()
            
            # Add new content based on current view mode
            debug_logger = logging.getLogger('view_debug')
            
            if self.current_view_mode.endswith("_view") and self.current_view_mode != "split_view":
                # This is a specific custom view (e.g., "harness_switch_view")
                debug_logger.info(f"Detected custom view mode: {self.current_view_mode}")
                view_name = self._get_view_name_from_mode(self.current_view_mode)
                debug_logger.info(f"Converted to view name: {view_name}")
                logger.info(f"Creating widget for custom view: {view_name}")
                
                view = self.view_registry.get_view_by_name(view_name)
                if view:
                    debug_logger.info(f"Found view in registry: {view}")
                    # Use create_widget if available, otherwise fallback to get_widget_class
                    if hasattr(view, 'create_widget'):
                        # Create async wrapper for send command
                        async def send_command_wrapper(command: str):
                            await self.on_command_submitted(command)
                        
                        widget = view.create_widget(
                            send_command_callback=send_command_wrapper,
                            id="custom_view_widget"
                        )
                        debug_logger.info(f"Created widget using create_widget method")
                    else:
                        widget_class = view.get_widget_class()
                        debug_logger.info(f"Got widget class: {widget_class}")
                        widget = widget_class(id="custom_view_widget")
                    message_panel.mount(widget)
                    debug_logger.info(f"Mounted widget: {widget}")
                    
                    # Connect the widget to the view
                    self.view_registry.connect_view_widget(view_name, widget)
                    logger.info(f"Connected widget to {view_name}")
                    
                    # Register widget for direct CAN ID routing (simple approach)
                    if hasattr(view, 'get_supported_can_ids'):
                        can_ids = view.get_supported_can_ids()
                        self.set_active_view_widget(widget, can_ids)
                        logger.error(f"REGISTERED: {view_name} widget for CAN IDs {[f'0x{cid:03X}' for cid in can_ids]}")
                    
                    debug_logger.info(f"Successfully created custom view widget")
                else:
                    debug_logger.error(f"View {view_name} not found in registry")
                    logger.error(f"View {view_name} not found, falling back to message log")
                    # Fallback to message log
                    message_log = MessageLogWidget(id="message_log")
                    message_panel.mount(message_log)
                    message_log.set_filter(self.message_filter)
                    debug_logger.info(f"Fell back to message log widget")
            elif self.current_view_mode == "split_view":
                # Create both widgets - use first available view + message log
                available_views = self.view_registry.get_available_view_names()
                if available_views:
                    view_name = available_views[0]  # Use first available view
                    view = self.view_registry.get_view_by_name(view_name)
                    if view:
                        # Use create_widget if available, otherwise fallback to get_widget_class
                        if hasattr(view, 'create_widget'):
                            # Create async wrapper for send command
                            async def send_command_wrapper(command: str):
                                await self.on_command_submitted(command)
                            
                            custom_widget = view.create_widget(
                                send_command_callback=send_command_wrapper,
                                id="custom_view_widget"
                            )
                        else:
                            widget_class = view.get_widget_class()
                            custom_widget = widget_class(id="custom_view_widget")
                        custom_widget.styles.height = "50%"
                        message_panel.mount(custom_widget)
                        
                        # Connect the widget to the view
                        self.view_registry.connect_view_widget(view_name, custom_widget)
                        logger.info(f"Split view: connected {widget_class.__name__} to {view_name}")
                
                # Add message log
                message_log = MessageLogWidget(id="message_log")
                message_log.styles.height = "50%"
                message_panel.mount(message_log)
                message_log.set_filter(self.message_filter)
                logger.info("Split view mode setup complete")
            else:
                # Default: message log only
                debug_logger.info(f"Using default message log for view mode: {self.current_view_mode}")
                message_log = MessageLogWidget(id="message_log")
                message_panel.mount(message_log)
                message_log.set_filter(self.message_filter)
                debug_logger.info(f"Mounted default message log widget")
            
            # Force refresh
            message_panel.refresh()
            logger.info(f"Main panel rebuilt successfully for view mode: {self.current_view_mode}")
            can_logger.info(f"UI_REBUILD: view_mode={self.current_view_mode}")
            
        except Exception as e:
            logger.error(f"Failed to rebuild main panel: {e}", exc_info=True)
            can_logger.error(f"UI_REBUILD_ERROR: {e}")
    
    def _get_view_name_from_mode(self, view_mode: str) -> str:
        """Convert view mode string to actual view name."""
        # Convert snake_case mode to Title Case view name
        if view_mode == "harness_switch_view":
            return "Harness Switch View"
        elif view_mode == "throttle_gauge_view":
            return "Throttle Gauge View"
        else:
            # Generic conversion: "some_view_name" -> "Some View Name"
            words = view_mode.replace("_view", "").replace("_", " ").title()
            return f"{words} View"
    
    def _route_message_to_widgets(self, message: CANMessage, parsed_message=None):
        """Route messages directly to registered handlers (simple approach)."""
        try:
            logger.error(f"SIMPLE_ROUTE: CAN ID 0x{message.can_id:03X}, handlers: {list(self.can_id_handlers.keys())}")
            
            # Check if we have a direct handler for this CAN ID
            if message.can_id in self.can_id_handlers:
                widget = self.can_id_handlers[message.can_id]
                logger.error(f"SIMPLE_ROUTE: Found handler {type(widget).__name__} for CAN ID 0x{message.can_id:03X}")
                
                try:
                    # Route based on CAN ID to appropriate widget method
                    if message.can_id == 0x500 and hasattr(widget, 'update_switch_states'):
                        logger.error(f"SIMPLE_ROUTE: Calling update_switch_states for 0x{message.can_id:03X}")
                        widget.update_switch_states(message, parsed_message)
                    elif message.can_id == 0x600 and hasattr(widget, 'update_system_status'):
                        logger.error(f"SIMPLE_ROUTE: Calling update_system_status for 0x{message.can_id:03X}")
                        widget.update_system_status(message, parsed_message)
                    else:
                        logger.error(f"SIMPLE_ROUTE: Widget {type(widget).__name__} has no handler for CAN ID 0x{message.can_id:03X}")
                        
                except Exception as e:
                    logger.error(f"SIMPLE_ROUTE: Error calling widget method: {e}")
            else:
                # No direct handler - fall back to message log if in message_log mode
                if self.current_view_mode == "message_log":
                    try:
                        message_log = self.query_one("#message_log", MessageLogWidget)
                        message_log.add_message(message, parsed_message)
                        logger.debug("Added message to message log (no direct handler)")
                    except Exception as e:
                        logger.error(f"Failed to add message to message log: {e}")
                else:
                    logger.error(f"SIMPLE_ROUTE: No handler for CAN ID 0x{message.can_id:03X}, view_mode={self.current_view_mode}")
                        
        except Exception as e:
            logger.error(f"Error routing message: {e}")
            # Fallback: try to log somewhere
            try:
                message_log = self.query_one("#message_log", MessageLogWidget)
                message_log.add_message(message, parsed_message)
            except:
                pass  # Give up gracefully

    def register_can_id_handler(self, can_id: int, widget) -> None:
        """Register a widget to receive messages for a specific CAN ID."""
        logger.error(f"REGISTER_HANDLER: CAN ID 0x{can_id:03X} -> {type(widget).__name__}")
        self.can_id_handlers[can_id] = widget
    
    def unregister_can_id_handler(self, can_id: int) -> None:
        """Unregister a CAN ID handler."""
        if can_id in self.can_id_handlers:
            logger.error(f"UNREGISTER_HANDLER: CAN ID 0x{can_id:03X}")
            del self.can_id_handlers[can_id]
    
    def set_active_view_widget(self, widget, can_ids: List[int]) -> None:
        """Set the active view widget and register it for specific CAN IDs."""
        logger.error(f"SET_ACTIVE_VIEW: {type(widget).__name__} for CAN IDs {[f'0x{can_id:03X}' for can_id in can_ids]}")
        
        # Clear existing handlers
        self.can_id_handlers.clear()
        
        # Register new widget for all its CAN IDs
        self.active_view_widget = widget
        for can_id in can_ids:
            self.register_can_id_handler(can_id, widget)
    
    def clear_active_view_widget(self) -> None:
        """Clear the active view widget and all CAN ID handlers."""
        logger.error("CLEAR_ACTIVE_VIEW: Clearing all handlers")
        self.active_view_widget = None
        self.can_id_handlers.clear()
    
    async def apply_settings(self, settings: dict):
        """Apply new connection settings."""
        new_port = settings.get("port")
        new_baudrate = settings.get("baudrate", 115200)
        
        logger.info(f"Applying settings: port={new_port}, baudrate={new_baudrate}")
        can_logger.info(f"APPLY_SETTINGS: port={new_port}, baudrate={new_baudrate}")
        
        # Show status message
        info_msg = CANMessage(
            type="INFO",
            error_message=f"Applying settings: Port={new_port or 'auto'}, Baud={new_baudrate}",
            success=True
        )
        message_log = self.query_one("#message_log", MessageLogWidget)
        message_log.add_message(info_msg)
        
        
        # Only disconnect if currently connected
        if self.serial_service.is_connected:
            logger.info("Disconnecting current connection...")
            await self.serial_service.disconnect()
            
            # Force update UI to show disconnected state
            self.on_connection_change(False)
            
            # Small delay to ensure clean disconnect
            await asyncio.sleep(0.1)
        
        # Update serial service settings
        self.serial_service.port = new_port
        self.serial_service.baudrate = new_baudrate
        logger.info(f"Updated serial service: port={self.serial_service.port}, baudrate={self.serial_service.baudrate}")
        
        # Show disconnected status message
        disconnected_msg = CANMessage(
            type="INFO",
            error_message="Disconnected - attempting to reconnect...",
            success=True
        )
        message_log.add_message(disconnected_msg)
        
        # Small delay to show disconnected state
        await asyncio.sleep(0.5)
        
        # Re-establish callbacks (in case they were lost during disconnect)
        self.serial_service.set_message_callback(self.on_serial_message)
        self.serial_service.set_connection_callback(self.on_connection_change)
        
        # Attempt to reconnect with new settings
        logger.info("Attempting to reconnect...")
        await self.connect_to_device()
        
        # Force a status refresh after reconnection
        self.set_timer(0.5, self._refresh_connection_status)
    
    async def on_exit(self):
        """Clean up when exiting the application."""
        await self.serial_service.disconnect()


def run_app(port: str = None, baudrate: int = 115200):
    """Run the CAN bridge TUI application."""
    app = CANBridgeApp(port=port, baudrate=baudrate)
    app.run()
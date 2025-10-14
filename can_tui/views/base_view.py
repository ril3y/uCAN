"""
Abstract base class for modular CAN message views.

This provides a standard interface for creating custom visualization views
that can be auto-discovered and registered with the application.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, NamedTuple
from ..models.can_message import CANMessage
from ..parsers.base import ParsedMessage


class ParsedField(NamedTuple):
    """Simple parsed field structure for view-specific parsing."""
    name: str
    value: Any
    field_type: str = "raw"


class ViewParsedMessage:
    """Self-contained parsed message for views."""
    
    def __init__(self, can_id: int, raw_data: List[int]):
        self.can_id = can_id
        self.raw_data = raw_data
        self.fields: List[ParsedField] = []
        self.errors: List[str] = []
        self.parser_name = "view_parser"
        self.valid = True
    
    def add_field(self, name: str, value: Any, field_type: str = "raw") -> None:
        """Add a parsed field."""
        self.fields.append(ParsedField(name, value, field_type))
    
    def add_error(self, error: str) -> None:
        """Add a parsing error."""
        self.errors.append(error)
        self.valid = False
    
    def get_field_by_name(self, name: str) -> Optional[ParsedField]:
        """Get field by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None
    
    def is_valid(self) -> bool:
        """Check if parsing was successful."""
        return self.valid and len(self.errors) == 0


class BaseView(ABC):
    """
    Abstract base class for all custom CAN message views.
    
    Custom views should inherit from this class and implement all abstract methods.
    The view system will auto-discover classes that inherit from this base.
    """
    
    def __init__(self):
        self.message_count = 0
        self.error_count = 0
        self.enabled = True
        self.widget = None  # Will be set when widget is created
        
    @abstractmethod
    def get_view_name(self) -> str:
        """
        Return the human-readable name of this view.
        This will appear in the settings modal dropdown.
        
        Example: "Harness Switch View", "Throttle Gauge View"
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Return a brief description of what this view displays.
        
        Example: "Visual dashboard showing wiring harness switch states"
        """
        pass
    
    @abstractmethod
    def get_supported_can_ids(self) -> List[int]:
        """
        Return list of CAN IDs this view can handle.
        
        Example: [0x500], [0x100, 0x101], etc.
        """
        pass
    
    def get_widget_class(self):
        """
        Return the widget class that provides the UI for this view.
        
        This is now optional - views can override create_widget() instead
        for more complex widget composition.
        
        Example: SwitchViewWidget
        """
        return None
    
    @abstractmethod
    def create_widget(self, send_command_callback=None, toast_manager=None, **kwargs):
        """
        Create the main widget for this view.
        
        Views can compose multiple widgets and create complex layouts here.
        This method should return a single root widget that contains all
        the view's UI components.
        
        Args:
            send_command_callback: Callback for sending CAN commands
            toast_manager: Toast manager for notifications
            **kwargs: Additional arguments for widget creation
            
        Returns:
            Widget instance (usually a Container with composed widgets)
        """
        pass
    
    @abstractmethod
    def can_handle_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> bool:
        """
        Determine if this view can handle the given message.
        
        Args:
            can_message: Raw CAN message
            parsed_message: Parsed message data (may be None)
            
        Returns:
            True if this view should process this message
        """
        pass
    
    @abstractmethod
    def parse_message(self, can_message: CANMessage) -> Optional[ViewParsedMessage]:
        """
        Parse a CAN message using view-specific logic.
        
        Each view implements its own parsing logic for the CAN IDs it supports.
        This makes views self-contained and reduces dependency on external parsers.
        
        Args:
            can_message: Raw CAN message to parse
            
        Returns:
            ViewParsedMessage if parsing succeeded, None if message not supported
        """
        pass
    
    def update_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> None:
        """
        Process a new CAN message for this view.
        
        This method first attempts view-specific parsing, then falls back to
        external parsed message if available, then forwards to the widget.
        
        Args:
            can_message: Raw CAN message
            parsed_message: External parsed message data (may be None)
        """
        self.message_count += 1
        
        # Try view-specific parsing first
        view_parsed = self.parse_message(can_message)
        
        if view_parsed and view_parsed.is_valid():
            # Use view-specific parsing
            self._forward_to_widget(can_message, view_parsed)
        elif parsed_message:
            # Fall back to external parsing
            if not parsed_message.is_valid():
                self.error_count += 1
            self._forward_to_widget(can_message, parsed_message)
        else:
            # No parsing available - just send raw message
            self.error_count += 1
            self._forward_to_widget(can_message, None)
    
    def _forward_to_widget(self, can_message: CANMessage, parsed_data: Any) -> None:
        """Forward message to connected widget if available."""
        if self.widget and hasattr(self.widget, 'update_message_data'):
            try:
                self.widget.update_message_data(can_message, parsed_data)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error forwarding message to widget: {e}")
                self.error_count += 1
    
    def get_priority(self) -> int:
        """
        Return priority for message routing (higher = higher priority).
        Default priority is 1. Override to change priority.
        
        Returns:
            Priority as integer (1-10, where 10 is highest)
        """
        return 1
    
    @staticmethod
    def calculate_crc8(data: List[int], polynomial: int = 0x07) -> int:
        """
        Calculate CRC8 checksum for data validation.
        
        Args:
            data: List of bytes to calculate CRC for
            polynomial: CRC8 polynomial (default 0x07)
            
        Returns:
            CRC8 checksum value
        """
        crc = 0
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc = crc << 1
                crc &= 0xFF
        return crc
    
    @staticmethod
    def verify_crc8(data: List[int], expected_crc: int, polynomial: int = 0x07) -> bool:
        """
        Verify CRC8 checksum of data.
        
        Args:
            data: List of bytes to verify (excluding CRC byte)
            expected_crc: Expected CRC value
            polynomial: CRC8 polynomial (default 0x07)
            
        Returns:
            True if CRC is valid
        """
        calculated_crc = BaseView.calculate_crc8(data, polynomial)
        return calculated_crc == expected_crc
    
    def create_default_parsed_message(self, can_message: CANMessage) -> ViewParsedMessage:
        """
        Create a default parsed message with raw data fields.
        
        This can be used by views that don't need custom parsing or as a fallback.
        
        Args:
            can_message: Raw CAN message
            
        Returns:
            ViewParsedMessage with basic raw data fields
        """
        parsed = ViewParsedMessage(can_message.can_id, can_message.data)
        parsed.parser_name = f"{self.get_view_name()}_default"
        
        # Add raw data as hex fields
        for i, byte in enumerate(can_message.data):
            parsed.add_field(f"Byte_{i}", f"0x{byte:02X}", "hex")
        
        # Add common fields
        parsed.add_field("CAN_ID", f"0x{can_message.can_id:03X}", "hex")
        parsed.add_field("Data_Length", len(can_message.data), "integer")
        
        return parsed
    
    def is_enabled(self) -> bool:
        """Return whether this view is currently enabled."""
        return self.enabled
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this view."""
        self.enabled = enabled
    
    def reset(self) -> None:
        """Reset view state (message counts, etc.)."""
        self.message_count = 0
        self.error_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get view statistics.
        
        Returns:
            Dictionary with view statistics
        """
        return {
            "message_count": self.message_count,
            "error_count": self.error_count,
            "enabled": self.enabled,
            "supported_can_ids": [f"0x{can_id:03X}" for can_id in self.get_supported_can_ids()],
            "priority": self.get_priority()
        }
    
    def connect_widget(self, widget) -> None:
        """
        Connect this view to its UI widget.
        
        Args:
            widget: Instance of the widget class returned by get_widget_class()
        """
        self.widget = widget
    
    def disconnect_widget(self) -> None:
        """Disconnect the UI widget from this view."""
        self.widget = None


class ViewMetadata:
    """Metadata about a discovered view."""
    
    def __init__(self, view_class, module_name: str, file_path: str):
        self.view_class = view_class
        self.module_name = module_name
        self.file_path = file_path
        self.view_name = None
        self.description = None
        self.supported_can_ids = []
        
        # Try to get metadata from the class
        try:
            instance = view_class()
            self.view_name = instance.get_view_name()
            self.description = instance.get_description()
            self.supported_can_ids = instance.get_supported_can_ids()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not get metadata from {view_class.__name__}: {e}")
            self.view_name = view_class.__name__
            self.description = "No description available"
            self.supported_can_ids = []
    
    def __repr__(self):
        return f"ViewMetadata(name='{self.view_name}', can_ids={self.supported_can_ids})"
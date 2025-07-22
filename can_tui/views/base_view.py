"""
Abstract base class for modular CAN message views.

This provides a standard interface for creating custom visualization views
that can be auto-discovered and registered with the application.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..models.can_message import CANMessage
from ..parsers.base import ParsedMessage


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
    
    @abstractmethod
    def get_widget_class(self):
        """
        Return the widget class that provides the UI for this view.
        
        The widget class should be importable and have an __init__ method
        that accepts **kwargs.
        
        Example: SwitchViewWidget
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
    def update_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> None:
        """
        Process a new CAN message for this view.
        
        This method should update the view's internal state and/or
        forward the message to the associated widget.
        
        Args:
            can_message: Raw CAN message
            parsed_message: Parsed message data (may be None)
        """
        pass
    
    def get_priority(self) -> int:
        """
        Return priority for message routing (higher = higher priority).
        Default priority is 1. Override to change priority.
        
        Returns:
            Priority as integer (1-10, where 10 is highest)
        """
        return 1
    
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
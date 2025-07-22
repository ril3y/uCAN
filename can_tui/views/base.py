"""
Base classes and enums for the custom view system.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, List, Dict, Any

from ..models.can_message import CANMessage
from ..parsers.base import ParsedMessage


class ViewMode(Enum):
    """Available view modes."""
    MESSAGE_LOG = "message_log"      # Default message log view
    CUSTOM_VIEW = "custom_view"      # Custom visualization for specific CAN IDs
    SPLIT_VIEW = "split_view"        # Custom view + message log split


class BaseCustomView(ABC):
    """
    Abstract base class for custom CAN message visualization widgets.
    
    Custom views are specialized widgets that provide domain-specific
    visualization of CAN messages, such as switch dashboards, gauge displays,
    or protocol-specific decoders.
    
    Note: Subclasses should also inherit from appropriate Textual Widget classes.
    """
    
    def __init__(self, **kwargs):
        super().__init__()
        self.message_count = 0
        self.error_count = 0
        
    @abstractmethod
    def get_supported_can_ids(self) -> List[int]:
        """
        Return list of CAN IDs this view can handle.
        
        Returns:
            List of CAN message IDs this view supports
        """
        pass
    
    @abstractmethod
    def can_handle_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> bool:
        """
        Check if this view can handle the given CAN message.
        
        Args:
            can_message: Raw CAN message
            parsed_message: Parsed message (if available)
            
        Returns:
            True if this view can display the message
        """
        pass
    
    @abstractmethod
    def update_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> None:
        """
        Update the view with a new CAN message.
        
        Args:
            can_message: Raw CAN message
            parsed_message: Parsed message data (if available)
        """
        pass
    
    @abstractmethod
    def get_view_name(self) -> str:
        """
        Return the display name of this view.
        
        Returns:
            Human-readable view name
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Return a description of what this view displays.
        
        Returns:
            View description for settings/selection UI
        """
        pass
    
    def get_priority(self) -> int:
        """
        Get view priority for selection (1 = highest priority).
        
        Returns:
            Priority value (1-10, lower is higher priority)
        """
        return 5
    
    def reset(self) -> None:
        """Reset view state (message counts, displays, etc.)."""
        self.message_count = 0
        self.error_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get view statistics.
        
        Returns:
            Dictionary of view statistics
        """
        return {
            "message_count": self.message_count,
            "error_count": self.error_count,
            "view_name": self.get_view_name()
        }
    
    def is_enabled(self) -> bool:
        """Check if view is enabled."""
        return True
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the view."""
        pass  # Override in subclasses if needed


class MessageLogView(BaseCustomView):
    """
    Wrapper for the default message log view to fit into the custom view system.
    This allows the message log to be treated as just another view mode.
    """
    
    def __init__(self, message_log_widget, **kwargs):
        super().__init__(**kwargs)
        self.message_log = message_log_widget
        
    def get_supported_can_ids(self) -> List[int]:
        """Message log supports all CAN IDs."""
        return []  # Empty list means "all IDs"
    
    def can_handle_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> bool:
        """Message log can handle any message."""
        return True
    
    def update_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> None:
        """Update the message log."""
        if hasattr(self.message_log, 'add_message'):
            self.message_log.add_message(can_message, parsed_message)
        self.message_count += 1
        
        if parsed_message and not parsed_message.is_valid():
            self.error_count += 1
    
    def get_view_name(self) -> str:
        """Return view name."""
        return "Message Log"
    
    def get_description(self) -> str:
        """Return view description."""
        return "Default scrolling message log with all CAN traffic"
    
    def get_priority(self) -> int:
        """Lowest priority - fallback view."""
        return 10


class SplitView(BaseCustomView):
    """
    Composite view that combines a custom view with the message log.
    Useful for showing both specialized visualization and raw message data.
    """
    
    def __init__(self, custom_view: BaseCustomView, message_log_view: MessageLogView, **kwargs):
        super().__init__(**kwargs)
        self.custom_view = custom_view
        self.message_log_view = message_log_view
        
    def get_supported_can_ids(self) -> List[int]:
        """Support same CAN IDs as the custom view."""
        return self.custom_view.get_supported_can_ids()
    
    def can_handle_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> bool:
        """Can handle if either view can handle it."""
        return (self.custom_view.can_handle_message(can_message, parsed_message) or 
                self.message_log_view.can_handle_message(can_message, parsed_message))
    
    def update_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> None:
        """Update both views."""
        self.custom_view.update_message(can_message, parsed_message)
        self.message_log_view.update_message(can_message, parsed_message)
        self.message_count += 1
        
        if parsed_message and not parsed_message.is_valid():
            self.error_count += 1
    
    def get_view_name(self) -> str:
        """Return combined view name."""
        return f"{self.custom_view.get_view_name()} + Log"
    
    def get_description(self) -> str:
        """Return combined description."""
        return f"Split view: {self.custom_view.get_description()} with message log"
    
    def get_priority(self) -> int:
        """Same priority as the custom view."""
        return self.custom_view.get_priority()
    
    def reset(self) -> None:
        """Reset both views."""
        super().reset()
        self.custom_view.reset()
        self.message_log_view.reset()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined stats."""
        stats = super().get_stats()
        stats.update({
            "custom_view_stats": self.custom_view.get_stats(),
            "message_log_stats": self.message_log_view.get_stats()
        })
        return stats
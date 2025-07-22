"""
Switch state visualization view for CAN ID 0x500 wiring harness messages.
"""

from typing import List, Optional
from ..views.base import BaseCustomView
from ..models.can_message import CANMessage
from ..parsers.base import ParsedMessage


class SwitchView(BaseCustomView):
    """
    Custom view for visualizing wiring harness switch states.
    
    This view provides a specialized dashboard for CAN ID 0x500 messages
    that contain switch state information with visual indicators and
    real-time updates.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.supported_can_ids = [0x500]
        self.switch_widget = None  # Will be initialized when UI is created
    
    def get_supported_can_ids(self) -> List[int]:
        """Return supported CAN IDs."""
        return self.supported_can_ids
    
    def can_handle_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> bool:
        """Check if this view can handle the message."""
        # Check CAN ID
        if can_message.can_id not in self.supported_can_ids:
            return False
        
        # Verify message format if parsed
        if parsed_message:
            # Look for switch-related fields or specific parser
            parser_name = parsed_message.parser_name.lower()
            if "switch" in parser_name or "wiring harness" in parser_name:
                return True
            
            # Check for switch fields
            for field in parsed_message.fields:
                if "switch" in field.name.lower():
                    return True
        
        # Basic format check for 0x500 messages
        if (can_message.can_id == 0x500 and 
            len(can_message.data) == 8 and 
            can_message.data[0] == 0x5A and  # Signature
            can_message.data[7] == 0xFF):    # End marker
            return True
        
        return False
    
    def update_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> None:
        """Update the view with a new message."""
        self.message_count += 1
        
        if not parsed_message or not parsed_message.is_valid():
            self.error_count += 1
        
        # Update the switch widget if available (for UI integration)
        if self.switch_widget:
            self.switch_widget.update_switch_states(can_message, parsed_message)
    
    def get_view_name(self) -> str:
        """Return view name."""
        return "Switch Dashboard"
    
    def get_description(self) -> str:
        """Return view description."""
        return "Visual dashboard showing wiring harness switch states (CAN ID 0x500)"
    
    def get_priority(self) -> int:
        """High priority for switch messages."""
        return 2
    
    def reset(self) -> None:
        """Reset view state."""
        super().reset()
        # The switch widget will handle its own reset if needed
    
    def get_stats(self):
        """Get view statistics including switch widget stats."""
        base_stats = super().get_stats()
        widget_stats = self.switch_widget.get_stats() if self.switch_widget else {}
        
        return {
            **base_stats,
            "widget_stats": widget_stats,
            "supported_can_ids": [f"0x{can_id:03X}" for can_id in self.supported_can_ids]
        }
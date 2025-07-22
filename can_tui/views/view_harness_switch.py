"""
Wiring Harness Switch View - Visual dashboard for CAN ID 0x500 switch state messages.

This view provides a specialized visualization for wiring harness switch states
with real-time updates and visual indicators for each switch.
"""

from typing import List, Optional
from .base_view import BaseView
from ..models.can_message import CANMessage
from ..parsers.base import ParsedMessage


class HarnessSwitchView(BaseView):
    """
    View for visualizing wiring harness switch states from CAN ID 0x500.
    
    This view displays switch states as visual indicators in a grid layout
    with real-time updates when switch state messages are received.
    """
    
    def get_view_name(self) -> str:
        """Return the human-readable name of this view."""
        return "Harness Switch View"
    
    def get_description(self) -> str:
        """Return a description of what this view displays."""
        return "Visual dashboard showing wiring harness switch states (brake, eco, reverse, etc.)"
    
    def get_supported_can_ids(self) -> List[int]:
        """Return CAN IDs this view supports."""
        return [0x500]
    
    def get_widget_class(self):
        """Return the widget class for this view."""
        from ..widgets.switch_view import SwitchViewWidget
        return SwitchViewWidget
    
    def create_widget(self, send_command_callback=None, **kwargs):
        """Create widget instance with supported CAN IDs."""
        widget_class = self.get_widget_class()
        return widget_class(
            supported_can_ids=self.get_supported_can_ids(), 
            send_command_callback=send_command_callback,
            **kwargs
        )
    
    def get_priority(self) -> int:
        """High priority for switch messages."""
        return 8
    
    def can_handle_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> bool:
        """
        Check if this view can handle the message.
        
        This view handles CAN ID 0x500 messages that contain switch state data
        in the expected format: [0x5A][switch bitmap][timestamp 4 bytes][0x00][0xFF]
        """
        # Check CAN ID first
        if can_message.can_id != 0x500:
            return False
        
        # Verify message has correct length
        if len(can_message.data) != 8:
            return False
        
        # Check for expected signature and end marker
        if can_message.data[0] != 0x5A or can_message.data[7] != 0xFF:
            return False
        
        # If we have parsed data, verify it's from the switch parser
        if parsed_message:
            parser_name = parsed_message.parser_name.lower()
            if "switch" in parser_name or "wiring harness" in parser_name:
                return True
            
            # Check for switch-related fields
            for field in parsed_message.fields:
                if "switch" in field.name.lower():
                    return True
        
        # If no parsed data, but format matches, we can handle it
        return True
    
    def update_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> None:
        """
        Process a new switch state message.
        
        Updates internal counters and forwards the message to the connected
        widget for visual display.
        """
        self.message_count += 1
        
        # Check if message is valid
        if not parsed_message or not parsed_message.is_valid():
            self.error_count += 1
        
        # Forward to widget if connected
        if self.widget:
            try:
                self.widget.update_switch_states(can_message, parsed_message)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error updating switch widget: {e}")
                self.error_count += 1
    
    def get_stats(self) -> dict:
        """Get detailed statistics for this view."""
        base_stats = super().get_stats()
        
        # Add widget stats if available
        widget_stats = {}
        if self.widget and hasattr(self.widget, 'get_stats'):
            try:
                widget_stats = self.widget.get_stats()
            except Exception:
                pass
        
        return {
            **base_stats,
            "view_type": "Harness Switch Dashboard",
            "widget_stats": widget_stats,
            "can_message_format": "0x5A + switch_bitmap + timestamp(4) + 0x00 + 0xFF"
        }
    
    def reset(self) -> None:
        """Reset view and widget state."""
        super().reset()
        # Widget will handle its own reset if needed
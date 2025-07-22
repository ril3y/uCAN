"""
View registry and management system for custom CAN message visualizations.
"""

import logging
from typing import Dict, List, Optional, Tuple, Type, Any
from collections import defaultdict

from .base import BaseCustomView, ViewMode, MessageLogView, SplitView
from ..models.can_message import CANMessage
from ..parsers.base import ParsedMessage

logger = logging.getLogger(__name__)


class ViewRegistry:
    """Registry for managing custom view widgets."""
    
    def __init__(self):
        self.views: Dict[str, BaseCustomView] = {}
        self.can_id_mappings: Dict[int, str] = {}
        self.priority_mappings: Dict[int, List[str]] = defaultdict(list)
        self.enabled_views: Dict[str, bool] = {}
        
    def register_view(self, view: BaseCustomView) -> None:
        """
        Register a custom view.
        
        Args:
            view: Custom view instance to register
        """
        if not isinstance(view, BaseCustomView):
            raise ValueError(f"View must be an instance of BaseCustomView, got {type(view)}")
        
        view_name = view.get_view_name()
        self.views[view_name] = view
        self.enabled_views[view_name] = view.is_enabled()
        
        # Add to priority mappings
        priority = view.get_priority()
        if view_name not in self.priority_mappings[priority]:
            self.priority_mappings[priority].append(view_name)
        
        # Auto-register CAN ID mappings
        for can_id in view.get_supported_can_ids():
            self.add_can_id_mapping(can_id, view_name)
        
        logger.info(f"Registered view: {view_name}")
    
    def unregister_view(self, view_name: str) -> bool:
        """
        Unregister a view by name.
        
        Args:
            view_name: View name to unregister
            
        Returns:
            True if view was found and removed
        """
        if view_name in self.views:
            view = self.views[view_name]
            
            # Remove CAN ID mappings
            can_ids_to_remove = []
            for can_id, mapped_name in self.can_id_mappings.items():
                if mapped_name == view_name:
                    can_ids_to_remove.append(can_id)
            
            for can_id in can_ids_to_remove:
                del self.can_id_mappings[can_id]
            
            # Remove from priority mappings
            for priority_list in self.priority_mappings.values():
                if view_name in priority_list:
                    priority_list.remove(view_name)
            
            # Remove from registry
            del self.views[view_name]
            del self.enabled_views[view_name]
            
            logger.info(f"Unregistered view: {view_name}")
            return True
        
        return False
    
    def get_view(self, view_name: str) -> Optional[BaseCustomView]:
        """
        Get a view by name.
        
        Args:
            view_name: View name
            
        Returns:
            View instance or None if not found
        """
        return self.views.get(view_name)
    
    def get_all_views(self) -> Dict[str, BaseCustomView]:
        """Get all registered views."""
        return self.views.copy()
    
    def get_enabled_views(self) -> Dict[str, BaseCustomView]:
        """Get all enabled views."""
        return {name: view for name, view in self.views.items() 
                if self.enabled_views.get(name, True)}
    
    def add_can_id_mapping(self, can_id: int, view_name: str) -> None:
        """
        Add a CAN ID to view mapping.
        
        Args:
            can_id: CAN message ID
            view_name: View name
        """
        if view_name not in self.views:
            raise ValueError(f"View '{view_name}' not registered")
        
        self.can_id_mappings[can_id] = view_name
        logger.debug(f"Added CAN ID mapping: 0x{can_id:03X} -> {view_name}")
    
    def remove_can_id_mapping(self, can_id: int) -> bool:
        """
        Remove a CAN ID mapping.
        
        Args:
            can_id: CAN message ID
            
        Returns:
            True if mapping was removed
        """
        if can_id in self.can_id_mappings:
            del self.can_id_mappings[can_id]
            logger.debug(f"Removed CAN ID mapping: 0x{can_id:03X}")
            return True
        return False
    
    def get_view_for_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> Optional[BaseCustomView]:
        """
        Find the best view for a CAN message.
        
        Args:
            can_message: CAN message
            parsed_message: Parsed message data
            
        Returns:
            Best matching view or None
        """
        # Check direct CAN ID mapping first
        if can_message.can_id in self.can_id_mappings:
            view_name = self.can_id_mappings[can_message.can_id]
            view = self.views.get(view_name)
            if view and self.enabled_views.get(view_name, True):
                return view
        
        # Check if any view can handle this message (by priority)
        candidate_views = []
        
        for view_name, view in self.views.items():
            if (self.enabled_views.get(view_name, True) and 
                view.can_handle_message(can_message, parsed_message)):
                candidate_views.append((view.get_priority(), view_name, view))
        
        # Sort by priority (lower number = higher priority)
        candidate_views.sort(key=lambda x: x[0])
        
        if candidate_views:
            return candidate_views[0][2]  # Return the view
        
        return None
    
    def set_view_enabled(self, view_name: str, enabled: bool) -> bool:
        """
        Enable or disable a view.
        
        Args:
            view_name: View name
            enabled: Enable state
            
        Returns:
            True if view was found and updated
        """
        if view_name in self.views:
            self.enabled_views[view_name] = enabled
            view = self.views[view_name]
            if hasattr(view, 'set_enabled'):
                view.set_enabled(enabled)
            logger.info(f"Set view {view_name} enabled: {enabled}")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        enabled_count = sum(1 for enabled in self.enabled_views.values() if enabled)
        total_count = len(self.views)
        
        return {
            "total_views": total_count,
            "enabled_views": enabled_count,
            "disabled_views": total_count - enabled_count,
            "can_id_mappings": len(self.can_id_mappings),
            "registered_can_ids": list(self.can_id_mappings.keys())
        }


class ViewManager:
    """
    Manager for switching between different view modes and handling message routing.
    """
    
    def __init__(self, view_registry: ViewRegistry, default_message_log=None):
        self.view_registry = view_registry
        self.current_mode = ViewMode.MESSAGE_LOG
        self.current_view: Optional[BaseCustomView] = None
        self.message_log_view: Optional[MessageLogView] = None
        self.active_can_ids: set[int] = set()
        
        # Set up message log view if provided
        if default_message_log:
            self.message_log_view = MessageLogView(default_message_log)
    
    def set_view_mode(self, mode: ViewMode) -> bool:
        """
        Set the current view mode.
        
        Args:
            mode: View mode to switch to
            
        Returns:
            True if mode was successfully changed
        """
        if mode == self.current_mode:
            return True
        
        old_mode = self.current_mode
        self.current_mode = mode
        
        logger.info(f"View mode changed: {old_mode.value} -> {mode.value}")
        return True
    
    def get_current_mode(self) -> ViewMode:
        """Get the current view mode."""
        return self.current_mode
    
    def set_active_can_ids(self, can_ids: List[int]) -> None:
        """
        Set which CAN IDs should trigger custom view switches.
        
        Args:
            can_ids: List of CAN IDs to monitor for custom views
        """
        self.active_can_ids = set(can_ids)
        logger.info(f"Set active CAN IDs for custom views: {[f'0x{can_id:03X}' for can_id in can_ids]}")
    
    def process_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage]) -> Optional[BaseCustomView]:
        """
        Process a CAN message and determine which view should handle it.
        
        Args:
            can_message: CAN message
            parsed_message: Parsed message data
            
        Returns:
            View that should handle the message, or None
        """
        if self.current_mode == ViewMode.MESSAGE_LOG:
            # Always use message log in message log mode
            if self.message_log_view:
                self.message_log_view.update_message(can_message, parsed_message)
                return self.message_log_view
            return None
        
        elif self.current_mode == ViewMode.CUSTOM_VIEW:
            # Try to find a custom view for this message
            custom_view = self.view_registry.get_view_for_message(can_message, parsed_message)
            if custom_view:
                custom_view.update_message(can_message, parsed_message)
                self.current_view = custom_view
                return custom_view
            
            # Fall back to message log if no custom view found
            if self.message_log_view:
                self.message_log_view.update_message(can_message, parsed_message)
                return self.message_log_view
            return None
        
        elif self.current_mode == ViewMode.SPLIT_VIEW:
            # Use split view if available
            custom_view = self.view_registry.get_view_for_message(can_message, parsed_message)
            if custom_view and self.message_log_view:
                # Create or reuse split view
                if (not isinstance(self.current_view, SplitView) or 
                    self.current_view.custom_view != custom_view):
                    self.current_view = SplitView(custom_view, self.message_log_view)
                
                self.current_view.update_message(can_message, parsed_message)
                return self.current_view
            
            # Fall back to message log
            if self.message_log_view:
                self.message_log_view.update_message(can_message, parsed_message)
                return self.message_log_view
            return None
        
        return None
    
    def get_current_view(self) -> Optional[BaseCustomView]:
        """Get the currently active view."""
        return self.current_view
    
    def get_available_modes(self) -> List[ViewMode]:
        """Get list of available view modes."""
        return list(ViewMode)
    
    def get_custom_views_for_can_ids(self, can_ids: List[int]) -> Dict[int, List[str]]:
        """
        Get available custom views for specific CAN IDs.
        
        Args:
            can_ids: List of CAN IDs to check
            
        Returns:
            Dictionary mapping CAN ID to list of available view names
        """
        result = {}
        
        for can_id in can_ids:
            available_views = []
            for view_name, view in self.view_registry.get_enabled_views().items():
                if (can_id in view.get_supported_can_ids() or 
                    not view.get_supported_can_ids()):  # Empty list means supports all
                    available_views.append(view_name)
            
            if available_views:
                result[can_id] = available_views
        
        return result
    
    def reset_all_views(self) -> None:
        """Reset state for all views."""
        for view in self.view_registry.get_all_views().values():
            view.reset()
        
        if self.message_log_view:
            self.message_log_view.reset()
        
        self.current_view = None
        logger.info("Reset all view states")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get view manager statistics."""
        stats = {
            "current_mode": self.current_mode.value,
            "active_can_ids": list(self.active_can_ids),
            "current_view": self.current_view.get_view_name() if self.current_view else None,
            "registry_stats": self.view_registry.get_stats()
        }
        
        if self.current_view:
            stats["current_view_stats"] = self.current_view.get_stats()
        
        return stats
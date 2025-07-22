"""
Modern view registry system with auto-discovery support.

This replaces the old registry system with a more modular approach
that automatically discovers and registers views from the filesystem.
"""

import logging
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict

from .base_view import BaseView
from .discovery import view_discovery, get_available_views, create_view
from ..models.can_message import CANMessage
from ..parsers.base import ParsedMessage

logger = logging.getLogger(__name__)


class ModernViewRegistry:
    """
    Modern view registry with automatic discovery and registration.
    
    This registry automatically discovers view classes that inherit from BaseView
    and provides a clean interface for managing and routing messages to views.
    """
    
    def __init__(self):
        """Initialize the modern view registry."""
        self.registered_views: Dict[str, BaseView] = {}
        self.can_id_mappings: Dict[int, str] = {}
        self.enabled_views: Set[str] = set()
        self.discovery_complete = False
        
        # Automatically discover and register views
        self._auto_discover_views()
    
    def _auto_discover_views(self) -> None:
        """Automatically discover and register all available views."""
        try:
            logger.info("Starting automatic view discovery...")
            
            # Get all discovered views
            discovered_views = get_available_views()
            
            if not discovered_views:
                logger.warning("No views discovered - check views directory")
                return
            
            # Register each discovered view
            for view_name, metadata in discovered_views.items():
                try:
                    # Create instance of the view
                    view_instance = create_view(view_name)
                    
                    # Register the view
                    self.registered_views[view_name] = view_instance
                    self.enabled_views.add(view_name)
                    
                    # Auto-register CAN ID mappings
                    for can_id in view_instance.get_supported_can_ids():
                        if can_id not in self.can_id_mappings:
                            self.can_id_mappings[can_id] = view_name
                            logger.debug(f"Mapped CAN ID 0x{can_id:03X} to {view_name}")
                    
                    logger.info(f"Registered view: {view_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to register view {view_name}: {e}")
            
            self.discovery_complete = True
            logger.info(f"View discovery complete. Registered {len(self.registered_views)} views.")
            
        except Exception as e:
            logger.error(f"Auto-discovery failed: {e}")
    
    def get_available_view_names(self) -> List[str]:
        """Get list of all available view names."""
        return list(self.registered_views.keys())
    
    def get_view_by_name(self, view_name: str) -> Optional[BaseView]:
        """Get a view instance by name."""
        return self.registered_views.get(view_name)
    
    def is_view_enabled(self, view_name: str) -> bool:
        """Check if a view is enabled."""
        return view_name in self.enabled_views
    
    def set_view_enabled(self, view_name: str, enabled: bool) -> bool:
        """
        Enable or disable a view.
        
        Args:
            view_name: Name of the view to enable/disable
            enabled: True to enable, False to disable
            
        Returns:
            True if operation succeeded, False if view not found
        """
        if view_name not in self.registered_views:
            logger.warning(f"Cannot enable/disable unknown view: {view_name}")
            return False
        
        view = self.registered_views[view_name]
        view.set_enabled(enabled)
        
        if enabled:
            self.enabled_views.add(view_name)
        else:
            self.enabled_views.discard(view_name)
        
        logger.info(f"View {view_name} {'enabled' if enabled else 'disabled'}")
        return True
    
    def get_enabled_views(self) -> Dict[str, BaseView]:
        """Get all enabled views."""
        return {name: view for name, view in self.registered_views.items() 
                if name in self.enabled_views and view.is_enabled()}
    
    def get_views_for_can_id(self, can_id: int) -> List[BaseView]:
        """
        Get all enabled views that can handle a specific CAN ID.
        
        Args:
            can_id: CAN ID to search for
            
        Returns:
            List of views that can handle this CAN ID, sorted by priority
        """
        matching_views = []
        
        for view_name, view in self.get_enabled_views().items():
            if can_id in view.get_supported_can_ids():
                matching_views.append(view)
        
        # Sort by priority (highest first)
        matching_views.sort(key=lambda v: v.get_priority(), reverse=True)
        return matching_views
    
    def route_message(self, can_message: CANMessage, parsed_message: Optional[ParsedMessage] = None) -> List[str]:
        """
        Route a message to appropriate views.
        
        Args:
            can_message: The CAN message to route
            parsed_message: Parsed message data (optional)
            
        Returns:
            List of view names that processed the message
        """
        processed_by = []
        
        # Get views that can handle this CAN ID
        candidate_views = self.get_views_for_can_id(can_message.can_id)
        
        for view in candidate_views:
            try:
                # Check if view can handle this specific message
                if view.can_handle_message(can_message, parsed_message):
                    view.update_message(can_message, parsed_message)
                    processed_by.append(view.get_view_name())
                    logger.debug(f"Message 0x{can_message.can_id:03X} processed by {view.get_view_name()}")
            except Exception as e:
                logger.error(f"Error routing message to {view.get_view_name()}: {e}")
        
        return processed_by
    
    def connect_view_widget(self, view_name: str, widget) -> bool:
        """
        Connect a widget to a view.
        
        Args:
            view_name: Name of the view
            widget: Widget instance to connect
            
        Returns:
            True if connection succeeded
        """
        view = self.get_view_by_name(view_name)
        if not view:
            logger.error(f"Cannot connect widget - view {view_name} not found")
            return False
        
        try:
            view.connect_widget(widget)
            logger.info(f"Connected widget to view {view_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect widget to {view_name}: {e}")
            return False
    
    def disconnect_view_widget(self, view_name: str) -> bool:
        """
        Disconnect widget from a view.
        
        Args:
            view_name: Name of the view
            
        Returns:
            True if disconnection succeeded
        """
        view = self.get_view_by_name(view_name)
        if not view:
            return False
        
        try:
            view.disconnect_widget()
            logger.info(f"Disconnected widget from view {view_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect widget from {view_name}: {e}")
            return False
    
    def get_view_options_for_settings(self) -> List[tuple]:
        """
        Get view options formatted for settings modal dropdown.
        
        Returns:
            List of (value, description) tuples for dropdown options
        """
        # Textual Select expects (description, value) tuples
        options = [
            ("Message Log - Traditional scrolling message display", "message_log")
        ]
        
        # Add each registered view
        for view_name, view in self.registered_views.items():
            try:
                description = f"{view_name} - {view.get_description()}"
                key = view_name.lower().replace(" ", "_")
                options.append((description, key))
            except Exception as e:
                logger.warning(f"Could not get description for {view_name}: {e}")
                key = view_name.lower().replace(" ", "_")
                options.append((view_name, key))
        
        # Add split view option
        if len(self.registered_views) > 0:
            options.append(("Split View - Custom view + message log", "split_view"))
        
        return options
    
    def refresh_discovery(self) -> None:
        """Force refresh of view discovery."""
        logger.info("Refreshing view discovery...")
        self.registered_views.clear()
        self.enabled_views.clear()
        self.can_id_mappings.clear()
        self.discovery_complete = False
        self._auto_discover_views()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        enabled_count = len(self.enabled_views)
        total_count = len(self.registered_views)
        
        view_details = {}
        for view_name, view in self.registered_views.items():
            try:
                view_details[view_name] = view.get_stats()
            except Exception as e:
                view_details[view_name] = {"error": str(e)}
        
        return {
            "total_views": total_count,
            "enabled_views": enabled_count,
            "disabled_views": total_count - enabled_count,
            "can_id_mappings": len(self.can_id_mappings),
            "discovery_complete": self.discovery_complete,
            "view_details": view_details
        }
"""
Auto-discovery system for modular CAN message views.

This system automatically finds and registers view classes that inherit
from BaseView, allowing for easy addition of new views by simply
dropping files into the views directory.
"""

import os
import importlib
import inspect
from pathlib import Path
from typing import List, Dict, Type
import logging

from .base_view import BaseView, ViewMetadata

logger = logging.getLogger(__name__)


class ViewDiscovery:
    """
    Discovers and manages view classes automatically.
    
    Scans the views directory for Python files containing classes
    that inherit from BaseView and makes them available for registration.
    """
    
    def __init__(self, views_package: str = "can_tui.views"):
        """
        Initialize view discovery.
        
        Args:
            views_package: Package name where views are located
        """
        self.views_package = views_package
        self.discovered_views: Dict[str, ViewMetadata] = {}
        self._discovery_attempted = False
    
    def discover_views(self, force_refresh: bool = False) -> Dict[str, ViewMetadata]:
        """
        Discover all available view classes.
        
        Args:
            force_refresh: If True, re-scan even if already discovered
            
        Returns:
            Dictionary mapping view names to ViewMetadata objects
        """
        if self._discovery_attempted and not force_refresh:
            return self.discovered_views
        
        self._discovery_attempted = True
        self.discovered_views.clear()
        
        logger.info("Starting view discovery...")
        
        try:
            views_dir = self._get_views_directory()
            if not views_dir.exists():
                logger.warning(f"Views directory not found: {views_dir}")
                return self.discovered_views
            
            # Find all Python files in views directory
            view_files = list(views_dir.glob("view_*.py"))
            logger.info(f"Found {len(view_files)} potential view files: {[f.name for f in view_files]}")
            
            for view_file in view_files:
                try:
                    self._discover_views_in_file(view_file)
                except Exception as e:
                    logger.error(f"Error discovering views in {view_file.name}: {e}")
            
            logger.info(f"Discovery complete. Found {len(self.discovered_views)} views:")
            for name, metadata in self.discovered_views.items():
                logger.info(f"  - {name}: {metadata.description} (CAN IDs: {metadata.supported_can_ids})")
            
        except Exception as e:
            logger.error(f"View discovery failed: {e}")
        
        return self.discovered_views
    
    def _get_views_directory(self) -> Path:
        """Get the path to the views directory."""
        # Get the directory where this file is located
        current_dir = Path(__file__).parent
        return current_dir
    
    def _discover_views_in_file(self, view_file: Path) -> None:
        """
        Discover view classes in a specific file.
        
        Args:
            view_file: Path to the Python file to scan
        """
        try:
            # Convert file path to module name
            module_name = f"{self.views_package}.{view_file.stem}"
            logger.debug(f"Importing module: {module_name}")
            
            # Import the module
            module = importlib.import_module(module_name)
            
            # Find all classes in the module that inherit from BaseView
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (obj != BaseView and 
                    issubclass(obj, BaseView) and 
                    obj.__module__ == module_name):
                    
                    logger.debug(f"Found view class: {name} in {module_name}")
                    
                    # Create metadata for this view
                    metadata = ViewMetadata(obj, module_name, str(view_file))
                    
                    if metadata.view_name and metadata.view_name not in self.discovered_views:
                        self.discovered_views[metadata.view_name] = metadata
                        logger.info(f"Registered view: {metadata.view_name}")
                    else:
                        logger.warning(f"Skipping duplicate or invalid view: {name}")
        
        except Exception as e:
            logger.error(f"Failed to import/process {view_file.name}: {e}")
    
    def get_view_names(self) -> List[str]:
        """Get list of all discovered view names."""
        return list(self.discovered_views.keys())
    
    def get_view_metadata(self, view_name: str) -> ViewMetadata:
        """Get metadata for a specific view."""
        return self.discovered_views.get(view_name)
    
    def create_view_instance(self, view_name: str) -> BaseView:
        """
        Create an instance of the specified view.
        
        Args:
            view_name: Name of the view to create
            
        Returns:
            Instance of the view class
            
        Raises:
            ValueError: If view name is not found
        """
        metadata = self.discovered_views.get(view_name)
        if not metadata:
            raise ValueError(f"View '{view_name}' not found. Available views: {list(self.discovered_views.keys())}")
        
        try:
            return metadata.view_class()
        except Exception as e:
            logger.error(f"Failed to create instance of view '{view_name}': {e}")
            raise
    
    def get_views_for_can_id(self, can_id: int) -> List[str]:
        """
        Get list of view names that support a specific CAN ID.
        
        Args:
            can_id: CAN ID to search for
            
        Returns:
            List of view names that support this CAN ID
        """
        matching_views = []
        for view_name, metadata in self.discovered_views.items():
            if can_id in metadata.supported_can_ids:
                matching_views.append(view_name)
        return matching_views
    
    def refresh_views(self) -> Dict[str, ViewMetadata]:
        """Force refresh of discovered views."""
        return self.discover_views(force_refresh=True)


# Global instance for easy access
view_discovery = ViewDiscovery()


def get_available_views() -> Dict[str, ViewMetadata]:
    """Get all available views (discovers if not already done)."""
    return view_discovery.discover_views()


def get_view_names() -> List[str]:
    """Get list of all available view names."""
    return view_discovery.get_view_names()


def create_view(view_name: str) -> BaseView:
    """Create an instance of the specified view."""
    return view_discovery.create_view_instance(view_name)


def refresh_view_discovery() -> Dict[str, ViewMetadata]:
    """Force refresh of view discovery."""
    return view_discovery.refresh_views()
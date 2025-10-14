"""
Modern view system for CAN message visualization.

This module provides a self-contained framework for creating and managing custom 
visualization views with automatic discovery, parsing, and widget composition.
"""

from .base_view import BaseView, ViewParsedMessage
from .discovery import get_available_views, create_view, view_discovery
from .modern_registry import ModernViewRegistry

# Import available view classes
from .view_console import ConsoleView
from .view_harness_switch import HarnessSwitchView

__all__ = [
    "BaseView",
    "ViewParsedMessage",
    "get_available_views", 
    "create_view",
    "view_discovery",
    "ModernViewRegistry",
    "ConsoleView",
    "HarnessSwitchView"
]
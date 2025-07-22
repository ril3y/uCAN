"""
Custom view system for CAN message visualization.

This module provides a framework for creating and managing custom visualization
widgets for specific CAN message types, beyond the default message log display.
"""

from .base import BaseCustomView, ViewMode
from .registry import ViewRegistry, ViewManager
from .switch_view import SwitchView

__all__ = [
    "BaseCustomView",
    "ViewMode", 
    "ViewRegistry",
    "ViewManager",
    "SwitchView"
]
"""
Toast notification widget for temporary user feedback.

Provides temporary notifications that auto-dismiss and can be stacked.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from typing import Literal, Optional
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

ToastType = Literal["info", "success", "warning", "error"]


class ToastItem(Static):
    """Individual toast notification item."""
    
    DEFAULT_CSS = """
    ToastItem {
        width: auto;
        max-width: 60;
        height: auto;
        margin: 1 0;
        padding: 1 2;
        border: thick;
        text-align: center;
        opacity: 0.95;
    }
    
    ToastItem.toast-info {
        background: $primary;
        color: $text;
        border: thick $primary-lighten-1;
    }
    
    ToastItem.toast-success {
        background: $success;
        color: $text;
        border: thick $success-lighten-1;
    }
    
    ToastItem.toast-warning {
        background: $warning;
        color: $text;
        border: thick $warning-lighten-1;
    }
    
    ToastItem.toast-error {
        background: $error;
        color: $text;
        border: thick $error-lighten-1;
    }
    
    ToastItem.toast-dismissing {
        opacity: 0.3;
    }
    """
    
    def __init__(self, message: str, toast_type: ToastType = "info", duration: float = 3.0, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.toast_type = toast_type
        self.duration = duration
        self.dismiss_time = datetime.now() + timedelta(seconds=duration)
        self.dismissing = False
        
        # Set the CSS class for styling
        self.add_class(f"toast-{toast_type}")
        
        # Set the content with emoji
        emoji_map = {
            "info": "ℹ️",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌"
        }
        emoji = emoji_map.get(toast_type, "ℹ️")
        self.update(f"{emoji} {message}")
    
    def start_auto_dismiss(self) -> None:
        """Start the auto-dismiss timer."""
        async def auto_dismiss():
            await asyncio.sleep(self.duration)
            if not self.dismissing:
                await self.dismiss()
        
        asyncio.create_task(auto_dismiss())
    
    async def dismiss(self) -> None:
        """Dismiss this toast with animation."""
        if self.dismissing:
            return
            
        self.dismissing = True
        self.add_class("toast-dismissing")
        
        # Wait for fade animation
        await asyncio.sleep(0.3)
        
        # Remove from parent
        if self.parent:
            self.parent.remove(self)


class ToastContainer(Container):
    """Container for stacking toast notifications."""
    
    DEFAULT_CSS = """
    ToastContainer {
        dock: top;
        height: auto;
        width: 100%;
        layer: toast;
        margin: 1 0;
        padding: 0;
        background: transparent;
        z-index: 1000;
    }
    
    ToastContainer > Vertical {
        height: auto;
        width: auto;
        align: center top;
        background: transparent;
    }
    """
    
    def __init__(self, max_toasts: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.max_toasts = max_toasts
        self.toasts: list[ToastItem] = []
    
    def compose(self) -> ComposeResult:
        """Compose the toast container."""
        with Vertical(id="toast_stack"):
            pass
    
    def show_toast(self, message: str, toast_type: ToastType = "info", duration: float = 3.0) -> ToastItem:
        """
        Show a new toast notification.
        
        Args:
            message: The message to display
            toast_type: Type of toast (info, success, warning, error)
            duration: How long to show the toast in seconds
            
        Returns:
            The created ToastItem
        """
        # Remove old toasts if we're at the limit
        while len(self.toasts) >= self.max_toasts:
            old_toast = self.toasts.pop(0)
            asyncio.create_task(old_toast.dismiss())
        
        # Create new toast
        toast = ToastItem(message, toast_type, duration)
        self.toasts.append(toast)
        
        try:
            # Add to the stack
            stack = self.query_one("#toast_stack", Vertical)
            stack.mount(toast)
            
            # Start auto-dismiss
            toast.start_auto_dismiss()
            
            logger.debug(f"Showed {toast_type} toast: {message}")
            
        except Exception as e:
            logger.error(f"Failed to show toast: {e}")
            # Remove from our list if mounting failed
            if toast in self.toasts:
                self.toasts.remove(toast)
        
        return toast
    
    def clear_all_toasts(self) -> None:
        """Clear all active toasts immediately."""
        for toast in self.toasts[:]:  # Copy list to avoid modification during iteration
            asyncio.create_task(toast.dismiss())
        self.toasts.clear()
    
    def remove_toast(self, toast: ToastItem) -> None:
        """Remove a specific toast from tracking."""
        if toast in self.toasts:
            self.toasts.remove(toast)


class ToastManager:
    """
    Global toast manager for easy access across the application.
    
    Usage:
        toast_manager.show("Message sent successfully!", "success")
        toast_manager.error("Failed to connect to device")
        toast_manager.warning("Connection unstable")
    """
    
    def __init__(self):
        self.container: Optional[ToastContainer] = None
    
    def set_container(self, container: ToastContainer) -> None:
        """Set the toast container to use for notifications."""
        self.container = container
    
    def show(self, message: str, toast_type: ToastType = "info", duration: float = 3.0) -> Optional[ToastItem]:
        """Show a toast notification."""
        if self.container:
            return self.container.show_toast(message, toast_type, duration)
        else:
            logger.warning(f"No toast container set - would show: {message}")
            return None
    
    def info(self, message: str, duration: float = 3.0) -> Optional[ToastItem]:
        """Show an info toast."""
        return self.show(message, "info", duration)
    
    def success(self, message: str, duration: float = 3.0) -> Optional[ToastItem]:
        """Show a success toast."""
        return self.show(message, "success", duration)
    
    def warning(self, message: str, duration: float = 3.0) -> Optional[ToastItem]:
        """Show a warning toast."""
        return self.show(message, "warning", duration)
    
    def error(self, message: str, duration: float = 5.0) -> Optional[ToastItem]:
        """Show an error toast (longer duration by default)."""
        return self.show(message, "error", duration)
    
    def clear_all(self) -> None:
        """Clear all active toasts."""
        if self.container:
            self.container.clear_all_toasts()


# Global toast manager instance
toast_manager = ToastManager()
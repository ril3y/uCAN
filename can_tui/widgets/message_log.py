from textual.widgets import RichLog
from textual.reactive import reactive
from textual.binding import Binding
from rich.text import Text
from rich.table import Table
from typing import List, Optional
from collections import deque

from ..models.can_message import CANMessage, MessageFilter
from ..parsers.base import ParsedMessage


class MessageLogWidget(RichLog):
    """Widget for displaying CAN messages with filtering and styling."""
    
    BINDINGS = [
        Binding("ctrl+shift+c", "copy_selected", "Copy selected text"),
        Binding("ctrl+shift+a", "copy_all", "Copy all text"),
        Binding("f5", "toggle_detailed_view", "Toggle detailed view"),
    ]
    
    def __init__(self, max_messages: int = 10000, **kwargs):
        super().__init__(**kwargs)
        self.max_messages = max_messages
        self.messages: deque[CANMessage] = deque(maxlen=max_messages)
        self.parsed_messages: deque[Optional[ParsedMessage]] = deque(maxlen=max_messages)
        self.message_filter = MessageFilter()
        self.auto_scroll = True
        
        # Configure styling and selection
        self.can_focus = True
        self.auto_scroll = True
        
        # Enable text selection
        self.highlight = True
        self.markup = True
        
        # View mode
        self.detailed_view = False
    
    def add_message(self, message: CANMessage, parsed_message: Optional[ParsedMessage] = None):
        """Add a new message to the log."""
        self.messages.append(message)
        self.parsed_messages.append(parsed_message)
        
        # Only display if it matches the filter
        if self.message_filter.matches(message):
            self._display_message(message, parsed_message)
    
    def _display_message(self, message: CANMessage, parsed_message: Optional[ParsedMessage] = None):
        """Display a single message with appropriate styling."""
        if self.detailed_view and message.type.value in ["RX", "TX"]:
            self._display_detailed_message(message, parsed_message)
        else:
            self._display_compact_message(message, parsed_message)
    
    def _display_compact_message(self, message: CANMessage, parsed_message: Optional[ParsedMessage] = None):
        """Display a message in compact format (original format)."""
        timestamp_str = message.timestamp.strftime("%H:%M:%S.%f")[:-3]
        
        # Create styled text based on message type
        if message.type.value == "RX":
            text = Text()
            text.append("🟢 ", style="green")
            text.append(f"{timestamp_str} ", style="dim")
            text.append("RX ", style="green bold")
            
            if message.can_id is not None:
                text.append(f"ID=0x{message.can_id:03X} ", style="green")
                text.append(f"[{message.data_length}] ", style="dim")
                
                if message.data:
                    # Alternate colors for data bytes for readability
                    for i, byte in enumerate(message.data):
                        style = "green" if i % 2 == 0 else "bright_green"
                        text.append(f"{byte:02X} ", style=style)
                
                # Add parser info if available
                if parsed_message:
                    text.append(f"[{parsed_message.parser_name}] ", style="cyan")
        
        elif message.type.value == "TX":
            text = Text()
            text.append("🔵 ", style="blue")
            text.append(f"{timestamp_str} ", style="dim")
            text.append("TX ", style="blue bold")
            
            if message.can_id is not None:
                text.append(f"ID=0x{message.can_id:03X} ", style="blue")
                text.append(f"[{message.data_length}] ", style="dim")
                
                if message.data:
                    # Alternate colors for data bytes
                    for i, byte in enumerate(message.data):
                        style = "blue" if i % 2 == 0 else "bright_blue"
                        text.append(f"{byte:02X} ", style=style)
                
                # Status indicator
                if message.success:
                    text.append("✓", style="green")
                else:
                    text.append("❌", style="red")
                
                # Add parser info if available
                if parsed_message:
                    text.append(f"[{parsed_message.parser_name}] ", style="cyan")
        
        elif message.type.value == "ERROR":
            text = Text()
            text.append("❌ ", style="red")
            text.append(f"{timestamp_str} ", style="dim")
            text.append("ERR ", style="red bold")
            text.append(str(message.error_message), style="red")
        
        else:  # INFO
            text = Text()
            text.append("ℹ️ ", style="cyan")
            text.append(f"{timestamp_str} ", style="dim")
            text.append("INFO ", style="cyan bold")
            text.append(str(message.error_message), style="cyan")
        
        # Add to log
        self.write(text)
    
    def _display_detailed_message(self, message: CANMessage, parsed_message: Optional[ParsedMessage] = None):
        """Display a CAN message with detailed field breakdown."""
        timestamp_str = message.timestamp.strftime("%H:%M:%S.%f")[:-3]
        
        # If we have parsed data, use it for detailed view
        if parsed_message:
            self._display_parsed_message(message, parsed_message, timestamp_str)
        else:
            self._display_raw_detailed_message(message, timestamp_str)
    
    def _display_parsed_message(self, message: CANMessage, parsed_message: ParsedMessage, timestamp_str: str):
        """Display a parsed CAN message with protocol-specific fields."""
        # Header
        direction_icon = "🟢" if message.type.value == "RX" else "🔵"
        direction_style = "green" if message.type.value == "RX" else "blue"
        
        header = Text()
        header.append(f"{direction_icon} {timestamp_str} ", style="dim")
        header.append(f"{message.type.value} ", style=f"{direction_style} bold")
        header.append(f"ID=0x{message.can_id:03X} ", style=direction_style)
        header.append(f"[{message.data_length}] ", style="dim")
        header.append(f"Parser: {parsed_message.parser_name} ", style="cyan")
        header.append(f"({parsed_message.confidence:.1%})", style="cyan dim")
        
        self.write(header)
        
        # Message type and name
        if parsed_message.message_type != "Unknown":
            info_text = Text()
            info_text.append(f"📋 {parsed_message.message_type}", style="cyan")
            if parsed_message.message_name:
                info_text.append(f" - {parsed_message.message_name}", style="cyan dim")
            self.write(info_text)
        
        # Create table for parsed fields
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("Field", style="dim", width=18)
        table.add_column("Value", width=12)
        table.add_column("Unit", style="dim", width=6)
        table.add_column("Raw", style="dim", width=8)
        table.add_column("Status", width=8)
        
        # Add parsed fields
        for field in parsed_message.fields:
            status_symbol = field.get_status_symbol()
            status_color = field.get_status_color()
            formatted_value = field.format_value()
            
            table.add_row(
                field.name,
                formatted_value,
                field.unit,
                f"0x{field.raw_value:02X}" if isinstance(field.raw_value, int) else str(field.raw_value),
                f"[{status_color}]{status_symbol}[/{status_color}]"
            )
        
        self.write(table)
        
        # Show errors and warnings
        if parsed_message.errors:
            error_text = Text()
            error_text.append("❌ Errors: ", style="red bold")
            error_text.append(", ".join(parsed_message.errors), style="red")
            self.write(error_text)
        
        if parsed_message.warnings:
            warning_text = Text()
            warning_text.append("⚠️  Warnings: ", style="yellow bold")
            warning_text.append(", ".join(parsed_message.warnings), style="yellow")
            self.write(warning_text)
        
        # Add separator
        separator = Text("─" * 60, style="dim")
        self.write(separator)
        self.write("")  # Empty line for spacing
    
    def _display_raw_detailed_message(self, message: CANMessage, timestamp_str: str):
        """Display a CAN message with raw field breakdown (fallback)."""
        # Create table for detailed view
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("Field", style="dim", width=12)
        table.add_column("Value", width=20)
        table.add_column("Hex", style="dim", width=10)
        table.add_column("Binary", style="dim", width=12)
        
        # Message type and timestamp
        direction_style = "green" if message.type.value == "RX" else "blue"
        direction_icon = "🟢" if message.type.value == "RX" else "🔵"
        
        table.add_row("Direction", f"{direction_icon} {message.type.value}", "", "")
        table.add_row("Timestamp", timestamp_str, "", "")
        
        if message.can_id is not None:
            # CAN ID breakdown
            table.add_row("CAN ID", f"{message.can_id}", f"0x{message.can_id:03X}", f"{message.can_id:011b}")
            table.add_row("Length", f"{message.data_length} bytes", f"0x{message.data_length:X}", f"{message.data_length:08b}")
            
            # Data bytes
            if message.data:
                for i, byte in enumerate(message.data):
                    table.add_row(f"Data[{i}]", f"{byte}", f"0x{byte:02X}", f"{byte:08b}")
        
        # Status for TX messages
        if message.type.value == "TX":
            status_text = "✓ Success" if message.success else "❌ Failed"
            table.add_row("Status", status_text, "", "")
        
        # Add separator line
        separator = Text("─" * 60, style="dim")
        self.write(separator)
        self.write(table)
        self.write("")  # Empty line for spacing
    
    def set_filter(self, message_filter: MessageFilter):
        """Update the message filter and refresh display."""
        self.message_filter = message_filter
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the entire display with current filter."""
        self.clear()
        
        for message, parsed_message in zip(self.messages, self.parsed_messages):
            if self.message_filter.matches(message):
                self._display_message(message, parsed_message)
        
        # Ensure display updates
        self.refresh()
    
    def clear_messages(self):
        """Clear all messages from the log."""
        self.messages.clear()
        self.parsed_messages.clear()
        self.clear()
    
    def get_messages(self) -> List[CANMessage]:
        """Get all messages as a list."""
        return list(self.messages)
    
    def search_messages(self, query: str) -> List[CANMessage]:
        """Search for messages containing the query string."""
        query_lower = query.lower()
        results = []
        
        for message in self.messages:
            # Search in formatted message text
            formatted = message.format_for_display().lower()
            if query_lower in formatted:
                results.append(message)
            
            # Search in raw data
            elif message.raw_data and query_lower in message.raw_data.lower():
                results.append(message)
            
            # Search in CAN ID (support hex search)
            elif message.can_id is not None:
                if query.startswith('0x'):
                    try:
                        search_id = int(query, 16)
                        if message.can_id == search_id:
                            results.append(message)
                    except ValueError:
                        pass
                elif query.isdigit():
                    if message.can_id == int(query):
                        results.append(message)
        
        return results
    
    def export_messages(self, format_type: str = "csv") -> str:
        """Export messages in various formats."""
        if format_type == "csv":
            lines = ["Timestamp,Type,CAN_ID,Length,Data,Success,Raw"]
            for msg in self.messages:
                timestamp = msg.timestamp.isoformat()
                can_id = f"0x{msg.can_id:03X}" if msg.can_id is not None else ""
                data = " ".join(f"{b:02X}" for b in (msg.data or []))
                lines.append(f"{timestamp},{msg.type.value},{can_id},{msg.data_length or 0},{data},{msg.success},{msg.raw_data or ''}")
            return "\n".join(lines)
        
        elif format_type == "json":
            import json
            messages_dict = []
            for msg in self.messages:
                messages_dict.append({
                    "timestamp": msg.timestamp.isoformat(),
                    "type": msg.type.value,
                    "can_id": msg.can_id,
                    "data_length": msg.data_length,
                    "data": msg.data,
                    "success": msg.success,
                    "error_message": msg.error_message,
                    "raw_data": msg.raw_data
                })
            return json.dumps(messages_dict, indent=2)
        
        else:  # raw text
            lines = []
            for msg in self.messages:
                lines.append(msg.format_for_display())
            return "\n".join(lines)
    
    def toggle_auto_scroll(self):
        """Toggle auto-scroll behavior."""
        self.auto_scroll = not self.auto_scroll
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the log."""
        if self.auto_scroll:
            self.scroll_end()
    
    def get_message_count(self) -> int:
        """Get the total number of messages."""
        return len(self.messages)
    
    def get_filtered_count(self) -> int:
        """Get the number of messages that match the current filter."""
        return sum(1 for msg in self.messages if self.message_filter.matches(msg))
    
    def action_copy_selected(self) -> None:
        """Copy selected text to clipboard."""
        # This is a placeholder - Textual's RichLog doesn't have built-in text selection
        # But we can copy the last few messages
        try:
            import pyperclip
            recent_messages = []
            for msg in list(self.messages)[-20:]:  # Last 20 messages
                recent_messages.append(msg.format_for_display())
            
            text_to_copy = "\n".join(recent_messages)
            pyperclip.copy(text_to_copy)
            
            # Show notification
            self.notify("Last 20 messages copied to clipboard!")
        except ImportError:
            self.notify("pyperclip not installed - cannot copy to clipboard")
        except Exception as e:
            self.notify(f"Failed to copy: {e}")
    
    def action_select_all(self) -> None:
        """Select all text (placeholder for now)."""
        try:
            import pyperclip
            all_messages = []
            for msg in self.messages:
                all_messages.append(msg.format_for_display())
            
            text_to_copy = "\n".join(all_messages)
            pyperclip.copy(text_to_copy)
            
            # Show notification
            self.notify(f"All {len(self.messages)} messages copied to clipboard!")
        except ImportError:
            self.notify("pyperclip not installed - cannot copy to clipboard")
        except Exception as e:
            self.notify(f"Failed to copy: {e}")
    
    def action_toggle_detailed_view(self) -> None:
        """Toggle between compact and detailed view."""
        self.detailed_view = not self.detailed_view
        mode = "detailed" if self.detailed_view else "compact"
        self.notify(f"Switched to {mode} view")
        self.refresh_display()
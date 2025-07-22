from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    RX = "RX"
    TX = "TX"
    ERROR = "ERROR"
    INFO = "INFO"


class CANMessage(BaseModel):
    """Represents a CAN message with all relevant metadata."""
    
    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.now)
    can_id: Optional[int] = None
    data_length: Optional[int] = None
    data: Optional[List[int]] = None
    raw_data: Optional[str] = None
    error_message: Optional[str] = None
    success: bool = True
    
    @classmethod
    def from_raw_string(cls, raw_string: str) -> "CANMessage":
        """Parse a raw string from the CAN bridge firmware into a CANMessage."""
        raw_string = raw_string.strip()
        
        # Handle different message formats according to PROTOCOL.md
        if raw_string.startswith("CAN_RX;"):
            return cls._parse_can_rx_message(raw_string)
        elif raw_string.startswith("CAN_TX;"):
            return cls._parse_can_tx_message(raw_string)
        elif raw_string.startswith("CAN_ERR;"):
            return cls._parse_can_error_message(raw_string)
        elif raw_string.startswith("STATUS;"):
            return cls._parse_status_message(raw_string)
        elif raw_string.startswith("STATS;"):
            return cls._parse_stats_message(raw_string)
        # Legacy formats (keep for backward compatibility)
        elif raw_string.startswith("RX:"):
            return cls._parse_rx_message(raw_string)
        elif raw_string.startswith("TX:"):
            return cls._parse_tx_message(raw_string)
        elif "Error" in raw_string or "ERROR" in raw_string or "Failed" in raw_string:
            return cls._parse_error_message(raw_string)
        else:
            return cls._parse_info_message(raw_string)
    
    @classmethod
    def _parse_rx_message(cls, raw_string: str) -> "CANMessage":
        """Parse RX message: RX: ID=0x123 LEN=8 DATA=0102030405060708"""
        try:
            parts = raw_string.split()
            can_id = None
            data_length = None
            data = None
            
            for part in parts:
                if part.startswith("ID=0x"):
                    can_id = int(part[5:], 16)
                elif part.startswith("LEN="):
                    data_length = int(part[4:])
                elif part.startswith("DATA="):
                    data_str = part[5:]
                    if data_str:
                        data = [int(data_str[i:i+2], 16) for i in range(0, len(data_str), 2)]
            
            return cls(
                type=MessageType.RX,
                can_id=can_id,
                data_length=data_length,
                data=data or [],
                raw_data=raw_string,
                success=True
            )
        except Exception as e:
            return cls(
                type=MessageType.ERROR,
                error_message=f"Failed to parse RX message: {str(e)}",
                raw_data=raw_string,
                success=False
            )
    
    @classmethod
    def _parse_tx_message(cls, raw_string: str) -> "CANMessage":
        """Parse TX message: TX: ID=0x123 LEN=8 DATA=0102030405060708 - SENT"""
        try:
            parts = raw_string.split()
            can_id = None
            data_length = None
            data = None
            success = "SENT" in raw_string
            
            for part in parts:
                if part.startswith("ID=0x"):
                    can_id = int(part[5:], 16)
                elif part.startswith("LEN="):
                    data_length = int(part[4:])
                elif part.startswith("DATA="):
                    data_str = part[5:]
                    if data_str:
                        data = [int(data_str[i:i+2], 16) for i in range(0, len(data_str), 2)]
            
            return cls(
                type=MessageType.TX,
                can_id=can_id,
                data_length=data_length,
                data=data or [],
                raw_data=raw_string,
                success=success
            )
        except Exception as e:
            return cls(
                type=MessageType.ERROR,
                error_message=f"Failed to parse TX message: {str(e)}",
                raw_data=raw_string,
                success=False
            )
    
    @classmethod
    def _parse_error_message(cls, raw_string: str) -> "CANMessage":
        """Parse error message: TX: Failed to send message"""
        return cls(
            type=MessageType.ERROR,
            error_message=raw_string,
            raw_data=raw_string,
            success=False
        )
    
    @classmethod
    def _parse_info_message(cls, raw_string: str) -> "CANMessage":
        """Parse info message: CAN initialization successful!"""
        return cls(
            type=MessageType.INFO,
            error_message=raw_string,
            raw_data=raw_string,
            success=True
        )
    
    @classmethod
    def _parse_can_rx_message(cls, raw_string: str) -> "CANMessage":
        """Parse CAN_RX message: CAN_RX;0x123;01,02,03,04[;timestamp]"""
        try:
            parts = raw_string.split(';')
            if len(parts) < 3:
                raise ValueError(f"Invalid CAN_RX format: {raw_string}")
            
            # Parse CAN ID
            can_id_str = parts[1].strip()
            if can_id_str.startswith("0x"):
                can_id = int(can_id_str, 16)
            else:
                can_id = int(can_id_str)
            
            # Parse data bytes
            data_str = parts[2].strip()
            data = []
            if data_str:
                data_parts = data_str.split(',')
                for part in data_parts:
                    part = part.strip()
                    if part:
                        data.append(int(part, 16))
            
            return cls(
                type=MessageType.RX,
                can_id=can_id,
                data_length=len(data),
                data=data,
                raw_data=raw_string,
                success=True
            )
        except Exception as e:
            return cls(
                type=MessageType.ERROR,
                error_message=f"Failed to parse CAN_RX message: {str(e)}",
                raw_data=raw_string,
                success=False
            )
    
    @classmethod
    def _parse_can_tx_message(cls, raw_string: str) -> "CANMessage":
        """Parse CAN_TX message: CAN_TX;0x123;01,02,03,04[;timestamp]"""
        try:
            parts = raw_string.split(';')
            if len(parts) < 3:
                raise ValueError(f"Invalid CAN_TX format: {raw_string}")
            
            # Parse CAN ID
            can_id_str = parts[1].strip()
            if can_id_str.startswith("0x"):
                can_id = int(can_id_str, 16)
            else:
                can_id = int(can_id_str)
            
            # Parse data bytes
            data_str = parts[2].strip()
            data = []
            if data_str:
                data_parts = data_str.split(',')
                for part in data_parts:
                    part = part.strip()
                    if part:
                        data.append(int(part, 16))
            
            return cls(
                type=MessageType.TX,
                can_id=can_id,
                data_length=len(data),
                data=data,
                raw_data=raw_string,
                success=True
            )
        except Exception as e:
            return cls(
                type=MessageType.ERROR,
                error_message=f"Failed to parse CAN_TX message: {str(e)}",
                raw_data=raw_string,
                success=False
            )
    
    @classmethod
    def _parse_can_error_message(cls, raw_string: str) -> "CANMessage":
        """Parse CAN_ERR message: CAN_ERR;0x01;Bus off detected[;details]"""
        try:
            parts = raw_string.split(';')
            if len(parts) < 3:
                raise ValueError(f"Invalid CAN_ERR format: {raw_string}")
            
            error_code = parts[1].strip()
            error_description = parts[2].strip()
            error_details = parts[3].strip() if len(parts) > 3 else ""
            
            full_message = f"Error {error_code}: {error_description}"
            if error_details:
                full_message += f" ({error_details})"
            
            return cls(
                type=MessageType.ERROR,
                error_message=full_message,
                raw_data=raw_string,
                success=False
            )
        except Exception as e:
            return cls(
                type=MessageType.ERROR,
                error_message=f"Failed to parse CAN_ERR message: {str(e)}",
                raw_data=raw_string,
                success=False
            )
    
    @classmethod
    def _parse_status_message(cls, raw_string: str) -> "CANMessage":
        """Parse STATUS message: STATUS;info_text"""
        try:
            parts = raw_string.split(';', 1)  # Split only on first semicolon
            if len(parts) < 2:
                raise ValueError(f"Invalid STATUS format: {raw_string}")
            
            status_message = parts[1].strip()
            
            return cls(
                type=MessageType.INFO,
                error_message=status_message,
                raw_data=raw_string,
                success=True
            )
        except Exception as e:
            return cls(
                type=MessageType.ERROR,
                error_message=f"Failed to parse STATUS message: {str(e)}",
                raw_data=raw_string,
                success=False
            )
    
    @classmethod
    def _parse_stats_message(cls, raw_string: str) -> None:
        """Parse STATS message: STATS;rx_count;tx_count;error_count;bus_load - but suppress from display"""
        # STATS messages are periodic statistics that clutter the display
        # Return None to suppress them from being displayed
        return None
    
    def format_for_display(self) -> str:
        """Format the message for display in the TUI."""
        timestamp_str = self.timestamp.strftime("%H:%M:%S.%f")[:-3]
        
        if self.type == MessageType.RX:
            data_str = " ".join(f"{b:02X}" for b in (self.data or []))
            return f"🟢 {timestamp_str} RX ID=0x{self.can_id:03X} [{self.data_length}] {data_str}"
        elif self.type == MessageType.TX:
            data_str = " ".join(f"{b:02X}" for b in (self.data or []))
            status = "✓" if self.success else "❌"
            return f"🔵 {timestamp_str} TX ID=0x{self.can_id:03X} [{self.data_length}] {data_str} {status}"
        elif self.type == MessageType.ERROR:
            return f"❌ {timestamp_str} ERR {self.error_message}"
        else:
            return f"ℹ️ {timestamp_str} INFO {self.error_message}"
    
    def get_color(self) -> str:
        """Get the color for this message type."""
        color_map = {
            MessageType.RX: "green",
            MessageType.TX: "blue",
            MessageType.ERROR: "red",
            MessageType.INFO: "cyan"
        }
        return color_map.get(self.type, "white")


class MessageFilter(BaseModel):
    """Filter configuration for message display."""
    
    show_rx: bool = True
    show_tx: bool = True
    show_errors: bool = True
    show_info: bool = True
    id_filter: Optional[str] = None  # Legacy single ID filter (deprecated)
    id_filters: List[int] = Field(default_factory=list)  # Multiple CAN ID filters
    
    def matches(self, message: CANMessage) -> bool:
        """Check if a message matches the current filter."""
        # Type filtering
        if message.type == MessageType.RX and not self.show_rx:
            return False
        if message.type == MessageType.TX and not self.show_tx:
            return False
        if message.type == MessageType.ERROR and not self.show_errors:
            return False
        if message.type == MessageType.INFO and not self.show_info:
            return False
        
        # ID filtering - check both legacy single filter and new multiple filters
        if message.can_id is not None and (self.id_filter or self.id_filters):
            # Check if message matches any of the active filters
            match_found = False
            
            # Check legacy single filter (for backward compatibility)
            if self.id_filter:
                try:
                    if self.id_filter.startswith("0x"):
                        filter_id = int(self.id_filter, 16)
                    else:
                        filter_id = int(self.id_filter)
                    
                    if message.can_id == filter_id:
                        match_found = True
                except ValueError:
                    pass
            
            # Check new multiple filters
            if self.id_filters and message.can_id in self.id_filters:
                match_found = True
            
            # If we have active ID filters but no match, reject the message
            if not match_found:
                return False
        
        return True
    
    def add_id_filter(self, can_id: int) -> bool:
        """Add a CAN ID to the filter list. Returns True if added, False if already exists."""
        if can_id not in self.id_filters:
            self.id_filters.append(can_id)
            return True
        return False
    
    def remove_id_filter(self, can_id: int) -> bool:
        """Remove a CAN ID from the filter list. Returns True if removed, False if not found."""
        try:
            self.id_filters.remove(can_id)
            return True
        except ValueError:
            return False
    
    def clear_id_filters(self):
        """Clear all ID filters."""
        self.id_filters.clear()
        self.id_filter = None  # Also clear legacy filter
    
    def has_id_filters(self) -> bool:
        """Check if any ID filters are active."""
        return bool(self.id_filters or self.id_filter)
    
    def get_active_filters(self) -> List[str]:
        """Get list of active ID filters as hex strings."""
        filters = []
        if self.id_filter:
            filters.append(self.id_filter)
        for can_id in self.id_filters:
            filters.append(f"0x{can_id:03X}")
        return filters


class MessageStats(BaseModel):
    """Statistics for message tracking."""
    
    rx_count: int = 0
    tx_count: int = 0
    error_count: int = 0
    info_count: int = 0
    start_time: datetime = Field(default_factory=datetime.now)
    
    def update(self, message: CANMessage):
        """Update statistics with a new message."""
        if message.type == MessageType.RX:
            self.rx_count += 1
        elif message.type == MessageType.TX:
            self.tx_count += 1
        elif message.type == MessageType.ERROR:
            self.error_count += 1
        elif message.type == MessageType.INFO:
            self.info_count += 1
    
    def get_rate(self) -> float:
        """Calculate messages per second."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed > 0:
            total_messages = self.rx_count + self.tx_count + self.error_count + self.info_count
            return total_messages / elapsed
        return 0.0
    
    def get_total_count(self) -> int:
        """Get total message count."""
        return self.rx_count + self.tx_count + self.error_count + self.info_count
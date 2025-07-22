import asyncio
import serial
import serial.tools.list_ports
from typing import Optional, Callable, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Get the CAN logger (configured in app.py)
can_logger = logging.getLogger('can_logger')


class SerialService:
    """Manages serial communication with the CAN bridge device."""
    
    def __init__(self, 
                 port: Optional[str] = None,
                 baudrate: int = 115200,
                 timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection: Optional[serial.Serial] = None
        self.is_connected = False
        self.message_callback: Optional[Callable[[str], None]] = None
        self.connection_callback: Optional[Callable[[bool], None]] = None
        self._read_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self.auto_reconnect = True
        
    def set_message_callback(self, callback: Callable[[str], None]):
        """Set callback for received messages."""
        self.message_callback = callback
    
    def set_connection_callback(self, callback: Callable[[bool], None]):
        """Set callback for connection status changes."""
        self.connection_callback = callback
    
    @staticmethod
    def find_can_bridge_ports() -> List[str]:
        """Find potential CAN bridge devices."""
        ports = []
        detailed_info = []
        
        for port in serial.tools.list_ports.comports():
            # Combine description and manufacturer for keyword search
            search_text = ""
            if port.description:
                search_text += port.description.lower() + " "
            if hasattr(port, 'manufacturer') and port.manufacturer:
                search_text += port.manufacturer.lower() + " "
            if hasattr(port, 'product') and port.product:
                search_text += port.product.lower() + " "
            
            # Look for CAN bridge device identifiers
            can_bridge_keywords = [
                'pico', 'rp2040',           # Raspberry Pi Pico
                'adafruit', 'feather', 'm4', 'same51',  # Adafruit Feather M4 CAN
                'arduino', 'esp32',         # Other Arduino-compatible boards
                'can', 'bridge',            # Generic CAN bridge terms
                'usb serial'                # Generic USB serial
            ]
            
            if any(keyword in search_text for keyword in can_bridge_keywords):
                ports.append(port.device)
                detailed_info.append({
                    'device': port.device,
                    'description': port.description,
                    'manufacturer': getattr(port, 'manufacturer', 'Unknown'),
                    'product': getattr(port, 'product', 'Unknown'),
                    'keywords_found': [kw for kw in can_bridge_keywords if kw in search_text]
                })
                logger.debug(f"CAN bridge candidate: {port.device} - {port.description}")
            
            # Also include generic USB serial devices as fallback
            elif 'usb' in search_text and 'serial' in search_text:
                ports.append(port.device)
                detailed_info.append({
                    'device': port.device,
                    'description': port.description,
                    'manufacturer': getattr(port, 'manufacturer', 'Unknown'),
                    'product': getattr(port, 'product', 'Unknown'),
                    'keywords_found': ['usb serial (fallback)']
                })
                logger.debug(f"USB serial fallback: {port.device} - {port.description}")
        
        # Add common device paths if not found (and they exist)
        common_paths = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']
        for path in common_paths:
            if path not in ports:
                try:
                    # Test if the port exists and is accessible
                    test_serial = serial.Serial(path, timeout=0.1)
                    test_serial.close()
                    ports.append(path)
                    detailed_info.append({
                        'device': path,
                        'description': 'Common device path',
                        'manufacturer': 'Unknown',
                        'product': 'Unknown',
                        'keywords_found': ['common path']
                    })
                    logger.debug(f"Common path available: {path}")
                except:
                    pass
        
        # Log detailed information about found ports
        if detailed_info:
            logger.info(f"Found {len(ports)} potential CAN bridge port(s):")
            for info in detailed_info:
                logger.info(f"  {info['device']}: {info['description']} "
                          f"(Keywords: {', '.join(info['keywords_found'])})")
        
        return ports
    
    async def connect(self, port: Optional[str] = None) -> bool:
        """Connect to the CAN bridge device."""
        can_logger.info(f"CONNECT_ATTEMPT: port={port}")
        
        if port:
            self.port = port
        
        if not self.port:
            can_logger.error("CONNECT_FAILED: No port specified")
            logger.error("No port specified for connection")
            return False
        
        try:
            # Close existing connection
            if self.connection and self.connection.is_open:
                can_logger.info("CONNECT: Closing existing connection")
                self.connection.close()
            
            # Open new connection
            can_logger.info(f"CONNECT: Opening serial connection to {self.port} at {self.baudrate} baud")
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            # Test connection with a simple command
            await asyncio.sleep(0.1)  # Give device time to initialize
            if self.connection.is_open:
                can_logger.info(f"CONNECT_SUCCESS: Connected to {self.port}")
                self.is_connected = True
                logger.info(f"Connected to CAN bridge at {self.port}")
                
                # Reset auto_reconnect flag
                self.auto_reconnect = True
                
                # Start reading task
                self._read_task = asyncio.create_task(self._read_loop())
                can_logger.info(f"CONNECT_SUCCESS: Started read task, message_callback={self.message_callback is not None}")
                
                # Notify connection status
                if self.connection_callback:
                    self.connection_callback(True)
                
                return True
            
        except Exception as e:
            can_logger.error(f"CONNECT_FAILED: port={self.port}, error={e}")
            logger.error(f"Failed to connect to {self.port}: {e}")
            self.is_connected = False
            if self.connection_callback:
                self.connection_callback(False)
        
        return False
    
    async def disconnect(self):
        """Disconnect from the CAN bridge device."""
        self.auto_reconnect = False
        
        # Cancel tasks
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        
        # Close connection
        if self.connection and self.connection.is_open:
            self.connection.close()
        
        self.is_connected = False
        if self.connection_callback:
            self.connection_callback(False)
        
        logger.info("Disconnected from CAN bridge")
    
    async def send_command(self, command: str) -> bool:
        """Send a command to the CAN bridge."""
        can_logger.info(f"SEND_COMMAND: '{command}'")
        
        if not self.is_connected or not self.connection:
            can_logger.error("SEND_COMMAND: Not connected to CAN bridge")
            logger.error("Not connected to CAN bridge")
            return False
        
        try:
            # Ensure command ends with newline
            if not command.endswith('\n'):
                command += '\n'
            
            can_logger.debug(f"SEND_COMMAND: Writing to serial: '{command.strip()}'")
            # Send command
            bytes_written = self.connection.write(command.encode('utf-8'))
            self.connection.flush()
            
            can_logger.info(f"SEND_COMMAND_SUCCESS: bytes_written={bytes_written}, command='{command.strip()}'")
            logger.debug(f"Sent command: {command.strip()}")
            return True
            
        except Exception as e:
            can_logger.error(f"SEND_COMMAND_FAILED: command='{command.strip()}', error={e}")
            logger.error(f"Failed to send command '{command.strip()}': {e}")
            return False
    
    async def _read_loop(self):
        """Main read loop for receiving messages."""
        can_logger.info("READ_LOOP: Starting read loop")
        buffer = ""
        
        while self.is_connected and self.connection and self.connection.is_open:
            try:
                # Read available data
                if self.connection.in_waiting > 0:
                    data = self.connection.read(self.connection.in_waiting)
                    if data:
                        decoded_data = data.decode('utf-8', errors='ignore')
                        can_logger.debug(f"READ_LOOP: Received raw data: '{decoded_data}'")
                        buffer += decoded_data
                        
                        # Process complete lines
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            
                            if line:
                                can_logger.debug(f"READ_LOOP: Processing line: '{line}'")
                                if self.message_callback:
                                    can_logger.debug(f"READ_LOOP: Calling message callback")
                                    self.message_callback(line)
                                else:
                                    can_logger.warning(f"READ_LOOP: No message callback set for line: '{line}'")
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
            except Exception as e:
                can_logger.error(f"READ_LOOP_ERROR: {e}")
                logger.error(f"Error in read loop: {e}")
                self.is_connected = False
                if self.connection_callback:
                    self.connection_callback(False)
                
                # Attempt reconnection if enabled
                if self.auto_reconnect:
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())
                break
        
        can_logger.info("READ_LOOP: Exiting read loop")
    
    async def _reconnect_loop(self):
        """Attempt to reconnect to the device."""
        reconnect_delay = 2.0
        max_delay = 30.0
        
        while self.auto_reconnect and not self.is_connected:
            logger.info(f"Attempting to reconnect in {reconnect_delay} seconds...")
            await asyncio.sleep(reconnect_delay)
            
            if await self.connect():
                logger.info("Reconnected successfully")
                break
            
            # Exponential backoff
            reconnect_delay = min(reconnect_delay * 1.5, max_delay)
    
    def get_connection_status(self) -> dict:
        """Get current connection status information."""
        return {
            'connected': self.is_connected,
            'port': self.port,
            'baudrate': self.baudrate,
            'auto_reconnect': self.auto_reconnect
        }
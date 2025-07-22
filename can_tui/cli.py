#!/usr/bin/env python3
"""
Command-line interface for the RPICAN TUI application.
"""

import argparse
import sys
from typing import Optional

from .app import run_app


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CAN TUI Monitor - Universal Terminal interface for CAN bridge devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  can-tui                           # Auto-detect CAN bridge device
  can-tui -l                        # List available serial ports
  can-tui -i                        # Interactive port selection
  can-tui -p /dev/ttyACM0           # Use specific serial port
  can-tui -p /dev/ttyUSB0 -b 115200 # Custom port and baud rate
  
Supported Hardware:
  • Raspberry Pi Pico (RP2040) with CAN transceiver
  • Adafruit Feather M4 CAN (SAMD51 with built-in CAN)
  • ESP32 with CAN transceiver
  • Any board implementing the CAN TUI serial protocol
  
Key Bindings:
  F1              Clear messages
  F2              Save message log
  F3              Pause/Resume monitoring
  F4              Show help
  F5              Settings (Port/Baud)
  Ctrl+R          Reconnect to device
  Ctrl+C          Quit application
        """
    )
    
    parser.add_argument(
        "-p", "--port",
        type=str,
        default=None,
        help="Serial port path (e.g., /dev/ttyACM0). If not specified, auto-detection is used."
    )
    
    parser.add_argument(
        "-l", "--list-ports",
        action="store_true",
        help="List available serial ports and exit"
    )
    
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Interactive port selection when multiple devices found"
    )
    
    parser.add_argument(
        "-b", "--baudrate",
        type=int,
        default=115200,
        help="Serial port baud rate (default: 115200)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="CAN TUI Monitor v1.0.0"
    )
    
    return parser.parse_args()


def select_port_interactively() -> Optional[str]:
    """Interactive port selection when multiple devices are found."""
    from .services.serial_service import SerialService
    import serial.tools.list_ports
    
    # Get CAN bridge ports
    can_bridge_ports = SerialService.find_can_bridge_ports()
    
    if not can_bridge_ports:
        print("❌ No CAN bridge devices found.")
        return None
    
    if len(can_bridge_ports) == 1:
        print(f"🎯 Auto-selecting only available device: {can_bridge_ports[0]}")
        return can_bridge_ports[0]
    
    # Multiple devices found - show selection menu
    print(f"🔍 Found {len(can_bridge_ports)} CAN bridge device(s):\n")
    
    # Get detailed info for each CAN bridge port
    all_ports = {port.device: port for port in serial.tools.list_ports.comports()}
    
    for i, port_device in enumerate(can_bridge_ports, 1):
        port_info = all_ports.get(port_device)
        print(f"{i}. {port_device}")
        
        if port_info:
            print(f"   Description: {port_info.description}")
            if hasattr(port_info, 'manufacturer') and port_info.manufacturer:
                print(f"   Manufacturer: {port_info.manufacturer}")
            if hasattr(port_info, 'vid') and port_info.vid:
                print(f"   VID:PID: {port_info.vid:04X}:{port_info.pid:04X}")
        print()
    
    # Get user selection
    while True:
        try:
            selection = input(f"Select device (1-{len(can_bridge_ports)}), or 'q' to quit: ").strip()
            
            if selection.lower() == 'q':
                print("👋 Exiting...")
                return None
            
            port_index = int(selection) - 1
            if 0 <= port_index < len(can_bridge_ports):
                selected_port = can_bridge_ports[port_index]
                print(f"✅ Selected: {selected_port}")
                return selected_port
            else:
                print(f"❌ Invalid selection. Please enter 1-{len(can_bridge_ports)} or 'q'.")
        
        except ValueError:
            print(f"❌ Invalid input. Please enter a number 1-{len(can_bridge_ports)} or 'q'.")
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            return None


def list_available_ports() -> None:
    """List all available serial ports with details."""
    from .services.serial_service import SerialService
    import serial.tools.list_ports
    
    print("🔍 Scanning for serial ports...\n")
    
    # Get all ports
    all_ports = list(serial.tools.list_ports.comports())
    
    if not all_ports:
        print("❌ No serial ports found.")
        return
    
    # Get CAN bridge ports (those that would be auto-detected)
    can_bridge_ports = SerialService.find_can_bridge_ports()
    
    print(f"📋 Found {len(all_ports)} serial port(s):\n")
    
    for i, port in enumerate(all_ports, 1):
        is_can_bridge = port.device in can_bridge_ports
        status = "🟢 CAN Bridge Candidate" if is_can_bridge else "⚪ Generic Port"
        
        print(f"{i}. {status}")
        print(f"   Port: {port.device}")
        print(f"   Name: {port.name}")
        print(f"   Description: {port.description}")
        if hasattr(port, 'manufacturer') and port.manufacturer:
            print(f"   Manufacturer: {port.manufacturer}")
        if hasattr(port, 'vid') and port.vid:
            print(f"   VID:PID: {port.vid:04X}:{port.pid:04X}")
        print()
    
    if can_bridge_ports:
        print(f"🎯 Auto-detection would use: {can_bridge_ports[0]}")
    else:
        print("⚠️  No CAN bridge devices auto-detected.")
        print("   Use -p <port> to specify manually.")


def main() -> None:
    """Main entry point for the CLI application."""
    args = parse_args()
    
    # Handle --list-ports option
    if args.list_ports:
        list_available_ports()
        sys.exit(0)
    
    # Handle interactive port selection
    selected_port = args.port
    if args.interactive and not selected_port:
        print("🔍 Interactive port selection mode\n")
        selected_port = select_port_interactively()
        if not selected_port:
            sys.exit(1)
    
    # Configure logging level
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        print(f"Starting CAN TUI Monitor with verbose logging...")
        print(f"Port: {selected_port or 'auto-detect'}")
        print(f"Baud rate: {args.baudrate}")
    
    try:
        # Run the TUI application
        run_app(port=selected_port, baudrate=args.baudrate)
    except KeyboardInterrupt:
        print("\nShutting down CAN TUI Monitor...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting CAN TUI Monitor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
CAN Bridge TUI - Terminal User Interface for USB-to-CAN Bridge

A modern, feature-rich terminal interface for monitoring and controlling
the Raspberry Pi Pico CAN bridge device.
"""

import click
import logging
from .app import run_app
from .services.serial_service import SerialService


@click.command()
@click.option('--port', '-p', 
              help='Serial port (auto-detect if not specified)')
@click.option('--baudrate', '-b', 
              default=115200, 
              help='Baud rate (default: 115200)')
@click.option('--list-ports', '-l', 
              is_flag=True, 
              help='List available serial ports')
@click.option('--debug', '-d', 
              is_flag=True, 
              help='Enable debug logging')
@click.version_option(version='1.0.0', prog_name='CAN Bridge TUI')
def main(port, baudrate, list_ports, debug):
    """
    CAN Bridge TUI - Terminal interface for USB-to-CAN bridge monitoring.
    
    This tool provides a modern, interactive terminal interface for communicating
    with the Raspberry Pi Pico CAN bridge device. Features include:
    
    • Real-time CAN message monitoring with color coding
    • Command input with validation and history
    • Message filtering and search capabilities  
    • Statistics tracking and session export
    • Auto-reconnection and error handling
    
    Examples:
    
        can-tui                          # Auto-detect device
        can-tui -p /dev/ttyACM0          # Specify port
        can-tui -l                       # List available ports
        can-tui --debug                  # Enable debug output
    """
    
    # Configure logging
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(level=logging.WARNING)
    
    # List ports if requested
    if list_ports:
        click.echo("Available serial ports:")
        ports = SerialService.find_can_bridge_ports()
        
        if ports:
            for i, port_name in enumerate(ports, 1):
                click.echo(f"  {i}. {port_name}")
        else:
            click.echo("  No CAN bridge devices found")
        
        return
    
    # Validate baudrate
    if baudrate <= 0:
        click.echo("Error: Baud rate must be positive", err=True)
        return
    
    # Show startup information
    if not debug:
        click.echo("🚀 Starting CAN Bridge TUI...")
        click.echo("   Press Ctrl+C to quit, F4 for help")
        
        if port:
            click.echo(f"   Connecting to: {port}")
        else:
            click.echo("   Auto-detecting CAN bridge device...")
        
        click.echo("")
    
    try:
        # Run the TUI application
        run_app(port=port, baudrate=baudrate)
        
    except KeyboardInterrupt:
        click.echo("\n👋 Goodbye!")
    except Exception as e:
        if debug:
            raise
        else:
            click.echo(f"❌ Error: {e}", err=True)


if __name__ == '__main__':
    main()
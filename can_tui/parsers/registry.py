"""
Parser registry system for managing and selecting protocol parsers.
"""

import importlib
import importlib.util
import os
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path
import yaml
import json

from .base import ProtocolParser, ParsedMessage


logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registry for managing protocol parsers."""
    
    def __init__(self):
        self.parsers: Dict[str, ProtocolParser] = {}
        self.can_id_mappings: Dict[int, str] = {}
        self.range_mappings: List[Tuple[range, str]] = []
        self.default_parser: Optional[str] = None
        self.config_file: Optional[str] = None
        
    def register_parser(self, parser: ProtocolParser) -> None:
        """
        Register a protocol parser.
        
        Args:
            parser: Parser instance to register
        """
        if not isinstance(parser, ProtocolParser):
            raise ValueError(f"Parser must be an instance of ProtocolParser, got {type(parser)}")
        
        full_name = parser.get_full_name()
        self.parsers[full_name] = parser
        logger.info(f"Registered parser: {full_name}")
    
    def unregister_parser(self, name: str) -> bool:
        """
        Unregister a parser by name.
        
        Args:
            name: Parser name to unregister
            
        Returns:
            True if parser was found and removed, False otherwise
        """
        if name in self.parsers:
            del self.parsers[name]
            logger.info(f"Unregistered parser: {name}")
            return True
        return False
    
    def get_parser(self, name: str) -> Optional[ProtocolParser]:
        """
        Get a parser by name.
        
        Args:
            name: Parser name
            
        Returns:
            Parser instance or None if not found
        """
        return self.parsers.get(name)
    
    def get_all_parsers(self) -> Dict[str, ProtocolParser]:
        """Get all registered parsers."""
        return self.parsers.copy()
    
    def get_enabled_parsers(self) -> Dict[str, ProtocolParser]:
        """Get all enabled parsers."""
        return {name: parser for name, parser in self.parsers.items() if parser.is_enabled()}
    
    def get_parser_for_message(self, can_id: int, data: bytes) -> Optional[ProtocolParser]:
        """
        Find the best parser for a CAN message.
        
        Args:
            can_id: CAN message ID
            data: Message data bytes
            
        Returns:
            Best matching parser or None if no parser found
        """
        # Check direct ID mapping first
        if can_id in self.can_id_mappings:
            parser_name = self.can_id_mappings[can_id]
            parser = self.parsers.get(parser_name)
            if parser and parser.is_enabled():
                return parser
        
        # Check range mappings
        for range_obj, parser_name in self.range_mappings:
            if can_id in range_obj:
                parser = self.parsers.get(parser_name)
                if parser and parser.is_enabled():
                    return parser
        
        # Check if any parser can handle this message (by priority)
        candidate_parsers = []
        for parser in self.parsers.values():
            if parser.is_enabled() and parser.can_parse(can_id, data):
                candidate_parsers.append(parser)
        
        # Sort by priority (1 = highest priority)
        candidate_parsers.sort(key=lambda p: p.get_priority())
        
        if candidate_parsers:
            return candidate_parsers[0]
        
        # Return default parser if available
        if self.default_parser:
            return self.parsers.get(self.default_parser)
        
        return None
    
    def parse_message(self, can_id: int, data: bytes) -> Optional[ParsedMessage]:
        """
        Parse a CAN message using the appropriate parser.
        
        Args:
            can_id: CAN message ID
            data: Message data bytes
            
        Returns:
            ParsedMessage or None if no parser available
        """
        parser = self.get_parser_for_message(can_id, data)
        if parser:
            try:
                return parser.parse(can_id, data)
            except Exception as e:
                logger.error(f"Error parsing message with {parser.get_name()}: {e}")
                return None
        return None
    
    def add_can_id_mapping(self, can_id: int, parser_name: str) -> None:
        """
        Add a direct CAN ID to parser mapping.
        
        Args:
            can_id: CAN message ID
            parser_name: Parser name
        """
        if parser_name not in self.parsers:
            raise ValueError(f"Parser '{parser_name}' not registered")
        
        self.can_id_mappings[can_id] = parser_name
        logger.info(f"Added CAN ID mapping: 0x{can_id:03X} -> {parser_name}")
    
    def add_range_mapping(self, start_id: int, end_id: int, parser_name: str) -> None:
        """
        Add a CAN ID range to parser mapping.
        
        Args:
            start_id: Start of ID range (inclusive)
            end_id: End of ID range (inclusive)
            parser_name: Parser name
        """
        if parser_name not in self.parsers:
            raise ValueError(f"Parser '{parser_name}' not registered")
        
        range_obj = range(start_id, end_id + 1)
        self.range_mappings.append((range_obj, parser_name))
        logger.info(f"Added CAN ID range mapping: 0x{start_id:03X}-0x{end_id:03X} -> {parser_name}")
    
    def remove_can_id_mapping(self, can_id: int) -> bool:
        """
        Remove a CAN ID mapping.
        
        Args:
            can_id: CAN message ID
            
        Returns:
            True if mapping was removed, False if not found
        """
        if can_id in self.can_id_mappings:
            del self.can_id_mappings[can_id]
            logger.info(f"Removed CAN ID mapping: 0x{can_id:03X}")
            return True
        return False
    
    def clear_mappings(self) -> None:
        """Clear all CAN ID mappings."""
        self.can_id_mappings.clear()
        self.range_mappings.clear()
        logger.info("Cleared all CAN ID mappings")
    
    def set_default_parser(self, parser_name: str) -> None:
        """
        Set the default parser for unknown messages.
        
        Args:
            parser_name: Parser name
        """
        if parser_name not in self.parsers:
            raise ValueError(f"Parser '{parser_name}' not registered")
        
        self.default_parser = parser_name
        logger.info(f"Set default parser: {parser_name}")
    
    def load_parsers_from_directory(self, directory: str) -> int:
        """
        Load parsers from a directory.
        
        Args:
            directory: Directory path containing parser modules
            
        Returns:
            Number of parsers loaded
        """
        loaded_count = 0
        directory_path = Path(directory)
        
        if not directory_path.exists():
            logger.warning(f"Parser directory does not exist: {directory}")
            return 0
        
        # Load all .py files in the directory
        for file_path in directory_path.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
            
            try:
                # Load module dynamically
                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for parser classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, ProtocolParser) and 
                            attr != ProtocolParser):
                            
                            # Instantiate and register parser
                            parser_instance = attr()
                            self.register_parser(parser_instance)
                            loaded_count += 1
                            
            except Exception as e:
                logger.error(f"Error loading parser from {file_path}: {e}")
        
        logger.info(f"Loaded {loaded_count} parsers from {directory}")
        return loaded_count
    
    def load_config(self, config_file: str) -> None:
        """
        Load configuration from a YAML or JSON file.
        
        Args:
            config_file: Path to configuration file
        """
        config_path = Path(config_file)
        if not config_path.exists():
            logger.warning(f"Config file does not exist: {config_file}")
            return
        
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    config = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
            
            self._apply_config(config)
            self.config_file = config_file
            logger.info(f"Loaded configuration from {config_file}")
            
        except Exception as e:
            logger.error(f"Error loading config file {config_file}: {e}")
    
    def save_config(self, config_file: Optional[str] = None) -> None:
        """
        Save current configuration to a file.
        
        Args:
            config_file: Path to save configuration (uses loaded file if None)
        """
        if config_file is None:
            config_file = self.config_file
        
        if config_file is None:
            raise ValueError("No config file specified")
        
        config = self._generate_config()
        
        try:
            config_path = Path(config_file)
            with open(config_path, 'w') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config, f, default_flow_style=False)
                elif config_path.suffix.lower() == '.json':
                    json.dump(config, f, indent=2)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
            
            logger.info(f"Saved configuration to {config_file}")
            
        except Exception as e:
            logger.error(f"Error saving config file {config_file}: {e}")
    
    def _apply_config(self, config: dict) -> None:
        """Apply configuration from loaded config."""
        # Set default parser
        if 'default_parser' in config:
            if config['default_parser'] in self.parsers:
                self.default_parser = config['default_parser']
        
        # Configure parsers
        if 'parsers' in config:
            for parser_config in config['parsers']:
                name = parser_config.get('name')
                if name in self.parsers:
                    parser = self.parsers[name]
                    
                    # Set enabled state
                    if 'enabled' in parser_config:
                        parser.set_enabled(parser_config['enabled'])
                    
                    # Set priority
                    if 'priority' in parser_config:
                        parser.set_priority(parser_config['priority'])
                    
                    # Set parser-specific config
                    if 'config' in parser_config:
                        parser.configure(parser_config['config'])
        
        # Set up CAN ID mappings
        if 'can_id_mappings' in config:
            mappings = config['can_id_mappings']
            
            # Direct ID mappings
            if 'direct' in mappings:
                for can_id, parser_name in mappings['direct'].items():
                    if isinstance(can_id, str):
                        can_id = int(can_id, 16) if can_id.startswith('0x') else int(can_id)
                    if parser_name in self.parsers:
                        self.add_can_id_mapping(can_id, parser_name)
            
            # Range mappings
            if 'ranges' in mappings:
                for range_config in mappings['ranges']:
                    start = range_config['start']
                    end = range_config['end']
                    parser_name = range_config['parser']
                    
                    if isinstance(start, str):
                        start = int(start, 16) if start.startswith('0x') else int(start)
                    if isinstance(end, str):
                        end = int(end, 16) if end.startswith('0x') else int(end)
                    
                    if parser_name in self.parsers:
                        self.add_range_mapping(start, end, parser_name)
    
    def _generate_config(self) -> dict:
        """Generate configuration dictionary from current state."""
        config = {
            'default_parser': self.default_parser,
            'parsers': [],
            'can_id_mappings': {
                'direct': {},
                'ranges': []
            }
        }
        
        # Add parser configurations
        for name, parser in self.parsers.items():
            parser_config = {
                'name': name,
                'enabled': parser.is_enabled(),
                'priority': parser.get_priority(),
                'config': parser.get_config()
            }
            config['parsers'].append(parser_config)
        
        # Add direct ID mappings
        for can_id, parser_name in self.can_id_mappings.items():
            config['can_id_mappings']['direct'][f"0x{can_id:03X}"] = parser_name
        
        # Add range mappings
        for range_obj, parser_name in self.range_mappings:
            config['can_id_mappings']['ranges'].append({
                'start': f"0x{range_obj.start:03X}",
                'end': f"0x{range_obj.stop-1:03X}",
                'parser': parser_name
            })
        
        return config
    
    def get_stats(self) -> dict:
        """Get registry statistics."""
        enabled_count = len(self.get_enabled_parsers())
        total_count = len(self.parsers)
        
        return {
            'total_parsers': total_count,
            'enabled_parsers': enabled_count,
            'disabled_parsers': total_count - enabled_count,
            'direct_mappings': len(self.can_id_mappings),
            'range_mappings': len(self.range_mappings),
            'default_parser': self.default_parser
        }
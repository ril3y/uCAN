# UCAN TUI - Modular Protocol Parser Implementation Plan

## 🎯 **Objective**
Implement a modular, extensible system for parsing and interpreting CAN message payloads according to custom protocols, allowing users to see meaningful field names and values instead of raw hex data.

## 📋 **Current Issues to Address**
1. **Ctrl+C Conflict**: Currently mapped to both "copy" and "quit" - need different shortcuts
2. **Raw Data Display**: Detailed view shows hex/binary but no semantic meaning
3. **No Protocol Support**: No way to interpret message payloads based on custom protocols

## 🏗️ **Architecture Design**

### 1. **Abstract Protocol Parser System**
```
📁 can_tui/parsers/
├── __init__.py
├── base.py              # Abstract base class
├── registry.py          # Parser registry and management
├── builtin/             # Built-in parsers
│   ├── __init__.py
│   ├── j1939.py        # SAE J1939 automotive protocol
│   ├── obd2.py         # OBD-II diagnostic protocol
│   └── raw.py          # Default raw hex parser
└── custom/              # User-defined parsers
    ├── __init__.py
    └── example_sensor.py # Example custom parser
```

### 2. **Parser Base Class Structure**
```python
# Abstract base class for all protocol parsers
class ProtocolParser(ABC):
    @abstractmethod
    def can_parse(self, can_id: int, data: bytes) -> bool:
        """Check if this parser can handle the given CAN message"""
        
    @abstractmethod
    def parse(self, can_id: int, data: bytes) -> ParsedMessage:
        """Parse the CAN message and return structured data"""
        
    @abstractmethod
    def get_name(self) -> str:
        """Return parser name for UI display"""
        
    @abstractmethod
    def get_description(self) -> str:
        """Return parser description"""
```

### 3. **Parsed Message Structure**
```python
@dataclass
class ParsedField:
    name: str              # Field name (e.g., "Brake Pressure")
    value: Any             # Parsed value (e.g., 45.2)
    unit: str              # Unit (e.g., "PSI", "RPM", "°C")
    raw_value: int         # Raw binary value
    bit_range: tuple       # (start_bit, end_bit) for highlighting
    description: str       # Field description
    valid: bool            # Whether value is valid/in range

@dataclass
class ParsedMessage:
    parser_name: str       # Name of parser used
    message_type: str      # Type of message (e.g., "Sensor Data")
    fields: List[ParsedField]
    errors: List[str]      # Parse errors/warnings
    confidence: float      # Parse confidence (0.0-1.0)
```

## 🔧 **Implementation Phases**

### **Phase 1: Core Parser Infrastructure** (High Priority)
1. **Create Abstract Base Classes**
   - `ProtocolParser` abstract base class
   - `ParsedMessage` and `ParsedField` data structures
   - Basic validation and error handling

2. **Parser Registry System**
   - Registry to manage available parsers
   - Dynamic parser loading and discovery
   - Parser priority and selection logic

3. **Configuration System**
   - YAML/JSON config files for parser assignments
   - CAN ID to parser mapping
   - Parser-specific configuration parameters

### **Phase 2: Built-in Parsers** (Medium Priority)
1. **Default Raw Parser**
   - Fallback parser for unknown messages
   - Enhanced hex/binary display with bit numbering
   - Basic field extraction (byte boundaries)

2. **Common Protocol Parsers**
   - **J1939 Parser**: Automotive standard protocol
   - **OBD-II Parser**: Diagnostic protocol
   - **Custom Sensor Parser**: Example implementation

### **Phase 3: UI Integration** (High Priority)
1. **Fix Keyboard Shortcuts**
   ```
   Current Issues:
   - Ctrl+C: Copy AND Quit (conflict!)
   
   Proposed Solution:
   - Ctrl+Shift+C: Copy messages
   - Ctrl+Shift+A: Copy all messages  
   - Ctrl+Q: Quit application
   - Ctrl+C: Keep as interrupt/quit (standard)
   ```

2. **Parser Selection UI**
   - Parser configuration panel in sidebar
   - Live parser switching
   - Parser status indicators

3. **Enhanced Detailed View**
   - Show parsed fields in structured format
   - Highlight bits/bytes being parsed
   - Show confidence levels and errors
   - Toggle between raw and parsed views

### **Phase 4: Advanced Features** (Low Priority)
1. **Parser Development Tools**
   - Parser testing framework
   - Message simulation and testing
   - Parser performance profiling

2. **Protocol Documentation**
   - Built-in protocol reference
   - Field documentation display
   - Interactive protocol explorer

## 🎨 **UI Design Mockups**

### **Enhanced Detailed View Example**
```
┌─ CAN Message Details ─────────────────────────────────────────────────┐
│ 🟢 13:45:23.456 RX ID=0x100 [3 bytes] Parser: Custom Sensor v1.0     │
├─ Raw Data ────────────────────────────────────────────────────────────┤
│ 22 33 44 │ 0x223344 │ 001000100011001101000100                       │
├─ Parsed Fields ───────────────────────────────────────────────────────┤
│ Field Name      │ Value    │ Unit │ Bits  │ Raw   │ Status            │
│ Sensor ID       │ 34       │ -    │ 0-7   │ 0x22  │ ✓ Valid           │
│ Brake Pressure  │ 51.2     │ PSI  │ 8-15  │ 0x33  │ ✓ Normal Range    │
│ Status Flags    │ Active   │ -    │ 16-23 │ 0x44  │ ✓ Valid           │
│ ├─ Brake Active │ ON       │ -    │ 16    │ 0     │ ✓ OK              │
│ ├─ ABS Enable   │ OFF      │ -    │ 17    │ 1     │ ✓ OK              │
│ └─ Error Flag   │ OFF      │ -    │ 18    │ 0     │ ✓ No Error        │
├─ Message Info ────────────────────────────────────────────────────────┤
│ Type: Brake System Sensor Data                                        │
│ Parser: Custom Sensor Protocol v1.0                                   │
│ Confidence: 95.5%                                                      │
│ Errors: None                                                           │
└────────────────────────────────────────────────────────────────────────┘
```

### **Parser Selection Panel**
```
┌─ Protocol Parsers ─────────────────────────────┐
│ 🔧 Active Parser: Custom Sensor v1.0          │
├─ Available Parsers ────────────────────────────┤
│ ☑ Raw Data (Default)                          │
│ ☑ J1939 Automotive                            │
│ ☑ OBD-II Diagnostic                           │
│ ☑ Custom Sensor v1.0                          │
│ ☐ Custom Motor Control                        │
├─ Parser Assignment ────────────────────────────┤
│ CAN ID Range: 0x100-0x1FF                     │
│ Parser: Custom Sensor v1.0                    │
│ Priority: High                                 │
│ [Edit] [Remove]                                │
├─ Quick Actions ────────────────────────────────┤
│ [📁 Load Parser]  [⚙️ Configure]              │
│ [📊 Test Parser]  [📖 Documentation]          │
└────────────────────────────────────────────────┘
```

## 🔨 **Implementation Details**

### **1. Example Custom Parser Implementation**
```python
class CustomSensorParser(ProtocolParser):
    def can_parse(self, can_id: int, data: bytes) -> bool:
        return 0x100 <= can_id <= 0x1FF and len(data) >= 3
    
    def parse(self, can_id: int, data: bytes) -> ParsedMessage:
        fields = []
        
        # Parse sensor ID (first byte)
        sensor_id = data[0]
        fields.append(ParsedField(
            name="Sensor ID",
            value=sensor_id,
            unit="",
            raw_value=sensor_id,
            bit_range=(0, 7),
            description="Unique sensor identifier",
            valid=1 <= sensor_id <= 100
        ))
        
        # Parse brake pressure (second byte)
        brake_raw = data[1]
        brake_psi = (brake_raw * 200) / 255  # Scale to 0-200 PSI
        fields.append(ParsedField(
            name="Brake Pressure",
            value=round(brake_psi, 1),
            unit="PSI",
            raw_value=brake_raw,
            bit_range=(8, 15),
            description="Brake system pressure",
            valid=0 <= brake_psi <= 200
        ))
        
        # Parse status flags (third byte)
        status_byte = data[2]
        brake_active = bool(status_byte & 0x01)
        abs_enabled = bool(status_byte & 0x02)
        error_flag = bool(status_byte & 0x04)
        
        fields.append(ParsedField(
            name="Brake Active",
            value="ON" if brake_active else "OFF",
            unit="",
            raw_value=int(brake_active),
            bit_range=(16, 16),
            description="Brake pedal activation status",
            valid=True
        ))
        
        return ParsedMessage(
            parser_name="Custom Sensor v1.0",
            message_type="Brake System Sensor Data",
            fields=fields,
            errors=[],
            confidence=0.95
        )
```

### **2. Parser Registry System**
```python
class ParserRegistry:
    def __init__(self):
        self.parsers: Dict[str, ProtocolParser] = {}
        self.can_id_mappings: Dict[int, str] = {}
        self.range_mappings: List[Tuple[range, str]] = []
    
    def register_parser(self, parser: ProtocolParser):
        self.parsers[parser.get_name()] = parser
    
    def get_parser_for_message(self, can_id: int, data: bytes) -> Optional[ProtocolParser]:
        # Check direct ID mapping first
        if can_id in self.can_id_mappings:
            return self.parsers.get(self.can_id_mappings[can_id])
        
        # Check range mappings
        for range_obj, parser_name in self.range_mappings:
            if can_id in range_obj:
                return self.parsers.get(parser_name)
        
        # Check if any parser can handle this message
        for parser in self.parsers.values():
            if parser.can_parse(can_id, data):
                return parser
        
        return self.parsers.get("Raw Data")  # Fallback
```

### **3. Configuration File Structure**
```yaml
# parser_config.yaml
parsers:
  - name: "Custom Sensor v1.0"
    class: "can_tui.parsers.custom.CustomSensorParser"
    enabled: true
    priority: 10
    
  - name: "J1939 Automotive"
    class: "can_tui.parsers.builtin.J1939Parser"
    enabled: true
    priority: 5

can_id_mappings:
  # Direct ID mappings
  0x100: "Custom Sensor v1.0"
  0x101: "Custom Sensor v1.0"
  
  # Range mappings
  ranges:
    - start: 0x200
      end: 0x2FF
      parser: "J1939 Automotive"
      
    - start: 0x7E0
      end: 0x7E7
      parser: "OBD-II Diagnostic"

default_parser: "Raw Data"
```

## 🎯 **Success Criteria**
1. **Modularity**: Easy to add new protocol parsers
2. **Usability**: Intuitive UI for parser selection and configuration
3. **Performance**: Parsing doesn't slow down message display
4. **Extensibility**: Support for complex nested protocols
5. **Documentation**: Clear examples and API documentation

## 🚀 **Next Steps**
1. **Immediate**: Fix Ctrl+C keyboard shortcut conflict
2. **Week 1**: Implement core parser infrastructure
3. **Week 2**: Create example custom parser and integrate with UI
4. **Week 3**: Add parser selection UI and configuration system
5. **Week 4**: Testing, documentation, and refinement

## 💡 **Future Enhancements**
- **Real-time Protocol Learning**: AI-assisted protocol discovery
- **Multi-message Parsing**: Parse sequences of related messages
- **Protocol Validation**: Validate parsed data against protocol specs
- **Export Parsed Data**: Export interpreted data in various formats
- **Protocol Marketplace**: Share and download community parsers

---

This modular approach will transform the TUI from a simple hex viewer into a powerful protocol analysis tool while maintaining flexibility for custom implementations.
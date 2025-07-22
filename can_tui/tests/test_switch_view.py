"""
Tests for the switch view system and parser.
"""

import unittest
from unittest.mock import Mock, patch

from ..models.can_message import CANMessage
from ..parsers.custom.wiring_harness_switch import WiringHarnessSwitchParser
from ..views.switch_view import SwitchView
from ..views.registry import ViewRegistry, ViewManager
from ..views.base import ViewMode


class TestWiringHarnessSwitchParser(unittest.TestCase):
    """Test the wiring harness switch parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = WiringHarnessSwitchParser()
        
        # Valid test message data
        data = bytearray(8)
        data[0] = 0x5A  # Signature
        data[1] = 0x10  # Switch bitmap (Forward switch = bit 3)
        data[2] = 0x34  # Timestamp LSB
        data[3] = 0x12  # Timestamp
        data[4] = 0x00  # Timestamp
        data[5] = 0x00  # Timestamp MSB
        data[6] = 0x00  # Reserved
        data[7] = 0xFF  # End marker
        self.valid_message_data = bytes(data)
        
        # Invalid signature data
        data[0] = 0x99  # Invalid signature
        self.invalid_signature_data = bytes(data)
    
    def test_parser_creation(self):
        """Test parser can be created."""
        self.assertEqual(self.parser.name, "Wiring Harness Switch State")
        self.assertEqual(self.parser.version, "1.0")
        self.assertEqual(self.parser.priority, 2)
    
    def test_can_parse_valid_message(self):
        """Test parser accepts valid 0x500 messages."""
        self.assertTrue(self.parser.can_parse(0x500, self.valid_message_data))
    
    def test_can_parse_wrong_can_id(self):
        """Test parser rejects wrong CAN ID."""
        self.assertFalse(self.parser.can_parse(0x501, self.valid_message_data))
    
    def test_can_parse_wrong_length(self):
        """Test parser rejects wrong data length."""
        short_data = bytes([0x5A, 0x10, 0x34, 0xFF])  # Only 4 bytes
        self.assertFalse(self.parser.can_parse(0x500, short_data))
    
    def test_can_parse_invalid_signature(self):
        """Test parser rejects invalid signature."""
        self.assertFalse(self.parser.can_parse(0x500, self.invalid_signature_data))
    
    def test_can_parse_invalid_end_marker(self):
        """Test parser rejects invalid end marker."""
        data = bytearray(8)
        data[0] = 0x5A  # Valid signature
        data[7] = 0x00  # Invalid end marker
        self.assertFalse(self.parser.can_parse(0x500, bytes(data)))
    
    def test_parse_valid_message(self):
        """Test parsing a valid message."""
        parsed = self.parser.parse(0x500, self.valid_message_data)
        
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.parser_name, "Wiring Harness Switch State")
        self.assertEqual(parsed.message_type, "Switch State")
        self.assertTrue(parsed.is_valid())
        self.assertEqual(len(parsed.errors), 0)
        
        # Check that we have the expected fields
        field_names = [field.name for field in parsed.fields]
        self.assertIn("Forward Switch", field_names)
        self.assertIn("Message Signature", field_names)
        self.assertIn("End Marker", field_names)
        self.assertIn("Timestamp", field_names)
    
    def test_parse_switch_states(self):
        """Test parsing individual switch states."""
        # Create message with multiple switches active
        data = bytearray(8)
        data[0] = 0x5A  # Signature
        data[1] = 0x19  # Binary: 00011001 = Brake(0) + Forward(3) + Horn(4)
        data[2] = 0x34  # Timestamp
        data[3] = 0x12
        data[4] = 0x00
        data[5] = 0x00
        data[6] = 0x00  # Reserved
        data[7] = 0xFF  # End marker
        
        parsed = self.parser.parse(0x500, bytes(data))
        
        # Check individual switches
        brake_field = parsed.get_field_by_name("Brake Switch")
        forward_field = parsed.get_field_by_name("Forward Switch")
        horn_field = parsed.get_field_by_name("Horn Switch")
        reverse_field = parsed.get_field_by_name("Reverse Switch")
        
        self.assertTrue(brake_field.value)    # Bit 0 set
        self.assertTrue(forward_field.value)  # Bit 3 set
        self.assertTrue(horn_field.value)     # Bit 4 set
        self.assertFalse(reverse_field.value) # Bit 2 not set
    
    def test_parse_timestamp(self):
        """Test timestamp parsing."""
        parsed = self.parser.parse(0x500, self.valid_message_data)
        timestamp_field = parsed.get_field_by_name("Timestamp")
        
        # Timestamp should be 0x00001234 (little-endian)
        expected_timestamp = 0x1234
        self.assertEqual(timestamp_field.value, expected_timestamp)
    
    def test_parse_operational_state(self):
        """Test operational state detection."""
        # Test FORWARD state
        data = bytearray(8)
        data[0] = 0x5A
        data[1] = 0x08  # Forward switch only (bit 3)
        data[7] = 0xFF
        
        parsed = self.parser.parse(0x500, bytes(data))
        state_field = parsed.get_field_by_name("Operational State")
        self.assertEqual(state_field.value, "FORWARD")
        
        # Test BRAKING state
        data[1] = 0x01  # Brake switch only (bit 0)
        parsed = self.parser.parse(0x500, bytes(data))
        state_field = parsed.get_field_by_name("Operational State")
        self.assertEqual(state_field.value, "BRAKING")
    
    def test_supported_can_ids(self):
        """Test supported CAN IDs."""
        supported_ids = self.parser.get_supported_ids()
        self.assertIn(0x500, supported_ids)
    
    def test_parser_description(self):
        """Test parser description."""
        desc = self.parser.get_description()
        self.assertIn("wiring harness", desc.lower())
        self.assertIn("0x500", desc)


class TestSwitchView(unittest.TestCase):
    """Test the switch view widget."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.switch_view = SwitchView()
        
        # Create test CAN message
        data = bytearray(8)
        data[0] = 0x5A  # Signature
        data[1] = 0x10  # Forward switch
        data[2] = 0x34  # Timestamp
        data[3] = 0x12
        data[4] = 0x00
        data[5] = 0x00
        data[6] = 0x00  # Reserved
        data[7] = 0xFF  # End marker
        
        self.test_can_message = CANMessage(
            type="CAN_RX",
            can_id=0x500,
            data=bytes(data),
            timestamp=None,
            success=True
        )
    
    def test_view_creation(self):
        """Test switch view can be created."""
        self.assertEqual(self.switch_view.get_view_name(), "Switch Dashboard")
        self.assertEqual(self.switch_view.get_priority(), 2)
        self.assertIn(0x500, self.switch_view.get_supported_can_ids())
    
    def test_can_handle_correct_message(self):
        """Test view can handle correct messages."""
        # Mock parsed message
        mock_parsed = Mock()
        mock_parsed.parser_name = "Wiring Harness Switch State"
        
        self.assertTrue(self.switch_view.can_handle_message(self.test_can_message, mock_parsed))
    
    def test_can_handle_wrong_can_id(self):
        """Test view rejects wrong CAN ID."""
        wrong_message = CANMessage(
            type="CAN_RX",
            can_id=0x400,  # Wrong ID
            data=bytes(8),
            timestamp=None,
            success=True
        )
        
        self.assertFalse(self.switch_view.can_handle_message(wrong_message, None))
    
    def test_view_stats(self):
        """Test view statistics."""
        stats = self.switch_view.get_stats()
        self.assertIn("message_count", stats)
        self.assertIn("error_count", stats)
        self.assertIn("view_name", stats)
        self.assertEqual(stats["view_name"], "Switch Dashboard")


class TestViewRegistry(unittest.TestCase):
    """Test the view registry system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = ViewRegistry()
        
        # Create mock view
        self.mock_view = Mock()
        self.mock_view.get_view_name.return_value = "Test View"
        self.mock_view.get_supported_can_ids.return_value = [0x500]
        self.mock_view.get_priority.return_value = 5
        self.mock_view.is_enabled.return_value = True
        self.mock_view.can_handle_message.return_value = True
    
    def test_registry_creation(self):
        """Test registry can be created."""
        self.assertEqual(len(self.registry.views), 0)
        self.assertEqual(len(self.registry.can_id_mappings), 0)
    
    def test_register_view(self):
        """Test registering a view."""
        self.registry.register_view(self.mock_view)
        
        self.assertIn("Test View", self.registry.views)
        self.assertIn(0x500, self.registry.can_id_mappings)
        self.assertEqual(self.registry.can_id_mappings[0x500], "Test View")
    
    def test_get_view_for_message(self):
        """Test finding view for a message."""
        self.registry.register_view(self.mock_view)
        
        test_message = CANMessage(
            type="CAN_RX",
            can_id=0x500,
            data=bytes(8),
            timestamp=None,
            success=True
        )
        
        found_view = self.registry.get_view_for_message(test_message, None)
        self.assertEqual(found_view, self.mock_view)
    
    def test_registry_stats(self):
        """Test registry statistics."""
        self.registry.register_view(self.mock_view)
        
        stats = self.registry.get_stats()
        self.assertEqual(stats["total_views"], 1)
        self.assertEqual(stats["enabled_views"], 1)
        self.assertEqual(stats["can_id_mappings"], 1)
        self.assertIn(0x500, stats["registered_can_ids"])


class TestViewManager(unittest.TestCase):
    """Test the view manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create registry with mock view
        self.registry = ViewRegistry()
        
        mock_view = Mock()
        mock_view.get_view_name.return_value = "Test View"
        mock_view.get_supported_can_ids.return_value = [0x500]
        mock_view.get_priority.return_value = 5
        mock_view.is_enabled.return_value = True
        mock_view.can_handle_message.return_value = True
        mock_view.update_message.return_value = None
        
        self.registry.register_view(mock_view)
        self.manager = ViewManager(self.registry)
    
    def test_manager_creation(self):
        """Test manager can be created."""
        self.assertEqual(self.manager.current_mode, ViewMode.MESSAGE_LOG)
    
    def test_set_view_mode(self):
        """Test setting view mode."""
        self.assertTrue(self.manager.set_view_mode(ViewMode.CUSTOM_VIEW))
        self.assertEqual(self.manager.get_current_mode(), ViewMode.CUSTOM_VIEW)
    
    def test_manager_stats(self):
        """Test manager statistics."""
        stats = self.manager.get_stats()
        self.assertIn("current_mode", stats)
        self.assertIn("registry_stats", stats)
        self.assertEqual(stats["current_mode"], "message_log")


def create_test_can_message(can_id=0x500, forward_switch=True, brake_switch=False):
    """Helper function to create test CAN messages."""
    switch_bitmap = 0
    if brake_switch:
        switch_bitmap |= (1 << 0)  # Brake Switch
    if forward_switch:
        switch_bitmap |= (1 << 3)  # Forward Switch
    
    data = bytearray(8)
    data[0] = 0x5A              # Signature
    data[1] = switch_bitmap     # Switch bitmap
    data[2] = 0x34              # Timestamp LSB
    data[3] = 0x12              # Timestamp
    data[4] = 0x00              # Timestamp
    data[5] = 0x00              # Timestamp MSB
    data[6] = 0x00              # Reserved
    data[7] = 0xFF              # End marker
    
    return CANMessage(
        type="CAN_RX",
        can_id=can_id,
        data=bytes(data),
        timestamp=None,
        success=True
    )


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete switch view system."""
    
    def test_parser_and_view_integration(self):
        """Test that parser and view work together."""
        # Create components
        parser = WiringHarnessSwitchParser()
        view = SwitchView()
        registry = ViewRegistry()
        
        # Register view
        registry.register_view(view)
        
        # Create test message
        test_message = create_test_can_message(forward_switch=True, brake_switch=True)
        
        # Parse message
        if parser.can_parse(test_message.can_id, test_message.data):
            parsed = parser.parse(test_message.can_id, test_message.data)
            
            # Check view can handle it
            found_view = registry.get_view_for_message(test_message, parsed)
            self.assertEqual(found_view, view)
            
            # Update view (mock the widget since we can't test UI)
            with patch.object(view, 'switch_widget'):
                view.update_message(test_message, parsed)
                self.assertEqual(view.message_count, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
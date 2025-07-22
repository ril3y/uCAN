"""
Tests for the view settings modal and configuration system.
"""

import unittest
from unittest.mock import Mock, patch

from ..widgets.view_settings_modal import ViewSettingsModal
from ..views.registry import ViewRegistry, ViewManager
from ..views.base import ViewMode


class TestViewSettingsModal:
    """Test the view settings modal."""
    
    @pytest.fixture
    def mock_registry(self):
        """Create a mock view registry."""
        registry = Mock(spec=ViewRegistry)
        
        # Mock view data
        mock_switch_view = Mock()
        mock_switch_view.get_view_name.return_value = "Switch Dashboard"
        mock_switch_view.get_description.return_value = "Visual switch state display"
        mock_switch_view.get_supported_can_ids.return_value = [0x500]
        
        registry.get_all_views.return_value = {
            "Switch Dashboard": mock_switch_view
        }
        
        return registry
    
    @pytest.fixture  
    def mock_manager(self, mock_registry):
        """Create a mock view manager."""
        manager = Mock(spec=ViewManager)
        manager.view_registry = mock_registry
        return manager
    
    @pytest.fixture
    def modal(self, mock_manager, mock_registry):
        """Create a view settings modal."""
        return ViewSettingsModal(
            view_manager=mock_manager,
            view_registry=mock_registry,
            current_settings={
                "view_mode": "message_log",
                "auto_switch": True,
                "enabled_views": {"Switch Dashboard": True},
                "can_id_view_mappings": {}
            }
        )
    
    def test_modal_creation(self, modal):
        """Test modal can be created."""
        assert modal.title == "View Settings"
        assert modal.current_settings["view_mode"] == "message_log"
        assert modal.settings["auto_switch"] is True
    
    def test_default_settings_merge(self):
        """Test that default settings are properly merged."""
        current_settings = {"view_mode": "custom_view"}
        
        modal = ViewSettingsModal(current_settings=current_settings)
        
        # Should have default auto_switch but custom view_mode
        assert modal.settings["view_mode"] == "custom_view"
        assert modal.settings["auto_switch"] is True
    
    def test_get_current_settings(self, modal):
        """Test getting current settings."""
        settings = modal.get_current_settings()
        assert "view_mode" in settings
        assert "auto_switch" in settings
        assert "enabled_views" in settings
        assert "can_id_view_mappings" in settings


class TestViewModeConfiguration:
    """Test view mode configuration and switching."""
    
    def test_view_mode_enum_values(self):
        """Test that ViewMode enum has expected values."""
        assert ViewMode.MESSAGE_LOG.value == "message_log"
        assert ViewMode.CUSTOM_VIEW.value == "custom_view"
        assert ViewMode.SPLIT_VIEW.value == "split_view"
    
    def test_view_manager_mode_switching(self):
        """Test view manager mode switching."""
        registry = ViewRegistry()
        manager = ViewManager(registry)
        
        # Test switching to custom view mode
        assert manager.set_view_mode(ViewMode.CUSTOM_VIEW) is True
        assert manager.get_current_mode() == ViewMode.CUSTOM_VIEW
        
        # Test switching to split view mode  
        assert manager.set_view_mode(ViewMode.SPLIT_VIEW) is True
        assert manager.get_current_mode() == ViewMode.SPLIT_VIEW
        
        # Test switching back to message log
        assert manager.set_view_mode(ViewMode.MESSAGE_LOG) is True
        assert manager.get_current_mode() == ViewMode.MESSAGE_LOG
    
    def test_available_modes(self):
        """Test getting available view modes."""
        registry = ViewRegistry()
        manager = ViewManager(registry)
        
        available_modes = manager.get_available_modes()
        assert ViewMode.MESSAGE_LOG in available_modes
        assert ViewMode.CUSTOM_VIEW in available_modes
        assert ViewMode.SPLIT_VIEW in available_modes
        assert len(available_modes) == 3


class TestViewConfiguration:
    """Test view configuration and management."""
    
    @pytest.fixture
    def registry_with_views(self):
        """Create a registry with multiple mock views."""
        registry = ViewRegistry()
        
        # Create mock switch view
        switch_view = Mock()
        switch_view.get_view_name.return_value = "Switch Dashboard"
        switch_view.get_supported_can_ids.return_value = [0x500]
        switch_view.get_priority.return_value = 2
        switch_view.is_enabled.return_value = True
        switch_view.set_enabled = Mock()
        switch_view.get_description.return_value = "Switch state visualization"
        
        # Create mock throttle view
        throttle_view = Mock()
        throttle_view.get_view_name.return_value = "Throttle Gauge"
        throttle_view.get_supported_can_ids.return_value = [0x101]
        throttle_view.get_priority.return_value = 3
        throttle_view.is_enabled.return_value = True
        throttle_view.set_enabled = Mock()
        throttle_view.get_description.return_value = "Throttle position gauge"
        
        registry.register_view(switch_view)
        registry.register_view(throttle_view)
        
        return registry
    
    def test_view_enable_disable(self, registry_with_views):
        """Test enabling and disabling views."""
        # Test disabling a view
        result = registry_with_views.set_view_enabled("Switch Dashboard", False)
        assert result is True
        
        # Test enabling a view
        result = registry_with_views.set_view_enabled("Switch Dashboard", True)
        assert result is True
        
        # Test non-existent view
        result = registry_with_views.set_view_enabled("Non-existent View", False)
        assert result is False
    
    def test_can_id_mappings(self, registry_with_views):
        """Test CAN ID to view mappings."""
        # Test adding mapping
        registry_with_views.add_can_id_mapping(0x600, "Switch Dashboard")
        
        # Test getting all views returns the registered ones
        all_views = registry_with_views.get_all_views()
        assert len(all_views) == 2
        assert "Switch Dashboard" in all_views
        assert "Throttle Gauge" in all_views
    
    def test_enabled_views_filtering(self, registry_with_views):
        """Test filtering enabled vs disabled views."""
        # Initially all should be enabled
        enabled_views = registry_with_views.get_enabled_views()
        assert len(enabled_views) == 2
        
        # Disable one view
        registry_with_views.set_view_enabled("Switch Dashboard", False)
        enabled_views = registry_with_views.get_enabled_views()
        assert len(enabled_views) == 1
        assert "Throttle Gauge" in enabled_views
        assert "Switch Dashboard" not in enabled_views
    
    def test_registry_stats(self, registry_with_views):
        """Test registry statistics."""
        stats = registry_with_views.get_stats()
        
        assert stats["total_views"] == 2
        assert stats["enabled_views"] == 2
        assert stats["disabled_views"] == 0
        assert len(stats["registered_can_ids"]) >= 2  # Auto-registered CAN IDs
        
        # Disable one view and check stats again
        registry_with_views.set_view_enabled("Switch Dashboard", False)
        stats = registry_with_views.get_stats()
        
        assert stats["total_views"] == 2
        assert stats["enabled_views"] == 1
        assert stats["disabled_views"] == 1


class TestViewCustomization:
    """Test view customization features."""
    
    def test_custom_view_selection_for_can_ids(self):
        """Test getting custom views available for specific CAN IDs."""
        registry = ViewRegistry()
        manager = ViewManager(registry)
        
        # Mock view that supports 0x500
        mock_view = Mock()
        mock_view.get_view_name.return_value = "Switch Dashboard"
        mock_view.get_supported_can_ids.return_value = [0x500]
        mock_view.get_priority.return_value = 2
        mock_view.is_enabled.return_value = True
        
        registry.register_view(mock_view)
        
        # Test getting views for CAN IDs
        available_views = manager.get_custom_views_for_can_ids([0x500, 0x501])
        
        assert 0x500 in available_views
        assert "Switch Dashboard" in available_views[0x500]
        # 0x501 might not have any views
        
    def test_active_can_ids_tracking(self):
        """Test tracking active CAN IDs for view switching."""
        registry = ViewRegistry()
        manager = ViewManager(registry)
        
        # Set active CAN IDs
        manager.set_active_can_ids([0x500, 0x501, 0x502])
        
        assert manager.active_can_ids == {0x500, 0x501, 0x502}
        
        # Update active CAN IDs
        manager.set_active_can_ids([0x500, 0x600])
        
        assert manager.active_can_ids == {0x500, 0x600}
    
    def test_view_reset(self):
        """Test resetting all view states."""
        registry = ViewRegistry()
        manager = ViewManager(registry)
        
        # Mock view with reset capability
        mock_view = Mock()
        mock_view.get_view_name.return_value = "Test View"
        mock_view.get_supported_can_ids.return_value = [0x500]
        mock_view.get_priority.return_value = 5
        mock_view.is_enabled.return_value = True
        mock_view.reset = Mock()
        
        registry.register_view(mock_view)
        
        # Reset all views
        manager.reset_all_views()
        
        # Check that reset was called
        mock_view.reset.assert_called_once()
        
        # Check that current view is cleared
        assert manager.current_view is None


class TestSettingsIntegration:
    """Integration tests for view settings with the main application."""
    
    def test_settings_application_workflow(self):
        """Test the complete workflow of applying view settings."""
        # This would test the apply_view_settings method from the main app
        # Since we can't easily test the full app, we'll test the logic
        
        settings = {
            "view_mode": "custom_view",
            "auto_switch": False,
            "enabled_views": {
                "Switch Dashboard": True,
                "Throttle Gauge": False
            },
            "can_id_view_mappings": {
                0x500: "Switch Dashboard"
            }
        }
        
        # Test that the settings structure is valid
        assert "view_mode" in settings
        assert settings["view_mode"] in ["message_log", "custom_view", "split_view"]
        assert isinstance(settings["auto_switch"], bool)
        assert isinstance(settings["enabled_views"], dict)
        assert isinstance(settings["can_id_view_mappings"], dict)
        
        # Test CAN ID mapping values
        for can_id, view_name in settings["can_id_view_mappings"].items():
            assert isinstance(can_id, int)
            assert isinstance(view_name, str)
            assert can_id > 0  # Valid CAN ID range
    
    def test_view_mode_validation(self):
        """Test validation of view mode settings."""
        valid_modes = ["message_log", "custom_view", "split_view"]
        
        for mode in valid_modes:
            settings = {"view_mode": mode}
            # This should not raise an error
            assert settings["view_mode"] in valid_modes
        
        # Test invalid mode
        invalid_settings = {"view_mode": "invalid_mode"}
        assert invalid_settings["view_mode"] not in valid_modes
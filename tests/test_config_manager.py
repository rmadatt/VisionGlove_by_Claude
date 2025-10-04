"""Tests for configuration manager."""

import pytest
import tempfile
import json
from pathlib import Path

from vision_glove.core.config_manager import ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def test_default_config_loading(self):
        """Test loading default configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            config_manager = ConfigManager(str(config_path))
            
            # Should have default values
            assert config_manager.get('system.name') == 'VisionGlove'
            assert config_manager.get('sensors.enabled') is True
            assert config_manager.get('vision.fps') == 30
    
    def test_config_get_set(self):
        """Test getting and setting configuration values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            config_manager = ConfigManager(str(config_path))
            
            # Test setting and getting values
            config_manager.set('test.value', 42)
            assert config_manager.get('test.value') == 42
            
            # Test nested values
            config_manager.set('nested.deep.value', 'test')
            assert config_manager.get('nested.deep.value') == 'test'
    
    def test_config_save_load(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            
            # Create and modify config
            config_manager1 = ConfigManager(str(config_path))
            config_manager1.set('test.save_load', 'test_value')
            config_manager1.save_config()
            
            # Load config in new instance
            config_manager2 = ConfigManager(str(config_path))
            assert config_manager2.get('test.save_load') == 'test_value'
    
    def test_config_validation(self):
        """Test configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            config_manager = ConfigManager(str(config_path))
            
            # Valid configuration should pass
            assert config_manager.validate() is True
            
            # Invalid sensor sample rate should fail
            config_manager.set('sensors.sample_rate', -1)
            assert config_manager.validate() is False
    
    def test_get_section(self):
        """Test getting entire configuration sections."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            config_manager = ConfigManager(str(config_path))
            
            # Get vision section
            vision_config = config_manager.get_section('vision')
            assert 'enabled' in vision_config
            assert 'camera_index' in vision_config
            assert 'fps' in vision_config

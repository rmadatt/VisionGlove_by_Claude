"""Configuration management for VisionGlove system."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration settings for the VisionGlove system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. If None, uses default.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_default_config()
        
        # Load from file if it exists
        if self.config_path.exists():
            self.load_config()
        else:
            # Create config directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.save_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration settings."""
        return {
            "system": {
                "name": "VisionGlove",
                "version": "1.0.0",
                "debug_mode": False,
                "log_level": "INFO"
            },
            "sensors": {
                "enabled": True,
                "sample_rate": 100,  # Hz
                "calibration_required": True,
                "timeout": 5.0  # seconds
            },
            "vision": {
                "enabled": True,
                "camera_index": 0,
                "resolution": [640, 480],
                "fps": 30,
                "detection_threshold": 0.7,
                "person_threshold": 3
            },
            "haptics": {
                "enabled": True,
                "intensity": 0.8,
                "duration": 1.0,  # seconds
                "pattern": "pulse"
            },
            "communications": {
                "emergency_contact": "",
                "police_number": "",
                "sms_service": {
                    "provider": "twilio",
                    "account_sid": "",
                    "auth_token": "",
                    "from_number": ""
                }
            },
            "security": {
                "encryption_enabled": True,
                "key_rotation_interval": 3600,  # seconds
                "max_failed_attempts": 3
            },
            "livestream": {
                "enabled": True,
                "quality": "medium",
                "platform": "youtube",
                "stream_key": "",
                "max_duration": 3600  # seconds
            }
        }
    
    def load_config(self) -> bool:
        """
        Load configuration from file.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            with open(self.config_path, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
            logger.info(f"Configuration loaded from {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        Save current configuration to file.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'vision.camera_index')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'vision.camera_index')
            value: Value to set
        """
        keys = key.split('.')
        config_ref = self.config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config_ref:
                config_ref[k] = {}
            config_ref = config_ref[k]
        
        # Set the value
        config_ref[keys[-1]] = value
        logger.debug(f"Configuration updated: {key} = {value}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Configuration section dictionary
        """
        return self.config.get(section, {})
    
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid, False otherwise.
        """
        required_sections = ['system', 'sensors', 'vision', 'haptics', 'communications']
        
        for section in required_sections:
            if section not in self.config:
                logger.error(f"Missing required configuration section: {section}")
                return False
        
        # Validate specific settings
        if not isinstance(self.get('sensors.sample_rate'), (int, float)) or self.get('sensors.sample_rate') <= 0:
            logger.error("Invalid sensors.sample_rate: must be positive number")
            return False
        
        if not isinstance(self.get('vision.resolution'), list) or len(self.get('vision.resolution')) != 2:
            logger.error("Invalid vision.resolution: must be [width, height] list")
            return False
        
        return True

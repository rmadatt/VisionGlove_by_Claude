"""
VisionGlove - A cybernetic glove project for enhanced safety and capabilities.

This package provides modular components for:
- Sensor data processing
- Computer vision capabilities
- Haptic feedback control
- Secure communications
- Emergency response systems
"""

__version__ = "1.0.0"
__author__ = "VisionGlove Development Team"

# Import main components for easy access
from .core.glove_system import VisionGloveSystem
from .core.config_manager import ConfigManager

__all__ = ["VisionGloveSystem", "ConfigManager"]

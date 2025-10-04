"""Main VisionGlove system controller."""

import asyncio
from typing import Optional, Dict, Any
import time

from .config_manager import ConfigManager
from .logger import LoggerMixin
from ..sensors.sensor_manager import SensorManager
from ..vision.vision_processor import VisionProcessor
from ..haptics.haptic_controller import HapticController
from ..communications.emergency_dispatcher import EmergencyDispatcher
from ..security.auth_manager import AuthManager


class VisionGloveSystem(LoggerMixin):
    """Main system controller for VisionGlove."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize VisionGlove system.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config = ConfigManager(config_path)
        self.is_running = False
        self.start_time = None
        
        # Initialize subsystems
        self.sensor_manager = None
        self.vision_processor = None
        self.haptic_controller = None
        self.emergency_dispatcher = None
        self.auth_manager = None
        
        # System state
        self.threat_level = 0  # 0: Safe, 1: Caution, 2: Alert, 3: Emergency
        self.last_update = None
        
        self.logger.info("VisionGlove system initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize all subsystems.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Starting system initialization...")
            
            # Validate configuration
            if not self.config.validate():
                raise RuntimeError("Configuration validation failed")
            
            # Initialize authentication
            self.auth_manager = AuthManager(self.config.get_section('security'))
            if not await self.auth_manager.initialize():
                raise RuntimeError("Authentication manager initialization failed")
            
            # Initialize sensor manager
            if self.config.get('sensors.enabled'):
                self.sensor_manager = SensorManager(self.config.get_section('sensors'))
                if not await self.sensor_manager.initialize():
                    raise RuntimeError("Sensor manager initialization failed")
            
            # Initialize vision processor
            if self.config.get('vision.enabled'):
                self.vision_processor = VisionProcessor(self.config.get_section('vision'))
                if not await self.vision_processor.initialize():
                    raise RuntimeError("Vision processor initialization failed")
            
            # Initialize haptic controller
            if self.config.get('haptics.enabled'):
                self.haptic_controller = HapticController(self.config.get_section('haptics'))
                if not await self.haptic_controller.initialize():
                    raise RuntimeError("Haptic controller initialization failed")
            
            # Initialize emergency dispatcher
            self.emergency_dispatcher = EmergencyDispatcher(
                self.config.get_section('communications'),
                self.config.get_section('livestream')
            )
            if not await self.emergency_dispatcher.initialize():
                raise RuntimeError("Emergency dispatcher initialization failed")
            
            self.logger.info("System initialization completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            return False
    
    async def start(self) -> bool:
        """
        Start the VisionGlove system.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            if self.is_running:
                self.logger.warning("System is already running")
                return True
            
            if not await self.initialize():
                return False
            
            self.is_running = True
            self.start_time = time.time()
            
            # Start main processing loop
            asyncio.create_task(self._main_loop())
            
            self.logger.info("VisionGlove system started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start system: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the VisionGlove system.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            if not self.is_running:
                self.logger.warning("System is not running")
                return True
            
            self.is_running = False
            
            # Stop all subsystems
            if self.sensor_manager:
                await self.sensor_manager.stop()
            
            if self.vision_processor:
                await self.vision_processor.stop()
            
            if self.haptic_controller:
                await self.haptic_controller.stop()
            
            if self.emergency_dispatcher:
                await self.emergency_dispatcher.stop()
            
            uptime = time.time() - self.start_time if self.start_time else 0
            self.logger.info(f"VisionGlove system stopped (uptime: {uptime:.2f}s)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop system: {e}")
            return False
    
    async def _main_loop(self):
        """Main processing loop."""
        self.logger.info("Main processing loop started")
        
        while self.is_running:
            try:
                await self._process_cycle()
                await asyncio.sleep(0.1)  # 10Hz main loop
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(1.0)  # Longer delay on error
    
    async def _process_cycle(self):
        """Process one cycle of sensor data and analysis."""
        current_time = time.time()
        
        # Collect sensor data
        sensor_data = {}
        if self.sensor_manager:
            sensor_data = await self.sensor_manager.get_latest_data()
        
        # Process vision data
        vision_data = {}
        if self.vision_processor:
            vision_data = await self.vision_processor.process_frame()
        
        # Analyze threat level
        new_threat_level = self._analyze_threat_level(sensor_data, vision_data)
        
        # Handle threat level changes
        if new_threat_level != self.threat_level:
            await self._handle_threat_change(new_threat_level)
        
        self.threat_level = new_threat_level
        self.last_update = current_time
    
    def _analyze_threat_level(self, sensor_data: Dict, vision_data: Dict) -> int:
        """
        Analyze current threat level based on sensor and vision data.
        
        Args:
            sensor_data: Latest sensor readings
            vision_data: Latest vision analysis
            
        Returns:
            Threat level (0-3)
        """
        threat_level = 0
        
        # Check for multiple people detected
        if vision_data.get('person_count', 0) >= self.config.get('vision.person_threshold'):
            threat_level = max(threat_level, 1)  # Caution
        
        # Check for suspicious movements or gestures
        if sensor_data.get('unusual_movement', False):
            threat_level = max(threat_level, 2)  # Alert
        
        # Check for emergency gestures or panic signals
        if sensor_data.get('emergency_gesture', False):
            threat_level = 3  # Emergency
        
        return threat_level
    
    async def _handle_threat_change(self, new_level: int):
        """
        Handle changes in threat level.
        
        Args:
            new_level: New threat level
        """
        self.logger.info(f"Threat level changed: {self.threat_level} -> {new_level}")
        
        # Provide haptic feedback
        if self.haptic_controller:
            await self.haptic_controller.threat_feedback(new_level)
        
        # Handle emergency situations
        if new_level >= 3:
            self.logger.warning("Emergency situation detected!")
            if self.emergency_dispatcher:
                await self.emergency_dispatcher.dispatch_emergency({
                    'threat_level': new_level,
                    'timestamp': time.time(),
                    'location': 'Unknown',  # TODO: Add GPS integration
                    'sensor_data': {},  # TODO: Add relevant sensor data
                    'vision_data': {}   # TODO: Add relevant vision data
                })
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current system status.
        
        Returns:
            Dictionary containing system status information
        """
        uptime = time.time() - self.start_time if self.start_time else 0
        
        return {
            'running': self.is_running,
            'uptime': uptime,
            'threat_level': self.threat_level,
            'last_update': self.last_update,
            'subsystems': {
                'sensors': self.sensor_manager is not None and self.sensor_manager.is_active(),
                'vision': self.vision_processor is not None and self.vision_processor.is_active(),
                'haptics': self.haptic_controller is not None and self.haptic_controller.is_active(),
                'emergency': self.emergency_dispatcher is not None and self.emergency_dispatcher.is_active()
            }
        }

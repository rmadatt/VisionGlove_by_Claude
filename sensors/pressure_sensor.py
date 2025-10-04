"""Pressure sensor implementation for grip and touch detection."""

import asyncio
from typing import Dict, Any
from datetime import datetime
import math

from ..core.logger import LoggerMixin


class PressureSensor(LoggerMixin):
    """Individual pressure sensor for detecting grip strength and contact points."""
    
    def __init__(self, location_id: int, config: Dict[str, Any]):
        """
        Initialize pressure sensor.
        
        Args:
            location_id: Sensor location identifier
            config: Sensor configuration
        """
        self.location_id = location_id
        self.config = config
        self.is_initialized = False
        
        # Location names for logging
        self.location_names = ['palm', 'thumb_tip', 'index_tip', 'middle_tip', 'ring_tip', 'pinky_tip']
        self.location_name = (self.location_names[location_id] 
                            if location_id < len(self.location_names) 
                            else f'location_{location_id}')
        
        # Calibration data
        self.min_pressure = 0.0
        self.max_pressure = 1000.0  # Example max pressure in arbitrary units
        self.baseline = 0.0
        self.sensitivity = 1.0
        
        # Touch detection
        self.touch_threshold = 0.1  # Minimum pressure to register as touch
        self.is_touching = False
        self.touch_start_time = None
        
        self.logger.debug(f"Pressure sensor initialized for {self.location_name}")
    
    async def initialize(self) -> bool:
        """
        Initialize the pressure sensor hardware.
        
        Returns:
            True if initialization successful
        """
        try:
            # TODO: Initialize actual hardware interface
            # This would typically involve:
            # - Setting up ADC channels for force-sensitive resistors (FSRs)
            # - Configuring amplifier circuits
            # - Setting up communication protocols
            
            self.is_initialized = True
            self.logger.info(f"Pressure sensor for {self.location_name} initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize pressure sensor for {self.location_name}: {e}")
            return False
    
    async def read(self) -> Dict[str, Any]:
        """
        Read current pressure sensor value.
        
        Returns:
            Dictionary containing pressure reading and metadata
        """
        try:
            if not self.is_initialized:
                raise RuntimeError(f"Pressure sensor for {self.location_name} not initialized")
            
            # Read raw sensor value
            raw_value = await self._read_hardware()
            
            # Apply calibration
            calibrated_value = self._apply_calibration(raw_value)
            
            # Update touch state
            self._update_touch_state(calibrated_value)
            
            # Calculate additional metrics
            pressure_percentage = (calibrated_value / self.max_pressure) * 100
            force_newton = self._pressure_to_force(calibrated_value)
            
            return {
                'location_id': self.location_id,
                'location_name': self.location_name,
                'raw_value': raw_value,
                'value': calibrated_value,
                'pressure_percentage': pressure_percentage,
                'force_newton': force_newton,
                'is_touching': self.is_touching,
                'touch_duration': self._get_touch_duration(),
                'timestamp': datetime.now(),
                'status': 'ok'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to read pressure sensor for {self.location_name}: {e}")
            return {
                'location_id': self.location_id,
                'location_name': self.location_name,
                'raw_value': 0.0,
                'value': 0.0,
                'pressure_percentage': 0.0,
                'force_newton': 0.0,
                'is_touching': False,
                'touch_duration': 0.0,
                'timestamp': datetime.now(),
                'status': 'error',
                'error': str(e)
            }
    
    async def _read_hardware(self) -> float:
        """
        Read raw value from hardware.
        
        Returns:
            Raw pressure reading
        """
        # TODO: Implement actual hardware reading
        # This is a placeholder that simulates pressure sensor readings
        
        import time
        
        # Simulate different pressure patterns based on location
        t = time.time()
        
        # Base pressure varies by location (some locations are more likely to have pressure)
        base_pressures = {
            0: 50,   # palm - moderate baseline
            1: 20,   # thumb_tip - low baseline
            2: 30,   # index_tip - low-moderate baseline
            3: 25,   # middle_tip - low baseline
            4: 15,   # ring_tip - very low baseline
            5: 10    # pinky_tip - very low baseline
        }
        
        base = base_pressures.get(self.location_id, 20)
        
        # Add time-based variation to simulate grip changes
        grip_variation = 100 * math.sin(t * 0.5 + self.location_id) if math.sin(t * 0.3) > 0.3 else 0
        
        # Add some noise
        noise = 10 * (hash(str(t + self.location_id)) % 100 - 50) / 50
        
        raw_value = max(0, base + grip_variation + noise)
        return raw_value
    
    def _apply_calibration(self, raw_value: float) -> float:
        """
        Apply calibration to raw sensor reading.
        
        Args:
            raw_value: Raw sensor reading
            
        Returns:
            Calibrated pressure value
        """
        # Apply baseline correction
        corrected = (raw_value - self.baseline) * self.sensitivity
        
        # Clamp to valid range
        return max(0.0, min(self.max_pressure, corrected))
    
    def _pressure_to_force(self, pressure: float) -> float:
        """
        Convert pressure reading to estimated force in Newtons.
        
        Args:
            pressure: Calibrated pressure value
            
        Returns:
            Estimated force in Newtons
        """
        # This conversion depends on the specific sensor and contact area
        # For FSRs, the relationship is typically non-linear
        
        # Simple linear approximation (replace with sensor-specific calibration)
        force_per_unit = 0.01  # Example: 0.01 N per pressure unit
        return pressure * force_per_unit
    
    def _update_touch_state(self, pressure: float):
        """
        Update touch detection state.
        
        Args:
            pressure: Current pressure reading
        """
        current_time = datetime.now()
        
        if pressure >= self.touch_threshold:
            if not self.is_touching:
                # Touch started
                self.is_touching = True
                self.touch_start_time = current_time
                self.logger.debug(f"Touch detected on {self.location_name}")
        else:
            if self.is_touching:
                # Touch ended
                touch_duration = self._get_touch_duration()
                self.is_touching = False
                self.touch_start_time = None
                self.logger.debug(f"Touch ended on {self.location_name} (duration: {touch_duration:.2f}s)")
    
    def _get_touch_duration(self) -> float:
        """
        Get current touch duration in seconds.
        
        Returns:
            Touch duration in seconds, or 0 if not currently touching
        """
        if not self.is_touching or not self.touch_start_time:
            return 0.0
        
        return (datetime.now() - self.touch_start_time).total_seconds()
    
    async def calibrate(self, samples: int = 100) -> bool:
        """
        Calibrate the pressure sensor.
        
        Args:
            samples: Number of calibration samples to collect
            
        Returns:
            True if calibration successful
        """
        try:
            self.logger.info(f"Calibrating pressure sensor for {self.location_name}...")
            self.logger.info("Please ensure no pressure is applied during calibration")
            
            # Collect baseline readings (no pressure applied)
            baseline_readings = []
            for i in range(samples):
                reading = await self._read_hardware()
                baseline_readings.append(reading)
                
                if i % 20 == 0:
                    progress = (i / samples) * 100
                    self.logger.debug(f"Baseline calibration progress: {progress:.0f}%")
                
                await asyncio.sleep(0.05)  # 20 Hz sampling
            
            # Calculate baseline
            self.baseline = sum(baseline_readings) / len(baseline_readings)
            baseline_std = (sum((x - self.baseline)**2 for x in baseline_readings) / len(baseline_readings))**0.5
            
            # Set touch threshold based on baseline noise
            self.touch_threshold = self.baseline + 3 * baseline_std  # 3-sigma threshold
            
            self.logger.info(f"Calibration complete for {self.location_name}:")
            self.logger.info(f"Baseline: {self.baseline:.2f}, Std: {baseline_std:.2f}")
            self.logger.info(f"Touch threshold: {self.touch_threshold:.2f}")
            
            # TODO: Implement maximum pressure calibration
            # This would involve prompting user to apply maximum expected pressure
            
            return True
            
        except Exception as e:
            self.logger.error(f"Calibration failed for pressure sensor {self.location_name}: {e}")
            return False
    
    def set_sensitivity(self, sensitivity: float):
        """
        Set sensor sensitivity multiplier.
        
        Args:
            sensitivity: Sensitivity multiplier (1.0 = default)
        """
        self.sensitivity = max(0.1, min(10.0, sensitivity))  # Reasonable range
        self.logger.info(f"Sensitivity set to {self.sensitivity:.2f} for {self.location_name}")
    
    def get_pressure_description(self, pressure: float) -> str:
        """
        Get human-readable description of pressure level.
        
        Args:
            pressure: Calibrated pressure value
            
        Returns:
            Description string
        """
        percentage = (pressure / self.max_pressure) * 100
        
        if percentage < 5:
            return "no contact"
        elif percentage < 20:
            return "light touch"
        elif percentage < 50:
            return "moderate pressure"
        elif percentage < 80:
            return "firm grip"
        else:
            return "strong grip"
    
    async def stop(self):
        """Stop the pressure sensor."""
        self.is_initialized = False
        self.is_touching = False
        self.touch_start_time = None
        # TODO: Clean up hardware resources
        self.logger.debug(f"Pressure sensor for {self.location_name} stopped")

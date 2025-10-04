"""Sensor data management and processing."""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import numpy as np

from ..core.logger import LoggerMixin
from .flex_sensor import FlexSensor
from .imu_sensor import IMUSensor
from .pressure_sensor import PressureSensor


class SensorManager(LoggerMixin):
    """Manages all sensor inputs and data processing."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize sensor manager.
        
        Args:
            config: Sensor configuration dictionary
        """
        self.config = config
        self.is_active = False
        
        # Initialize sensors
        self.flex_sensors = []
        self.imu_sensor = None
        self.pressure_sensors = []
        
        # Data storage
        self.latest_data = {}
        self.data_history = []
        self.max_history_size = 1000
        
        # Calibration data
        self.is_calibrated = False
        self.calibration_data = {}
        
        self.logger.info("Sensor manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize all sensors.
        
        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing sensors...")
            
            # Initialize flex sensors (one for each finger)
            for i in range(5):  # 5 fingers
                sensor = FlexSensor(finger_id=i, config=self.config)
                if await sensor.initialize():
                    self.flex_sensors.append(sensor)
                else:
                    self.logger.warning(f"Failed to initialize flex sensor {i}")
            
            # Initialize IMU sensor
            self.imu_sensor = IMUSensor(config=self.config)
            if not await self.imu_sensor.initialize():
                self.logger.warning("Failed to initialize IMU sensor")
            
            # Initialize pressure sensors
            for i in range(5):  # Palm and fingertips
                sensor = PressureSensor(location_id=i, config=self.config)
                if await sensor.initialize():
                    self.pressure_sensors.append(sensor)
                else:
                    self.logger.warning(f"Failed to initialize pressure sensor {i}")
            
            # Start data collection
            asyncio.create_task(self._data_collection_loop())
            
            self.is_active = True
            self.logger.info("Sensor initialization completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Sensor initialization failed: {e}")
            return False
    
    async def _data_collection_loop(self):
        """Main data collection loop."""
        sample_rate = self.config.get('sample_rate', 100)
        interval = 1.0 / sample_rate
        
        while self.is_active:
            try:
                await self._collect_sensor_data()
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(f"Error in data collection: {e}")
                await asyncio.sleep(0.1)
    
    async def _collect_sensor_data(self):
        """Collect data from all sensors."""
        timestamp = datetime.now()
        data = {
            'timestamp': timestamp,
            'flex_sensors': [],
            'imu': {},
            'pressure_sensors': [],
            'processed': {}
        }
        
        # Collect flex sensor data
        for sensor in self.flex_sensors:
            flex_data = await sensor.read()
            data['flex_sensors'].append(flex_data)
        
        # Collect IMU data
        if self.imu_sensor:
            data['imu'] = await self.imu_sensor.read()
        
        # Collect pressure sensor data
        for sensor in self.pressure_sensors:
            pressure_data = await sensor.read()
            data['pressure_sensors'].append(pressure_data)
        
        # Process the raw data
        data['processed'] = self._process_sensor_data(data)
        
        # Update latest data
        self.latest_data = data
        
        # Add to history
        self.data_history.append(data)
        if len(self.data_history) > self.max_history_size:
            self.data_history.pop(0)
    
    def _process_sensor_data(self, raw_data: Dict) -> Dict:
        """
        Process raw sensor data into meaningful information.
        
        Args:
            raw_data: Raw sensor readings
            
        Returns:
            Processed data dictionary
        """
        processed = {}
        
        # Process flex sensor data for gesture recognition
        flex_values = [sensor_data.get('value', 0) for sensor_data in raw_data['flex_sensors']]
        processed['finger_positions'] = flex_values
        processed['hand_closure'] = np.mean(flex_values) if flex_values else 0
        
        # Detect basic gestures
        processed['gestures'] = self._detect_gestures(flex_values)
        
        # Process IMU data for movement detection
        if raw_data['imu']:
            imu_data = raw_data['imu']
            processed['acceleration'] = imu_data.get('acceleration', [0, 0, 0])
            processed['rotation'] = imu_data.get('rotation', [0, 0, 0])
            processed['movement_magnitude'] = np.linalg.norm(processed['acceleration'])
            processed['unusual_movement'] = self._detect_unusual_movement(processed['acceleration'])
        
        # Process pressure data
        pressure_values = [sensor_data.get('value', 0) for sensor_data in raw_data['pressure_sensors']]
        processed['pressure_points'] = pressure_values
        processed['grip_strength'] = np.mean(pressure_values) if pressure_values else 0
        
        # Detect emergency signals
        processed['emergency_gesture'] = self._detect_emergency_gesture(processed)
        
        return processed
    
    def _detect_gestures(self, flex_values: List[float]) -> List[str]:
        """
        Detect basic hand gestures from flex sensor data.
        
        Args:
            flex_values: List of flex sensor values
            
        Returns:
            List of detected gestures
        """
        gestures = []
        
        if not flex_values or len(flex_values) < 5:
            return gestures
        
        # Threshold for "closed" finger (adjust based on calibration)
        closed_threshold = 0.7
        open_threshold = 0.3
        
        closed_fingers = sum(1 for value in flex_values if value > closed_threshold)
        open_fingers = sum(1 for value in flex_values if value < open_threshold)
        
        # Detect basic gestures
        if closed_fingers == 5:
            gestures.append("fist")
        elif open_fingers == 5:
            gestures.append("open_hand")
        elif closed_fingers == 4 and flex_values[1] < open_threshold:  # Index finger extended
            gestures.append("pointing")
        elif closed_fingers == 3 and flex_values[1] < open_threshold and flex_values[4] < open_threshold:
            gestures.append("peace_sign")
        
        return gestures
    
    def _detect_unusual_movement(self, acceleration: List[float]) -> bool:
        """
        Detect unusual or violent movements.
        
        Args:
            acceleration: 3D acceleration vector
            
        Returns:
            True if unusual movement detected
        """
        if not acceleration or len(acceleration) != 3:
            return False
        
        # Calculate movement magnitude
        magnitude = np.linalg.norm(acceleration)
        
        # Threshold for unusual movement (adjust based on testing)
        unusual_threshold = 15.0  # m/s^2
        
        return magnitude > unusual_threshold
    
    def _detect_emergency_gesture(self, processed_data: Dict) -> bool:
        """
        Detect emergency gestures or panic signals.
        
        Args:
            processed_data: Processed sensor data
            
        Returns:
            True if emergency gesture detected
        """
        gestures = processed_data.get('gestures', [])
        
        # Emergency gestures: rapid fist clenching, specific gesture sequences, etc.
        if 'fist' in gestures and processed_data.get('movement_magnitude', 0) > 10:
            return True
        
        # Add more sophisticated emergency detection logic here
        
        return False
    
    async def calibrate(self) -> bool:
        """
        Perform sensor calibration.
        
        Returns:
            True if calibration successful
        """
        try:
            self.logger.info("Starting sensor calibration...")
            
            # Collect baseline readings for each sensor type
            calibration_samples = 50
            flex_readings = []
            pressure_readings = []
            imu_readings = []
            
            for _ in range(calibration_samples):
                # Collect flex sensor baseline
                for sensor in self.flex_sensors:
                    reading = await sensor.read()
                    flex_readings.append(reading.get('value', 0))
                
                # Collect pressure sensor baseline
                for sensor in self.pressure_sensors:
                    reading = await sensor.read()
                    pressure_readings.append(reading.get('value', 0))
                
                # Collect IMU baseline
                if self.imu_sensor:
                    reading = await self.imu_sensor.read()
                    imu_readings.append(reading)
                
                await asyncio.sleep(0.1)
            
            # Calculate calibration parameters
            self.calibration_data = {
                'flex_baseline': np.mean(flex_readings) if flex_readings else 0,
                'flex_std': np.std(flex_readings) if flex_readings else 1,
                'pressure_baseline': np.mean(pressure_readings) if pressure_readings else 0,
                'pressure_std': np.std(pressure_readings) if pressure_readings else 1,
                'timestamp': datetime.now()
            }
            
            self.is_calibrated = True
            self.logger.info("Sensor calibration completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Sensor calibration failed: {e}")
            return False
    
    async def get_latest_data(self) -> Dict[str, Any]:
        """
        Get the latest sensor data.
        
        Returns:
            Latest sensor data dictionary
        """
        return self.latest_data.copy() if self.latest_data else {}
    
    def is_active(self) -> bool:
        """Check if sensor manager is active."""
        return self.is_active
    
    async def stop(self):
        """Stop sensor data collection."""
        self.is_active = False
        
        # Stop all sensors
        for sensor in self.flex_sensors:
            await sensor.stop()
        
        if self.imu_sensor:
            await self.imu_sensor.stop()
        
        for sensor in self.pressure_sensors:
            await sensor.stop()
        
        self.logger.info("Sensor manager stopped")

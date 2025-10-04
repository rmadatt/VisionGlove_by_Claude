"""IMU sensor implementation for hand orientation and movement tracking."""

import asyncio
from typing import Dict, Any, List
from datetime import datetime
import math

from ..core.logger import LoggerMixin


class IMUSensor(LoggerMixin):
    """Inertial Measurement Unit sensor for tracking hand movement and orientation."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize IMU sensor.
        
        Args:
            config: Sensor configuration
        """
        self.config = config
        self.is_initialized = False
        
        # Calibration data
        self.accel_bias = [0.0, 0.0, 0.0]
        self.gyro_bias = [0.0, 0.0, 0.0]
        self.mag_bias = [0.0, 0.0, 0.0]
        
        # Current orientation estimate
        self.orientation = [0.0, 0.0, 0.0]  # Roll, Pitch, Yaw in degrees
        self.quaternion = [1.0, 0.0, 0.0, 0.0]  # w, x, y, z
        
        # Movement tracking
        self.velocity = [0.0, 0.0, 0.0]
        self.position = [0.0, 0.0, 0.0]
        self.last_update_time = None
        
        self.logger.debug("IMU sensor initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the IMU sensor hardware.
        
        Returns:
            True if initialization successful
        """
        try:
            # TODO: Initialize actual IMU hardware
            # This would typically involve:
            # - Setting up I2C/SPI communication
            # - Configuring sensor ranges and filters
            # - Performing initial calibration
            
            # Reset state
            self.last_update_time = datetime.now()
            
            self.is_initialized = True
            self.logger.info("IMU sensor initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize IMU sensor: {e}")
            return False
    
    async def read(self) -> Dict[str, Any]:
        """
        Read current IMU sensor values.
        
        Returns:
            Dictionary containing all IMU readings and computed values
        """
        try:
            if not self.is_initialized:
                raise RuntimeError("IMU sensor not initialized")
            
            current_time = datetime.now()
            
            # Read raw sensor data
            raw_accel = await self._read_accelerometer()
            raw_gyro = await self._read_gyroscope()
            raw_mag = await self._read_magnetometer()
            
            # Apply calibration
            accel = self._apply_bias_correction(raw_accel, self.accel_bias)
            gyro = self._apply_bias_correction(raw_gyro, self.gyro_bias)
            mag = self._apply_bias_correction(raw_mag, self.mag_bias)
            
            # Update orientation estimate
            if self.last_update_time:
                dt = (current_time - self.last_update_time).total_seconds()
                self._update_orientation(accel, gyro, mag, dt)
                self._update_position(accel, dt)
            
            self.last_update_time = current_time
            
            return {
                'timestamp': current_time,
                'raw_data': {
                    'accelerometer': raw_accel,
                    'gyroscope': raw_gyro,
                    'magnetometer': raw_mag
                },
                'calibrated_data': {
                    'acceleration': accel,
                    'angular_velocity': gyro,
                    'magnetic_field': mag
                },
                'orientation': {
                    'euler': self.orientation.copy(),  # [roll, pitch, yaw] in degrees
                    'quaternion': self.quaternion.copy()  # [w, x, y, z]
                },
                'motion': {
                    'velocity': self.velocity.copy(),
                    'position': self.position.copy(),
                    'acceleration_magnitude': self._vector_magnitude(accel),
                    'angular_velocity_magnitude': self._vector_magnitude(gyro)
                },
                'status': 'ok'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to read IMU sensor: {e}")
            return {
                'timestamp': datetime.now(),
                'status': 'error',
                'error': str(e)
            }
    
    async def _read_accelerometer(self) -> List[float]:
        """
        Read accelerometer data.
        
        Returns:
            [x, y, z] acceleration in m/s^2
        """
        # TODO: Read from actual hardware
        # Simulate accelerometer readings with gravity and some movement
        import time
        
        # Base gravity vector (assuming glove is roughly level)
        gravity = [0.0, 0.0, 9.81]
        
        # Add some simulated movement
        t = time.time()
        movement = [
            2.0 * math.sin(t * 2.0),      # X movement
            1.5 * math.cos(t * 1.5),      # Y movement
            0.5 * math.sin(t * 3.0)       # Z movement
        ]
        
        return [gravity[i] + movement[i] for i in range(3)]
    
    async def _read_gyroscope(self) -> List[float]:
        """
        Read gyroscope data.
        
        Returns:
            [x, y, z] angular velocity in rad/s
        """
        # TODO: Read from actual hardware
        # Simulate gyroscope readings
        import time
        
        t = time.time()
        return [
            0.1 * math.sin(t * 0.5),      # Roll rate
            0.2 * math.cos(t * 0.7),      # Pitch rate  
            0.05 * math.sin(t * 1.2)      # Yaw rate
        ]
    
    async def _read_magnetometer(self) -> List[float]:
        """
        Read magnetometer data.
        
        Returns:
            [x, y, z] magnetic field in µT
        """
        # TODO: Read from actual hardware
        # Simulate magnetometer readings (rough Earth's magnetic field)
        import time
        
        # Earth's magnetic field varies by location, roughly 25-65 µT
        earth_field = [20.0, 5.0, 40.0]  # Rough values for a temperate location
        
        # Add some noise and variation
        t = time.time()
        noise = [
            2.0 * math.sin(t * 0.3) + (hash(str(t)) % 100 - 50) / 100,
            1.5 * math.cos(t * 0.4) + (hash(str(t * 1.1)) % 100 - 50) / 100,
            1.0 * math.sin(t * 0.2) + (hash(str(t * 1.2)) % 100 - 50) / 100
        ]
        
        return [earth_field[i] + noise[i] for i in range(3)]
    
    def _apply_bias_correction(self, raw_data: List[float], bias: List[float]) -> List[float]:
        """Apply bias correction to raw sensor data."""
        return [raw_data[i] - bias[i] for i in range(len(raw_data))]
    
    def _update_orientation(self, accel: List[float], gyro: List[float], mag: List[float], dt: float):
        """
        Update orientation estimate using sensor fusion.
        
        Args:
            accel: Accelerometer data [x, y, z] in m/s^2
            gyro: Gyroscope data [x, y, z] in rad/s
            mag: Magnetometer data [x, y, z] in µT
            dt: Time step in seconds
        """
        # Simple complementary filter for orientation estimation
        # In a real implementation, you'd use a more sophisticated algorithm
        # like Madgwick filter or Extended Kalman Filter
        
        # Calculate angles from accelerometer (tilt only)
        accel_roll = math.atan2(accel[1], accel[2]) * 180 / math.pi
        accel_pitch = math.atan2(-accel[0], math.sqrt(accel[1]**2 + accel[2]**2)) * 180 / math.pi
        
        # Integrate gyroscope for rotation rates
        gyro_roll = self.orientation[0] + gyro[0] * dt * 180 / math.pi
        gyro_pitch = self.orientation[1] + gyro[1] * dt * 180 / math.pi
        gyro_yaw = self.orientation[2] + gyro[2] * dt * 180 / math.pi
        
        # Complementary filter (simple sensor fusion)
        alpha = 0.98  # Trust gyro more for short term, accel for long term
        
        self.orientation[0] = alpha * gyro_roll + (1 - alpha) * accel_roll  # Roll
        self.orientation[1] = alpha * gyro_pitch + (1 - alpha) * accel_pitch  # Pitch
        self.orientation[2] = gyro_yaw  # Yaw (only from gyro for now)
        
        # Keep angles in reasonable range
        for i in range(3):
            while self.orientation[i] > 180:
                self.orientation[i] -= 360
            while self.orientation[i] < -180:
                self.orientation[i] += 360
        
        # Update quaternion representation
        self._euler_to_quaternion()
    
    def _euler_to_quaternion(self):
        """Convert current Euler angles to quaternion."""
        roll = math.radians(self.orientation[0])
        pitch = math.radians(self.orientation[1])
        yaw = math.radians(self.orientation[2])
        
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        
        self.quaternion[0] = cr * cp * cy + sr * sp * sy  # w
        self.quaternion[1] = sr * cp * cy - cr * sp * sy  # x
        self.quaternion[2] = cr * sp * cy + sr * cp * sy  # y
        self.quaternion[3] = cr * cp * sy - sr * sp * cy  # z
    
    def _update_position(self, accel: List[float], dt: float):
        """
        Update position estimate using double integration.
        
        Args:
            accel: Accelerometer data [x, y, z] in m/s^2
            dt: Time step in seconds
        """
        # Remove gravity component (simple approximation)
        # In a real implementation, you'd use the orientation to properly remove gravity
        gravity_removed = [
            accel[0],
            accel[1],
            accel[2] - 9.81
        ]
        
        # Update velocity (integration of acceleration)
        for i in range(3):
            self.velocity[i] += gravity_removed[i] * dt
        
        # Update position (integration of velocity)
        for i in range(3):
            self.position[i] += self.velocity[i] * dt
        
        # Apply some damping to prevent drift (simple approach)
        damping = 0.99
        for i in range(3):
            self.velocity[i] *= damping
    
    def _vector_magnitude(self, vector: List[float]) -> float:
        """Calculate magnitude of a 3D vector."""
        return math.sqrt(sum(x**2 for x in vector))
    
    async def calibrate(self, duration: float = 10.0) -> bool:
        """
        Calibrate the IMU sensor.
        
        Args:
            duration: Calibration duration in seconds
            
        Returns:
            True if calibration successful
        """
        try:
            self.logger.info(f"Starting IMU calibration for {duration} seconds...")
            self.logger.info("Please keep the glove stationary during calibration")
            
            # Collect samples for bias estimation
            samples = int(duration * 100)  # 100 Hz sampling
            accel_samples = []
            gyro_samples = []
            mag_samples = []
            
            for i in range(samples):
                accel = await self._read_accelerometer()
                gyro = await self._read_gyroscope()
                mag = await self._read_magnetometer()
                
                accel_samples.append(accel)
                gyro_samples.append(gyro)
                mag_samples.append(mag)
                
                if i % 100 == 0:
                    progress = (i / samples) * 100
                    self.logger.info(f"Calibration progress: {progress:.0f}%")
                
                await asyncio.sleep(0.01)  # 100 Hz
            
            # Calculate bias values
            self.accel_bias = [
                sum(sample[i] for sample in accel_samples) / len(accel_samples)
                for i in range(3)
            ]
            
            self.gyro_bias = [
                sum(sample[i] for sample in gyro_samples) / len(gyro_samples)
                for i in range(3)
            ]
            
            self.mag_bias = [
                sum(sample[i] for sample in mag_samples) / len(mag_samples)
                for i in range(3)
            ]
            
            # Adjust accelerometer bias to account for gravity
            # Assume the glove was level during calibration
            self.accel_bias[2] -= 9.81  # Remove gravity from Z bias
            
            self.logger.info(f"IMU calibration complete:")
            self.logger.info(f"Accel bias: {[f'{x:.3f}' for x in self.accel_bias]}")
            self.logger.info(f"Gyro bias: {[f'{x:.3f}' for x in self.gyro_bias]}")
            self.logger.info(f"Mag bias: {[f'{x:.3f}' for x in self.mag_bias]}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"IMU calibration failed: {e}")
            return False
    
    def reset_position(self):
        """Reset position and velocity estimates."""
        self.position = [0.0, 0.0, 0.0]
        self.velocity = [0.0, 0.0, 0.0]
        self.logger.info("IMU position reset")
    
    async def stop(self):
        """Stop the IMU sensor."""
        self.is_initialized = False
        # TODO: Clean up hardware resources
        self.logger.debug("IMU sensor stopped")

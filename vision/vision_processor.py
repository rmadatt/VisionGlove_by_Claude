"""Main vision processing system for VisionGlove."""

import asyncio
import cv2
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from ..core.logger import LoggerMixin
from .person_detector import PersonDetector
from .gesture_recognizer import GestureRecognizer
from .threat_analyzer import ThreatAnalyzer


class VisionProcessor(LoggerMixin):
    """Main vision processing system coordinating all computer vision tasks."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize vision processor.
        
        Args:
            config: Vision configuration dictionary
        """
        self.config = config
        self.is_active = False
        
        # Camera configuration
        self.camera_index = config.get('camera_index', 0)
        self.resolution = config.get('resolution', [640, 480])
        self.fps = config.get('fps', 30)
        
        # Detection configuration
        self.detection_threshold = config.get('detection_threshold', 0.7)
        self.person_threshold = config.get('person_threshold', 3)
        
        # Video capture
        self.cap = None
        self.frame_count = 0
        self.last_frame_time = None
        
        # Vision components
        self.person_detector = PersonDetector(config)
        self.gesture_recognizer = GestureRecognizer(config)
        self.threat_analyzer = ThreatAnalyzer(config)
        
        # Current frame data
        self.current_frame = None
        self.latest_analysis = {}
        
        # Performance metrics
        self.processing_times = []
        self.max_processing_history = 100
        
        self.logger.info("Vision processor initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize vision processing system.
        
        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing vision system...")
            
            # Initialize camera
            if not await self._initialize_camera():
                return False
            
            # Initialize vision components
            if not await self.person_detector.initialize():
                self.logger.error("Failed to initialize person detector")
                return False
            
            if not await self.gesture_recognizer.initialize():
                self.logger.error("Failed to initialize gesture recognizer")
                return False
            
            if not await self.threat_analyzer.initialize():
                self.logger.error("Failed to initialize threat analyzer")
                return False
            
            # Start processing loop
            asyncio.create_task(self._processing_loop())
            
            self.is_active = True
            self.logger.info("Vision system initialization completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Vision system initialization failed: {e}")
            return False
    
    async def _initialize_camera(self) -> bool:
        """Initialize camera capture."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            
            if not self.cap.isOpened():
                raise RuntimeError(f"Cannot open camera {self.camera_index}")
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps:.1f} FPS")
            return True
            
        except Exception as e:
            self.logger.error(f"Camera initialization failed: {e}")
            return False
    
    async def _processing_loop(self):
        """Main vision processing loop."""
        self.logger.info("Vision processing loop started")
        
        target_interval = 1.0 / self.fps
        
        while self.is_active:
            try:
                start_time = time.time()
                
                # Process current frame
                await self._process_frame_cycle()
                
                # Calculate processing time
                processing_time = time.time() - start_time
                self.processing_times.append(processing_time)
                
                # Maintain processing time history
                if len(self.processing_times) > self.max_processing_history:
                    self.processing_times.pop(0)
                
                # Sleep to maintain target FPS
                sleep_time = max(0, target_interval - processing_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    self.logger.debug(f"Processing slower than target FPS: {processing_time:.3f}s")
                
            except Exception as e:
                self.logger.error(f"Error in vision processing loop: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_frame_cycle(self):
        """Process one frame cycle."""
        # Capture frame
        if not await self._capture_frame():
            return
        
        if self.current_frame is None:
            return
        
        # Process frame through all vision components
        frame_analysis = await self._analyze_frame(self.current_frame)
        
        # Update latest analysis
        self.latest_analysis = frame_analysis
        self.last_frame_time = datetime.now()
        self.frame_count += 1
    
    async def _capture_frame(self) -> bool:
        """
        Capture frame from camera.
        
        Returns:
            True if frame captured successfully
        """
        try:
            if not self.cap or not self.cap.isOpened():
                return False
            
            ret, frame = self.cap.read()
            if not ret:
                self.logger.warning("Failed to capture frame")
                return False
            
            self.current_frame = frame
            return True
            
        except Exception as e:
            self.logger.error(f"Frame capture error: {e}")
            return False
    
    async def _analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Analyze frame through all vision components.
        
        Args:
            frame: Input frame
            
        Returns:
            Analysis results dictionary
        """
        try:
            analysis = {
                'timestamp': datetime.now(),
                'frame_shape': frame.shape,
                'persons': [],
                'gestures': [],
                'threats': {},
                'summary': {}
            }
            
            # Person detection
            person_results = await self.person_detector.detect(frame)
            analysis['persons'] = person_results.get('detections', [])
            
            # Gesture recognition (on detected persons and hands)
            gesture_results = await self.gesture_recognizer.recognize(frame, analysis['persons'])
            analysis['gestures'] = gesture_results.get('gestures', [])
            
            # Threat analysis
            threat_results = await self.threat_analyzer.analyze(frame, analysis['persons'], analysis['gestures'])
            analysis['threats'] = threat_results
            
            # Generate summary
            analysis['summary'] = self._generate_summary(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Frame analysis error: {e}")
            return {
                'timestamp': datetime.now(),
                'error': str(e),
                'summary': {'error': True}
            }
    
    def _generate_summary(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate analysis summary.
        
        Args:
            analysis: Full analysis results
            
        Returns:
            Summary dictionary
        """
        summary = {
            'person_count': len(analysis.get('persons', [])),
            'gesture_count': len(analysis.get('gestures', [])),
            'threat_level': analysis.get('threats', {}).get('level', 0),
            'alerts': []
        }
        
        # Check person count threshold
        if summary['person_count'] >= self.person_threshold:
            summary['alerts'].append({
                'type': 'person_count',
                'message': f"Multiple people detected: {summary['person_count']}",
                'severity': 'warning'
            })
        
        # Check for threatening gestures or behaviors
        threats = analysis.get('threats', {})
        if threats.get('level', 0) > 1:
            summary['alerts'].append({
                'type': 'threat_detected',
                'message': threats.get('description', 'Potential threat detected'),
                'severity': 'alert' if threats.get('level', 0) < 3 else 'emergency'
            })
        
        # Performance metrics
        if self.processing_times:
            avg_processing_time = sum(self.processing_times) / len(self.processing_times)
            summary['performance'] = {
                'avg_processing_time': avg_processing_time,
                'current_fps': 1.0 / avg_processing_time if avg_processing_time > 0 else 0
            }
        
        return summary
    
    async def process_frame(self) -> Dict[str, Any]:
        """
        Get latest frame analysis.
        
        Returns:
            Latest analysis results
        """
        return self.latest_analysis.copy() if self.latest_analysis else {}
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get current camera frame.
        
        Returns:
            Current frame or None if not available
        """
        return self.current_frame.copy() if self.current_frame is not None else None
    
    async def save_frame(self, filename: str, frame: Optional[np.ndarray] = None) -> bool:
        """
        Save frame to file.
        
        Args:
            filename: Output filename
            frame: Frame to save (uses current frame if None)
            
        Returns:
            True if saved successfully
        """
        try:
            save_frame = frame if frame is not None else self.current_frame
            
            if save_frame is None:
                return False
            
            success = cv2.imwrite(filename, save_frame)
            if success:
                self.logger.info(f"Frame saved to {filename}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to save frame: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get vision system performance statistics.
        
        Returns:
            Performance statistics dictionary
        """
        stats = {
            'is_active': self.is_active,
            'frame_count': self.frame_count,
            'last_frame_time': self.last_frame_time
        }
        
        if self.processing_times:
            avg_time = sum(self.processing_times) / len(self.processing_times)
            min_time = min(self.processing_times)
            max_time = max(self.processing_times)
            
            stats.update({
                'avg_processing_time': avg_time,
                'min_processing_time': min_time,
                'max_processing_time': max_time,
                'current_fps': 1.0 / avg_time if avg_time > 0 else 0,
                'target_fps': self.fps
            })
        
        return stats
    
    def is_active(self) -> bool:
        """Check if vision processor is active."""
        return self.is_active
    
    async def stop(self):
        """Stop vision processing."""
        self.is_active = False
        
        # Release camera
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # Stop vision components
        await self.person_detector.stop()
        await self.gesture_recognizer.stop()
        await self.threat_analyzer.stop()
        
        self.logger.info("Vision processor stopped")

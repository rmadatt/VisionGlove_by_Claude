"""Emergency response dispatcher for VisionGlove."""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from ..core.logger import LoggerMixin
from .sms_service import SMSService
from .livestream_service import LivestreamService


class EmergencyDispatcher(LoggerMixin):
    """Coordinates emergency response actions including alerts and livestreaming."""
    
    def __init__(self, comm_config: Dict[str, Any], stream_config: Dict[str, Any]):
        """
        Initialize emergency dispatcher.
        
        Args:
            comm_config: Communications configuration
            stream_config: Livestream configuration
        """
        self.comm_config = comm_config
        self.stream_config = stream_config
        self.is_active = False
        
        # Services
        self.sms_service = SMSService(comm_config)
        self.livestream_service = LivestreamService(stream_config)
        
        # Emergency state
        self.current_emergency = None
        self.emergency_history = []
        self.max_history_size = 100
        
        # Response configuration
        self.auto_response_enabled = True
        self.emergency_contacts = comm_config.get('emergency_contact', '').split(',')
        self.police_number = comm_config.get('police_number', '')
        
        self.logger.info("Emergency dispatcher initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize emergency dispatcher services.
        
        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing emergency dispatcher...")
            
            # Initialize SMS service
            if not await self.sms_service.initialize():
                self.logger.warning("SMS service initialization failed")
            
            # Initialize livestream service
            if not await self.livestream_service.initialize():
                self.logger.warning("Livestream service initialization failed")
            
            self.is_active = True
            self.logger.info("Emergency dispatcher initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Emergency dispatcher initialization failed: {e}")
            return False
    
    async def dispatch_emergency(self, emergency_data: Dict[str, Any]) -> bool:
        """
        Dispatch emergency response based on threat level.
        
        Args:
            emergency_data: Emergency information dictionary
            
        Returns:
            True if emergency response initiated successfully
        """
        try:
            threat_level = emergency_data.get('threat_level', 0)
            timestamp = emergency_data.get('timestamp', datetime.now())
            location = emergency_data.get('location', 'Unknown location')
            
            self.logger.warning(f"Emergency dispatch triggered - Threat level: {threat_level}")
            
            # Create emergency record
            emergency = {
                'id': self._generate_emergency_id(timestamp),
                'timestamp': timestamp,
                'threat_level': threat_level,
                'location': location,
                'data': emergency_data,
                'actions_taken': [],
                'status': 'active'
            }
            
            self.current_emergency = emergency
            
            # Execute response actions based on threat level
            if threat_level >= 1:  # Caution level
                await self._handle_caution_level(emergency)
            
            if threat_level >= 2:  # Alert level
                await self._handle_alert_level(emergency)
            
            if threat_level >= 3:  # Emergency level
                await self._handle_emergency_level(emergency)
            
            # Add to history
            self.emergency_history.append(emergency)
            if len(self.emergency_history) > self.max_history_size:
                self.emergency_history.pop(0)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Emergency dispatch failed: {e}")
            return False
    
    async def _handle_caution_level(self, emergency: Dict[str, Any]):
        """Handle caution level response."""
        self.logger.info("Executing caution level response")
        
        # Log the event
        emergency['actions_taken'].append({
            'action': 'logged_event',
            'timestamp': datetime.now(),
            'details': 'Caution level event logged'
        })
        
        # Prepare systems but don't send alerts yet
        await self._prepare_emergency_systems()
    
    async def _handle_alert_level(self, emergency: Dict[str, Any]):
        """Handle alert level response."""
        self.logger.warning("Executing alert level response")
        
        # Send alerts to emergency contacts (but not police yet)
        if self.emergency_contacts and self.auto_response_enabled:
            message = self._create_alert_message(emergency, is_police=False)
            
            for contact in self.emergency_contacts:
                contact = contact.strip()
                if contact:
                    success = await self.sms_service.send_sms(contact, message)
                    emergency['actions_taken'].append({
                        'action': 'sms_sent',
                        'timestamp': datetime.now(),
                        'recipient': contact,
                        'success': success
                    })
        
        # Start livestream but don't alert authorities yet
        if self.stream_config.get('enabled', True):
            stream_success = await self.livestream_service.start_emergency_stream(emergency)
            emergency['actions_taken'].append({
                'action': 'livestream_started',
                'timestamp': datetime.now(),
                'success': stream_success
            })
    
    async def _handle_emergency_level(self, emergency: Dict[str, Any]):
        """Handle emergency level response."""
        self.logger.error("Executing emergency level response")
        
        # Send immediate alert to police
        if self.police_number and self.auto_response_enabled:
            police_message = self._create_alert_message(emergency, is_police=True)
            
            success = await self.sms_service.send_sms(self.police_number, police_message)
            emergency['actions_taken'].append({
                'action': 'police_alert_sent',
                'timestamp': datetime.now(),
                'recipient': self.police_number,
                'success': success
            })
            
            if success:
                self.logger.info("Police alert sent successfully")
            else:
                self.logger.error("Failed to send police alert")
        
        # Ensure livestream is running
        if not await self.livestream_service.is_streaming():
            stream_success = await self.livestream_service.start_emergency_stream(emergency)
            emergency['actions_taken'].append({
                'action': 'emergency_livestream_started',
                'timestamp': datetime.now(),
                'success': stream_success
            })
    
    async def _prepare_emergency_systems(self):
        """Prepare emergency systems for potential activation."""
        try:
            # Pre-initialize services for faster response
            await self.sms_service.test_connection()
            await self.livestream_service.prepare_stream()
            
            self.logger.debug("Emergency systems prepared")
            
        except Exception as e:
            self.logger.error(f"Failed to prepare emergency systems: {e}")
    
    def _create_alert_message(self, emergency: Dict[str, Any], is_police: bool = False) -> str:
        """
        Create appropriate alert message.
        
        Args:
            emergency: Emergency data
            is_police: Whether message is for police
            
        Returns:
            Formatted alert message
        """
        threat_level = emergency.get('threat_level', 0)
        location = emergency.get('location', 'Unknown location')
        timestamp = emergency.get('timestamp', datetime.now())
        
        if is_police:
            message = f"EMERGENCY ALERT - VisionGlove Security System\n"
            message += f"Threat Level: {threat_level}\n"
            message += f"Location: {location}\n"
            message += f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"Incident ID: {emergency.get('id', 'Unknown')}\n"
            message += f"Immediate response required."
        else:
            message = f"VisionGlove Alert\n"
            message += f"Alert Level: {threat_level}\n"
            message += f"Location: {location}\n"
            message += f"Time: {timestamp.strftime('%H:%M:%S')}\n"
            
            if threat_level >= 3:
                message += f"EMERGENCY - Authorities have been contacted."
            else:
                message += f"Monitoring situation."
        
        return message
    
    def _generate_emergency_id(self, timestamp: datetime) -> str:
        """Generate unique emergency ID."""
        return f"VG_{timestamp.strftime('%Y%m%d_%H%M%S')}_{hash(str(timestamp.microsecond)) % 1000:03d}"
    
    async def resolve_emergency(self, emergency_id: str, resolution_notes: str = "") -> bool:
        """
        Mark emergency as resolved.
        
        Args:
            emergency_id: Emergency ID to resolve
            resolution_notes: Optional resolution notes
            
        Returns:
            True if emergency resolved successfully
        """
        try:
            if self.current_emergency and self.current_emergency.get('id') == emergency_id:
                self.current_emergency['status'] = 'resolved'
                self.current_emergency['resolution_time'] = datetime.now()
                self.current_emergency['resolution_notes'] = resolution_notes
                
                # Stop livestream
                await self.livestream_service.stop_stream()
                
                self.logger.info(f"Emergency {emergency_id} resolved")
                self.current_emergency = None
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to resolve emergency {emergency_id}: {e}")
            return False
    
    async def test_emergency_systems(self) -> Dict[str, bool]:
        """
        Test all emergency systems.
        
        Returns:
            Dictionary of system test results
        """
        results = {}
        
        try:
            # Test SMS service
            results['sms'] = await self.sms_service.test_connection()
            
            # Test livestream service
            results['livestream'] = await self.livestream_service.test_connection()
            
            self.logger.info(f"Emergency systems test completed: {results}")
            
        except Exception as e:
            self.logger.error(f"Emergency systems test failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def get_current_emergency(self) -> Dict[str, Any]:
        """Get current active emergency."""
        return self.current_emergency.copy() if self.current_emergency else {}
    
    def get_emergency_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent emergency history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of emergency records
        """
        return self.emergency_history[-limit:] if self.emergency_history else []
    
    def set_auto_response(self, enabled: bool):
        """
        Enable or disable automatic emergency response.
        
        Args:
            enabled: Whether to enable auto response
        """
        self.auto_response_enabled = enabled
        self.logger.info(f"Auto response {'enabled' if enabled else 'disabled'}")
    
    def is_active(self) -> bool:
        """Check if emergency dispatcher is active."""
        return self.is_active
    
    async def stop(self):
        """Stop emergency dispatcher."""
        self.is_active = False
        
        # Stop services
        await self.sms_service.stop()
        await self.livestream_service.stop()
        
        self.logger.info("Emergency dispatcher stopped")

#!/usr/bin/env python3
"""
VisionGlove Main Application

A modern, production-ready implementation of the VisionGlove cybernetic glove system.
This script provides the main entry point for running the complete VisionGlove system.
"""

import asyncio
import argparse
import signal
import sys
from pathlib import Path
import logging

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vision_glove.core.glove_system import VisionGloveSystem
from vision_glove.core.logger import setup_logger
from vision_glove.core.config_manager import ConfigManager


class VisionGloveApp:
    """Main VisionGlove application class."""
    
    def __init__(self, config_path: str = None, debug: bool = False):
        """
        Initialize VisionGlove application.
        
        Args:
            config_path: Optional path to configuration file
            debug: Enable debug mode
        """
        self.config_path = config_path
        self.debug = debug
        self.system = None
        self.running = False
        
        # Set up logging
        log_level = "DEBUG" if debug else "INFO"
        self.logger = setup_logger("VisionGloveApp", log_level)
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def start(self) -> bool:
        """
        Start the VisionGlove system.
        
        Returns:
            True if started successfully
        """
        try:
            self.logger.info("Starting VisionGlove system...")
            
            # Initialize system
            self.system = VisionGloveSystem(self.config_path)
            
            if not await self.system.start():
                self.logger.error("Failed to start VisionGlove system")
                return False
            
            self.running = True
            self.logger.info("VisionGlove system started successfully")
            
            # Main run loop
            await self._run_loop()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start VisionGlove system: {e}")
            return False
        finally:
            await self._cleanup()
    
    async def _run_loop(self):
        """Main application run loop."""
        self.logger.info("VisionGlove application running...")
        self.logger.info("Press Ctrl+C to stop")
        
        try:
            while self.running:
                # Monitor system status
                status = self.system.get_status()
                
                if self.debug:
                    self.logger.debug(f"System status: {status}")
                
                # Check for any critical issues
                if not status.get('running', False):
                    self.logger.error("System stopped running unexpectedly")
                    break
                
                # Sleep for status check interval
                await asyncio.sleep(5.0)
                
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            self.running = False
    
    async def _cleanup(self):
        """Clean up resources."""
        if self.system:
            self.logger.info("Stopping VisionGlove system...")
            await self.system.stop()
        
        self.logger.info("VisionGlove application shutdown complete")
    
    async def test_systems(self) -> bool:
        """
        Test all systems without starting main loop.
        
        Returns:
            True if all systems test successfully
        """
        try:
            self.logger.info("Testing VisionGlove systems...")
            
            # Initialize system
            self.system = VisionGloveSystem(self.config_path)
            
            if not await self.system.initialize():
                self.logger.error("System initialization failed")
                return False
            
            # Run system tests
            self.logger.info("Running system tests...")
            
            # Test configuration
            config_valid = self.system.config.validate()
            self.logger.info(f"Configuration test: {'PASS' if config_valid else 'FAIL'}")
            
            # Test subsystems
            status = self.system.get_status()
            subsystems = status.get('subsystems', {})
            
            all_tests_passed = True
            for subsystem, active in subsystems.items():
                test_result = "PASS" if active else "FAIL"
                self.logger.info(f"{subsystem.capitalize()} test: {test_result}")
                if not active:
                    all_tests_passed = False
            
            # Test emergency systems if available
            if hasattr(self.system, 'emergency_dispatcher') and self.system.emergency_dispatcher:
                emergency_tests = await self.system.emergency_dispatcher.test_emergency_systems()
                for system, result in emergency_tests.items():
                    test_result = "PASS" if result else "FAIL"
                    self.logger.info(f"Emergency {system} test: {test_result}")
                    if not result:
                        all_tests_passed = False
            
            self.logger.info(f"System tests {'PASSED' if all_tests_passed else 'FAILED'}")
            return all_tests_passed
            
        except Exception as e:
            self.logger.error(f"System test failed: {e}")
            return False
        finally:
            if self.system:
                await self.system.stop()


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="VisionGlove - Cybernetic Glove Safety System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main_app.py                    # Run with default configuration
    python main_app.py --debug            # Run with debug logging
    python main_app.py --config custom.json  # Use custom configuration
    python main_app.py --test             # Test systems only
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        help="Path to configuration file",
        type=str,
        default=None
    )
    
    parser.add_argument(
        "--debug", "-d",
        help="Enable debug mode",
        action="store_true"
    )
    
    parser.add_argument(
        "--test", "-t",
        help="Test systems and exit",
        action="store_true"
    )
    
    parser.add_argument(
        "--version", "-v",
        help="Show version information",
        action="store_true"
    )
    
    return parser


async def main():
    """Main application entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.version:
        print("VisionGlove v1.0.0")
        print("Cybernetic Glove Safety System")
        return 0
    
    # Create application
    app = VisionGloveApp(
        config_path=args.config,
        debug=args.debug
    )
    
    try:
        if args.test:
            # Run system tests
            success = await app.test_systems()
            return 0 if success else 1
        else:
            # Run full application
            success = await app.start()
            return 0 if success else 1
            
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return 0
    except Exception as e:
        print(f"Application error: {e}")
        return 1


if __name__ == "__main__":
    # Run the application
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

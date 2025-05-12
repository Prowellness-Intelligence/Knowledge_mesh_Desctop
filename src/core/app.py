"""
Main application entry point for the Knowledge Mesh Desktop application.

This module initializes the application, sets up the core services, and
manages the application lifecycle.
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..services.file_monitor import FileMonitorService
from ..services.document_processor import DocumentProcessorService
from ..services.vector_store import VectorStoreService
from ..services.knowledge_mesh import KnowledgeMeshService
from ..services.proactive_service import ProactiveService
from ..services.calendar_service import CalendarService
from ..services.email_service import EmailService
from ..services.voice_service import VoiceService
from ..ui.main_window import MainWindow
from .config import Config
from .events import EventType, publish, subscribe, event_bus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser("~/knowledge_mesh_desktop/logs/app.log")),
    ],
)

logger = logging.getLogger(__name__)


class Application:
    """
    Main application class for the Knowledge Mesh Desktop application.
    
    This class manages the application lifecycle, initializes services,
    and coordinates communication between components.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the application.
        
        Args:
            config_dir: Optional directory containing configuration files.
                        Defaults to the config directory in the project root.
        """
        self.config = Config(config_dir)
        
        self.services = {}
        self.ui = None
        
        self._setup_signal_handlers()
        
        self.loop = asyncio.get_event_loop()
        
        self.shutdown_requested = False
        
        self.data_dir = Path(self.config.get("app.data_dir"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logs_dir = self.data_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Application initialized")
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown())
            )
    
    async def initialize_services(self):
        """Initialize all services."""
        logger.info("Initializing services")
        
        self.services["vector_store"] = VectorStoreService(self.config)
        await self.services["vector_store"].initialize()
        
        self.services["document_processor"] = DocumentProcessorService(self.config)
        await self.services["document_processor"].initialize()
        
        self.services["file_monitor"] = FileMonitorService(self.config)
        await self.services["file_monitor"].initialize()
        
        self.services["knowledge_mesh"] = KnowledgeMeshService(self.config)
        await self.services["knowledge_mesh"].initialize()
        
        self.services["proactive"] = ProactiveService(self.config)
        await self.services["proactive"].initialize()
        
        if self.config.get("calendar.enabled", False):
            self.services["calendar"] = CalendarService(self.config)
            await self.services["calendar"].initialize()
        
        if self.config.get("email.enabled", False):
            self.services["email"] = EmailService(self.config)
            await self.services["email"].initialize()
        
        if self.config.get("voice.enabled", False):
            self.services["voice"] = VoiceService(self.config)
            await self.services["voice"].initialize()
        
        logger.info("All services initialized")
    
    async def start_services(self):
        """Start all services."""
        logger.info("Starting services")
        
        for service_name in [
            "vector_store",
            "document_processor",
            "file_monitor",
            "knowledge_mesh",
            "proactive",
            "calendar",
            "email",
            "voice",
        ]:
            if service_name in self.services:
                logger.info(f"Starting {service_name} service")
                await self.services[service_name].start()
        
        logger.info("All services started")
    
    async def initialize_ui(self):
        """Initialize the user interface."""
        logger.info("Initializing UI")
        
        self.ui = MainWindow(self.config, self.services)
        await self.ui.initialize()
        
        logger.info("UI initialized")
    
    async def start_ui(self):
        """Start the user interface."""
        if self.ui:
            logger.info("Starting UI")
            await self.ui.start()
    
    async def run(self):
        """Run the application."""
        logger.info("Starting application")
        
        try:
            await self.initialize_services()
            
            await self.start_services()
            
            await self.initialize_ui()
            
            await self.start_ui()
            
            publish(EventType.APP_STARTED)
            
            while not self.shutdown_requested:
                await asyncio.sleep(0.1)
            
            logger.info("Shutdown requested, stopping application")
            
            publish(EventType.APP_STOPPING)
            
            if self.ui:
                await self.ui.stop()
            
            for service_name in [
                "voice",
                "email",
                "calendar",
                "proactive",
                "knowledge_mesh",
                "file_monitor",
                "document_processor",
                "vector_store",
            ]:
                if service_name in self.services:
                    logger.info(f"Stopping {service_name} service")
                    await self.services[service_name].stop()
            
            logger.info("Application stopped")
            
        except Exception as e:
            logger.error(f"Error running application: {e}", exc_info=True)
            raise
    
    async def shutdown(self):
        """Request application shutdown."""
        if not self.shutdown_requested:
            logger.info("Shutdown requested")
            self.shutdown_requested = True


def main():
    """Main entry point for the application."""
    app = Application()
    
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Error running application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
File monitoring service for the Knowledge Mesh Desktop application.

This module provides a service that monitors the file system for changes
(new files, modified files, deleted files) and publishes events that other
services can subscribe to.
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent,
    FileMovedEvent,
    DirCreatedEvent,
    DirDeletedEvent,
)

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus

logger = logging.getLogger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """
    Event handler for file system events.
    
    This class handles file system events from the watchdog observer and
    publishes corresponding events to the event bus.
    """
    
    def __init__(self, service: "FileMonitorService"):
        """
        Initialize the event handler.
        
        Args:
            service: The file monitor service that owns this handler
        """
        self.service = service
        self.ignore_patterns = service.ignore_patterns
        self.monitored_extensions = service.monitored_extensions
    
    def _should_ignore(self, path: Union[str, bytes]) -> bool:
        """
        Check if a path should be ignored.
        
        Args:
            path: The path to check (can be str or bytes)
            
        Returns:
            True if the path should be ignored, False otherwise
        """
        if isinstance(path, bytes):
            path = path.decode('utf-8')
            
        for pattern in self.ignore_patterns:
            if pattern in path:
                return True
        
        if os.path.isfile(path):
            _, ext = os.path.splitext(path)
            if self.monitored_extensions and ext.lower() not in self.monitored_extensions:
                return True
        
        return False
    
    def on_created(self, event: FileSystemEvent):
        """
        Handle file/directory creation events.
        
        Args:
            event: The file system event
        """
        if self._should_ignore(event.src_path):
            return
        
        if isinstance(event, FileCreatedEvent):
            logger.debug(f"File created: {event.src_path}")
            publish(EventType.FILE_CREATED, {"path": event.src_path})
        elif isinstance(event, DirCreatedEvent):
            logger.debug(f"Directory created: {event.src_path}")
            publish(EventType.DIRECTORY_CREATED, {"path": event.src_path})
    
    def on_modified(self, event: FileSystemEvent):
        """
        Handle file modification events.
        
        Args:
            event: The file system event
        """
        if self._should_ignore(event.src_path):
            return
        
        if isinstance(event, FileModifiedEvent):
            logger.debug(f"File modified: {event.src_path}")
            publish(EventType.FILE_MODIFIED, {"path": event.src_path})
    
    def on_deleted(self, event: FileSystemEvent):
        """
        Handle file/directory deletion events.
        
        Args:
            event: The file system event
        """
        if self._should_ignore(event.src_path):
            return
        
        if isinstance(event, FileDeletedEvent):
            logger.debug(f"File deleted: {event.src_path}")
            publish(EventType.FILE_DELETED, {"path": event.src_path})
        elif isinstance(event, DirDeletedEvent):
            logger.debug(f"Directory deleted: {event.src_path}")
            publish(EventType.DIRECTORY_DELETED, {"path": event.src_path})
    
    def on_moved(self, event: FileSystemEvent):
        """
        Handle file/directory move events.
        
        Args:
            event: The file system event
        """
        if self._should_ignore(event.src_path) or self._should_ignore(event.dest_path):
            return
        
        if isinstance(event, FileMovedEvent):
            logger.debug(f"File moved: {event.src_path} -> {event.dest_path}")
            publish(EventType.FILE_MOVED, {"src_path": event.src_path, "dest_path": event.dest_path})


class FileMonitorService:
    """
    Service for monitoring file system changes.
    
    This service monitors specified directories for file system changes
    (new files, modified files, deleted files) and publishes events that
    other services can subscribe to.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the file monitor service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.observer = None
        self.event_handler = FileEventHandler(self)
        self.monitored_directories = []
        self.monitored_extensions = []
        self.ignore_patterns = []
        self.scan_interval = 60  # Default scan interval in seconds
        self.is_running = False
        self.scan_task = None
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.monitored_directories = [
            os.path.expanduser(d)
            for d in self.config.get("file_monitor.directories", ["~/Documents"])
        ]
        
        extensions = self.config.get(
            "file_monitor.extensions",
            [".pdf", ".docx", ".doc", ".txt", ".md", ".pptx", ".xlsx", ".csv"]
        )
        self.monitored_extensions = [ext.lower() for ext in extensions]
        
        self.ignore_patterns = self.config.get(
            "file_monitor.ignore_patterns",
            ["~$", ".", ".tmp", ".temp", ".git", "__pycache__", ".DS_Store"]
        )
        
        self.scan_interval = self.config.get("file_monitor.scan_interval_seconds", 60)
    
    async def initialize(self):
        """Initialize the file monitor service."""
        logger.info("Initializing file monitor service")
        
        self.observer = Observer()
        
        for directory in self.monitored_directories:
            path = Path(directory)
            if path.exists() and path.is_dir():
                logger.info(f"Scheduling directory for monitoring: {directory}")
                self.observer.schedule(self.event_handler, directory, recursive=True)
            else:
                logger.warning(f"Directory does not exist or is not a directory: {directory}")
        
        logger.info("File monitor service initialized")
    
    async def start(self):
        """Start the file monitor service."""
        if self.is_running:
            logger.warning("File monitor service is already running")
            return
        
        logger.info("Starting file monitor service")
        
        if self.observer:
            self.observer.start()
        else:
            logger.warning("Observer is not initialized")
            self.observer = Observer()
            self.observer.start()
        
        self.is_running = True
        
        self.scan_task = asyncio.create_task(self._periodic_scan())
        
        logger.info("File monitor service started")
    
    async def stop(self):
        """Stop the file monitor service."""
        if not self.is_running:
            logger.warning("File monitor service is not running")
            return
        
        logger.info("Stopping file monitor service")
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        else:
            logger.warning("Observer is not initialized")
        
        if self.scan_task:
            self.scan_task.cancel()
            try:
                await self.scan_task
            except asyncio.CancelledError:
                pass
        
        self.is_running = False
        
        logger.info("File monitor service stopped")
    
    async def _periodic_scan(self):
        """Periodically scan monitored directories for changes."""
        while self.is_running:
            try:
                await asyncio.sleep(self.scan_interval)
                
                await self._scan_directories()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic scan: {e}", exc_info=True)
    
    async def _scan_directories(self):
        """Scan monitored directories for changes."""
        logger.debug("Scanning directories for changes")
        
        for directory in self.monitored_directories:
            path = Path(directory)
            if path.exists() and path.is_dir():
                await self._scan_directory(path)
    
    async def _scan_directory(self, directory: Path):
        """
        Scan a directory for changes.
        
        Args:
            directory: The directory to scan
        """
        try:
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if not self._should_ignore(os.path.join(root, d))]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self._should_ignore(file_path):
                        pass
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}", exc_info=True)
    
    def _should_ignore(self, path: Union[str, bytes]) -> bool:
        """
        Check if a path should be ignored.
        
        Args:
            path: The path to check (can be str or bytes)
            
        Returns:
            True if the path should be ignored, False otherwise
        """
        if isinstance(path, bytes):
            path = path.decode('utf-8')
            
        for pattern in self.ignore_patterns:
            if pattern in path:
                return True
        
        if os.path.isfile(path):
            _, ext = os.path.splitext(path)
            if self.monitored_extensions and ext.lower() not in self.monitored_extensions:
                return True
        
        return False
    
    def add_monitored_directory(self, directory: str):
        """
        Add a directory to the list of monitored directories.
        
        Args:
            directory: The directory to monitor
        """
        directory = os.path.expanduser(directory)
        if directory not in self.monitored_directories:
            logger.info(f"Adding monitored directory: {directory}")
            self.monitored_directories.append(directory)
            
            if self.observer and self.observer.is_alive():
                path = Path(directory)
                if path.exists() and path.is_dir():
                    self.observer.schedule(self.event_handler, directory, recursive=True)
                else:
                    logger.warning(f"Directory does not exist or is not a directory: {directory}")
    
    def remove_monitored_directory(self, directory: str):
        """
        Remove a directory from the list of monitored directories.
        
        Args:
            directory: The directory to stop monitoring
        """
        directory = os.path.expanduser(directory)
        if directory in self.monitored_directories:
            logger.info(f"Removing monitored directory: {directory}")
            self.monitored_directories.remove(directory)
            
            if self.observer and self.observer.is_alive():
                watches = list(self.observer._watches)
                
                for watch in watches:
                    if str(watch).startswith(directory):
                        self.observer.unschedule(watch)
    
    def add_monitored_extension(self, extension: str):
        """
        Add a file extension to the list of monitored extensions.
        
        Args:
            extension: The file extension to monitor (e.g., ".pdf")
        """
        extension = extension.lower()
        if extension not in self.monitored_extensions:
            logger.info(f"Adding monitored extension: {extension}")
            self.monitored_extensions.append(extension)
    
    def remove_monitored_extension(self, extension: str):
        """
        Remove a file extension from the list of monitored extensions.
        
        Args:
            extension: The file extension to stop monitoring (e.g., ".pdf")
        """
        extension = extension.lower()
        if extension in self.monitored_extensions:
            logger.info(f"Removing monitored extension: {extension}")
            self.monitored_extensions.remove(extension)
    
    def add_ignore_pattern(self, pattern: str):
        """
        Add a pattern to the list of ignored patterns.
        
        Args:
            pattern: The pattern to ignore
        """
        if pattern not in self.ignore_patterns:
            logger.info(f"Adding ignore pattern: {pattern}")
            self.ignore_patterns.append(pattern)
    
    def remove_ignore_pattern(self, pattern: str):
        """
        Remove a pattern from the list of ignored patterns.
        
        Args:
            pattern: The pattern to stop ignoring
        """
        if pattern in self.ignore_patterns:
            logger.info(f"Removing ignore pattern: {pattern}")
            self.ignore_patterns.remove(pattern)
    
    def set_scan_interval(self, interval: int):
        """
        Set the scan interval.
        
        Args:
            interval: The scan interval in seconds
        """
        if interval > 0:
            logger.info(f"Setting scan interval to {interval} seconds")
            self.scan_interval = interval
        else:
            logger.warning(f"Invalid scan interval: {interval}")

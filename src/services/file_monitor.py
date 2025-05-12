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
from typing import Dict, List, Optional, Set, Tuple, Union, Callable, Any

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
from ..core.events import EventType, Event, publish, subscribe, event_bus

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
        self.extensions = service.extensions
    
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
            if self.extensions and ext.lower() not in self.extensions:
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
            
            asyncio.create_task(self.service._process_file(event.src_path))
            
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
            
            asyncio.create_task(self.service._process_file(event.src_path))
    
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
            
            asyncio.create_task(self.service._process_file(event.dest_path))


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
        self.directories = []
        self.extensions = []
        self.ignore_patterns = []
        self.polling_interval = 1  # Default polling interval in seconds
        self.is_running = False
        self.scan_task = None
        self.enabled = True
        self.recursive = True
        self.watched_paths = set()
        self.file_handlers = {}
        
        self._load_config()
        self.event_handler = FileEventHandler(self)
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.directories = [
            os.path.expanduser(d)
            for d in self.config.get("file_monitor.directories", ["~/Documents"])
        ]
        
        extensions = self.config.get(
            "file_monitor.extensions",
            [".pdf", ".docx", ".doc", ".txt", ".md", ".pptx", ".xlsx", ".csv"]
        )
        self.extensions = [ext.lower() for ext in extensions]
        
        self.ignore_patterns = self.config.get(
            "file_monitor.ignore_patterns",
            [".*", "~*", ".tmp", ".temp", ".git", "__pycache__", ".DS_Store"]
        )
        
        self.polling_interval = self.config.get("file_monitor.polling_interval", 1)
        self.recursive = self.config.get("file_monitor.recursive", True)
        self.enabled = self.config.get("file_monitor.enabled", True)
    
    async def initialize(self):
        """Initialize the file monitor service."""
        logger.info("Initializing file monitor service")
        
        event_bus.subscribe(EventType.APP_CONFIGURATION_CHANGED, self._on_config_changed)
        
        logger.info("File monitor service initialized")
    
    async def start(self):
        """Start the file monitor service."""
        if self.is_running:
            logger.warning("File monitor service is already running")
            return
        
        if not self.enabled:
            logger.info("File monitor service is disabled")
            return
        
        logger.info("Starting file monitor service")
        
        self.observer = Observer()
        
        for directory in self.directories:
            path = Path(directory)
            if path.exists() and path.is_dir():
                logger.info(f"Scheduling directory for monitoring: {directory}")
                watch = self.observer.schedule(
                    self.event_handler, 
                    directory, 
                    recursive=self.recursive
                )
                self.watched_paths.add(directory)
            else:
                logger.warning(f"Directory does not exist or is not a directory: {directory}")
        
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
        
        if self.scan_task:
            self.scan_task.cancel()
            try:
                await self.scan_task
            except asyncio.CancelledError:
                pass
        
        self.is_running = False
        self.watched_paths.clear()
        
        logger.info("File monitor service stopped")
    
    async def restart(self):
        """Restart the file monitor service."""
        logger.info("Restarting file monitor service")
        
        if self.is_running:
            await self.stop()
        
        await self.start()
    
    def _on_config_changed(self, event: Event):
        """
        Handle configuration changes.
        
        Args:
            event: The configuration changed event
        """
        if not event.data or "settings" not in event.data:
            return
        
        settings = event.data["settings"]
        config_changed = False
        
        if "file_monitor.directories" in settings:
            self.directories = [
                os.path.expanduser(d) for d in settings["file_monitor.directories"]
            ]
            config_changed = True
        
        if "file_monitor.extensions" in settings:
            self.extensions = [ext.lower() for ext in settings["file_monitor.extensions"]]
            config_changed = True
        
        if "file_monitor.ignore_patterns" in settings:
            self.ignore_patterns = settings["file_monitor.ignore_patterns"]
            config_changed = True
        
        if "file_monitor.recursive" in settings:
            self.recursive = settings["file_monitor.recursive"]
            config_changed = True
        
        if "file_monitor.polling_interval" in settings:
            self.polling_interval = settings["file_monitor.polling_interval"]
            config_changed = True
        
        if "file_monitor.enabled" in settings:
            self.enabled = settings["file_monitor.enabled"]
            config_changed = True
        
        if config_changed:
            asyncio.create_task(self.restart())
    
    async def _periodic_scan(self):
        """Periodically scan monitored directories for changes."""
        while self.is_running:
            try:
                await asyncio.sleep(self.polling_interval)
                
                await self._scan_directories()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic scan: {e}", exc_info=True)
    
    async def _scan_directories(self):
        """Scan monitored directories for changes."""
        logger.debug("Scanning directories for changes")
        
        for directory in self.directories:
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
                        await self._process_file(file_path)
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}", exc_info=True)
    
    async def _process_file(self, file_path: str):
        """
        Process a file with registered handlers.
        
        Args:
            file_path: The path to the file to process
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext in self.file_handlers:
            try:
                await self.file_handlers[ext](file_path)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
    
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
            if self.extensions and ext.lower() not in self.extensions:
                return True
        
        return False
    
    def register_handler(self, extension: str, handler: Callable[[str], Any]):
        """
        Register a handler for a specific file extension.
        
        Args:
            extension: The file extension to handle (e.g., ".pdf")
            handler: The handler function to call for files with this extension
        """
        extension = extension.lower()
        logger.info(f"Registering handler for extension: {extension}")
        self.file_handlers[extension] = handler
    
    def unregister_handler(self, extension: str):
        """
        Unregister a handler for a specific file extension.
        
        Args:
            extension: The file extension to stop handling (e.g., ".pdf")
        """
        extension = extension.lower()
        if extension in self.file_handlers:
            logger.info(f"Unregistering handler for extension: {extension}")
            del self.file_handlers[extension]
    
    def add_directory(self, directory: str):
        """
        Add a directory to the list of monitored directories.
        
        Args:
            directory: The directory to monitor
        """
        directory = os.path.expanduser(directory)
        if directory not in self.directories:
            logger.info(f"Adding monitored directory: {directory}")
            self.directories.append(directory)
            
            if self.observer and self.observer.is_alive():
                path = Path(directory)
                if path.exists() and path.is_dir():
                    watch = self.observer.schedule(
                        self.event_handler, 
                        directory, 
                        recursive=self.recursive
                    )
                    self.watched_paths.add(directory)
                else:
                    logger.warning(f"Directory does not exist or is not a directory: {directory}")
    
    def remove_directory(self, directory: str):
        """
        Remove a directory from the list of monitored directories.
        
        Args:
            directory: The directory to stop monitoring
        """
        directory = os.path.expanduser(directory)
        if directory in self.directories:
            logger.info(f"Removing monitored directory: {directory}")
            self.directories.remove(directory)
            
            if self.observer and self.observer.is_alive():
                for watch in list(self.observer._watches.keys()):
                    watch_path = self.observer._watches[watch][0].path
                    if watch_path.startswith(directory):
                        self.observer.unschedule(watch)
                
                if directory in self.watched_paths:
                    self.watched_paths.remove(directory)
    
    def add_extension(self, extension: str):
        """
        Add a file extension to the list of monitored extensions.
        
        Args:
            extension: The file extension to monitor (e.g., ".pdf")
        """
        extension = extension.lower()
        if extension not in self.extensions:
            logger.info(f"Adding monitored extension: {extension}")
            self.extensions.append(extension)
    
    def remove_extension(self, extension: str):
        """
        Remove a file extension from the list of monitored extensions.
        
        Args:
            extension: The file extension to stop monitoring (e.g., ".pdf")
        """
        extension = extension.lower()
        if extension in self.extensions:
            logger.info(f"Removing monitored extension: {extension}")
            self.extensions.remove(extension)
    
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
    
    def set_polling_interval(self, interval: int):
        """
        Set the polling interval.
        
        Args:
            interval: The polling interval in seconds
        """
        if interval > 0:
            logger.info(f"Setting polling interval to {interval} seconds")
            self.polling_interval = interval
        else:
            logger.warning(f"Invalid polling interval: {interval}")

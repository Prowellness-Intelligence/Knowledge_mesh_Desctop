"""
Tests for the file monitor service.

This module contains tests for the file monitor service.
"""

import os
import tempfile
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.config import Config
from src.core.events import EventType, Event
from src.services.file_monitor import FileMonitorService


@pytest.fixture
def config():
    """Create a test configuration."""
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "file_monitor.directories": ["/tmp/test_dir"],
        "file_monitor.extensions": [".pdf", ".docx", ".txt"],
        "file_monitor.recursive": True,
        "file_monitor.ignore_patterns": [".*", "~*"],
        "file_monitor.polling_interval": 1,
        "file_monitor.enabled": True,
    }.get(key, default)
    return config


@pytest.fixture
def test_dir():
    """Create a temporary test directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.mark.asyncio
async def test_file_monitor_init(config):
    """Test file monitor initialization."""
    service = FileMonitorService(config)
    
    assert service.config == config
    assert service.is_running is False
    assert service.directories == ["/tmp/test_dir"]
    assert service.extensions == [".pdf", ".docx", ".txt"]
    assert service.recursive is True
    assert service.ignore_patterns == [".*", "~*"]
    assert service.polling_interval == 1
    assert service.enabled is True
    assert service.observer is None
    assert service.watched_paths == set()
    assert service.file_handlers == {}


@pytest.mark.asyncio
async def test_file_monitor_initialize(config):
    """Test file monitor initialization."""
    service = FileMonitorService(config)
    
    with patch("src.services.file_monitor.event_bus") as mock_event_bus:
        await service.initialize()
        
        mock_event_bus.subscribe.assert_called_with(
            EventType.CONFIG_CHANGED, service._on_config_changed
        )


@pytest.mark.asyncio
async def test_file_monitor_start_stop(config, test_dir):
    """Test starting and stopping the file monitor."""
    config.get.side_effect = lambda key, default=None: {
        "file_monitor.directories": [test_dir],
        "file_monitor.extensions": [".pdf", ".docx", ".txt"],
        "file_monitor.recursive": True,
        "file_monitor.ignore_patterns": [".*", "~*"],
        "file_monitor.polling_interval": 1,
        "file_monitor.enabled": True,
    }.get(key, default)
    
    service = FileMonitorService(config)
    await service.initialize()
    
    with patch("src.services.file_monitor.Observer") as mock_observer:
        await service.start()
        
        assert service.is_running is True
        mock_observer.return_value.start.assert_called_once()
        
        await service.stop()
        
        assert service.is_running is False
        mock_observer.return_value.stop.assert_called_once()
        mock_observer.return_value.join.assert_called_once()


@pytest.mark.asyncio
async def test_file_monitor_on_config_changed(config):
    """Test handling config changes."""
    service = FileMonitorService(config)
    await service.initialize()
    
    service.restart = MagicMock()
    
    event = Event(
        type=EventType.CONFIG_CHANGED,
        data={
            "settings": {
                "file_monitor.directories": ["/tmp/new_dir"],
                "file_monitor.extensions": [".pdf", ".docx"],
                "file_monitor.recursive": False,
                "file_monitor.ignore_patterns": [".*"],
                "file_monitor.polling_interval": 2,
                "file_monitor.enabled": True,
            }
        },
    )
    
    service._on_config_changed(event)
    
    assert service.directories == ["/tmp/new_dir"]
    assert service.extensions == [".pdf", ".docx"]
    assert service.recursive is False
    assert service.ignore_patterns == [".*"]
    assert service.polling_interval == 2
    assert service.enabled is True
    
    service.restart.assert_called_once()


@pytest.mark.asyncio
async def test_file_monitor_restart(config):
    """Test restarting the file monitor."""
    service = FileMonitorService(config)
    await service.initialize()
    
    service.start = MagicMock()
    service.stop = MagicMock()
    
    service.is_running = True
    
    await service.restart()
    
    service.stop.assert_called_once()
    service.start.assert_called_once()


@pytest.mark.asyncio
async def test_file_monitor_register_handler(config):
    """Test registering a file handler."""
    service = FileMonitorService(config)
    await service.initialize()
    
    async def handler(file_path):
        pass
    
    service.register_handler(".pdf", handler)
    
    assert service.file_handlers[".pdf"] == handler


@pytest.mark.asyncio
async def test_file_monitor_unregister_handler(config):
    """Test unregistering a file handler."""
    service = FileMonitorService(config)
    await service.initialize()
    
    async def handler(file_path):
        pass
    
    service.register_handler(".pdf", handler)
    
    assert service.file_handlers[".pdf"] == handler
    
    service.unregister_handler(".pdf")
    
    assert ".pdf" not in service.file_handlers

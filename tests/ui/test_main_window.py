"""
Tests for the main window UI component.

This module contains tests for the main window UI component.
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from tkinter import Tk

from src.core.config import Config
from src.core.events import EventType, Event
from src.ui.main_window import MainWindow


@pytest.fixture
def config():
    """Create a test configuration."""
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "ui.theme": "light",
        "ui.window_width": 1200,
        "ui.window_height": 800,
        "ui.window_title": "Knowledge Mesh Desktop",
        "ui.window_icon": None,
        "ui.font_family": "Arial",
        "ui.font_size": 10,
    }.get(key, default)
    return config


@pytest.fixture
def root():
    """Create a Tkinter root window."""
    root = Tk()
    yield root
    root.destroy()


def test_main_window_init(config, root):
    """Test main window initialization."""
    with patch("src.ui.main_window.event_bus"):
        window = MainWindow(root, config)
        
        assert window.root == root
        assert window.config == config
        assert window.title == "Knowledge Mesh Desktop"
        assert window.width == 1200
        assert window.height == 800
        assert window.theme == "light"
        assert window.font_family == "Arial"
        assert window.font_size == 10


def test_main_window_create_widgets(config, root):
    """Test creating widgets in the main window."""
    with patch("src.ui.main_window.event_bus"):
        with patch("src.ui.main_window.DocumentPanel") as mock_document_panel:
            with patch("src.ui.main_window.RelationshipPanel") as mock_relationship_panel:
                with patch("src.ui.main_window.SearchPanel") as mock_search_panel:
                    with patch("src.ui.main_window.SettingsPanel") as mock_settings_panel:
                        with patch("src.ui.main_window.NotificationPanel") as mock_notification_panel:
                            window = MainWindow(root, config)
                            window.create_widgets()
                            
                            mock_document_panel.assert_called_once()
                            mock_relationship_panel.assert_called_once()
                            mock_search_panel.assert_called_once()
                            mock_settings_panel.assert_called_once()
                            mock_notification_panel.assert_called_once()


def test_main_window_create_menu(config, root):
    """Test creating the menu in the main window."""
    with patch("src.ui.main_window.event_bus"):
        window = MainWindow(root, config)
        window.create_menu()
        
        assert root.nametowidget(".menubar") is not None
        assert root.nametowidget(".menubar.file") is not None
        assert root.nametowidget(".menubar.edit") is not None
        assert root.nametowidget(".menubar.view") is not None
        assert root.nametowidget(".menubar.help") is not None


def test_main_window_on_config_changed(config, root):
    """Test handling config changes in the main window."""
    with patch("src.ui.main_window.event_bus"):
        window = MainWindow(root, config)
        
        window.apply_theme = MagicMock()
        
        event = Event(
            type=EventType.CONFIG_CHANGED,
            data={
                "settings": {
                    "ui.theme": "dark",
                    "ui.font_family": "Helvetica",
                    "ui.font_size": 12,
                }
            }
        )
        
        window._on_config_changed(event)
        
        assert window.theme == "dark"
        assert window.font_family == "Helvetica"
        assert window.font_size == 12
        window.apply_theme.assert_called_once()


def test_main_window_apply_theme(config, root):
    """Test applying a theme to the main window."""
    with patch("src.ui.main_window.event_bus"):
        window = MainWindow(root, config)
        
        window.theme = "light"
        window.apply_theme()
        
        assert root.cget("background") == "#FFFFFF"
        
        window.theme = "dark"
        window.apply_theme()
        
        assert root.cget("background") == "#1E1E1E"


def test_main_window_on_close(config, root):
    """Test handling the window close event."""
    with patch("src.ui.main_window.event_bus") as mock_event_bus:
        window = MainWindow(root, config)
        
        window.on_close()
        
        mock_event_bus.publish.assert_called_with(
            EventType.APPLICATION_CLOSING,
            {}
        )

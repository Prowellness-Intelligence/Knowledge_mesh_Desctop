"""
Tests for the theme manager service.

This module provides tests for the theme manager service.
"""

import sys
import os
import asyncio
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor

from src.core.config import Config
from src.services.theme_manager import ThemeManagerService, Theme, ThemeType
from src.ui.theme_selector import ThemeSelectorWidget, ThemePreviewWidget, ColorPreviewWidget


app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


async def test_theme_manager():
    """Test the theme manager service."""
    temp_dir = Path("/tmp/knowledge_mesh_test_themes")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "app.data_dir": str(temp_dir),
    }.get(key, default)
    
    theme_manager = ThemeManagerService(config)
    
    print("Testing theme manager initialization...")
    
    themes = theme_manager.get_themes()
    assert len(themes) >= 4  # Dark, Light, Blue, Green
    
    assert "Dark Theme" in [theme.name for theme in themes]
    assert "Light Theme" in [theme.name for theme in themes]
    assert "Blue Theme" in [theme.name for theme in themes]
    assert "Green Theme" in [theme.name for theme in themes]
    
    current_theme = theme_manager.get_current_theme()
    assert current_theme is not None
    assert current_theme.name in [theme.name for theme in themes]
    
    print("Testing theme switching...")
    
    success = theme_manager.set_theme("Light Theme")
    assert success is True
    
    current_theme = theme_manager.get_current_theme()
    assert current_theme.name == "Light Theme"
    assert current_theme.type == ThemeType.LIGHT
    
    success = theme_manager.set_theme("Blue Theme")
    assert success is True
    
    current_theme = theme_manager.get_current_theme()
    assert current_theme.name == "Blue Theme"
    assert current_theme.type == ThemeType.BLUE
    
    print("Testing theme creation...")
    
    new_theme = Theme(
        name="Test Theme",
        type=ThemeType.DARK,
        colors={
            "background": "#000000",
            "card_background": "#111111",
            "text": "#FFFFFF",
            "accent": "#FF0000",
            "accent_text": "#FFFFFF",
            "accent_secondary": "#00FF00",
            "button_background": "#222222",
            "button_text": "#FFFFFF",
            "border": "#333333",
            "alternate_background": "#444444",
            "disabled_text": "#666666",
            "error": "#FF0000",
            "warning": "#FFFF00",
            "success": "#00FF00",
            "info": "#0000FF",
            "glow": "#FF0000",
            "card_shadow": "#000000",
            "high_priority": "#FF0000",
            "medium_priority": "#FFFF00",
            "low_priority": "#00FF00",
            "node_document": "#0000FF",
            "node_concept": "#FF00FF",
            "node_person": "#00FF00",
            "edge_semantic": "#00FFFF",
            "edge_reference": "#FFFF00",
            "edge_authorship": "#FF00FF",
        },
        description="A test theme",
    )
    
    success = theme_manager.add_theme(new_theme)
    assert success is True
    
    themes = theme_manager.get_themes()
    assert "Test Theme" in [theme.name for theme in themes]
    
    success = theme_manager.set_theme("Test Theme")
    assert success is True
    
    current_theme = theme_manager.get_current_theme()
    assert current_theme.name == "Test Theme"
    
    print("Testing theme removal...")
    
    success = theme_manager.remove_theme("Test Theme")
    assert success is True
    
    themes = theme_manager.get_themes()
    assert "Test Theme" not in [theme.name for theme in themes]
    
    current_theme = theme_manager.get_current_theme()
    assert current_theme.name in ["Dark Theme", "Light Theme", "Blue Theme", "Green Theme"]
    
    print("Testing theme to palette conversion...")
    
    theme = theme_manager.get_theme("Dark Theme")
    assert theme is not None
    
    palette = theme.to_palette()
    assert isinstance(palette, QPalette)
    
    assert palette.color(QPalette.Window) == theme.get_qcolor("background")
    assert palette.color(QPalette.WindowText) == theme.get_qcolor("text")
    assert palette.color(QPalette.Button) == theme.get_qcolor("button_background")
    assert palette.color(QPalette.ButtonText) == theme.get_qcolor("button_text")
    
    print("All theme manager tests passed!")


async def test_theme_selector():
    """Test the theme selector widget."""
    temp_dir = Path("/tmp/knowledge_mesh_test_themes")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "app.data_dir": str(temp_dir),
    }.get(key, default)
    
    theme_manager = ThemeManagerService(config)
    
    theme_selector = ThemeSelectorWidget(theme_manager)
    
    print("Testing theme selector initialization...")
    
    assert theme_selector.theme_combo.count() >= 4  # Dark, Light, Blue, Green
    
    current_theme = theme_manager.get_current_theme()
    current_index = theme_selector.theme_combo.currentIndex()
    assert theme_selector.theme_combo.itemData(current_index) == current_theme.name
    
    print("Testing theme selection...")
    
    theme_selector.theme_combo.setCurrentIndex(1)  # Select the second theme
    
    current_theme = theme_manager.get_current_theme()
    assert current_theme.name == theme_selector.theme_combo.itemData(1)
    
    print("Testing theme preview widget...")
    
    theme = theme_manager.get_theme("Dark Theme")
    preview = ThemePreviewWidget(theme)
    
    assert preview.theme == theme
    
    print("Testing color preview widget...")
    
    color = QColor("#FF0000")
    color_preview = ColorPreviewWidget(color)
    
    assert color_preview.color == color
    
    print("All theme selector tests passed!")


if __name__ == "__main__":
    asyncio.run(test_theme_manager())
    asyncio.run(test_theme_selector())

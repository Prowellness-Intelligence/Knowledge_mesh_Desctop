"""
Theme manager service for the Knowledge Mesh Desktop application.

This module provides a service for managing application themes, including
iMac-inspired color themes (blue, light green) and white alternatives
alongside the existing dark theme.
"""

import os
import json
from enum import Enum
from typing import Dict, Any, Optional, List
from pathlib import Path

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import QObject, pyqtSignal, QSettings

from src.core.config import Config
from src.core.events import EventType, publish_event


class ThemeType(str, Enum):
    """Enum for theme types."""
    DARK = "dark"
    LIGHT = "light"
    BLUE = "blue"
    GREEN = "green"


class Theme:
    """Class representing a theme."""
    
    def __init__(
        self,
        name: str,
        type: ThemeType,
        colors: Dict[str, str],
        description: str = "",
    ):
        """Initialize a theme.
        
        Args:
            name: The name of the theme.
            type: The type of the theme.
            colors: The colors of the theme.
            description: The description of the theme.
        """
        self.name = name
        self.type = type
        self.colors = colors
        self.description = description
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Theme":
        """Create a theme from a dictionary.
        
        Args:
            data: The dictionary to create the theme from.
            
        Returns:
            The created theme.
        """
        return cls(
            name=data["name"],
            type=ThemeType(data["type"]),
            colors=data["colors"],
            description=data.get("description", ""),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the theme to a dictionary.
        
        Returns:
            The theme as a dictionary.
        """
        return {
            "name": self.name,
            "type": self.type.value,
            "colors": self.colors,
            "description": self.description,
        }
    
    def get_color(self, key: str) -> str:
        """Get a color from the theme.
        
        Args:
            key: The key of the color to get.
            
        Returns:
            The color.
        """
        return self.colors.get(key, "#000000")
    
    def get_qcolor(self, key: str) -> QColor:
        """Get a QColor from the theme.
        
        Args:
            key: The key of the color to get.
            
        Returns:
            The QColor.
        """
        return QColor(self.get_color(key))
    
    def to_palette(self) -> QPalette:
        """Convert the theme to a QPalette.
        
        Returns:
            The QPalette.
        """
        palette = QPalette()
        
        palette.setColor(QPalette.Window, self.get_qcolor("background"))
        palette.setColor(QPalette.WindowText, self.get_qcolor("text"))
        
        palette.setColor(QPalette.Button, self.get_qcolor("button_background"))
        palette.setColor(QPalette.ButtonText, self.get_qcolor("button_text"))
        
        palette.setColor(QPalette.Base, self.get_qcolor("card_background"))
        palette.setColor(QPalette.AlternateBase, self.get_qcolor("alternate_background"))
        palette.setColor(QPalette.Text, self.get_qcolor("text"))
        
        palette.setColor(QPalette.Highlight, self.get_qcolor("accent"))
        palette.setColor(QPalette.HighlightedText, self.get_qcolor("accent_text"))
        
        palette.setColor(QPalette.Disabled, QPalette.WindowText, self.get_qcolor("disabled_text"))
        palette.setColor(QPalette.Disabled, QPalette.Text, self.get_qcolor("disabled_text"))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, self.get_qcolor("disabled_text"))
        
        return palette


class ThemeManagerService(QObject):
    """Service for managing application themes."""
    
    theme_changed = pyqtSignal(Theme)
    
    def __init__(self, config: Config):
        """Initialize the theme manager service.
        
        Args:
            config: The application configuration.
        """
        super().__init__()
        
        self.config = config
        self.themes: Dict[str, Theme] = {}
        self.current_theme: Optional[Theme] = None
        self.settings = QSettings("Prowellness-Intelligence", "Knowledge-Mesh-Desktop")
        
        self._load_default_themes()
        self._load_custom_themes()
        
        theme_name = self.settings.value("theme/current", "Dark Theme")
        if theme_name in self.themes:
            self.current_theme = self.themes[theme_name]
        else:
            self.current_theme = self.themes["Dark Theme"]
    
    def _load_default_themes(self):
        """Load the default themes."""
        self.themes["Dark Theme"] = Theme(
            name="Dark Theme",
            type=ThemeType.DARK,
            colors={
                "background": "#121212",
                "card_background": "#1E1E1E",
                "text": "#FFFFFF",
                "accent": "#00BCD4",
                "accent_text": "#FFFFFF",
                "accent_secondary": "#4CAF50",
                "button_background": "#2D2D2D",
                "button_text": "#FFFFFF",
                "border": "#333333",
                "alternate_background": "#252525",
                "disabled_text": "#666666",
                "error": "#F44336",
                "warning": "#FFC107",
                "success": "#4CAF50",
                "info": "#2196F3",
                "glow": "#00BCD4",
                "card_shadow": "#000000",
                "high_priority": "#F44336",
                "medium_priority": "#FFC107",
                "low_priority": "#4CAF50",
                "node_document": "#2196F3",
                "node_concept": "#9C27B0",
                "node_person": "#4CAF50",
                "edge_semantic": "#00BCD4",
                "edge_reference": "#FFC107",
                "edge_authorship": "#9C27B0",
            },
            description="A dark theme with teal accents",
        )
        
        self.themes["Light Theme"] = Theme(
            name="Light Theme",
            type=ThemeType.LIGHT,
            colors={
                "background": "#F5F5F5",
                "card_background": "#FFFFFF",
                "text": "#212121",
                "accent": "#00838F",
                "accent_text": "#FFFFFF",
                "accent_secondary": "#388E3C",
                "button_background": "#E0E0E0",
                "button_text": "#212121",
                "border": "#BDBDBD",
                "alternate_background": "#EEEEEE",
                "disabled_text": "#9E9E9E",
                "error": "#D32F2F",
                "warning": "#FFA000",
                "success": "#388E3C",
                "info": "#1976D2",
                "glow": "#00838F",
                "card_shadow": "#BDBDBD",
                "high_priority": "#D32F2F",
                "medium_priority": "#FFA000",
                "low_priority": "#388E3C",
                "node_document": "#1976D2",
                "node_concept": "#7B1FA2",
                "node_person": "#388E3C",
                "edge_semantic": "#00838F",
                "edge_reference": "#FFA000",
                "edge_authorship": "#7B1FA2",
            },
            description="A light theme with teal accents",
        )
        
        self.themes["Blue Theme"] = Theme(
            name="Blue Theme",
            type=ThemeType.BLUE,
            colors={
                "background": "#1A237E",
                "card_background": "#283593",
                "text": "#FFFFFF",
                "accent": "#00B0FF",
                "accent_text": "#FFFFFF",
                "accent_secondary": "#64FFDA",
                "button_background": "#3949AB",
                "button_text": "#FFFFFF",
                "border": "#3F51B5",
                "alternate_background": "#303F9F",
                "disabled_text": "#9FA8DA",
                "error": "#FF5252",
                "warning": "#FFD740",
                "success": "#69F0AE",
                "info": "#40C4FF",
                "glow": "#00B0FF",
                "card_shadow": "#0D47A1",
                "high_priority": "#FF5252",
                "medium_priority": "#FFD740",
                "low_priority": "#69F0AE",
                "node_document": "#40C4FF",
                "node_concept": "#EA80FC",
                "node_person": "#69F0AE",
                "edge_semantic": "#00B0FF",
                "edge_reference": "#FFD740",
                "edge_authorship": "#EA80FC",
            },
            description="A blue theme inspired by iMac colors",
        )
        
        self.themes["Green Theme"] = Theme(
            name="Green Theme",
            type=ThemeType.GREEN,
            colors={
                "background": "#1B5E20",
                "card_background": "#2E7D32",
                "text": "#FFFFFF",
                "accent": "#00E676",
                "accent_text": "#212121",
                "accent_secondary": "#FFFF00",
                "button_background": "#388E3C",
                "button_text": "#FFFFFF",
                "border": "#43A047",
                "alternate_background": "#388E3C",
                "disabled_text": "#A5D6A7",
                "error": "#FF5252",
                "warning": "#FFD740",
                "success": "#69F0AE",
                "info": "#40C4FF",
                "glow": "#00E676",
                "card_shadow": "#1B5E20",
                "high_priority": "#FF5252",
                "medium_priority": "#FFD740",
                "low_priority": "#69F0AE",
                "node_document": "#40C4FF",
                "node_concept": "#EA80FC",
                "node_person": "#FFFF00",
                "edge_semantic": "#00E676",
                "edge_reference": "#FFD740",
                "edge_authorship": "#EA80FC",
            },
            description="A green theme inspired by iMac colors",
        )
    
    def _load_custom_themes(self):
        """Load custom themes from the themes directory."""
        themes_dir = Path(self.config.get("app.data_dir", "./data")) / "themes"
        
        if not themes_dir.exists():
            themes_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for theme_file in themes_dir.glob("*.json"):
            try:
                with open(theme_file, "r") as f:
                    theme_data = json.load(f)
                
                theme = Theme.from_dict(theme_data)
                self.themes[theme.name] = theme
            except Exception as e:
                print(f"Error loading theme {theme_file}: {e}")
    
    def get_themes(self) -> List[Theme]:
        """Get all available themes.
        
        Returns:
            A list of all available themes.
        """
        return list(self.themes.values())
    
    def get_theme(self, name: str) -> Optional[Theme]:
        """Get a theme by name.
        
        Args:
            name: The name of the theme to get.
            
        Returns:
            The theme, or None if not found.
        """
        return self.themes.get(name)
    
    def get_current_theme(self) -> Theme:
        """Get the current theme.
        
        Returns:
            The current theme.
        """
        return self.current_theme
    
    def set_theme(self, name: str) -> bool:
        """Set the current theme.
        
        Args:
            name: The name of the theme to set.
            
        Returns:
            True if the theme was set, False otherwise.
        """
        if name not in self.themes:
            return False
        
        self.current_theme = self.themes[name]
        self.settings.setValue("theme/current", name)
        
        publish_event(
            EventType.THEME_CHANGED,
            {
                "theme_name": name,
                "theme_type": self.current_theme.type.value,
            },
        )
        
        self.theme_changed.emit(self.current_theme)
        
        return True
    
    def add_theme(self, theme: Theme) -> bool:
        """Add a new theme.
        
        Args:
            theme: The theme to add.
            
        Returns:
            True if the theme was added, False otherwise.
        """
        if theme.name in self.themes:
            return False
        
        self.themes[theme.name] = theme
        
        themes_dir = Path(self.config.get("app.data_dir", "./data")) / "themes"
        themes_dir.mkdir(parents=True, exist_ok=True)
        
        theme_file = themes_dir / f"{theme.name.lower().replace(' ', '_')}.json"
        
        with open(theme_file, "w") as f:
            json.dump(theme.to_dict(), f, indent=2)
        
        return True
    
    def remove_theme(self, name: str) -> bool:
        """Remove a theme.
        
        Args:
            name: The name of the theme to remove.
            
        Returns:
            True if the theme was removed, False otherwise.
        """
        if name not in self.themes:
            return False
        
        if name in ["Dark Theme", "Light Theme", "Blue Theme", "Green Theme"]:
            return False
        
        if self.current_theme and self.current_theme.name == name:
            self.set_theme("Dark Theme")
        
        del self.themes[name]
        
        themes_dir = Path(self.config.get("app.data_dir", "./data")) / "themes"
        theme_file = themes_dir / f"{name.lower().replace(' ', '_')}.json"
        
        if theme_file.exists():
            theme_file.unlink()
        
        return True

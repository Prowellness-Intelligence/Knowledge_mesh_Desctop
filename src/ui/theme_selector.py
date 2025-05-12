"""
Theme selector UI component for the Knowledge Mesh Desktop application.

This module provides a UI component for selecting and managing themes,
including iMac-inspired color themes (blue, light green) and white alternatives
alongside the existing dark theme.
"""

import os
from typing import Dict, List, Optional, Any, Callable

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QColorDialog, QDialog, QLineEdit, QFormLayout,
    QDialogButtonBox, QTabWidget, QScrollArea, QFrame, QGridLayout,
    QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QColor, QPalette, QIcon, QPixmap, QPainter, QBrush, QLinearGradient
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRect, QPoint

from src.services.theme_manager import ThemeManagerService, Theme, ThemeType


class ColorPreviewWidget(QWidget):
    """Widget for previewing a color."""
    
    def __init__(self, color: QColor, size: int = 24, parent=None):
        """Initialize the color preview widget.
        
        Args:
            color: The color to preview
            size: The size of the preview widget
            parent: The parent widget
        """
        super().__init__(parent)
        
        self.color = color
        self.size = size
        self.setFixedSize(size, size)
        self.setToolTip(color.name())
    
    def paintEvent(self, event):
        """Paint the color preview."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setPen(Qt.gray)
        painter.setBrush(QBrush(self.color))
        painter.drawRoundedRect(0, 0, self.size, self.size, 4, 4)


class ThemePreviewWidget(QWidget):
    """Widget for previewing a theme."""
    
    def __init__(self, theme: Theme, parent=None):
        """Initialize the theme preview widget.
        
        Args:
            theme: The theme to preview
            parent: The parent widget
        """
        super().__init__(parent)
        
        self.theme = theme
        self.setFixedSize(200, 120)
        self.setToolTip(theme.description)
    
    def paintEvent(self, event):
        """Paint the theme preview."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        background_color = self.theme.get_qcolor("background")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(background_color))
        painter.drawRect(0, 0, self.width(), self.height())
        
        card_color = self.theme.get_qcolor("card_background")
        painter.setBrush(QBrush(card_color))
        card_rect = QRect(10, 10, self.width() - 20, 60)
        painter.drawRoundedRect(card_rect, 8, 8)
        
        text_color = self.theme.get_qcolor("text")
        painter.setPen(text_color)
        painter.drawText(card_rect.adjusted(8, 8, -8, -8), Qt.AlignLeft | Qt.AlignTop, "Sample Text")
        
        accent_color = self.theme.get_qcolor("accent")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(accent_color))
        accent_rect = QRect(10, 80, 80, 30)
        painter.drawRoundedRect(accent_rect, 4, 4)
        
        accent_text_color = self.theme.get_qcolor("accent_text")
        painter.setPen(accent_text_color)
        painter.drawText(accent_rect, Qt.AlignCenter, "Button")
        
        secondary_color = self.theme.get_qcolor("accent_secondary")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(secondary_color))
        secondary_rect = QRect(100, 80, 80, 30)
        painter.drawRoundedRect(secondary_rect, 4, 4)
        
        painter.setPen(self.theme.get_qcolor("text"))
        painter.drawText(secondary_rect, Qt.AlignCenter, "Button 2")


class ThemeEditorDialog(QDialog):
    """Dialog for editing a theme."""
    
    def __init__(self, theme: Optional[Theme] = None, parent=None):
        """Initialize the theme editor dialog.
        
        Args:
            theme: The theme to edit, or None to create a new theme
            parent: The parent widget
        """
        super().__init__(parent)
        
        self.theme = theme
        self.color_widgets: Dict[str, ColorPreviewWidget] = {}
        
        self.setWindowTitle("Theme Editor" if theme else "Create Theme")
        self.setMinimumWidth(500)
        
        self.layout = QVBoxLayout(self)
        
        self.form_layout = QFormLayout()
        
        self.name_edit = QLineEdit(theme.name if theme else "")
        self.form_layout.addRow("Name:", self.name_edit)
        
        self.type_combo = QComboBox()
        for theme_type in ThemeType:
            self.type_combo.addItem(theme_type.value.capitalize(), theme_type)
        
        if theme:
            index = self.type_combo.findData(theme.type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
        
        self.form_layout.addRow("Type:", self.type_combo)
        
        self.description_edit = QLineEdit(theme.description if theme else "")
        self.form_layout.addRow("Description:", self.description_edit)
        
        self.layout.addLayout(self.form_layout)
        
        self.tab_widget = QTabWidget()
        
        self.main_colors_widget = QWidget()
        self.main_colors_layout = QGridLayout(self.main_colors_widget)
        
        self._add_color_editor("background", "Background", 0, 0)
        self._add_color_editor("card_background", "Card Background", 0, 1)
        self._add_color_editor("text", "Text", 1, 0)
        self._add_color_editor("accent", "Accent", 1, 1)
        self._add_color_editor("accent_text", "Accent Text", 2, 0)
        self._add_color_editor("accent_secondary", "Secondary Accent", 2, 1)
        self._add_color_editor("button_background", "Button Background", 3, 0)
        self._add_color_editor("button_text", "Button Text", 3, 1)
        self._add_color_editor("border", "Border", 4, 0)
        self._add_color_editor("alternate_background", "Alternate Background", 4, 1)
        
        self.tab_widget.addTab(self.main_colors_widget, "Main Colors")
        
        self.status_colors_widget = QWidget()
        self.status_colors_layout = QGridLayout(self.status_colors_widget)
        
        self._add_color_editor("disabled_text", "Disabled Text", 0, 0)
        self._add_color_editor("error", "Error", 0, 1)
        self._add_color_editor("warning", "Warning", 1, 0)
        self._add_color_editor("success", "Success", 1, 1)
        self._add_color_editor("info", "Info", 2, 0)
        self._add_color_editor("glow", "Glow", 2, 1)
        self._add_color_editor("card_shadow", "Card Shadow", 3, 0)
        
        self.tab_widget.addTab(self.status_colors_widget, "Status Colors")
        
        self.priority_colors_widget = QWidget()
        self.priority_colors_layout = QGridLayout(self.priority_colors_widget)
        
        self._add_color_editor("high_priority", "High Priority", 0, 0)
        self._add_color_editor("medium_priority", "Medium Priority", 0, 1)
        self._add_color_editor("low_priority", "Low Priority", 1, 0)
        
        self.tab_widget.addTab(self.priority_colors_widget, "Priority Colors")
        
        self.mesh_colors_widget = QWidget()
        self.mesh_colors_layout = QGridLayout(self.mesh_colors_widget)
        
        self._add_color_editor("node_document", "Document Node", 0, 0)
        self._add_color_editor("node_concept", "Concept Node", 0, 1)
        self._add_color_editor("node_person", "Person Node", 1, 0)
        self._add_color_editor("edge_semantic", "Semantic Edge", 1, 1)
        self._add_color_editor("edge_reference", "Reference Edge", 2, 0)
        self._add_color_editor("edge_authorship", "Authorship Edge", 2, 1)
        
        self.tab_widget.addTab(self.mesh_colors_widget, "Knowledge Mesh")
        
        self.layout.addWidget(self.tab_widget)
        
        self.preview_label = QLabel("Preview:")
        self.layout.addWidget(self.preview_label)
        
        self.preview_widget = ThemePreviewWidget(
            theme or Theme(
                name="New Theme",
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
                description="",
            )
        )
        self.layout.addWidget(self.preview_widget, alignment=Qt.AlignCenter)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        
        for widget in self.color_widgets.values():
            widget.color_changed = self._update_preview
    
    def _add_color_editor(self, key: str, label: str, row: int, col: int):
        """Add a color editor for a specific color key.
        
        Args:
            key: The color key
            label: The label for the color
            row: The row in the grid layout
            col: The column in the grid layout
        """
        color_layout = QHBoxLayout()
        
        color_label = QLabel(label)
        color_layout.addWidget(color_label)
        
        color = QColor(self.theme.get_color(key) if self.theme else "#000000")
        color_preview = ColorPreviewWidget(color)
        self.color_widgets[key] = color_preview
        color_layout.addWidget(color_preview)
        
        color_button = QPushButton("Edit")
        color_button.clicked.connect(lambda: self._edit_color(key))
        color_layout.addWidget(color_button)
        
        if col == 0:
            self.main_colors_layout.addLayout(color_layout, row, col)
        else:
            self.main_colors_layout.addLayout(color_layout, row, col)
    
    def _edit_color(self, key: str):
        """Edit a color.
        
        Args:
            key: The color key to edit
        """
        color_dialog = QColorDialog(self.color_widgets[key].color, self)
        if color_dialog.exec_():
            color = color_dialog.selectedColor()
            self.color_widgets[key].color = color
            self.color_widgets[key].update()
            self._update_preview()
    
    def _update_preview(self):
        """Update the theme preview."""
        colors = {}
        for key, widget in self.color_widgets.items():
            colors[key] = widget.color.name()
        
        theme = Theme(
            name=self.name_edit.text(),
            type=self.type_combo.currentData(),
            colors=colors,
            description=self.description_edit.text(),
        )
        
        self.preview_widget.theme = theme
        self.preview_widget.update()
    
    def get_theme(self) -> Theme:
        """Get the edited theme.
        
        Returns:
            The edited theme
        """
        colors = {}
        for key, widget in self.color_widgets.items():
            colors[key] = widget.color.name()
        
        return Theme(
            name=self.name_edit.text(),
            type=self.type_combo.currentData(),
            colors=colors,
            description=self.description_edit.text(),
        )


class ThemeSelectorWidget(QWidget):
    """Widget for selecting and managing themes."""
    
    theme_changed = pyqtSignal(str)
    
    def __init__(self, theme_manager: ThemeManagerService, parent=None):
        """Initialize the theme selector widget.
        
        Args:
            theme_manager: The theme manager service
            parent: The parent widget
        """
        super().__init__(parent)
        
        self.theme_manager = theme_manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.selector_layout = QHBoxLayout()
        
        self.selector_label = QLabel("Theme:")
        self.selector_layout.addWidget(self.selector_label)
        
        self.theme_combo = QComboBox()
        self._update_theme_list()
        self.selector_layout.addWidget(self.theme_combo)
        
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self._edit_theme)
        self.selector_layout.addWidget(self.edit_button)
        
        self.new_button = QPushButton("New")
        self.new_button.clicked.connect(self._create_theme)
        self.selector_layout.addWidget(self.new_button)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self._delete_theme)
        self.selector_layout.addWidget(self.delete_button)
        
        self.layout.addLayout(self.selector_layout)
        
        self.previews_label = QLabel("Available Themes:")
        self.layout.addWidget(self.previews_label)
        
        self.previews_scroll = QScrollArea()
        self.previews_scroll.setWidgetResizable(True)
        self.previews_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.previews_scroll.setFrameShape(QFrame.NoFrame)
        
        self.previews_widget = QWidget()
        self.previews_layout = QGridLayout(self.previews_widget)
        
        self._update_theme_previews()
        
        self.previews_scroll.setWidget(self.previews_widget)
        self.layout.addWidget(self.previews_scroll)
        
        self.theme_combo.currentIndexChanged.connect(self._on_theme_selected)
        self.theme_manager.theme_changed.connect(self._on_theme_changed)
    
    def _update_theme_list(self):
        """Update the theme list in the combo box."""
        self.theme_combo.clear()
        
        for theme in self.theme_manager.get_themes():
            self.theme_combo.addItem(theme.name, theme.name)
        
        current_theme = self.theme_manager.get_current_theme()
        if current_theme:
            index = self.theme_combo.findData(current_theme.name)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
    
    def _update_theme_previews(self):
        """Update the theme previews."""
        while self.previews_layout.count():
            item = self.previews_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        themes = self.theme_manager.get_themes()
        cols = 3
        
        for i, theme in enumerate(themes):
            row = i // cols
            col = i % cols
            
            preview = ThemePreviewWidget(theme)
            preview.setToolTip(f"{theme.name}: {theme.description}")
            preview.mousePressEvent = lambda event, theme=theme: self._on_preview_clicked(theme)
            
            self.previews_layout.addWidget(preview, row, col, alignment=Qt.AlignCenter)
        
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.previews_layout.addItem(spacer, len(themes) // cols + 1, 0, 1, cols)
    
    def _on_theme_selected(self, index: int):
        """Handle theme selection.
        
        Args:
            index: The index of the selected theme
        """
        if index < 0:
            return
        
        theme_name = self.theme_combo.itemData(index)
        if theme_name:
            self.theme_manager.set_theme(theme_name)
            self.theme_changed.emit(theme_name)
    
    def _on_preview_clicked(self, theme: Theme):
        """Handle theme preview click.
        
        Args:
            theme: The clicked theme
        """
        self.theme_manager.set_theme(theme.name)
        
        index = self.theme_combo.findData(theme.name)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        self.theme_changed.emit(theme.name)
    
    def _on_theme_changed(self, theme: Theme):
        """Handle theme change.
        
        Args:
            theme: The new theme
        """
        index = self.theme_combo.findData(theme.name)
        if index >= 0 and index != self.theme_combo.currentIndex():
            self.theme_combo.setCurrentIndex(index)
    
    def _edit_theme(self):
        """Edit the current theme."""
        theme_name = self.theme_combo.currentData()
        if not theme_name:
            return
        
        theme = self.theme_manager.get_theme(theme_name)
        if not theme:
            return
        
        if theme_name in ["Dark Theme", "Light Theme", "Blue Theme", "Green Theme"]:
            dialog = ThemeEditorDialog(theme, self)
            dialog.name_edit.setText(f"{theme.name} (Custom)")
            
            if dialog.exec_():
                new_theme = dialog.get_theme()
                self.theme_manager.add_theme(new_theme)
                self._update_theme_list()
                self._update_theme_previews()
                
                self.theme_manager.set_theme(new_theme.name)
            
            return
        
        dialog = ThemeEditorDialog(theme, self)
        if dialog.exec_():
            edited_theme = dialog.get_theme()
            
            self.theme_manager.remove_theme(theme_name)
            
            self.theme_manager.add_theme(edited_theme)
            
            self._update_theme_list()
            self._update_theme_previews()
            
            self.theme_manager.set_theme(edited_theme.name)
    
    def _create_theme(self):
        """Create a new theme."""
        dialog = ThemeEditorDialog(None, self)
        if dialog.exec_():
            theme = dialog.get_theme()
            self.theme_manager.add_theme(theme)
            
            self._update_theme_list()
            self._update_theme_previews()
            
            self.theme_manager.set_theme(theme.name)
    
    def _delete_theme(self):
        """Delete the current theme."""
        theme_name = self.theme_combo.currentData()
        if not theme_name:
            return
        
        if theme_name in ["Dark Theme", "Light Theme", "Blue Theme", "Green Theme"]:
            return
        
        self.theme_manager.remove_theme(theme_name)
        
        self._update_theme_list()
        self._update_theme_previews()

"""
Smart card UI components for the Knowledge Mesh Desktop application.

This module provides UI components for displaying smart cards and daily plans
with a dark theme and glowing elements.
"""

import os
import sys
import math
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Callable

from PyQt5.QtCore import Qt, QSize, QRect, QPoint, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush, QPen, QLinearGradient, QRadialGradient, QPainterPath, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QFrame, QGraphicsDropShadowEffect, QStackedWidget
)

from src.models.smart_card import SmartCard, DailyPlan, CardType, CardPriority, CardStatus
from src.services.daily_planner import DailyPlannerService


BACKGROUND_COLOR = QColor(18, 18, 24)
CARD_BACKGROUND_COLOR = QColor(28, 28, 36, 180)  # Semi-transparent for glass effect
CARD_BORDER_COLOR = QColor(45, 45, 60)
TEXT_COLOR = QColor(220, 220, 230)
ACCENT_COLOR = QColor(0, 210, 255)  # Teal/blue for glowing elements
SECONDARY_ACCENT_COLOR = QColor(120, 80, 255)  # Purple for secondary accents
CRITICAL_COLOR = QColor(255, 80, 80)
HIGH_COLOR = QColor(255, 160, 0)
MEDIUM_COLOR = QColor(0, 180, 180)
LOW_COLOR = QColor(0, 160, 255)
INFO_COLOR = QColor(160, 160, 255)

CARD_WIDTH = 320
CARD_HEIGHT = 180
CARD_RADIUS = 12
CARD_MARGIN = 16
CARD_PADDING = 12

HOVER_ANIMATION_DURATION = 200
EXPAND_ANIMATION_DURATION = 300


class GlowEffect(QGraphicsDropShadowEffect):
    """Custom glow effect for UI elements."""
    
    def __init__(self, color=ACCENT_COLOR, blur_radius=15, x_offset=0, y_offset=0, parent=None):
        """
        Initialize the glow effect.
        
        Args:
            color: The color of the glow
            blur_radius: The radius of the blur
            x_offset: The x offset of the shadow
            y_offset: The y offset of the shadow
            parent: The parent widget
        """
        super().__init__(parent)
        self.setColor(color)
        self.setBlurRadius(blur_radius)
        self.setXOffset(x_offset)
        self.setYOffset(y_offset)


class SmartCardWidget(QFrame):
    """Widget for displaying a smart card."""
    
    def __init__(self, card: SmartCard, on_action: Callable[[str, SmartCard, Dict], None] = None, parent=None):
        """
        Initialize the smart card widget.
        
        Args:
            card: The smart card to display
            on_action: Callback for card actions
            parent: The parent widget
        """
        super().__init__(parent)
        self.card = card
        self.on_action = on_action
        self.expanded = False
        self.hovered = False
        
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setObjectName("smartCard")
        self.setMouseTracking(True)
        
        self.setStyleSheet(f"""
            QFrame#smartCard {{
                background-color: rgba(28, 28, 36, 180);
                border-radius: {CARD_RADIUS}px;
                border: 1px solid rgba(45, 45, 60, 180);
            }}
        """)
        
        self.glow_effect = GlowEffect(self.get_priority_color(), 20, 0, 0, self)
        self.setGraphicsEffect(self.glow_effect)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        self.main_layout.setSpacing(8)
        
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(8)
        
        self.type_indicator = QLabel()
        self.type_indicator.setFixedSize(24, 24)
        self.type_indicator.setStyleSheet(f"""
            background-color: {self.get_priority_color().name()};
            border-radius: 12px;
        """)
        self.header_layout.addWidget(self.type_indicator)
        
        self.title_label = QLabel(card.title)
        self.title_label.setStyleSheet(f"""
            color: {TEXT_COLOR.name()};
            font-size: 14px;
            font-weight: bold;
        """)
        self.title_label.setWordWrap(True)
        self.header_layout.addWidget(self.title_label, 1)
        
        self.priority_indicator = QLabel()
        self.priority_indicator.setFixedSize(16, 16)
        self.priority_indicator.setStyleSheet(f"""
            background-color: {self.get_priority_color().name()};
            border-radius: 8px;
        """)
        self.header_layout.addWidget(self.priority_indicator)
        
        self.main_layout.addLayout(self.header_layout)
        
        self.description_label = QLabel(card.description)
        self.description_label.setStyleSheet(f"""
            color: {TEXT_COLOR.name()};
            font-size: 12px;
        """)
        self.description_label.setWordWrap(True)
        self.main_layout.addWidget(self.description_label, 1)
        
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setSpacing(8)
        
        self.action_buttons = []
        for action in card.actions:
            button = QPushButton(action.get("name", "Action"))
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(0, 210, 255, 40);
                    color: {TEXT_COLOR.name()};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: rgba(0, 210, 255, 80);
                }}
                QPushButton:pressed {{
                    background-color: rgba(0, 210, 255, 120);
                }}
            """)
            button.clicked.connect(lambda checked, a=action: self.handle_action(a))
            self.footer_layout.addWidget(button)
            self.action_buttons.append(button)
        
        self.footer_layout.addStretch(1)
        
        timestamp_text = f"Updated: {card.updated_at.strftime('%H:%M')}"
        if card.due_at:
            timestamp_text = f"Due: {card.due_at.strftime('%H:%M')}"
        
        self.timestamp_label = QLabel(timestamp_text)
        self.timestamp_label.setStyleSheet(f"""
            color: rgba(220, 220, 230, 120);
            font-size: 10px;
        """)
        self.footer_layout.addWidget(self.timestamp_label)
        
        self.main_layout.addLayout(self.footer_layout)
        
        self.hover_animation = QPropertyAnimation(self.glow_effect, b"blurRadius")
        self.hover_animation.setDuration(HOVER_ANIMATION_DURATION)
        self.hover_animation.setEasingCurve(QEasingCurve.InOutQuad)
    
    def get_priority_color(self) -> QColor:
        """Get the color for the card's priority."""
        if self.card.priority == CardPriority.CRITICAL:
            return CRITICAL_COLOR
        elif self.card.priority == CardPriority.HIGH:
            return HIGH_COLOR
        elif self.card.priority == CardPriority.MEDIUM:
            return MEDIUM_COLOR
        elif self.card.priority == CardPriority.LOW:
            return LOW_COLOR
        else:  # INFO
            return INFO_COLOR
    
    def handle_action(self, action: Dict[str, Any]):
        """
        Handle a card action.
        
        Args:
            action: The action to handle
        """
        if self.on_action:
            self.on_action(action.get("type", "unknown"), self.card, action)
    
    def enterEvent(self, event):
        """Handle mouse enter event."""
        self.hovered = True
        self.hover_animation.setStartValue(20)
        self.hover_animation.setEndValue(30)
        self.hover_animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave event."""
        self.hovered = False
        self.hover_animation.setStartValue(30)
        self.hover_animation.setEndValue(20)
        self.hover_animation.start()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        """Custom paint event for glass effect."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(QRect(0, 0, self.width(), self.height()), CARD_RADIUS, CARD_RADIUS)
        
        painter.setOpacity(0.7)
        painter.fillPath(path, QBrush(CARD_BACKGROUND_COLOR))
        
        pen = QPen(CARD_BORDER_COLOR)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)
        
        if self.hovered:
            painter.setOpacity(0.2)
            glow_gradient = QRadialGradient(
                QPoint(self.width() - 16, 16),
                40
            )
            glow_gradient.setColorAt(0, self.get_priority_color())
            glow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
            painter.fillPath(path, QBrush(glow_gradient))
        
        super().paintEvent(event)


class DailyPlanWidget(QWidget):
    """Widget for displaying a daily plan."""
    
    def __init__(self, planner_service: DailyPlannerService, parent=None):
        """
        Initialize the daily plan widget.
        
        Args:
            planner_service: The daily planner service
            parent: The parent widget
        """
        super().__init__(parent)
        self.planner_service = planner_service
        self.current_plan = None
        self.current_date = date.today()
        
        self.setObjectName("dailyPlan")
        self.setStyleSheet(f"""
            QWidget#dailyPlan {{
                background-color: {BACKGROUND_COLOR.name()};
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(16)
        
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(8)
        
        self.title_label = QLabel("Daily Plan")
        self.title_label.setStyleSheet(f"""
            color: {TEXT_COLOR.name()};
            font-size: 24px;
            font-weight: bold;
        """)
        self.header_layout.addWidget(self.title_label)
        
        self.date_label = QLabel(self.current_date.strftime("%B %d, %Y"))
        self.date_label.setStyleSheet(f"""
            color: {ACCENT_COLOR.name()};
            font-size: 18px;
            font-weight: bold;
        """)
        self.header_layout.addWidget(self.date_label)
        
        self.header_layout.addStretch(1)
        
        self.prev_button = QPushButton("◀")
        self.prev_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(0, 210, 255, 40);
                color: {TEXT_COLOR.name()};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 210, 255, 80);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 210, 255, 120);
            }}
        """)
        self.prev_button.clicked.connect(self.show_previous_day)
        self.header_layout.addWidget(self.prev_button)
        
        self.today_button = QPushButton("Today")
        self.today_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(0, 210, 255, 40);
                color: {TEXT_COLOR.name()};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 210, 255, 80);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 210, 255, 120);
            }}
        """)
        self.today_button.clicked.connect(self.show_today)
        self.header_layout.addWidget(self.today_button)
        
        self.next_button = QPushButton("▶")
        self.next_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(0, 210, 255, 40);
                color: {TEXT_COLOR.name()};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 210, 255, 80);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 210, 255, 120);
            }}
        """)
        self.next_button.clicked.connect(self.show_next_day)
        self.header_layout.addWidget(self.next_button)
        
        self.main_layout.addLayout(self.header_layout)
        
        self.tabs_layout = QHBoxLayout()
        self.tabs_layout.setSpacing(0)
        
        self.all_tab = QPushButton("All")
        self.all_tab.setCheckable(True)
        self.all_tab.setChecked(True)
        self.all_tab.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_COLOR.name()};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 8px 16px;
                font-size: 14px;
            }}
            QPushButton:checked {{
                border-bottom: 2px solid {ACCENT_COLOR.name()};
                color: {ACCENT_COLOR.name()};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 10);
            }}
        """)
        self.all_tab.clicked.connect(lambda: self.switch_tab("all"))
        self.tabs_layout.addWidget(self.all_tab)
        
        self.documents_tab = QPushButton("Documents")
        self.documents_tab.setCheckable(True)
        self.documents_tab.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_COLOR.name()};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 8px 16px;
                font-size: 14px;
            }}
            QPushButton:checked {{
                border-bottom: 2px solid {ACCENT_COLOR.name()};
                color: {ACCENT_COLOR.name()};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 10);
            }}
        """)
        self.documents_tab.clicked.connect(lambda: self.switch_tab("documents"))
        self.tabs_layout.addWidget(self.documents_tab)
        
        self.insights_tab = QPushButton("Insights")
        self.insights_tab.setCheckable(True)
        self.insights_tab.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_COLOR.name()};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 8px 16px;
                font-size: 14px;
            }}
            QPushButton:checked {{
                border-bottom: 2px solid {ACCENT_COLOR.name()};
                color: {ACCENT_COLOR.name()};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 10);
            }}
        """)
        self.insights_tab.clicked.connect(lambda: self.switch_tab("insights"))
        self.tabs_layout.addWidget(self.insights_tab)
        
        self.signatures_tab = QPushButton("Signatures")
        self.signatures_tab.setCheckable(True)
        self.signatures_tab.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_COLOR.name()};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 8px 16px;
                font-size: 14px;
            }}
            QPushButton:checked {{
                border-bottom: 2px solid {ACCENT_COLOR.name()};
                color: {ACCENT_COLOR.name()};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 10);
            }}
        """)
        self.signatures_tab.clicked.connect(lambda: self.switch_tab("signatures"))
        self.tabs_layout.addWidget(self.signatures_tab)
        
        self.tabs_layout.addStretch(1)
        
        self.main_layout.addLayout(self.tabs_layout)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: rgba(0, 0, 0, 0);
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(0, 210, 255, 80);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.content_widget = QWidget()
        self.content_widget.setObjectName("contentWidget")
        self.content_widget.setStyleSheet("""
            QWidget#contentWidget {
                background-color: transparent;
            }
        """)
        
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(CARD_MARGIN)
        
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area, 1)
        
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_plan)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
        self.refresh_plan()
    
    async def refresh_plan(self):
        """Refresh the current plan."""
        if self.current_date == date.today():
            self.current_plan = await self.planner_service.get_current_plan()
        else:
            self.current_plan = await self.planner_service.get_plan_for_date(self.current_date)
        
        self.update_ui()
    
    def update_ui(self):
        """Update the UI with the current plan."""
        self.date_label.setText(self.current_date.strftime("%B %d, %Y"))
        
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if self.current_plan:
            cards = self.current_plan.cards
            
            if hasattr(self, "current_tab") and self.current_tab != "all":
                if self.current_tab == "documents":
                    cards = [card for card in cards if card.card_type in [CardType.DOCUMENT_REMINDER, CardType.SIMILAR_DOCUMENTS]]
                elif self.current_tab == "insights":
                    cards = [card for card in cards if card.card_type == CardType.KNOWLEDGE_INSIGHT]
                elif self.current_tab == "signatures":
                    cards = [card for card in cards if card.card_type == CardType.SIGNATURE_REMINDER]
            
            cards.sort(key=lambda c: (
                0 if c.is_active() else 1,
                0 if c.priority == CardPriority.CRITICAL else
                1 if c.priority == CardPriority.HIGH else
                2 if c.priority == CardPriority.MEDIUM else
                3 if c.priority == CardPriority.LOW else 4,
                c.created_at
            ))
            
            for card in cards:
                card_widget = SmartCardWidget(card, self.handle_card_action)
                self.content_layout.addWidget(card_widget)
            
            self.content_layout.addStretch(1)
        else:
            empty_label = QLabel("No cards for this day")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {TEXT_COLOR.name()};
                font-size: 16px;
                padding: 32px;
            """)
            self.content_layout.addWidget(empty_label)
            self.content_layout.addStretch(1)
    
    def switch_tab(self, tab_name: str):
        """
        Switch to a different tab.
        
        Args:
            tab_name: The name of the tab to switch to
        """
        self.current_tab = tab_name
        
        self.all_tab.setChecked(tab_name == "all")
        self.documents_tab.setChecked(tab_name == "documents")
        self.insights_tab.setChecked(tab_name == "insights")
        self.signatures_tab.setChecked(tab_name == "signatures")
        
        self.update_ui()
    
    def show_previous_day(self):
        """Show the previous day's plan."""
        self.current_date = self.current_date - timedelta(days=1)
        self.refresh_plan()
    
    def show_next_day(self):
        """Show the next day's plan."""
        next_date = self.current_date + timedelta(days=1)
        if next_date <= date.today():
            self.current_date = next_date
            self.refresh_plan()
    
    def show_today(self):
        """Show today's plan."""
        self.current_date = date.today()
        self.refresh_plan()
    
    async def handle_card_action(self, action_type: str, card: SmartCard, action: Dict[str, Any]):
        """
        Handle a card action.
        
        Args:
            action_type: The type of action
            card: The card the action was performed on
            action: The action data
        """
        if action_type == "dismiss_card":
            await self.planner_service.dismiss_card(card.id)
            self.refresh_plan()
        elif action_type == "complete_card":
            await self.planner_service.complete_card(card.id)
            self.refresh_plan()
        elif action_type == "open_document":
            document_id = action.get("document_id")
            if document_id and "document_processor" in self.planner_service.services:
                document_processor = self.planner_service.services["document_processor"]
                await document_processor.open_document(document_id)
        elif action_type == "sign_document":
            signature_request_id = action.get("signature_request_id")
            if signature_request_id and "docusign_integration" in self.planner_service.services:
                docusign_integration = self.planner_service.services["docusign_integration"]
                await docusign_integration.open_signature_request(signature_request_id)
        elif action_type == "explore_insight":
            insight_id = action.get("insight_id")
            if insight_id and "knowledge_mesh" in self.planner_service.services:
                knowledge_mesh = self.planner_service.services["knowledge_mesh"]
                await knowledge_mesh.explore_insight(insight_id)


class KnowledgeMeshVisualizerWidget(QWidget):
    """Widget for visualizing the knowledge mesh with glowing connections."""
    
    def __init__(self, knowledge_mesh_service, parent=None):
        """
        Initialize the knowledge mesh visualizer widget.
        
        Args:
            knowledge_mesh_service: The knowledge mesh service
            parent: The parent widget
        """
        super().__init__(parent)
        self.knowledge_mesh_service = knowledge_mesh_service
        self.nodes = []
        self.edges = []
        self.selected_node = None
        self.hovered_node = None
        self.dragging = False
        self.drag_start = None
        self.offset = QPoint(0, 0)
        self.scale = 1.0
        
        self.setObjectName("knowledgeMeshVisualizer")
        self.setStyleSheet(f"""
            QWidget#knowledgeMeshVisualizer {{
                background-color: {BACKGROUND_COLOR.name()};
            }}
        """)
        self.setMouseTracking(True)
        
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_mesh)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update)
        self.animation_timer.start(50)  # Update every 50ms
        
        self.animation_time = 0
        
        self.refresh_mesh()
    
    async def refresh_mesh(self):
        """Refresh the knowledge mesh visualization."""
        if not self.knowledge_mesh_service:
            return
        
        self.nodes = await self.knowledge_mesh_service.get_visualization_nodes()
        self.edges = await self.knowledge_mesh_service.get_visualization_edges()
        
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event for the visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(self.rect(), BACKGROUND_COLOR)
        
        painter.translate(self.width() / 2 + self.offset.x(), self.height() / 2 + self.offset.y())
        painter.scale(self.scale, self.scale)
        
        for edge in self.edges:
            source_node = next((n for n in self.nodes if n["id"] == edge["source"]), None)
            target_node = next((n for n in self.nodes if n["id"] == edge["target"]), None)
            
            if source_node and target_node:
                source_pos = QPoint(source_node["x"], source_node["y"])
                target_pos = QPoint(target_node["x"], target_node["y"])
                
                self.draw_edge(painter, source_pos, target_pos, edge["weight"], edge["type"])
        
        for node in self.nodes:
            pos = QPoint(node["x"], node["y"])
            
            self.draw_node(painter, pos, node["size"], node["type"], node["id"] == self.selected_node, node["id"] == self.hovered_node)
    
    def draw_edge(self, painter, source_pos, target_pos, weight, edge_type):
        """
        Draw an edge between two nodes.
        
        Args:
            painter: The QPainter to use
            source_pos: The position of the source node
            target_pos: The position of the target node
            weight: The weight of the edge
            edge_type: The type of the edge
        """
        if edge_type == "semantic":
            edge_color = ACCENT_COLOR
        elif edge_type == "citation":
            edge_color = SECONDARY_ACCENT_COLOR
        else:
            edge_color = QColor(160, 160, 200)
        
        edge_width = max(1, min(5, weight * 5))
        
        pen = QPen(edge_color)
        pen.setWidth(edge_width)
        painter.setPen(pen)
        
        painter.drawLine(source_pos, target_pos)
        
        glow_pen = QPen(QColor(edge_color.red(), edge_color.green(), edge_color.blue(), 40))
        glow_pen.setWidth(edge_width + 4)
        painter.setPen(glow_pen)
        painter.drawLine(source_pos, target_pos)
        
        pulse_opacity = (math.sin(self.animation_time * 0.1 + (source_pos.x() + target_pos.x()) * 0.01) + 1) * 0.3
        pulse_pen = QPen(QColor(edge_color.red(), edge_color.green(), edge_color.blue(), int(pulse_opacity * 255)))
        pulse_pen.setWidth(edge_width + 8)
        painter.setPen(pulse_pen)
        painter.drawLine(source_pos, target_pos)
    
    def draw_node(self, painter, pos, size, node_type, selected, hovered):
        """
        Draw a node.
        
        Args:
            painter: The QPainter to use
            pos: The position of the node
            size: The size of the node
            node_type: The type of the node
            selected: Whether the node is selected
            hovered: Whether the node is hovered
        """
        if node_type == "document":
            node_color = ACCENT_COLOR
        elif node_type == "concept":
            node_color = SECONDARY_ACCENT_COLOR
        else:
            node_color = QColor(160, 160, 200)
        
        radius = max(5, min(20, size * 10))
        
        if selected or hovered:
            glow_radius = radius * 2
            glow_gradient = QRadialGradient(pos, glow_radius)
            glow_color = QColor(node_color)
            glow_color.setAlpha(100)
            glow_gradient.setColorAt(0, glow_color)
            glow_color.setAlpha(0)
            glow_gradient.setColorAt(1, glow_color)
            painter.setBrush(glow_gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(pos, glow_radius, glow_radius)
        
        painter.setBrush(QBrush(node_color))
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        painter.drawEllipse(pos, radius, radius)
        
        pulse_opacity = (math.sin(self.animation_time * 0.1 + pos.x() * 0.01) + 1) * 0.3
        pulse_color = QColor(node_color)
        pulse_color.setAlpha(int(pulse_opacity * 255))
        pulse_gradient = QRadialGradient(pos, radius * 1.5)
        pulse_gradient.setColorAt(0, pulse_color)
        pulse_color.setAlpha(0)
        pulse_gradient.setColorAt(1, pulse_color)
        painter.setBrush(pulse_gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(pos, radius * 1.5, radius * 1.5)
    
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.LeftButton:
            for node in self.nodes:
                node_pos = QPoint(node["x"], node["y"])
                node_pos = self.transform_point(node_pos)
                
                if (node_pos - event.pos()).manhattanLength() < node["size"] * 10 * self.scale:
                    self.selected_node = node["id"]
                    self.update()
                    return
            
            self.dragging = True
            self.drag_start = event.pos()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release event."""
        if event.button() == Qt.LeftButton:
            self.dragging = False
    
    def mouseMoveEvent(self, event):
        """Handle mouse move event."""
        if self.dragging:
            delta = event.pos() - self.drag_start
            self.offset += delta
            self.drag_start = event.pos()
            self.update()
        else:
            self.hovered_node = None
            for node in self.nodes:
                node_pos = QPoint(node["x"], node["y"])
                node_pos = self.transform_point(node_pos)
                
                if (node_pos - event.pos()).manhattanLength() < node["size"] * 10 * self.scale:
                    self.hovered_node = node["id"]
                    self.update()
                    break
    
    def wheelEvent(self, event):
        """Handle mouse wheel event for zooming."""
        zoom_factor = 1.1
        
        if event.angleDelta().y() > 0:
            self.scale *= zoom_factor
        else:
            self.scale /= zoom_factor
        
        self.scale = max(0.1, min(5.0, self.scale))
        
        self.update()
    
    def transform_point(self, point):
        """
        Transform a point from world coordinates to screen coordinates.
        
        Args:
            point: The point to transform
            
        Returns:
            The transformed point
        """
        return QPoint(
            int(point.x() * self.scale + self.width() / 2 + self.offset.x()),
            int(point.y() * self.scale + self.height() / 2 + self.offset.y())
        )
    
    def timerEvent(self, event):
        """Handle timer event for animation."""
        if event.timerId() == self.animation_timer.timerId():
            self.animation_time += 1
            self.update()

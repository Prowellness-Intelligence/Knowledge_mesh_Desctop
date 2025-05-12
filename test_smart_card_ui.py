"""
Tests for the smart card UI components.

This module provides tests for the smart card UI components.
"""

import sys
import os
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtTest import QTest

from src.models.smart_card import SmartCard, DailyPlan, CardType, CardPriority, CardStatus
from src.services.daily_planner import DailyPlannerService
from src.ui.smart_card_ui import SmartCardWidget, DailyPlanWidget, KnowledgeMeshVisualizerWidget


app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestSmartCardUI:
    """Tests for the smart card UI components."""
    
    def setup_method(self):
        """Set up the test environment."""
        self.window = QMainWindow()
        self.window.setGeometry(100, 100, 800, 600)
        
        self.central_widget = QWidget()
        self.window.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        
        self.test_card = SmartCard.create(
            title="Test Card",
            description="This is a test card for UI testing",
            card_type=CardType.DOCUMENT_REMINDER,
            priority=CardPriority.MEDIUM,
            actions=[
                {
                    "name": "Open Document",
                    "type": "open_document",
                    "document_id": "test-doc-1",
                },
                {
                    "name": "Dismiss",
                    "type": "dismiss_card",
                },
            ],
        )
        
        self.test_plan = DailyPlan.create(
            date=date.today(),
            cards=[self.test_card],
        )
        
        self.mock_planner_service = MagicMock(spec=DailyPlannerService)
        self.mock_planner_service.get_current_plan = MagicMock(return_value=self.test_plan)
        self.mock_planner_service.get_plan_for_date = MagicMock(return_value=self.test_plan)
        
        self.mock_knowledge_mesh_service = MagicMock()
        self.mock_knowledge_mesh_service.get_visualization_nodes = MagicMock(return_value=[
            {"id": "node1", "x": 0, "y": 0, "size": 1, "type": "document"},
            {"id": "node2", "x": 100, "y": 100, "size": 1, "type": "document"},
        ])
        self.mock_knowledge_mesh_service.get_visualization_edges = MagicMock(return_value=[
            {"source": "node1", "target": "node2", "weight": 0.8, "type": "semantic"},
        ])
    
    def test_smart_card_widget(self):
        """Test the SmartCardWidget."""
        card_widget = SmartCardWidget(self.test_card)
        self.layout.addWidget(card_widget)
        
        self.window.show()
        
        assert card_widget is not None
        assert card_widget.card == self.test_card
        assert card_widget.title_label.text() == "Test Card"
        assert card_widget.description_label.text() == "This is a test card for UI testing"
        
        assert len(card_widget.action_buttons) == 2
        assert card_widget.action_buttons[0].text() == "Open Document"
        assert card_widget.action_buttons[1].text() == "Dismiss"
        
        card_widget.enterEvent(None)
        assert card_widget.hovered is True
        
        card_widget.leaveEvent(None)
        assert card_widget.hovered is False
        
        self.window.hide()
    
    def test_daily_plan_widget(self):
        """Test the DailyPlanWidget."""
        plan_widget = DailyPlanWidget(self.mock_planner_service)
        self.layout.addWidget(plan_widget)
        
        self.window.show()
        
        assert plan_widget is not None
        assert plan_widget.planner_service == self.mock_planner_service
        assert plan_widget.current_date == date.today()
        assert plan_widget.title_label.text() == "Daily Plan"
        assert plan_widget.date_label.text() == date.today().strftime("%B %d, %Y")
        
        plan_widget.switch_tab("documents")
        assert plan_widget.current_tab == "documents"
        assert plan_widget.documents_tab.isChecked() is True
        
        plan_widget.switch_tab("all")
        assert plan_widget.current_tab == "all"
        assert plan_widget.all_tab.isChecked() is True
        
        plan_widget.show_previous_day()
        assert plan_widget.current_date == date.today() - timedelta(days=1)
        
        plan_widget.show_today()
        assert plan_widget.current_date == date.today()
        
        self.window.hide()
    
    def test_knowledge_mesh_visualizer_widget(self):
        """Test the KnowledgeMeshVisualizerWidget."""
        visualizer_widget = KnowledgeMeshVisualizerWidget(self.mock_knowledge_mesh_service)
        self.layout.addWidget(visualizer_widget)
        
        self.window.show()
        
        assert visualizer_widget is not None
        assert visualizer_widget.knowledge_mesh_service == self.mock_knowledge_mesh_service
        assert len(visualizer_widget.nodes) == 2
        assert len(visualizer_widget.edges) == 1
        
        event = MagicMock()
        event.button.return_value = Qt.LeftButton
        event.pos.return_value = QPoint(400, 300)  # Center of the widget
        
        visualizer_widget.mousePressEvent(event)
        assert visualizer_widget.selected_node == "node1"  # The node at the center
        
        drag_event = MagicMock()
        drag_event.button.return_value = Qt.LeftButton
        drag_event.pos.return_value = QPoint(410, 310)  # Moved 10 pixels
        
        visualizer_widget.mousePressEvent(event)
        visualizer_widget.mouseMoveEvent(drag_event)
        assert visualizer_widget.dragging is True
        assert visualizer_widget.offset == QPoint(10, 10)
        
        zoom_event = MagicMock()
        zoom_event.angleDelta().y.return_value = 120  # Zoom in
        
        visualizer_widget.wheelEvent(zoom_event)
        assert visualizer_widget.scale > 1.0
        
        self.window.hide()


if __name__ == "__main__":
    test = TestSmartCardUI()
    test.setup_method()
    test.test_smart_card_widget()
    test.test_daily_plan_widget()
    test.test_knowledge_mesh_visualizer_widget()
    
    print("All tests passed!")

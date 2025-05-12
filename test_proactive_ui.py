"""
Test file for the Proactive UI components of the Knowledge Mesh Desktop application.

This module provides tests for the Work Pattern Monitor, Contextual Awareness Engine,
Knowledge Mesh Visualizer, and Proactive Notification System.
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.core.config import Config
from src.core.events import EventType, Event, event_bus
from src.models.context import Context, ContextType, FocusLevel
from src.models.work_pattern import WorkPattern, WorkPatternType, WorkPatternConfidence
from src.services.work_pattern_monitor import WorkPatternMonitorService
from src.services.contextual_awareness import ContextualAwarenessEngine
from src.services.proactive_notification import ProactiveNotificationSystem


class TestWorkPatternMonitor(unittest.TestCase):
    """Test the Work Pattern Monitor service."""
    
    def setUp(self):
        """Set up the test environment."""
        self.config = Config({
            "app.data_dir": "./test_data",
            "work_pattern_monitor.enabled": True,
            "work_pattern_monitor.min_confidence": 0.3,
            "work_pattern_monitor.max_patterns": 100,
            "work_pattern_monitor.detection_interval": 1,
            "work_pattern_monitor.max_recent_events": 100,
        })
        
        self.service = WorkPatternMonitorService(self.config)
        
        os.makedirs("./test_data/patterns", exist_ok=True)
    
    def tearDown(self):
        """Clean up the test environment."""
        import shutil
        if os.path.exists("./test_data"):
            shutil.rmtree("./test_data")
    
    def test_initialization(self):
        """Test service initialization."""
        self.assertEqual(self.service.config, self.config)
        self.assertFalse(self.service.is_running)
        self.assertEqual(self.service.patterns, {})
        self.assertEqual(self.service.recent_events, [])
        self.assertEqual(self.service.max_recent_events, 100)
        self.assertEqual(self.service.pattern_detection_interval, 1)
        self.assertIsNone(self.service.pattern_detection_task)
    
    def test_record_event(self):
        """Test recording events."""
        self.service._record_event("TEST_EVENT", {"test": "data"})
        
        self.assertEqual(len(self.service.recent_events), 1)
        self.assertEqual(self.service.recent_events[0]["event_type"], "TEST_EVENT")
        self.assertEqual(self.service.recent_events[0]["data"], {"test": "data"})
        self.assertIn("timestamp", self.service.recent_events[0])
    
    def test_get_patterns(self):
        """Test getting patterns."""
        pattern1 = WorkPattern(
            id="test_pattern_1",
            type=WorkPatternType.DOCUMENT_ACCESS,
            data={"document_id": "doc1"},
            confidence=0.5,
        )
        
        pattern2 = WorkPattern(
            id="test_pattern_2",
            type=WorkPatternType.TIME_OF_DAY,
            data={"hour": 10},
            confidence=0.7,
        )
        
        self.service.patterns = {
            "test_pattern_1": pattern1,
            "test_pattern_2": pattern2,
        }
        
        loop = asyncio.get_event_loop()
        patterns = loop.run_until_complete(self.service.get_patterns())
        
        self.assertEqual(len(patterns), 2)
        self.assertIn(pattern1, patterns)
        self.assertIn(pattern2, patterns)
        
        patterns = loop.run_until_complete(self.service.get_patterns(pattern_type=WorkPatternType.DOCUMENT_ACCESS))
        
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0], pattern1)
        
        patterns = loop.run_until_complete(self.service.get_patterns(min_confidence=0.6))
        
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0], pattern2)
    
    def test_generate_insights(self):
        """Test generating insights."""
        pattern1 = WorkPattern(
            id="test_pattern_1",
            type=WorkPatternType.DOCUMENT_ACCESS,
            data={"document_id": "doc1"},
            confidence=0.5,
        )
        
        pattern2 = WorkPattern(
            id="test_pattern_2",
            type=WorkPatternType.TIME_OF_DAY,
            data={"hour": 10},
            confidence=0.7,
        )
        
        self.service.patterns = {
            "test_pattern_1": pattern1,
            "test_pattern_2": pattern2,
        }
        
        loop = asyncio.get_event_loop()
        insights = loop.run_until_complete(self.service.generate_insights())
        
        self.assertGreater(len(insights), 0)


class TestContextualAwareness(unittest.TestCase):
    """Test the Contextual Awareness Engine."""
    
    def setUp(self):
        """Set up the test environment."""
        self.config = Config({
            "app.data_dir": "./test_data",
            "contextual_awareness.enabled": True,
            "contextual_awareness.update_interval": 1,
            "contextual_awareness.max_history": 100,
            "contextual_awareness.idle_threshold": 300,
        })
        
        self.engine = ContextualAwarenessEngine(self.config)
        
        os.makedirs("./test_data/contexts", exist_ok=True)
    
    def tearDown(self):
        """Clean up the test environment."""
        import shutil
        if os.path.exists("./test_data"):
            shutil.rmtree("./test_data")
    
    def test_initialization(self):
        """Test engine initialization."""
        self.assertEqual(self.engine.config, self.config)
        self.assertFalse(self.engine.is_running)
        self.assertIsNone(self.engine.current_context)
        self.assertEqual(self.engine.context_history, [])
        self.assertEqual(self.engine.max_context_history, 100)
        self.assertEqual(self.engine.context_update_interval, 1)
        self.assertIsNone(self.engine.context_update_task)
    
    def test_create_initial_context(self):
        """Test creating the initial context."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.engine._create_initial_context())
        
        self.assertIsNotNone(self.engine.current_context)
        self.assertEqual(self.engine.current_context.type, ContextType.APPLICATION_CONTEXT)
        self.assertEqual(self.engine.current_context.focus_level, FocusLevel.INTERRUPTIBLE)
    
    def test_switch_context(self):
        """Test switching contexts."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.engine._create_initial_context())
        
        loop.run_until_complete(self.engine._switch_context(
            ContextType.DOCUMENT_FOCUS,
            {"document_id": "doc1"},
            FocusLevel.FOCUSED,
        ))
        
        self.assertIsNotNone(self.engine.current_context)
        self.assertEqual(self.engine.current_context.type, ContextType.DOCUMENT_FOCUS)
        self.assertEqual(self.engine.current_context.focus_level, FocusLevel.FOCUSED)
        self.assertEqual(self.engine.current_context.data, {"document_id": "doc1"})
        
        self.assertEqual(len(self.engine.context_history), 1)
        self.assertEqual(self.engine.context_history[0].type, ContextType.APPLICATION_CONTEXT)
    
    def test_is_interruption_appropriate(self):
        """Test checking if interruption is appropriate."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.engine._create_initial_context())
        
        is_appropriate = loop.run_until_complete(self.engine.is_interruption_appropriate())
        
        self.assertTrue(is_appropriate)
        
        loop.run_until_complete(self.engine._switch_context(
            ContextType.DOCUMENT_FOCUS,
            {"document_id": "doc1"},
            FocusLevel.HIGHLY_FOCUSED,
        ))
        
        is_appropriate = loop.run_until_complete(self.engine.is_interruption_appropriate())
        
        self.assertFalse(is_appropriate)


class TestProactiveNotification(unittest.TestCase):
    """Test the Proactive Notification System."""
    
    def setUp(self):
        """Set up the test environment."""
        self.config = Config({
            "app.data_dir": "./test_data",
            "proactive.enabled": True,
            "proactive.notification_interval": 1,
            "proactive.max_queue_size": 20,
            "proactive.max_notifications_per_day": 20,
            "security.level": "STANDARD",
            "security.sensitive_data_enabled": False,
            "security.sensitive_data_timeout": 300,
        })
        
        self.services = {
            "work_pattern_monitor": MagicMock(),
            "contextual_awareness": MagicMock(),
            "knowledge_mesh": MagicMock(),
            "document_processor": MagicMock(),
        }
        
        self.system = ProactiveNotificationSystem(self.config, self.services)
        
        os.makedirs("./test_data/notifications", exist_ok=True)
    
    def tearDown(self):
        """Clean up the test environment."""
        import shutil
        if os.path.exists("./test_data"):
            shutil.rmtree("./test_data")
    
    def test_initialization(self):
        """Test system initialization."""
        self.assertEqual(self.system.config, self.config)
        self.assertEqual(self.system.services, self.services)
        self.assertFalse(self.system.is_running)
        self.assertEqual(self.system.notification_queue, [])
        self.assertEqual(self.system.max_queue_size, 20)
        self.assertEqual(self.system.notification_interval, 1)
        self.assertIsNone(self.system.notification_task)
    
    def test_queue_notification(self):
        """Test queuing a notification."""
        self.system._queue_notification("TEST_NOTIFICATION", {"test": "data"})
        
        self.assertEqual(len(self.system.notification_queue), 1)
        self.assertEqual(self.system.notification_queue[0]["type"], "TEST_NOTIFICATION")
        self.assertEqual(self.system.notification_queue[0]["content"], {"test": "data"})
        self.assertIn("timestamp", self.system.notification_queue[0])
        self.assertIn("id", self.system.notification_queue[0])
        self.assertIn("is_sensitive", self.system.notification_queue[0])
        self.assertIn("security_level", self.system.notification_queue[0])
    
    def test_sensitive_data_handling(self):
        """Test handling of sensitive data."""
        self.system.sensitive_data_enabled = False
        
        self.system._queue_notification("TEST_NOTIFICATION", {"test": "data", "is_sensitive": True})
        
        self.assertEqual(len(self.system.notification_queue), 0)
        
        self.system.sensitive_data_enabled = True
        
        self.system._queue_notification("TEST_NOTIFICATION", {"test": "data", "is_sensitive": True})
        
        self.assertEqual(len(self.system.notification_queue), 1)
        self.assertEqual(self.system.notification_queue[0]["type"], "TEST_NOTIFICATION")
        self.assertEqual(self.system.notification_queue[0]["content"], {"test": "data", "is_sensitive": True})
        self.assertTrue(self.system.notification_queue[0]["is_sensitive"])
    
    def test_is_sensitive_document(self):
        """Test checking if a document is sensitive."""
        document = MagicMock()
        document.metadata = {}
        document.title = "Test Document"
        document.content = "This is a test document."
        
        is_sensitive = self.system._is_sensitive_document(document)
        
        self.assertFalse(is_sensitive)
        
        document.metadata = {"sensitive": True}
        
        is_sensitive = self.system._is_sensitive_document(document)
        
        self.assertTrue(is_sensitive)
        
        document.metadata = {}
        document.title = "Confidential Document"
        
        is_sensitive = self.system._is_sensitive_document(document)
        
        self.assertTrue(is_sensitive)
        
        document.title = "Test Document"
        document.content = "This is a private document with personal information."
        
        is_sensitive = self.system._is_sensitive_document(document)
        
        self.assertTrue(is_sensitive)


if __name__ == "__main__":
    unittest.main()

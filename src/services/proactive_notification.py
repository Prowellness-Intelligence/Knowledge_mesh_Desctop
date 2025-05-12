"""
Proactive Notification System for the Knowledge Mesh Desktop application.

This module provides a service for coordinating proactive notifications
based on work patterns, contextual awareness, and knowledge mesh insights.
"""

import asyncio
import logging
import os
import pickle
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus
from ..models.context import Context, ContextType, FocusLevel
from ..models.work_pattern import WorkPattern, WorkPatternType

logger = logging.getLogger(__name__)


class ProactiveNotificationSystem:
    """
    System for coordinating proactive notifications.
    
    This service coordinates between the work pattern monitor, contextual awareness
    engine, and knowledge mesh service to provide proactive notifications to the user.
    """
    
    def __init__(self, config: Config, services: Dict[str, Any]):
        """
        Initialize the proactive notification system.
        
        Args:
            config: Application configuration
            services: Application services
        """
        self.config = config
        self.services = services
        self.is_running = False
        self.notification_queue = []
        self.max_queue_size = 20
        self.notification_interval = 60  # seconds
        self.notification_task = None
        self.data_dir = Path(self.config.get("app.data_dir", "."))
        self.notifications_dir = self.data_dir / "notifications"
        self.security_level = "STANDARD"  # STANDARD, HIGH, VERY_HIGH
        self.sensitive_data_enabled = False
        self.sensitive_data_password = None
        self.sensitive_data_timeout = 300  # 5 minutes
        self.last_sensitive_data_access = 0
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.enabled = self.config.get("proactive.enabled", True)
        self.notification_interval = self.config.get("proactive.notification_interval", 60)
        self.max_queue_size = self.config.get("proactive.max_queue_size", 20)
        self.max_notifications_per_day = self.config.get("proactive.max_notifications_per_day", 20)
        self.notification_quiet_hours = self.config.get("proactive.quiet_hours", [])
        self.security_level = self.config.get("security.level", "STANDARD")
        self.sensitive_data_enabled = self.config.get("security.sensitive_data_enabled", False)
        self.sensitive_data_timeout = self.config.get("security.sensitive_data_timeout", 300)
    
    async def initialize(self):
        """Initialize the proactive notification system."""
        logger.info("Initializing proactive notification system")
        
        try:
            self.notifications_dir.mkdir(parents=True, exist_ok=True)
            
            event_bus.subscribe(EventType.WORK_PATTERN_UPDATED, self._on_work_pattern_updated)
            event_bus.subscribe(EventType.DOCUMENT_ADDED, self._on_document_added)
            event_bus.subscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
            event_bus.subscribe(EventType.UI_SETTINGS_CHANGED, self._on_settings_changed)
            
            logger.info("Proactive notification system initialized")
        except Exception as e:
            logger.error(f"Error initializing proactive notification system: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Start the proactive notification system."""
        logger.info("Starting proactive notification system")
        
        if not self.enabled:
            logger.info("Proactive notification system is disabled")
            return
        
        self.is_running = True
        
        self.notification_task = asyncio.create_task(self._notification_loop())
        
        logger.info("Proactive notification system started")
    
    async def stop(self):
        """Stop the proactive notification system."""
        logger.info("Stopping proactive notification system")
        
        self.is_running = False
        
        if self.notification_task:
            self.notification_task.cancel()
            try:
                await self.notification_task
            except asyncio.CancelledError:
                pass
            self.notification_task = None
        
        event_bus.unsubscribe(EventType.WORK_PATTERN_UPDATED, self._on_work_pattern_updated)
        event_bus.unsubscribe(EventType.DOCUMENT_ADDED, self._on_document_added)
        event_bus.unsubscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
        event_bus.unsubscribe(EventType.UI_SETTINGS_CHANGED, self._on_settings_changed)
        
        logger.info("Proactive notification system stopped")
    
    async def _notification_loop(self):
        """Run the notification loop."""
        try:
            while self.is_running:
                await asyncio.sleep(self.notification_interval)
                
                if not self.enabled:
                    continue
                
                try:
                    await self._check_for_notifications()
                except Exception as e:
                    logger.error(f"Error checking for notifications: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.debug("Notification loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in notification loop: {e}", exc_info=True)
    
    async def _check_for_notifications(self):
        """Check for notifications to send."""
        if not self.enabled:
            return
        
        current_hour = datetime.now().hour
        if current_hour in self.notification_quiet_hours:
            logger.debug(f"In quiet hours ({current_hour}), skipping notifications")
            return
        
        today = datetime.now().date()
        notifications_today = await self._count_notifications_for_day(today)
        
        if notifications_today >= self.max_notifications_per_day:
            logger.debug(f"Reached daily notification limit ({self.max_notifications_per_day}), skipping notifications")
            return
        
        if "contextual_awareness" in self.services:
            is_appropriate = await self.services["contextual_awareness"].is_interruption_appropriate()
            if not is_appropriate:
                logger.debug("Not appropriate to interrupt user, skipping notifications")
                return
        
        await self._generate_notifications()
        
        await self._send_next_notification()
    
    async def _count_notifications_for_day(self, day: datetime.date) -> int:
        """
        Count the number of notifications sent on a specific day.
        
        Args:
            day: The day to count notifications for
            
        Returns:
            The number of notifications sent on the specified day
        """
        count = 0
        
        for notification_file in self.notifications_dir.glob("*.pkl"):
            try:
                with open(notification_file, "rb") as f:
                    notification = pickle.load(f)
                    
                    if "timestamp" in notification:
                        notification_date = datetime.fromtimestamp(notification["timestamp"]).date()
                        if notification_date == day:
                            count += 1
            except Exception as e:
                logger.error(f"Error counting notification {notification_file}: {e}", exc_info=True)
        
        return count
    
    async def _generate_notifications(self):
        """Generate notifications based on work patterns, context, and knowledge mesh."""
        if "work_pattern_monitor" in self.services:
            await self._generate_work_pattern_notifications()
        
        if "contextual_awareness" in self.services and "knowledge_mesh" in self.services:
            await self._generate_document_suggestions()
        
        if "knowledge_mesh" in self.services:
            await self._generate_relationship_suggestions()
    
    async def _generate_work_pattern_notifications(self):
        """Generate notifications based on work patterns."""
        try:
            work_pattern_monitor = self.services["work_pattern_monitor"]
            
            patterns = await work_pattern_monitor.get_patterns(min_confidence=0.5)
            
            if not patterns:
                return
            
            insights = await work_pattern_monitor.generate_insights()
            
            for insight in insights:
                self._queue_notification(
                    "WORK_PATTERN_INSIGHT",
                    {
                        "insight": insight.get("message", ""),
                        "action": insight.get("action"),
                        "action_data": insight.get("action_data", {}),
                    },
                )
        except Exception as e:
            logger.error(f"Error generating work pattern notifications: {e}", exc_info=True)
    
    async def _generate_document_suggestions(self):
        """Generate document suggestions based on context and knowledge mesh."""
        try:
            contextual_awareness = self.services["contextual_awareness"]
            knowledge_mesh = self.services["knowledge_mesh"]
            
            current_context = await contextual_awareness.get_current_context()
            
            if not current_context:
                return
            
            relevant_docs = await contextual_awareness.get_relevant_documents()
            
            if not relevant_docs:
                return
            
            for doc_id in relevant_docs:
                related_docs = await knowledge_mesh.get_related_documents(doc_id)
                
                for related_doc in related_docs:
                    if related_doc.id in relevant_docs:
                        continue
                    
                    is_sensitive = self._is_sensitive_document(related_doc)
                    
                    if is_sensitive and not self.sensitive_data_enabled:
                        continue
                    
                    self._queue_notification(
                        "DOCUMENT_SUGGESTION",
                        {
                            "document_id": related_doc.id,
                            "document_title": related_doc.title,
                            "reason": f"Related to {doc_id}",
                            "is_sensitive": is_sensitive,
                        },
                    )
        except Exception as e:
            logger.error(f"Error generating document suggestions: {e}", exc_info=True)
    
    async def _generate_relationship_suggestions(self):
        """Generate relationship suggestions based on knowledge mesh."""
        try:
            knowledge_mesh = self.services["knowledge_mesh"]
            
            relationships = await knowledge_mesh.get_recent_relationships(limit=5)
            
            for relationship in relationships:
                source_doc = await self._get_document(relationship.source_id)
                target_doc = await self._get_document(relationship.target_id)
                
                if source_doc and target_doc:
                    is_sensitive = self._is_sensitive_document(source_doc) or self._is_sensitive_document(target_doc)
                    
                    if is_sensitive and not self.sensitive_data_enabled:
                        continue
                    
                    self._queue_notification(
                        "RELATIONSHIP_SUGGESTION",
                        {
                            "relationship_id": relationship.id,
                            "source_id": relationship.source_id,
                            "source_title": source_doc.title,
                            "target_id": relationship.target_id,
                            "target_title": target_doc.title,
                            "relationship_type": relationship.type.name,
                            "strength": relationship.strength,
                            "is_sensitive": is_sensitive,
                        },
                    )
        except Exception as e:
            logger.error(f"Error generating relationship suggestions: {e}", exc_info=True)
    
    async def _get_document(self, document_id: str):
        """
        Get a document by ID.
        
        Args:
            document_id: The document ID
            
        Returns:
            The document, or None if not found
        """
        if "document_processor" in self.services:
            return await self.services["document_processor"].get_document(document_id)
        return None
    
    def _is_sensitive_document(self, document) -> bool:
        """
        Check if a document contains sensitive information.
        
        Args:
            document: The document to check
            
        Returns:
            True if the document contains sensitive information, False otherwise
        """
        if not document:
            return False
        
        if document.metadata and document.metadata.get("sensitive", False):
            return True
        
        sensitive_keywords = ["confidential", "secret", "private", "sensitive", "personal"]
        if document.title and any(keyword in document.title.lower() for keyword in sensitive_keywords):
            return True
        
        if document.content:
            if "@" in document.content and "." in document.content:
                return True
            
            if any(c.isdigit() for c in document.content) and len([c for c in document.content if c.isdigit()]) >= 10:
                return True
            
            if any(keyword in document.content.lower() for keyword in sensitive_keywords):
                return True
        
        return False
    
    def _queue_notification(self, interaction_type: str, content: Dict[str, Any]):
        """
        Queue a notification.
        
        Args:
            interaction_type: The type of interaction
            content: The notification content
        """
        if not self.enabled:
            return
        
        is_sensitive = content.get("is_sensitive", False)
        
        if is_sensitive and not self.sensitive_data_enabled:
            return
        
        notification = {
            "id": str(uuid.uuid4()),
            "type": interaction_type,
            "content": content,
            "timestamp": time.time(),
            "is_sensitive": is_sensitive,
            "security_level": self.security_level,
        }
        
        self.notification_queue.append(notification)
        
        if len(self.notification_queue) > self.max_queue_size:
            self.notification_queue = self.notification_queue[-self.max_queue_size:]
        
        self._save_notification(notification)
    
    def _save_notification(self, notification: Dict[str, Any]):
        """
        Save a notification to disk.
        
        Args:
            notification: The notification to save
        """
        try:
            notification_file = self.notifications_dir / f"{notification['id']}.pkl"
            with open(notification_file, "wb") as f:
                pickle.dump(notification, f)
        except Exception as e:
            logger.error(f"Error saving notification: {e}", exc_info=True)
    
    async def _send_next_notification(self):
        """Send the next notification in the queue."""
        if not self.notification_queue:
            return
        
        notification = self.notification_queue.pop(0)
        
        is_sensitive = notification.get("is_sensitive", False)
        
        if is_sensitive and not self.sensitive_data_enabled:
            return
        
        if is_sensitive and not self._is_sensitive_data_access_valid():
            publish(
                EventType.AUTHENTICATION_REQUIRED,
                {
                    "reason": "Sensitive data access",
                    "callback_event": EventType.PROACTIVE_INTERACTION,
                    "callback_data": notification,
                },
            )
            return
        
        publish(
            EventType.PROACTIVE_INTERACTION,
            {
                "interaction_type": notification["type"],
                "content": notification["content"],
            },
        )
    
    def _is_sensitive_data_access_valid(self) -> bool:
        """
        Check if sensitive data access is valid.
        
        Returns:
            True if sensitive data access is valid, False otherwise
        """
        if not self.sensitive_data_enabled:
            return False
        
        if not self.sensitive_data_password:
            return False
        
        current_time = time.time()
        if current_time - self.last_sensitive_data_access > self.sensitive_data_timeout:
            return False
        
        return True
    
    async def authenticate_sensitive_data(self, password: str) -> bool:
        """
        Authenticate for sensitive data access.
        
        Args:
            password: The password to authenticate with
            
        Returns:
            True if authentication was successful, False otherwise
        """
        if not self.sensitive_data_enabled:
            return False
        
        if password and len(password) > 0:
            self.sensitive_data_password = password
            self.last_sensitive_data_access = time.time()
            return True
        
        return False
    
    def _on_work_pattern_updated(self, event):
        """
        Handle work pattern updated events.
        
        Args:
            event: The work pattern updated event
        """
        insight = event.data.get("insight")
        if insight:
            self._queue_notification(
                "WORK_PATTERN_INSIGHT",
                {
                    "insight": insight.get("message", ""),
                    "action": insight.get("action"),
                    "action_data": insight.get("action_data", {}),
                },
            )
    
    def _on_document_added(self, event):
        """
        Handle document added events.
        
        Args:
            event: The document added event
        """
        document_id = event.data.get("document_id")
        if document_id:
            asyncio.create_task(self._check_new_document(document_id))
    
    async def _check_new_document(self, document_id: str):
        """
        Check a new document for notifications.
        
        Args:
            document_id: The document ID
        """
        try:
            document = await self._get_document(document_id)
            
            if not document:
                return
            
            is_sensitive = self._is_sensitive_document(document)
            
            if is_sensitive and not self.sensitive_data_enabled:
                return
            
            self._queue_notification(
                "DOCUMENT_ADDED",
                {
                    "document_id": document_id,
                    "document_title": document.title,
                    "is_sensitive": is_sensitive,
                },
            )
        except Exception as e:
            logger.error(f"Error checking new document: {e}", exc_info=True)
    
    def _on_relationship_detected(self, event):
        """
        Handle relationship detected events.
        
        Args:
            event: The relationship detected event
        """
        relationship = event.data.get("relationship")
        if relationship:
            asyncio.create_task(self._check_new_relationship(relationship))
    
    async def _check_new_relationship(self, relationship):
        """
        Check a new relationship for notifications.
        
        Args:
            relationship: The relationship
        """
        try:
            source_doc = await self._get_document(relationship.source_id)
            target_doc = await self._get_document(relationship.target_id)
            
            if not source_doc or not target_doc:
                return
            
            is_sensitive = self._is_sensitive_document(source_doc) or self._is_sensitive_document(target_doc)
            
            if is_sensitive and not self.sensitive_data_enabled:
                return
            
            self._queue_notification(
                "RELATIONSHIP_DETECTED",
                {
                    "relationship_id": relationship.id,
                    "source_id": relationship.source_id,
                    "source_title": source_doc.title,
                    "target_id": relationship.target_id,
                    "target_title": target_doc.title,
                    "relationship_type": relationship.type.name,
                    "strength": relationship.strength,
                    "is_sensitive": is_sensitive,
                },
            )
        except Exception as e:
            logger.error(f"Error checking new relationship: {e}", exc_info=True)
    
    def _on_settings_changed(self, event):
        """
        Handle settings changed events.
        
        Args:
            event: The settings changed event
        """
        self._load_config()

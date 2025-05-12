"""
Proactive Service for the Knowledge Mesh Desktop application.

This module provides a service that monitors user behavior, detects patterns,
and proactively suggests relevant information at appropriate times.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus
from ..models.document import Document

logger = logging.getLogger(__name__)


class InteractionType(Enum):
    """Types of proactive interactions with the user."""
    
    DOCUMENT_SUGGESTION = auto()  # Suggest a relevant document
    RELATIONSHIP_INSIGHT = auto()  # Surface a relationship between documents
    WORK_PATTERN_INSIGHT = auto()  # Provide insight about work patterns
    FOCUS_REMINDER = auto()  # Remind user to focus on a task
    BREAK_REMINDER = auto()  # Remind user to take a break
    CALENDAR_REMINDER = auto()  # Remind user about calendar events
    EMAIL_NOTIFICATION = auto()  # Notify about important emails
    SEARCH_SUGGESTION = auto()  # Suggest a search query
    TASK_SUGGESTION = auto()  # Suggest a task to work on
    CUSTOM = auto()  # Custom interaction type


class UserState(Enum):
    """Possible states of the user."""
    
    FOCUSED = auto()  # User is focused on a task
    DISTRACTED = auto()  # User is distracted
    IDLE = auto()  # User is idle
    BUSY = auto()  # User is busy with many tasks
    RECEPTIVE = auto()  # User is receptive to suggestions
    UNRECEPTIVE = auto()  # User is not receptive to suggestions
    UNKNOWN = auto()  # User state is unknown


class ProactiveService:
    """
    Service for proactive interactions with the user.
    
    This service monitors user behavior, detects patterns, and proactively
    suggests relevant information at appropriate times.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the proactive service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.is_running = False
        self.user_state = UserState.UNKNOWN
        self.last_interaction_time = None
        self.interaction_history: List[Dict[str, Any]] = []
        self.work_pattern_model = None
        self.receptivity_model = None
        self.interaction_scheduler = None
        self.min_interaction_interval = timedelta(minutes=15)
        self.max_daily_interactions = 20
        self.daily_interaction_count = 0
        self.last_reset_day = datetime.now().day
        self.enabled = True
        self.monitoring_task = None
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.enabled = self.config.get(
            "proactive.enabled", True
        )
        
        self.min_interaction_interval = timedelta(minutes=self.config.get(
            "proactive.min_interaction_interval_minutes", 15
        ))
        
        self.max_daily_interactions = self.config.get(
            "proactive.max_daily_interactions", 20
        )
        
        self.work_pattern_learning_rate = self.config.get(
            "proactive.work_pattern_learning_rate", 0.1
        )
        
        self.receptivity_threshold = self.config.get(
            "proactive.receptivity_threshold", 0.7
        )
        
        self.interaction_types = {
            "document_suggestion": self.config.get("proactive.document_suggestion_enabled", True),
            "relationship_insight": self.config.get("proactive.relationship_insight_enabled", True),
            "work_pattern_insight": self.config.get("proactive.work_pattern_insight_enabled", True),
            "focus_reminder": self.config.get("proactive.focus_reminder_enabled", True),
            "break_reminder": self.config.get("proactive.break_reminder_enabled", True),
            "calendar_reminder": self.config.get("proactive.calendar_reminder_enabled", True),
            "email_notification": self.config.get("proactive.email_notification_enabled", True),
            "search_suggestion": self.config.get("proactive.search_suggestion_enabled", True),
            "task_suggestion": self.config.get("proactive.task_suggestion_enabled", True),
        }
        
        data_dir = Path(self.config.get("app.data_dir"))
        self.models_dir = data_dir / "proactive_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.work_pattern_model_path = str(self.models_dir / "work_pattern_model.pkl")
        self.receptivity_model_path = str(self.models_dir / "receptivity_model.pkl")
        self.interaction_history_path = str(self.models_dir / "interaction_history.csv")
    
    async def initialize(self):
        """Initialize the proactive service."""
        logger.info("Initializing proactive service")
        
        try:
            if not self.enabled:
                logger.info("Proactive service is disabled in configuration")
                return
            
            await self._initialize_models()
            
            await self._load_interaction_history()
            
            event_bus.subscribe(EventType.USER_ACTIVITY, self._on_user_activity)
            event_bus.subscribe(EventType.DOCUMENT_OPENED, self._on_document_opened)
            event_bus.subscribe(EventType.DOCUMENT_INDEXED, self._on_document_indexed)
            event_bus.subscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
            event_bus.subscribe(EventType.USER_SEARCH, self._on_user_search)
            event_bus.subscribe(EventType.USER_FEEDBACK, self._on_user_feedback)
            
            logger.info("Proactive service initialized")
        except Exception as e:
            logger.error(f"Error initializing proactive service: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Start the proactive service."""
        if self.is_running:
            logger.warning("Proactive service is already running")
            return
        
        if not self.enabled:
            logger.info("Proactive service is disabled in configuration")
            return
        
        logger.info("Starting proactive service")
        
        self.is_running = True
        
        self.monitoring_task = asyncio.create_task(self._monitor_user_state())
        
        logger.info("Proactive service started")
    
    async def stop(self):
        """Stop the proactive service."""
        if not self.is_running:
            logger.warning("Proactive service is not running")
            return
        
        logger.info("Stopping proactive service")
        
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        await self._save_models()
        await self._save_interaction_history()
        
        logger.info("Proactive service stopped")
    
    async def _initialize_models(self):
        """Initialize the work pattern and receptivity models."""
        logger.info("Initializing proactive models")
        
        self.work_pattern_model = IsolationForest(
            contamination=0.1,
            random_state=42,
        )
        
        self.receptivity_model = KMeans(
            n_clusters=2,
            random_state=42,
        )
        
        try:
            await self._load_models()
        except Exception as e:
            logger.warning(f"Could not load existing models: {e}")
            logger.info("Using new models")
        
        logger.info("Proactive models initialized")
    
    async def _load_models(self):
        """Load the work pattern and receptivity models from disk."""
        import pickle
        
        logger.info("Loading proactive models")
        
        if os.path.exists(self.work_pattern_model_path):
            with open(self.work_pattern_model_path, "rb") as f:
                self.work_pattern_model = pickle.load(f)
            logger.info("Loaded work pattern model")
        
        if os.path.exists(self.receptivity_model_path):
            with open(self.receptivity_model_path, "rb") as f:
                self.receptivity_model = pickle.load(f)
            logger.info("Loaded receptivity model")
    
    async def _save_models(self):
        """Save the work pattern and receptivity models to disk."""
        import pickle
        
        logger.info("Saving proactive models")
        
        if self.work_pattern_model:
            with open(self.work_pattern_model_path, "wb") as f:
                pickle.dump(self.work_pattern_model, f)
            logger.info("Saved work pattern model")
        
        if self.receptivity_model:
            with open(self.receptivity_model_path, "wb") as f:
                pickle.dump(self.receptivity_model, f)
            logger.info("Saved receptivity model")
    
    async def _load_interaction_history(self):
        """Load the interaction history from disk."""
        logger.info("Loading interaction history")
        
        if os.path.exists(self.interaction_history_path):
            try:
                df = pd.read_csv(self.interaction_history_path)
                self.interaction_history = df.to_dict("records")
                logger.info(f"Loaded {len(self.interaction_history)} interaction records")
            except Exception as e:
                logger.error(f"Error loading interaction history: {e}", exc_info=True)
                self.interaction_history = []
        else:
            logger.info("No interaction history found")
            self.interaction_history = []
    
    async def _save_interaction_history(self):
        """Save the interaction history to disk."""
        logger.info("Saving interaction history")
        
        try:
            df = pd.DataFrame(self.interaction_history)
            df.to_csv(self.interaction_history_path, index=False)
            logger.info(f"Saved {len(self.interaction_history)} interaction records")
        except Exception as e:
            logger.error(f"Error saving interaction history: {e}", exc_info=True)
    
    async def _monitor_user_state(self):
        """Monitor the user state and schedule proactive interactions."""
        logger.info("Starting user state monitoring")
        
        while self.is_running:
            try:
                current_day = datetime.now().day
                if current_day != self.last_reset_day:
                    self.daily_interaction_count = 0
                    self.last_reset_day = current_day
                
                if self._can_interact():
                    interaction_type = await self._determine_best_interaction()
                    
                    if interaction_type:
                        content = await self._generate_interaction_content(interaction_type)
                        
                        if content:
                            await self._trigger_interaction(interaction_type, content)
                
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                logger.info("User state monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in user state monitoring: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait before trying again
        
        logger.info("User state monitoring stopped")
    
    def _can_interact(self) -> bool:
        """
        Check if we can interact with the user.
        
        Returns:
            True if we can interact, False otherwise
        """
        if self.daily_interaction_count >= self.max_daily_interactions:
            return False
        
        if self.last_interaction_time:
            time_since_last = datetime.now() - self.last_interaction_time
            if time_since_last < self.min_interaction_interval:
                return False
        
        if self.user_state == UserState.UNRECEPTIVE:
            return False
        
        if self.user_state in [UserState.FOCUSED, UserState.BUSY]:
            return False
        
        return True
    
    async def _determine_best_interaction(self) -> Optional[InteractionType]:
        """
        Determine the best interaction type based on the current context.
        
        Returns:
            The best interaction type, or None if no interaction is appropriate
        """
        context = await self._get_current_context()
        
        scores = {}
        
        if self.interaction_types.get("document_suggestion", True):
            scores[InteractionType.DOCUMENT_SUGGESTION] = await self._score_document_suggestion(context)
        
        if self.interaction_types.get("relationship_insight", True):
            scores[InteractionType.RELATIONSHIP_INSIGHT] = await self._score_relationship_insight(context)
        
        if self.interaction_types.get("work_pattern_insight", True):
            scores[InteractionType.WORK_PATTERN_INSIGHT] = await self._score_work_pattern_insight(context)
        
        if self.interaction_types.get("focus_reminder", True):
            scores[InteractionType.FOCUS_REMINDER] = await self._score_focus_reminder(context)
        
        if self.interaction_types.get("break_reminder", True):
            scores[InteractionType.BREAK_REMINDER] = await self._score_break_reminder(context)
        
        if self.interaction_types.get("calendar_reminder", True):
            scores[InteractionType.CALENDAR_REMINDER] = await self._score_calendar_reminder(context)
        
        if self.interaction_types.get("email_notification", True):
            scores[InteractionType.EMAIL_NOTIFICATION] = await self._score_email_notification(context)
        
        if self.interaction_types.get("search_suggestion", True):
            scores[InteractionType.SEARCH_SUGGESTION] = await self._score_search_suggestion(context)
        
        if self.interaction_types.get("task_suggestion", True):
            scores[InteractionType.TASK_SUGGESTION] = await self._score_task_suggestion(context)
        
        if scores:
            best_type = max(scores.items(), key=lambda x: x[1])[0]
            best_score = scores[best_type]
            
            if best_score >= self.receptivity_threshold:
                return best_type
        
        return None
    
    async def _get_current_context(self) -> Dict[str, Any]:
        """
        Get the current context for determining the best interaction.
        
        Returns:
            A dictionary with context information
        """
        return {
            "user_state": self.user_state,
            "time_of_day": datetime.now().hour,
            "day_of_week": datetime.now().weekday(),
            "active_documents": [],
            "recent_searches": [],
            "upcoming_events": [],
            "unread_emails": 0,
        }
    
    async def _score_document_suggestion(self, context: Dict[str, Any]) -> float:
        """
        Score the document suggestion interaction type.
        
        Args:
            context: The current context
            
        Returns:
            A score between 0 and 1
        """
        return np.random.random()
    
    async def _score_relationship_insight(self, context: Dict[str, Any]) -> float:
        """
        Score the relationship insight interaction type.
        
        Args:
            context: The current context
            
        Returns:
            A score between 0 and 1
        """
        return np.random.random()
    
    async def _score_work_pattern_insight(self, context: Dict[str, Any]) -> float:
        """
        Score the work pattern insight interaction type.
        
        Args:
            context: The current context
            
        Returns:
            A score between 0 and 1
        """
        return np.random.random()
    
    async def _score_focus_reminder(self, context: Dict[str, Any]) -> float:
        """
        Score the focus reminder interaction type.
        
        Args:
            context: The current context
            
        Returns:
            A score between 0 and 1
        """
        return np.random.random()
    
    async def _score_break_reminder(self, context: Dict[str, Any]) -> float:
        """
        Score the break reminder interaction type.
        
        Args:
            context: The current context
            
        Returns:
            A score between 0 and 1
        """
        return np.random.random()
    
    async def _score_calendar_reminder(self, context: Dict[str, Any]) -> float:
        """
        Score the calendar reminder interaction type.
        
        Args:
            context: The current context
            
        Returns:
            A score between 0 and 1
        """
        return np.random.random()
    
    async def _score_email_notification(self, context: Dict[str, Any]) -> float:
        """
        Score the email notification interaction type.
        
        Args:
            context: The current context
            
        Returns:
            A score between 0 and 1
        """
        return np.random.random()
    
    async def _score_search_suggestion(self, context: Dict[str, Any]) -> float:
        """
        Score the search suggestion interaction type.
        
        Args:
            context: The current context
            
        Returns:
            A score between 0 and 1
        """
        return np.random.random()
    
    async def _score_task_suggestion(self, context: Dict[str, Any]) -> float:
        """
        Score the task suggestion interaction type.
        
        Args:
            context: The current context
            
        Returns:
            A score between 0 and 1
        """
        return np.random.random()
    
    async def _generate_interaction_content(self, interaction_type: InteractionType) -> Optional[Dict[str, Any]]:
        """
        Generate the content for an interaction.
        
        Args:
            interaction_type: The type of interaction
            
        Returns:
            A dictionary with the interaction content, or None if no content could be generated
        """
        
        if interaction_type == InteractionType.DOCUMENT_SUGGESTION:
            return {
                "title": "Document Suggestion",
                "message": "You might find this document relevant to your current work.",
                "document_id": "123",
                "document_title": "Example Document",
            }
        elif interaction_type == InteractionType.RELATIONSHIP_INSIGHT:
            return {
                "title": "Relationship Insight",
                "message": "I found a connection between these documents that might interest you.",
                "source_document_id": "123",
                "source_document_title": "Example Document 1",
                "target_document_id": "456",
                "target_document_title": "Example Document 2",
                "relationship_type": "semantic_similarity",
                "relationship_strength": 0.85,
            }
        elif interaction_type == InteractionType.WORK_PATTERN_INSIGHT:
            return {
                "title": "Work Pattern Insight",
                "message": "You tend to be most productive between 9 AM and 11 AM.",
            }
        elif interaction_type == InteractionType.FOCUS_REMINDER:
            return {
                "title": "Focus Reminder",
                "message": "You've been working on this task for 45 minutes. Consider taking a short break soon.",
            }
        elif interaction_type == InteractionType.BREAK_REMINDER:
            return {
                "title": "Break Reminder",
                "message": "You've been working for 2 hours straight. Consider taking a break.",
            }
        elif interaction_type == InteractionType.CALENDAR_REMINDER:
            return {
                "title": "Calendar Reminder",
                "message": "You have a meeting in 15 minutes.",
                "event_id": "789",
                "event_title": "Team Meeting",
                "event_time": datetime.now() + timedelta(minutes=15),
            }
        elif interaction_type == InteractionType.EMAIL_NOTIFICATION:
            return {
                "title": "Email Notification",
                "message": "You have a new email from John Doe about the project deadline.",
                "email_id": "abc",
                "email_subject": "Project Deadline",
                "email_sender": "John Doe",
            }
        elif interaction_type == InteractionType.SEARCH_SUGGESTION:
            return {
                "title": "Search Suggestion",
                "message": "Based on your recent activity, you might want to search for 'knowledge management'.",
                "search_query": "knowledge management",
            }
        elif interaction_type == InteractionType.TASK_SUGGESTION:
            return {
                "title": "Task Suggestion",
                "message": "You might want to review the project proposal document.",
                "task_id": "def",
                "task_title": "Review Project Proposal",
            }
        else:
            return None
    
    async def _trigger_interaction(self, interaction_type: InteractionType, content: Dict[str, Any]):
        """
        Trigger a proactive interaction with the user.
        
        Args:
            interaction_type: The type of interaction
            content: The interaction content
        """
        logger.info(f"Triggering proactive interaction: {interaction_type.name}")
        
        self._record_interaction(interaction_type, content)
        
        publish(
            EventType.PROACTIVE_INTERACTION,
            {
                "interaction_type": interaction_type.name,
                "content": content,
            },
        )
        
        self.last_interaction_time = datetime.now()
        
        self.daily_interaction_count += 1
    
    def _record_interaction(self, interaction_type: InteractionType, content: Dict[str, Any]):
        """
        Record an interaction in the interaction history.
        
        Args:
            interaction_type: The type of interaction
            content: The interaction content
        """
        record: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "interaction_type": interaction_type.name,
            "user_state": self.user_state.name,
            "content": str(content),
        }
        
        self.interaction_history.append(record)
        
        max_history_size = 1000
        if len(self.interaction_history) > max_history_size:
            self.interaction_history = self.interaction_history[-max_history_size:]
    
    async def _on_user_activity(self, event):
        """
        Handle user activity events.
        
        Args:
            event: The user activity event
        """
        activity_type = event.data.get("activity_type")
        
        if activity_type == "keyboard":
            self.user_state = UserState.FOCUSED
        elif activity_type == "mouse":
            if self.user_state == UserState.IDLE:
                self.user_state = UserState.RECEPTIVE
        elif activity_type == "idle":
            self.user_state = UserState.IDLE
        elif activity_type == "window_switch":
            self.user_state = UserState.DISTRACTED
        
        await self._update_work_pattern_model(event.data)
    
    async def _on_document_opened(self, event):
        """
        Handle document opened events.
        
        Args:
            event: The document opened event
        """
        pass
    
    async def _on_document_indexed(self, event):
        """
        Handle document indexed events.
        
        Args:
            event: The document indexed event
        """
        pass
    
    async def _on_relationship_detected(self, event):
        """
        Handle relationship detected events.
        
        Args:
            event: The relationship detected event
        """
        pass
    
    async def _on_user_search(self, event):
        """
        Handle user search events.
        
        Args:
            event: The user search event
        """
        pass
    
    async def _on_user_feedback(self, event):
        """
        Handle user feedback events.
        
        Args:
            event: The user feedback event
        """
        await self._update_receptivity_model(event.data)
    
    async def _update_work_pattern_model(self, data: Dict[str, Any]):
        """
        Update the work pattern model with new data.
        
        Args:
            data: The data to update the model with
        """
        logger.debug(f"Updating work pattern model with data: {data}")
    
    async def _update_receptivity_model(self, data: Dict[str, Any]):
        """
        Update the receptivity model with new data.
        
        Args:
            data: The data to update the model with
        """
        logger.debug(f"Updating receptivity model with data: {data}")

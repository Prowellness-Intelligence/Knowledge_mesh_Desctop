"""
Contextual Awareness Engine for the Knowledge Mesh Desktop application.

This module provides a service for understanding the user's current context
and determining when and how to provide proactive assistance.
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


class ContextualAwarenessEngine:
    """
    Engine for understanding the user's current context.
    
    This service tracks the user's current context, including what they're
    working on, their focus level, and other relevant information for
    providing proactive assistance.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the contextual awareness engine.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.is_running = False
        self.current_context: Optional[Context] = None
        self.context_history: List[Context] = []
        self.max_context_history = 100
        self.context_update_interval = 30  # seconds
        self.context_update_task = None
        self.data_dir = Path(self.config.get("app.data_dir", "."))
        self.contexts_dir = self.data_dir / "contexts"
        self.last_activity_time = time.time()
        self.idle_threshold = 300  # 5 minutes
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.enabled = self.config.get("contextual_awareness.enabled", True)
        self.context_update_interval = self.config.get(
            "contextual_awareness.update_interval", 30
        )
        self.max_context_history = self.config.get("contextual_awareness.max_history", 100)
        self.idle_threshold = self.config.get("contextual_awareness.idle_threshold", 300)
    
    async def initialize(self):
        """Initialize the contextual awareness engine."""
        logger.info("Initializing contextual awareness engine")
        
        try:
            self.contexts_dir.mkdir(parents=True, exist_ok=True)
            
            await self._load_context_history()
            
            event_bus.subscribe(EventType.UI_DOCUMENT_SELECTED, self._on_document_selected)
            event_bus.subscribe(EventType.UI_DOCUMENT_OPENED, self._on_document_opened)
            event_bus.subscribe(EventType.UI_DOCUMENT_CLOSED, self._on_document_closed)
            event_bus.subscribe(EventType.UI_MESH_VIEW_CHANGED, self._on_mesh_view_changed)
            event_bus.subscribe(EventType.UI_SETTINGS_CHANGED, self._on_settings_changed)
            
            logger.info("Contextual awareness engine initialized")
        except Exception as e:
            logger.error(f"Error initializing contextual awareness engine: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Start the contextual awareness engine."""
        logger.info("Starting contextual awareness engine")
        
        if not self.enabled:
            logger.info("Contextual awareness engine is disabled")
            return
        
        self.is_running = True
        
        self.context_update_task = asyncio.create_task(self._context_update_loop())
        
        await self._create_initial_context()
        
        logger.info("Contextual awareness engine started")
    
    async def stop(self):
        """Stop the contextual awareness engine."""
        logger.info("Stopping contextual awareness engine")
        
        self.is_running = False
        
        if self.current_context:
            self.current_context.end()
            await self._save_context(self.current_context)
            self.current_context = None
        
        if self.context_update_task:
            self.context_update_task.cancel()
            try:
                await self.context_update_task
            except asyncio.CancelledError:
                pass
            self.context_update_task = None
        
        event_bus.unsubscribe(EventType.UI_DOCUMENT_SELECTED, self._on_document_selected)
        event_bus.unsubscribe(EventType.UI_DOCUMENT_OPENED, self._on_document_opened)
        event_bus.unsubscribe(EventType.UI_DOCUMENT_CLOSED, self._on_document_closed)
        event_bus.unsubscribe(EventType.UI_MESH_VIEW_CHANGED, self._on_mesh_view_changed)
        event_bus.unsubscribe(EventType.UI_SETTINGS_CHANGED, self._on_settings_changed)
        
        logger.info("Contextual awareness engine stopped")
    
    async def _load_context_history(self):
        """Load context history from disk."""
        try:
            for context_file in self.contexts_dir.glob("*.pkl"):
                try:
                    with open(context_file, "rb") as f:
                        context_dict = pickle.load(f)
                        context = Context.from_dict(context_dict)
                        self.context_history.append(context)
                except Exception as e:
                    logger.error(f"Error loading context from {context_file}: {e}", exc_info=True)
            
            self.context_history.sort(key=lambda c: c.start_time)
            
            if len(self.context_history) > self.max_context_history:
                self.context_history = self.context_history[-self.max_context_history:]
            
            logger.info(f"Loaded {len(self.context_history)} contexts")
        except Exception as e:
            logger.error(f"Error loading context history: {e}", exc_info=True)
    
    async def _save_context(self, context: Context):
        """
        Save a context to disk.
        
        Args:
            context: The context to save
        """
        try:
            context_file = self.contexts_dir / f"{context.id}.pkl"
            with open(context_file, "wb") as f:
                pickle.dump(context.to_dict(), f)
            
            logger.debug(f"Saved context {context.id}")
        except Exception as e:
            logger.error(f"Error saving context {context.id}: {e}", exc_info=True)
    
    async def _create_initial_context(self):
        """Create an initial context."""
        self.current_context = Context(
            id=str(uuid.uuid4()),
            type=ContextType.APPLICATION_CONTEXT,
            data={
                "application": "Knowledge Mesh Desktop",
                "view": "main",
            },
            focus_level=FocusLevel.INTERRUPTIBLE,
        )
        
        logger.info(f"Created initial context: {self.current_context}")
    
    async def _context_update_loop(self):
        """Run the context update loop."""
        try:
            while self.is_running:
                await asyncio.sleep(self.context_update_interval)
                
                if not self.enabled:
                    continue
                
                try:
                    await self._update_context()
                except Exception as e:
                    logger.error(f"Error updating context: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.debug("Context update loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in context update loop: {e}", exc_info=True)
    
    async def _update_context(self):
        """Update the current context."""
        if not self.current_context:
            return
        
        current_time = time.time()
        time_since_activity = current_time - self.last_activity_time
        
        if time_since_activity > self.idle_threshold:
            if self.current_context.focus_level != FocusLevel.IDLE:
                logger.info(f"User is idle for {time_since_activity:.1f} seconds")
                self.current_context.update(focus_level=FocusLevel.IDLE)
        
        await self._save_context(self.current_context)
    
    def _update_activity_time(self):
        """Update the last activity time."""
        self.last_activity_time = time.time()
        
        if self.current_context and self.current_context.focus_level == FocusLevel.IDLE:
            self.current_context.update(focus_level=FocusLevel.INTERRUPTIBLE)
    
    async def _switch_context(self, context_type: ContextType, data: Dict[str, Any], focus_level: FocusLevel = FocusLevel.INTERRUPTIBLE):
        """
        Switch to a new context.
        
        Args:
            context_type: The type of the new context
            data: The context data
            focus_level: The user's focus level in the new context
        """
        if not self.enabled:
            return
        
        if self.current_context:
            self.current_context.end()
            self.context_history.append(self.current_context)
            
            if len(self.context_history) > self.max_context_history:
                self.context_history = self.context_history[-self.max_context_history:]
            
            await self._save_context(self.current_context)
        
        self.current_context = Context(
            id=str(uuid.uuid4()),
            type=context_type,
            data=data,
            focus_level=focus_level,
        )
        
        logger.info(f"Switched to new context: {self.current_context}")
        
        self._update_activity_time()
    
    def _on_document_selected(self, event):
        """
        Handle document selected events.
        
        Args:
            event: The document selected event
        """
        if not self.enabled:
            return
        
        document_id = event.data.get("document_id")
        if document_id:
            asyncio.create_task(self._switch_context(
                ContextType.DOCUMENT_FOCUS,
                {
                    "document_id": document_id,
                    "action": "selected",
                },
                FocusLevel.INTERRUPTIBLE,
            ))
        
        self._update_activity_time()
    
    def _on_document_opened(self, event):
        """
        Handle document opened events.
        
        Args:
            event: The document opened event
        """
        if not self.enabled:
            return
        
        document_id = event.data.get("document_id")
        if document_id:
            asyncio.create_task(self._switch_context(
                ContextType.DOCUMENT_FOCUS,
                {
                    "document_id": document_id,
                    "action": "opened",
                },
                FocusLevel.FOCUSED,  # User is more focused when actively opening a document
            ))
        
        self._update_activity_time()
    
    def _on_document_closed(self, event):
        """
        Handle document closed events.
        
        Args:
            event: The document closed event
        """
        if not self.enabled:
            return
        
        asyncio.create_task(self._switch_context(
            ContextType.APPLICATION_CONTEXT,
            {
                "application": "Knowledge Mesh Desktop",
                "view": "main",
            },
            FocusLevel.INTERRUPTIBLE,
        ))
        
        self._update_activity_time()
    
    def _on_mesh_view_changed(self, event):
        """
        Handle mesh view changed events.
        
        Args:
            event: The mesh view changed event
        """
        if not self.enabled:
            return
        
        view_type = event.data.get("view_type")
        if view_type:
            asyncio.create_task(self._switch_context(
                ContextType.APPLICATION_CONTEXT,
                {
                    "application": "Knowledge Mesh Desktop",
                    "view": view_type,
                },
                FocusLevel.INTERRUPTIBLE,
            ))
        
        self._update_activity_time()
    
    def _on_settings_changed(self, event):
        """
        Handle settings changed events.
        
        Args:
            event: The settings changed event
        """
        self._load_config()
        
        self._update_activity_time()
    
    async def get_current_context(self) -> Optional[Context]:
        """
        Get the current context.
        
        Returns:
            The current context, or None if not available
        """
        return self.current_context
    
    async def get_context_history(self, limit: int = 10) -> List[Context]:
        """
        Get the context history.
        
        Args:
            limit: Maximum number of contexts to return
            
        Returns:
            A list of contexts
        """
        return self.context_history[-limit:]
    
    async def is_interruption_appropriate(self) -> bool:
        """
        Determine if it's appropriate to interrupt the user.
        
        Returns:
            True if it's appropriate to interrupt the user, False otherwise
        """
        if not self.enabled:
            return False
        
        if not self.current_context:
            return True
        
        return self.current_context.is_interruption_appropriate
    
    async def get_relevant_documents(self, limit: int = 5) -> List[str]:
        """
        Get documents relevant to the current context.
        
        Args:
            limit: Maximum number of documents to return
            
        Returns:
            A list of document IDs
        """
        if not self.current_context:
            return []
        
        relevant_docs = []
        
        if self.current_context.type == ContextType.DOCUMENT_FOCUS:
            doc_id = self.current_context.data.get("document_id")
            if doc_id:
                relevant_docs.append(doc_id)
        
        for context in reversed(self.context_history):
            if context.type == ContextType.DOCUMENT_FOCUS:
                doc_id = context.data.get("document_id")
                if doc_id and doc_id not in relevant_docs:
                    relevant_docs.append(doc_id)
                    
                    if len(relevant_docs) >= limit:
                        break
        
        return relevant_docs
    
    async def generate_proactive_suggestions(self, work_patterns: List[WorkPattern] = None) -> List[Dict[str, Any]]:
        """
        Generate proactive suggestions based on the current context.
        
        Args:
            work_patterns: Optional list of work patterns to consider
            
        Returns:
            A list of suggestions
        """
        if not self.enabled or not self.current_context:
            return []
        
        suggestions = []
        
        if not await self.is_interruption_appropriate():
            return []
        
        relevant_docs = await self.get_relevant_documents()
        
        if relevant_docs and self.current_context.type == ContextType.DOCUMENT_FOCUS:
            current_doc = self.current_context.data.get("document_id")
            if current_doc and current_doc in relevant_docs:
                suggestions.append({
                    "interaction_type": "DOCUMENT_SUGGESTION",
                    "content": {
                        "document_id": relevant_docs[0],
                        "document_title": f"Document {relevant_docs[0]}",
                        "reason": "This document is related to your current work.",
                    },
                })
        
        if work_patterns:
            for pattern in work_patterns:
                if pattern.type == WorkPatternType.DOCUMENT_ACCESS and pattern.confidence > 0.5:
                    doc_id = pattern.data.get("document_id")
                    if doc_id and doc_id not in relevant_docs:
                        suggestions.append({
                            "interaction_type": "DOCUMENT_SUGGESTION",
                            "content": {
                                "document_id": doc_id,
                                "document_title": f"Document {doc_id}",
                                "reason": "You frequently access this document.",
                            },
                        })
        
        return suggestions
    
    async def publish_suggestions(self, work_patterns: List[WorkPattern] = None):
        """
        Publish proactive suggestions.
        
        Args:
            work_patterns: Optional list of work patterns to consider
        """
        if not self.enabled:
            return
        
        suggestions = await self.generate_proactive_suggestions(work_patterns)
        
        for suggestion in suggestions:
            publish(
                EventType.SUGGESTION_GENERATED,
                suggestion,
            )

"""
Work Pattern Monitor Service for the Knowledge Mesh Desktop application.

This module provides a service for monitoring user behavior and identifying
patterns that can be used for proactive interactions.
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
from ..models.work_pattern import WorkPattern, WorkPatternType, WorkPatternConfidence

logger = logging.getLogger(__name__)


class WorkPatternMonitorService:
    """
    Service for monitoring user behavior and identifying patterns.
    
    This service tracks user interactions with the application and documents,
    identifies patterns in the user's behavior, and provides insights that
    can be used for proactive interactions.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the work pattern monitor service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.is_running = False
        self.patterns: Dict[str, WorkPattern] = {}
        self.recent_events: List[Dict[str, Any]] = []
        self.max_recent_events = 1000
        self.pattern_detection_interval = 60  # seconds
        self.pattern_detection_task = None
        self.data_dir = Path(self.config.get("app.data_dir", "."))
        self.patterns_dir = self.data_dir / "patterns"
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.enabled = self.config.get("work_pattern_monitor.enabled", True)
        self.min_pattern_confidence = self.config.get("work_pattern_monitor.min_confidence", 0.3)
        self.max_patterns = self.config.get("work_pattern_monitor.max_patterns", 100)
        self.pattern_detection_interval = self.config.get(
            "work_pattern_monitor.detection_interval", 60
        )
        self.max_recent_events = self.config.get("work_pattern_monitor.max_recent_events", 1000)
    
    async def initialize(self):
        """Initialize the work pattern monitor service."""
        logger.info("Initializing work pattern monitor service")
        
        try:
            self.patterns_dir.mkdir(parents=True, exist_ok=True)
            
            await self._load_patterns()
            
            event_bus.subscribe(EventType.UI_DOCUMENT_SELECTED, self._on_document_selected)
            event_bus.subscribe(EventType.UI_DOCUMENT_OPENED, self._on_document_opened)
            event_bus.subscribe(EventType.DOCUMENT_PROCESSING_COMPLETED, self._on_document_processed)
            event_bus.subscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
            event_bus.subscribe(EventType.UI_MESH_VIEW_CHANGED, self._on_mesh_view_changed)
            event_bus.subscribe(EventType.UI_SETTINGS_CHANGED, self._on_settings_changed)
            
            logger.info("Work pattern monitor service initialized")
        except Exception as e:
            logger.error(f"Error initializing work pattern monitor service: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Start the work pattern monitor service."""
        logger.info("Starting work pattern monitor service")
        
        if not self.enabled:
            logger.info("Work pattern monitor service is disabled")
            return
        
        self.is_running = True
        
        self.pattern_detection_task = asyncio.create_task(self._pattern_detection_loop())
        
        logger.info("Work pattern monitor service started")
    
    async def stop(self):
        """Stop the work pattern monitor service."""
        logger.info("Stopping work pattern monitor service")
        
        self.is_running = False
        
        if self.pattern_detection_task:
            self.pattern_detection_task.cancel()
            try:
                await self.pattern_detection_task
            except asyncio.CancelledError:
                pass
            self.pattern_detection_task = None
        
        event_bus.unsubscribe(EventType.UI_DOCUMENT_SELECTED, self._on_document_selected)
        event_bus.unsubscribe(EventType.UI_DOCUMENT_OPENED, self._on_document_opened)
        event_bus.unsubscribe(EventType.DOCUMENT_PROCESSING_COMPLETED, self._on_document_processed)
        event_bus.unsubscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
        event_bus.unsubscribe(EventType.UI_MESH_VIEW_CHANGED, self._on_mesh_view_changed)
        event_bus.unsubscribe(EventType.UI_SETTINGS_CHANGED, self._on_settings_changed)
        
        await self._save_patterns()
        
        logger.info("Work pattern monitor service stopped")
    
    async def _load_patterns(self):
        """Load patterns from disk."""
        try:
            for pattern_file in self.patterns_dir.glob("*.pkl"):
                try:
                    with open(pattern_file, "rb") as f:
                        pattern_dict = pickle.load(f)
                        pattern = WorkPattern.from_dict(pattern_dict)
                        self.patterns[pattern.id] = pattern
                except Exception as e:
                    logger.error(f"Error loading pattern from {pattern_file}: {e}", exc_info=True)
            
            logger.info(f"Loaded {len(self.patterns)} work patterns")
        except Exception as e:
            logger.error(f"Error loading patterns: {e}", exc_info=True)
    
    async def _save_patterns(self):
        """Save patterns to disk."""
        try:
            for pattern_id, pattern in self.patterns.items():
                pattern_file = self.patterns_dir / f"{pattern_id}.pkl"
                with open(pattern_file, "wb") as f:
                    pickle.dump(pattern.to_dict(), f)
            
            logger.info(f"Saved {len(self.patterns)} work patterns")
        except Exception as e:
            logger.error(f"Error saving patterns: {e}", exc_info=True)
    
    async def _pattern_detection_loop(self):
        """Run the pattern detection loop."""
        try:
            while self.is_running:
                await asyncio.sleep(self.pattern_detection_interval)
                
                if not self.enabled:
                    continue
                
                try:
                    await self._detect_patterns()
                except Exception as e:
                    logger.error(f"Error detecting patterns: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.debug("Pattern detection loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in pattern detection loop: {e}", exc_info=True)
    
    async def _detect_patterns(self):
        """Detect patterns in user behavior."""
        if not self.recent_events:
            return
        
        logger.debug(f"Detecting patterns from {len(self.recent_events)} recent events")
        
        await self._detect_document_access_patterns()
        
        await self._detect_time_of_day_patterns()
        
        await self._detect_search_query_patterns()
        
        await self._detect_application_usage_patterns()
        
        await self._detect_focus_duration_patterns()
        
        await self._prune_patterns()
        
        await self._save_patterns()
    
    async def _detect_document_access_patterns(self):
        """Detect patterns in document access."""
        doc_events = [
            e for e in self.recent_events
            if e.get("event_type") in ["UI_DOCUMENT_SELECTED", "UI_DOCUMENT_OPENED"]
        ]
        
        if not doc_events:
            return
        
        doc_counts = {}
        for event in doc_events:
            doc_id = event.get("data", {}).get("document_id")
            if doc_id:
                doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
        
        for doc_id, count in doc_counts.items():
            if count >= 3:  # Threshold for pattern detection
                pattern_id = f"document_access_{doc_id}"
                
                if pattern_id in self.patterns:
                    self.patterns[pattern_id].update_observation()
                else:
                    pattern = WorkPattern(
                        id=pattern_id,
                        type=WorkPatternType.DOCUMENT_ACCESS,
                        data={
                            "document_id": doc_id,
                            "access_count": count,
                        },
                        confidence=0.3,  # Initial confidence
                    )
                    self.patterns[pattern_id] = pattern
                    
                    logger.info(f"Detected new document access pattern: {pattern}")
    
    async def _detect_time_of_day_patterns(self):
        """Detect patterns in time of day usage."""
        hour_counts = {}
        for event in self.recent_events:
            timestamp = event.get("timestamp")
            if timestamp:
                dt = datetime.fromtimestamp(timestamp)
                hour = dt.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        total_events = sum(hour_counts.values())
        if total_events == 0:
            return
        
        for hour, count in hour_counts.items():
            ratio = count / total_events
            if ratio >= 0.2:  # Threshold for pattern detection
                pattern_id = f"time_of_day_{hour}"
                
                if pattern_id in self.patterns:
                    self.patterns[pattern_id].update_observation({
                        "event_count": count,
                        "ratio": ratio,
                    })
                else:
                    pattern = WorkPattern(
                        id=pattern_id,
                        type=WorkPatternType.TIME_OF_DAY,
                        data={
                            "hour": hour,
                            "event_count": count,
                            "ratio": ratio,
                        },
                        confidence=0.3,  # Initial confidence
                    )
                    self.patterns[pattern_id] = pattern
                    
                    logger.info(f"Detected new time of day pattern: {pattern}")
    
    async def _detect_search_query_patterns(self):
        """Detect patterns in search queries."""
        pass
    
    async def _detect_application_usage_patterns(self):
        """Detect patterns in application usage."""
        pass
    
    async def _detect_focus_duration_patterns(self):
        """Detect patterns in focus duration."""
        pass
    
    async def _prune_patterns(self):
        """Prune old or low-confidence patterns."""
        patterns_to_remove = []
        
        for pattern_id, pattern in self.patterns.items():
            if (pattern.age_days > 30 and pattern.confidence < 0.4) or \
               (pattern.age_days > 90 and pattern.confidence < 0.6):
                patterns_to_remove.append(pattern_id)
        
        for pattern_id in patterns_to_remove:
            del self.patterns[pattern_id]
            
            pattern_file = self.patterns_dir / f"{pattern_id}.pkl"
            if pattern_file.exists():
                pattern_file.unlink()
        
        if len(self.patterns) > self.max_patterns:
            patterns_list = list(self.patterns.values())
            patterns_list.sort(key=lambda p: (p.confidence, -p.age_days))
            
            patterns_to_remove = patterns_list[:len(patterns_list) - self.max_patterns]
            
            for pattern in patterns_to_remove:
                del self.patterns[pattern.id]
                
                pattern_file = self.patterns_dir / f"{pattern.id}.pkl"
                if pattern_file.exists():
                    pattern_file.unlink()
    
    def _record_event(self, event_type: str, data: Dict[str, Any]):
        """
        Record an event for pattern detection.
        
        Args:
            event_type: The type of event
            data: The event data
        """
        if not self.enabled:
            return
        
        self.recent_events.append({
            "event_type": event_type,
            "data": data,
            "timestamp": time.time(),
        })
        
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events = self.recent_events[-self.max_recent_events:]
    
    def _on_document_selected(self, event):
        """
        Handle document selected events.
        
        Args:
            event: The document selected event
        """
        self._record_event("UI_DOCUMENT_SELECTED", event.data)
    
    def _on_document_opened(self, event):
        """
        Handle document opened events.
        
        Args:
            event: The document opened event
        """
        self._record_event("UI_DOCUMENT_OPENED", event.data)
    
    def _on_document_processed(self, event):
        """
        Handle document processed events.
        
        Args:
            event: The document processed event
        """
        self._record_event("DOCUMENT_PROCESSING_COMPLETED", event.data)
    
    def _on_relationship_detected(self, event):
        """
        Handle relationship detected events.
        
        Args:
            event: The relationship detected event
        """
        self._record_event("RELATIONSHIP_DETECTED", event.data)
    
    def _on_mesh_view_changed(self, event):
        """
        Handle mesh view changed events.
        
        Args:
            event: The mesh view changed event
        """
        self._record_event("UI_MESH_VIEW_CHANGED", event.data)
    
    def _on_settings_changed(self, event):
        """
        Handle settings changed events.
        
        Args:
            event: The settings changed event
        """
        self._record_event("UI_SETTINGS_CHANGED", event.data)
        
        self._load_config()
    
    async def get_patterns(self, pattern_type: Optional[WorkPatternType] = None, min_confidence: float = 0.0) -> List[WorkPattern]:
        """
        Get work patterns.
        
        Args:
            pattern_type: Optional type to filter by
            min_confidence: Minimum confidence level
            
        Returns:
            A list of work patterns
        """
        patterns = list(self.patterns.values())
        
        if pattern_type:
            patterns = [p for p in patterns if p.type == pattern_type]
        
        patterns = [p for p in patterns if p.confidence >= min_confidence]
        
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        
        return patterns
    
    async def get_pattern(self, pattern_id: str) -> Optional[WorkPattern]:
        """
        Get a work pattern by ID.
        
        Args:
            pattern_id: The pattern ID
            
        Returns:
            The work pattern, or None if not found
        """
        return self.patterns.get(pattern_id)
    
    async def generate_insights(self) -> List[Dict[str, Any]]:
        """
        Generate insights from work patterns.
        
        Returns:
            A list of insights
        """
        insights = []
        
        high_confidence_patterns = await self.get_patterns(min_confidence=self.min_pattern_confidence)
        
        if not high_confidence_patterns:
            return insights
        
        doc_access_patterns = [p for p in high_confidence_patterns if p.type == WorkPatternType.DOCUMENT_ACCESS]
        for pattern in doc_access_patterns:
            doc_id = pattern.data.get("document_id")
            if doc_id:
                insights.append({
                    "type": "DOCUMENT_ACCESS_PATTERN",
                    "document_id": doc_id,
                    "confidence": pattern.confidence,
                    "message": f"You frequently access this document.",
                    "action": "View Document",
                    "action_data": {
                        "document_id": doc_id,
                    },
                })
        
        time_patterns = [p for p in high_confidence_patterns if p.type == WorkPatternType.TIME_OF_DAY]
        for pattern in time_patterns:
            hour = pattern.data.get("hour")
            if hour is not None:
                insights.append({
                    "type": "TIME_OF_DAY_PATTERN",
                    "hour": hour,
                    "confidence": pattern.confidence,
                    "message": f"You're most active around {hour}:00.",
                })
        
        return insights
    
    async def publish_insights(self):
        """Publish insights from work patterns."""
        if not self.enabled:
            return
        
        insights = await self.generate_insights()
        
        for insight in insights:
            publish(
                EventType.WORK_PATTERN_UPDATED,
                {
                    "insight": insight,
                },
            )
            
            publish(
                EventType.SUGGESTION_GENERATED,
                {
                    "interaction_type": "WORK_PATTERN_INSIGHT",
                    "content": {
                        "insight": insight.get("message", ""),
                        "action": insight.get("action"),
                        "action_data": insight.get("action_data", {}),
                    },
                },
            )

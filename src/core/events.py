"""
Event system for the Knowledge Mesh Desktop application.

This module provides a publish-subscribe event system that allows different
components of the application to communicate with each other without direct
dependencies. Components can publish events and subscribe to events from
other components.
"""

import asyncio
import inspect
import logging
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Enum defining the types of events that can be published in the system."""

    APP_STARTED = auto()
    APP_STOPPING = auto()
    APP_CONFIGURATION_CHANGED = auto()

    FILE_CREATED = auto()
    FILE_MODIFIED = auto()
    FILE_DELETED = auto()
    FILE_MOVED = auto()
    DIRECTORY_CREATED = auto()
    DIRECTORY_DELETED = auto()

    DOCUMENT_PROCESSING_STARTED = auto()
    DOCUMENT_PROCESSING_COMPLETED = auto()
    DOCUMENT_PROCESSING_FAILED = auto()
    DOCUMENT_INDEXED = auto()
    DOCUMENT_SUMMARY_GENERATED = auto()

    RELATIONSHIP_DETECTED = auto()
    RELATIONSHIP_UPDATED = auto()
    RELATIONSHIP_DELETED = auto()
    KNOWLEDGE_MESH_UPDATED = auto()

    SUGGESTION_GENERATED = auto()
    SUGGESTION_DISPLAYED = auto()
    SUGGESTION_ACCEPTED = auto()
    SUGGESTION_REJECTED = auto()
    WORK_PATTERN_UPDATED = auto()

    CALENDAR_SYNCED = auto()
    EVENT_CREATED = auto()
    EVENT_UPDATED = auto()
    EVENT_DELETED = auto()
    EVENT_REMINDER = auto()

    EMAIL_SYNCED = auto()
    EMAIL_RECEIVED = auto()
    EMAIL_PROCESSED = auto()
    ATTACHMENT_PROCESSED = auto()

    VOICE_COMMAND_DETECTED = auto()
    VOICE_COMMAND_PROCESSED = auto()
    SPEECH_SYNTHESIS_STARTED = auto()
    SPEECH_SYNTHESIS_COMPLETED = auto()

    UI_DOCUMENT_SELECTED = auto()
    UI_DOCUMENT_OPENED = auto()
    UI_DOCUMENT_CLOSED = auto()
    UI_MESH_VIEW_CHANGED = auto()
    UI_SETTINGS_CHANGED = auto()


class Event:
    """
    Represents an event in the system.

    Attributes:
        type: The type of the event
        data: Additional data associated with the event
        source: The source component that published the event
    """

    def __init__(self, type: EventType, data: Any = None, source: Optional[str] = None):
        """
        Initialize a new event.

        Args:
            type: The type of the event
            data: Additional data associated with the event
            source: The source component that published the event
        """
        self.type = type
        self.data = data
        self.source = source

    def __str__(self) -> str:
        """Return a string representation of the event."""
        return f"Event(type={self.type.name}, source={self.source}, data={self.data})"


class EventBus:
    """
    Event bus for publishing and subscribing to events.

    This class implements the publish-subscribe pattern, allowing components
    to publish events and subscribe to events from other components without
    direct dependencies.
    """

    def __init__(self):
        """Initialize a new event bus."""
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._async_subscribers: Dict[EventType, List[Callable[[Event], Any]]] = {}
        self._wildcard_subscribers: List[Callable[[Event], None]] = []
        self._async_wildcard_subscribers: List[Callable[[Event], Any]] = []
        self._event_history: Dict[EventType, List[Event]] = {}
        self._max_history_per_type = 100

    def subscribe(self, event_type: Optional[EventType], callback: Callable[[Event], Any]) -> None:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: The type of events to subscribe to, or None to subscribe to all events
            callback: The function to call when an event of the specified type is published
        """
        is_async = asyncio.iscoroutinefunction(callback)

        if event_type is None:
            if is_async:
                self._async_wildcard_subscribers.append(callback)
            else:
                self._wildcard_subscribers.append(callback)
        else:
            if is_async:
                if event_type not in self._async_subscribers:
                    self._async_subscribers[event_type] = []
                self._async_subscribers[event_type].append(callback)
            else:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = []
                self._subscribers[event_type].append(callback)

        logger.debug(f"Subscribed {'async ' if is_async else ''}callback to {event_type.name if event_type else 'all events'}")

    def unsubscribe(self, event_type: Optional[EventType], callback: Callable[[Event], Any]) -> bool:
        """
        Unsubscribe from events of a specific type.

        Args:
            event_type: The type of events to unsubscribe from, or None to unsubscribe from all events
            callback: The function to unsubscribe

        Returns:
            True if the callback was unsubscribed, False otherwise
        """
        is_async = asyncio.iscoroutinefunction(callback)

        if event_type is None:
            if is_async:
                if callback in self._async_wildcard_subscribers:
                    self._async_wildcard_subscribers.remove(callback)
                    logger.debug(f"Unsubscribed async callback from all events")
                    return True
            else:
                if callback in self._wildcard_subscribers:
                    self._wildcard_subscribers.remove(callback)
                    logger.debug(f"Unsubscribed callback from all events")
                    return True
        else:
            if is_async:
                if event_type in self._async_subscribers and callback in self._async_subscribers[event_type]:
                    self._async_subscribers[event_type].remove(callback)
                    logger.debug(f"Unsubscribed async callback from {event_type.name}")
                    return True
            else:
                if event_type in self._subscribers and callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
                    logger.debug(f"Unsubscribed callback from {event_type.name}")
                    return True

        return False

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish
        """
        logger.debug(f"Publishing event: {event}")

        if event.type not in self._event_history:
            self._event_history[event.type] = []

        self._event_history[event.type].append(event)

        if len(self._event_history[event.type]) > self._max_history_per_type:
            self._event_history[event.type] = self._event_history[event.type][-self._max_history_per_type:]

        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in event subscriber: {e}", exc_info=True)

        for callback in self._wildcard_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in wildcard event subscriber: {e}", exc_info=True)

        asyncio.create_task(self._publish_async(event))

    async def _publish_async(self, event: Event) -> None:
        """
        Publish an event to all async subscribers.

        Args:
            event: The event to publish
        """
        if event.type in self._async_subscribers:
            for callback in self._async_subscribers[event.type]:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"Error in async event subscriber: {e}", exc_info=True)

        for callback in self._async_wildcard_subscribers:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error in async wildcard event subscriber: {e}", exc_info=True)

    def get_event_history(self, event_type: Optional[EventType] = None, limit: int = 10) -> List[Event]:
        """
        Get the history of events of a specific type.

        Args:
            event_type: The type of events to get, or None to get all events
            limit: The maximum number of events to return

        Returns:
            A list of events
        """
        if event_type is None:
            all_events = []
            for events in self._event_history.values():
                all_events.extend(events)

            all_events.sort(key=lambda e: getattr(e, "timestamp", 0), reverse=True)

            return all_events[:limit]
        else:
            if event_type not in self._event_history:
                return []

            return self._event_history[event_type][-limit:]


event_bus = EventBus()


def subscribe(event_type: Optional[EventType] = None):
    """
    Decorator for subscribing a function to events of a specific type.

    Args:
        event_type: The type of events to subscribe to, or None to subscribe to all events

    Returns:
        A decorator function
    """
    def decorator(func):
        event_bus.subscribe(event_type, func)
        return func

    return decorator


def publish(event_type: EventType, data: Any = None, source: Optional[str] = None) -> None:
    """
    Publish an event to all subscribers.

    Args:
        event_type: The type of the event
        data: Additional data associated with the event
        source: The source component that published the event
    """
    if source is None:
        frame = inspect.currentframe()
        if frame is not None:
            frame = frame.f_back
            module = inspect.getmodule(frame)
            source = module.__name__ if module else "unknown"
        else:
            source = "unknown"

    event = Event(event_type, data, source)
    event_bus.publish(event)

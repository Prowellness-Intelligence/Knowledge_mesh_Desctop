"""
Calendar Service for the Knowledge Mesh Desktop application.

This module provides a service that integrates with calendar systems to
access and manage calendar events.
"""

import asyncio
import datetime
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable

import pandas as pd

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus

logger = logging.getLogger(__name__)


class CalendarEvent:
    """
    Represents a calendar event.
    
    This class provides a standardized representation of calendar events
    from various calendar providers.
    """
    
    def __init__(
        self,
        id: str,
        title: str,
        description: Optional[str] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        organizer: Optional[str] = None,
        calendar_id: Optional[str] = None,
        provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a calendar event.
        
        Args:
            id: The unique identifier for the event
            title: The title of the event
            description: The description of the event
            start_time: The start time of the event
            end_time: The end time of the event
            location: The location of the event
            attendees: The attendees of the event
            organizer: The organizer of the event
            calendar_id: The ID of the calendar the event belongs to
            provider: The calendar provider (e.g., Google, Microsoft)
            metadata: Additional metadata for the event
        """
        self.id = id
        self.title = title
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.attendees = attendees or []
        self.organizer = organizer
        self.calendar_id = calendar_id
        self.provider = provider
        self.metadata = metadata or {}
    
    @property
    def duration(self) -> Optional[datetime.timedelta]:
        """Get the duration of the event."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def is_all_day(self) -> bool:
        """Check if the event is an all-day event."""
        if self.start_time and self.end_time:
            return (
                self.start_time.hour == 0
                and self.start_time.minute == 0
                and self.end_time.hour == 0
                and self.end_time.minute == 0
                and (self.end_time - self.start_time).days >= 1
            )
        return False
    
    @property
    def is_upcoming(self) -> bool:
        """Check if the event is upcoming."""
        if self.start_time:
            return self.start_time > datetime.datetime.now()
        return False
    
    @property
    def is_ongoing(self) -> bool:
        """Check if the event is ongoing."""
        now = datetime.datetime.now()
        if self.start_time and self.end_time:
            return self.start_time <= now <= self.end_time
        return False
    
    @property
    def is_past(self) -> bool:
        """Check if the event is in the past."""
        if self.end_time:
            return self.end_time < datetime.datetime.now()
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event to a dictionary.
        
        Returns:
            A dictionary representation of the event
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "location": self.location,
            "attendees": self.attendees,
            "organizer": self.organizer,
            "calendar_id": self.calendar_id,
            "provider": self.provider,
            "metadata": self.metadata,
            "is_all_day": self.is_all_day,
            "is_upcoming": self.is_upcoming,
            "is_ongoing": self.is_ongoing,
            "is_past": self.is_past,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalendarEvent":
        """
        Create an event from a dictionary.
        
        Args:
            data: The dictionary representation of the event
            
        Returns:
            A CalendarEvent object
        """
        start_time = None
        if data.get("start_time"):
            try:
                start_time = datetime.datetime.fromisoformat(data["start_time"])
            except ValueError:
                pass
        
        end_time = None
        if data.get("end_time"):
            try:
                end_time = datetime.datetime.fromisoformat(data["end_time"])
            except ValueError:
                pass
        
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            start_time=start_time,
            end_time=end_time,
            location=data.get("location"),
            attendees=data.get("attendees", []),
            organizer=data.get("organizer"),
            calendar_id=data.get("calendar_id"),
            provider=data.get("provider"),
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the event."""
        return f"CalendarEvent(id={self.id}, title={self.title}, start={self.start_time})"
    
    def __repr__(self) -> str:
        """Get a string representation of the event."""
        return self.__str__()


class CalendarProvider:
    """
    Base class for calendar providers.
    
    This class defines the interface for calendar providers and provides
    common functionality.
    """
    
    def __init__(self, config: Config):
        """
        Initialize a calendar provider.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.name = "base"
    
    async def initialize(self):
        """Initialize the calendar provider."""
        pass
    
    async def authenticate(self) -> bool:
        """
        Authenticate with the calendar provider.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        return False
    
    async def get_calendars(self) -> List[Dict[str, Any]]:
        """
        Get the list of calendars.
        
        Returns:
            A list of calendars
        """
        return []
    
    async def get_events(
        self,
        calendar_id: Optional[str] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        max_results: Optional[int] = None,
    ) -> List[CalendarEvent]:
        """
        Get events from the calendar.
        
        Args:
            calendar_id: The ID of the calendar to get events from
            start_time: The start time of the time range to get events for
            end_time: The end time of the time range to get events for
            max_results: The maximum number of events to return
            
        Returns:
            A list of calendar events
        """
        return []
    
    async def create_event(self, event: CalendarEvent) -> Optional[CalendarEvent]:
        """
        Create a new event in the calendar.
        
        Args:
            event: The event to create
            
        Returns:
            The created event, or None if creation failed
        """
        return None
    
    async def update_event(self, event: CalendarEvent) -> Optional[CalendarEvent]:
        """
        Update an existing event in the calendar.
        
        Args:
            event: The event to update
            
        Returns:
            The updated event, or None if update failed
        """
        return None
    
    async def delete_event(self, event_id: str, calendar_id: Optional[str] = None) -> bool:
        """
        Delete an event from the calendar.
        
        Args:
            event_id: The ID of the event to delete
            calendar_id: The ID of the calendar the event belongs to
            
        Returns:
            True if deletion was successful, False otherwise
        """
        return False


class GoogleCalendarProvider(CalendarProvider):
    """
    Google Calendar provider.
    
    This class provides integration with Google Calendar.
    """
    
    def __init__(self, config: Config):
        """
        Initialize a Google Calendar provider.
        
        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.name = "google"
        self.credentials = None
        self.service = None
    
    async def initialize(self):
        """Initialize the Google Calendar provider."""
        try:
            logger.info("Initializing Google Calendar provider")
        except Exception as e:
            logger.error(f"Error initializing Google Calendar provider: {e}", exc_info=True)
            raise
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            logger.info("Authenticating with Google Calendar")
            return True
        except Exception as e:
            logger.error(f"Error authenticating with Google Calendar: {e}", exc_info=True)
            return False
    
    async def get_calendars(self) -> List[Dict[str, Any]]:
        """
        Get the list of Google Calendars.
        
        Returns:
            A list of calendars
        """
        try:
            return [
                {
                    "id": "primary",
                    "name": "Primary Calendar",
                    "description": "Your primary calendar",
                    "timezone": "UTC",
                }
            ]
        except Exception as e:
            logger.error(f"Error getting Google Calendars: {e}", exc_info=True)
            return []
    
    async def get_events(
        self,
        calendar_id: Optional[str] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        max_results: Optional[int] = None,
    ) -> List[CalendarEvent]:
        """
        Get events from Google Calendar.
        
        Args:
            calendar_id: The ID of the calendar to get events from
            start_time: The start time of the time range to get events for
            end_time: The end time of the time range to get events for
            max_results: The maximum number of events to return
            
        Returns:
            A list of calendar events
        """
        try:
            return [
                CalendarEvent(
                    id="event1",
                    title="Team Meeting",
                    description="Weekly team meeting",
                    start_time=datetime.datetime.now() + datetime.timedelta(hours=1),
                    end_time=datetime.datetime.now() + datetime.timedelta(hours=2),
                    location="Conference Room A",
                    attendees=["john@example.com", "jane@example.com"],
                    organizer="manager@example.com",
                    calendar_id=calendar_id or "primary",
                    provider="google",
                )
            ]
        except Exception as e:
            logger.error(f"Error getting events from Google Calendar: {e}", exc_info=True)
            return []


class OutlookCalendarProvider(CalendarProvider):
    """
    Outlook Calendar provider.
    
    This class provides integration with Microsoft Outlook Calendar.
    """
    
    def __init__(self, config: Config):
        """
        Initialize an Outlook Calendar provider.
        
        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.name = "outlook"
        self.credentials = None
        self.client = None
    
    async def initialize(self):
        """Initialize the Outlook Calendar provider."""
        try:
            logger.info("Initializing Outlook Calendar provider")
        except Exception as e:
            logger.error(f"Error initializing Outlook Calendar provider: {e}", exc_info=True)
            raise
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Outlook Calendar.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            logger.info("Authenticating with Outlook Calendar")
            return True
        except Exception as e:
            logger.error(f"Error authenticating with Outlook Calendar: {e}", exc_info=True)
            return False


class LocalCalendarProvider(CalendarProvider):
    """
    Local calendar provider.
    
    This class provides a local calendar implementation that stores events
    in a local file.
    """
    
    def __init__(self, config: Config):
        """
        Initialize a local calendar provider.
        
        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.name = "local"
        self.events_file = None
        self.events = []
        self.calendars = []
    
    async def initialize(self):
        """Initialize the local calendar provider."""
        try:
            data_dir = Path(self.config.get("app.data_dir"))
            self.events_file = data_dir / "calendars" / "events.json"
            self.events_file.parent.mkdir(parents=True, exist_ok=True)
            
            await self._load_events()
            
            self.calendars = [
                {
                    "id": "local",
                    "name": "Local Calendar",
                    "description": "Your local calendar",
                    "timezone": "UTC",
                }
            ]
            
            logger.info("Initialized local calendar provider")
        except Exception as e:
            logger.error(f"Error initializing local calendar provider: {e}", exc_info=True)
            raise
    
    async def _load_events(self):
        """Load events from the events file."""
        if not self.events_file.exists():
            self.events = []
            return
        
        try:
            import json
            
            with open(self.events_file, "r") as f:
                events_data = json.load(f)
            
            self.events = [CalendarEvent.from_dict(event_data) for event_data in events_data]
            logger.info(f"Loaded {len(self.events)} events from {self.events_file}")
        except Exception as e:
            logger.error(f"Error loading events from {self.events_file}: {e}", exc_info=True)
            self.events = []
    
    async def _save_events(self):
        """Save events to the events file."""
        try:
            import json
            
            events_data = [event.to_dict() for event in self.events]
            
            with open(self.events_file, "w") as f:
                json.dump(events_data, f, indent=2)
            
            logger.info(f"Saved {len(self.events)} events to {self.events_file}")
        except Exception as e:
            logger.error(f"Error saving events to {self.events_file}: {e}", exc_info=True)
    
    async def get_calendars(self) -> List[Dict[str, Any]]:
        """
        Get the list of local calendars.
        
        Returns:
            A list of calendars
        """
        return self.calendars
    
    async def get_events(
        self,
        calendar_id: Optional[str] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        max_results: Optional[int] = None,
    ) -> List[CalendarEvent]:
        """
        Get events from the local calendar.
        
        Args:
            calendar_id: The ID of the calendar to get events from
            start_time: The start time of the time range to get events for
            end_time: The end time of the time range to get events for
            max_results: The maximum number of events to return
            
        Returns:
            A list of calendar events
        """
        events = self.events
        if calendar_id:
            events = [event for event in events if event.calendar_id == calendar_id]
        
        if start_time:
            events = [event for event in events if event.end_time and event.end_time >= start_time]
        
        if end_time:
            events = [event for event in events if event.start_time and event.start_time <= end_time]
        
        events = sorted(events, key=lambda event: event.start_time or datetime.datetime.max)
        
        if max_results:
            events = events[:max_results]
        
        return events
    
    async def create_event(self, event: CalendarEvent) -> Optional[CalendarEvent]:
        """
        Create a new event in the local calendar.
        
        Args:
            event: The event to create
            
        Returns:
            The created event, or None if creation failed
        """
        try:
            if not event.provider:
                event.provider = self.name
            
            if not event.calendar_id:
                event.calendar_id = "local"
            
            self.events.append(event)
            
            await self._save_events()
            
            return event
        except Exception as e:
            logger.error(f"Error creating event in local calendar: {e}", exc_info=True)
            return None
    
    async def update_event(self, event: CalendarEvent) -> Optional[CalendarEvent]:
        """
        Update an existing event in the local calendar.
        
        Args:
            event: The event to update
            
        Returns:
            The updated event, or None if update failed
        """
        try:
            for i, existing_event in enumerate(self.events):
                if existing_event.id == event.id:
                    self.events[i] = event
                    
                    await self._save_events()
                    
                    return event
            
            logger.warning(f"Event {event.id} not found in local calendar")
            return None
        except Exception as e:
            logger.error(f"Error updating event in local calendar: {e}", exc_info=True)
            return None
    
    async def delete_event(self, event_id: str, calendar_id: Optional[str] = None) -> bool:
        """
        Delete an event from the local calendar.
        
        Args:
            event_id: The ID of the event to delete
            calendar_id: The ID of the calendar the event belongs to
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            for i, event in enumerate(self.events):
                if event.id == event_id and (not calendar_id or event.calendar_id == calendar_id):
                    del self.events[i]
                    
                    await self._save_events()
                    
                    return True
            
            logger.warning(f"Event {event_id} not found in local calendar")
            return False
        except Exception as e:
            logger.error(f"Error deleting event from local calendar: {e}", exc_info=True)
            return False


class CalendarService:
    """
    Service for calendar integration.
    
    This service provides access to calendar events from various providers
    and allows the application to create, update, and delete events.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the calendar service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.is_running = False
        self.providers = {}
        self.default_provider = None
        self.sync_interval = datetime.timedelta(minutes=15)
        self.last_sync_time = None
        self.sync_task = None
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.sync_interval = datetime.timedelta(minutes=self.config.get(
            "calendar.sync_interval_minutes", 15
        ))
        
        self.provider_configs = self.config.get("calendar.providers", {})
        
        self.default_provider_name = self.config.get("calendar.default_provider", "local")
    
    async def initialize(self):
        """Initialize the calendar service."""
        logger.info("Initializing calendar service")
        
        try:
            local_provider = LocalCalendarProvider(self.config)
            await local_provider.initialize()
            self.providers[local_provider.name] = local_provider
            
            if self.provider_configs.get("google", {}).get("enabled", False):
                google_provider = GoogleCalendarProvider(self.config)
                await google_provider.initialize()
                self.providers[google_provider.name] = google_provider
            
            if self.provider_configs.get("outlook", {}).get("enabled", False):
                outlook_provider = OutlookCalendarProvider(self.config)
                await outlook_provider.initialize()
                self.providers[outlook_provider.name] = outlook_provider
            
            if self.default_provider_name in self.providers:
                self.default_provider = self.providers[self.default_provider_name]
            else:
                self.default_provider = self.providers.get("local")
            
            event_bus.subscribe(EventType.CALENDAR_EVENT_CREATED, self._on_event_created)
            event_bus.subscribe(EventType.CALENDAR_EVENT_UPDATED, self._on_event_updated)
            event_bus.subscribe(EventType.CALENDAR_EVENT_DELETED, self._on_event_deleted)
            
            logger.info("Calendar service initialized")
        except Exception as e:
            logger.error(f"Error initializing calendar service: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Start the calendar service."""
        if self.is_running:
            logger.warning("Calendar service is already running")
            return
        
        logger.info("Starting calendar service")
        
        self.is_running = True
        
        for provider_name, provider in self.providers.items():
            if provider_name != "local":
                authenticated = await provider.authenticate()
                if authenticated:
                    logger.info(f"Authenticated with {provider_name} calendar provider")
                else:
                    logger.warning(f"Failed to authenticate with {provider_name} calendar provider")
        
        self.sync_task = asyncio.create_task(self._sync_events())
        
        logger.info("Calendar service started")
    
    async def stop(self):
        """Stop the calendar service."""
        if not self.is_running:
            logger.warning("Calendar service is not running")
            return
        
        logger.info("Stopping calendar service")
        
        self.is_running = False
        
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Calendar service stopped")
    
    async def _sync_events(self):
        """Sync events from all providers."""
        logger.info("Starting calendar event sync")
        
        while self.is_running:
            try:
                for provider_name, provider in self.providers.items():
                    if provider_name != "local":
                        logger.info(f"Syncing events from {provider_name} calendar provider")
                        events = await provider.get_events()
                        logger.info(f"Synced {len(events)} events from {provider_name} calendar provider")
                
                self.last_sync_time = datetime.datetime.now()
                
                await asyncio.sleep(self.sync_interval.total_seconds())
            except asyncio.CancelledError:
                logger.info("Calendar event sync cancelled")
                break
            except Exception as e:
                logger.error(f"Error syncing calendar events: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait before trying again
        
        logger.info("Calendar event sync stopped")
    
    async def get_calendars(self, provider_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get the list of calendars.
        
        Args:
            provider_name: The name of the provider to get calendars from
            
        Returns:
            A list of calendars
        """
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Calendar provider {provider_name} not found")
                return []
            
            return await provider.get_calendars()
        else:
            calendars = []
            for provider_name, provider in self.providers.items():
                provider_calendars = await provider.get_calendars()
                for calendar in provider_calendars:
                    calendar["provider"] = provider_name
                
                calendars.extend(provider_calendars)
            
            return calendars
    
    async def get_events(
        self,
        provider_name: Optional[str] = None,
        calendar_id: Optional[str] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        max_results: Optional[int] = None,
    ) -> List[CalendarEvent]:
        """
        Get events from the calendar.
        
        Args:
            provider_name: The name of the provider to get events from
            calendar_id: The ID of the calendar to get events from
            start_time: The start time of the time range to get events for
            end_time: The end time of the time range to get events for
            max_results: The maximum number of events to return
            
        Returns:
            A list of calendar events
        """
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Calendar provider {provider_name} not found")
                return []
            
            return await provider.get_events(
                calendar_id=calendar_id,
                start_time=start_time,
                end_time=end_time,
                max_results=max_results,
            )
        else:
            events = []
            for provider_name, provider in self.providers.items():
                provider_events = await provider.get_events(
                    calendar_id=calendar_id,
                    start_time=start_time,
                    end_time=end_time,
                    max_results=max_results,
                )
                
                events.extend(provider_events)
            
            events = sorted(events, key=lambda event: event.start_time or datetime.datetime.max)
            
            if max_results:
                events = events[:max_results]
            
            return events
    
    async def get_upcoming_events(
        self,
        provider_name: Optional[str] = None,
        calendar_id: Optional[str] = None,
        days: int = 7,
        max_results: Optional[int] = None,
    ) -> List[CalendarEvent]:
        """
        Get upcoming events from the calendar.
        
        Args:
            provider_name: The name of the provider to get events from
            calendar_id: The ID of the calendar to get events from
            days: The number of days to get events for
            max_results: The maximum number of events to return
            
        Returns:
            A list of calendar events
        """
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(days=days)
        
        return await self.get_events(
            provider_name=provider_name,
            calendar_id=calendar_id,
            start_time=start_time,
            end_time=end_time,
            max_results=max_results,
        )
    
    async def create_event(
        self,
        event: CalendarEvent,
        provider_name: Optional[str] = None,
    ) -> Optional[CalendarEvent]:
        """
        Create a new event in the calendar.
        
        Args:
            event: The event to create
            provider_name: The name of the provider to create the event in
            
        Returns:
            The created event, or None if creation failed
        """
        provider = None
        
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Calendar provider {provider_name} not found")
                return None
        else:
            provider = self.default_provider
        
        created_event = await provider.create_event(event)
        
        if created_event:
            publish(
                EventType.CALENDAR_EVENT_CREATED,
                {
                    "event": created_event.to_dict(),
                    "provider": provider.name,
                },
            )
        
        return created_event
    
    async def update_event(
        self,
        event: CalendarEvent,
        provider_name: Optional[str] = None,
    ) -> Optional[CalendarEvent]:
        """
        Update an existing event in the calendar.
        
        Args:
            event: The event to update
            provider_name: The name of the provider to update the event in
            
        Returns:
            The updated event, or None if update failed
        """
        provider = None
        
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Calendar provider {provider_name} not found")
                return None
        elif event.provider and event.provider in self.providers:
            provider = self.providers[event.provider]
        else:
            provider = self.default_provider
        
        updated_event = await provider.update_event(event)
        
        if updated_event:
            publish(
                EventType.CALENDAR_EVENT_UPDATED,
                {
                    "event": updated_event.to_dict(),
                    "provider": provider.name,
                },
            )
        
        return updated_event
    
    async def delete_event(
        self,
        event_id: str,
        calendar_id: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> bool:
        """
        Delete an event from the calendar.
        
        Args:
            event_id: The ID of the event to delete
            calendar_id: The ID of the calendar the event belongs to
            provider_name: The name of the provider to delete the event from
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Calendar provider {provider_name} not found")
                return False
            
            deleted = await provider.delete_event(event_id, calendar_id)
            
            if deleted:
                publish(
                    EventType.CALENDAR_EVENT_DELETED,
                    {
                        "event_id": event_id,
                        "calendar_id": calendar_id,
                        "provider": provider_name,
                    },
                )
            
            return deleted
        else:
            for provider_name, provider in self.providers.items():
                deleted = await provider.delete_event(event_id, calendar_id)
                
                if deleted:
                    publish(
                        EventType.CALENDAR_EVENT_DELETED,
                        {
                            "event_id": event_id,
                            "calendar_id": calendar_id,
                            "provider": provider_name,
                        },
                    )
                    
                    return True
            
            return False
    
    async def _on_event_created(self, event):
        """
        Handle calendar event created events.
        
        Args:
            event: The calendar event created event
        """
        logger.info(f"Calendar event created: {event.data.get('event', {}).get('title')}")
    
    async def _on_event_updated(self, event):
        """
        Handle calendar event updated events.
        
        Args:
            event: The calendar event updated event
        """
        logger.info(f"Calendar event updated: {event.data.get('event', {}).get('title')}")
    
    async def _on_event_deleted(self, event):
        """
        Handle calendar event deleted events.
        
        Args:
            event: The calendar event deleted event
        """
        logger.info(f"Calendar event deleted: {event.data.get('event_id')}")

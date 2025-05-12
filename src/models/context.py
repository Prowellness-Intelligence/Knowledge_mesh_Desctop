"""
Context model for the Knowledge Mesh Desktop application.

This module defines the Context class, which represents the user's current
context for contextual awareness and proactive interactions.
"""

import os
from datetime import datetime, time
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union, Set


class ContextType(Enum):
    """Enum defining the types of context."""
    
    DOCUMENT_FOCUS = auto()     # User is focused on a specific document
    SEARCH_CONTEXT = auto()     # User is searching for information
    TASK_CONTEXT = auto()       # User is working on a specific task
    TIME_CONTEXT = auto()       # Time-based context (morning, afternoon, etc.)
    APPLICATION_CONTEXT = auto() # User is using a specific application
    LOCATION_CONTEXT = auto()   # User's physical or virtual location
    COLLABORATION_CONTEXT = auto() # User is collaborating with others
    CUSTOM = auto()             # Custom context type


class FocusLevel(Enum):
    """Enum defining the user's focus level."""
    
    HIGHLY_FOCUSED = auto()     # User is highly focused and should not be interrupted
    FOCUSED = auto()            # User is focused but can be interrupted for important matters
    INTERRUPTIBLE = auto()      # User is interruptible
    SEEKING_INPUT = auto()      # User is actively seeking input or suggestions
    IDLE = auto()               # User is idle or away


class Context:
    """
    Represents the user's current context.
    
    A context captures the user's current state, including what they're
    working on, their focus level, and other relevant information for
    providing proactive assistance.
    """
    
    def __init__(
        self,
        id: str,
        type: ContextType,
        data: Dict[str, Any],
        focus_level: FocusLevel = FocusLevel.INTERRUPTIBLE,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a context.
        
        Args:
            id: The unique identifier for the context
            type: The type of the context
            data: The context data
            focus_level: The user's focus level in this context
            start_time: When the context started
            end_time: When the context ended (None if still active)
            active: Whether the context is currently active
            metadata: Additional metadata for the context
        """
        self.id = id
        self.type = type
        self.data = data
        self.focus_level = focus_level
        self.start_time = start_time or datetime.utcnow()
        self.end_time = end_time
        self.active = active
        self.metadata = metadata or {}
    
    @property
    def duration_seconds(self) -> float:
        """Get the duration of the context in seconds."""
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()
    
    @property
    def is_interruption_appropriate(self) -> bool:
        """
        Determine if it's appropriate to interrupt the user in this context.
        
        This considers the focus level, duration, and other factors to decide
        if a proactive notification would be appropriate.
        """
        if self.focus_level == FocusLevel.HIGHLY_FOCUSED:
            return False
        
        if self.focus_level == FocusLevel.SEEKING_INPUT:
            return True
        
        if self.focus_level == FocusLevel.FOCUSED:
            return self.duration_seconds > 300  # 5 minutes
        
        return True
    
    def end(self):
        """End the context."""
        if self.active:
            self.active = False
            self.end_time = datetime.utcnow()
    
    def update(self, data: Optional[Dict[str, Any]] = None, focus_level: Optional[FocusLevel] = None):
        """
        Update the context with new data or focus level.
        
        Args:
            data: New data to merge with existing context data
            focus_level: New focus level
        """
        if data:
            self.data.update(data)
        
        if focus_level:
            self.focus_level = focus_level
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the context to a dictionary.
        
        Returns:
            A dictionary representation of the context
        """
        return {
            "id": self.id,
            "type": self.type.name,
            "data": self.data,
            "focus_level": self.focus_level.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "active": self.active,
            "metadata": self.metadata,
            "duration_seconds": self.duration_seconds,
            "is_interruption_appropriate": self.is_interruption_appropriate,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        """
        Create a context from a dictionary.
        
        Args:
            data: The dictionary representation of the context
            
        Returns:
            A Context object
        """
        context_type = ContextType.CUSTOM
        if data.get("type"):
            try:
                context_type = ContextType[data["type"]]
            except KeyError:
                context_type = ContextType.CUSTOM
        
        focus_level = FocusLevel.INTERRUPTIBLE
        if data.get("focus_level"):
            try:
                focus_level = FocusLevel[data["focus_level"]]
            except KeyError:
                focus_level = FocusLevel.INTERRUPTIBLE
        
        start_time = None
        if data.get("start_time"):
            try:
                start_time = datetime.fromisoformat(data["start_time"])
            except ValueError:
                start_time = datetime.utcnow()
        
        end_time = None
        if data.get("end_time"):
            try:
                end_time = datetime.fromisoformat(data["end_time"])
            except ValueError:
                end_time = None
        
        return cls(
            id=data.get("id", ""),
            type=context_type,
            data=data.get("data", {}),
            focus_level=focus_level,
            start_time=start_time,
            end_time=end_time,
            active=data.get("active", True),
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the context."""
        return (
            f"Context(id={self.id}, type={self.type.name}, "
            f"focus_level={self.focus_level.name}, active={self.active})"
        )
    
    def __repr__(self) -> str:
        """Get a string representation of the context."""
        return self.__str__()

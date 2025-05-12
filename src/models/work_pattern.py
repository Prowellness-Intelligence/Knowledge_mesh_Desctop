"""
Work Pattern model for the Knowledge Mesh Desktop application.

This module defines the WorkPattern class, which represents a pattern
of user behavior that can be used for proactive interactions.
"""

import os
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union, Set


class WorkPatternType(Enum):
    """Enum defining the types of work patterns."""
    
    DOCUMENT_ACCESS = auto()      # Pattern of document access
    SEARCH_QUERY = auto()         # Pattern of search queries
    TIME_OF_DAY = auto()          # Pattern of activity at specific times
    APPLICATION_USAGE = auto()    # Pattern of application usage
    FOCUS_DURATION = auto()       # Pattern of focus duration
    BREAK_PATTERN = auto()        # Pattern of taking breaks
    COLLABORATION = auto()        # Pattern of collaboration with others
    CUSTOM = auto()               # Custom pattern type


class WorkPatternConfidence(Enum):
    """Enum defining the confidence levels for work patterns."""
    
    LOW = 1        # Low confidence (initial detection)
    MEDIUM = 2     # Medium confidence (some repetition)
    HIGH = 3       # High confidence (consistent pattern)
    VERY_HIGH = 4  # Very high confidence (strong consistent pattern)


class WorkPattern:
    """
    Represents a pattern of user behavior.
    
    A work pattern captures recurring behavior of the user that can be
    used to provide proactive assistance.
    """
    
    def __init__(
        self,
        id: str,
        type: WorkPatternType,
        data: Dict[str, Any],
        confidence: float,
        first_observed: Optional[datetime] = None,
        last_observed: Optional[datetime] = None,
        observation_count: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a work pattern.
        
        Args:
            id: The unique identifier for the pattern
            type: The type of the pattern
            data: The pattern data
            confidence: The confidence level (0.0 to 1.0)
            first_observed: When the pattern was first observed
            last_observed: When the pattern was last observed
            observation_count: How many times the pattern has been observed
            metadata: Additional metadata for the pattern
        """
        self.id = id
        self.type = type
        self.data = data
        self.confidence = confidence
        self.first_observed = first_observed or datetime.utcnow()
        self.last_observed = last_observed or datetime.utcnow()
        self.observation_count = observation_count
        self.metadata = metadata or {}
    
    @property
    def confidence_level(self) -> WorkPatternConfidence:
        """Get the confidence level of the pattern."""
        if self.confidence < 0.25:
            return WorkPatternConfidence.LOW
        elif self.confidence < 0.5:
            return WorkPatternConfidence.MEDIUM
        elif self.confidence < 0.75:
            return WorkPatternConfidence.HIGH
        else:
            return WorkPatternConfidence.VERY_HIGH
    
    @property
    def age_days(self) -> float:
        """Get the age of the pattern in days."""
        delta = datetime.utcnow() - self.first_observed
        return delta.total_seconds() / (24 * 60 * 60)
    
    @property
    def is_active(self) -> bool:
        """Check if the pattern is still active (observed in the last 7 days)."""
        delta = datetime.utcnow() - self.last_observed
        return delta.total_seconds() < 7 * 24 * 60 * 60
    
    def update_observation(self, data: Optional[Dict[str, Any]] = None):
        """
        Update the pattern with a new observation.
        
        Args:
            data: New data to merge with existing pattern data
        """
        self.last_observed = datetime.utcnow()
        self.observation_count += 1
        
        self.confidence = min(0.1 + (self.observation_count / 100) + (1.0 / (self.age_days + 1)), 1.0)
        
        if data:
            self.data.update(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the work pattern to a dictionary.
        
        Returns:
            A dictionary representation of the work pattern
        """
        return {
            "id": self.id,
            "type": self.type.name,
            "data": self.data,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.name,
            "first_observed": self.first_observed.isoformat() if self.first_observed else None,
            "last_observed": self.last_observed.isoformat() if self.last_observed else None,
            "observation_count": self.observation_count,
            "metadata": self.metadata,
            "is_active": self.is_active,
            "age_days": self.age_days,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkPattern":
        """
        Create a work pattern from a dictionary.
        
        Args:
            data: The dictionary representation of the work pattern
            
        Returns:
            A WorkPattern object
        """
        pattern_type = WorkPatternType.CUSTOM
        if data.get("type"):
            try:
                pattern_type = WorkPatternType[data["type"]]
            except KeyError:
                pattern_type = WorkPatternType.CUSTOM
        
        first_observed = None
        if data.get("first_observed"):
            try:
                first_observed = datetime.fromisoformat(data["first_observed"])
            except ValueError:
                first_observed = datetime.utcnow()
        
        last_observed = None
        if data.get("last_observed"):
            try:
                last_observed = datetime.fromisoformat(data["last_observed"])
            except ValueError:
                last_observed = datetime.utcnow()
        
        return cls(
            id=data.get("id", ""),
            type=pattern_type,
            data=data.get("data", {}),
            confidence=data.get("confidence", 0.0),
            first_observed=first_observed,
            last_observed=last_observed,
            observation_count=data.get("observation_count", 1),
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the work pattern."""
        return (
            f"WorkPattern(id={self.id}, type={self.type.name}, "
            f"confidence={self.confidence:.2f}, observations={self.observation_count})"
        )
    
    def __repr__(self) -> str:
        """Get a string representation of the work pattern."""
        return self.__str__()

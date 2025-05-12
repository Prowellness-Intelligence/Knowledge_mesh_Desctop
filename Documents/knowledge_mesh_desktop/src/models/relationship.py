"""
Relationship model for the Knowledge Mesh Desktop application.

This module defines the Relationship class, which represents a relationship
between two documents in the knowledge mesh.
"""

import os
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union


class RelationshipType(Enum):
    """Enum defining the types of relationships between documents."""
    
    SEMANTIC_SIMILARITY = auto()  # Documents are semantically similar
    KEYWORD_OVERLAP = auto()      # Documents share keywords
    REFERENCE_LINK = auto()       # One document references the other
    TEMPORAL_PROXIMITY = auto()   # Documents were created/modified close in time
    AUTHOR_SIMILARITY = auto()    # Documents share authors
    TOPIC_SIMILARITY = auto()     # Documents share topics
    PARENT_CHILD = auto()         # One document is a parent of the other
    DERIVED_FROM = auto()         # One document is derived from the other
    RELATED_TO = auto()           # Generic relationship
    CUSTOM = auto()               # Custom relationship type


class RelationshipStrength(Enum):
    """Enum defining the strength of relationships between documents."""
    
    WEAK = 1       # Weak relationship
    MODERATE = 2   # Moderate relationship
    STRONG = 3     # Strong relationship
    VERY_STRONG = 4  # Very strong relationship


class Relationship:
    """
    Represents a relationship between two documents in the knowledge mesh.
    
    A relationship connects two documents and has a type, strength, and
    optional metadata.
    """
    
    def __init__(
        self,
        source_id: str,
        target_id: str,
        type: RelationshipType,
        strength: float,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        """
        Initialize a relationship.
        
        Args:
            source_id: The ID of the source document
            target_id: The ID of the target document
            type: The type of the relationship
            strength: The strength of the relationship (0.0 to 1.0)
            metadata: Additional metadata for the relationship
            created_at: The creation timestamp
            updated_at: The last update timestamp
        """
        self.source_id = source_id
        self.target_id = target_id
        self.type = type
        self.strength = strength
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    @property
    def strength_category(self) -> RelationshipStrength:
        """Get the strength category of the relationship."""
        if self.strength < 0.25:
            return RelationshipStrength.WEAK
        elif self.strength < 0.5:
            return RelationshipStrength.MODERATE
        elif self.strength < 0.75:
            return RelationshipStrength.STRONG
        else:
            return RelationshipStrength.VERY_STRONG
    
    @property
    def is_bidirectional(self) -> bool:
        """Check if the relationship is bidirectional."""
        return self.metadata.get("bidirectional", False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the relationship to a dictionary.
        
        Returns:
            A dictionary representation of the relationship
        """
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type.name,
            "strength": self.strength,
            "strength_category": self.strength_category.name,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_bidirectional": self.is_bidirectional,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        """
        Create a relationship from a dictionary.
        
        Args:
            data: The dictionary representation of the relationship
            
        Returns:
            A Relationship object
        """
        relationship_type = RelationshipType.RELATED_TO
        if data.get("type"):
            try:
                relationship_type = RelationshipType[data["type"]]
            except KeyError:
                relationship_type = RelationshipType.CUSTOM
        
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                created_at = datetime.utcnow()
        
        updated_at = None
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(data["updated_at"])
            except ValueError:
                updated_at = datetime.utcnow()
        
        return cls(
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            type=relationship_type,
            strength=data.get("strength", 0.0),
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
        )
    
    def __str__(self) -> str:
        """Get a string representation of the relationship."""
        return (
            f"Relationship(source={self.source_id}, target={self.target_id}, "
            f"type={self.type.name}, strength={self.strength:.2f})"
        )
    
    def __repr__(self) -> str:
        """Get a string representation of the relationship."""
        return self.__str__()

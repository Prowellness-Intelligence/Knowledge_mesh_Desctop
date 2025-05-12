"""
Tests for the relationship model.

This module contains tests for the relationship model.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.models.relationship import Relationship, RelationshipType, RelationshipStrength


def test_relationship_init():
    """Test relationship initialization."""
    source_id = str(uuid4())
    target_id = str(uuid4())
    relationship_type = RelationshipType.SEMANTIC_SIMILARITY
    strength = 0.85
    metadata = {"keywords": ["test", "document"], "confidence": 0.9}
    created_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    
    relationship = Relationship(
        source_id=source_id,
        target_id=target_id,
        type=relationship_type,
        strength=strength,
        metadata=metadata,
        created_at=created_at,
        updated_at=updated_at,
    )
    
    assert relationship.source_id == source_id
    assert relationship.target_id == target_id
    assert relationship.type == relationship_type
    assert relationship.strength == strength
    assert relationship.metadata == metadata
    assert relationship.created_at == created_at
    assert relationship.updated_at == updated_at


def test_relationship_strength_category():
    """Test relationship strength category."""
    relationship = Relationship(
        source_id=str(uuid4()),
        target_id=str(uuid4()),
        type=RelationshipType.SEMANTIC_SIMILARITY,
        strength=0.2,
    )
    assert relationship.strength_category == RelationshipStrength.WEAK
    
    relationship = Relationship(
        source_id=str(uuid4()),
        target_id=str(uuid4()),
        type=RelationshipType.SEMANTIC_SIMILARITY,
        strength=0.4,
    )
    assert relationship.strength_category == RelationshipStrength.MODERATE
    
    relationship = Relationship(
        source_id=str(uuid4()),
        target_id=str(uuid4()),
        type=RelationshipType.SEMANTIC_SIMILARITY,
        strength=0.7,
    )
    assert relationship.strength_category == RelationshipStrength.STRONG
    
    relationship = Relationship(
        source_id=str(uuid4()),
        target_id=str(uuid4()),
        type=RelationshipType.SEMANTIC_SIMILARITY,
        strength=0.9,
    )
    assert relationship.strength_category == RelationshipStrength.VERY_STRONG


def test_relationship_is_bidirectional():
    """Test relationship bidirectionality."""
    relationship = Relationship(
        source_id=str(uuid4()),
        target_id=str(uuid4()),
        type=RelationshipType.PARENT_CHILD,
        strength=0.8,
        metadata={},
    )
    assert relationship.is_bidirectional is False
    
    relationship = Relationship(
        source_id=str(uuid4()),
        target_id=str(uuid4()),
        type=RelationshipType.SEMANTIC_SIMILARITY,
        strength=0.8,
        metadata={"bidirectional": True},
    )
    assert relationship.is_bidirectional is True


def test_relationship_to_dict():
    """Test converting a relationship to a dictionary."""
    source_id = str(uuid4())
    target_id = str(uuid4())
    relationship_type = RelationshipType.SEMANTIC_SIMILARITY
    strength = 0.85
    metadata = {"keywords": ["test", "document"], "confidence": 0.9}
    created_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    
    relationship = Relationship(
        source_id=source_id,
        target_id=target_id,
        type=relationship_type,
        strength=strength,
        metadata=metadata,
        created_at=created_at,
        updated_at=updated_at,
    )
    
    relationship_dict = relationship.to_dict()
    
    assert relationship_dict["source_id"] == source_id
    assert relationship_dict["target_id"] == target_id
    assert relationship_dict["type"] == relationship_type.name
    assert relationship_dict["strength"] == strength
    assert relationship_dict["strength_category"] == RelationshipStrength.VERY_STRONG.name
    assert relationship_dict["metadata"] == metadata
    assert relationship_dict["created_at"] == created_at.isoformat()
    assert relationship_dict["updated_at"] == updated_at.isoformat()
    assert relationship_dict["is_bidirectional"] is False


def test_relationship_from_dict():
    """Test creating a relationship from a dictionary."""
    source_id = str(uuid4())
    target_id = str(uuid4())
    relationship_type = "SEMANTIC_SIMILARITY"
    strength = 0.85
    metadata = {"keywords": ["test", "document"], "confidence": 0.9}
    created_at = datetime.utcnow().isoformat()
    updated_at = datetime.utcnow().isoformat()
    
    relationship_dict = {
        "source_id": source_id,
        "target_id": target_id,
        "type": relationship_type,
        "strength": strength,
        "metadata": metadata,
        "created_at": created_at,
        "updated_at": updated_at,
    }
    
    relationship = Relationship.from_dict(relationship_dict)
    
    assert relationship.source_id == source_id
    assert relationship.target_id == target_id
    assert relationship.type == RelationshipType.SEMANTIC_SIMILARITY
    assert relationship.strength == strength
    assert relationship.metadata == metadata
    assert relationship.created_at.isoformat() == created_at
    assert relationship.updated_at.isoformat() == updated_at


def test_relationship_from_dict_invalid_type():
    """Test creating a relationship from a dictionary with an invalid type."""
    source_id = str(uuid4())
    target_id = str(uuid4())
    relationship_type = "INVALID_TYPE"
    strength = 0.85
    
    relationship_dict = {
        "source_id": source_id,
        "target_id": target_id,
        "type": relationship_type,
        "strength": strength,
    }
    
    relationship = Relationship.from_dict(relationship_dict)
    
    assert relationship.source_id == source_id
    assert relationship.target_id == target_id
    assert relationship.type == RelationshipType.CUSTOM
    assert relationship.strength == strength


def test_relationship_from_dict_invalid_dates():
    """Test creating a relationship from a dictionary with invalid dates."""
    source_id = str(uuid4())
    target_id = str(uuid4())
    relationship_type = "SEMANTIC_SIMILARITY"
    strength = 0.85
    created_at = "invalid_date"
    updated_at = "invalid_date"
    
    relationship_dict = {
        "source_id": source_id,
        "target_id": target_id,
        "type": relationship_type,
        "strength": strength,
        "created_at": created_at,
        "updated_at": updated_at,
    }
    
    relationship = Relationship.from_dict(relationship_dict)
    
    assert relationship.source_id == source_id
    assert relationship.target_id == target_id
    assert relationship.type == RelationshipType.SEMANTIC_SIMILARITY
    assert relationship.strength == strength
    assert isinstance(relationship.created_at, datetime)
    assert isinstance(relationship.updated_at, datetime)

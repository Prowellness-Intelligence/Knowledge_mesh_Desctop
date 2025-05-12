"""
Tests for the knowledge mesh service.

This module contains tests for the knowledge mesh service.
"""

import os
import tempfile
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.core.config import Config
from src.core.events import EventType, Event
from src.models.document import Document, DocumentType, DocumentStatus
from src.models.relationship import Relationship, RelationshipType
from src.services.knowledge_mesh import KnowledgeMeshService


@pytest.fixture
def config():
    """Create a test configuration."""
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "knowledge_mesh.embedding_model": "all-MiniLM-L6-v2",
        "knowledge_mesh.similarity_threshold": 0.7,
        "knowledge_mesh.min_strength": 0.3,
        "knowledge_mesh.auto_detect": True,
        "knowledge_mesh.relationship_types": [
            "SEMANTIC_SIMILARITY",
            "KEYWORD_OVERLAP",
            "TEMPORAL_PROXIMITY"
        ],
        "knowledge_mesh.max_relationships": 50,
    }.get(key, default)
    return config


@pytest.fixture
def document():
    """Create a test document."""
    return Document(
        id=str(uuid4()),
        title="Test Document",
        content="This is a test document about knowledge mesh and semantic relationships.",
        file_path="/path/to/document.pdf",
        file_type=DocumentType.PDF,
        summary="A test document about knowledge mesh.",
        metadata={"author": "Test Author", "created": "2023-01-01"},
        status=DocumentStatus.PROCESSED,
    )


@pytest.fixture
def documents():
    """Create a list of test documents."""
    return [
        Document(
            id=str(uuid4()),
            title="Document 1",
            content="This is a document about knowledge mesh and semantic relationships.",
            file_path="/path/to/document1.pdf",
            file_type=DocumentType.PDF,
            status=DocumentStatus.PROCESSED,
        ),
        Document(
            id=str(uuid4()),
            title="Document 2",
            content="This is a document about vector embeddings and similarity search.",
            file_path="/path/to/document2.pdf",
            file_type=DocumentType.PDF,
            status=DocumentStatus.PROCESSED,
        ),
        Document(
            id=str(uuid4()),
            title="Document 3",
            content="This is a document about file system monitoring and document processing.",
            file_path="/path/to/document3.pdf",
            file_type=DocumentType.PDF,
            status=DocumentStatus.PROCESSED,
        ),
    ]


@pytest.mark.asyncio
async def test_knowledge_mesh_init(config):
    """Test knowledge mesh initialization."""
    service = KnowledgeMeshService(config)
    
    assert service.config == config
    assert service.is_running is False
    assert service.embedding_model == "all-MiniLM-L6-v2"
    assert service.similarity_threshold == 0.7
    assert service.min_strength == 0.3
    assert service.auto_detect is True
    assert service.relationship_types == [
        "SEMANTIC_SIMILARITY",
        "KEYWORD_OVERLAP",
        "TEMPORAL_PROXIMITY"
    ]
    assert service.max_relationships == 50


@pytest.mark.asyncio
async def test_knowledge_mesh_initialize(config):
    """Test knowledge mesh initialization."""
    service = KnowledgeMeshService(config)
    
    with patch("src.services.knowledge_mesh.event_bus") as mock_event_bus:
        await service.initialize()
        
        mock_event_bus.subscribe.assert_called_with(
            EventType.DOCUMENT_PROCESSED, service._on_document_processed
        )


@pytest.mark.asyncio
async def test_knowledge_mesh_start_stop(config):
    """Test starting and stopping the knowledge mesh."""
    service = KnowledgeMeshService(config)
    await service.initialize()
    
    await service.start()
    
    assert service.is_running is True
    
    await service.stop()
    
    assert service.is_running is False


@pytest.mark.asyncio
async def test_discover_relationships(config, document, documents):
    """Test discovering relationships."""
    service = KnowledgeMeshService(config)
    await service.initialize()
    
    vector_store_service = MagicMock()
    vector_store_service.search.return_value = asyncio.Future()
    vector_store_service.search.return_value.set_result([
        (documents[0].id, 0.9),
        (documents[1].id, 0.6),
        (documents[2].id, 0.4),
    ])
    
    document_store_service = MagicMock()
    document_store_service.get_document.side_effect = lambda doc_id: asyncio.Future()
    for doc in documents:
        future = asyncio.Future()
        future.set_result(doc)
        document_store_service.get_document.return_value = future
    
    service.vector_store_service = vector_store_service
    service.document_store_service = document_store_service
    
    service.create_relationship = MagicMock(return_value=asyncio.Future())
    service.create_relationship.return_value.set_result(None)
    
    with patch("src.services.knowledge_mesh.event_bus") as mock_event_bus:
        await service.discover_relationships(document)
        
        assert service.create_relationship.call_count == 3
        
        assert mock_event_bus.publish.call_count == 3


@pytest.mark.asyncio
async def test_create_relationship(config):
    """Test creating a relationship."""
    service = KnowledgeMeshService(config)
    await service.initialize()
    
    relationship_store_service = MagicMock()
    relationship_store_service.add_relationship.return_value = asyncio.Future()
    relationship_store_service.add_relationship.return_value.set_result(None)
    
    service.relationship_store_service = relationship_store_service
    
    source_id = str(uuid4())
    target_id = str(uuid4())
    relationship_type = RelationshipType.SEMANTIC_SIMILARITY
    strength = 0.8
    metadata = {"keywords": ["test", "document"]}
    
    with patch("src.services.knowledge_mesh.event_bus") as mock_event_bus:
        await service.create_relationship(
            source_id, target_id, relationship_type, strength, metadata
        )
        
        relationship_store_service.add_relationship.assert_called_once()
        
        mock_event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_get_relationships(config):
    """Test getting relationships."""
    service = KnowledgeMeshService(config)
    await service.initialize()
    
    relationship_store_service = MagicMock()
    relationship_store_service.get_relationships.return_value = asyncio.Future()
    relationship_store_service.get_relationships.return_value.set_result([
        Relationship(
            source_id=str(uuid4()),
            target_id=str(uuid4()),
            type=RelationshipType.SEMANTIC_SIMILARITY,
            strength=0.8,
        ),
        Relationship(
            source_id=str(uuid4()),
            target_id=str(uuid4()),
            type=RelationshipType.KEYWORD_OVERLAP,
            strength=0.6,
        ),
    ])
    
    service.relationship_store_service = relationship_store_service
    
    document_id = str(uuid4())
    relationships = await service.get_relationships(document_id)
    
    relationship_store_service.get_relationships.assert_called_with(document_id)
    assert len(relationships) == 2


@pytest.mark.asyncio
async def test_delete_relationship(config):
    """Test deleting a relationship."""
    service = KnowledgeMeshService(config)
    await service.initialize()
    
    relationship_store_service = MagicMock()
    relationship_store_service.delete_relationship.return_value = asyncio.Future()
    relationship_store_service.delete_relationship.return_value.set_result(None)
    
    service.relationship_store_service = relationship_store_service
    
    source_id = str(uuid4())
    target_id = str(uuid4())
    
    with patch("src.services.knowledge_mesh.event_bus") as mock_event_bus:
        await service.delete_relationship(source_id, target_id)
        
        relationship_store_service.delete_relationship.assert_called_with(source_id, target_id)
        
        mock_event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_on_document_processed(config, document):
    """Test handling document processed events."""
    service = KnowledgeMeshService(config)
    await service.initialize()
    
    document_store_service = MagicMock()
    document_store_service.get_document.return_value = asyncio.Future()
    document_store_service.get_document.return_value.set_result(document)
    
    service.document_store_service = document_store_service
    
    service.discover_relationships = MagicMock(return_value=asyncio.Future())
    service.discover_relationships.return_value.set_result(None)
    
    event = Event(
        type=EventType.DOCUMENT_PROCESSED,
        data={"document_id": document.id}
    )
    
    await service._on_document_processed(event)
    
    document_store_service.get_document.assert_called_with(document.id)
    service.discover_relationships.assert_called_with(document)

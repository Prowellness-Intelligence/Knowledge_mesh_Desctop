"""
Tests for the vector store service.

This module contains tests for the vector store service.
"""

import os
import tempfile
import pytest
import asyncio
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.core.config import Config
from src.core.events import EventType, Event
from src.models.document import Document, DocumentType, DocumentStatus, DocumentChunk
from src.services.vector_store import VectorStoreService


@pytest.fixture
def config():
    """Create a test configuration."""
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "vector_store.embedding_model": "all-MiniLM-L6-v2",
        "vector_store.embedding_dimension": 384,
        "vector_store.similarity_metric": "cosine",
        "vector_store.index_path": "/tmp/vector_store",
        "vector_store.batch_size": 32,
        "vector_store.use_gpu": False,
    }.get(key, default)
    return config


@pytest.fixture
def document():
    """Create a test document."""
    return Document(
        id=str(uuid4()),
        title="Test Document",
        content="This is a test document about vector embeddings and semantic search.",
        file_path="/path/to/document.pdf",
        file_type=DocumentType.PDF,
        summary="A test document about vector embeddings.",
        metadata={"author": "Test Author", "created": "2023-01-01"},
        status=DocumentStatus.PROCESSED,
    )


@pytest.fixture
def document_chunk():
    """Create a test document chunk."""
    doc_id = str(uuid4())
    return DocumentChunk(
        id=str(uuid4()),
        document_id=doc_id,
        content="This is a test chunk about vector embeddings and semantic search.",
        chunk_index=0,
        metadata={"position": "beginning"},
    )


@pytest.mark.asyncio
async def test_vector_store_init(config):
    """Test vector store initialization."""
    service = VectorStoreService(config)
    
    assert service.config == config
    assert service.is_running is False
    assert service.embedding_model == "all-MiniLM-L6-v2"
    assert service.embedding_dimension == 384
    assert service.similarity_metric == "cosine"
    assert service.index_path == "/tmp/vector_store"
    assert service.batch_size == 32
    assert service.use_gpu is False


@pytest.mark.asyncio
async def test_vector_store_initialize(config):
    """Test vector store initialization."""
    service = VectorStoreService(config)
    
    with patch("src.services.vector_store.event_bus") as mock_event_bus:
        with patch("src.services.vector_store.SentenceTransformer") as mock_transformer:
            await service.initialize()
            
            mock_event_bus.subscribe.assert_called_with(
                EventType.DOCUMENT_PROCESSED, service._on_document_processed
            )
            
            mock_transformer.assert_called_with("all-MiniLM-L6-v2")


@pytest.mark.asyncio
async def test_vector_store_start_stop(config):
    """Test starting and stopping the vector store."""
    service = VectorStoreService(config)
    
    with patch("src.services.vector_store.SentenceTransformer"):
        await service.initialize()
    
    await service.start()
    
    assert service.is_running is True
    
    await service.stop()
    
    assert service.is_running is False


@pytest.mark.asyncio
async def test_add_document(config, document):
    """Test adding a document to the vector store."""
    service = VectorStoreService(config)
    
    with patch("src.services.vector_store.SentenceTransformer"):
        await service.initialize()
    
    service.model = MagicMock()
    service.model.encode.return_value = np.random.rand(1, 384)
    
    service.index = MagicMock()
    
    await service.add_document(document)
    
    service.model.encode.assert_called_with(document.content)
    service.index.add_items.assert_called_once()


@pytest.mark.asyncio
async def test_add_chunk(config, document_chunk):
    """Test adding a document chunk to the vector store."""
    service = VectorStoreService(config)
    
    with patch("src.services.vector_store.SentenceTransformer"):
        await service.initialize()
    
    service.model = MagicMock()
    service.model.encode.return_value = np.random.rand(1, 384)
    
    service.index = MagicMock()
    
    await service.add_chunk(document_chunk)
    
    service.model.encode.assert_called_with(document_chunk.content)
    service.index.add_items.assert_called_once()


@pytest.mark.asyncio
async def test_search(config):
    """Test searching the vector store."""
    service = VectorStoreService(config)
    
    with patch("src.services.vector_store.SentenceTransformer"):
        await service.initialize()
    
    service.model = MagicMock()
    service.model.encode.return_value = np.random.rand(384)
    
    service.index = MagicMock()
    service.index.search.return_value = (
        np.array([[0.9, 0.8, 0.7]]),
        np.array([["doc1", "doc2", "doc3"]])
    )
    
    results = await service.search("test query", limit=3)
    
    service.model.encode.assert_called_with("test query")
    service.index.search.assert_called_once()
    
    assert len(results) == 3
    assert results[0][0] == "doc1"
    assert results[0][1] == 0.9
    assert results[1][0] == "doc2"
    assert results[1][1] == 0.8
    assert results[2][0] == "doc3"
    assert results[2][1] == 0.7


@pytest.mark.asyncio
async def test_delete_document(config):
    """Test deleting a document from the vector store."""
    service = VectorStoreService(config)
    
    with patch("src.services.vector_store.SentenceTransformer"):
        await service.initialize()
    
    service.index = MagicMock()
    
    document_id = str(uuid4())
    await service.delete_document(document_id)
    
    service.index.delete_items.assert_called_with([document_id])


@pytest.mark.asyncio
async def test_on_document_processed(config, document):
    """Test handling document processed events."""
    service = VectorStoreService(config)
    
    with patch("src.services.vector_store.SentenceTransformer"):
        await service.initialize()
    
    document_store_service = MagicMock()
    document_store_service.get_document.return_value = asyncio.Future()
    document_store_service.get_document.return_value.set_result(document)
    
    service.document_store_service = document_store_service
    
    service.add_document = MagicMock(return_value=asyncio.Future())
    service.add_document.return_value.set_result(None)
    
    event = Event(
        type=EventType.DOCUMENT_PROCESSED,
        data={"document_id": document.id}
    )
    
    await service._on_document_processed(event)
    
    document_store_service.get_document.assert_called_with(document.id)
    service.add_document.assert_called_with(document)

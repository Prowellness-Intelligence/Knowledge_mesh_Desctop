"""
Tests for the document model.

This module contains tests for the document model.
"""

import os
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from src.models.document import Document, DocumentType, DocumentStatus, DocumentChunk


def test_document_init():
    """Test document initialization."""
    doc_id = str(uuid4())
    title = "Test Document"
    content = "This is a test document."
    file_path = "/path/to/document.pdf"
    file_type = DocumentType.PDF
    summary = "A test document."
    metadata = {"author": "Test Author", "created": "2023-01-01"}
    status = DocumentStatus.PROCESSED
    created_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    
    doc = Document(
        id=doc_id,
        title=title,
        content=content,
        file_path=file_path,
        file_type=file_type,
        summary=summary,
        metadata=metadata,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
    )
    
    assert doc.id == doc_id
    assert doc.title == title
    assert doc.content == content
    assert doc.file_path == file_path
    assert doc.file_type == file_type
    assert doc.summary == summary
    assert doc.metadata == metadata
    assert doc.status == status
    assert doc.created_at == created_at
    assert doc.updated_at == updated_at
    assert doc.chunks == []


def test_document_properties():
    """Test document properties."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"Test content")
        file_path = f.name
    
    try:
        doc = Document(
            id=str(uuid4()),
            title="Test Document",
            content="This is a test document with some words.",
            file_path=file_path,
            file_type=DocumentType.PDF,
        )
        
        assert doc.filename == os.path.basename(file_path)
        assert doc.extension == ".pdf"
        assert doc.size == len(b"Test content")
        assert doc.word_count == 7  # "This is a test document with some words."
        assert doc.is_processed is False
    finally:
        os.unlink(file_path)


def test_document_add_chunk():
    """Test adding a chunk to a document."""
    doc = Document(
        id=str(uuid4()),
        title="Test Document",
        content="This is a test document.",
    )
    
    chunk = DocumentChunk(
        id=str(uuid4()),
        document_id=doc.id,
        content="This is a test chunk.",
        chunk_index=0,
    )
    
    doc.add_chunk(chunk)
    
    assert len(doc.chunks) == 1
    assert doc.chunks[0] == chunk


def test_document_to_dict():
    """Test converting a document to a dictionary."""
    doc_id = str(uuid4())
    title = "Test Document"
    content = "This is a test document."
    file_path = "/path/to/document.pdf"
    file_type = DocumentType.PDF
    summary = "A test document."
    metadata = {"author": "Test Author", "created": "2023-01-01"}
    status = DocumentStatus.PROCESSED
    created_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    
    doc = Document(
        id=doc_id,
        title=title,
        content=content,
        file_path=file_path,
        file_type=file_type,
        summary=summary,
        metadata=metadata,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
    )
    
    doc_dict = doc.to_dict()
    
    assert doc_dict["id"] == doc_id
    assert doc_dict["title"] == title
    assert doc_dict["content"] == content
    assert doc_dict["file_path"] == file_path
    assert doc_dict["file_type"] == file_type.name
    assert doc_dict["summary"] == summary
    assert doc_dict["metadata"] == metadata
    assert doc_dict["status"] == status.name
    assert doc_dict["created_at"] == created_at.isoformat()
    assert doc_dict["updated_at"] == updated_at.isoformat()


def test_document_from_dict():
    """Test creating a document from a dictionary."""
    doc_id = str(uuid4())
    title = "Test Document"
    content = "This is a test document."
    file_path = "/path/to/document.pdf"
    file_type = "PDF"
    summary = "A test document."
    metadata = {"author": "Test Author", "created": "2023-01-01"}
    status = "PROCESSED"
    created_at = datetime.utcnow().isoformat()
    updated_at = datetime.utcnow().isoformat()
    
    doc_dict = {
        "id": doc_id,
        "title": title,
        "content": content,
        "file_path": file_path,
        "file_type": file_type,
        "summary": summary,
        "metadata": metadata,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
    }
    
    doc = Document.from_dict(doc_dict)
    
    assert doc.id == doc_id
    assert doc.title == title
    assert doc.content == content
    assert doc.file_path == file_path
    assert doc.file_type == DocumentType.PDF
    assert doc.summary == summary
    assert doc.metadata == metadata
    assert doc.status == DocumentStatus.PROCESSED
    assert doc.created_at.isoformat() == created_at
    assert doc.updated_at.isoformat() == updated_at


def test_document_chunk_init():
    """Test document chunk initialization."""
    chunk_id = str(uuid4())
    document_id = str(uuid4())
    content = "This is a test chunk."
    metadata = {"position": "beginning"}
    chunk_index = 0
    
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=document_id,
        content=content,
        metadata=metadata,
        chunk_index=chunk_index,
    )
    
    assert chunk.id == chunk_id
    assert chunk.document_id == document_id
    assert chunk.content == content
    assert chunk.metadata == metadata
    assert chunk.chunk_index == chunk_index


def test_document_chunk_to_dict():
    """Test converting a document chunk to a dictionary."""
    chunk_id = str(uuid4())
    document_id = str(uuid4())
    content = "This is a test chunk."
    metadata = {"position": "beginning"}
    chunk_index = 0
    
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=document_id,
        content=content,
        metadata=metadata,
        chunk_index=chunk_index,
    )
    
    chunk_dict = chunk.to_dict()
    
    assert chunk_dict["id"] == chunk_id
    assert chunk_dict["document_id"] == document_id
    assert chunk_dict["content"] == content
    assert chunk_dict["metadata"] == metadata
    assert chunk_dict["chunk_index"] == chunk_index


def test_document_chunk_from_dict():
    """Test creating a document chunk from a dictionary."""
    chunk_id = str(uuid4())
    document_id = str(uuid4())
    content = "This is a test chunk."
    metadata = {"position": "beginning"}
    chunk_index = 0
    
    chunk_dict = {
        "id": chunk_id,
        "document_id": document_id,
        "content": content,
        "metadata": metadata,
        "chunk_index": chunk_index,
    }
    
    chunk = DocumentChunk.from_dict(chunk_dict)
    
    assert chunk.id == chunk_id
    assert chunk.document_id == document_id
    assert chunk.content == content
    assert chunk.metadata == metadata
    assert chunk.chunk_index == chunk_index

"""
Tests for the document processor service.

This module contains tests for the document processor service.
"""

import os
import tempfile
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.config import Config
from src.core.events import EventType, Event
from src.models.document import Document, DocumentType, DocumentStatus
from src.services.document_processor import DocumentProcessorService


@pytest.fixture
def config():
    """Create a test configuration."""
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "document_processor.chunk_size": 1000,
        "document_processor.chunk_overlap": 200,
        "document_processor.extract_metadata": True,
        "document_processor.generate_summaries": True,
        "document_processor.summary_length": 200,
        "document_processor.ocr_enabled": True,
        "document_processor.ocr_language": "eng",
        "document_processor.max_workers": 4,
    }.get(key, default)
    return config


@pytest.fixture
def test_pdf_file():
    """Create a temporary PDF file."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.5\n%Test PDF file\nTest content")
        yield f.name
    
    os.unlink(f.name)


@pytest.fixture
def test_docx_file():
    """Create a temporary DOCX file."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        f.write(b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00Test content")
        yield f.name
    
    os.unlink(f.name)


@pytest.fixture
def test_txt_file():
    """Create a temporary TXT file."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"This is a test document.\nIt has multiple lines.\nAnd some content.")
        yield f.name
    
    os.unlink(f.name)


@pytest.mark.asyncio
async def test_document_processor_init(config):
    """Test document processor initialization."""
    service = DocumentProcessorService(config)
    
    assert service.config == config
    assert service.is_running is False
    assert service.chunk_size == 1000
    assert service.chunk_overlap == 200
    assert service.extract_metadata is True
    assert service.generate_summaries is True
    assert service.summary_length == 200
    assert service.ocr_enabled is True
    assert service.ocr_language == "eng"
    assert service.max_workers == 4


@pytest.mark.asyncio
async def test_document_processor_initialize(config):
    """Test document processor initialization."""
    service = DocumentProcessorService(config)
    
    with patch("src.services.document_processor.event_bus") as mock_event_bus:
        await service.initialize()
        
        mock_event_bus.subscribe.assert_called_with(
            EventType.FILE_DETECTED, service._on_file_detected
        )


@pytest.mark.asyncio
async def test_document_processor_start_stop(config):
    """Test starting and stopping the document processor."""
    service = DocumentProcessorService(config)
    await service.initialize()
    
    await service.start()
    
    assert service.is_running is True
    
    await service.stop()
    
    assert service.is_running is False


@pytest.mark.asyncio
async def test_process_document_txt(config, test_txt_file):
    """Test processing a TXT document."""
    service = DocumentProcessorService(config)
    await service.initialize()
    
    with patch("src.services.document_processor.event_bus") as mock_event_bus:
        document = await service.process_document(test_txt_file)
        
        assert document is not None
        assert document.file_path == test_txt_file
        assert document.file_type == DocumentType.TXT
        assert document.content == "This is a test document.\nIt has multiple lines.\nAnd some content."
        assert document.status == DocumentStatus.PROCESSED
        
        mock_event_bus.publish.assert_called_with(
            EventType.DOCUMENT_PROCESSED,
            {"document_id": document.id}
        )


@pytest.mark.asyncio
async def test_extract_text_txt(config, test_txt_file):
    """Test extracting text from a TXT document."""
    service = DocumentProcessorService(config)
    await service.initialize()
    
    text, metadata = await service.extract_text(test_txt_file)
    
    assert text == "This is a test document.\nIt has multiple lines.\nAnd some content."
    assert metadata["file_type"] == "TXT"
    assert metadata["file_path"] == test_txt_file
    assert metadata["file_name"] == os.path.basename(test_txt_file)
    assert metadata["file_size"] > 0
    assert "created_at" in metadata
    assert "updated_at" in metadata


@pytest.mark.asyncio
async def test_generate_summary(config):
    """Test generating a summary."""
    service = DocumentProcessorService(config)
    await service.initialize()
    
    text = "This is a test document. It has multiple lines. And some content. " * 10
    summary = await service.generate_summary(text)
    
    assert summary is not None
    assert len(summary) <= service.summary_length


@pytest.mark.asyncio
async def test_chunk_document(config):
    """Test chunking a document."""
    service = DocumentProcessorService(config)
    await service.initialize()
    
    document = Document(
        id="test_id",
        title="Test Document",
        content="This is a test document. " * 1000,
        file_path="/path/to/document.txt",
        file_type=DocumentType.TXT,
    )
    
    chunks = await service.chunk_document(document)
    
    assert chunks is not None
    assert len(chunks) > 0
    assert chunks[0].document_id == document.id
    assert chunks[0].chunk_index == 0
    assert len(chunks[0].content) <= service.chunk_size
    
    if len(chunks) > 1:
        assert chunks[0].content[-service.chunk_overlap:] == chunks[1].content[:service.chunk_overlap]


@pytest.mark.asyncio
async def test_on_file_detected(config, test_txt_file):
    """Test handling file detected events."""
    service = DocumentProcessorService(config)
    await service.initialize()
    
    service.process_document = MagicMock(return_value=asyncio.Future())
    service.process_document.return_value.set_result(None)
    
    event = Event(
        type=EventType.FILE_DETECTED,
        data={"file_path": test_txt_file}
    )
    
    await service._on_file_detected(event)
    
    service.process_document.assert_called_with(test_txt_file)

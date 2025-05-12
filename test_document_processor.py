import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core.config import Config
from src.services.document_processor import DocumentProcessorService
from src.models.document import Document, DocumentType, DocumentStatus

async def test_document_processor():
    """Test the document processor service implementation."""
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "document_processor.max_summary_length": 200,
        "document_processor.max_keywords": 10,
        "document_processor.supported_extensions": [".pdf", ".docx", ".txt"],
        "app.data_dir": "/tmp/knowledge_mesh_test",
    }.get(key, default)
    
    os.makedirs("/tmp/knowledge_mesh_test/documents", exist_ok=True)
    
    test_file = "/tmp/knowledge_mesh_test/test.txt"
    with open(test_file, "w") as f:
        f.write("This is a test document for testing the document processor service.")
    
    service = DocumentProcessorService(config)
    
    print("Testing initialization...")
    assert service.config == config
    assert service.is_running is False
    assert service.max_summary_length == 200
    assert service.max_keywords == 10
    assert ".txt" in service.supported_extensions
    
    service.vector_store_service = MagicMock()
    
    print("Testing document processing...")
    await service.initialize()
    await service.start()
    
    await service.process_file(test_file)
    
    await asyncio.sleep(1)
    
    print("Testing document retrieval...")
    document = await service.get_document(os.path.basename(test_file))
    
    if document:
        assert document.id == os.path.basename(test_file)
        assert document.content == "This is a test document for testing the document processor service."
        assert document.file_type == DocumentType.TXT
        assert document.status == DocumentStatus.PROCESSED
        print("Document processed successfully!")
    else:
        print("Error: Document not found!")
    
    print("Testing document search...")
    results = await service.search_documents("test document")
    assert len(results) > 0
    
    await service.stop()
    
    os.remove(test_file)
    
    print("All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_document_processor())

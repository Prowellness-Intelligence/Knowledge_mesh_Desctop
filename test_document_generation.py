"""
Test file for the Document Generation Service of the Knowledge Mesh Desktop application.

This module provides tests for the AI-powered document generation functionality.
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.core.config import Config
from src.core.events import EventType, Event, event_bus
from src.models.document import Document, DocumentType, DocumentStatus
from src.models.document_generation import (
    GenerationRequest, GeneratedContent, GenerationFormat, 
    GenerationTemplate, GenerationStatus
)
from src.models.relationship import RelationshipType
from src.services.document_generation import DocumentGenerationService


class TestDocumentGeneration(unittest.TestCase):
    """Test the Document Generation Service."""
    
    def setUp(self):
        """Set up the test environment."""
        self.config = Config({
            "app.data_dir": "./test_data",
            "document_generation.enabled": True,
            "document_generation.max_concurrent_generations": 2,
            "document_generation.ai_model": "test-model",
            "document_generation.ai_temperature": 0.7,
            "document_generation.ai_max_tokens": 1000,
        })
        
        self.document_processor = MagicMock()
        self.knowledge_mesh = MagicMock()
        self.vector_store = MagicMock()
        self.llm_service = MagicMock()
        
        self.services = {
            "document_processor": self.document_processor,
            "knowledge_mesh": self.knowledge_mesh,
            "vector_store": self.vector_store,
            "llm": self.llm_service,
        }
        
        self.service = DocumentGenerationService(self.config, self.services)
        
        os.makedirs("./test_data/document_generation/requests", exist_ok=True)
        os.makedirs("./test_data/document_generation/content", exist_ok=True)
        os.makedirs("./test_data/temp", exist_ok=True)
        
        self.mock_document1 = Document(
            id="doc1",
            title="Test Document 1",
            content="This is the content of test document 1.",
            file_path="/path/to/doc1.txt",
            file_type=DocumentType.TXT,
            status=DocumentStatus.PROCESSED,
        )
        
        self.mock_document2 = Document(
            id="doc2",
            title="Test Document 2",
            content="This is the content of test document 2.",
            file_path="/path/to/doc2.txt",
            file_type=DocumentType.TXT,
            status=DocumentStatus.PROCESSED,
        )
        
        self.document_processor.get_document.side_effect = self._mock_get_document
        self.document_processor.create_document.side_effect = self._mock_create_document
        
        self.llm_service.generate_text.side_effect = self._mock_generate_text
    
    def tearDown(self):
        """Clean up the test environment."""
        import shutil
        if os.path.exists("./test_data"):
            shutil.rmtree("./test_data")
    
    def _mock_get_document(self, doc_id):
        """Mock getting a document."""
        if doc_id == "doc1":
            return self.mock_document1
        elif doc_id == "doc2":
            return self.mock_document2
        return None
    
    def _mock_create_document(self, title, file_path, file_type, metadata=None):
        """Mock creating a document."""
        return Document(
            id=f"generated_{datetime.utcnow().timestamp()}",
            title=title,
            content="Generated document content",
            file_path=file_path,
            file_type=file_type,
            status=DocumentStatus.PROCESSED,
            metadata=metadata or {},
        )
    
    def _mock_generate_text(self, system_prompt, user_prompt, model, temperature, max_tokens):
        """Mock generating text with an LLM."""
        return f"""# Generated Content

This is a test generated document based on the provided documents.


The documents contain test content.


The documents include:
- Test Document 1
- Test Document 2


- Model: {model}
- Temperature: {temperature}
- Max Tokens: {max_tokens}
"""
    
    def test_initialization(self):
        """Test service initialization."""
        self.assertEqual(self.service.config, self.config)
        self.assertEqual(self.service.services, self.services)
        self.assertFalse(self.service.is_running)
        self.assertEqual(self.service.requests_cache, {})
        self.assertEqual(self.service.content_cache, {})
        self.assertEqual(self.service.max_concurrent_generations, 2)
        self.assertEqual(self.service.ai_model, "test-model")
        self.assertEqual(self.service.ai_temperature, 0.7)
        self.assertEqual(self.service.ai_max_tokens, 1000)
        self.assertIsNotNone(self.service.templates)
        self.assertIn(GenerationTemplate.SUMMARY, self.service.templates)
        self.assertIn(GenerationTemplate.REPORT, self.service.templates)
    
    async def _test_create_generation_request(self):
        """Test creating a generation request."""
        await self.service.initialize()
        await self.service.start()
        
        request = await self.service.create_generation_request(
            user_id="user1",
            title="Test Generation",
            source_document_ids=["doc1", "doc2"],
            format=GenerationFormat.MARKDOWN,
            template=GenerationTemplate.SUMMARY,
        )
        
        self.assertIsNotNone(request)
        self.assertEqual(request.user_id, "user1")
        self.assertEqual(request.title, "Test Generation")
        self.assertEqual(request.source_document_ids, ["doc1", "doc2"])
        self.assertEqual(request.format, GenerationFormat.MARKDOWN)
        self.assertEqual(request.template, GenerationTemplate.SUMMARY)
        self.assertEqual(request.status, GenerationStatus.PENDING)
        
        self.assertIn(request.id, self.service.requests_cache)
        
        self.assertEqual(self.service.generation_queue.qsize(), 1)
        
        await self.service.stop()
    
    async def _test_get_generation_request(self):
        """Test getting a generation request."""
        await self.service.initialize()
        await self.service.start()
        
        request = await self.service.create_generation_request(
            user_id="user1",
            title="Test Generation",
            source_document_ids=["doc1", "doc2"],
            format=GenerationFormat.MARKDOWN,
            template=GenerationTemplate.SUMMARY,
        )
        
        retrieved_request = await self.service.get_generation_request(request.id)
        
        self.assertIsNotNone(retrieved_request)
        self.assertEqual(retrieved_request.id, request.id)
        self.assertEqual(retrieved_request.user_id, "user1")
        self.assertEqual(retrieved_request.title, "Test Generation")
        
        non_existent_request = await self.service.get_generation_request("non_existent")
        
        self.assertIsNone(non_existent_request)
        
        await self.service.stop()
    
    async def _test_cancel_generation_request(self):
        """Test cancelling a generation request."""
        await self.service.initialize()
        await self.service.start()
        
        request = await self.service.create_generation_request(
            user_id="user1",
            title="Test Generation",
            source_document_ids=["doc1", "doc2"],
            format=GenerationFormat.MARKDOWN,
            template=GenerationTemplate.SUMMARY,
        )
        
        result = await self.service.cancel_generation_request(request.id)
        
        self.assertTrue(result)
        
        cancelled_request = await self.service.get_generation_request(request.id)
        
        self.assertIsNotNone(cancelled_request)
        self.assertEqual(cancelled_request.status, GenerationStatus.CANCELLED)
        
        result = await self.service.cancel_generation_request("non_existent")
        
        self.assertFalse(result)
        
        await self.service.stop()
    
    async def _test_get_user_requests(self):
        """Test getting user requests."""
        await self.service.initialize()
        await self.service.start()
        
        request1 = await self.service.create_generation_request(
            user_id="user1",
            title="Test Generation 1",
            source_document_ids=["doc1"],
            format=GenerationFormat.MARKDOWN,
            template=GenerationTemplate.SUMMARY,
        )
        
        request2 = await self.service.create_generation_request(
            user_id="user1",
            title="Test Generation 2",
            source_document_ids=["doc2"],
            format=GenerationFormat.HTML,
            template=GenerationTemplate.REPORT,
        )
        
        request3 = await self.service.create_generation_request(
            user_id="user2",
            title="Test Generation 3",
            source_document_ids=["doc1", "doc2"],
            format=GenerationFormat.PDF,
            template=GenerationTemplate.NOTES,
        )
        
        user1_requests = await self.service.get_user_requests("user1")
        
        self.assertEqual(len(user1_requests), 2)
        self.assertIn(request1, user1_requests)
        self.assertIn(request2, user1_requests)
        
        user2_requests = await self.service.get_user_requests("user2")
        
        self.assertEqual(len(user2_requests), 1)
        self.assertIn(request3, user2_requests)
        
        non_existent_user_requests = await self.service.get_user_requests("non_existent")
        
        self.assertEqual(len(non_existent_user_requests), 0)
        
        await self.service.stop()
    
    async def _test_document_generation(self):
        """Test the document generation process."""
        await self.service.initialize()
        await self.service.start()
        
        request = await self.service.create_generation_request(
            user_id="user1",
            title="Test Generation",
            source_document_ids=["doc1", "doc2"],
            format=GenerationFormat.MARKDOWN,
            template=GenerationTemplate.SUMMARY,
        )
        
        for _ in range(10):
            updated_request = await self.service.get_generation_request(request.id)
            
            if updated_request.status == GenerationStatus.COMPLETED:
                break
            
            await asyncio.sleep(0.5)
        
        updated_request = await self.service.get_generation_request(request.id)
        
        self.assertIsNotNone(updated_request)
        self.assertEqual(updated_request.status, GenerationStatus.COMPLETED)
        self.assertIsNotNone(updated_request.result_document_id)
        
        content = await self.service.get_request_content(request.id)
        
        self.assertIsNotNone(content)
        self.assertEqual(content.request_id, request.id)
        self.assertEqual(content.format, GenerationFormat.MARKDOWN)
        self.assertIn("Generated Content", content.content)
        
        self.document_processor.create_document.assert_called_once()
        
        self.knowledge_mesh.create_relationship.assert_called()
        
        await self.service.stop()
    
    async def _test_fallback_generation(self):
        """Test fallback generation when LLM service is not available."""
        service_without_llm = DocumentGenerationService(
            self.config,
            {
                "document_processor": self.document_processor,
                "knowledge_mesh": self.knowledge_mesh,
                "vector_store": self.vector_store,
            },
        )
        
        await service_without_llm.initialize()
        await service_without_llm.start()
        
        request = await service_without_llm.create_generation_request(
            user_id="user1",
            title="Fallback Generation",
            source_document_ids=["doc1", "doc2"],
            format=GenerationFormat.MARKDOWN,
            template=GenerationTemplate.SUMMARY,
        )
        
        for _ in range(10):
            updated_request = await service_without_llm.get_generation_request(request.id)
            
            if updated_request.status == GenerationStatus.COMPLETED:
                break
            
            await asyncio.sleep(0.5)
        
        updated_request = await service_without_llm.get_generation_request(request.id)
        
        self.assertIsNotNone(updated_request)
        self.assertEqual(updated_request.status, GenerationStatus.COMPLETED)
        
        content = await service_without_llm.get_request_content(request.id)
        
        self.assertIsNotNone(content)
        self.assertIn("# Fallback Generation", content.content)
        self.assertIn("Document Contents", content.content)
        
        await service_without_llm.stop()
    
    def test_all(self):
        """Run all tests."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self._test_create_generation_request())
        loop.run_until_complete(self._test_get_generation_request())
        loop.run_until_complete(self._test_cancel_generation_request())
        loop.run_until_complete(self._test_get_user_requests())
        loop.run_until_complete(self._test_document_generation())
        loop.run_until_complete(self._test_fallback_generation())


if __name__ == "__main__":
    unittest.main()

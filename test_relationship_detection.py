import sys
import os
import asyncio
import pickle
from unittest.mock import MagicMock, patch
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core.config import Config
from src.services.knowledge_mesh import KnowledgeMeshService
from src.services.document_processor import DocumentProcessorService
from src.services.vector_store import VectorStoreService
from src.models.document import Document, DocumentType, DocumentStatus
from src.models.relationship import Relationship, RelationshipType, RelationshipStrength

async def test_relationship_detection():
    """Test the relationship detection functionality."""
    test_dir = Path("/tmp/knowledge_mesh_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    doc1 = Document(
        id="doc1",
        title="Machine Learning Basics",
        content="This document covers the basics of machine learning, including supervised and unsupervised learning.",
        file_path="/tmp/knowledge_mesh_test/doc1.txt",
        file_type=DocumentType.TXT,
        metadata={
            "keywords": ["machine learning", "supervised learning", "unsupervised learning"],
            "authors": ["John Doe"],
            "created_at": "2023-01-01T12:00:00",
        },
        status=DocumentStatus.PROCESSED,
    )
    
    doc2 = Document(
        id="doc2",
        title="Deep Learning Introduction",
        content="Deep learning is a subset of machine learning that uses neural networks with many layers.",
        file_path="/tmp/knowledge_mesh_test/doc2.txt",
        file_type=DocumentType.TXT,
        metadata={
            "keywords": ["deep learning", "neural networks", "machine learning"],
            "authors": ["Jane Smith"],
            "created_at": "2023-01-05T14:30:00",
        },
        status=DocumentStatus.PROCESSED,
    )
    
    doc3 = Document(
        id="doc3",
        title="Reinforcement Learning",
        content="Reinforcement learning is an area of machine learning concerned with how agents take actions in an environment.",
        file_path="/tmp/knowledge_mesh_test/doc3.txt",
        file_type=DocumentType.TXT,
        metadata={
            "keywords": ["reinforcement learning", "machine learning", "agents"],
            "authors": ["John Doe", "Jane Smith"],
            "created_at": "2023-01-10T09:15:00",
            "references": ["doc1", "doc2"],
        },
        status=DocumentStatus.PROCESSED,
    )
    
    docs_dir = test_dir / "documents"
    docs_dir.mkdir(exist_ok=True)
    
    for doc in [doc1, doc2, doc3]:
        with open(docs_dir / f"{doc.id}.pkl", "wb") as f:
            pickle.dump(doc.to_dict(), f)
    
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "knowledge_mesh.relationship_threshold": 0.3,
        "knowledge_mesh.max_relationships_per_document": 10,
        "app.data_dir": str(test_dir),
    }.get(key, default)
    
    doc_processor = MagicMock(spec=DocumentProcessorService)
    doc_processor.get_document.side_effect = lambda doc_id: asyncio.Future().set_result(
        next((doc for doc in [doc1, doc2, doc3] if doc.id == doc_id), None)
    )
    
    vector_store = MagicMock(spec=VectorStoreService)
    vector_store.search.side_effect = lambda query, limit=None: asyncio.Future().set_result(
        [("doc2", 0.85), ("doc3", 0.75)] if "machine" in query else 
        [("doc1", 0.80), ("doc3", 0.70)] if "deep" in query else
        [("doc1", 0.65), ("doc2", 0.60)]
    )
    
    service = KnowledgeMeshService(config)
    service.document_processor_service = doc_processor
    service.vector_store_service = vector_store
    
    await service.initialize()
    await service.start()
    
    print("Testing relationship detection...")
    
    await service._analyze_document_relationships("doc1")
    
    relationships = await service.get_document_relationships("doc1")
    assert len(relationships) > 0, "No relationships found for doc1"
    
    related_docs = await service.get_related_documents("doc1")
    assert len(related_docs) > 0, "No related documents found for doc1"
    
    semantic_relationships = await service.get_document_relationships(
        "doc1", relationship_types=[RelationshipType.SEMANTIC_SIMILARITY]
    )
    assert any(r.type == RelationshipType.SEMANTIC_SIMILARITY for r in semantic_relationships), \
        "No semantic similarity relationships found"
    
    await service.rebuild_mesh()
    
    await service.stop()
    
    print("All relationship detection tests passed!")

if __name__ == "__main__":
    asyncio.run(test_relationship_detection())

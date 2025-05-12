"""
Knowledge Mesh Service for the Knowledge Mesh Desktop application.

This module provides a service that analyzes documents and detects relationships
between them, building a "knowledge mesh" that connects related information
across different documents.
"""

import asyncio
import logging
import os
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus
from ..models.document import Document
from ..models.relationship import Relationship, RelationshipType, RelationshipStrength

logger = logging.getLogger(__name__)


class KnowledgeMeshService:
    """
    Service for building and maintaining the knowledge mesh.
    
    This service analyzes documents and detects relationships between them,
    building a "knowledge mesh" that connects related information across
    different documents.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the knowledge mesh service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.is_running = False
        self.processing_queue = asyncio.Queue()
        self.processing_task = None
        self.relationship_detection_methods = []
        self.relationship_threshold = 0.7  # Default threshold for relationship detection
        self.max_relationships_per_document = 20
        self.vector_store_service = None
        self.document_processor_service = None
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.relationship_threshold = self.config.get(
            "knowledge_mesh.relationship_threshold", 0.7
        )
        
        self.max_relationships_per_document = self.config.get(
            "knowledge_mesh.max_relationships_per_document", 20
        )
    
    async def initialize(self):
        """Initialize the knowledge mesh service."""
        logger.info("Initializing knowledge mesh service")
        
        self.relationship_detection_methods = [
            self._detect_semantic_similarity,
            self._detect_keyword_overlap,
            self._detect_reference_links,
            self._detect_temporal_proximity,
            self._detect_author_similarity,
            self._detect_topic_similarity,
        ]
        
        event_bus.subscribe(EventType.DOCUMENT_INDEXED, self._on_document_indexed)
        
        logger.info("Knowledge mesh service initialized")
    
    async def start(self):
        """Start the knowledge mesh service."""
        if self.is_running:
            logger.warning("Knowledge mesh service is already running")
            return
        
        logger.info("Starting knowledge mesh service")
        
        self.is_running = True
        
        self.processing_task = asyncio.create_task(self._process_documents())
        
        logger.info("Knowledge mesh service started")
    
    async def stop(self):
        """Stop the knowledge mesh service."""
        if not self.is_running:
            logger.warning("Knowledge mesh service is not running")
            return
        
        logger.info("Stopping knowledge mesh service")
        
        self.is_running = False
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Knowledge mesh service stopped")
    
    async def _process_documents(self):
        """Process documents in the queue."""
        while self.is_running:
            try:
                document_id = await self.processing_queue.get()
                
                await self._analyze_document_relationships(document_id)
                
                self.processing_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing document: {e}", exc_info=True)
    
    async def _on_document_indexed(self, event):
        """
        Handle document indexed events.
        
        Args:
            event: The document indexed event
        """
        document_id = event.data.get("document_id")
        if document_id:
            await self.processing_queue.put(document_id)
    
    async def _analyze_document_relationships(self, document_id: str):
        """
        Analyze relationships for a document.
        
        Args:
            document_id: The ID of the document to analyze
        """
        logger.info(f"Analyzing relationships for document {document_id}")
        
        try:
            document = await self._get_document(document_id)
            if not document:
                logger.warning(f"Document {document_id} not found")
                return
            
            candidate_documents = await self._get_candidate_documents(document)
            
            relationships = []
            for candidate in candidate_documents:
                relationship = await self._detect_relationship(document, candidate)
                if relationship:
                    relationships.append(relationship)
            
            relationships.sort(key=lambda r: r.strength, reverse=True)
            relationships = relationships[:self.max_relationships_per_document]
            
            await self._save_relationships(document, relationships)
            
            publish(
                EventType.KNOWLEDGE_MESH_UPDATED,
                {
                    "document_id": document_id,
                    "relationship_count": len(relationships),
                },
            )
            
            logger.info(f"Found {len(relationships)} relationships for document {document_id}")
        except Exception as e:
            logger.error(f"Error analyzing relationships for document {document_id}: {e}", exc_info=True)
    
    async def _get_document(self, document_id: str) -> Optional[Document]:
        """
        Get a document by ID.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            The document, or None if not found
        """
        if self.document_processor_service:
            return await self.document_processor_service.get_document(document_id)
        
        logger.warning(f"Document processor service not available, cannot get document {document_id}")
        return None
    
    async def _get_candidate_documents(self, document: Document) -> List[Document]:
        """
        Get candidate documents for relationship detection.
        
        Args:
            document: The document to find relationships for
            
        Returns:
            A list of candidate documents
        """
        candidates = []
        
        # Use vector store to find semantically similar documents
        if self.vector_store_service and document.content:
            search_results = await self.vector_store_service.search(document.content)
            
            for doc_id, similarity in search_results:
                if doc_id != document.id:  # Skip the document itself
                    candidate = await self._get_document(doc_id)
                    if candidate:
                        candidates.append(candidate)
        
        # If we don't have enough candidates, get some recent documents
        if len(candidates) < self.max_relationships_per_document and self.document_processor_service:
            # This would typically query a database for recent documents
            pass
        
        return candidates
    
    async def _detect_relationship(
        self, document: Document, candidate: Document
    ) -> Optional[Relationship]:
        """
        Detect a relationship between two documents.
        
        Args:
            document: The source document
            candidate: The candidate document
            
        Returns:
            A relationship, or None if no relationship is detected
        """
        scores = []
        for method in self.relationship_detection_methods:
            score = await method(document, candidate)
            if score is not None:
                scores.append(score)
        
        if not scores:
            return None
        
        strength = sum(scores) / len(scores)
        
        if strength < self.relationship_threshold:
            return None
        
        relationship_type = RelationshipType.SEMANTIC_SIMILARITY
        
        return Relationship(
            source_id=document.id,
            target_id=candidate.id,
            type=relationship_type,
            strength=strength,
            metadata={},
        )
    
    async def _save_relationships(self, document: Document, relationships: List[Relationship]):
        """
        Save relationships for a document.
        
        Args:
            document: The source document
            relationships: The relationships to save
        """
        try:
            data_dir = Path(self.config.get("app.data_dir", "."))
            relationships_dir = data_dir / "relationships"
            relationships_dir.mkdir(parents=True, exist_ok=True)
            
            # Save relationships for the document
            relationship_path = relationships_dir / f"{document.id}.pkl"
            
            relationship_dicts = [r.to_dict() for r in relationships]
            
            with open(relationship_path, "wb") as f:
                pickle.dump(relationship_dicts, f)
            
            for relationship in relationships:
                logger.debug(
                    f"Relationship: {relationship.source_id} -> {relationship.target_id} "
                    f"({relationship.type.name}, {relationship.strength:.2f})"
                )
            
            logger.info(f"Saved {len(relationships)} relationships for document {document.id}")
        except Exception as e:
            logger.error(f"Error saving relationships for document {document.id}: {e}", exc_info=True)
    
    async def _detect_semantic_similarity(
        self, document: Document, candidate: Document
    ) -> Optional[float]:
        """
        Detect semantic similarity between two documents.
        
        Args:
            document: The source document
            candidate: The candidate document
            
        Returns:
            A similarity score between 0 and 1, or None if similarity cannot be determined
        """
        if document.embedding is None or candidate.embedding is None:
            return None
        
        similarity = cosine_similarity(
            document.embedding.reshape(1, -1), candidate.embedding.reshape(1, -1)
        )[0][0]
        
        return float(similarity)
    
    async def _detect_keyword_overlap(
        self, document: Document, candidate: Document
    ) -> Optional[float]:
        """
        Detect keyword overlap between two documents.
        
        Args:
            document: The source document
            candidate: The candidate document
            
        Returns:
            A similarity score between 0 and 1, or None if similarity cannot be determined
        """
        if not document.metadata.get("keywords") or not candidate.metadata.get("keywords"):
            return None
        
        doc_keywords = set(document.metadata["keywords"])
        candidate_keywords = set(candidate.metadata["keywords"])
        
        if not doc_keywords or not candidate_keywords:
            return None
        
        intersection = len(doc_keywords.intersection(candidate_keywords))
        union = len(doc_keywords.union(candidate_keywords))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    async def _detect_reference_links(
        self, document: Document, candidate: Document
    ) -> Optional[float]:
        """
        Detect reference links between two documents.
        
        Args:
            document: The source document
            candidate: The candidate document
            
        Returns:
            A similarity score between 0 and 1, or None if similarity cannot be determined
        """
        if not document.metadata.get("references") or not candidate.metadata.get("references"):
            return None
        
        doc_references = document.metadata["references"]
        candidate_references = candidate.metadata["references"]
        
        if candidate.id in doc_references:
            return 1.0
        elif document.id in candidate_references:
            return 0.8
        else:
            return 0.0
    
    async def _detect_temporal_proximity(
        self, document: Document, candidate: Document
    ) -> Optional[float]:
        """
        Detect temporal proximity between two documents.
        
        Args:
            document: The source document
            candidate: The candidate document
            
        Returns:
            A similarity score between 0 and 1, or None if similarity cannot be determined
        """
        if not document.metadata.get("created_at") or not candidate.metadata.get("created_at"):
            return None
        
        doc_date = document.metadata["created_at"]
        candidate_date = candidate.metadata["created_at"]
        
        if not isinstance(doc_date, datetime) or not isinstance(candidate_date, datetime):
            return None
        
        time_diff = abs((doc_date - candidate_date).total_seconds() / (24 * 3600))
        
        max_days = 30  # Maximum number of days to consider
        if time_diff > max_days:
            return 0.0
        
        return np.exp(-time_diff / max_days)
    
    async def _detect_author_similarity(
        self, document: Document, candidate: Document
    ) -> Optional[float]:
        """
        Detect author similarity between two documents.
        
        Args:
            document: The source document
            candidate: The candidate document
            
        Returns:
            A similarity score between 0 and 1, or None if similarity cannot be determined
        """
        if not document.metadata.get("authors") or not candidate.metadata.get("authors"):
            return None
        
        doc_authors = set(document.metadata["authors"])
        candidate_authors = set(candidate.metadata["authors"])
        
        if not doc_authors or not candidate_authors:
            return None
        
        intersection = len(doc_authors.intersection(candidate_authors))
        union = len(doc_authors.union(candidate_authors))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    async def _detect_topic_similarity(
        self, document: Document, candidate: Document
    ) -> Optional[float]:
        """
        Detect topic similarity between two documents.
        
        Args:
            document: The source document
            candidate: The candidate document
            
        Returns:
            A similarity score between 0 and 1, or None if similarity cannot be determined
        """
        if not document.metadata.get("topics") or not candidate.metadata.get("topics"):
            return None
        
        doc_topics = document.metadata["topics"]
        candidate_topics = candidate.metadata["topics"]
        
        if not isinstance(doc_topics, dict) or not isinstance(candidate_topics, dict):
            return None
        
        all_topics = set(doc_topics.keys()).union(set(candidate_topics.keys()))
        
        if not all_topics:
            return 0.0
        
        similarity = 0.0
        for topic in all_topics:
            doc_weight = doc_topics.get(topic, 0.0)
            candidate_weight = candidate_topics.get(topic, 0.0)
            
            similarity += min(doc_weight, candidate_weight)
        
        max_similarity = min(sum(doc_topics.values()), sum(candidate_topics.values()))
        
        if max_similarity == 0:
            return 0.0
        
        return similarity / max_similarity
    
    async def get_document_relationships(self, document_id: str, relationship_types: Optional[List[RelationshipType]] = None) -> List[Relationship]:
        """
        Get relationships for a document.
        
        Args:
            document_id: The ID of the document
            relationship_types: Optional list of relationship types to filter by
            
        Returns:
            A list of relationships
        """
        try:
            data_dir = Path(self.config.get("app.data_dir", "."))
            relationships_dir = data_dir / "relationships"
            relationship_path = relationships_dir / f"{document_id}.pkl"
            
            if not relationship_path.exists():
                logger.debug(f"No relationships found for document {document_id}")
                return []
            
            with open(relationship_path, "rb") as f:
                relationship_dicts = pickle.load(f)
            
            relationships = [Relationship.from_dict(r_dict) for r_dict in relationship_dicts]
            
            if relationship_types:
                relationships = [r for r in relationships if r.type in relationship_types]
            
            return relationships
        except Exception as e:
            logger.error(f"Error getting relationships for document {document_id}: {e}", exc_info=True)
            return []
    
    async def get_related_documents(
        self, document_id: str, relationship_types: Optional[List[RelationshipType]] = None
    ) -> List[Document]:
        """
        Get related documents for a document.
        
        Args:
            document_id: The ID of the document
            relationship_types: Optional list of relationship types to filter by
            
        Returns:
            A list of related documents
        """
        try:
            # Get relationships for the document
            relationships = await self.get_document_relationships(document_id, relationship_types)
            
            if not relationships:
                return []
            
            # Get related document IDs
            related_doc_ids = [r.target_id for r in relationships]
            
            # Get related documents
            related_docs = []
            for doc_id in related_doc_ids:
                doc = await self._get_document(doc_id)
                if doc:
                    related_docs.append(doc)
            
            return related_docs
        except Exception as e:
            logger.error(f"Error getting related documents for {document_id}: {e}", exc_info=True)
            return []
    
    async def rebuild_mesh(self):
        """Rebuild the entire knowledge mesh."""
        logger.info("Rebuilding knowledge mesh")
        
        try:
            # Get all documents
            if self.document_processor_service:
                # This would typically query a database for all documents
                data_dir = Path(self.config.get("app.data_dir", "."))
                documents_dir = data_dir / "documents"
                
                if not documents_dir.exists():
                    logger.warning("Documents directory not found, cannot rebuild mesh")
                    return
                
                for document_path in documents_dir.glob("*.pkl"):
                    try:
                        document_id = document_path.stem
                        await self._analyze_document_relationships(document_id)
                        logger.info(f"Processed relationships for document {document_id}")
                    except Exception as e:
                        logger.error(f"Error processing document {document_path}: {e}", exc_info=True)
            else:
                logger.warning("Document processor service not available, cannot rebuild mesh")
            
            logger.info("Knowledge mesh rebuilt")
        except Exception as e:
            logger.error(f"Error rebuilding knowledge mesh: {e}", exc_info=True)

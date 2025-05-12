"""
Vector Store Service for the Knowledge Mesh Desktop application.

This module provides a service that manages vector embeddings for documents
and enables semantic search across the knowledge mesh.
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

import numpy as np
import faiss
import pickle
from sentence_transformers import SentenceTransformer

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus
from ..models.document import Document, DocumentChunk

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Service for managing vector embeddings and semantic search.
    
    This service manages vector embeddings for documents and enables
    semantic search across the knowledge mesh.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the vector store service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.is_running = False
        self.embedding_model = None
        self.index = None
        self.document_ids = []
        self.chunk_ids = []
        self.embedding_dimension = 768  # Default for most sentence transformers
        self.embedding_batch_size = 32
        self.similarity_threshold = 0.7
        self.max_results = 20
        self.index_path = None
        self.metadata_path = None
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.embedding_model_name = self.config.get(
            "vector_store.embedding_model", "all-MiniLM-L6-v2"
        )
        
        self.embedding_dimension = self.config.get(
            "vector_store.embedding_dimension", 768
        )
        
        self.embedding_batch_size = self.config.get(
            "vector_store.embedding_batch_size", 32
        )
        
        self.similarity_threshold = self.config.get(
            "vector_store.similarity_threshold", 0.7
        )
        
        self.max_results = self.config.get(
            "vector_store.max_results", 20
        )
        
        data_dir = Path(self.config.get("app.data_dir"))
        vector_dir = data_dir / "vector_store"
        vector_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_path = str(vector_dir / "faiss_index.bin")
        self.metadata_path = str(vector_dir / "metadata.pkl")
    
    async def initialize(self):
        """Initialize the vector store service."""
        logger.info("Initializing vector store service")
        
        try:
            # Load the embedding model
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
            
            # Update the embedding dimension based on the model
            self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Embedding dimension: {self.embedding_dimension}")
            
            # Create or load the index
            if (self.index_path and os.path.exists(self.index_path) and 
                self.metadata_path and os.path.exists(self.metadata_path)):
                await self._load_index()
            else:
                self._create_index()
            
            # Subscribe to events
            event_bus.subscribe(EventType.DOCUMENT_PROCESSING_COMPLETED, self._on_document_processed)
            
            logger.info("Vector store service initialized")
        except Exception as e:
            logger.error(f"Error initializing vector store service: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Start the vector store service."""
        if self.is_running:
            logger.warning("Vector store service is already running")
            return
        
        logger.info("Starting vector store service")
        
        self.is_running = True
        
        logger.info("Vector store service started")
    
    async def stop(self):
        """Stop the vector store service."""
        if not self.is_running:
            logger.warning("Vector store service is not running")
            return
        
        logger.info("Stopping vector store service")
        
        self.is_running = False
        
        # Save the index
        if self.index is not None:
            await self._save_index()
        
        logger.info("Vector store service stopped")
    
    def _create_index(self):
        """Create a new FAISS index."""
        logger.info("Creating new FAISS index")
        
        # Create a new index
        self.index = faiss.IndexFlatL2(self.embedding_dimension)
        
        # Initialize metadata
        self.document_ids = []
        self.chunk_ids = []
        
        logger.info("FAISS index created")
    
    async def _load_index(self):
        """Load the FAISS index from disk."""
        logger.info("Loading FAISS index")
        
        try:
            # Load the index
            if self.index_path:
                self.index = faiss.read_index(self.index_path)
            
                # Load metadata
                if self.metadata_path:
                    with open(self.metadata_path, "rb") as f:
                        metadata = pickle.load(f)
                        self.document_ids = metadata.get("document_ids", [])
                        self.chunk_ids = metadata.get("chunk_ids", [])
            
                logger.info(f"Loaded FAISS index with {len(self.document_ids)} documents and {len(self.chunk_ids)} chunks")
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}", exc_info=True)
            self._create_index()
    
    async def _save_index(self):
        """Save the FAISS index to disk."""
        logger.info("Saving FAISS index")
        
        try:
            # Save the index
            if self.index is not None and self.index_path:
                faiss.write_index(self.index, self.index_path)
            
                # Save metadata
                if self.metadata_path:
                    with open(self.metadata_path, "wb") as f:
                        metadata = {
                            "document_ids": self.document_ids,
                            "chunk_ids": self.chunk_ids,
                        }
                        pickle.dump(metadata, f)
            
                logger.info(f"Saved FAISS index with {len(self.document_ids)} documents and {len(self.chunk_ids)} chunks")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}", exc_info=True)
    
    async def _on_document_processed(self, event):
        """
        Handle document processed events.
        
        Args:
            event: The document processed event
        """
        document_id = event.data.get("document_id")
        if document_id:
            # Get the document
            document = await self._get_document(document_id)
            if document:
                # Index the document
                await self.index_document(document)
    
    async def _get_document(self, document_id: str) -> Optional[Document]:
        """
        Get a document by ID.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            The document, or None if not found
        """
        # This would typically query a database or document store
        # For now, we'll return a mock document
        return Document(
            id=document_id,
            title=f"Document {document_id}",
            content="Sample content",
            metadata={},
        )
    
    async def index_document(self, document: Document):
        """
        Index a document in the vector store.
        
        Args:
            document: The document to index
        """
        logger.info(f"Indexing document: {document.id}")
        
        try:
            # Check if the document is already indexed
            if document.id in self.document_ids:
                # Remove the existing document
                await self.remove_document(document.id)
            
            # Generate embeddings for the document
            if document.content and self.index is not None:
                # If the document has chunks, index each chunk
                if document.chunks:
                    for chunk in document.chunks:
                        await self.index_chunk(chunk)
                else:
                    # Generate an embedding for the document
                    embedding = self._generate_embedding(document.content)
                    
                    # Add the embedding to the index
                    self.index.add(np.array([embedding], dtype=np.float32))
                    
                    # Add the document ID to the metadata
                    self.document_ids.append(document.id)
                    
                    # Save the embedding to the document
                    document.embedding = embedding
            
            # Publish event
            publish(
                EventType.DOCUMENT_INDEXED,
                {
                    "document_id": document.id,
                },
            )
            
            logger.info(f"Document indexed: {document.id}")
        except Exception as e:
            logger.error(f"Error indexing document {document.id}: {e}", exc_info=True)
    
    async def index_chunk(self, chunk: DocumentChunk):
        """
        Index a document chunk in the vector store.
        
        Args:
            chunk: The chunk to index
        """
        logger.debug(f"Indexing chunk: {chunk.id}")
        
        try:
            # Check if the chunk is already indexed
            if chunk.id in self.chunk_ids:
                # Remove the existing chunk
                await self.remove_chunk(chunk.id)
            
            # Generate an embedding for the chunk
            if chunk.content and self.index is not None:
                embedding = self._generate_embedding(chunk.content)
                
                # Add the embedding to the index
                self.index.add(np.array([embedding], dtype=np.float32))
                
                # Add the chunk ID to the metadata
                self.chunk_ids.append(chunk.id)
                
                # Save the embedding to the chunk
                chunk.embedding = embedding
            
            logger.debug(f"Chunk indexed: {chunk.id}")
        except Exception as e:
            logger.error(f"Error indexing chunk {chunk.id}: {e}", exc_info=True)
    
    async def remove_document(self, document_id: str):
        """
        Remove a document from the vector store.
        
        Args:
            document_id: The ID of the document to remove
        """
        logger.info(f"Removing document: {document_id}")
        
        try:
            # Find the indices of the document in the metadata
            indices = [i for i, doc_id in enumerate(self.document_ids) if doc_id == document_id]
            
            if indices and self.index is not None:
                # Create a new index without the document
                new_index = faiss.IndexFlatL2(self.embedding_dimension)
                
                # Get all vectors
                all_vectors = np.array([self.index.reconstruct(i) for i in range(self.index.ntotal)], dtype=np.float32)
                
                # Create a mask for vectors to keep
                mask = np.ones(self.index.ntotal, dtype=bool)
                for idx in indices:
                    mask[idx] = False
                
                # Add vectors to keep to the new index
                if np.any(mask):
                    new_index.add(all_vectors[mask])
                
                # Update metadata
                self.document_ids = [doc_id for i, doc_id in enumerate(self.document_ids) if i not in indices]
                
                # Replace the index
                self.index = new_index
                
                logger.info(f"Document removed: {document_id}")
            else:
                logger.warning(f"Document not found in index: {document_id}")
        except Exception as e:
            logger.error(f"Error removing document {document_id}: {e}", exc_info=True)
    
    async def remove_chunk(self, chunk_id: str):
        """
        Remove a chunk from the vector store.
        
        Args:
            chunk_id: The ID of the chunk to remove
        """
        logger.debug(f"Removing chunk: {chunk_id}")
        
        try:
            # Find the index of the chunk in the metadata
            indices = [i for i, c_id in enumerate(self.chunk_ids) if c_id == chunk_id]
            
            if indices and self.index is not None:
                # Create a new index without the chunk
                new_index = faiss.IndexFlatL2(self.embedding_dimension)
                
                # Get all vectors
                all_vectors = np.array([self.index.reconstruct(i) for i in range(self.index.ntotal)], dtype=np.float32)
                
                # Create a mask for vectors to keep
                mask = np.ones(self.index.ntotal, dtype=bool)
                for idx in indices:
                    mask[idx] = False
                
                # Add vectors to keep to the new index
                if np.any(mask):
                    new_index.add(all_vectors[mask])
                
                # Update metadata
                self.chunk_ids = [c_id for i, c_id in enumerate(self.chunk_ids) if i not in indices]
                
                # Replace the index
                self.index = new_index
                
                logger.debug(f"Chunk removed: {chunk_id}")
            else:
                logger.warning(f"Chunk not found in index: {chunk_id}")
        except Exception as e:
            logger.error(f"Error removing chunk {chunk_id}: {e}", exc_info=True)
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate an embedding for a text.
        
        Args:
            text: The text to embed
            
        Returns:
            The embedding vector
        """
        # Truncate text if it's too long
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
        
        # Generate the embedding
        if self.embedding_model is not None:
            embedding = self.embedding_model.encode(text, show_progress_bar=False)
            return embedding
        
        # Return a zero vector if the embedding model is not available
        return np.zeros(self.embedding_dimension, dtype=np.float32)
    
    async def search(self, query: str, limit: int = None) -> List[Tuple[str, float]]:
        """
        Search for documents similar to a query.
        
        Args:
            query: The search query
            limit: The maximum number of results to return
            
        Returns:
            A list of (document_id, similarity) tuples
        """
        if not self.index or self.index.ntotal == 0:
            return []
        
        if not limit:
            limit = self.max_results
        
        # Generate an embedding for the query
        query_embedding = self._generate_embedding(query)
        
        # Search the index
        distances, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32), limit
        )
        
        # Convert distances to similarities (1 - normalized distance)
        max_distance = np.max(distances)
        if max_distance > 0:
            similarities = 1 - distances[0] / max_distance
        else:
            similarities = np.ones_like(distances[0])
        
        # Get the document IDs for the results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.document_ids):
                doc_id = self.document_ids[idx]
                similarity = similarities[i]
                
                # Only include results above the threshold
                if similarity >= self.similarity_threshold:
                    results.append((doc_id, similarity))
            elif idx < len(self.document_ids) + len(self.chunk_ids):
                chunk_idx = idx - len(self.document_ids)
                chunk_id = self.chunk_ids[chunk_idx]
                similarity = similarities[i]
                
                # Only include results above the threshold
                if similarity >= self.similarity_threshold:
                    # Extract the document ID from the chunk ID
                    doc_id = chunk_id.split("_")[0]
                    results.append((doc_id, similarity))
        
        return results
    
    async def get_similar_documents(self, document_id: str, limit: int = None) -> List[Tuple[str, float]]:
        """
        Get documents similar to a document.
        
        Args:
            document_id: The ID of the document
            limit: The maximum number of results to return
            
        Returns:
            A list of (document_id, similarity) tuples
        """
        # Get the document
        document = await self._get_document(document_id)
        if not document or not document.content:
            return []
        
        # Search using the document content
        return await self.search(document.content, limit)

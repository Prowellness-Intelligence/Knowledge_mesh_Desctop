"""
Document model for the Knowledge Mesh Desktop application.

This module defines the Document class, which represents a document in the
knowledge mesh.
"""

import os
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union

import numpy as np


class DocumentType(Enum):
    """Enum defining the types of documents that can be processed."""
    
    PDF = auto()
    DOCX = auto()
    TXT = auto()
    MARKDOWN = auto()
    CSV = auto()
    EXCEL = auto()
    IMAGE = auto()
    EMAIL = auto()
    CALENDAR = auto()
    WEBPAGE = auto()
    UNKNOWN = auto()


class DocumentStatus(Enum):
    """Enum defining the status of a document in the system."""
    
    PENDING = auto()
    PROCESSING = auto()
    PROCESSED = auto()
    FAILED = auto()
    DELETED = auto()


class Document:
    """
    Represents a document in the knowledge mesh.
    
    A document can be a file, email, calendar event, or any other type of
    content that can be processed and indexed.
    """
    
    def __init__(
        self,
        id: str,
        title: str,
        content: str,
        file_path: Optional[str] = None,
        file_type: Optional[DocumentType] = None,
        embedding: Optional[np.ndarray] = None,
        summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: DocumentStatus = DocumentStatus.PENDING,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        """
        Initialize a document.
        
        Args:
            id: The unique identifier for the document
            title: The title of the document
            content: The text content of the document
            file_path: The path to the document file, if applicable
            file_type: The type of the document
            embedding: The vector embedding of the document
            summary: A summary of the document
            metadata: Additional metadata for the document
            status: The status of the document
            created_at: The creation timestamp
            updated_at: The last update timestamp
        """
        self.id = id
        self.title = title
        self.content = content
        self.file_path = file_path
        self.file_type = file_type or DocumentType.UNKNOWN
        self.embedding = embedding
        self.summary = summary
        self.metadata = metadata or {}
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.chunks = []
    
    @property
    def filename(self) -> Optional[str]:
        """Get the filename of the document, if applicable."""
        if self.file_path:
            return os.path.basename(self.file_path)
        return None
    
    @property
    def extension(self) -> Optional[str]:
        """Get the file extension of the document, if applicable."""
        if self.file_path:
            _, ext = os.path.splitext(self.file_path)
            return ext.lower()
        return None
    
    @property
    def size(self) -> Optional[int]:
        """Get the file size of the document in bytes, if applicable."""
        if self.file_path and os.path.exists(self.file_path):
            return os.path.getsize(self.file_path)
        return None
    
    @property
    def word_count(self) -> int:
        """Get the word count of the document."""
        if not self.content:
            return 0
        return len(self.content.split())
    
    @property
    def is_processed(self) -> bool:
        """Check if the document has been processed."""
        return self.status == DocumentStatus.PROCESSED
    
    def add_chunk(self, chunk: "DocumentChunk"):
        """
        Add a chunk to the document.
        
        Args:
            chunk: The chunk to add
        """
        self.chunks.append(chunk)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the document to a dictionary.
        
        Returns:
            A dictionary representation of the document
        """
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "file_path": self.file_path,
            "file_type": self.file_type.name if self.file_type else None,
            "summary": self.summary,
            "metadata": self.metadata,
            "status": self.status.name if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "word_count": self.word_count,
            "size": self.size,
            "filename": self.filename,
            "extension": self.extension,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """
        Create a document from a dictionary.
        
        Args:
            data: The dictionary representation of the document
            
        Returns:
            A Document object
        """
        file_type = None
        if data.get("file_type"):
            try:
                file_type = DocumentType[data["file_type"]]
            except KeyError:
                file_type = DocumentType.UNKNOWN
        
        status = DocumentStatus.PENDING
        if data.get("status"):
            try:
                status = DocumentStatus[data["status"]]
            except KeyError:
                pass
        
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                created_at = datetime.utcnow()
        
        updated_at = None
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(data["updated_at"])
            except ValueError:
                updated_at = datetime.utcnow()
        
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            file_path=data.get("file_path"),
            file_type=file_type,
            summary=data.get("summary"),
            metadata=data.get("metadata", {}),
            status=status,
            created_at=created_at,
            updated_at=updated_at,
        )
    
    def __str__(self) -> str:
        """Get a string representation of the document."""
        return f"Document(id={self.id}, title={self.title}, type={self.file_type.name if self.file_type else 'None'})"
    
    def __repr__(self) -> str:
        """Get a string representation of the document."""
        return self.__str__()


class DocumentChunk:
    """
    Represents a chunk of a document.
    
    Documents are split into chunks for more effective processing and indexing.
    Each chunk has its own embedding and can be indexed separately.
    """
    
    def __init__(
        self,
        id: str,
        document_id: str,
        content: str,
        embedding: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_index: int = 0,
    ):
        """
        Initialize a document chunk.
        
        Args:
            id: The unique identifier for the chunk
            document_id: The ID of the parent document
            content: The text content of the chunk
            embedding: The vector embedding of the chunk
            metadata: Additional metadata for the chunk
            chunk_index: The index of the chunk in the document
        """
        self.id = id
        self.document_id = document_id
        self.content = content
        self.embedding = embedding
        self.metadata = metadata or {}
        self.chunk_index = chunk_index
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the chunk to a dictionary.
        
        Returns:
            A dictionary representation of the chunk
        """
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "metadata": self.metadata,
            "chunk_index": self.chunk_index,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk":
        """
        Create a chunk from a dictionary.
        
        Args:
            data: The dictionary representation of the chunk
            
        Returns:
            A DocumentChunk object
        """
        return cls(
            id=data.get("id", ""),
            document_id=data.get("document_id", ""),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            chunk_index=data.get("chunk_index", 0),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the chunk."""
        return f"DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})"
    
    def __repr__(self) -> str:
        """Get a string representation of the chunk."""
        return self.__str__()

"""
Document Generation Model for the Knowledge Mesh Desktop application.

This module defines the models for AI-powered document generation based on
the knowledge mesh.
"""

import os
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Any, Union
import uuid


class GenerationFormat(Enum):
    """Enum defining the formats for generated documents."""
    
    MARKDOWN = auto()
    HTML = auto()
    TEXT = auto()
    PDF = auto()
    DOCX = auto()
    CUSTOM = auto()


class GenerationTemplate(Enum):
    """Enum defining the templates for generated documents."""
    
    SUMMARY = auto()
    REPORT = auto()
    NOTES = auto()
    PRESENTATION = auto()
    ARTICLE = auto()
    EMAIL = auto()
    CUSTOM = auto()


class GenerationStatus(Enum):
    """Enum defining the status of a document generation request."""
    
    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class GenerationRequest:
    """
    Represents a request to generate a document.
    
    A generation request contains the parameters for generating a document,
    such as the source documents, format, template, and other options.
    """
    
    def __init__(
        self,
        id: str,
        user_id: str,
        title: str,
        source_document_ids: List[str],
        format: GenerationFormat,
        template: GenerationTemplate,
        prompt: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        status: GenerationStatus = GenerationStatus.PENDING,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result_document_id: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a generation request.
        
        Args:
            id: The unique identifier for the request
            user_id: The ID of the user who created the request
            title: The title of the generated document
            source_document_ids: The IDs of the source documents
            format: The format of the generated document
            template: The template to use for generation
            prompt: Optional prompt to guide the generation
            parameters: Additional parameters for the generation
            status: The status of the request
            created_at: When the request was created
            updated_at: When the request was last updated
            completed_at: When the request was completed
            result_document_id: The ID of the generated document
            error_message: Error message if the request failed
            metadata: Additional metadata for the request
        """
        self.id = id
        self.user_id = user_id
        self.title = title
        self.source_document_ids = source_document_ids
        self.format = format
        self.template = template
        self.prompt = prompt
        self.parameters = parameters or {}
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at
        self.completed_at = completed_at
        self.result_document_id = result_document_id
        self.error_message = error_message
        self.metadata = metadata or {}
    
    @classmethod
    def create(
        cls,
        user_id: str,
        title: str,
        source_document_ids: List[str],
        format: Union[GenerationFormat, str],
        template: Union[GenerationTemplate, str],
        prompt: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GenerationRequest":
        """
        Create a new generation request.
        
        Args:
            user_id: The ID of the user creating the request
            title: The title of the generated document
            source_document_ids: The IDs of the source documents
            format: The format of the generated document
            template: The template to use for generation
            prompt: Optional prompt to guide the generation
            parameters: Additional parameters for the generation
            metadata: Additional metadata for the request
            
        Returns:
            A new GenerationRequest object
        """
        if isinstance(format, str):
            try:
                format = GenerationFormat[format.upper()]
            except KeyError:
                format = GenerationFormat.CUSTOM
        
        if isinstance(template, str):
            try:
                template = GenerationTemplate[template.upper()]
            except KeyError:
                template = GenerationTemplate.CUSTOM
        
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            source_document_ids=source_document_ids,
            format=format,
            template=template,
            prompt=prompt,
            parameters=parameters,
            status=GenerationStatus.PENDING,
            metadata=metadata,
        )
    
    def update_status(
        self,
        status: GenerationStatus,
        error_message: Optional[str] = None,
        result_document_id: Optional[str] = None,
    ):
        """
        Update the status of the request.
        
        Args:
            status: The new status
            error_message: Error message if the request failed
            result_document_id: The ID of the generated document
        """
        self.status = status
        self.updated_at = datetime.utcnow()
        
        if error_message:
            self.error_message = error_message
        
        if result_document_id:
            self.result_document_id = result_document_id
        
        if status == GenerationStatus.COMPLETED or status == GenerationStatus.FAILED:
            self.completed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the request to a dictionary.
        
        Returns:
            A dictionary representation of the request
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "source_document_ids": self.source_document_ids,
            "format": self.format.name,
            "template": self.template.name,
            "prompt": self.prompt,
            "parameters": self.parameters,
            "status": self.status.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_document_id": self.result_document_id,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationRequest":
        """
        Create a request from a dictionary.
        
        Args:
            data: The dictionary representation of the request
            
        Returns:
            A GenerationRequest object
        """
        format_str = data.get("format", "MARKDOWN")
        try:
            format = GenerationFormat[format_str]
        except KeyError:
            format = GenerationFormat.CUSTOM
        
        template_str = data.get("template", "SUMMARY")
        try:
            template = GenerationTemplate[template_str]
        except KeyError:
            template = GenerationTemplate.CUSTOM
        
        status_str = data.get("status", "PENDING")
        try:
            status = GenerationStatus[status_str]
        except KeyError:
            status = GenerationStatus.PENDING
        
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
        
        completed_at = None
        if data.get("completed_at"):
            try:
                completed_at = datetime.fromisoformat(data["completed_at"])
            except ValueError:
                completed_at = None
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            title=data.get("title", ""),
            source_document_ids=data.get("source_document_ids", []),
            format=format,
            template=template,
            prompt=data.get("prompt"),
            parameters=data.get("parameters", {}),
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            result_document_id=data.get("result_document_id"),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the request."""
        return (
            f"GenerationRequest(id={self.id}, title={self.title}, "
            f"status={self.status.name}, format={self.format.name}, "
            f"template={self.template.name})"
        )
    
    def __repr__(self) -> str:
        """Get a string representation of the request."""
        return self.__str__()


class GeneratedContent:
    """
    Represents the content of a generated document.
    
    This class contains the actual content of a generated document,
    along with metadata about the generation process.
    """
    
    def __init__(
        self,
        id: str,
        request_id: str,
        content: str,
        format: GenerationFormat,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize generated content.
        
        Args:
            id: The unique identifier for the content
            request_id: The ID of the generation request
            content: The actual content
            format: The format of the content
            created_at: When the content was created
            metadata: Additional metadata for the content
        """
        self.id = id
        self.request_id = request_id
        self.content = content
        self.format = format
        self.created_at = created_at or datetime.utcnow()
        self.metadata = metadata or {}
    
    @classmethod
    def create(
        cls,
        request_id: str,
        content: str,
        format: Union[GenerationFormat, str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GeneratedContent":
        """
        Create new generated content.
        
        Args:
            request_id: The ID of the generation request
            content: The actual content
            format: The format of the content
            metadata: Additional metadata for the content
            
        Returns:
            A new GeneratedContent object
        """
        if isinstance(format, str):
            try:
                format = GenerationFormat[format.upper()]
            except KeyError:
                format = GenerationFormat.CUSTOM
        
        return cls(
            id=str(uuid.uuid4()),
            request_id=request_id,
            content=content,
            format=format,
            metadata=metadata,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the content to a dictionary.
        
        Returns:
            A dictionary representation of the content
        """
        return {
            "id": self.id,
            "request_id": self.request_id,
            "content": self.content,
            "format": self.format.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeneratedContent":
        """
        Create content from a dictionary.
        
        Args:
            data: The dictionary representation of the content
            
        Returns:
            A GeneratedContent object
        """
        format_str = data.get("format", "MARKDOWN")
        try:
            format = GenerationFormat[format_str]
        except KeyError:
            format = GenerationFormat.CUSTOM
        
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                created_at = datetime.utcnow()
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            request_id=data.get("request_id", ""),
            content=data.get("content", ""),
            format=format,
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the content."""
        return (
            f"GeneratedContent(id={self.id}, request_id={self.request_id}, "
            f"format={self.format.name})"
        )
    
    def __repr__(self) -> str:
        """Get a string representation of the content."""
        return self.__str__()

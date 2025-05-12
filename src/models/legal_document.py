"""
Legal document models for the Knowledge Mesh Desktop application.

This module defines the models for legal document templates and DocuSign integration.
"""

import os
import uuid
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union, Set

from src.core.config import Config
from src.models.document import Document
from src.models.document_generation import (
    DocumentGenerationFormat, 
    DocumentGenerationRequest,
    DocumentGenerationContent,
    DocumentGenerationStatus
)


class LegalDocumentType(Enum):
    """Enum defining the types of legal documents."""
    
    ARTICLES_OF_INCORPORATION = auto()
    OPERATING_AGREEMENT = auto()
    BYLAWS = auto()
    PARTNERSHIP_AGREEMENT = auto()
    
    EMPLOYMENT_CONTRACT = auto()
    INDEPENDENT_CONTRACTOR = auto()
    NON_DISCLOSURE = auto()
    SERVICE_AGREEMENT = auto()
    SALES_AGREEMENT = auto()
    LEASE_AGREEMENT = auto()
    
    COPYRIGHT_ASSIGNMENT = auto()
    TRADEMARK_ASSIGNMENT = auto()
    PATENT_ASSIGNMENT = auto()
    LICENSE_AGREEMENT = auto()
    
    WILL = auto()
    TRUST = auto()
    POWER_OF_ATTORNEY = auto()
    HEALTHCARE_DIRECTIVE = auto()
    
    CUSTOM = auto()


class LegalDocumentSector(Enum):
    """Enum defining the sectors for legal documents."""
    
    BUSINESS = auto()
    REAL_ESTATE = auto()
    INTELLECTUAL_PROPERTY = auto()
    EMPLOYMENT = auto()
    HEALTHCARE = auto()
    FINANCE = auto()
    TECHNOLOGY = auto()
    EDUCATION = auto()
    ENTERTAINMENT = auto()
    GENERAL = auto()
    CUSTOM = auto()


class SignatureStatus(Enum):
    """Enum defining the status of document signatures."""
    
    NOT_SENT = auto()         # Document has not been sent for signature
    SENT = auto()             # Document has been sent for signature
    VIEWED = auto()           # Document has been viewed by the recipient
    SIGNED_PARTIAL = auto()   # Document has been signed by some parties
    SIGNED_COMPLETE = auto()  # Document has been signed by all parties
    DECLINED = auto()         # Document signature has been declined
    EXPIRED = auto()          # Document signature request has expired
    CANCELED = auto()         # Document signature request has been canceled
    ERROR = auto()            # Error occurred during signature process


class LegalDocumentTemplate:
    """
    Represents a legal document template.
    
    A legal document template is a pre-defined template for generating legal
    documents of a specific type and sector.
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        document_type: LegalDocumentType,
        sector: LegalDocumentSector,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        variables: Optional[List[str]] = None,
        format: DocumentGenerationFormat = DocumentGenerationFormat.DOCX,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_sensitive: bool = True,
    ):
        """
        Initialize a legal document template.
        
        Args:
            id: The unique identifier for the template
            name: The name of the template
            description: The description of the template
            document_type: The type of legal document
            sector: The sector the document is for
            content: The template content with variables
            metadata: Additional metadata for the template
            variables: List of variable names used in the template
            format: The format of the template
            created_at: When the template was created
            updated_at: When the template was last updated
            is_sensitive: Whether the template contains sensitive information
        """
        self.id = id
        self.name = name
        self.description = description
        self.document_type = document_type
        self.sector = sector
        self.content = content
        self.metadata = metadata or {}
        self.variables = variables or []
        self.format = format
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.is_sensitive = is_sensitive
    
    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        document_type: LegalDocumentType,
        sector: LegalDocumentSector,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        variables: Optional[List[str]] = None,
        format: DocumentGenerationFormat = DocumentGenerationFormat.DOCX,
        is_sensitive: bool = True,
    ) -> "LegalDocumentTemplate":
        """
        Create a new legal document template.
        
        Args:
            name: The name of the template
            description: The description of the template
            document_type: The type of legal document
            sector: The sector the document is for
            content: The template content with variables
            metadata: Additional metadata for the template
            variables: List of variable names used in the template
            format: The format of the template
            is_sensitive: Whether the template contains sensitive information
            
        Returns:
            A new LegalDocumentTemplate
        """
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            document_type=document_type,
            sector=sector,
            content=content,
            metadata=metadata,
            variables=variables,
            format=format,
            is_sensitive=is_sensitive,
        )
    
    def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        document_type: Optional[LegalDocumentType] = None,
        sector: Optional[LegalDocumentSector] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        variables: Optional[List[str]] = None,
        format: Optional[DocumentGenerationFormat] = None,
        is_sensitive: Optional[bool] = None,
    ) -> "LegalDocumentTemplate":
        """
        Update the legal document template.
        
        Args:
            name: The name of the template
            description: The description of the template
            document_type: The type of legal document
            sector: The sector the document is for
            content: The template content with variables
            metadata: Additional metadata for the template
            variables: List of variable names used in the template
            format: The format of the template
            is_sensitive: Whether the template contains sensitive information
            
        Returns:
            The updated LegalDocumentTemplate
        """
        if name is not None:
            self.name = name
        
        if description is not None:
            self.description = description
        
        if document_type is not None:
            self.document_type = document_type
        
        if sector is not None:
            self.sector = sector
        
        if content is not None:
            self.content = content
        
        if metadata is not None:
            self.metadata.update(metadata)
        
        if variables is not None:
            self.variables = variables
        
        if format is not None:
            self.format = format
        
        if is_sensitive is not None:
            self.is_sensitive = is_sensitive
        
        self.updated_at = datetime.utcnow()
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the legal document template to a dictionary.
        
        Returns:
            A dictionary representation of the legal document template
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "document_type": self.document_type.name,
            "sector": self.sector.name,
            "content": self.content,
            "metadata": self.metadata,
            "variables": self.variables,
            "format": self.format.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_sensitive": self.is_sensitive,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalDocumentTemplate":
        """
        Create a legal document template from a dictionary.
        
        Args:
            data: The dictionary representation of the legal document template
            
        Returns:
            A LegalDocumentTemplate object
        """
        document_type = LegalDocumentType.CUSTOM
        if data.get("document_type"):
            try:
                document_type = LegalDocumentType[data["document_type"]]
            except KeyError:
                document_type = LegalDocumentType.CUSTOM
        
        sector = LegalDocumentSector.GENERAL
        if data.get("sector"):
            try:
                sector = LegalDocumentSector[data["sector"]]
            except KeyError:
                sector = LegalDocumentSector.GENERAL
        
        format = DocumentGenerationFormat.DOCX
        if data.get("format"):
            try:
                format = DocumentGenerationFormat[data["format"]]
            except KeyError:
                format = DocumentGenerationFormat.DOCX
        
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
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            document_type=document_type,
            sector=sector,
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            variables=data.get("variables", []),
            format=format,
            created_at=created_at,
            updated_at=updated_at,
            is_sensitive=data.get("is_sensitive", True),
        )


class LegalDocumentGenerationRequest(DocumentGenerationRequest):
    """
    Represents a request to generate a legal document.
    
    This extends the DocumentGenerationRequest with legal document specific
    fields and functionality.
    """
    
    def __init__(
        self,
        id: str,
        template_id: str,
        variable_values: Dict[str, Any],
        user_id: str,
        status: DocumentGenerationStatus = DocumentGenerationStatus.PENDING,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        document_type: Optional[LegalDocumentType] = None,
        sector: Optional[LegalDocumentSector] = None,
        signature_required: bool = False,
        signatories: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize a legal document generation request.
        
        Args:
            id: The unique identifier for the request
            template_id: The ID of the template to use
            variable_values: Values for the template variables
            user_id: The ID of the user making the request
            status: The status of the request
            created_at: When the request was created
            updated_at: When the request was last updated
            completed_at: When the request was completed
            error_message: Error message if the request failed
            metadata: Additional metadata for the request
            document_type: The type of legal document
            sector: The sector the document is for
            signature_required: Whether the document requires signatures
            signatories: List of signatories for the document
        """
        super().__init__(
            id=id,
            template_id=template_id,
            variable_values=variable_values,
            user_id=user_id,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error_message=error_message,
            metadata=metadata or {},
        )
        
        self.document_type = document_type
        self.sector = sector
        self.signature_required = signature_required
        self.signatories = signatories or []
    
    @classmethod
    def create(
        cls,
        template_id: str,
        variable_values: Dict[str, Any],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_type: Optional[LegalDocumentType] = None,
        sector: Optional[LegalDocumentSector] = None,
        signature_required: bool = False,
        signatories: Optional[List[Dict[str, Any]]] = None,
    ) -> "LegalDocumentGenerationRequest":
        """
        Create a new legal document generation request.
        
        Args:
            template_id: The ID of the template to use
            variable_values: Values for the template variables
            user_id: The ID of the user making the request
            metadata: Additional metadata for the request
            document_type: The type of legal document
            sector: The sector the document is for
            signature_required: Whether the document requires signatures
            signatories: List of signatories for the document
            
        Returns:
            A new LegalDocumentGenerationRequest
        """
        return cls(
            id=str(uuid.uuid4()),
            template_id=template_id,
            variable_values=variable_values,
            user_id=user_id,
            status=DocumentGenerationStatus.PENDING,
            metadata=metadata,
            document_type=document_type,
            sector=sector,
            signature_required=signature_required,
            signatories=signatories,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the legal document generation request to a dictionary.
        
        Returns:
            A dictionary representation of the legal document generation request
        """
        data = super().to_dict()
        
        data.update({
            "document_type": self.document_type.name if self.document_type else None,
            "sector": self.sector.name if self.sector else None,
            "signature_required": self.signature_required,
            "signatories": self.signatories,
        })
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalDocumentGenerationRequest":
        """
        Create a legal document generation request from a dictionary.
        
        Args:
            data: The dictionary representation of the legal document generation request
            
        Returns:
            A LegalDocumentGenerationRequest object
        """
        document_type = None
        if data.get("document_type"):
            try:
                document_type = LegalDocumentType[data["document_type"]]
            except KeyError:
                document_type = None
        
        sector = None
        if data.get("sector"):
            try:
                sector = LegalDocumentSector[data["sector"]]
            except KeyError:
                sector = None
        
        status = DocumentGenerationStatus.PENDING
        if data.get("status"):
            try:
                status = DocumentGenerationStatus[data["status"]]
            except KeyError:
                status = DocumentGenerationStatus.PENDING
        
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
            template_id=data.get("template_id", ""),
            variable_values=data.get("variable_values", {}),
            user_id=data.get("user_id", ""),
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
            document_type=document_type,
            sector=sector,
            signature_required=data.get("signature_required", False),
            signatories=data.get("signatories", []),
        )


class SignatureRequest:
    """
    Represents a request for document signatures.
    
    A signature request is created when a document needs to be signed by one
    or more parties.
    """
    
    def __init__(
        self,
        id: str,
        document_id: str,
        signatories: List[Dict[str, Any]],
        status: SignatureStatus = SignatureStatus.NOT_SENT,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        docusign_envelope_id: Optional[str] = None,
    ):
        """
        Initialize a signature request.
        
        Args:
            id: The unique identifier for the request
            document_id: The ID of the document to be signed
            signatories: List of signatories for the document
            status: The status of the signature request
            created_at: When the request was created
            updated_at: When the request was last updated
            completed_at: When the request was completed
            expires_at: When the request expires
            metadata: Additional metadata for the request
            docusign_envelope_id: The DocuSign envelope ID
        """
        self.id = id
        self.document_id = document_id
        self.signatories = signatories
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.completed_at = completed_at
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(days=30))
        self.metadata = metadata or {}
        self.docusign_envelope_id = docusign_envelope_id
    
    @classmethod
    def create(
        cls,
        document_id: str,
        signatories: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_days: int = 30,
    ) -> "SignatureRequest":
        """
        Create a new signature request.
        
        Args:
            document_id: The ID of the document to be signed
            signatories: List of signatories for the document
            metadata: Additional metadata for the request
            expires_in_days: Number of days until the request expires
            
        Returns:
            A new SignatureRequest
        """
        return cls(
            id=str(uuid.uuid4()),
            document_id=document_id,
            signatories=signatories,
            status=SignatureStatus.NOT_SENT,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
            metadata=metadata,
        )
    
    def update_status(self, status: SignatureStatus) -> "SignatureRequest":
        """
        Update the status of the signature request.
        
        Args:
            status: The new status
            
        Returns:
            The updated SignatureRequest
        """
        self.status = status
        self.updated_at = datetime.utcnow()
        
        if status == SignatureStatus.SIGNED_COMPLETE:
            self.completed_at = datetime.utcnow()
        
        return self
    
    def is_expired(self) -> bool:
        """
        Check if the signature request has expired.
        
        Returns:
            True if the request has expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the signature request to a dictionary.
        
        Returns:
            A dictionary representation of the signature request
        """
        return {
            "id": self.id,
            "document_id": self.document_id,
            "signatories": self.signatories,
            "status": self.status.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat(),
            "metadata": self.metadata,
            "docusign_envelope_id": self.docusign_envelope_id,
            "is_expired": self.is_expired(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignatureRequest":
        """
        Create a signature request from a dictionary.
        
        Args:
            data: The dictionary representation of the signature request
            
        Returns:
            A SignatureRequest object
        """
        status = SignatureStatus.NOT_SENT
        if data.get("status"):
            try:
                status = SignatureStatus[data["status"]]
            except KeyError:
                status = SignatureStatus.NOT_SENT
        
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
        if data.get("completed_at") and data["completed_at"] is not None:
            try:
                completed_at = datetime.fromisoformat(data["completed_at"])
            except ValueError:
                completed_at = None
        
        expires_at = None
        if data.get("expires_at"):
            try:
                expires_at = datetime.fromisoformat(data["expires_at"])
            except ValueError:
                expires_at = datetime.utcnow() + timedelta(days=30)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            document_id=data.get("document_id", ""),
            signatories=data.get("signatories", []),
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            expires_at=expires_at,
            metadata=data.get("metadata", {}),
            docusign_envelope_id=data.get("docusign_envelope_id"),
        )

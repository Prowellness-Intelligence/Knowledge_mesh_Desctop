"""
Email models for the Knowledge Mesh Desktop application.

This module provides data models for email messages, attachments, and related entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Dict, Optional, Any, Union
from uuid import UUID, uuid4

from src.models.document import Document


class EmailImportance(Enum):
    """Email importance levels."""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()


class EmailFlag(Enum):
    """Email flags."""
    NONE = auto()
    FLAGGED = auto()
    COMPLETED = auto()
    ANSWERED = auto()
    FORWARDED = auto()


class EmailFolder(Enum):
    """Standard email folders."""
    INBOX = auto()
    SENT = auto()
    DRAFTS = auto()
    JUNK = auto()
    DELETED = auto()
    ARCHIVE = auto()
    CUSTOM = auto()


@dataclass
class EmailAddress:
    """Email address model."""
    address: str
    name: Optional[str] = None
    
    @classmethod
    def create(cls, address: str, name: Optional[str] = None) -> 'EmailAddress':
        """Create a new email address."""
        return cls(address=address, name=name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "address": self.address,
            "name": self.name,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailAddress':
        """Create from dictionary."""
        return cls(
            address=data["address"],
            name=data.get("name"),
        )


@dataclass
class EmailAttachment:
    """Email attachment model."""
    id: UUID = field(default_factory=uuid4)
    filename: str = ""
    content_type: str = ""
    size: int = 0
    content_id: Optional[str] = None
    is_inline: bool = False
    document_id: Optional[UUID] = None
    
    @classmethod
    def create(cls, filename: str, content_type: str, size: int, 
               content_id: Optional[str] = None, is_inline: bool = False,
               document_id: Optional[UUID] = None) -> 'EmailAttachment':
        """Create a new email attachment."""
        return cls(
            filename=filename,
            content_type=content_type,
            size=size,
            content_id=content_id,
            is_inline=is_inline,
            document_id=document_id,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "content_id": self.content_id,
            "is_inline": self.is_inline,
            "document_id": str(self.document_id) if self.document_id else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailAttachment':
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]),
            filename=data["filename"],
            content_type=data["content_type"],
            size=data["size"],
            content_id=data.get("content_id"),
            is_inline=data.get("is_inline", False),
            document_id=UUID(data["document_id"]) if data.get("document_id") else None,
        )


@dataclass
class Email:
    """Email message model."""
    id: UUID = field(default_factory=uuid4)
    message_id: str = ""
    conversation_id: Optional[str] = None
    subject: str = ""
    from_address: Optional[EmailAddress] = None
    to_addresses: List[EmailAddress] = field(default_factory=list)
    cc_addresses: List[EmailAddress] = field(default_factory=list)
    bcc_addresses: List[EmailAddress] = field(default_factory=list)
    reply_to_addresses: List[EmailAddress] = field(default_factory=list)
    date: datetime = field(default_factory=datetime.now)
    received_date: datetime = field(default_factory=datetime.now)
    body_text: str = ""
    body_html: Optional[str] = None
    importance: EmailImportance = EmailImportance.NORMAL
    flag: EmailFlag = EmailFlag.NONE
    is_read: bool = False
    has_attachments: bool = False
    attachments: List[EmailAttachment] = field(default_factory=list)
    folder: EmailFolder = EmailFolder.INBOX
    custom_folder: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    document_id: Optional[UUID] = None
    vector_embedding: Optional[List[float]] = None
    
    @classmethod
    def create(cls, message_id: str, subject: str, from_address: EmailAddress,
               to_addresses: List[EmailAddress], body_text: str,
               cc_addresses: List[EmailAddress] = None,
               bcc_addresses: List[EmailAddress] = None,
               reply_to_addresses: List[EmailAddress] = None,
               date: datetime = None,
               received_date: datetime = None,
               body_html: Optional[str] = None,
               importance: EmailImportance = EmailImportance.NORMAL,
               flag: EmailFlag = EmailFlag.NONE,
               is_read: bool = False,
               attachments: List[EmailAttachment] = None,
               folder: EmailFolder = EmailFolder.INBOX,
               custom_folder: Optional[str] = None,
               headers: Dict[str, str] = None,
               conversation_id: Optional[str] = None) -> 'Email':
        """Create a new email message."""
        if cc_addresses is None:
            cc_addresses = []
        if bcc_addresses is None:
            bcc_addresses = []
        if reply_to_addresses is None:
            reply_to_addresses = []
        if attachments is None:
            attachments = []
        if headers is None:
            headers = {}
        if date is None:
            date = datetime.now()
        if received_date is None:
            received_date = datetime.now()
            
        has_attachments = len(attachments) > 0
            
        return cls(
            message_id=message_id,
            conversation_id=conversation_id,
            subject=subject,
            from_address=from_address,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            bcc_addresses=bcc_addresses,
            reply_to_addresses=reply_to_addresses,
            date=date,
            received_date=received_date,
            body_text=body_text,
            body_html=body_html,
            importance=importance,
            flag=flag,
            is_read=is_read,
            has_attachments=has_attachments,
            attachments=attachments,
            folder=folder,
            custom_folder=custom_folder,
            headers=headers,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "subject": self.subject,
            "from_address": self.from_address.to_dict() if self.from_address else None,
            "to_addresses": [addr.to_dict() for addr in self.to_addresses],
            "cc_addresses": [addr.to_dict() for addr in self.cc_addresses],
            "bcc_addresses": [addr.to_dict() for addr in self.bcc_addresses],
            "reply_to_addresses": [addr.to_dict() for addr in self.reply_to_addresses],
            "date": self.date.isoformat(),
            "received_date": self.received_date.isoformat(),
            "body_text": self.body_text,
            "body_html": self.body_html,
            "importance": self.importance.name,
            "flag": self.flag.name,
            "is_read": self.is_read,
            "has_attachments": self.has_attachments,
            "attachments": [att.to_dict() for att in self.attachments],
            "folder": self.folder.name,
            "custom_folder": self.custom_folder,
            "headers": self.headers,
            "document_id": str(self.document_id) if self.document_id else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Email':
        """Create from dictionary."""
        email = cls(
            id=UUID(data["id"]),
            message_id=data["message_id"],
            conversation_id=data.get("conversation_id"),
            subject=data["subject"],
            from_address=EmailAddress.from_dict(data["from_address"]) if data.get("from_address") else None,
            to_addresses=[EmailAddress.from_dict(addr) for addr in data.get("to_addresses", [])],
            cc_addresses=[EmailAddress.from_dict(addr) for addr in data.get("cc_addresses", [])],
            bcc_addresses=[EmailAddress.from_dict(addr) for addr in data.get("bcc_addresses", [])],
            reply_to_addresses=[EmailAddress.from_dict(addr) for addr in data.get("reply_to_addresses", [])],
            date=datetime.fromisoformat(data["date"]),
            received_date=datetime.fromisoformat(data["received_date"]),
            body_text=data["body_text"],
            body_html=data.get("body_html"),
            importance=EmailImportance[data["importance"]],
            flag=EmailFlag[data["flag"]],
            is_read=data["is_read"],
            has_attachments=data["has_attachments"],
            attachments=[EmailAttachment.from_dict(att) for att in data.get("attachments", [])],
            folder=EmailFolder[data["folder"]],
            custom_folder=data.get("custom_folder"),
            headers=data.get("headers", {}),
            document_id=UUID(data["document_id"]) if data.get("document_id") else None,
        )
        return email
    
    def to_document(self) -> Document:
        """Convert email to document."""
        from src.models.document import DocumentType, DocumentMetadata
        
        metadata = DocumentMetadata(
            title=self.subject,
            author=self.from_address.name if self.from_address and self.from_address.name else 
                   self.from_address.address if self.from_address else "Unknown",
            created_date=self.date,
            modified_date=self.received_date,
            source_type="email",
            source_id=self.message_id,
            custom_metadata={
                "from_address": self.from_address.address if self.from_address else "",
                "to_addresses": [addr.address for addr in self.to_addresses],
                "cc_addresses": [addr.address for addr in self.cc_addresses],
                "conversation_id": self.conversation_id or "",
                "importance": self.importance.name,
                "flag": self.flag.name,
                "folder": self.folder.name,
                "custom_folder": self.custom_folder or "",
                "has_attachments": str(self.has_attachments),
            }
        )
        
        content = self.body_text
        
        document = Document.create(
            title=self.subject,
            content=content,
            document_type=DocumentType.EMAIL,
            metadata=metadata,
        )
        
        return document


@dataclass
class EmailSearchQuery:
    """Email search query model."""
    query_text: str
    folder: Optional[EmailFolder] = None
    custom_folder: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    subject: Optional[str] = None
    has_attachments: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    is_read: Optional[bool] = None
    importance: Optional[EmailImportance] = None
    flag: Optional[EmailFlag] = None
    limit: int = 50
    offset: int = 0
    
    @classmethod
    def create(cls, query_text: str, **kwargs) -> 'EmailSearchQuery':
        """Create a new email search query."""
        return cls(query_text=query_text, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "query_text": self.query_text,
            "limit": self.limit,
            "offset": self.offset,
        }
        
        if self.folder is not None:
            result["folder"] = self.folder.name
        if self.custom_folder is not None:
            result["custom_folder"] = self.custom_folder
        if self.from_address is not None:
            result["from_address"] = self.from_address
        if self.to_address is not None:
            result["to_address"] = self.to_address
        if self.subject is not None:
            result["subject"] = self.subject
        if self.has_attachments is not None:
            result["has_attachments"] = self.has_attachments
        if self.date_from is not None:
            result["date_from"] = self.date_from.isoformat()
        if self.date_to is not None:
            result["date_to"] = self.date_to.isoformat()
        if self.is_read is not None:
            result["is_read"] = self.is_read
        if self.importance is not None:
            result["importance"] = self.importance.name
        if self.flag is not None:
            result["flag"] = self.flag.name
            
        return result


@dataclass
class EmailSearchResult:
    """Email search result model."""
    emails: List[Email]
    total_count: int
    query: EmailSearchQuery
    
    @classmethod
    def create(cls, emails: List[Email], total_count: int, query: EmailSearchQuery) -> 'EmailSearchResult':
        """Create a new email search result."""
        return cls(emails=emails, total_count=total_count, query=query)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "emails": [email.to_dict() for email in self.emails],
            "total_count": self.total_count,
            "query": self.query.to_dict(),
        }

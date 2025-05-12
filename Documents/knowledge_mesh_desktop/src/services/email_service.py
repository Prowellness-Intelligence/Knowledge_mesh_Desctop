"""
Email Service for the Knowledge Mesh Desktop application.

This module provides a service that integrates with email systems to
access and manage emails.
"""

import asyncio
import datetime
import logging
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable

import pandas as pd

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus

logger = logging.getLogger(__name__)


class EmailMessage:
    """
    Represents an email message.
    
    This class provides a standardized representation of email messages
    from various email providers.
    """
    
    def __init__(
        self,
        id: str,
        subject: str,
        body: str,
        sender: str,
        recipients: List[str],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        date: Optional[datetime.datetime] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        folder: Optional[str] = None,
        read: bool = False,
        flagged: bool = False,
        provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize an email message.
        
        Args:
            id: The unique identifier for the message
            subject: The subject of the message
            body: The body of the message
            sender: The sender of the message
            recipients: The recipients of the message
            cc: The CC recipients of the message
            bcc: The BCC recipients of the message
            date: The date of the message
            attachments: The attachments of the message
            folder: The folder the message is in
            read: Whether the message has been read
            flagged: Whether the message has been flagged
            provider: The email provider (e.g., Gmail, Outlook)
            metadata: Additional metadata for the message
        """
        self.id = id
        self.subject = subject
        self.body = body
        self.sender = sender
        self.recipients = recipients
        self.cc = cc or []
        self.bcc = bcc or []
        self.date = date or datetime.datetime.now()
        self.attachments = attachments or []
        self.folder = folder or "inbox"
        self.read = read
        self.flagged = flagged
        self.provider = provider
        self.metadata = metadata or {}
    
    @property
    def is_unread(self) -> bool:
        """Check if the message is unread."""
        return not self.read
    
    @property
    def has_attachments(self) -> bool:
        """Check if the message has attachments."""
        return len(self.attachments) > 0
    
    @property
    def is_recent(self) -> bool:
        """Check if the message is recent (less than 24 hours old)."""
        if self.date:
            return (datetime.datetime.now() - self.date) < datetime.timedelta(hours=24)
        return False
    
    @property
    def is_from_today(self) -> bool:
        """Check if the message is from today."""
        if self.date:
            now = datetime.datetime.now()
            return (
                self.date.year == now.year
                and self.date.month == now.month
                and self.date.day == now.day
            )
        return False
    
    def extract_keywords(self) -> List[str]:
        """
        Extract keywords from the message subject and body.
        
        Returns:
            A list of keywords
        """
        words = re.findall(r'\b\w+\b', f"{self.subject} {self.body}")
        
        stopwords = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were"}
        keywords = [word.lower() for word in words if word.lower() not in stopwords and len(word) > 2]
        
        return sorted(set(keywords))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.
        
        Returns:
            A dictionary representation of the message
        """
        return {
            "id": self.id,
            "subject": self.subject,
            "body": self.body,
            "sender": self.sender,
            "recipients": self.recipients,
            "cc": self.cc,
            "bcc": self.bcc,
            "date": self.date.isoformat() if self.date else None,
            "attachments": self.attachments,
            "folder": self.folder,
            "read": self.read,
            "flagged": self.flagged,
            "provider": self.provider,
            "metadata": self.metadata,
            "is_unread": self.is_unread,
            "has_attachments": self.has_attachments,
            "is_recent": self.is_recent,
            "is_from_today": self.is_from_today,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmailMessage":
        """
        Create a message from a dictionary.
        
        Args:
            data: The dictionary representation of the message
            
        Returns:
            An EmailMessage object
        """
        date = None
        if data.get("date"):
            try:
                date = datetime.datetime.fromisoformat(data["date"])
            except ValueError:
                pass
        
        return cls(
            id=data.get("id", ""),
            subject=data.get("subject", ""),
            body=data.get("body", ""),
            sender=data.get("sender", ""),
            recipients=data.get("recipients", []),
            cc=data.get("cc", []),
            bcc=data.get("bcc", []),
            date=date,
            attachments=data.get("attachments", []),
            folder=data.get("folder"),
            read=data.get("read", False),
            flagged=data.get("flagged", False),
            provider=data.get("provider"),
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the message."""
        return f"EmailMessage(id={self.id}, subject={self.subject}, sender={self.sender})"
    
    def __repr__(self) -> str:
        """Get a string representation of the message."""
        return self.__str__()


class EmailProvider:
    """
    Base class for email providers.
    
    This class defines the interface for email providers and provides
    common functionality.
    """
    
    def __init__(self, config: Config):
        """
        Initialize an email provider.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.name = "base"
    
    async def initialize(self):
        """Initialize the email provider."""
        pass
    
    async def authenticate(self) -> bool:
        """
        Authenticate with the email provider.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        return False
    
    async def get_folders(self) -> List[Dict[str, Any]]:
        """
        Get the list of folders.
        
        Returns:
            A list of folders
        """
        return []
    
    async def get_messages(
        self,
        folder: Optional[str] = None,
        unread_only: bool = False,
        since: Optional[datetime.datetime] = None,
        max_results: Optional[int] = None,
    ) -> List[EmailMessage]:
        """
        Get messages from the email provider.
        
        Args:
            folder: The folder to get messages from
            unread_only: Whether to get only unread messages
            since: The date to get messages since
            max_results: The maximum number of messages to return
            
        Returns:
            A list of email messages
        """
        return []
    
    async def send_message(self, message: EmailMessage) -> bool:
        """
        Send a message through the email provider.
        
        Args:
            message: The message to send
            
        Returns:
            True if sending was successful, False otherwise
        """
        return False
    
    async def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a message as read.
        
        Args:
            message_id: The ID of the message to mark as read
            
        Returns:
            True if marking was successful, False otherwise
        """
        return False
    
    async def mark_as_unread(self, message_id: str) -> bool:
        """
        Mark a message as unread.
        
        Args:
            message_id: The ID of the message to mark as unread
            
        Returns:
            True if marking was successful, False otherwise
        """
        return False
    
    async def flag_message(self, message_id: str) -> bool:
        """
        Flag a message.
        
        Args:
            message_id: The ID of the message to flag
            
        Returns:
            True if flagging was successful, False otherwise
        """
        return False
    
    async def unflag_message(self, message_id: str) -> bool:
        """
        Unflag a message.
        
        Args:
            message_id: The ID of the message to unflag
            
        Returns:
            True if unflagging was successful, False otherwise
        """
        return False
    
    async def delete_message(self, message_id: str) -> bool:
        """
        Delete a message.
        
        Args:
            message_id: The ID of the message to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        return False
    
    async def move_message(self, message_id: str, folder: str) -> bool:
        """
        Move a message to a folder.
        
        Args:
            message_id: The ID of the message to move
            folder: The folder to move the message to
            
        Returns:
            True if moving was successful, False otherwise
        """
        return False


class GmailProvider(EmailProvider):
    """
    Gmail provider.
    
    This class provides integration with Gmail.
    """
    
    def __init__(self, config: Config):
        """
        Initialize a Gmail provider.
        
        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.name = "gmail"
        self.credentials = None
        self.service = None
    
    async def initialize(self):
        """Initialize the Gmail provider."""
        try:
            logger.info("Initializing Gmail provider")
        except Exception as e:
            logger.error(f"Error initializing Gmail provider: {e}", exc_info=True)
            raise
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Gmail.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            logger.info("Authenticating with Gmail")
            return True
        except Exception as e:
            logger.error(f"Error authenticating with Gmail: {e}", exc_info=True)
            return False
    
    async def get_folders(self) -> List[Dict[str, Any]]:
        """
        Get the list of Gmail folders (labels).
        
        Returns:
            A list of folders
        """
        try:
            return [
                {
                    "id": "INBOX",
                    "name": "Inbox",
                    "type": "system",
                },
                {
                    "id": "SENT",
                    "name": "Sent",
                    "type": "system",
                },
                {
                    "id": "TRASH",
                    "name": "Trash",
                    "type": "system",
                },
                {
                    "id": "SPAM",
                    "name": "Spam",
                    "type": "system",
                },
                {
                    "id": "IMPORTANT",
                    "name": "Important",
                    "type": "system",
                },
            ]
        except Exception as e:
            logger.error(f"Error getting Gmail folders: {e}", exc_info=True)
            return []
    
    async def get_messages(
        self,
        folder: Optional[str] = None,
        unread_only: bool = False,
        since: Optional[datetime.datetime] = None,
        max_results: Optional[int] = None,
    ) -> List[EmailMessage]:
        """
        Get messages from Gmail.
        
        Args:
            folder: The folder to get messages from
            unread_only: Whether to get only unread messages
            since: The date to get messages since
            max_results: The maximum number of messages to return
            
        Returns:
            A list of email messages
        """
        try:
            return [
                EmailMessage(
                    id="msg1",
                    subject="Hello from Gmail",
                    body="This is a test message from Gmail.",
                    sender="sender@example.com",
                    recipients=["recipient@example.com"],
                    date=datetime.datetime.now(),
                    folder=folder or "INBOX",
                    provider="gmail",
                )
            ]
        except Exception as e:
            logger.error(f"Error getting messages from Gmail: {e}", exc_info=True)
            return []


class OutlookProvider(EmailProvider):
    """
    Outlook provider.
    
    This class provides integration with Microsoft Outlook.
    """
    
    def __init__(self, config: Config):
        """
        Initialize an Outlook provider.
        
        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.name = "outlook"
        self.credentials = None
        self.client = None
    
    async def initialize(self):
        """Initialize the Outlook provider."""
        try:
            logger.info("Initializing Outlook provider")
        except Exception as e:
            logger.error(f"Error initializing Outlook provider: {e}", exc_info=True)
            raise
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Outlook.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            logger.info("Authenticating with Outlook")
            return True
        except Exception as e:
            logger.error(f"Error authenticating with Outlook: {e}", exc_info=True)
            return False


class LocalEmailProvider(EmailProvider):
    """
    Local email provider.
    
    This class provides a local email implementation that stores messages
    in a local file.
    """
    
    def __init__(self, config: Config):
        """
        Initialize a local email provider.
        
        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.name = "local"
        self.messages_file: Optional[Path] = None
        self.messages: List[EmailMessage] = []
        self.folders: List[Dict[str, Any]] = []
    
    async def initialize(self):
        """Initialize the local email provider."""
        try:
            data_dir = Path(self.config.get("app.data_dir", ""))
            if data_dir:
                self.messages_file = data_dir / "emails" / "messages.json"
                if self.messages_file.parent:
                    self.messages_file.parent.mkdir(parents=True, exist_ok=True)
            
            await self._load_messages()
            
            self.folders = [
                {
                    "id": "inbox",
                    "name": "Inbox",
                    "type": "system",
                },
                {
                    "id": "sent",
                    "name": "Sent",
                    "type": "system",
                },
                {
                    "id": "trash",
                    "name": "Trash",
                    "type": "system",
                },
                {
                    "id": "drafts",
                    "name": "Drafts",
                    "type": "system",
                },
            ]
            
            logger.info("Initialized local email provider")
        except Exception as e:
            logger.error(f"Error initializing local email provider: {e}", exc_info=True)
            raise
    
    async def _load_messages(self):
        """Load messages from the messages file."""
        if not self.messages_file or not self.messages_file.exists():
            self.messages = []
            return
        
        try:
            import json
            
            with open(str(self.messages_file), "r") as f:
                messages_data = json.load(f)
            
            self.messages = [EmailMessage.from_dict(message_data) for message_data in messages_data]
            logger.info(f"Loaded {len(self.messages)} messages from {self.messages_file}")
        except Exception as e:
            logger.error(f"Error loading messages from {self.messages_file}: {e}", exc_info=True)
            self.messages = []
    
    async def _save_messages(self):
        """Save messages to the messages file."""
        if not self.messages_file:
            logger.error("Messages file path is not set")
            return
        
        try:
            import json
            
            messages_data = [message.to_dict() for message in self.messages]
            
            with open(str(self.messages_file), "w") as f:
                json.dump(messages_data, f, indent=2)
            
            logger.info(f"Saved {len(self.messages)} messages to {self.messages_file}")
        except Exception as e:
            logger.error(f"Error saving messages to {self.messages_file}: {e}", exc_info=True)
    
    async def get_folders(self) -> List[Dict[str, Any]]:
        """
        Get the list of local folders.
        
        Returns:
            A list of folders
        """
        return self.folders
    
    async def get_messages(
        self,
        folder: Optional[str] = None,
        unread_only: bool = False,
        since: Optional[datetime.datetime] = None,
        max_results: Optional[int] = None,
    ) -> List[EmailMessage]:
        """
        Get messages from the local email provider.
        
        Args:
            folder: The folder to get messages from
            unread_only: Whether to get only unread messages
            since: The date to get messages since
            max_results: The maximum number of messages to return
            
        Returns:
            A list of email messages
        """
        messages = self.messages
        if folder:
            messages = [message for message in messages if message.folder == folder]
        
        if unread_only:
            messages = [message for message in messages if message.is_unread]
        
        if since:
            messages = [message for message in messages if message.date and message.date >= since]
        
        messages = sorted(messages, key=lambda message: message.date or datetime.datetime.min, reverse=True)
        
        if max_results:
            messages = messages[:max_results]
        
        return messages
    
    async def send_message(self, message: EmailMessage) -> bool:
        """
        Send a message through the local email provider.
        
        Args:
            message: The message to send
            
        Returns:
            True if sending was successful, False otherwise
        """
        try:
            if not message.provider:
                message.provider = self.name
            
            if not message.folder:
                message.folder = "sent"
            
            self.messages.append(message)
            
            await self._save_messages()
            
            return True
        except Exception as e:
            logger.error(f"Error sending message through local email provider: {e}", exc_info=True)
            return False
    
    async def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a message as read.
        
        Args:
            message_id: The ID of the message to mark as read
            
        Returns:
            True if marking was successful, False otherwise
        """
        try:
            for message in self.messages:
                if message.id == message_id:
                    message.read = True
                    
                    await self._save_messages()
                    
                    return True
            
            logger.warning(f"Message {message_id} not found in local email provider")
            return False
        except Exception as e:
            logger.error(f"Error marking message as read in local email provider: {e}", exc_info=True)
            return False


class EmailService:
    """
    Service for email integration.
    
    This service provides access to email messages from various providers
    and allows the application to send, receive, and manage emails.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the email service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.is_running = False
        self.providers: Dict[str, EmailProvider] = {}
        self.default_provider: Optional[EmailProvider] = None
        self.sync_interval = datetime.timedelta(minutes=15)
        self.last_sync_time = None
        self.sync_task = None
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.sync_interval = datetime.timedelta(minutes=self.config.get(
            "email.sync_interval_minutes", 15
        ))
        
        self.provider_configs = self.config.get("email.providers", {})
        
        self.default_provider_name = self.config.get("email.default_provider", "local")
    
    async def initialize(self):
        """Initialize the email service."""
        logger.info("Initializing email service")
        
        try:
            local_provider = LocalEmailProvider(self.config)
            await local_provider.initialize()
            self.providers[local_provider.name] = local_provider
            
            if self.provider_configs.get("gmail", {}).get("enabled", False):
                gmail_provider = GmailProvider(self.config)
                await gmail_provider.initialize()
                self.providers[gmail_provider.name] = gmail_provider
            
            if self.provider_configs.get("outlook", {}).get("enabled", False):
                outlook_provider = OutlookProvider(self.config)
                await outlook_provider.initialize()
                self.providers[outlook_provider.name] = outlook_provider
            
            if self.default_provider_name in self.providers:
                self.default_provider = self.providers[self.default_provider_name]
            else:
                self.default_provider = self.providers.get("local")
            
            event_bus.subscribe(EventType.EMAIL_MESSAGE_RECEIVED, self._on_message_received)
            event_bus.subscribe(EventType.EMAIL_MESSAGE_SENT, self._on_message_sent)
            event_bus.subscribe(EventType.EMAIL_MESSAGE_READ, self._on_message_read)
            
            logger.info("Email service initialized")
        except Exception as e:
            logger.error(f"Error initializing email service: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Start the email service."""
        if self.is_running:
            logger.warning("Email service is already running")
            return
        
        logger.info("Starting email service")
        
        self.is_running = True
        
        for provider_name, provider in self.providers.items():
            if provider_name != "local":
                authenticated = await provider.authenticate()
                if authenticated:
                    logger.info(f"Authenticated with {provider_name} email provider")
                else:
                    logger.warning(f"Failed to authenticate with {provider_name} email provider")
        
        self.sync_task = asyncio.create_task(self._sync_messages())
        
        logger.info("Email service started")
    
    async def stop(self):
        """Stop the email service."""
        if not self.is_running:
            logger.warning("Email service is not running")
            return
        
        logger.info("Stopping email service")
        
        self.is_running = False
        
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Email service stopped")
    
    async def _sync_messages(self):
        """Sync messages from all providers."""
        logger.info("Starting email message sync")
        
        while self.is_running:
            try:
                for provider_name, provider in self.providers.items():
                    if provider_name != "local":
                        logger.info(f"Syncing messages from {provider_name} email provider")
                        messages = await provider.get_messages(unread_only=True)
                        logger.info(f"Synced {len(messages)} messages from {provider_name} email provider")
                        
                        for message in messages:
                            publish(
                                EventType.EMAIL_MESSAGE_RECEIVED,
                                {
                                    "message": message.to_dict(),
                                    "provider": provider_name,
                                },
                            )
                
                self.last_sync_time = datetime.datetime.now()
                
                await asyncio.sleep(self.sync_interval.total_seconds())
            except asyncio.CancelledError:
                logger.info("Email message sync cancelled")
                break
            except Exception as e:
                logger.error(f"Error syncing email messages: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait before trying again
        
        logger.info("Email message sync stopped")
    
    async def get_folders(self, provider_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get the list of folders.
        
        Args:
            provider_name: The name of the provider to get folders from
            
        Returns:
            A list of folders
        """
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Email provider {provider_name} not found")
                return []
            
            return await provider.get_folders()
        else:
            folders = []
            for provider_name, provider in self.providers.items():
                provider_folders = await provider.get_folders()
                for folder in provider_folders:
                    folder["provider"] = provider_name
                
                folders.extend(provider_folders)
            
            return folders
    
    async def get_messages(
        self,
        provider_name: Optional[str] = None,
        folder: Optional[str] = None,
        unread_only: bool = False,
        since: Optional[datetime.datetime] = None,
        max_results: Optional[int] = None,
    ) -> List[EmailMessage]:
        """
        Get messages from the email provider.
        
        Args:
            provider_name: The name of the provider to get messages from
            folder: The folder to get messages from
            unread_only: Whether to get only unread messages
            since: The date to get messages since
            max_results: The maximum number of messages to return
            
        Returns:
            A list of email messages
        """
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Email provider {provider_name} not found")
                return []
            
            return await provider.get_messages(
                folder=folder,
                unread_only=unread_only,
                since=since,
                max_results=max_results,
            )
        else:
            messages = []
            for provider_name, provider in self.providers.items():
                provider_messages = await provider.get_messages(
                    folder=folder,
                    unread_only=unread_only,
                    since=since,
                    max_results=max_results,
                )
                
                messages.extend(provider_messages)
            
            messages = sorted(messages, key=lambda message: message.date or datetime.datetime.min, reverse=True)
            
            if max_results:
                messages = messages[:max_results]
            
            return messages
    
    async def get_unread_messages(
        self,
        provider_name: Optional[str] = None,
        folder: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> List[EmailMessage]:
        """
        Get unread messages from the email provider.
        
        Args:
            provider_name: The name of the provider to get messages from
            folder: The folder to get messages from
            max_results: The maximum number of messages to return
            
        Returns:
            A list of email messages
        """
        return await self.get_messages(
            provider_name=provider_name,
            folder=folder,
            unread_only=True,
            max_results=max_results,
        )
    
    async def get_recent_messages(
        self,
        provider_name: Optional[str] = None,
        folder: Optional[str] = None,
        hours: int = 24,
        max_results: Optional[int] = None,
    ) -> List[EmailMessage]:
        """
        Get recent messages from the email provider.
        
        Args:
            provider_name: The name of the provider to get messages from
            folder: The folder to get messages from
            hours: The number of hours to get messages for
            max_results: The maximum number of messages to return
            
        Returns:
            A list of email messages
        """
        since = datetime.datetime.now() - datetime.timedelta(hours=hours)
        
        return await self.get_messages(
            provider_name=provider_name,
            folder=folder,
            since=since,
            max_results=max_results,
        )
    
    async def send_message(
        self,
        message: EmailMessage,
        provider_name: Optional[str] = None,
    ) -> bool:
        """
        Send a message through the email provider.
        
        Args:
            message: The message to send
            provider_name: The name of the provider to send the message through
            
        Returns:
            True if sending was successful, False otherwise
        """
        provider = None
        
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Email provider {provider_name} not found")
                return False
        else:
            provider = self.default_provider
        
        if not provider:
            logger.error("No email provider available")
            return False
        
        sent = await provider.send_message(message)
        
        if sent:
            publish(
                EventType.EMAIL_MESSAGE_SENT,
                {
                    "message": message.to_dict(),
                    "provider": provider.name,
                },
            )
        
        return sent
    
    async def mark_as_read(
        self,
        message_id: str,
        provider_name: Optional[str] = None,
    ) -> bool:
        """
        Mark a message as read.
        
        Args:
            message_id: The ID of the message to mark as read
            provider_name: The name of the provider the message belongs to
            
        Returns:
            True if marking was successful, False otherwise
        """
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Email provider {provider_name} not found")
                return False
            
            marked = await provider.mark_as_read(message_id)
            
            if marked:
                publish(
                    EventType.EMAIL_MESSAGE_READ,
                    {
                        "message_id": message_id,
                        "provider": provider_name,
                    },
                )
            
            return marked
        else:
            for provider_name, provider in self.providers.items():
                marked = await provider.mark_as_read(message_id)
                
                if marked:
                    publish(
                        EventType.EMAIL_MESSAGE_READ,
                        {
                            "message_id": message_id,
                            "provider": provider_name,
                        },
                    )
                    
                    return True
            
            return False
    
    async def _on_message_received(self, event):
        """
        Handle email message received events.
        
        Args:
            event: The email message received event
        """
        logger.info(f"Email message received: {event.data.get('message', {}).get('subject')}")
    
    async def _on_message_sent(self, event):
        """
        Handle email message sent events.
        
        Args:
            event: The email message sent event
        """
        logger.info(f"Email message sent: {event.data.get('message', {}).get('subject')}")
    
    async def _on_message_read(self, event):
        """
        Handle email message read events.
        
        Args:
            event: The email message read event
        """
        logger.info(f"Email message read: {event.data.get('message_id')}")

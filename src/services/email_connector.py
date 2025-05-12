"""
Email connector service for the Knowledge Mesh Desktop application.

This module provides services for connecting to email providers and retrieving emails.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import List, Dict, Any, Optional, Tuple, Set, Callable
import email
import email.utils
import imaplib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import re
import ssl
import time
import uuid
from pathlib import Path

from src.core.config import Config
from src.core.events import EventType, publish_event
from src.models.email import Email, EmailAddress, EmailAttachment, EmailImportance, EmailFlag, EmailFolder
from src.services.vault_integration import VaultService


logger = logging.getLogger(__name__)


class EmailProvider(Enum):
    """Email provider types."""
    GMAIL = auto()
    OUTLOOK = auto()
    YAHOO = auto()
    IMAP = auto()
    OFFICE365 = auto()
    EXCHANGE = auto()
    CUSTOM = auto()


class EmailConnectorService:
    """Service for connecting to email providers and retrieving emails."""
    
    def __init__(self, config: Config, vault_service: VaultService):
        """Initialize the email connector service."""
        self.config = config
        self.vault_service = vault_service
        self.connections = {}
        self.provider_settings = {}
        self.sync_tasks = {}
        self.sync_intervals = {}
        self.sync_running = {}
        self.email_processors = []
        
        self._load_provider_settings()
    
    def _load_provider_settings(self):
        """Load email provider settings from config."""
        providers = self.config.get("email.providers", [])
        for provider in providers:
            provider_id = provider.get("id")
            if not provider_id:
                continue
                
            self.provider_settings[provider_id] = provider
    
    async def connect(self, provider_id: str) -> bool:
        """Connect to an email provider."""
        if provider_id in self.connections and self.connections[provider_id]:
            return True
            
        provider_config = self.provider_settings.get(provider_id)
        if not provider_config:
            logger.error(f"Provider {provider_id} not found in settings")
            return False
            
        provider_type = EmailProvider[provider_config.get("type", "IMAP")]
        
        credentials = await self._get_credentials(provider_id)
        if not credentials:
            logger.error(f"Failed to get credentials for provider {provider_id}")
            return False
            
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            logger.error(f"Invalid credentials for provider {provider_id}")
            return False
        
        try:
            if provider_type in [EmailProvider.GMAIL, EmailProvider.OUTLOOK, EmailProvider.YAHOO, 
                                EmailProvider.IMAP, EmailProvider.OFFICE365]:
                host = provider_config.get("imap_host")
                port = provider_config.get("imap_port", 993)
                use_ssl = provider_config.get("use_ssl", True)
                
                if not host:
                    logger.error(f"IMAP host not specified for provider {provider_id}")
                    return False
                
                if use_ssl:
                    connection = imaplib.IMAP4_SSL(host, port)
                else:
                    connection = imaplib.IMAP4(host, port)
                
                connection.login(username, password)
                
                self.connections[provider_id] = {
                    "type": provider_type,
                    "imap": connection,
                    "smtp": None,  # Will be initialized when needed
                }
                
                logger.info(f"Connected to email provider {provider_id}")
                
                publish_event(EventType.EMAIL_PROVIDER_CONNECTED, {
                    "provider_id": provider_id,
                    "provider_type": provider_type.name,
                })
                
                return True
            else:
                logger.error(f"Unsupported provider type: {provider_type}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to email provider {provider_id}: {str(e)}")
            return False
    
    async def disconnect(self, provider_id: str) -> bool:
        """Disconnect from an email provider."""
        if provider_id not in self.connections:
            return True  # Already disconnected
            
        connection = self.connections.get(provider_id)
        if not connection:
            return True
            
        try:
            await self.stop_sync(provider_id)
            
            if "imap" in connection and connection["imap"]:
                connection["imap"].logout()
            
            if "smtp" in connection and connection["smtp"]:
                connection["smtp"].quit()
            
            self.connections[provider_id] = None
            
            logger.info(f"Disconnected from email provider {provider_id}")
            
            publish_event(EventType.EMAIL_PROVIDER_DISCONNECTED, {
                "provider_id": provider_id,
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect from email provider {provider_id}: {str(e)}")
            return False
    
    async def _get_credentials(self, provider_id: str) -> Dict[str, str]:
        """Get credentials for an email provider from vault."""
        try:
            credentials_path = f"email/providers/{provider_id}"
            credentials = await self.vault_service.get_secret(credentials_path)
            
            if not credentials:
                provider_config = self.provider_settings.get(provider_id, {})
                username = provider_config.get("username")
                password = provider_config.get("password")
                
                if username and password:
                    credentials = {
                        "username": username,
                        "password": password,
                    }
                    
                    await self.vault_service.set_secret(credentials_path, credentials)
            
            return credentials or {}
        except Exception as e:
            logger.error(f"Failed to get credentials for provider {provider_id}: {str(e)}")
            return {}
    
    async def _ensure_smtp_connection(self, provider_id: str) -> bool:
        """Ensure SMTP connection is established."""
        if provider_id not in self.connections or not self.connections[provider_id]:
            if not await self.connect(provider_id):
                return False
        
        connection = self.connections[provider_id]
        if "smtp" in connection and connection["smtp"]:
            return True
            
        provider_config = self.provider_settings.get(provider_id)
        if not provider_config:
            logger.error(f"Provider {provider_id} not found in settings")
            return False
            
        credentials = await self._get_credentials(provider_id)
        if not credentials:
            logger.error(f"Failed to get credentials for provider {provider_id}")
            return False
            
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            logger.error(f"Invalid credentials for provider {provider_id}")
            return False
            
        try:
            host = provider_config.get("smtp_host")
            port = provider_config.get("smtp_port", 587)
            use_ssl = provider_config.get("smtp_use_ssl", False)
            use_tls = provider_config.get("smtp_use_tls", True)
            
            if not host:
                logger.error(f"SMTP host not specified for provider {provider_id}")
                return False
            
            if use_ssl:
                smtp = smtplib.SMTP_SSL(host, port)
            else:
                smtp = smtplib.SMTP(host, port)
            
            if use_tls and not use_ssl:
                smtp.starttls()
            
            smtp.login(username, password)
            
            connection["smtp"] = smtp
            
            logger.info(f"Connected to SMTP server for provider {provider_id}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server for provider {provider_id}: {str(e)}")
            return False
    
    async def start_sync(self, provider_id: str, interval_seconds: int = 300) -> bool:
        """Start syncing emails from a provider at regular intervals."""
        if provider_id in self.sync_running and self.sync_running[provider_id]:
            return True
            
        if not await self.connect(provider_id):
            return False
            
        self.sync_intervals[provider_id] = interval_seconds
        
        self.sync_running[provider_id] = True
        
        self.sync_tasks[provider_id] = asyncio.create_task(self._sync_task(provider_id))
        
        logger.info(f"Started email sync for provider {provider_id} with interval {interval_seconds}s")
        
        return True
    
    async def stop_sync(self, provider_id: str) -> bool:
        """Stop syncing emails from a provider."""
        if provider_id not in self.sync_running or not self.sync_running[provider_id]:
            return True
            
        self.sync_running[provider_id] = False
        
        if provider_id in self.sync_tasks and self.sync_tasks[provider_id]:
            self.sync_tasks[provider_id].cancel()
            try:
                await self.sync_tasks[provider_id]
            except asyncio.CancelledError:
                pass
            
            self.sync_tasks[provider_id] = None
        
        logger.info(f"Stopped email sync for provider {provider_id}")
        
        return True
    
    async def _sync_task(self, provider_id: str):
        """Background task for syncing emails."""
        try:
            while self.sync_running.get(provider_id, False):
                await self.sync_emails(provider_id)
                
                interval = self.sync_intervals.get(provider_id, 300)
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info(f"Email sync task for provider {provider_id} cancelled")
        except Exception as e:
            logger.error(f"Error in email sync task for provider {provider_id}: {str(e)}")
            self.sync_running[provider_id] = False
    
    async def sync_emails(self, provider_id: str, folder: EmailFolder = EmailFolder.INBOX, 
                         custom_folder: Optional[str] = None, limit: int = 100) -> List[Email]:
        """Sync emails from a provider folder."""
        if not await self.connect(provider_id):
            return []
            
        connection = self.connections.get(provider_id)
        if not connection or "imap" not in connection or not connection["imap"]:
            logger.error(f"No IMAP connection for provider {provider_id}")
            return []
            
        imap = connection["imap"]
        
        try:
            folder_name = self._get_folder_name(provider_id, folder, custom_folder)
            result, data = imap.select(folder_name)
            
            if result != "OK":
                logger.error(f"Failed to select folder {folder_name} for provider {provider_id}: {data}")
                return []
                
            result, data = imap.search(None, "ALL")
            
            if result != "OK":
                logger.error(f"Failed to search emails for provider {provider_id}: {data}")
                return []
                
            email_ids = data[0].split()
            
            if limit > 0 and len(email_ids) > limit:
                email_ids = email_ids[-limit:]
                
            emails = []
            
            for email_id in email_ids:
                result, data = imap.fetch(email_id, "(RFC822)")
                
                if result != "OK":
                    logger.error(f"Failed to fetch email {email_id} for provider {provider_id}: {data}")
                    continue
                    
                raw_email = data[0][1]
                
                email_obj = self._parse_email(raw_email, folder, custom_folder)
                
                if email_obj:
                    emails.append(email_obj)
                    
                    for processor in self.email_processors:
                        try:
                            await processor(email_obj)
                        except Exception as e:
                            logger.error(f"Error processing email: {str(e)}")
            
            publish_event(EventType.EMAILS_SYNCED, {
                "provider_id": provider_id,
                "folder": folder.name,
                "custom_folder": custom_folder,
                "count": len(emails),
            })
            
            return emails
        except Exception as e:
            logger.error(f"Failed to sync emails for provider {provider_id}: {str(e)}")
            return []
    
    def _get_folder_name(self, provider_id: str, folder: EmailFolder, custom_folder: Optional[str] = None) -> str:
        """Get the actual folder name for a provider."""
        if folder == EmailFolder.CUSTOM and custom_folder:
            return custom_folder
            
        provider_config = self.provider_settings.get(provider_id, {})
        provider_type = EmailProvider[provider_config.get("type", "IMAP")]
        
        folder_mappings = {
            EmailProvider.GMAIL: {
                EmailFolder.INBOX: "INBOX",
                EmailFolder.SENT: "[Gmail]/Sent Mail",
                EmailFolder.DRAFTS: "[Gmail]/Drafts",
                EmailFolder.JUNK: "[Gmail]/Spam",
                EmailFolder.DELETED: "[Gmail]/Trash",
                EmailFolder.ARCHIVE: "[Gmail]/All Mail",
            },
            EmailProvider.OUTLOOK: {
                EmailFolder.INBOX: "INBOX",
                EmailFolder.SENT: "Sent",
                EmailFolder.DRAFTS: "Drafts",
                EmailFolder.JUNK: "Junk",
                EmailFolder.DELETED: "Deleted",
                EmailFolder.ARCHIVE: "Archive",
            },
            EmailProvider.YAHOO: {
                EmailFolder.INBOX: "INBOX",
                EmailFolder.SENT: "Sent",
                EmailFolder.DRAFTS: "Draft",
                EmailFolder.JUNK: "Bulk Mail",
                EmailFolder.DELETED: "Trash",
                EmailFolder.ARCHIVE: "Archive",
            },
            EmailProvider.OFFICE365: {
                EmailFolder.INBOX: "INBOX",
                EmailFolder.SENT: "Sent Items",
                EmailFolder.DRAFTS: "Drafts",
                EmailFolder.JUNK: "Junk Email",
                EmailFolder.DELETED: "Deleted Items",
                EmailFolder.ARCHIVE: "Archive",
            },
        }
        
        mapping = folder_mappings.get(provider_type, {})
        
        folder_name = mapping.get(folder)
        
        if not folder_name:
            folder_name = folder.name
            
        return folder_name
    
    def _parse_email(self, raw_email: bytes, folder: EmailFolder, 
                    custom_folder: Optional[str] = None) -> Optional[Email]:
        """Parse raw email data into Email object."""
        try:
            msg = email.message_from_bytes(raw_email)
            
            message_id = msg.get("Message-ID", "")
            subject = msg.get("Subject", "")
            
            from_addr = self._parse_address(msg.get("From", ""))
            to_addrs = self._parse_addresses(msg.get("To", ""))
            cc_addrs = self._parse_addresses(msg.get("Cc", ""))
            bcc_addrs = self._parse_addresses(msg.get("Bcc", ""))
            reply_to_addrs = self._parse_addresses(msg.get("Reply-To", ""))
            
            date_str = msg.get("Date", "")
            date = email.utils.parsedate_to_datetime(date_str) if date_str else datetime.now()
            
            received_str = msg.get("Received", "")
            if received_str:
                match = re.search(r";\s*(.+)$", received_str)
                if match:
                    try:
                        received_date = email.utils.parsedate_to_datetime(match.group(1))
                    except:
                        received_date = date
                else:
                    received_date = date
            else:
                received_date = date
            
            importance_str = msg.get("Importance", "").lower()
            if importance_str == "high":
                importance = EmailImportance.HIGH
            elif importance_str == "low":
                importance = EmailImportance.LOW
            else:
                importance = EmailImportance.NORMAL
            
            flag_str = msg.get("Flag", "").lower()
            if flag_str == "flagged":
                flag = EmailFlag.FLAGGED
            elif flag_str == "completed":
                flag = EmailFlag.COMPLETED
            elif flag_str == "answered":
                flag = EmailFlag.ANSWERED
            elif flag_str == "forwarded":
                flag = EmailFlag.FORWARDED
            else:
                flag = EmailFlag.NONE
            
            conversation_id = msg.get("Thread-Index", msg.get("References", ""))
            
            body_text, body_html, attachments = self._extract_content(msg)
            
            email_obj = Email.create(
                message_id=message_id,
                subject=subject,
                from_address=from_addr,
                to_addresses=to_addrs,
                cc_addresses=cc_addrs,
                bcc_addresses=bcc_addrs,
                reply_to_addresses=reply_to_addrs,
                date=date,
                received_date=received_date,
                body_text=body_text,
                body_html=body_html,
                importance=importance,
                flag=flag,
                attachments=attachments,
                folder=folder,
                custom_folder=custom_folder,
                headers={k: v for k, v in msg.items()},
                conversation_id=conversation_id,
            )
            
            return email_obj
        except Exception as e:
            logger.error(f"Failed to parse email: {str(e)}")
            return None
    
    def _parse_address(self, address_str: str) -> Optional[EmailAddress]:
        """Parse email address string into EmailAddress object."""
        if not address_str:
            return None
            
        try:
            name, addr = email.utils.parseaddr(address_str)
            
            if not addr:
                return None
                
            return EmailAddress.create(address=addr, name=name if name else None)
        except:
            return None
    
    def _parse_addresses(self, addresses_str: str) -> List[EmailAddress]:
        """Parse multiple email addresses string into EmailAddress objects."""
        if not addresses_str:
            return []
            
        addresses = []
        
        for addr_str in addresses_str.split(","):
            addr = self._parse_address(addr_str.strip())
            if addr:
                addresses.append(addr)
                
        return addresses
    
    def _extract_content(self, msg) -> Tuple[str, Optional[str], List[EmailAttachment]]:
        """Extract body text, HTML, and attachments from email message."""
        body_text = ""
        body_html = None
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = part.get("Content-Disposition", "")
                
                if content_type == "multipart/alternative" or content_type == "multipart/mixed":
                    continue
                
                if "attachment" in content_disposition or "inline" in content_disposition:
                    filename = part.get_filename()
                    if not filename:
                        ext = content_type.split("/")[1] if "/" in content_type else "bin"
                        filename = f"attachment_{uuid.uuid4()}.{ext}"
                        
                    content = part.get_payload(decode=True)
                    size = len(content) if content else 0
                    
                    attachment = EmailAttachment.create(
                        filename=filename,
                        content_type=content_type,
                        size=size,
                        content_id=part.get("Content-ID"),
                        is_inline="inline" in content_disposition,
                    )
                    
                    attachments.append(attachment)
                elif content_type == "text/plain":
                    text = part.get_payload(decode=True)
                    if text:
                        body_text = text.decode("utf-8", errors="replace")
                elif content_type == "text/html":
                    html = part.get_payload(decode=True)
                    if html:
                        body_html = html.decode("utf-8", errors="replace")
        else:
            content_type = msg.get_content_type()
            
            if content_type == "text/plain":
                text = msg.get_payload(decode=True)
                if text:
                    body_text = text.decode("utf-8", errors="replace")
            elif content_type == "text/html":
                html = msg.get_payload(decode=True)
                if html:
                    body_html = html.decode("utf-8", errors="replace")
                    body_text = self._html_to_text(body_html)
        
        return body_text, body_html, attachments
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&quot;", "\"", text)
        text = re.sub(r"&apos;", "'", text)
        text = re.sub(r"\s+", " ", text)
        
        return text.strip()
    
    async def send_email(self, provider_id: str, email_obj: Email) -> bool:
        """Send an email using a provider."""
        if not await self._ensure_smtp_connection(provider_id):
            return False
            
        connection = self.connections.get(provider_id)
        if not connection or "smtp" not in connection or not connection["smtp"]:
            logger.error(f"No SMTP connection for provider {provider_id}")
            return False
            
        smtp = connection["smtp"]
        
        try:
            msg = MIMEMultipart()
            
            msg["Subject"] = email_obj.subject
            
            if email_obj.from_address:
                if email_obj.from_address.name:
                    msg["From"] = f"{email_obj.from_address.name} <{email_obj.from_address.address}>"
                else:
                    msg["From"] = email_obj.from_address.address
            
            if email_obj.to_addresses:
                to_addrs = []
                for addr in email_obj.to_addresses:
                    if addr.name:
                        to_addrs.append(f"{addr.name} <{addr.address}>")
                    else:
                        to_addrs.append(addr.address)
                msg["To"] = ", ".join(to_addrs)
            
            if email_obj.cc_addresses:
                cc_addrs = []
                for addr in email_obj.cc_addresses:
                    if addr.name:
                        cc_addrs.append(f"{addr.name} <{addr.address}>")
                    else:
                        cc_addrs.append(addr.address)
                msg["Cc"] = ", ".join(cc_addrs)
            
            if email_obj.reply_to_addresses:
                reply_to_addrs = []
                for addr in email_obj.reply_to_addresses:
                    if addr.name:
                        reply_to_addrs.append(f"{addr.name} <{addr.address}>")
                    else:
                        reply_to_addrs.append(addr.address)
                msg["Reply-To"] = ", ".join(reply_to_addrs)
            
            if email_obj.importance == EmailImportance.HIGH:
                msg["Importance"] = "High"
            elif email_obj.importance == EmailImportance.LOW:
                msg["Importance"] = "Low"
            
            if email_obj.body_text:
                msg.attach(MIMEText(email_obj.body_text, "plain"))
            
            if email_obj.body_html:
                msg.attach(MIMEText(email_obj.body_html, "html"))
            
            for attachment in email_obj.attachments:
                pass
            
            recipients = []
            
            if email_obj.to_addresses:
                recipients.extend([addr.address for addr in email_obj.to_addresses])
            
            if email_obj.cc_addresses:
                recipients.extend([addr.address for addr in email_obj.cc_addresses])
            
            if email_obj.bcc_addresses:
                recipients.extend([addr.address for addr in email_obj.bcc_addresses])
            
            if not recipients:
                logger.error("No recipients specified")
                return False
            
            smtp.sendmail(
                email_obj.from_address.address if email_obj.from_address else "",
                recipients,
                msg.as_string()
            )
            
            logger.info(f"Email sent: {email_obj.subject}")
            
            publish_event(EventType.EMAIL_SENT, {
                "provider_id": provider_id,
                "email_id": str(email_obj.id),
                "subject": email_obj.subject,
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def register_email_processor(self, processor: Callable[[Email], None]):
        """Register a function to process emails when they are synced."""
        if processor not in self.email_processors:
            self.email_processors.append(processor)
    
    def unregister_email_processor(self, processor: Callable[[Email], None]):
        """Unregister an email processor function."""
        if processor in self.email_processors:
            self.email_processors.remove(processor)

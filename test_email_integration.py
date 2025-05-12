"""
Tests for the email integration components.

This module provides tests for the email models, connector, processor, search, and UI components.
"""

import sys
import os
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from pathlib import Path
import uuid

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from src.core.config import Config
from src.core.events import EventType, subscribe_event
from src.models.email import Email, EmailAddress, EmailAttachment, EmailImportance, EmailFlag, EmailFolder, EmailSearchQuery
from src.services.email_connector import EmailConnectorService, EmailProvider
from src.services.email_processor import EmailProcessorService
from src.services.email_search import EmailSearchService
from src.services.document_processor import DocumentProcessorService
from src.services.vector_store import VectorStoreService
from src.services.vault_integration import VaultService
from src.ui.email_ui import EmailListItem, EmailListWidget, EmailViewWidget, EmailSearchWidget, EmailComposeWidget, EmailMainWidget


app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


def create_test_email():
    """Create a test email for testing."""
    from_address = EmailAddress.create(address="sender@example.com", name="Sender Name")
    to_addresses = [EmailAddress.create(address="recipient@example.com", name="Recipient Name")]
    
    attachments = [
        EmailAttachment.create(
            filename="test.txt",
            content_type="text/plain",
            size=1024,
        )
    ]
    
    email = Email.create(
        message_id=f"<{uuid.uuid4()}@example.com>",
        subject="Test Email Subject",
        from_address=from_address,
        to_addresses=to_addresses,
        body_text="This is a test email body.",
        body_html="<html><body><p>This is a test email body.</p></body></html>",
        attachments=attachments,
    )
    
    return email


async def test_email_models():
    """Test the email models."""
    print("Testing email models...")
    
    address = EmailAddress.create(address="test@example.com", name="Test User")
    assert address.address == "test@example.com"
    assert address.name == "Test User"
    
    address_dict = address.to_dict()
    assert address_dict["address"] == "test@example.com"
    assert address_dict["name"] == "Test User"
    
    address2 = EmailAddress.from_dict(address_dict)
    assert address2.address == address.address
    assert address2.name == address.name
    
    attachment = EmailAttachment.create(
        filename="test.txt",
        content_type="text/plain",
        size=1024,
        content_id="test-content-id",
        is_inline=True,
    )
    
    assert attachment.filename == "test.txt"
    assert attachment.content_type == "text/plain"
    assert attachment.size == 1024
    assert attachment.content_id == "test-content-id"
    assert attachment.is_inline is True
    
    attachment_dict = attachment.to_dict()
    assert attachment_dict["filename"] == "test.txt"
    assert attachment_dict["content_type"] == "text/plain"
    assert attachment_dict["size"] == 1024
    assert attachment_dict["content_id"] == "test-content-id"
    assert attachment_dict["is_inline"] is True
    
    attachment2 = EmailAttachment.from_dict(attachment_dict)
    assert attachment2.filename == attachment.filename
    assert attachment2.content_type == attachment.content_type
    assert attachment2.size == attachment.size
    assert attachment2.content_id == attachment.content_id
    assert attachment2.is_inline == attachment.is_inline
    
    from_address = EmailAddress.create(address="sender@example.com", name="Sender Name")
    to_addresses = [EmailAddress.create(address="recipient@example.com", name="Recipient Name")]
    cc_addresses = [EmailAddress.create(address="cc@example.com", name="CC Name")]
    
    email = Email.create(
        message_id="<test@example.com>",
        subject="Test Subject",
        from_address=from_address,
        to_addresses=to_addresses,
        cc_addresses=cc_addresses,
        body_text="Test body",
        body_html="<p>Test body</p>",
        importance=EmailImportance.HIGH,
        flag=EmailFlag.FLAGGED,
        attachments=[attachment],
        folder=EmailFolder.INBOX,
    )
    
    assert email.message_id == "<test@example.com>"
    assert email.subject == "Test Subject"
    assert email.from_address.address == "sender@example.com"
    assert email.to_addresses[0].address == "recipient@example.com"
    assert email.cc_addresses[0].address == "cc@example.com"
    assert email.body_text == "Test body"
    assert email.body_html == "<p>Test body</p>"
    assert email.importance == EmailImportance.HIGH
    assert email.flag == EmailFlag.FLAGGED
    assert len(email.attachments) == 1
    assert email.attachments[0].filename == "test.txt"
    assert email.folder == EmailFolder.INBOX
    
    email_dict = email.to_dict()
    assert email_dict["message_id"] == "<test@example.com>"
    assert email_dict["subject"] == "Test Subject"
    assert email_dict["from_address"]["address"] == "sender@example.com"
    assert email_dict["to_addresses"][0]["address"] == "recipient@example.com"
    assert email_dict["cc_addresses"][0]["address"] == "cc@example.com"
    assert email_dict["body_text"] == "Test body"
    assert email_dict["body_html"] == "<p>Test body</p>"
    assert email_dict["importance"] == "HIGH"
    assert email_dict["flag"] == "FLAGGED"
    assert len(email_dict["attachments"]) == 1
    assert email_dict["attachments"][0]["filename"] == "test.txt"
    assert email_dict["folder"] == "INBOX"
    
    email2 = Email.from_dict(email_dict)
    assert email2.message_id == email.message_id
    assert email2.subject == email.subject
    assert email2.from_address.address == email.from_address.address
    assert email2.to_addresses[0].address == email.to_addresses[0].address
    assert email2.cc_addresses[0].address == email.cc_addresses[0].address
    assert email2.body_text == email.body_text
    assert email2.body_html == email.body_html
    assert email2.importance == email.importance
    assert email2.flag == email.flag
    assert len(email2.attachments) == len(email.attachments)
    assert email2.attachments[0].filename == email.attachments[0].filename
    assert email2.folder == email.folder
    
    document = email.to_document()
    assert document.title == email.subject
    assert document.content == email.body_text
    assert document.metadata.author == email.from_address.name
    assert document.metadata.source_type == "email"
    assert document.metadata.source_id == email.message_id
    
    query = EmailSearchQuery.create(
        query_text="test query",
        folder=EmailFolder.INBOX,
        from_address="sender@example.com",
        subject="test",
        has_attachments=True,
        date_from=datetime.now() - timedelta(days=7),
        date_to=datetime.now(),
        is_read=False,
        importance=EmailImportance.HIGH,
        limit=10,
        offset=0,
    )
    
    assert query.query_text == "test query"
    assert query.folder == EmailFolder.INBOX
    assert query.from_address == "sender@example.com"
    assert query.subject == "test"
    assert query.has_attachments is True
    assert (datetime.now() - query.date_from).days <= 7
    assert (query.date_to - datetime.now()).days == 0
    assert query.is_read is False
    assert query.importance == EmailImportance.HIGH
    assert query.limit == 10
    assert query.offset == 0
    
    query_dict = query.to_dict()
    assert query_dict["query_text"] == "test query"
    assert query_dict["folder"] == "INBOX"
    assert query_dict["from_address"] == "sender@example.com"
    assert query_dict["subject"] == "test"
    assert query_dict["has_attachments"] is True
    assert "date_from" in query_dict
    assert "date_to" in query_dict
    assert query_dict["is_read"] is False
    assert query_dict["importance"] == "HIGH"
    assert query_dict["limit"] == 10
    assert query_dict["offset"] == 0
    
    print("Email models tests passed!")


async def test_email_connector():
    """Test the email connector service."""
    print("Testing email connector service...")
    
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "email.providers": [
            {
                "id": "test_provider",
                "name": "Test Provider",
                "type": "IMAP",
                "imap_host": "imap.example.com",
                "imap_port": 993,
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
            }
        ]
    }.get(key, default)
    
    vault_service = MagicMock(spec=VaultService)
    vault_service.get_secret.return_value = asyncio.Future()
    vault_service.get_secret.return_value.set_result({
        "username": "test@example.com",
        "password": "test_password",
    })
    
    connector = EmailConnectorService(config, vault_service)
    
    assert "test_provider" in connector.provider_settings
    assert connector.provider_settings["test_provider"]["name"] == "Test Provider"
    
    with patch("imaplib.IMAP4_SSL") as mock_imap, patch("smtplib.SMTP") as mock_smtp:
        mock_imap_instance = MagicMock()
        mock_imap.return_value = mock_imap_instance
        mock_imap_instance.login.return_value = None
        mock_imap_instance.select.return_value = ("OK", [b"1"])
        mock_imap_instance.search.return_value = ("OK", [b"1 2 3"])
        mock_imap_instance.fetch.return_value = ("OK", [(b"1", b"test email data")])
        
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_instance.starttls.return_value = None
        mock_smtp_instance.login.return_value = None
        mock_smtp_instance.sendmail.return_value = {}
        
        success = await connector.connect("test_provider")
        assert success is True
        assert "test_provider" in connector.connections
        assert connector.connections["test_provider"]["type"] == EmailProvider.IMAP
        assert connector.connections["test_provider"]["imap"] is not None
        
        emails = await connector.sync_emails("test_provider", EmailFolder.INBOX)
        assert len(emails) == 3  # Mock returned 3 emails
        
        email = create_test_email()
        success = await connector.send_email("test_provider", email)
        assert success is True
        
        success = await connector.disconnect("test_provider")
        assert success is True
        assert connector.connections["test_provider"] is None
    
    print("Email connector service tests passed!")


async def test_email_processor():
    """Test the email processor service."""
    print("Testing email processor service...")
    
    config = MagicMock(spec=Config)
    email_connector = MagicMock(spec=EmailConnectorService)
    document_processor = MagicMock(spec=DocumentProcessorService)
    vector_store = MagicMock(spec=VectorStoreService)
    
    document_processor.process_document.return_value = asyncio.Future()
    document_processor.process_document.return_value.set_result(MagicMock())
    
    vector_store.generate_embedding.return_value = asyncio.Future()
    vector_store.generate_embedding.return_value.set_result([0.1] * 384)
    
    vector_store.store_vectors.return_value = asyncio.Future()
    vector_store.store_vectors.return_value.set_result(None)
    
    processor = EmailProcessorService(config, email_connector, document_processor, vector_store)
    
    email = create_test_email()
    await processor.process_email(email)
    
    document_processor.process_document.assert_called_once()
    
    vector_store.generate_embedding.assert_called_once()
    vector_store.store_vectors.assert_called_once()
    
    entities = await processor.extract_entities(email)
    assert "keywords" in entities
    assert len(entities["keywords"]) > 0
    
    sentiment = await processor.analyze_sentiment(email)
    assert "sentiment" in sentiment
    assert "score" in sentiment
    
    print("Email processor service tests passed!")


async def test_email_search():
    """Test the email search service."""
    print("Testing email search service...")
    
    config = MagicMock(spec=Config)
    vector_store = MagicMock(spec=VectorStoreService)
    
    vector_store.list_collections.return_value = asyncio.Future()
    vector_store.list_collections.return_value.set_result(["emails"])
    
    vector_store.generate_embedding.return_value = asyncio.Future()
    vector_store.generate_embedding.return_value.set_result([0.1] * 384)
    
    vector_store.search_vectors.return_value = asyncio.Future()
    vector_store.search_vectors.return_value.set_result({
        "matches": [
            {"id": "1", "score": 0.9, "metadata": {"subject": "Test Email"}},
            {"id": "2", "score": 0.8, "metadata": {"subject": "Another Email"}},
        ],
        "total": 2,
    })
    
    vector_store.get_collection_count.return_value = asyncio.Future()
    vector_store.get_collection_count.return_value.set_result(10)
    
    search = EmailSearchService(config, vector_store)
    
    query = EmailSearchQuery.create(
        query_text="test query",
        folder=EmailFolder.INBOX,
    )
    
    result = await search.search(query)
    
    vector_store.generate_embedding.assert_called_once_with("test query")
    vector_store.search_vectors.assert_called_once()
    
    assert result.total_count == 2
    assert result.query == query
    
    emails = await search.get_recent_emails(limit=5)
    assert len(emails) == 2  # Mock returned 2 emails
    
    stats = await search.get_email_stats()
    assert stats["total_count"] == 10
    assert "folder_counts" in stats
    assert "date_counts" in stats
    
    print("Email search service tests passed!")


async def test_email_ui():
    """Test the email UI components."""
    print("Testing email UI components...")
    
    email = create_test_email()
    list_item = EmailListItem(email)
    
    assert list_item.email == email
    assert list_item.from_label.text() == "Sender Name"
    assert list_item.subject_label.text() == "Test Email Subject"
    
    list_widget = EmailListWidget()
    list_widget.set_emails([email])
    
    assert len(list_widget.emails) == 1
    assert len(list_widget.email_items) == 1
    
    view_widget = EmailViewWidget()
    view_widget.set_email(email)
    
    assert view_widget.email == email
    assert view_widget.subject_label.text() == "Test Email Subject"
    assert view_widget.from_label.text() == "Sender Name <sender@example.com>"
    assert view_widget.to_label.text() == "Recipient Name <recipient@example.com>"
    
    search_widget = EmailSearchWidget()
    
    assert search_widget.search_input is not None
    assert search_widget.search_button is not None
    assert search_widget.advanced_button is not None
    
    compose_widget = EmailComposeWidget()
    compose_widget.set_reply_to(email)
    
    assert compose_widget.reply_to == email
    assert compose_widget.to_input.text() == "sender@example.com"
    assert "Re: Test Email Subject" in compose_widget.subject_input.text()
    
    config = MagicMock(spec=Config)
    email_connector = MagicMock(spec=EmailConnectorService)
    email_processor = MagicMock(spec=EmailProcessorService)
    email_search = MagicMock(spec=EmailSearchService)
    
    main_widget = EmailMainWidget(config, email_connector, email_processor, email_search)
    
    assert main_widget.email_connector == email_connector
    assert main_widget.email_processor == email_processor
    assert main_widget.email_search == email_search
    
    print("Email UI components tests passed!")


async def run_tests():
    """Run all tests."""
    await test_email_models()
    await test_email_connector()
    await test_email_processor()
    await test_email_search()
    await test_email_ui()
    
    print("All email integration tests passed!")


if __name__ == "__main__":
    asyncio.run(run_tests())

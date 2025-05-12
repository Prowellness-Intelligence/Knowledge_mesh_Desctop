"""
Test file for the Legal Document Templates and DocuSign integration.

This module provides tests for the legal document templates and DocuSign
integration functionality.
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.core.config import Config
from src.core.events import EventType, Event, event_bus
from src.models.legal_document import (
    LegalDocumentType,
    LegalDocumentSector,
    LegalDocumentTemplate,
    LegalDocumentGenerationRequest,
    SignatureRequest,
    SignatureStatus,
)
from src.services.docusign_integration import DocuSignIntegrationService
from src.services.vault_integration import VaultIntegrationService


class TestLegalDocumentModels(unittest.TestCase):
    """Test the legal document models."""
    
    def test_legal_document_template(self):
        """Test the LegalDocumentTemplate class."""
        template = LegalDocumentTemplate.create(
            name="Employment Contract",
            description="Standard employment contract template",
            document_type=LegalDocumentType.EMPLOYMENT_CONTRACT,
            sector=LegalDocumentSector.EMPLOYMENT,
            content="This is an employment contract between {{company}} and {{employee}}.",
            variables=["company", "employee"],
        )
        
        self.assertEqual(template.name, "Employment Contract")
        self.assertEqual(template.description, "Standard employment contract template")
        self.assertEqual(template.document_type, LegalDocumentType.EMPLOYMENT_CONTRACT)
        self.assertEqual(template.sector, LegalDocumentSector.EMPLOYMENT)
        self.assertEqual(template.content, "This is an employment contract between {{company}} and {{employee}}.")
        self.assertEqual(template.variables, ["company", "employee"])
        self.assertTrue(template.is_sensitive)
        
        template_dict = template.to_dict()
        template2 = LegalDocumentTemplate.from_dict(template_dict)
        
        self.assertEqual(template.id, template2.id)
        self.assertEqual(template.name, template2.name)
        self.assertEqual(template.description, template2.description)
        self.assertEqual(template.document_type, template2.document_type)
        self.assertEqual(template.sector, template2.sector)
        self.assertEqual(template.content, template2.content)
        self.assertEqual(template.variables, template2.variables)
        self.assertEqual(template.is_sensitive, template2.is_sensitive)
        
        template.update(
            name="Updated Employment Contract",
            description="Updated description",
            is_sensitive=False,
        )
        
        self.assertEqual(template.name, "Updated Employment Contract")
        self.assertEqual(template.description, "Updated description")
        self.assertFalse(template.is_sensitive)
    
    def test_legal_document_generation_request(self):
        """Test the LegalDocumentGenerationRequest class."""
        request = LegalDocumentGenerationRequest.create(
            template_id="template123",
            variable_values={"company": "Acme Inc.", "employee": "John Doe"},
            user_id="user123",
            document_type=LegalDocumentType.EMPLOYMENT_CONTRACT,
            sector=LegalDocumentSector.EMPLOYMENT,
            signature_required=True,
            signatories=[
                {"name": "John Doe", "email": "john@example.com"},
                {"name": "Jane Smith", "email": "jane@example.com"},
            ],
        )
        
        self.assertEqual(request.template_id, "template123")
        self.assertEqual(request.variable_values, {"company": "Acme Inc.", "employee": "John Doe"})
        self.assertEqual(request.user_id, "user123")
        self.assertEqual(request.document_type, LegalDocumentType.EMPLOYMENT_CONTRACT)
        self.assertEqual(request.sector, LegalDocumentSector.EMPLOYMENT)
        self.assertTrue(request.signature_required)
        self.assertEqual(len(request.signatories), 2)
        self.assertEqual(request.signatories[0]["name"], "John Doe")
        self.assertEqual(request.signatories[1]["email"], "jane@example.com")
        
        request_dict = request.to_dict()
        request2 = LegalDocumentGenerationRequest.from_dict(request_dict)
        
        self.assertEqual(request.id, request2.id)
        self.assertEqual(request.template_id, request2.template_id)
        self.assertEqual(request.variable_values, request2.variable_values)
        self.assertEqual(request.user_id, request2.user_id)
        self.assertEqual(request.document_type, request2.document_type)
        self.assertEqual(request.sector, request2.sector)
        self.assertEqual(request.signature_required, request2.signature_required)
        self.assertEqual(len(request.signatories), len(request2.signatories))
    
    def test_signature_request(self):
        """Test the SignatureRequest class."""
        request = SignatureRequest.create(
            document_id="doc123",
            signatories=[
                {"name": "John Doe", "email": "john@example.com"},
                {"name": "Jane Smith", "email": "jane@example.com"},
            ],
            expires_in_days=15,
        )
        
        self.assertEqual(request.document_id, "doc123")
        self.assertEqual(len(request.signatories), 2)
        self.assertEqual(request.status, SignatureStatus.NOT_SENT)
        self.assertIsNone(request.completed_at)
        self.assertIsNotNone(request.expires_at)
        self.assertFalse(request.is_expired())
        
        request.update_status(SignatureStatus.SENT)
        self.assertEqual(request.status, SignatureStatus.SENT)
        
        request.update_status(SignatureStatus.SIGNED_COMPLETE)
        self.assertEqual(request.status, SignatureStatus.SIGNED_COMPLETE)
        self.assertIsNotNone(request.completed_at)
        
        request_dict = request.to_dict()
        request2 = SignatureRequest.from_dict(request_dict)
        
        self.assertEqual(request.id, request2.id)
        self.assertEqual(request.document_id, request2.document_id)
        self.assertEqual(request.status, request2.status)
        self.assertEqual(len(request.signatories), len(request2.signatories))
        
        request.expires_at = datetime.utcnow() - timedelta(days=1)
        self.assertTrue(request.is_expired())


class TestDocuSignIntegration(unittest.TestCase):
    """Test the DocuSign integration service."""
    
    def setUp(self):
        """Set up the test environment."""
        self.config = Config({
            "app.data_dir": "./test_data",
            "docusign.base_url": "https://demo.docusign.net/restapi",
            "docusign.integration_key": "test_integration_key",
            "docusign.user_id": "test_user_id",
            "docusign.account_id": "test_account_id",
            "docusign.signature_check_interval": 1,
        })
        
        self.vault_service = MagicMock(spec=VaultIntegrationService)
        self.vault_service.get_secret = AsyncMock(return_value="test_private_key")
        
        self.service = DocuSignIntegrationService(self.config, self.vault_service)
        
        os.makedirs("./test_data/docusign", exist_ok=True)
    
    def tearDown(self):
        """Clean up the test environment."""
        import shutil
        if os.path.exists("./test_data"):
            shutil.rmtree("./test_data")
    
    def test_initialization(self):
        """Test service initialization."""
        self.assertEqual(self.service.config, self.config)
        self.assertEqual(self.service.vault_service, self.vault_service)
        self.assertFalse(self.service.is_running)
        self.assertEqual(self.service.base_url, "https://demo.docusign.net/restapi")
        self.assertEqual(self.service.integration_key, "test_integration_key")
        self.assertEqual(self.service.user_id, "test_user_id")
        self.assertEqual(self.service.account_id, "test_account_id")
        self.assertIsNone(self.service.auth_token)
        self.assertIsNone(self.service.auth_token_expires_at)
        self.assertEqual(self.service.signature_requests, {})
        self.assertEqual(self.service.signature_check_interval, 1)
        self.assertIsNone(self.service.signature_check_task)
    
    @patch("aiohttp.ClientSession.post")
    async def test_get_auth_token(self, mock_post):
        """Test getting an authentication token."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "test_access_token",
            "expires_in": 3600,
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        with patch.object(self.service, "_create_jwt", return_value="test_jwt"):
            loop = asyncio.get_event_loop()
            token = await loop.run_until_complete(self.service._get_auth_token())
            
            self.assertEqual(token, "test_access_token")
            self.assertEqual(self.service.auth_token, "test_access_token")
            self.assertIsNotNone(self.service.auth_token_expires_at)
            
            self.vault_service.get_secret.assert_called_once_with("docusign_private_key")
            
            self.service._create_jwt.assert_called_once_with("test_private_key")
            
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], "https://demo.docusign.net/oauth/token")
            self.assertEqual(kwargs["data"]["grant_type"], "urn:ietf:params:oauth:grant-type:jwt-bearer")
            self.assertEqual(kwargs["data"]["assertion"], "test_jwt")
    
    @patch("aiohttp.ClientSession.post")
    async def test_send_document_for_signature(self, mock_post):
        """Test sending a document for signature."""
        test_document_path = "./test_data/test_document.pdf"
        os.makedirs(os.path.dirname(test_document_path), exist_ok=True)
        with open(test_document_path, "wb") as f:
            f.write(b"Test document content")
        
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={
            "envelopeId": "test_envelope_id",
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        with patch.object(self.service, "_get_auth_token", AsyncMock(return_value="test_auth_token")):
            with patch("src.services.docusign_integration.publish_event") as mock_publish:
                loop = asyncio.get_event_loop()
                
                signatories = [
                    {"name": "John Doe", "email": "john@example.com"},
                    {"name": "Jane Smith", "email": "jane@example.com"},
                ]
                
                signature_request = await loop.run_until_complete(self.service.send_document_for_signature(
                    document_path=test_document_path,
                    document_name="Test Document",
                    signatories=signatories,
                ))
                
                self.assertIsNotNone(signature_request)
                self.assertEqual(signature_request.document_id, "test_document.pdf")
                self.assertEqual(signature_request.status, SignatureStatus.SENT)
                self.assertEqual(signature_request.docusign_envelope_id, "test_envelope_id")
                self.assertEqual(len(signature_request.signatories), 2)
                
                self.service._get_auth_token.assert_called_once()
                
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertEqual(args[0], "https://demo.docusign.net/restapi/v2.1/accounts/test_account_id/envelopes")
                self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test_auth_token")
                self.assertEqual(kwargs["json"]["emailSubject"], "Please sign this document")
                self.assertEqual(len(kwargs["json"]["documents"]), 1)
                self.assertEqual(kwargs["json"]["documents"][0]["name"], "Test Document")
                self.assertEqual(len(kwargs["json"]["recipients"]["signers"]), 2)
                
                mock_publish.assert_called_once()
                args, kwargs = mock_publish.call_args
                self.assertEqual(args[0], EventType.DOCUMENT_SENT_FOR_SIGNATURE)
                self.assertEqual(args[1]["envelope_id"], "test_envelope_id")
                
                self.assertEqual(len(self.service.signature_requests), 1)
                self.assertIn(signature_request.id, self.service.signature_requests)
    
    @patch("aiohttp.ClientSession.get")
    async def test_check_signature_status(self, mock_get):
        """Test checking signature status."""
        signature_request = SignatureRequest.create(
            document_id="test_document.pdf",
            signatories=[
                {"name": "John Doe", "email": "john@example.com"},
            ],
        )
        signature_request.docusign_envelope_id = "test_envelope_id"
        signature_request.update_status(SignatureStatus.SENT)
        
        self.service.signature_requests[signature_request.id] = signature_request
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "status": "completed",
        })
        mock_get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(self.service, "_get_auth_token", AsyncMock(return_value="test_auth_token")):
            with patch("src.services.docusign_integration.publish_event") as mock_publish:
                loop = asyncio.get_event_loop()
                
                updated_request = await loop.run_until_complete(self.service._check_signature_status(signature_request))
                
                self.assertEqual(updated_request.status, SignatureStatus.SIGNED_COMPLETE)
                self.assertIsNotNone(updated_request.completed_at)
                
                self.service._get_auth_token.assert_called_once()
                
                mock_get.assert_called_once()
                args, kwargs = mock_get.call_args
                self.assertEqual(args[0], "https://demo.docusign.net/restapi/v2.1/accounts/test_account_id/envelopes/test_envelope_id")
                self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test_auth_token")
                
                mock_publish.assert_called_once()
                args, kwargs = mock_publish.call_args
                self.assertEqual(args[0], EventType.DOCUMENT_SIGNATURE_STATUS_CHANGED)
                self.assertEqual(args[1]["old_status"], "SENT")
                self.assertEqual(args[1]["new_status"], "SIGNED_COMPLETE")
    
    @patch("aiohttp.ClientSession.put")
    async def test_cancel_signature_request(self, mock_put):
        """Test canceling a signature request."""
        signature_request = SignatureRequest.create(
            document_id="test_document.pdf",
            signatories=[
                {"name": "John Doe", "email": "john@example.com"},
            ],
        )
        signature_request.docusign_envelope_id = "test_envelope_id"
        signature_request.update_status(SignatureStatus.SENT)
        
        self.service.signature_requests[signature_request.id] = signature_request
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_put.return_value.__aenter__.return_value = mock_response
        
        with patch.object(self.service, "_get_auth_token", AsyncMock(return_value="test_auth_token")):
            with patch("src.services.docusign_integration.publish_event") as mock_publish:
                loop = asyncio.get_event_loop()
                
                canceled_request = await loop.run_until_complete(self.service.cancel_signature_request(signature_request.id))
                
                self.assertEqual(canceled_request.status, SignatureStatus.CANCELED)
                
                self.service._get_auth_token.assert_called_once()
                
                mock_put.assert_called_once()
                args, kwargs = mock_put.call_args
                self.assertEqual(args[0], "https://demo.docusign.net/restapi/v2.1/accounts/test_account_id/envelopes/test_envelope_id")
                self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test_auth_token")
                self.assertEqual(kwargs["json"]["status"], "voided")
                
                mock_publish.assert_called_once()
                args, kwargs = mock_publish.call_args
                self.assertEqual(args[0], EventType.DOCUMENT_SIGNATURE_CANCELED)
    
    @patch("aiohttp.ClientSession.get")
    async def test_download_signed_document(self, mock_get):
        """Test downloading a signed document."""
        signature_request = SignatureRequest.create(
            document_id="test_document.pdf",
            signatories=[
                {"name": "John Doe", "email": "john@example.com"},
            ],
        )
        signature_request.docusign_envelope_id = "test_envelope_id"
        signature_request.update_status(SignatureStatus.SIGNED_COMPLETE)
        
        self.service.signature_requests[signature_request.id] = signature_request
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"Signed document content")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(self.service, "_get_auth_token", AsyncMock(return_value="test_auth_token")):
            loop = asyncio.get_event_loop()
            
            output_path = "./test_data/signed_document.pdf"
            
            success = await loop.run_until_complete(self.service.download_signed_document(signature_request.id, output_path))
            
            self.assertTrue(success)
            self.assertTrue(os.path.exists(output_path))
            
            with open(output_path, "rb") as f:
                content = f.read()
                self.assertEqual(content, b"Signed document content")
            
            self.service._get_auth_token.assert_called_once()
            
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            self.assertEqual(args[0], "https://demo.docusign.net/restapi/v2.1/accounts/test_account_id/envelopes/test_envelope_id/documents/combined")
            self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test_auth_token")


if __name__ == "__main__":
    unittest.main()

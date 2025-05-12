"""
DocuSign integration service for the Knowledge Mesh Desktop application.

This module provides integration with DocuSign for electronic signatures
on legal documents.
"""

import os
import json
import uuid
import base64
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple

import aiohttp
from aiohttp import ClientSession

from src.core.config import Config
from src.core.events import EventType, publish_event
from src.models.legal_document import SignatureRequest, SignatureStatus
from src.services.vault_integration import VaultIntegrationService


logger = logging.getLogger(__name__)


class DocuSignIntegrationService:
    """
    Service for integrating with DocuSign for electronic signatures.
    
    This service provides functionality for sending documents for signature,
    checking signature status, and handling signature callbacks.
    """
    
    def __init__(self, config: Config, vault_service: VaultIntegrationService):
        """
        Initialize the DocuSign integration service.
        
        Args:
            config: The application configuration
            vault_service: The vault integration service for secure storage
        """
        self.config = config
        self.vault_service = vault_service
        self.is_running = False
        
        self.base_url = self.config.get("docusign.base_url", "https://demo.docusign.net/restapi")
        self.integration_key = self.config.get("docusign.integration_key", "")
        self.user_id = self.config.get("docusign.user_id", "")
        self.account_id = self.config.get("docusign.account_id", "")
        
        self.auth_token = None
        self.auth_token_expires_at = None
        
        self.signature_requests = {}
        self.signature_check_interval = self.config.get("docusign.signature_check_interval", 300)  # 5 minutes
        self.signature_check_task = None
        
        self.data_dir = os.path.join(self.config.get("app.data_dir", "./data"), "docusign")
        os.makedirs(self.data_dir, exist_ok=True)
    
    async def start(self):
        """Start the DocuSign integration service."""
        if self.is_running:
            return
        
        logger.info("Starting DocuSign integration service")
        
        self.is_running = True
        
        await self._load_signature_requests()
        
        self.signature_check_task = asyncio.create_task(self._check_signatures_periodically())
        
        logger.info("DocuSign integration service started")
    
    async def stop(self):
        """Stop the DocuSign integration service."""
        if not self.is_running:
            return
        
        logger.info("Stopping DocuSign integration service")
        
        self.is_running = False
        
        if self.signature_check_task:
            self.signature_check_task.cancel()
            try:
                await self.signature_check_task
            except asyncio.CancelledError:
                pass
            self.signature_check_task = None
        
        await self._save_signature_requests()
        
        logger.info("DocuSign integration service stopped")
    
    async def _load_signature_requests(self):
        """Load signature requests from disk."""
        try:
            signature_requests_file = os.path.join(self.data_dir, "signature_requests.json")
            
            if not os.path.exists(signature_requests_file):
                self.signature_requests = {}
                return
            
            with open(signature_requests_file, "r") as f:
                signature_requests_data = json.load(f)
            
            self.signature_requests = {}
            
            for request_id, request_data in signature_requests_data.items():
                self.signature_requests[request_id] = SignatureRequest.from_dict(request_data)
            
            logger.info(f"Loaded {len(self.signature_requests)} signature requests from disk")
        except Exception as e:
            logger.error(f"Error loading signature requests: {e}")
            self.signature_requests = {}
    
    async def _save_signature_requests(self):
        """Save signature requests to disk."""
        try:
            signature_requests_file = os.path.join(self.data_dir, "signature_requests.json")
            
            signature_requests_data = {}
            
            for request_id, request in self.signature_requests.items():
                signature_requests_data[request_id] = request.to_dict()
            
            with open(signature_requests_file, "w") as f:
                json.dump(signature_requests_data, f, indent=2)
            
            logger.info(f"Saved {len(self.signature_requests)} signature requests to disk")
        except Exception as e:
            logger.error(f"Error saving signature requests: {e}")
    
    async def _check_signatures_periodically(self):
        """Check signature status periodically."""
        while self.is_running:
            try:
                await self._check_all_signatures()
            except Exception as e:
                logger.error(f"Error checking signatures: {e}")
            
            await asyncio.sleep(self.signature_check_interval)
    
    async def _check_all_signatures(self):
        """Check the status of all pending signature requests."""
        for request_id, request in list(self.signature_requests.items()):
            if request.status in [SignatureStatus.SENT, SignatureStatus.VIEWED, SignatureStatus.SIGNED_PARTIAL]:
                try:
                    await self._check_signature_status(request)
                except Exception as e:
                    logger.error(f"Error checking signature status for request {request_id}: {e}")
    
    async def _get_auth_token(self) -> str:
        """
        Get an authentication token for DocuSign API.
        
        Returns:
            The authentication token
        """
        if self.auth_token and self.auth_token_expires_at and datetime.utcnow() < self.auth_token_expires_at:
            return self.auth_token
        
        private_key = await self.vault_service.get_secret("docusign_private_key")
        
        if not private_key:
            raise ValueError("DocuSign private key not found in vault")
        
        async with ClientSession() as session:
            url = f"{self.base_url.replace('/restapi', '')}/oauth/token"
            
            payload = {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": self._create_jwt(private_key),
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }
            
            async with session.post(url, data=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"Error getting DocuSign auth token: {error_text}")
                
                data = await response.json()
                
                self.auth_token = data["access_token"]
                self.auth_token_expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"] - 300)  # 5 minutes buffer
                
                return self.auth_token
    
    def _create_jwt(self, private_key: str) -> str:
        """
        Create a JWT token for DocuSign authentication.
        
        Args:
            private_key: The private key for signing the JWT
            
        Returns:
            The JWT token
        """
        import jwt
        
        now = datetime.utcnow()
        
        payload = {
            "iss": self.integration_key,
            "sub": self.user_id,
            "iat": now,
            "exp": now + timedelta(hours=1),
            "aud": self.base_url.replace("/restapi", ""),
            "scope": "signature impersonation",
        }
        
        return jwt.encode(payload, private_key, algorithm="RS256")
    
    async def send_document_for_signature(
        self,
        document_path: str,
        document_name: str,
        signatories: List[Dict[str, Any]],
        email_subject: str = "Please sign this document",
        email_body: str = "Please sign this document",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SignatureRequest:
        """
        Send a document for signature via DocuSign.
        
        Args:
            document_path: Path to the document file
            document_name: Name of the document
            signatories: List of signatories for the document
            email_subject: Subject of the email sent to signatories
            email_body: Body of the email sent to signatories
            metadata: Additional metadata for the signature request
            
        Returns:
            A SignatureRequest object
        """
        if not os.path.exists(document_path):
            raise FileNotFoundError(f"Document not found: {document_path}")
        
        signature_request = SignatureRequest.create(
            document_id=os.path.basename(document_path),
            signatories=signatories,
            metadata=metadata,
        )
        
        auth_token = await self._get_auth_token()
        
        with open(document_path, "rb") as f:
            document_bytes = f.read()
        
        document_base64 = base64.b64encode(document_bytes).decode("utf-8")
        
        envelope_definition = {
            "emailSubject": email_subject,
            "emailBlurb": email_body,
            "documents": [
                {
                    "documentBase64": document_base64,
                    "name": document_name,
                    "fileExtension": os.path.splitext(document_path)[1][1:],
                    "documentId": "1",
                }
            ],
            "recipients": {
                "signers": []
            },
            "status": "sent",
        }
        
        for i, signatory in enumerate(signatories):
            envelope_definition["recipients"]["signers"].append({
                "email": signatory["email"],
                "name": signatory["name"],
                "recipientId": str(i + 1),
                "routingOrder": str(i + 1),
                "tabs": {
                    "signHereTabs": [
                        {
                            "documentId": "1",
                            "pageNumber": "1",
                            "xPosition": signatory.get("x_position", "100"),
                            "yPosition": signatory.get("y_position", "100"),
                        }
                    ]
                }
            })
        
        async with ClientSession() as session:
            url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes"
            
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }
            
            async with session.post(url, json=envelope_definition, headers=headers) as response:
                if response.status != 201:
                    error_text = await response.text()
                    raise ValueError(f"Error sending document for signature: {error_text}")
                
                data = await response.json()
                
                envelope_id = data["envelopeId"]
                
                signature_request.docusign_envelope_id = envelope_id
                signature_request.update_status(SignatureStatus.SENT)
                
                self.signature_requests[signature_request.id] = signature_request
                await self._save_signature_requests()
                
                publish_event(
                    EventType.DOCUMENT_SENT_FOR_SIGNATURE,
                    {
                        "signature_request_id": signature_request.id,
                        "document_id": signature_request.document_id,
                        "envelope_id": envelope_id,
                    },
                )
                
                return signature_request
    
    async def _check_signature_status(self, signature_request: SignatureRequest) -> SignatureRequest:
        """
        Check the status of a signature request.
        
        Args:
            signature_request: The signature request to check
            
        Returns:
            The updated SignatureRequest
        """
        if not signature_request.docusign_envelope_id:
            return signature_request
        
        auth_token = await self._get_auth_token()
        
        async with ClientSession() as session:
            url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{signature_request.docusign_envelope_id}"
            
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error checking signature status: {error_text}")
                    return signature_request
                
                data = await response.json()
                
                status = data["status"]
                
                if status == "sent":
                    new_status = SignatureStatus.SENT
                elif status == "delivered":
                    new_status = SignatureStatus.VIEWED
                elif status == "completed":
                    new_status = SignatureStatus.SIGNED_COMPLETE
                elif status == "declined":
                    new_status = SignatureStatus.DECLINED
                elif status == "voided":
                    new_status = SignatureStatus.CANCELED
                else:
                    recipients = data.get("recipients", {}).get("signers", [])
                    
                    if any(r.get("status") == "completed" for r in recipients):
                        new_status = SignatureStatus.SIGNED_PARTIAL
                    else:
                        new_status = SignatureStatus.SENT
                
                if new_status != signature_request.status:
                    old_status = signature_request.status
                    signature_request.update_status(new_status)
                    
                    await self._save_signature_requests()
                    
                    publish_event(
                        EventType.DOCUMENT_SIGNATURE_STATUS_CHANGED,
                        {
                            "signature_request_id": signature_request.id,
                            "document_id": signature_request.document_id,
                            "old_status": old_status.name,
                            "new_status": new_status.name,
                        },
                    )
                
                return signature_request
    
    async def get_signature_request(self, request_id: str) -> Optional[SignatureRequest]:
        """
        Get a signature request by ID.
        
        Args:
            request_id: The ID of the signature request
            
        Returns:
            The SignatureRequest or None if not found
        """
        return self.signature_requests.get(request_id)
    
    async def get_signature_requests_for_document(self, document_id: str) -> List[SignatureRequest]:
        """
        Get all signature requests for a document.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A list of SignatureRequest objects
        """
        return [r for r in self.signature_requests.values() if r.document_id == document_id]
    
    async def cancel_signature_request(self, request_id: str) -> Optional[SignatureRequest]:
        """
        Cancel a signature request.
        
        Args:
            request_id: The ID of the signature request
            
        Returns:
            The updated SignatureRequest or None if not found
        """
        signature_request = self.signature_requests.get(request_id)
        
        if not signature_request or not signature_request.docusign_envelope_id:
            return None
        
        auth_token = await self._get_auth_token()
        
        async with ClientSession() as session:
            url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{signature_request.docusign_envelope_id}"
            
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "status": "voided",
                "voidedReason": "Canceled by user",
            }
            
            async with session.put(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"Error canceling signature request: {error_text}")
                
                signature_request.update_status(SignatureStatus.CANCELED)
                
                await self._save_signature_requests()
                
                publish_event(
                    EventType.DOCUMENT_SIGNATURE_CANCELED,
                    {
                        "signature_request_id": signature_request.id,
                        "document_id": signature_request.document_id,
                    },
                )
                
                return signature_request
    
    async def download_signed_document(self, request_id: str, output_path: str) -> bool:
        """
        Download a signed document.
        
        Args:
            request_id: The ID of the signature request
            output_path: Path to save the signed document
            
        Returns:
            True if successful, False otherwise
        """
        signature_request = self.signature_requests.get(request_id)
        
        if not signature_request or not signature_request.docusign_envelope_id:
            return False
        
        if signature_request.status != SignatureStatus.SIGNED_COMPLETE:
            return False
        
        auth_token = await self._get_auth_token()
        
        async with ClientSession() as session:
            url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{signature_request.docusign_envelope_id}/documents/combined"
            
            headers = {
                "Authorization": f"Bearer {auth_token}",
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error downloading signed document: {error_text}")
                    return False
                
                document_bytes = await response.read()
                
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, "wb") as f:
                    f.write(document_bytes)
                
                return True
    
    async def get_docusign_status(self) -> Dict[str, Any]:
        """
        Get the status of the DocuSign integration.
        
        Returns:
            A dictionary with the status information
        """
        try:
            auth_token = await self._get_auth_token()
            
            async with ClientSession() as session:
                url = f"{self.base_url}/v2.1/accounts/{self.account_id}/users/{self.user_id}"
                
                headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json",
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return {
                            "status": "error",
                            "message": "Error connecting to DocuSign API",
                            "connected": False,
                        }
                    
                    data = await response.json()
                    
                    return {
                        "status": "ok",
                        "message": "Connected to DocuSign API",
                        "connected": True,
                        "user_name": data.get("userName", ""),
                        "user_email": data.get("email", ""),
                        "account_name": data.get("accountName", ""),
                    }
        except Exception as e:
            logger.error(f"Error getting DocuSign status: {e}")
            
            return {
                "status": "error",
                "message": str(e),
                "connected": False,
            }

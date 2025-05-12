"""
HashiCorp Vault Integration for the Knowledge Mesh Desktop application.

This module provides integration with HashiCorp Vault for secure storage
of sensitive information and secrets.
"""

import asyncio
import logging
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable
import hvac
import requests

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus

logger = logging.getLogger(__name__)


class VaultIntegration:
    """
    Integration with HashiCorp Vault for secure storage.
    
    This service provides integration with HashiCorp Vault for secure storage
    of sensitive information, secrets, and encryption keys.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Vault integration.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.client = None
        self.is_authenticated = False
        self.token = None
        self.token_expiry = None
        self.mount_point = "knowledge-mesh"
        self.data_dir = Path(self.config.get("app.data_dir", "."))
        self.vault_config_dir = self.data_dir / "vault"
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.vault_url = self.config.get("vault.url", "http://127.0.0.1:8200")
        self.vault_token = self.config.get("vault.token", None)
        self.vault_role_id = self.config.get("vault.role_id", None)
        self.vault_secret_id = self.config.get("vault.secret_id", None)
        self.mount_point = self.config.get("vault.mount_point", "knowledge-mesh")
        self.token_ttl = self.config.get("vault.token_ttl", 3600)  # 1 hour
        self.enabled = self.config.get("vault.enabled", False)
    
    async def initialize(self):
        """Initialize the Vault integration."""
        logger.info("Initializing Vault integration")
        
        if not self.enabled:
            logger.info("Vault integration is disabled")
            return
        
        try:
            self.vault_config_dir.mkdir(parents=True, exist_ok=True)
            
            self.client = hvac.Client(url=self.vault_url)
            
            if not self.client.sys.is_sealed():
                logger.info("Vault is available and unsealed")
            else:
                logger.warning("Vault is sealed, some operations may not be available")
            
            await self.authenticate()
            
            event_bus.subscribe(EventType.AUTHENTICATION_REQUIRED, self._on_authentication_required)
            
            logger.info("Vault integration initialized")
        except Exception as e:
            logger.error(f"Error initializing Vault integration: {e}", exc_info=True)
            self.enabled = False
    
    async def start(self):
        """Start the Vault integration."""
        logger.info("Starting Vault integration")
        
        if not self.enabled:
            logger.info("Vault integration is disabled")
            return
        
        if self.is_authenticated and not self.client.sys.list_mounted_secrets_engines().get(f"{self.mount_point}/"):
            await self._setup_vault()
        
        logger.info("Vault integration started")
    
    async def stop(self):
        """Stop the Vault integration."""
        logger.info("Stopping Vault integration")
        
        event_bus.unsubscribe(EventType.AUTHENTICATION_REQUIRED, self._on_authentication_required)
        
        if self.is_authenticated and self.token:
            try:
                self.client.auth.token.revoke_self()
                logger.info("Vault token revoked")
            except Exception as e:
                logger.error(f"Error revoking Vault token: {e}", exc_info=True)
        
        self.is_authenticated = False
        self.token = None
        self.token_expiry = None
        
        logger.info("Vault integration stopped")
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Vault.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            if self.token and self.token_expiry and datetime.now() < self.token_expiry:
                self.client.token = self.token
                self.is_authenticated = True
                logger.debug("Using existing Vault token")
                return True
            
            if self.vault_token:
                self.client.token = self.vault_token
                if self.client.is_authenticated():
                    self.token = self.vault_token
                    self.token_expiry = datetime.now() + timedelta(seconds=self.token_ttl)
                    self.is_authenticated = True
                    logger.info("Authenticated with Vault using token")
                    return True
            
            if self.vault_role_id and self.vault_secret_id:
                try:
                    result = self.client.auth.approle.login(
                        role_id=self.vault_role_id,
                        secret_id=self.vault_secret_id,
                    )
                    
                    self.token = result["auth"]["client_token"]
                    self.token_expiry = datetime.now() + timedelta(seconds=result["auth"]["lease_duration"])
                    self.client.token = self.token
                    self.is_authenticated = True
                    logger.info("Authenticated with Vault using AppRole")
                    return True
                except Exception as e:
                    logger.error(f"Error authenticating with Vault using AppRole: {e}", exc_info=True)
            
            logger.warning("Failed to authenticate with Vault")
            self.is_authenticated = False
            return False
        except Exception as e:
            logger.error(f"Error authenticating with Vault: {e}", exc_info=True)
            self.is_authenticated = False
            return False
    
    async def _setup_vault(self):
        """Set up the Vault with the necessary secrets engines and policies."""
        if not self.is_authenticated:
            logger.warning("Not authenticated with Vault, cannot set up")
            return
        
        try:
            if not self.client.sys.list_mounted_secrets_engines().get(f"{self.mount_point}/"):
                self.client.sys.enable_secrets_engine(
                    backend_type="kv",
                    path=self.mount_point,
                    options={"version": "2"},
                )
                logger.info(f"Enabled KV secrets engine at {self.mount_point}")
            
            policy_name = "knowledge-mesh-policy"
            policy_rules = {
                "path": {
                    f"{self.mount_point}/*": {
                        "capabilities": ["create", "read", "update", "delete", "list"]
                    }
                }
            }
            
            self.client.sys.create_or_update_policy(
                name=policy_name,
                policy=json.dumps(policy_rules),
            )
            
            logger.info(f"Created policy {policy_name}")
        except Exception as e:
            logger.error(f"Error setting up Vault: {e}", exc_info=True)
    
    async def store_secret(self, path: str, data: Dict[str, Any]) -> bool:
        """
        Store a secret in Vault.
        
        Args:
            path: The path to store the secret at
            data: The secret data
            
        Returns:
            True if the secret was stored successfully, False otherwise
        """
        if not self.enabled or not self.is_authenticated:
            logger.warning("Not authenticated with Vault, cannot store secret")
            return False
        
        try:
            if not await self.authenticate():
                logger.warning("Failed to authenticate with Vault, cannot store secret")
                return False
            
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=data,
                mount_point=self.mount_point,
            )
            
            logger.info(f"Stored secret at {path}")
            return True
        except Exception as e:
            logger.error(f"Error storing secret: {e}", exc_info=True)
            return False
    
    async def get_secret(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get a secret from Vault.
        
        Args:
            path: The path to get the secret from
            
        Returns:
            The secret data, or None if the secret was not found
        """
        if not self.enabled or not self.is_authenticated:
            logger.warning("Not authenticated with Vault, cannot get secret")
            return None
        
        try:
            if not await self.authenticate():
                logger.warning("Failed to authenticate with Vault, cannot get secret")
                return None
            
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point,
            )
            
            if response and "data" in response and "data" in response["data"]:
                logger.info(f"Retrieved secret from {path}")
                return response["data"]["data"]
            
            logger.warning(f"Secret not found at {path}")
            return None
        except Exception as e:
            logger.error(f"Error getting secret: {e}", exc_info=True)
            return None
    
    async def delete_secret(self, path: str) -> bool:
        """
        Delete a secret from Vault.
        
        Args:
            path: The path to delete the secret from
            
        Returns:
            True if the secret was deleted successfully, False otherwise
        """
        if not self.enabled or not self.is_authenticated:
            logger.warning("Not authenticated with Vault, cannot delete secret")
            return False
        
        try:
            if not await self.authenticate():
                logger.warning("Failed to authenticate with Vault, cannot delete secret")
                return False
            
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=self.mount_point,
            )
            
            logger.info(f"Deleted secret at {path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting secret: {e}", exc_info=True)
            return False
    
    async def list_secrets(self, path: str) -> Optional[List[str]]:
        """
        List secrets at a path in Vault.
        
        Args:
            path: The path to list secrets at
            
        Returns:
            A list of secret names, or None if the path was not found
        """
        if not self.enabled or not self.is_authenticated:
            logger.warning("Not authenticated with Vault, cannot list secrets")
            return None
        
        try:
            if not await self.authenticate():
                logger.warning("Failed to authenticate with Vault, cannot list secrets")
                return None
            
            response = self.client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=self.mount_point,
            )
            
            if response and "data" in response and "keys" in response["data"]:
                logger.info(f"Listed secrets at {path}")
                return response["data"]["keys"]
            
            logger.warning(f"No secrets found at {path}")
            return []
        except Exception as e:
            logger.error(f"Error listing secrets: {e}", exc_info=True)
            return None
    
    async def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Encrypt a plaintext string using Vault's transit engine.
        
        Args:
            plaintext: The plaintext to encrypt
            
        Returns:
            The encrypted ciphertext, or None if encryption failed
        """
        if not self.enabled or not self.is_authenticated:
            logger.warning("Not authenticated with Vault, cannot encrypt")
            return None
        
        try:
            if not await self.authenticate():
                logger.warning("Failed to authenticate with Vault, cannot encrypt")
                return None
            
            if not self.client.sys.list_mounted_secrets_engines().get("transit/"):
                self.client.sys.enable_secrets_engine(
                    backend_type="transit",
                    path="transit",
                )
                logger.info("Enabled transit secrets engine")
                
                self.client.secrets.transit.create_key(
                    name="knowledge-mesh",
                    mount_point="transit",
                )
                logger.info("Created encryption key")
            
            response = self.client.secrets.transit.encrypt_data(
                name="knowledge-mesh",
                plaintext=plaintext,
                mount_point="transit",
            )
            
            if response and "data" in response and "ciphertext" in response["data"]:
                logger.debug("Encrypted plaintext")
                return response["data"]["ciphertext"]
            
            logger.warning("Failed to encrypt plaintext")
            return None
        except Exception as e:
            logger.error(f"Error encrypting plaintext: {e}", exc_info=True)
            return None
    
    async def decrypt(self, ciphertext: str) -> Optional[str]:
        """
        Decrypt a ciphertext string using Vault's transit engine.
        
        Args:
            ciphertext: The ciphertext to decrypt
            
        Returns:
            The decrypted plaintext, or None if decryption failed
        """
        if not self.enabled or not self.is_authenticated:
            logger.warning("Not authenticated with Vault, cannot decrypt")
            return None
        
        try:
            if not await self.authenticate():
                logger.warning("Failed to authenticate with Vault, cannot decrypt")
                return None
            
            if not self.client.sys.list_mounted_secrets_engines().get("transit/"):
                logger.warning("Transit engine not enabled, cannot decrypt")
                return None
            
            response = self.client.secrets.transit.decrypt_data(
                name="knowledge-mesh",
                ciphertext=ciphertext,
                mount_point="transit",
            )
            
            if response and "data" in response and "plaintext" in response["data"]:
                logger.debug("Decrypted ciphertext")
                return response["data"]["plaintext"]
            
            logger.warning("Failed to decrypt ciphertext")
            return None
        except Exception as e:
            logger.error(f"Error decrypting ciphertext: {e}", exc_info=True)
            return None
    
    def _on_authentication_required(self, event):
        """
        Handle authentication required events.
        
        Args:
            event: The authentication required event
        """
        reason = event.data.get("reason", "")
        callback_event = event.data.get("callback_event")
        callback_data = event.data.get("callback_data")
        
        if callback_event and callback_data:
            publish(
                EventType.AUTHENTICATION_REQUEST,
                {
                    "reason": reason,
                    "callback_event": callback_event,
                    "callback_data": callback_data,
                },
            )

"""
Microsoft 365 integration service for the Knowledge Mesh Desktop application.

This module provides a service for integrating with Microsoft 365 for document
handling and synchronization.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path

import aiohttp
import msal

from src.core.config import Config
from src.core.events import EventType, publish_event
from src.models.document import Document, DocumentType, DocumentStatus
from src.services.vault_integration import VaultIntegrationService


logger = logging.getLogger(__name__)


class Office365SyncStatus(Enum):
    """Enum for Office 365 sync status."""
    
    NOT_CONFIGURED = "not_configured"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"


class Office365IntegrationService:
    """Service for integrating with Microsoft 365."""
    
    def __init__(
        self,
        config: Config,
        vault_service: VaultIntegrationService,
    ):
        """Initialize the Office 365 integration service.
        
        Args:
            config: The application configuration
            vault_service: The vault integration service for secure storage
        """
        self.config = config
        self.vault_service = vault_service
        
        self.status = Office365SyncStatus.NOT_CONFIGURED
        self.status_message = "Microsoft 365 integration not configured"
        
        self.client_id = None
        self.tenant_id = None
        self.authority = None
        self.scopes = [
            "User.Read",
            "Files.ReadWrite.All",
            "Sites.ReadWrite.All",
            "offline_access",
        ]
        
        self.app = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires = None
        
        self.sync_interval = int(self.config.get("office365.sync_interval", 300))  # 5 minutes
        self.sync_task = None
        self.is_syncing = False
        
        self.watched_folders = set()
        self.synced_files = {}
        self.last_sync = None
    
    async def initialize(self):
        """Initialize the Office 365 integration service."""
        logger.info("Initializing Office 365 integration service")
        
        self.client_id = self.config.get("office365.client_id")
        self.tenant_id = self.config.get("office365.tenant_id")
        
        if not self.client_id or not self.tenant_id:
            try:
                credentials = await self.vault_service.get_secret("office365_credentials")
                if credentials:
                    self.client_id = credentials.get("client_id")
                    self.tenant_id = credentials.get("tenant_id")
                    
                    self.access_token = credentials.get("access_token")
                    self.refresh_token = credentials.get("refresh_token")
                    
                    expires_str = credentials.get("token_expires")
                    if expires_str:
                        self.token_expires = datetime.fromisoformat(expires_str)
            except Exception as e:
                logger.error(f"Error loading Office 365 credentials from vault: {e}")
        
        if not self.client_id or not self.tenant_id:
            self.status = Office365SyncStatus.NOT_CONFIGURED
            self.status_message = "Microsoft 365 integration not configured"
            return
        
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority,
        )
        
        watched_folders_str = self.config.get("office365.watched_folders", "")
        if watched_folders_str:
            self.watched_folders = set(watched_folders_str.split(","))
        
        synced_files_path = Path(self.config.get("app.data_dir", "./data")) / "office365_synced_files.json"
        if synced_files_path.exists():
            try:
                with open(synced_files_path, "r") as f:
                    self.synced_files = json.load(f)
            except Exception as e:
                logger.error(f"Error loading synced files: {e}")
        
        if self.access_token and self.token_expires and self.token_expires > datetime.utcnow():
            self.status = Office365SyncStatus.CONNECTED
            self.status_message = "Connected to Microsoft 365"
        elif self.refresh_token:
            await self._refresh_token()
        else:
            self.status = Office365SyncStatus.DISCONNECTED
            self.status_message = "Disconnected from Microsoft 365"
    
    async def start(self):
        """Start the Office 365 integration service."""
        logger.info("Starting Office 365 integration service")
        
        if self.status == Office365SyncStatus.NOT_CONFIGURED:
            logger.warning("Office 365 integration not configured, cannot start")
            return
        
        self.sync_task = asyncio.create_task(self._sync_loop())
        
        publish_event(
            EventType.OFFICE365_CONNECTED,
            {
                "status": self.status.value,
                "message": self.status_message,
            },
        )
    
    async def stop(self):
        """Stop the Office 365 integration service."""
        logger.info("Stopping Office 365 integration service")
        
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
            
            self.sync_task = None
        
        await self._save_synced_files()
    
    async def connect(self, client_id: str, tenant_id: str):
        """Connect to Microsoft 365.
        
        Args:
            client_id: The client ID for the Microsoft 365 application
            tenant_id: The tenant ID for the Microsoft 365 application
            
        Returns:
            A tuple of (success, auth_url) where success is a boolean indicating
            whether the connection was successful, and auth_url is the URL to
            redirect the user to for authentication if success is False.
        """
        logger.info("Connecting to Microsoft 365")
        
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        
        await self.vault_service.set_secret(
            "office365_credentials",
            {
                "client_id": self.client_id,
                "tenant_id": self.tenant_id,
            },
        )
        
        self.app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority,
        )
        
        auth_url = self.app.get_authorization_request_url(
            self.scopes,
            redirect_uri="http://localhost:8000/auth/callback",
            state="office365",
        )
        
        self.status = Office365SyncStatus.CONNECTING
        self.status_message = "Connecting to Microsoft 365"
        
        return False, auth_url
    
    async def handle_auth_callback(self, code: str):
        """Handle the authentication callback from Microsoft 365.
        
        Args:
            code: The authorization code from the callback
            
        Returns:
            A boolean indicating whether the authentication was successful
        """
        logger.info("Handling Microsoft 365 authentication callback")
        
        try:
            result = self.app.acquire_token_by_authorization_code(
                code,
                self.scopes,
                redirect_uri="http://localhost:8000/auth/callback",
            )
            
            if "access_token" not in result:
                logger.error(f"Error acquiring token: {result.get('error_description', 'Unknown error')}")
                self.status = Office365SyncStatus.ERROR
                self.status_message = f"Error connecting to Microsoft 365: {result.get('error_description', 'Unknown error')}"
                return False
            
            self.access_token = result["access_token"]
            self.refresh_token = result.get("refresh_token")
            self.token_expires = datetime.utcnow() + timedelta(seconds=result["expires_in"])
            
            await self.vault_service.set_secret(
                "office365_credentials",
                {
                    "client_id": self.client_id,
                    "tenant_id": self.tenant_id,
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "token_expires": self.token_expires.isoformat(),
                },
            )
            
            self.status = Office365SyncStatus.CONNECTED
            self.status_message = "Connected to Microsoft 365"
            
            if not self.sync_task:
                self.sync_task = asyncio.create_task(self._sync_loop())
            
            publish_event(
                EventType.OFFICE365_CONNECTED,
                {
                    "status": self.status.value,
                    "message": self.status_message,
                },
            )
            
            return True
        except Exception as e:
            logger.error(f"Error handling Microsoft 365 authentication callback: {e}")
            self.status = Office365SyncStatus.ERROR
            self.status_message = f"Error connecting to Microsoft 365: {str(e)}"
            return False
    
    async def disconnect(self):
        """Disconnect from Microsoft 365."""
        logger.info("Disconnecting from Microsoft 365")
        
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
            
            self.sync_task = None
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires = None
        
        await self.vault_service.set_secret(
            "office365_credentials",
            {
                "client_id": self.client_id,
                "tenant_id": self.tenant_id,
            },
        )
        
        self.status = Office365SyncStatus.DISCONNECTED
        self.status_message = "Disconnected from Microsoft 365"
        
        publish_event(
            EventType.OFFICE365_DISCONNECTED,
            {
                "status": self.status.value,
                "message": self.status_message,
            },
        )
    
    async def add_watched_folder(self, folder_id: str):
        """Add a folder to watch for changes.
        
        Args:
            folder_id: The ID of the folder to watch
            
        Returns:
            A boolean indicating whether the folder was added successfully
        """
        logger.info(f"Adding watched folder: {folder_id}")
        
        if self.status != Office365SyncStatus.CONNECTED:
            logger.warning("Not connected to Microsoft 365, cannot add watched folder")
            return False
        
        folder = await self._get_folder(folder_id)
        if not folder:
            logger.error(f"Folder not found: {folder_id}")
            return False
        
        self.watched_folders.add(folder_id)
        
        self.config.set(
            "office365.watched_folders",
            ",".join(self.watched_folders),
        )
        
        asyncio.create_task(self.sync())
        
        return True
    
    async def remove_watched_folder(self, folder_id: str):
        """Remove a folder from the watch list.
        
        Args:
            folder_id: The ID of the folder to remove
            
        Returns:
            A boolean indicating whether the folder was removed successfully
        """
        logger.info(f"Removing watched folder: {folder_id}")
        
        if folder_id not in self.watched_folders:
            logger.warning(f"Folder not in watch list: {folder_id}")
            return False
        
        self.watched_folders.remove(folder_id)
        
        self.config.set(
            "office365.watched_folders",
            ",".join(self.watched_folders),
        )
        
        return True
    
    async def get_watched_folders(self):
        """Get the list of watched folders.
        
        Returns:
            A list of folder information dictionaries
        """
        logger.info("Getting watched folders")
        
        if self.status != Office365SyncStatus.CONNECTED:
            logger.warning("Not connected to Microsoft 365, cannot get watched folders")
            return []
        
        folders = []
        for folder_id in self.watched_folders:
            folder = await self._get_folder(folder_id)
            if folder:
                folders.append(folder)
        
        return folders
    
    async def sync(self):
        """Sync documents from Microsoft 365."""
        logger.info("Syncing documents from Microsoft 365")
        
        if self.status != Office365SyncStatus.CONNECTED:
            logger.warning("Not connected to Microsoft 365, cannot sync")
            return
        
        if self.is_syncing:
            logger.warning("Already syncing, skipping")
            return
        
        self.is_syncing = True
        self.status = Office365SyncStatus.SYNCING
        self.status_message = "Syncing documents from Microsoft 365"
        
        try:
            if not self.access_token or not self.token_expires or self.token_expires <= datetime.utcnow():
                await self._refresh_token()
                
                if self.status != Office365SyncStatus.CONNECTED:
                    logger.error("Failed to refresh token, cannot sync")
                    return
            
            for folder_id in self.watched_folders:
                await self._sync_folder(folder_id)
            
            self.last_sync = datetime.utcnow()
            
            await self._save_synced_files()
            
            self.status = Office365SyncStatus.CONNECTED
            self.status_message = "Connected to Microsoft 365"
        except Exception as e:
            logger.error(f"Error syncing documents: {e}")
            self.status = Office365SyncStatus.ERROR
            self.status_message = f"Error syncing documents: {str(e)}"
        finally:
            self.is_syncing = False
    
    async def get_status(self):
        """Get the current status of the Office 365 integration.
        
        Returns:
            A dictionary with status information
        """
        return {
            "status": self.status.value,
            "message": self.status_message,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "watched_folders": len(self.watched_folders),
            "synced_files": len(self.synced_files),
        }
    
    async def _refresh_token(self):
        """Refresh the access token."""
        logger.info("Refreshing Microsoft 365 access token")
        
        if not self.app or not self.refresh_token:
            logger.error("Cannot refresh token, app or refresh token not available")
            self.status = Office365SyncStatus.DISCONNECTED
            self.status_message = "Disconnected from Microsoft 365"
            return
        
        try:
            result = self.app.acquire_token_by_refresh_token(
                self.refresh_token,
                self.scopes,
            )
            
            if "access_token" not in result:
                logger.error(f"Error refreshing token: {result.get('error_description', 'Unknown error')}")
                self.status = Office365SyncStatus.ERROR
                self.status_message = f"Error refreshing token: {result.get('error_description', 'Unknown error')}"
                return
            
            self.access_token = result["access_token"]
            self.refresh_token = result.get("refresh_token", self.refresh_token)
            self.token_expires = datetime.utcnow() + timedelta(seconds=result["expires_in"])
            
            await self.vault_service.set_secret(
                "office365_credentials",
                {
                    "client_id": self.client_id,
                    "tenant_id": self.tenant_id,
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "token_expires": self.token_expires.isoformat(),
                },
            )
            
            self.status = Office365SyncStatus.CONNECTED
            self.status_message = "Connected to Microsoft 365"
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            self.status = Office365SyncStatus.ERROR
            self.status_message = f"Error refreshing token: {str(e)}"
    
    async def _sync_loop(self):
        """Sync loop for periodically syncing documents."""
        logger.info("Starting Office 365 sync loop")
        
        while True:
            try:
                await self.sync()
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
            
            await asyncio.sleep(self.sync_interval)
    
    async def _sync_folder(self, folder_id: str):
        """Sync a folder from Microsoft 365.
        
        Args:
            folder_id: The ID of the folder to sync
        """
        logger.info(f"Syncing folder: {folder_id}")
        
        files = await self._get_folder_contents(folder_id)
        
        for file in files:
            file_id = file.get("id")
            if not file_id:
                continue
            
            if file.get("folder"):
                continue
            
            last_modified = file.get("lastModifiedDateTime")
            if not last_modified:
                continue
            
            last_modified = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
            
            if file_id in self.synced_files:
                synced_file = self.synced_files[file_id]
                synced_modified = datetime.fromisoformat(synced_file["lastModified"].replace("Z", "+00:00"))
                
                if last_modified <= synced_modified:
                    continue
            
            await self._process_file(file)
    
    async def _process_file(self, file: Dict[str, Any]):
        """Process a file from Microsoft 365.
        
        Args:
            file: The file information dictionary
        """
        file_id = file.get("id")
        file_name = file.get("name")
        
        logger.info(f"Processing file: {file_name} ({file_id})")
        
        content = await self._download_file(file_id)
        if not content:
            logger.error(f"Failed to download file: {file_name} ({file_id})")
            return
        
        file_path = Path(self.config.get("app.data_dir", "./data")) / "office365" / file_id
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        self.synced_files[file_id] = {
            "id": file_id,
            "name": file_name,
            "path": str(file_path),
            "lastModified": file.get("lastModifiedDateTime"),
            "size": file.get("size"),
            "webUrl": file.get("webUrl"),
        }
        
        publish_event(
            EventType.OFFICE365_DOCUMENT_SYNCED,
            {
                "id": file_id,
                "name": file_name,
                "path": str(file_path),
                "webUrl": file.get("webUrl"),
            },
        )
    
    async def _get_folder(self, folder_id: str):
        """Get information about a folder.
        
        Args:
            folder_id: The ID of the folder
            
        Returns:
            A dictionary with folder information, or None if the folder was not found
        """
        logger.info(f"Getting folder information: {folder_id}")
        
        if not self.access_token:
            logger.error("No access token available")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}"
                
                async with session.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Accept": "application/json",
                    },
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error getting folder: {response.status} {await response.text()}")
                        return None
                    
                    data = await response.json()
                    
                    return {
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "webUrl": data.get("webUrl"),
                    }
        except Exception as e:
            logger.error(f"Error getting folder: {e}")
            return None
    
    async def _get_folder_contents(self, folder_id: str):
        """Get the contents of a folder.
        
        Args:
            folder_id: The ID of the folder
            
        Returns:
            A list of file information dictionaries
        """
        logger.info(f"Getting folder contents: {folder_id}")
        
        if not self.access_token:
            logger.error("No access token available")
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children"
                
                async with session.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Accept": "application/json",
                    },
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error getting folder contents: {response.status} {await response.text()}")
                        return []
                    
                    data = await response.json()
                    
                    return data.get("value", [])
        except Exception as e:
            logger.error(f"Error getting folder contents: {e}")
            return []
    
    async def _download_file(self, file_id: str):
        """Download a file from Microsoft 365.
        
        Args:
            file_id: The ID of the file
            
        Returns:
            The file content as bytes, or None if the download failed
        """
        logger.info(f"Downloading file: {file_id}")
        
        if not self.access_token:
            logger.error("No access token available")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
                
                async with session.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error downloading file: {response.status} {await response.text()}")
                        return None
                    
                    return await response.read()
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    async def _save_synced_files(self):
        """Save the synced files to disk."""
        logger.info("Saving synced files")
        
        synced_files_path = Path(self.config.get("app.data_dir", "./data")) / "office365_synced_files.json"
        synced_files_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(synced_files_path, "w") as f:
                json.dump(self.synced_files, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving synced files: {e}")

"""
Collaboration Service for the Knowledge Mesh Desktop application.

This module provides services for collaborative knowledge sharing between users,
including managing collaboration spaces, user permissions, and document sharing.
"""

import asyncio
import logging
import os
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable
import uuid

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus
from ..models.collaboration import (
    CollaborationSpace, CollaborationUser, CollaborationActivity,
    CollaborationInvitation, CollaborationRole, CollaborationPermission,
    CollaborationStatus,
)

logger = logging.getLogger(__name__)


class CollaborationService:
    """
    Service for collaborative knowledge sharing.
    
    This service manages collaboration spaces, user permissions, and document
    sharing between users.
    """
    
    def __init__(self, config: Config, services: Optional[Dict[str, Any]] = None):
        """
        Initialize the collaboration service.
        
        Args:
            config: Application configuration
            services: Other services that this service depends on
        """
        self.config = config
        self.services = services or {}
        self.is_running = False
        self.data_dir = Path(self.config.get("app.data_dir", "."))
        self.spaces_dir = self.data_dir / "collaboration" / "spaces"
        self.invitations_dir = self.data_dir / "collaboration" / "invitations"
        self.spaces_dir.mkdir(parents=True, exist_ok=True)
        self.invitations_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_user_id = self.config.get("user.id", str(uuid.uuid4()))
        self.current_username = self.config.get("user.username", "User")
        self.current_email = self.config.get("user.email", "user@example.com")
        
        self.spaces_cache = {}
        self.invitations_cache = {}
        
        event_bus.subscribe(EventType.DOCUMENT_CREATED, self._on_document_created)
        event_bus.subscribe(EventType.DOCUMENT_UPDATED, self._on_document_updated)
        event_bus.subscribe(EventType.DOCUMENT_DELETED, self._on_document_deleted)
    
    async def initialize(self):
        """Initialize the collaboration service."""
        logger.info("Initializing collaboration service")
        
        self.spaces_dir.mkdir(parents=True, exist_ok=True)
        self.invitations_dir.mkdir(parents=True, exist_ok=True)
        
        self.document_processor_service = self.services.get("document_processor")
        self.knowledge_mesh_service = self.services.get("knowledge_mesh")
        self.vault_service = self.services.get("vault")
        
        await self._load_spaces()
        await self._load_invitations()
        
        logger.info("Collaboration service initialized")
    
    async def start(self):
        """Start the collaboration service."""
        logger.info("Starting collaboration service")
        self.is_running = True
        logger.info("Collaboration service started")
    
    async def stop(self):
        """Stop the collaboration service."""
        logger.info("Stopping collaboration service")
        self.is_running = False
        logger.info("Collaboration service stopped")
    
    async def _load_spaces(self):
        """Load collaboration spaces from disk."""
        logger.info("Loading collaboration spaces")
        
        try:
            for space_file in self.spaces_dir.glob("*.pkl"):
                try:
                    with open(space_file, "rb") as f:
                        space_dict = pickle.load(f)
                    
                    space = CollaborationSpace.from_dict(space_dict)
                    self.spaces_cache[space.id] = space
                    logger.debug(f"Loaded space: {space}")
                except Exception as e:
                    logger.error(f"Error loading space {space_file}: {e}", exc_info=True)
            
            logger.info(f"Loaded {len(self.spaces_cache)} collaboration spaces")
        except Exception as e:
            logger.error(f"Error loading spaces: {e}", exc_info=True)
    
    async def _load_invitations(self):
        """Load collaboration invitations from disk."""
        logger.info("Loading collaboration invitations")
        
        try:
            for invitation_file in self.invitations_dir.glob("*.pkl"):
                try:
                    with open(invitation_file, "rb") as f:
                        invitation_dict = pickle.load(f)
                    
                    invitation = CollaborationInvitation.from_dict(invitation_dict)
                    
                    if invitation.is_expired():
                        continue
                    
                    self.invitations_cache[invitation.id] = invitation
                    logger.debug(f"Loaded invitation: {invitation}")
                except Exception as e:
                    logger.error(f"Error loading invitation {invitation_file}: {e}", exc_info=True)
            
            logger.info(f"Loaded {len(self.invitations_cache)} collaboration invitations")
        except Exception as e:
            logger.error(f"Error loading invitations: {e}", exc_info=True)
    
    async def _save_space(self, space: CollaborationSpace) -> bool:
        """
        Save a collaboration space to disk.
        
        Args:
            space: The space to save
            
        Returns:
            True if the space was saved successfully, False otherwise
        """
        try:
            space_path = self.spaces_dir / f"{space.id}.pkl"
            
            if self.vault_service and hasattr(self.vault_service, "encrypt_data"):
                space_dict = space.to_dict()
                
                for user_id, user_data in space_dict["users"].items():
                    if "email" in user_data:
                        user_data["email"] = await self.vault_service.encrypt_data(user_data["email"])
                
                with open(space_path, "wb") as f:
                    pickle.dump(space_dict, f)
            else:
                with open(space_path, "wb") as f:
                    pickle.dump(space.to_dict(), f)
            
            self.spaces_cache[space.id] = space
            
            logger.info(f"Saved space: {space.id}")
            return True
        except Exception as e:
            logger.error(f"Error saving space: {e}", exc_info=True)
            return False
    
    async def _save_invitation(self, invitation: CollaborationInvitation) -> bool:
        """
        Save a collaboration invitation to disk.
        
        Args:
            invitation: The invitation to save
            
        Returns:
            True if the invitation was saved successfully, False otherwise
        """
        try:
            invitation_path = self.invitations_dir / f"{invitation.id}.pkl"
            
            if self.vault_service and hasattr(self.vault_service, "encrypt_data"):
                invitation_dict = invitation.to_dict()
                
                if "invitee_email" in invitation_dict:
                    invitation_dict["invitee_email"] = await self.vault_service.encrypt_data(
                        invitation_dict["invitee_email"]
                    )
                
                with open(invitation_path, "wb") as f:
                    pickle.dump(invitation_dict, f)
            else:
                with open(invitation_path, "wb") as f:
                    pickle.dump(invitation.to_dict(), f)
            
            self.invitations_cache[invitation.id] = invitation
            
            logger.info(f"Saved invitation: {invitation.id}")
            return True
        except Exception as e:
            logger.error(f"Error saving invitation: {e}", exc_info=True)
            return False
    
    async def create_space(
        self,
        name: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[CollaborationSpace]:
        """
        Create a new collaboration space.
        
        Args:
            name: The name of the space
            description: The description of the space
            metadata: Additional metadata for the space
            
        Returns:
            The created space, or None if creation failed
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return None
        
        try:
            space = CollaborationSpace.create(
                name=name,
                description=description,
                owner_id=self.current_user_id,
                owner_username=self.current_username,
                owner_email=self.current_email,
                metadata=metadata,
            )
            
            if await self._save_space(space):
                publish(
                    EventType.COLLABORATION_SPACE_CREATED,
                    {
                        "space_id": space.id,
                        "name": space.name,
                        "owner_id": space.owner_id,
                    },
                )
                
                logger.info(f"Created space: {space}")
                return space
            
            logger.warning(f"Failed to save space: {name}")
            return None
        except Exception as e:
            logger.error(f"Error creating space: {e}", exc_info=True)
            return None
    
    async def get_space(self, space_id: str) -> Optional[CollaborationSpace]:
        """
        Get a collaboration space by ID.
        
        Args:
            space_id: The ID of the space
            
        Returns:
            The space, or None if not found
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return None
        
        try:
            if space_id in self.spaces_cache:
                return self.spaces_cache[space_id]
            
            space_path = self.spaces_dir / f"{space_id}.pkl"
            
            if not space_path.exists():
                logger.warning(f"Space not found: {space_id}")
                return None
            
            with open(space_path, "rb") as f:
                space_dict = pickle.load(f)
            
            if self.vault_service and hasattr(self.vault_service, "decrypt_data"):
                for user_id, user_data in space_dict["users"].items():
                    if "email" in user_data:
                        try:
                            user_data["email"] = await self.vault_service.decrypt_data(user_data["email"])
                        except Exception as e:
                            logger.error(f"Error decrypting user email: {e}", exc_info=True)
            
            space = CollaborationSpace.from_dict(space_dict)
            
            self.spaces_cache[space.id] = space
            
            return space
        except Exception as e:
            logger.error(f"Error getting space: {e}", exc_info=True)
            return None
    
    async def update_space(
        self,
        space_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[CollaborationSpace]:
        """
        Update a collaboration space.
        
        Args:
            space_id: The ID of the space to update
            name: The new name of the space
            description: The new description of the space
            metadata: The new metadata for the space
            
        Returns:
            The updated space, or None if update failed
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return None
        
        try:
            space = await self.get_space(space_id)
            
            if not space:
                logger.warning(f"Space not found: {space_id}")
                return None
            
            current_user = space.get_user(self.current_user_id)
            
            if not current_user:
                logger.warning(f"Current user not in space: {space_id}")
                return None
            
            if (
                current_user.role != CollaborationRole.OWNER
                and current_user.role != CollaborationRole.ADMIN
            ):
                logger.warning(f"Current user does not have permission to update space: {space_id}")
                return None
            
            if name:
                space.name = name
            
            if description:
                space.description = description
            
            if metadata:
                space.metadata.update(metadata)
            
            space.updated_at = datetime.utcnow()
            
            space.add_activity(
                user_id=self.current_user_id,
                action="update_space",
                target_type="space",
                target_id=space.id,
                metadata={
                    "name": name,
                    "description": description,
                },
            )
            
            if await self._save_space(space):
                publish(
                    EventType.COLLABORATION_SPACE_UPDATED,
                    {
                        "space_id": space.id,
                        "name": space.name,
                        "owner_id": space.owner_id,
                    },
                )
                
                logger.info(f"Updated space: {space}")
                return space
            
            logger.warning(f"Failed to save space: {space_id}")
            return None
        except Exception as e:
            logger.error(f"Error updating space: {e}", exc_info=True)
            return None
    
    async def delete_space(self, space_id: str) -> bool:
        """
        Delete a collaboration space.
        
        Args:
            space_id: The ID of the space to delete
            
        Returns:
            True if the space was deleted, False otherwise
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return False
        
        try:
            space = await self.get_space(space_id)
            
            if not space:
                logger.warning(f"Space not found: {space_id}")
                return False
            
            if space.owner_id != self.current_user_id:
                logger.warning(f"Current user is not the owner of space: {space_id}")
                return False
            
            space_path = self.spaces_dir / f"{space_id}.pkl"
            
            if space_path.exists():
                space_path.unlink()
            
            if space_id in self.spaces_cache:
                del self.spaces_cache[space_id]
            
            publish(
                EventType.COLLABORATION_SPACE_DELETED,
                {
                    "space_id": space_id,
                    "name": space.name,
                    "owner_id": space.owner_id,
                },
            )
            
            logger.info(f"Deleted space: {space_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting space: {e}", exc_info=True)
            return False
    
    async def get_spaces(
        self,
        owner_id: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[CollaborationSpace]:
        """
        Get collaboration spaces.
        
        Args:
            owner_id: Filter by owner ID
            include_archived: Whether to include archived spaces
            
        Returns:
            A list of spaces
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return []
        
        try:
            spaces = []
            
            if len(self.spaces_cache) == 0:
                await self._load_spaces()
            
            for space in self.spaces_cache.values():
                if not include_archived and space.status == CollaborationStatus.ARCHIVED:
                    continue
                
                if owner_id and space.owner_id != owner_id:
                    continue
                
                spaces.append(space)
            
            return spaces
        except Exception as e:
            logger.error(f"Error getting spaces: {e}", exc_info=True)
            return []
    
    async def get_user_spaces(
        self,
        user_id: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[CollaborationSpace]:
        """
        Get spaces that a user is a member of.
        
        Args:
            user_id: The ID of the user (defaults to current user)
            include_archived: Whether to include archived spaces
            
        Returns:
            A list of spaces
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return []
        
        try:
            user_id = user_id or self.current_user_id
            spaces = []
            
            if len(self.spaces_cache) == 0:
                await self._load_spaces()
            
            for space in self.spaces_cache.values():
                if not include_archived and space.status == CollaborationStatus.ARCHIVED:
                    continue
                
                if user_id in space.users:
                    spaces.append(space)
            
            return spaces
        except Exception as e:
            logger.error(f"Error getting user spaces: {e}", exc_info=True)
            return []
    
    async def add_user_to_space(
        self,
        space_id: str,
        user_id: str,
        username: str,
        email: str,
        role: CollaborationRole,
        permissions: Optional[Set[CollaborationPermission]] = None,
    ) -> Optional[CollaborationUser]:
        """
        Add a user to a collaboration space.
        
        Args:
            space_id: The ID of the space
            user_id: The ID of the user to add
            username: The username of the user
            email: The email of the user
            role: The role of the user
            permissions: The permissions of the user
            
        Returns:
            The added user, or None if addition failed
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return None
        
        try:
            space = await self.get_space(space_id)
            
            if not space:
                logger.warning(f"Space not found: {space_id}")
                return None
            
            current_user = space.get_user(self.current_user_id)
            
            if not current_user:
                logger.warning(f"Current user not in space: {space_id}")
                return None
            
            if not current_user.has_permission(CollaborationPermission.MANAGE_USERS):
                logger.warning(f"Current user does not have permission to add users to space: {space_id}")
                return None
            
            user = space.add_user(
                user_id=user_id,
                username=username,
                email=email,
                role=role,
                permissions=permissions,
                added_by=self.current_user_id,
            )
            
            if await self._save_space(space):
                publish(
                    EventType.COLLABORATION_USER_ADDED,
                    {
                        "space_id": space.id,
                        "user_id": user.id,
                        "username": user.username,
                        "role": user.role.name,
                    },
                )
                
                logger.info(f"Added user to space: {user}")
                return user
            
            logger.warning(f"Failed to save space after adding user: {space_id}")
            return None
        except Exception as e:
            logger.error(f"Error adding user to space: {e}", exc_info=True)
            return None
    
    async def remove_user_from_space(self, space_id: str, user_id: str) -> bool:
        """
        Remove a user from a collaboration space.
        
        Args:
            space_id: The ID of the space
            user_id: The ID of the user to remove
            
        Returns:
            True if the user was removed, False otherwise
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return False
        
        try:
            space = await self.get_space(space_id)
            
            if not space:
                logger.warning(f"Space not found: {space_id}")
                return False
            
            current_user = space.get_user(self.current_user_id)
            
            if not current_user:
                logger.warning(f"Current user not in space: {space_id}")
                return False
            
            if not current_user.has_permission(CollaborationPermission.MANAGE_USERS):
                logger.warning(f"Current user does not have permission to remove users from space: {space_id}")
                return False
            
            if space.remove_user(user_id, removed_by=self.current_user_id):
                if await self._save_space(space):
                    publish(
                        EventType.COLLABORATION_USER_REMOVED,
                        {
                            "space_id": space.id,
                            "user_id": user_id,
                        },
                    )
                    
                    logger.info(f"Removed user from space: {user_id}")
                    return True
                
                logger.warning(f"Failed to save space after removing user: {space_id}")
                return False
            
            logger.warning(f"Failed to remove user from space: {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error removing user from space: {e}", exc_info=True)
            return False
    
    async def update_user_role(
        self,
        space_id: str,
        user_id: str,
        role: CollaborationRole,
        permissions: Optional[Set[CollaborationPermission]] = None,
    ) -> bool:
        """
        Update a user's role in a collaboration space.
        
        Args:
            space_id: The ID of the space
            user_id: The ID of the user to update
            role: The new role of the user
            permissions: The new permissions of the user
            
        Returns:
            True if the user was updated, False otherwise
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return False
        
        try:
            space = await self.get_space(space_id)
            
            if not space:
                logger.warning(f"Space not found: {space_id}")
                return False
            
            current_user = space.get_user(self.current_user_id)
            
            if not current_user:
                logger.warning(f"Current user not in space: {space_id}")
                return False
            
            if not current_user.has_permission(CollaborationPermission.MANAGE_PERMISSIONS):
                logger.warning(f"Current user does not have permission to update user roles in space: {space_id}")
                return False
            
            if space.update_user_role(
                user_id=user_id,
                role=role,
                permissions=permissions,
                updated_by=self.current_user_id,
            ):
                if await self._save_space(space):
                    publish(
                        EventType.COLLABORATION_USER_UPDATED,
                        {
                            "space_id": space.id,
                            "user_id": user_id,
                            "role": role.name,
                        },
                    )
                    
                    logger.info(f"Updated user role in space: {user_id}")
                    return True
                
                logger.warning(f"Failed to save space after updating user role: {space_id}")
                return False
            
            logger.warning(f"Failed to update user role in space: {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating user role in space: {e}", exc_info=True)
            return False
    
    async def add_document_to_space(self, space_id: str, document_id: str) -> bool:
        """
        Add a document to a collaboration space.
        
        Args:
            space_id: The ID of the space
            document_id: The ID of the document to add
            
        Returns:
            True if the document was added, False otherwise
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return False
        
        try:
            space = await self.get_space(space_id)
            
            if not space:
                logger.warning(f"Space not found: {space_id}")
                return False
            
            current_user = space.get_user(self.current_user_id)
            
            if not current_user:
                logger.warning(f"Current user not in space: {space_id}")
                return False
            
            if not current_user.has_permission(CollaborationPermission.CREATE_CONTENT):
                logger.warning(f"Current user does not have permission to add documents to space: {space_id}")
                return False
            
            if self.document_processor_service:
                document = await self.document_processor_service.get_document(document_id)
                
                if not document:
                    logger.warning(f"Document not found: {document_id}")
                    return False
            
            if space.add_document(document_id, added_by=self.current_user_id):
                if await self._save_space(space):
                    publish(
                        EventType.COLLABORATION_DOCUMENT_ADDED,
                        {
                            "space_id": space.id,
                            "document_id": document_id,
                        },
                    )
                    
                    logger.info(f"Added document to space: {document_id}")
                    return True
                
                logger.warning(f"Failed to save space after adding document: {space_id}")
                return False
            
            logger.warning(f"Failed to add document to space: {document_id}")
            return False
        except Exception as e:
            logger.error(f"Error adding document to space: {e}", exc_info=True)
            return False
    
    async def remove_document_from_space(self, space_id: str, document_id: str) -> bool:
        """
        Remove a document from a collaboration space.
        
        Args:
            space_id: The ID of the space
            document_id: The ID of the document to remove
            
        Returns:
            True if the document was removed, False otherwise
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return False
        
        try:
            space = await self.get_space(space_id)
            
            if not space:
                logger.warning(f"Space not found: {space_id}")
                return False
            
            current_user = space.get_user(self.current_user_id)
            
            if not current_user:
                logger.warning(f"Current user not in space: {space_id}")
                return False
            
            if not current_user.has_permission(CollaborationPermission.DELETE_CONTENT):
                logger.warning(f"Current user does not have permission to remove documents from space: {space_id}")
                return False
            
            if space.remove_document(document_id, removed_by=self.current_user_id):
                if await self._save_space(space):
                    publish(
                        EventType.COLLABORATION_DOCUMENT_REMOVED,
                        {
                            "space_id": space.id,
                            "document_id": document_id,
                        },
                    )
                    
                    logger.info(f"Removed document from space: {document_id}")
                    return True
                
                logger.warning(f"Failed to save space after removing document: {space_id}")
                return False
            
            logger.warning(f"Failed to remove document from space: {document_id}")
            return False
        except Exception as e:
            logger.error(f"Error removing document from space: {e}", exc_info=True)
            return False
    
    async def get_space_documents(self, space_id: str) -> List[str]:
        """
        Get the documents in a collaboration space.
        
        Args:
            space_id: The ID of the space
            
        Returns:
            A list of document IDs
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return []
        
        try:
            space = await self.get_space(space_id)
            
            if not space:
                logger.warning(f"Space not found: {space_id}")
                return []
            
            current_user = space.get_user(self.current_user_id)
            
            if not current_user:
                logger.warning(f"Current user not in space: {space_id}")
                return []
            
            if not current_user.has_permission(CollaborationPermission.VIEW_CONTENT):
                logger.warning(f"Current user does not have permission to view documents in space: {space_id}")
                return []
            
            return space.documents
        except Exception as e:
            logger.error(f"Error getting space documents: {e}", exc_info=True)
            return []
    
    async def create_invitation(
        self,
        space_id: str,
        invitee_email: str,
        role: CollaborationRole,
        expires_in_days: Optional[int] = 7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[CollaborationInvitation]:
        """
        Create an invitation to a collaboration space.
        
        Args:
            space_id: The ID of the space
            invitee_email: The email of the user to invite
            role: The role the invitee will have
            expires_in_days: Number of days until the invitation expires
            metadata: Additional metadata for the invitation
            
        Returns:
            The created invitation, or None if creation failed
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return None
        
        try:
            space = await self.get_space(space_id)
            
            if not space:
                logger.warning(f"Space not found: {space_id}")
                return None
            
            current_user = space.get_user(self.current_user_id)
            
            if not current_user:
                logger.warning(f"Current user not in space: {space_id}")
                return None
            
            if not current_user.has_permission(CollaborationPermission.INVITE_USERS):
                logger.warning(f"Current user does not have permission to invite users to space: {space_id}")
                return None
            
            invitation = CollaborationInvitation.create(
                space_id=space_id,
                inviter_id=self.current_user_id,
                invitee_email=invitee_email,
                role=role,
                expires_in_days=expires_in_days,
                metadata=metadata,
            )
            
            if await self._save_invitation(invitation):
                space.add_activity(
                    user_id=self.current_user_id,
                    action="create_invitation",
                    target_type="invitation",
                    target_id=invitation.id,
                    metadata={
                        "invitee_email": invitee_email,
                        "role": role.name,
                    },
                )
                
                await self._save_space(space)
                
                publish(
                    EventType.COLLABORATION_INVITATION_CREATED,
                    {
                        "invitation_id": invitation.id,
                        "space_id": space_id,
                        "invitee_email": invitee_email,
                    },
                )
                
                logger.info(f"Created invitation: {invitation}")
                return invitation
            
            logger.warning(f"Failed to save invitation: {invitee_email}")
            return None
        except Exception as e:
            logger.error(f"Error creating invitation: {e}", exc_info=True)
            return None
    
    async def get_invitation(self, invitation_id: str) -> Optional[CollaborationInvitation]:
        """
        Get a collaboration invitation by ID.
        
        Args:
            invitation_id: The ID of the invitation
            
        Returns:
            The invitation, or None if not found
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return None
        
        try:
            if invitation_id in self.invitations_cache:
                invitation = self.invitations_cache[invitation_id]
                
                if invitation.is_expired():
                    del self.invitations_cache[invitation_id]
                    return None
                
                return invitation
            
            invitation_path = self.invitations_dir / f"{invitation_id}.pkl"
            
            if not invitation_path.exists():
                logger.warning(f"Invitation not found: {invitation_id}")
                return None
            
            with open(invitation_path, "rb") as f:
                invitation_dict = pickle.load(f)
            
            if self.vault_service and hasattr(self.vault_service, "decrypt_data"):
                if "invitee_email" in invitation_dict:
                    try:
                        invitation_dict["invitee_email"] = await self.vault_service.decrypt_data(
                            invitation_dict["invitee_email"]
                        )
                    except Exception as e:
                        logger.error(f"Error decrypting invitee email: {e}", exc_info=True)
            
            invitation = CollaborationInvitation.from_dict(invitation_dict)
            
            if invitation.is_expired():
                return None
            
            self.invitations_cache[invitation.id] = invitation
            
            return invitation
        except Exception as e:
            logger.error(f"Error getting invitation: {e}", exc_info=True)
            return None
    
    async def accept_invitation(self, invitation_id: str) -> Optional[CollaborationSpace]:
        """
        Accept a collaboration invitation.
        
        Args:
            invitation_id: The ID of the invitation
            
        Returns:
            The space the invitation was for, or None if acceptance failed
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return None
        
        try:
            invitation = await self.get_invitation(invitation_id)
            
            if not invitation:
                logger.warning(f"Invitation not found: {invitation_id}")
                return None
            
            if invitation.invitee_email != self.current_email:
                logger.warning(f"Invitation is not for the current user: {invitation_id}")
                return None
            
            if not invitation.accept():
                logger.warning(f"Failed to accept invitation: {invitation_id}")
                return None
            
            await self._save_invitation(invitation)
            
            space = await self.get_space(invitation.space_id)
            
            if not space:
                logger.warning(f"Space not found: {invitation.space_id}")
                return None
            
            user = space.add_user(
                user_id=self.current_user_id,
                username=self.current_username,
                email=self.current_email,
                role=invitation.role,
                added_by=invitation.inviter_id,
            )
            
            if await self._save_space(space):
                publish(
                    EventType.COLLABORATION_INVITATION_ACCEPTED,
                    {
                        "invitation_id": invitation.id,
                        "space_id": space.id,
                        "user_id": self.current_user_id,
                    },
                )
                
                logger.info(f"Accepted invitation: {invitation}")
                return space
            
            logger.warning(f"Failed to save space after accepting invitation: {invitation_id}")
            return None
        except Exception as e:
            logger.error(f"Error accepting invitation: {e}", exc_info=True)
            return None
    
    async def decline_invitation(self, invitation_id: str) -> bool:
        """
        Decline a collaboration invitation.
        
        Args:
            invitation_id: The ID of the invitation
            
        Returns:
            True if the invitation was declined, False otherwise
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return False
        
        try:
            invitation = await self.get_invitation(invitation_id)
            
            if not invitation:
                logger.warning(f"Invitation not found: {invitation_id}")
                return False
            
            if invitation.invitee_email != self.current_email:
                logger.warning(f"Invitation is not for the current user: {invitation_id}")
                return False
            
            if not invitation.decline():
                logger.warning(f"Failed to decline invitation: {invitation_id}")
                return False
            
            await self._save_invitation(invitation)
            
            publish(
                EventType.COLLABORATION_INVITATION_DECLINED,
                {
                    "invitation_id": invitation.id,
                    "space_id": invitation.space_id,
                    "user_id": self.current_user_id,
                },
            )
            
            logger.info(f"Declined invitation: {invitation}")
            return True
        except Exception as e:
            logger.error(f"Error declining invitation: {e}", exc_info=True)
            return False
    
    async def get_invitations(
        self,
        space_id: Optional[str] = None,
        invitee_email: Optional[str] = None,
    ) -> List[CollaborationInvitation]:
        """
        Get collaboration invitations.
        
        Args:
            space_id: Filter by space ID
            invitee_email: Filter by invitee email
            
        Returns:
            A list of invitations
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return []
        
        try:
            invitations = []
            
            if len(self.invitations_cache) == 0:
                await self._load_invitations()
            
            for invitation in self.invitations_cache.values():
                if invitation.is_expired():
                    continue
                
                if space_id and invitation.space_id != space_id:
                    continue
                
                if invitee_email and invitation.invitee_email != invitee_email:
                    continue
                
                invitations.append(invitation)
            
            return invitations
        except Exception as e:
            logger.error(f"Error getting invitations: {e}", exc_info=True)
            return []
    
    async def get_user_invitations(self) -> List[CollaborationInvitation]:
        """
        Get invitations for the current user.
        
        Returns:
            A list of invitations
        """
        return await self.get_invitations(invitee_email=self.current_email)
    
    async def get_space_activities(
        self,
        space_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[CollaborationActivity]:
        """
        Get activities in a collaboration space.
        
        Args:
            space_id: The ID of the space
            user_id: Filter by user ID
            action: Filter by action
            target_type: Filter by target type
            target_id: Filter by target ID
            limit: Maximum number of activities to return
            
        Returns:
            A list of activities
        """
        if not self.is_running:
            logger.warning("Collaboration service is not running")
            return []
        
        try:
            space = await self.get_space(space_id)
            
            if not space:
                logger.warning(f"Space not found: {space_id}")
                return []
            
            current_user = space.get_user(self.current_user_id)
            
            if not current_user:
                logger.warning(f"Current user not in space: {space_id}")
                return []
            
            return space.get_activities(
                user_id=user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Error getting space activities: {e}", exc_info=True)
            return []
    
    def _on_document_created(self, event):
        """
        Handle document created events.
        
        Args:
            event: The document created event
        """
        if not self.is_running:
            return
        
        document_id = event.data.get("document_id")
        if not document_id:
            return
        
        asyncio.create_task(self._handle_document_event(document_id, "created"))
    
    def _on_document_updated(self, event):
        """
        Handle document updated events.
        
        Args:
            event: The document updated event
        """
        if not self.is_running:
            return
        
        document_id = event.data.get("document_id")
        if not document_id:
            return
        
        asyncio.create_task(self._handle_document_event(document_id, "updated"))
    
    def _on_document_deleted(self, event):
        """
        Handle document deleted events.
        
        Args:
            event: The document deleted event
        """
        if not self.is_running:
            return
        
        document_id = event.data.get("document_id")
        if not document_id:
            return
        
        asyncio.create_task(self._handle_document_event(document_id, "deleted"))
    
    async def _handle_document_event(self, document_id: str, event_type: str):
        """
        Handle a document event.
        
        Args:
            document_id: The ID of the document
            event_type: The type of event ("created", "updated", "deleted")
        """
        try:
            spaces = []
            
            for space in self.spaces_cache.values():
                if document_id in space.documents:
                    spaces.append(space)
            
            for space in spaces:
                if event_type == "created":
                    space.add_activity(
                        user_id=self.current_user_id,
                        action="create_document",
                        target_type="document",
                        target_id=document_id,
                    )
                elif event_type == "updated":
                    space.add_activity(
                        user_id=self.current_user_id,
                        action="update_document",
                        target_type="document",
                        target_id=document_id,
                    )
                elif event_type == "deleted":
                    space.remove_document(document_id, removed_by=self.current_user_id)
                
                await self._save_space(space)
        except Exception as e:
            logger.error(f"Error handling document event: {e}", exc_info=True)

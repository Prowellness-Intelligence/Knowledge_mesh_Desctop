"""
Collaboration models for the Knowledge Mesh Desktop application.

This module defines models for collaborative knowledge sharing between users,
including shared documents, collaboration spaces, and user permissions.
"""

import os
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import uuid


class CollaborationRole(Enum):
    """Enum defining the roles in a collaboration."""
    
    OWNER = auto()       # Owner of the collaboration, has full control
    ADMIN = auto()       # Administrator, can manage users and content
    EDITOR = auto()      # Can edit content
    VIEWER = auto()      # Can only view content
    GUEST = auto()       # Limited access, typically temporary


class CollaborationPermission(Enum):
    """Enum defining the permissions in a collaboration."""
    
    MANAGE_USERS = auto()        # Can add/remove users
    MANAGE_PERMISSIONS = auto()  # Can change user permissions
    CREATE_CONTENT = auto()      # Can create new content
    EDIT_CONTENT = auto()        # Can edit existing content
    DELETE_CONTENT = auto()      # Can delete content
    VIEW_CONTENT = auto()        # Can view content
    SHARE_CONTENT = auto()       # Can share content with others
    EXPORT_CONTENT = auto()      # Can export content
    INVITE_USERS = auto()        # Can invite new users


class CollaborationStatus(Enum):
    """Enum defining the status of a collaboration."""
    
    ACTIVE = auto()      # Active collaboration
    ARCHIVED = auto()    # Archived collaboration
    DELETED = auto()     # Deleted collaboration
    PENDING = auto()     # Pending invitation or request


class CollaborationUser:
    """
    Represents a user in a collaboration.
    
    This class stores information about a user's role and permissions
    within a collaboration.
    """
    
    def __init__(
        self,
        id: str,
        username: str,
        email: str,
        role: CollaborationRole,
        permissions: Optional[Set[CollaborationPermission]] = None,
        joined_at: Optional[datetime] = None,
        last_active_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a collaboration user.
        
        Args:
            id: The unique identifier for the user
            username: The username of the user
            email: The email address of the user
            role: The role of the user in the collaboration
            permissions: The specific permissions of the user
            joined_at: When the user joined the collaboration
            last_active_at: When the user was last active
            metadata: Additional metadata for the user
        """
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.permissions = permissions or self._default_permissions_for_role(role)
        self.joined_at = joined_at or datetime.utcnow()
        self.last_active_at = last_active_at or datetime.utcnow()
        self.metadata = metadata or {}
    
    def _default_permissions_for_role(self, role: CollaborationRole) -> Set[CollaborationPermission]:
        """
        Get the default permissions for a role.
        
        Args:
            role: The role to get permissions for
            
        Returns:
            A set of permissions
        """
        if role == CollaborationRole.OWNER:
            return set(CollaborationPermission)
        elif role == CollaborationRole.ADMIN:
            return {
                CollaborationPermission.MANAGE_USERS,
                CollaborationPermission.MANAGE_PERMISSIONS,
                CollaborationPermission.CREATE_CONTENT,
                CollaborationPermission.EDIT_CONTENT,
                CollaborationPermission.DELETE_CONTENT,
                CollaborationPermission.VIEW_CONTENT,
                CollaborationPermission.SHARE_CONTENT,
                CollaborationPermission.EXPORT_CONTENT,
                CollaborationPermission.INVITE_USERS,
            }
        elif role == CollaborationRole.EDITOR:
            return {
                CollaborationPermission.CREATE_CONTENT,
                CollaborationPermission.EDIT_CONTENT,
                CollaborationPermission.VIEW_CONTENT,
                CollaborationPermission.SHARE_CONTENT,
                CollaborationPermission.EXPORT_CONTENT,
            }
        elif role == CollaborationRole.VIEWER:
            return {
                CollaborationPermission.VIEW_CONTENT,
                CollaborationPermission.EXPORT_CONTENT,
            }
        elif role == CollaborationRole.GUEST:
            return {
                CollaborationPermission.VIEW_CONTENT,
            }
        else:
            return set()
    
    def has_permission(self, permission: CollaborationPermission) -> bool:
        """
        Check if the user has a specific permission.
        
        Args:
            permission: The permission to check
            
        Returns:
            True if the user has the permission, False otherwise
        """
        return permission in self.permissions
    
    def update_last_active(self):
        """Update the last active timestamp."""
        self.last_active_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the user to a dictionary.
        
        Returns:
            A dictionary representation of the user
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.name,
            "permissions": [p.name for p in self.permissions],
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationUser":
        """
        Create a user from a dictionary.
        
        Args:
            data: The dictionary representation of the user
            
        Returns:
            A CollaborationUser object
        """
        role = CollaborationRole.VIEWER
        if data.get("role"):
            try:
                role = CollaborationRole[data["role"]]
            except KeyError:
                role = CollaborationRole.VIEWER
        
        permissions = set()
        if data.get("permissions"):
            for p in data["permissions"]:
                try:
                    permissions.add(CollaborationPermission[p])
                except KeyError:
                    pass
        
        joined_at = None
        if data.get("joined_at"):
            try:
                joined_at = datetime.fromisoformat(data["joined_at"])
            except ValueError:
                joined_at = datetime.utcnow()
        
        last_active_at = None
        if data.get("last_active_at"):
            try:
                last_active_at = datetime.fromisoformat(data["last_active_at"])
            except ValueError:
                last_active_at = datetime.utcnow()
        
        return cls(
            id=data.get("id", ""),
            username=data.get("username", ""),
            email=data.get("email", ""),
            role=role,
            permissions=permissions,
            joined_at=joined_at,
            last_active_at=last_active_at,
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the user."""
        return (
            f"CollaborationUser(id={self.id}, username={self.username}, "
            f"role={self.role.name})"
        )
    
    def __repr__(self) -> str:
        """Get a string representation of the user."""
        return self.__str__()


class CollaborationActivity:
    """
    Represents an activity in a collaboration.
    
    This class stores information about an activity performed by a user
    within a collaboration.
    """
    
    def __init__(
        self,
        id: str,
        user_id: str,
        action: str,
        target_type: str,
        target_id: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a collaboration activity.
        
        Args:
            id: The unique identifier for the activity
            user_id: The ID of the user who performed the activity
            action: The action performed (e.g., "create", "edit", "delete")
            target_type: The type of the target (e.g., "document", "space")
            target_id: The ID of the target
            timestamp: When the activity occurred
            metadata: Additional metadata for the activity
        """
        self.id = id
        self.user_id = user_id
        self.action = action
        self.target_type = target_type
        self.target_id = target_id
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}
    
    @classmethod
    def create(
        cls,
        user_id: str,
        action: str,
        target_type: str,
        target_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "CollaborationActivity":
        """
        Create a new activity.
        
        Args:
            user_id: The ID of the user who performed the activity
            action: The action performed (e.g., "create", "edit", "delete")
            target_type: The type of the target (e.g., "document", "space")
            target_id: The ID of the target
            metadata: Additional metadata for the activity
            
        Returns:
            A CollaborationActivity object
        """
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the activity to a dictionary.
        
        Returns:
            A dictionary representation of the activity
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationActivity":
        """
        Create an activity from a dictionary.
        
        Args:
            data: The dictionary representation of the activity
            
        Returns:
            A CollaborationActivity object
        """
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except ValueError:
                timestamp = datetime.utcnow()
        
        return cls(
            id=data.get("id", ""),
            user_id=data.get("user_id", ""),
            action=data.get("action", ""),
            target_type=data.get("target_type", ""),
            target_id=data.get("target_id", ""),
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the activity."""
        return (
            f"CollaborationActivity(id={self.id}, user_id={self.user_id}, "
            f"action={self.action}, target_type={self.target_type}, "
            f"target_id={self.target_id})"
        )
    
    def __repr__(self) -> str:
        """Get a string representation of the activity."""
        return self.__str__()


class CollaborationSpace:
    """
    Represents a collaboration space.
    
    A collaboration space is a shared workspace where users can collaborate
    on documents and other content.
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        owner_id: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        status: CollaborationStatus = CollaborationStatus.ACTIVE,
        users: Optional[Dict[str, CollaborationUser]] = None,
        documents: Optional[List[str]] = None,
        activities: Optional[List[CollaborationActivity]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a collaboration space.
        
        Args:
            id: The unique identifier for the space
            name: The name of the space
            description: The description of the space
            owner_id: The ID of the owner of the space
            created_at: When the space was created
            updated_at: When the space was last updated
            status: The status of the space
            users: The users in the space
            documents: The documents in the space
            activities: The activities in the space
            metadata: Additional metadata for the space
        """
        self.id = id
        self.name = name
        self.description = description
        self.owner_id = owner_id
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.status = status
        self.users = users or {}
        self.documents = documents or []
        self.activities = activities or []
        self.metadata = metadata or {}
    
    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        owner_id: str,
        owner_username: str,
        owner_email: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "CollaborationSpace":
        """
        Create a new collaboration space.
        
        Args:
            name: The name of the space
            description: The description of the space
            owner_id: The ID of the owner of the space
            owner_username: The username of the owner
            owner_email: The email of the owner
            metadata: Additional metadata for the space
            
        Returns:
            A CollaborationSpace object
        """
        space_id = str(uuid.uuid4())
        
        owner = CollaborationUser(
            id=owner_id,
            username=owner_username,
            email=owner_email,
            role=CollaborationRole.OWNER,
        )
        
        space = cls(
            id=space_id,
            name=name,
            description=description,
            owner_id=owner_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status=CollaborationStatus.ACTIVE,
            users={owner_id: owner},
            documents=[],
            activities=[],
            metadata=metadata or {},
        )
        
        space.add_activity(
            user_id=owner_id,
            action="create",
            target_type="space",
            target_id=space_id,
        )
        
        return space
    
    def add_user(
        self,
        user_id: str,
        username: str,
        email: str,
        role: CollaborationRole,
        permissions: Optional[Set[CollaborationPermission]] = None,
        added_by: Optional[str] = None,
    ) -> CollaborationUser:
        """
        Add a user to the space.
        
        Args:
            user_id: The ID of the user
            username: The username of the user
            email: The email of the user
            role: The role of the user
            permissions: The permissions of the user
            added_by: The ID of the user who added this user
            
        Returns:
            The added user
        """
        user = CollaborationUser(
            id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=permissions,
        )
        
        self.users[user_id] = user
        
        if added_by:
            self.add_activity(
                user_id=added_by,
                action="add_user",
                target_type="user",
                target_id=user_id,
                metadata={"role": role.name},
            )
        
        self.updated_at = datetime.utcnow()
        
        return user
    
    def remove_user(self, user_id: str, removed_by: Optional[str] = None) -> bool:
        """
        Remove a user from the space.
        
        Args:
            user_id: The ID of the user to remove
            removed_by: The ID of the user who removed this user
            
        Returns:
            True if the user was removed, False otherwise
        """
        if user_id not in self.users:
            return False
        
        if user_id == self.owner_id:
            return False
        
        user = self.users.pop(user_id)
        
        if removed_by:
            self.add_activity(
                user_id=removed_by,
                action="remove_user",
                target_type="user",
                target_id=user_id,
                metadata={"role": user.role.name},
            )
        
        self.updated_at = datetime.utcnow()
        
        return True
    
    def update_user_role(
        self,
        user_id: str,
        role: CollaborationRole,
        permissions: Optional[Set[CollaborationPermission]] = None,
        updated_by: Optional[str] = None,
    ) -> bool:
        """
        Update a user's role in the space.
        
        Args:
            user_id: The ID of the user to update
            role: The new role of the user
            permissions: The new permissions of the user
            updated_by: The ID of the user who updated this user
            
        Returns:
            True if the user was updated, False otherwise
        """
        if user_id not in self.users:
            return False
        
        if user_id == self.owner_id and role != CollaborationRole.OWNER:
            return False
        
        user = self.users[user_id]
        old_role = user.role
        user.role = role
        
        if permissions is not None:
            user.permissions = permissions
        else:
            user.permissions = user._default_permissions_for_role(role)
        
        if updated_by:
            self.add_activity(
                user_id=updated_by,
                action="update_user_role",
                target_type="user",
                target_id=user_id,
                metadata={
                    "old_role": old_role.name,
                    "new_role": role.name,
                },
            )
        
        self.updated_at = datetime.utcnow()
        
        return True
    
    def add_document(self, document_id: str, added_by: Optional[str] = None) -> bool:
        """
        Add a document to the space.
        
        Args:
            document_id: The ID of the document to add
            added_by: The ID of the user who added the document
            
        Returns:
            True if the document was added, False otherwise
        """
        if document_id in self.documents:
            return False
        
        self.documents.append(document_id)
        
        if added_by:
            self.add_activity(
                user_id=added_by,
                action="add_document",
                target_type="document",
                target_id=document_id,
            )
        
        self.updated_at = datetime.utcnow()
        
        return True
    
    def remove_document(self, document_id: str, removed_by: Optional[str] = None) -> bool:
        """
        Remove a document from the space.
        
        Args:
            document_id: The ID of the document to remove
            removed_by: The ID of the user who removed the document
            
        Returns:
            True if the document was removed, False otherwise
        """
        if document_id not in self.documents:
            return False
        
        self.documents.remove(document_id)
        
        if removed_by:
            self.add_activity(
                user_id=removed_by,
                action="remove_document",
                target_type="document",
                target_id=document_id,
            )
        
        self.updated_at = datetime.utcnow()
        
        return True
    
    def add_activity(
        self,
        user_id: str,
        action: str,
        target_type: str,
        target_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CollaborationActivity:
        """
        Add an activity to the space.
        
        Args:
            user_id: The ID of the user who performed the activity
            action: The action performed
            target_type: The type of the target
            target_id: The ID of the target
            metadata: Additional metadata for the activity
            
        Returns:
            The added activity
        """
        activity = CollaborationActivity.create(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata,
        )
        
        self.activities.append(activity)
        
        if user_id in self.users:
            self.users[user_id].update_last_active()
        
        return activity
    
    def get_user(self, user_id: str) -> Optional[CollaborationUser]:
        """
        Get a user in the space.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            The user, or None if not found
        """
        return self.users.get(user_id)
    
    def get_activities(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[CollaborationActivity]:
        """
        Get activities in the space.
        
        Args:
            user_id: Filter by user ID
            action: Filter by action
            target_type: Filter by target type
            target_id: Filter by target ID
            limit: Maximum number of activities to return
            
        Returns:
            A list of activities
        """
        activities = self.activities
        
        if user_id:
            activities = [a for a in activities if a.user_id == user_id]
        
        if action:
            activities = [a for a in activities if a.action == action]
        
        if target_type:
            activities = [a for a in activities if a.target_type == target_type]
        
        if target_id:
            activities = [a for a in activities if a.target_id == target_id]
        
        activities = sorted(activities, key=lambda a: a.timestamp, reverse=True)
        
        if limit:
            activities = activities[:limit]
        
        return activities
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the space to a dictionary.
        
        Returns:
            A dictionary representation of the space
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status.name,
            "users": {uid: user.to_dict() for uid, user in self.users.items()},
            "documents": self.documents,
            "activities": [a.to_dict() for a in self.activities],
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationSpace":
        """
        Create a space from a dictionary.
        
        Args:
            data: The dictionary representation of the space
            
        Returns:
            A CollaborationSpace object
        """
        status = CollaborationStatus.ACTIVE
        if data.get("status"):
            try:
                status = CollaborationStatus[data["status"]]
            except KeyError:
                status = CollaborationStatus.ACTIVE
        
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
        
        users = {}
        if data.get("users"):
            for uid, user_data in data["users"].items():
                users[uid] = CollaborationUser.from_dict(user_data)
        
        activities = []
        if data.get("activities"):
            for activity_data in data["activities"]:
                activities.append(CollaborationActivity.from_dict(activity_data))
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            owner_id=data.get("owner_id", ""),
            created_at=created_at,
            updated_at=updated_at,
            status=status,
            users=users,
            documents=data.get("documents", []),
            activities=activities,
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the space."""
        return (
            f"CollaborationSpace(id={self.id}, name={self.name}, "
            f"owner_id={self.owner_id}, users={len(self.users)}, "
            f"documents={len(self.documents)})"
        )
    
    def __repr__(self) -> str:
        """Get a string representation of the space."""
        return self.__str__()


class CollaborationInvitation:
    """
    Represents an invitation to a collaboration space.
    
    This class stores information about an invitation sent to a user
    to join a collaboration space.
    """
    
    def __init__(
        self,
        id: str,
        space_id: str,
        inviter_id: str,
        invitee_email: str,
        role: CollaborationRole,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        status: CollaborationStatus = CollaborationStatus.PENDING,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a collaboration invitation.
        
        Args:
            id: The unique identifier for the invitation
            space_id: The ID of the space
            inviter_id: The ID of the user who sent the invitation
            invitee_email: The email of the user being invited
            role: The role the invitee will have
            created_at: When the invitation was created
            expires_at: When the invitation expires
            status: The status of the invitation
            metadata: Additional metadata for the invitation
        """
        self.id = id
        self.space_id = space_id
        self.inviter_id = inviter_id
        self.invitee_email = invitee_email
        self.role = role
        self.created_at = created_at or datetime.utcnow()
        self.expires_at = expires_at
        self.status = status
        self.metadata = metadata or {}
    
    @classmethod
    def create(
        cls,
        space_id: str,
        inviter_id: str,
        invitee_email: str,
        role: CollaborationRole,
        expires_in_days: Optional[int] = 7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "CollaborationInvitation":
        """
        Create a new invitation.
        
        Args:
            space_id: The ID of the space
            inviter_id: The ID of the user who sent the invitation
            invitee_email: The email of the user being invited
            role: The role the invitee will have
            expires_in_days: Number of days until the invitation expires
            metadata: Additional metadata for the invitation
            
        Returns:
            A CollaborationInvitation object
        """
        created_at = datetime.utcnow()
        expires_at = None
        
        if expires_in_days:
            expires_at = created_at + datetime.timedelta(days=expires_in_days)
        
        return cls(
            id=str(uuid.uuid4()),
            space_id=space_id,
            inviter_id=inviter_id,
            invitee_email=invitee_email,
            role=role,
            created_at=created_at,
            expires_at=expires_at,
            status=CollaborationStatus.PENDING,
            metadata=metadata or {},
        )
    
    def is_expired(self) -> bool:
        """
        Check if the invitation is expired.
        
        Returns:
            True if the invitation is expired, False otherwise
        """
        if not self.expires_at:
            return False
        
        return datetime.utcnow() > self.expires_at
    
    def accept(self) -> bool:
        """
        Accept the invitation.
        
        Returns:
            True if the invitation was accepted, False otherwise
        """
        if self.status != CollaborationStatus.PENDING:
            return False
        
        if self.is_expired():
            return False
        
        self.status = CollaborationStatus.ACTIVE
        return True
    
    def decline(self) -> bool:
        """
        Decline the invitation.
        
        Returns:
            True if the invitation was declined, False otherwise
        """
        if self.status != CollaborationStatus.PENDING:
            return False
        
        self.status = CollaborationStatus.DELETED
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the invitation to a dictionary.
        
        Returns:
            A dictionary representation of the invitation
        """
        return {
            "id": self.id,
            "space_id": self.space_id,
            "inviter_id": self.inviter_id,
            "invitee_email": self.invitee_email,
            "role": self.role.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.name,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationInvitation":
        """
        Create an invitation from a dictionary.
        
        Args:
            data: The dictionary representation of the invitation
            
        Returns:
            A CollaborationInvitation object
        """
        role = CollaborationRole.VIEWER
        if data.get("role"):
            try:
                role = CollaborationRole[data["role"]]
            except KeyError:
                role = CollaborationRole.VIEWER
        
        status = CollaborationStatus.PENDING
        if data.get("status"):
            try:
                status = CollaborationStatus[data["status"]]
            except KeyError:
                status = CollaborationStatus.PENDING
        
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                created_at = datetime.utcnow()
        
        expires_at = None
        if data.get("expires_at"):
            try:
                expires_at = datetime.fromisoformat(data["expires_at"])
            except ValueError:
                expires_at = None
        
        return cls(
            id=data.get("id", ""),
            space_id=data.get("space_id", ""),
            inviter_id=data.get("inviter_id", ""),
            invitee_email=data.get("invitee_email", ""),
            role=role,
            created_at=created_at,
            expires_at=expires_at,
            status=status,
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the invitation."""
        return (
            f"CollaborationInvitation(id={self.id}, space_id={self.space_id}, "
            f"invitee_email={self.invitee_email}, role={self.role.name}, "
            f"status={self.status.name})"
        )
    
    def __repr__(self) -> str:
        """Get a string representation of the invitation."""
        return self.__str__()

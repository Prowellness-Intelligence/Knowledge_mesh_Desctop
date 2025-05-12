"""
Test file for the Collaboration Service of the Knowledge Mesh Desktop application.

This module provides tests for the collaborative knowledge sharing features,
including managing collaboration spaces, user permissions, and document sharing.
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.core.config import Config
from src.core.events import EventType, Event, event_bus
from src.models.collaboration import (
    CollaborationSpace, CollaborationUser, CollaborationActivity,
    CollaborationInvitation, CollaborationRole, CollaborationPermission,
    CollaborationStatus,
)
from src.services.collaboration_service import CollaborationService


class TestCollaborationService(unittest.TestCase):
    """Test the Collaboration Service."""
    
    def setUp(self):
        """Set up the test environment."""
        self.config = Config({
            "app.data_dir": "./test_data",
            "user.id": "test_user_id",
            "user.username": "Test User",
            "user.email": "test@example.com",
        })
        
        self.services = {
            "document_processor": MagicMock(),
            "knowledge_mesh": MagicMock(),
            "vault": MagicMock(),
        }
        
        self.service = CollaborationService(self.config, self.services)
        
        os.makedirs("./test_data/collaboration/spaces", exist_ok=True)
        os.makedirs("./test_data/collaboration/invitations", exist_ok=True)
    
    def tearDown(self):
        """Clean up the test environment."""
        import shutil
        if os.path.exists("./test_data"):
            shutil.rmtree("./test_data")
    
    def test_initialization(self):
        """Test service initialization."""
        self.assertEqual(self.service.config, self.config)
        self.assertEqual(self.service.services, self.services)
        self.assertFalse(self.service.is_running)
        self.assertEqual(self.service.current_user_id, "test_user_id")
        self.assertEqual(self.service.current_username, "Test User")
        self.assertEqual(self.service.current_email, "test@example.com")
        self.assertEqual(self.service.spaces_cache, {})
        self.assertEqual(self.service.invitations_cache, {})
    
    def test_create_space(self):
        """Test creating a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
            metadata={"test_key": "test_value"},
        ))
        
        self.assertIsNotNone(space)
        self.assertEqual(space.name, "Test Space")
        self.assertEqual(space.description, "A test collaboration space")
        self.assertEqual(space.owner_id, "test_user_id")
        self.assertEqual(space.metadata, {"test_key": "test_value"})
        self.assertEqual(space.status, CollaborationStatus.ACTIVE)
        
        space_path = Path("./test_data/collaboration/spaces") / f"{space.id}.pkl"
        self.assertTrue(space_path.exists())
        
        self.assertIn(space.id, self.service.spaces_cache)
        
        loop.run_until_complete(self.service.stop())
    
    def test_get_space(self):
        """Test getting a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        self.assertIsNotNone(retrieved_space)
        self.assertEqual(retrieved_space.id, space.id)
        self.assertEqual(retrieved_space.name, space.name)
        self.assertEqual(retrieved_space.description, space.description)
        self.assertEqual(retrieved_space.owner_id, space.owner_id)
        
        loop.run_until_complete(self.service.stop())
    
    def test_update_space(self):
        """Test updating a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        updated_space = loop.run_until_complete(self.service.update_space(
            space_id=space.id,
            name="Updated Space",
            description="An updated test collaboration space",
            metadata={"updated_key": "updated_value"},
        ))
        
        self.assertIsNotNone(updated_space)
        self.assertEqual(updated_space.id, space.id)
        self.assertEqual(updated_space.name, "Updated Space")
        self.assertEqual(updated_space.description, "An updated test collaboration space")
        self.assertEqual(updated_space.metadata, {"updated_key": "updated_value"})
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        self.assertEqual(retrieved_space.name, "Updated Space")
        self.assertEqual(retrieved_space.description, "An updated test collaboration space")
        self.assertEqual(retrieved_space.metadata, {"updated_key": "updated_value"})
        
        loop.run_until_complete(self.service.stop())
    
    def test_delete_space(self):
        """Test deleting a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        result = loop.run_until_complete(self.service.delete_space(space.id))
        
        self.assertTrue(result)
        
        space_path = Path("./test_data/collaboration/spaces") / f"{space.id}.pkl"
        self.assertFalse(space_path.exists())
        
        self.assertNotIn(space.id, self.service.spaces_cache)
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        self.assertIsNone(retrieved_space)
        
        loop.run_until_complete(self.service.stop())
    
    def test_add_user_to_space(self):
        """Test adding a user to a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        user = loop.run_until_complete(self.service.add_user_to_space(
            space_id=space.id,
            user_id="test_user_2",
            username="Test User 2",
            email="test2@example.com",
            role=CollaborationRole.EDITOR,
        ))
        
        self.assertIsNotNone(user)
        self.assertEqual(user.id, "test_user_2")
        self.assertEqual(user.username, "Test User 2")
        self.assertEqual(user.email, "test2@example.com")
        self.assertEqual(user.role, CollaborationRole.EDITOR)
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        self.assertIn("test_user_2", retrieved_space.users)
        self.assertEqual(retrieved_space.users["test_user_2"].username, "Test User 2")
        self.assertEqual(retrieved_space.users["test_user_2"].role, CollaborationRole.EDITOR)
        
        loop.run_until_complete(self.service.stop())
    
    def test_remove_user_from_space(self):
        """Test removing a user from a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        user = loop.run_until_complete(self.service.add_user_to_space(
            space_id=space.id,
            user_id="test_user_2",
            username="Test User 2",
            email="test2@example.com",
            role=CollaborationRole.EDITOR,
        ))
        
        result = loop.run_until_complete(self.service.remove_user_from_space(
            space_id=space.id,
            user_id="test_user_2",
        ))
        
        self.assertTrue(result)
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        self.assertNotIn("test_user_2", retrieved_space.users)
        
        loop.run_until_complete(self.service.stop())
    
    def test_update_user_role(self):
        """Test updating a user's role in a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        user = loop.run_until_complete(self.service.add_user_to_space(
            space_id=space.id,
            user_id="test_user_2",
            username="Test User 2",
            email="test2@example.com",
            role=CollaborationRole.EDITOR,
        ))
        
        result = loop.run_until_complete(self.service.update_user_role(
            space_id=space.id,
            user_id="test_user_2",
            role=CollaborationRole.ADMIN,
        ))
        
        self.assertTrue(result)
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        self.assertEqual(retrieved_space.users["test_user_2"].role, CollaborationRole.ADMIN)
        
        loop.run_until_complete(self.service.stop())
    
    def test_add_document_to_space(self):
        """Test adding a document to a collaboration space."""
        loop = asyncio.get_event_loop()
        
        self.services["document_processor"].get_document = MagicMock(
            return_value=asyncio.Future()
        )
        self.services["document_processor"].get_document.return_value.set_result(MagicMock())
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        result = loop.run_until_complete(self.service.add_document_to_space(
            space_id=space.id,
            document_id="test_document_id",
        ))
        
        self.assertTrue(result)
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        self.assertIn("test_document_id", retrieved_space.documents)
        
        loop.run_until_complete(self.service.stop())
    
    def test_remove_document_from_space(self):
        """Test removing a document from a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        space.add_document("test_document_id", added_by="test_user_id")
        
        loop.run_until_complete(self.service._save_space(space))
        
        result = loop.run_until_complete(self.service.remove_document_from_space(
            space_id=space.id,
            document_id="test_document_id",
        ))
        
        self.assertTrue(result)
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        self.assertNotIn("test_document_id", retrieved_space.documents)
        
        loop.run_until_complete(self.service.stop())
    
    def test_create_invitation(self):
        """Test creating an invitation to a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        invitation = loop.run_until_complete(self.service.create_invitation(
            space_id=space.id,
            invitee_email="invitee@example.com",
            role=CollaborationRole.EDITOR,
            expires_in_days=7,
            metadata={"test_key": "test_value"},
        ))
        
        self.assertIsNotNone(invitation)
        self.assertEqual(invitation.space_id, space.id)
        self.assertEqual(invitation.inviter_id, "test_user_id")
        self.assertEqual(invitation.invitee_email, "invitee@example.com")
        self.assertEqual(invitation.role, CollaborationRole.EDITOR)
        self.assertEqual(invitation.status, CollaborationStatus.PENDING)
        self.assertEqual(invitation.metadata, {"test_key": "test_value"})
        
        invitation_path = Path("./test_data/collaboration/invitations") / f"{invitation.id}.pkl"
        self.assertTrue(invitation_path.exists())
        
        self.assertIn(invitation.id, self.service.invitations_cache)
        
        loop.run_until_complete(self.service.stop())
    
    def test_get_invitation(self):
        """Test getting an invitation to a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        invitation = loop.run_until_complete(self.service.create_invitation(
            space_id=space.id,
            invitee_email="invitee@example.com",
            role=CollaborationRole.EDITOR,
        ))
        
        retrieved_invitation = loop.run_until_complete(self.service.get_invitation(invitation.id))
        
        self.assertIsNotNone(retrieved_invitation)
        self.assertEqual(retrieved_invitation.id, invitation.id)
        self.assertEqual(retrieved_invitation.space_id, invitation.space_id)
        self.assertEqual(retrieved_invitation.inviter_id, invitation.inviter_id)
        self.assertEqual(retrieved_invitation.invitee_email, invitation.invitee_email)
        self.assertEqual(retrieved_invitation.role, invitation.role)
        
        loop.run_until_complete(self.service.stop())
    
    def test_accept_invitation(self):
        """Test accepting an invitation to a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        invitation = loop.run_until_complete(self.service.create_invitation(
            space_id=space.id,
            invitee_email="test@example.com",  # Same as current user
            role=CollaborationRole.EDITOR,
        ))
        
        result_space = loop.run_until_complete(self.service.accept_invitation(invitation.id))
        
        self.assertIsNotNone(result_space)
        self.assertEqual(result_space.id, space.id)
        
        retrieved_invitation = loop.run_until_complete(self.service.get_invitation(invitation.id))
        
        self.assertEqual(retrieved_invitation.status, CollaborationStatus.ACTIVE)
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        self.assertIn("test_user_id", retrieved_space.users)
        self.assertEqual(retrieved_space.users["test_user_id"].role, CollaborationRole.EDITOR)
        
        loop.run_until_complete(self.service.stop())
    
    def test_decline_invitation(self):
        """Test declining an invitation to a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        invitation = loop.run_until_complete(self.service.create_invitation(
            space_id=space.id,
            invitee_email="test@example.com",  # Same as current user
            role=CollaborationRole.EDITOR,
        ))
        
        result = loop.run_until_complete(self.service.decline_invitation(invitation.id))
        
        self.assertTrue(result)
        
        retrieved_invitation = loop.run_until_complete(self.service.get_invitation(invitation.id))
        
        self.assertEqual(retrieved_invitation.status, CollaborationStatus.DELETED)
        
        loop.run_until_complete(self.service.stop())
    
    def test_get_invitations(self):
        """Test getting invitations to collaboration spaces."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        invitation1 = loop.run_until_complete(self.service.create_invitation(
            space_id=space.id,
            invitee_email="invitee1@example.com",
            role=CollaborationRole.EDITOR,
        ))
        
        invitation2 = loop.run_until_complete(self.service.create_invitation(
            space_id=space.id,
            invitee_email="invitee2@example.com",
            role=CollaborationRole.VIEWER,
        ))
        
        invitations = loop.run_until_complete(self.service.get_invitations())
        
        self.assertEqual(len(invitations), 2)
        self.assertIn(invitation1, invitations)
        self.assertIn(invitation2, invitations)
        
        invitations = loop.run_until_complete(self.service.get_invitations(space_id=space.id))
        
        self.assertEqual(len(invitations), 2)
        self.assertIn(invitation1, invitations)
        self.assertIn(invitation2, invitations)
        
        invitations = loop.run_until_complete(self.service.get_invitations(invitee_email="invitee1@example.com"))
        
        self.assertEqual(len(invitations), 1)
        self.assertIn(invitation1, invitations)
        self.assertNotIn(invitation2, invitations)
        
        loop.run_until_complete(self.service.stop())
    
    def test_get_user_invitations(self):
        """Test getting invitations for the current user."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        invitation1 = loop.run_until_complete(self.service.create_invitation(
            space_id=space.id,
            invitee_email="test@example.com",  # Same as current user
            role=CollaborationRole.EDITOR,
        ))
        
        invitation2 = loop.run_until_complete(self.service.create_invitation(
            space_id=space.id,
            invitee_email="invitee@example.com",
            role=CollaborationRole.VIEWER,
        ))
        
        invitations = loop.run_until_complete(self.service.get_user_invitations())
        
        self.assertEqual(len(invitations), 1)
        self.assertIn(invitation1, invitations)
        self.assertNotIn(invitation2, invitations)
        
        loop.run_until_complete(self.service.stop())
    
    def test_get_space_activities(self):
        """Test getting activities in a collaboration space."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        loop.run_until_complete(self.service.add_document_to_space(
            space_id=space.id,
            document_id="test_document_id",
        ))
        
        activities = loop.run_until_complete(self.service.get_space_activities(space.id))
        
        self.assertEqual(len(activities), 2)  # Create space and add document
        self.assertEqual(activities[0].action, "add_document")
        self.assertEqual(activities[0].target_type, "document")
        self.assertEqual(activities[0].target_id, "test_document_id")
        self.assertEqual(activities[1].action, "create")
        self.assertEqual(activities[1].target_type, "space")
        self.assertEqual(activities[1].target_id, space.id)
        
        activities = loop.run_until_complete(self.service.get_space_activities(
            space_id=space.id,
            user_id="test_user_id",
        ))
        
        self.assertEqual(len(activities), 2)
        
        activities = loop.run_until_complete(self.service.get_space_activities(
            space_id=space.id,
            action="add_document",
        ))
        
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].action, "add_document")
        
        loop.run_until_complete(self.service.stop())
    
    def test_vault_integration(self):
        """Test integration with HashiCorp Vault."""
        loop = asyncio.get_event_loop()
        
        self.services["vault"].encrypt_data = MagicMock(
            return_value=asyncio.Future()
        )
        self.services["vault"].encrypt_data.return_value.set_result("encrypted_data")
        
        self.services["vault"].decrypt_data = MagicMock(
            return_value=asyncio.Future()
        )
        self.services["vault"].decrypt_data.return_value.set_result("decrypted_data")
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        user = loop.run_until_complete(self.service.add_user_to_space(
            space_id=space.id,
            user_id="test_user_2",
            username="Test User 2",
            email="test2@example.com",
            role=CollaborationRole.EDITOR,
        ))
        
        self.services["vault"].encrypt_data.assert_called_with("test2@example.com")
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        self.services["vault"].decrypt_data.assert_called()
        
        loop.run_until_complete(self.service.stop())
    
    def test_document_event_handling(self):
        """Test handling of document events."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        space = loop.run_until_complete(self.service.create_space(
            name="Test Space",
            description="A test collaboration space",
        ))
        
        loop.run_until_complete(self.service.add_document_to_space(
            space_id=space.id,
            document_id="test_document_id",
        ))
        
        event_bus.publish(
            EventType.DOCUMENT_CREATED,
            {
                "document_id": "test_document_id_2",
            },
        )
        
        loop.run_until_complete(asyncio.sleep(0.1))
        
        event_bus.publish(
            EventType.DOCUMENT_UPDATED,
            {
                "document_id": "test_document_id",
            },
        )
        
        loop.run_until_complete(asyncio.sleep(0.1))
        
        event_bus.publish(
            EventType.DOCUMENT_DELETED,
            {
                "document_id": "test_document_id",
            },
        )
        
        loop.run_until_complete(asyncio.sleep(0.1))
        
        retrieved_space = loop.run_until_complete(self.service.get_space(space.id))
        
        activities = retrieved_space.get_activities()
        
        self.assertGreaterEqual(len(activities), 3)
        
        loop.run_until_complete(self.service.stop())


if __name__ == "__main__":
    unittest.main()

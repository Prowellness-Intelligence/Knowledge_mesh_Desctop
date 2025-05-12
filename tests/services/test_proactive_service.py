"""
Tests for the proactive service.

This module contains tests for the proactive service.
"""

import os
import tempfile
import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.core.config import Config
from src.core.events import EventType, Event
from src.services.proactive_service import ProactiveService, UserState, InteractionType


@pytest.fixture
def config():
    """Create a test configuration."""
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        "proactive_service.enabled": True,
        "proactive_service.min_interaction_interval": 15,  # minutes
        "proactive_service.max_daily_interactions": 20,
        "proactive_service.work_pattern_learning_rate": 0.1,
        "proactive_service.suggestion_threshold": 0.7,
        "proactive_service.quiet_hours_start": 22,  # 10 PM
        "proactive_service.quiet_hours_end": 8,     # 8 AM
        "proactive_service.weekend_mode": "reduced",
    }.get(key, default)
    return config


@pytest.mark.asyncio
async def test_proactive_service_init(config):
    """Test proactive service initialization."""
    service = ProactiveService(config)
    
    assert service.config == config
    assert service.is_running is False
    assert service.user_state == UserState.UNKNOWN
    assert service.last_interaction_time is None
    assert service.interaction_history == []
    assert service.work_pattern_model is None
    assert service.receptivity_model is None
    assert service.interaction_scheduler is None
    assert service.min_interaction_interval == timedelta(minutes=15)
    assert service.max_daily_interactions == 20
    assert service.daily_interaction_count == 0
    assert service.last_reset_day == datetime.now().day
    assert service.enabled is True
    assert service.monitoring_task is None


@pytest.mark.asyncio
async def test_proactive_service_initialize(config):
    """Test proactive service initialization."""
    service = ProactiveService(config)
    
    with patch("src.services.proactive_service.event_bus") as mock_event_bus:
        await service.initialize()
        
        mock_event_bus.subscribe.assert_any_call(
            EventType.USER_ACTIVITY, service._on_user_activity
        )
        mock_event_bus.subscribe.assert_any_call(
            EventType.USER_INTERACTION, service._on_user_interaction
        )
        mock_event_bus.subscribe.assert_any_call(
            EventType.DOCUMENT_PROCESSED, service._on_document_processed
        )
        mock_event_bus.subscribe.assert_any_call(
            EventType.RELATIONSHIP_DISCOVERED, service._on_relationship_discovered
        )


@pytest.mark.asyncio
async def test_proactive_service_start_stop(config):
    """Test starting and stopping the proactive service."""
    service = ProactiveService(config)
    await service.initialize()
    
    with patch("src.services.proactive_service.asyncio.create_task") as mock_create_task:
        await service.start()
        
        assert service.is_running is True
        mock_create_task.assert_called_once()
    
    with patch("src.services.proactive_service.asyncio.create_task") as mock_create_task:
        await service.stop()
        
        assert service.is_running is False


@pytest.mark.asyncio
async def test_update_user_state(config):
    """Test updating user state."""
    service = ProactiveService(config)
    await service.initialize()
    
    with patch("src.services.proactive_service.event_bus") as mock_event_bus:
        await service.update_user_state(UserState.FOCUSED)
        
        assert service.user_state == UserState.FOCUSED
        
        mock_event_bus.publish.assert_called_with(
            EventType.USER_STATE_CHANGED,
            {"previous_state": UserState.UNKNOWN, "current_state": UserState.FOCUSED}
        )


@pytest.mark.asyncio
async def test_record_interaction(config):
    """Test recording an interaction."""
    service = ProactiveService(config)
    await service.initialize()
    
    interaction_type = InteractionType.USER_INITIATED
    document_id = str(uuid4())
    relationship_id = str(uuid4())
    
    await service.record_interaction(
        interaction_type=interaction_type,
        document_id=document_id,
        relationship_id=relationship_id,
    )
    
    assert len(service.interaction_history) == 1
    assert service.interaction_history[0]["type"] == interaction_type
    assert service.interaction_history[0]["document_id"] == document_id
    assert service.interaction_history[0]["relationship_id"] == relationship_id
    assert "timestamp" in service.interaction_history[0]
    assert service.last_interaction_time is not None


@pytest.mark.asyncio
async def test_suggest_interaction(config):
    """Test suggesting an interaction."""
    service = ProactiveService(config)
    await service.initialize()
    
    knowledge_mesh_service = MagicMock()
    knowledge_mesh_service.get_relationships.return_value = asyncio.Future()
    knowledge_mesh_service.get_relationships.return_value.set_result([
        MagicMock(
            source_id=str(uuid4()),
            target_id=str(uuid4()),
            type="SEMANTIC_SIMILARITY",
            strength=0.9,
        ),
    ])
    
    service.knowledge_mesh_service = knowledge_mesh_service
    
    document_store_service = MagicMock()
    document_store_service.get_document.return_value = asyncio.Future()
    document_store_service.get_document.return_value.set_result(
        MagicMock(
            id=str(uuid4()),
            title="Test Document",
            summary="A test document about proactive suggestions.",
        )
    )
    
    service.document_store_service = document_store_service
    
    with patch("src.services.proactive_service.event_bus") as mock_event_bus:
        document_id = str(uuid4())
        await service.suggest_interaction(document_id)
        
        mock_event_bus.publish.assert_called_with(
            EventType.PROACTIVE_INTERACTION,
            {
                "document_id": document_id,
                "related_documents": [{"id": mock_event_bus.publish.call_args[0][1]["related_documents"][0]["id"]}],
                "suggestion_type": "DOCUMENT_RELATIONSHIP",
                "confidence": mock_event_bus.publish.call_args[0][1]["confidence"],
            }
        )


@pytest.mark.asyncio
async def test_can_suggest_now(config):
    """Test checking if a suggestion can be made now."""
    service = ProactiveService(config)
    await service.initialize()
    
    service.user_state = UserState.RECEPTIVE
    service.last_interaction_time = datetime.now() - timedelta(minutes=30)
    service.daily_interaction_count = 5
    
    result = await service.can_suggest_now()
    
    assert result is True
    
    service.user_state = UserState.FOCUSED
    
    result = await service.can_suggest_now()
    
    assert result is False
    
    service.user_state = UserState.RECEPTIVE
    service.last_interaction_time = datetime.now() - timedelta(minutes=5)
    
    result = await service.can_suggest_now()
    
    assert result is False
    
    service.user_state = UserState.RECEPTIVE
    service.last_interaction_time = datetime.now() - timedelta(minutes=30)
    service.daily_interaction_count = 20
    
    result = await service.can_suggest_now()
    
    assert result is False


@pytest.mark.asyncio
async def test_on_user_activity(config):
    """Test handling user activity events."""
    service = ProactiveService(config)
    await service.initialize()
    
    service.update_user_state = MagicMock(return_value=asyncio.Future())
    service.update_user_state.return_value.set_result(None)
    
    event = Event(
        type=EventType.USER_ACTIVITY,
        data={
            "activity_type": "KEYBOARD",
            "timestamp": datetime.now().isoformat(),
        }
    )
    
    await service._on_user_activity(event)
    
    service.update_user_state.assert_called_once()


@pytest.mark.asyncio
async def test_on_user_interaction(config):
    """Test handling user interaction events."""
    service = ProactiveService(config)
    await service.initialize()
    
    service.record_interaction = MagicMock(return_value=asyncio.Future())
    service.record_interaction.return_value.set_result(None)
    
    document_id = str(uuid4())
    event = Event(
        type=EventType.USER_INTERACTION,
        data={
            "interaction_type": InteractionType.USER_INITIATED,
            "document_id": document_id,
            "timestamp": datetime.now().isoformat(),
        }
    )
    
    await service._on_user_interaction(event)
    
    service.record_interaction.assert_called_with(
        interaction_type=InteractionType.USER_INITIATED,
        document_id=document_id,
        timestamp=event.data["timestamp"],
    )


@pytest.mark.asyncio
async def test_on_document_processed(config):
    """Test handling document processed events."""
    service = ProactiveService(config)
    await service.initialize()
    
    service.can_suggest_now = MagicMock(return_value=asyncio.Future())
    service.can_suggest_now.return_value.set_result(True)
    
    service.suggest_interaction = MagicMock(return_value=asyncio.Future())
    service.suggest_interaction.return_value.set_result(None)
    
    document_id = str(uuid4())
    event = Event(
        type=EventType.DOCUMENT_PROCESSED,
        data={"document_id": document_id}
    )
    
    await service._on_document_processed(event)
    
    service.can_suggest_now.assert_called_once()
    service.suggest_interaction.assert_called_with(document_id)


@pytest.mark.asyncio
async def test_on_relationship_discovered(config):
    """Test handling relationship discovered events."""
    service = ProactiveService(config)
    await service.initialize()
    
    service.can_suggest_now = MagicMock(return_value=asyncio.Future())
    service.can_suggest_now.return_value.set_result(True)
    
    service.suggest_interaction = MagicMock(return_value=asyncio.Future())
    service.suggest_interaction.return_value.set_result(None)
    
    source_id = str(uuid4())
    target_id = str(uuid4())
    event = Event(
        type=EventType.RELATIONSHIP_DISCOVERED,
        data={
            "source_id": source_id,
            "target_id": target_id,
            "type": "SEMANTIC_SIMILARITY",
            "strength": 0.9,
        }
    )
    
    await service._on_relationship_discovered(event)
    
    service.can_suggest_now.assert_called_once()
    service.suggest_interaction.assert_called_with(source_id)

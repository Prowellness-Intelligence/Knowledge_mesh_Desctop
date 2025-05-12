"""
Daily planner service for the Knowledge Mesh Desktop application.

This module provides the DailyPlannerService class, which manages smart cards
and daily plans for monitoring documents, activities, and providing insights.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set, Tuple

from src.core.config import Config
from src.core.events import EventType, Event, event_bus, publish_event
from src.models.document import Document
from src.models.context import Context, ContextType, FocusLevel
from src.models.smart_card import SmartCard, DailyPlan, CardType, CardPriority, CardStatus
from src.models.legal_document import LegalDocumentTemplate, SignatureRequest, SignatureStatus
from src.services.vault_integration import VaultIntegrationService


class DailyPlannerService:
    """
    Service for managing smart cards and daily plans.
    
    This service is responsible for creating and managing smart cards,
    generating daily plans, monitoring documents and activities, and
    providing insights and recommendations.
    """
    
    def __init__(self, config: Config, services: Optional[Dict[str, Any]] = None):
        """
        Initialize the daily planner service.
        
        Args:
            config: The application configuration
            services: Dictionary of other services
        """
        self.config = config
        self.services = services or {}
        self.is_running = False
        self.data_dir = Path(config.get("app.data_dir", "./data"))
        self.cards_dir = self.data_dir / "cards"
        self.plans_dir = self.data_dir / "plans"
        self.max_cards_per_day = config.get("daily_planner.max_cards_per_day", 20)
        self.max_plans_history = config.get("daily_planner.max_plans_history", 30)
        self.card_generation_interval = config.get("daily_planner.card_generation_interval", 60)  # seconds
        self.plan_generation_interval = config.get("daily_planner.plan_generation_interval", 3600)  # seconds
        self.sensitive_data_enabled = config.get("security.sensitive_data_enabled", False)
        self.security_level = config.get("security.level", "STANDARD")
        self.card_generation_task = None
        self.plan_generation_task = None
        self.current_plan = None
        self.plans_history = []
        self.cards = {}
        
        os.makedirs(self.cards_dir, exist_ok=True)
        os.makedirs(self.plans_dir, exist_ok=True)
    
    async def start(self):
        """Start the daily planner service."""
        if self.is_running:
            return
        
        self.is_running = True
        
        await self._load_cards()
        await self._load_plans()
        
        if not self.current_plan or self.current_plan.date != date.today():
            self.current_plan = await self._create_daily_plan(date.today())
        
        event_bus.subscribe(EventType.DOCUMENT_CREATED, self._handle_document_created)
        event_bus.subscribe(EventType.DOCUMENT_UPDATED, self._handle_document_updated)
        event_bus.subscribe(EventType.DOCUMENT_DELETED, self._handle_document_deleted)
        event_bus.subscribe(EventType.DOCUMENT_ACCESSED, self._handle_document_accessed)
        event_bus.subscribe(EventType.RELATIONSHIP_CREATED, self._handle_relationship_created)
        event_bus.subscribe(EventType.CONTEXT_CHANGED, self._handle_context_changed)
        event_bus.subscribe(EventType.SIGNATURE_REQUEST_CREATED, self._handle_signature_request_created)
        event_bus.subscribe(EventType.SIGNATURE_REQUEST_UPDATED, self._handle_signature_request_updated)
        
        self.card_generation_task = asyncio.create_task(self._card_generation_loop())
        self.plan_generation_task = asyncio.create_task(self._plan_generation_loop())
        
        publish_event(EventType.SERVICE_STARTED, {"service": "daily_planner"})
    
    async def stop(self):
        """Stop the daily planner service."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        event_bus.unsubscribe(EventType.DOCUMENT_CREATED, self._handle_document_created)
        event_bus.unsubscribe(EventType.DOCUMENT_UPDATED, self._handle_document_updated)
        event_bus.unsubscribe(EventType.DOCUMENT_DELETED, self._handle_document_deleted)
        event_bus.unsubscribe(EventType.DOCUMENT_ACCESSED, self._handle_document_accessed)
        event_bus.unsubscribe(EventType.RELATIONSHIP_CREATED, self._handle_relationship_created)
        event_bus.unsubscribe(EventType.CONTEXT_CHANGED, self._handle_context_changed)
        event_bus.unsubscribe(EventType.SIGNATURE_REQUEST_CREATED, self._handle_signature_request_created)
        event_bus.unsubscribe(EventType.SIGNATURE_REQUEST_UPDATED, self._handle_signature_request_updated)
        
        if self.card_generation_task:
            self.card_generation_task.cancel()
            try:
                await self.card_generation_task
            except asyncio.CancelledError:
                pass
            self.card_generation_task = None
        
        if self.plan_generation_task:
            self.plan_generation_task.cancel()
            try:
                await self.plan_generation_task
            except asyncio.CancelledError:
                pass
            self.plan_generation_task = None
        
        await self._save_cards()
        await self._save_plans()
        
        publish_event(EventType.SERVICE_STOPPED, {"service": "daily_planner"})
    
    async def get_current_plan(self) -> Optional[DailyPlan]:
        """
        Get the current daily plan.
        
        Returns:
            The current daily plan, or None if not available
        """
        if not self.current_plan or self.current_plan.date != date.today():
            self.current_plan = await self._create_daily_plan(date.today())
        
        return self.current_plan
    
    async def get_plan_for_date(self, plan_date: date) -> Optional[DailyPlan]:
        """
        Get the daily plan for a specific date.
        
        Args:
            plan_date: The date to get the plan for
            
        Returns:
            The daily plan for the specified date, or None if not available
        """
        if plan_date == date.today() and self.current_plan:
            return self.current_plan
        
        for plan in self.plans_history:
            if plan.date == plan_date:
                return plan
        
        plan_path = self.plans_dir / f"plan_{plan_date.isoformat()}.json"
        if plan_path.exists():
            try:
                with open(plan_path, "r") as f:
                    plan_data = json.load(f)
                
                return DailyPlan.from_dict(plan_data)
            except Exception as e:
                publish_event(
                    EventType.ERROR,
                    {
                        "message": f"Failed to load plan for date {plan_date.isoformat()}",
                        "error": str(e),
                        "service": "daily_planner",
                    },
                )
        
        return None
    
    async def get_card(self, card_id: str) -> Optional[SmartCard]:
        """
        Get a smart card by ID.
        
        Args:
            card_id: The ID of the card to get
            
        Returns:
            The smart card, or None if not found
        """
        if card_id in self.cards:
            return self.cards[card_id]
        
        card_path = self.cards_dir / f"card_{card_id}.json"
        if card_path.exists():
            try:
                with open(card_path, "r") as f:
                    card_data = json.load(f)
                
                card = SmartCard.from_dict(card_data)
                self.cards[card_id] = card
                return card
            except Exception as e:
                publish_event(
                    EventType.ERROR,
                    {
                        "message": f"Failed to load card {card_id}",
                        "error": str(e),
                        "service": "daily_planner",
                    },
                )
        
        return None
        
    async def create_card(self, card: SmartCard) -> SmartCard:
        """
        Create a new smart card.
        
        Args:
            card: The smart card to create
            
        Returns:
            The created smart card
        """
        self.cards[card.id] = card
        
        if self.current_plan:
            self.current_plan.add_card(card)
        
        await self._save_card(card)
        
        publish_event(
            EventType.CARD_CREATED,
            {
                "card_id": card.id,
                "card_type": card.card_type.name,
                "service": "daily_planner",
            },
        )
        
        return card
    
    async def update_card(self, card: SmartCard) -> SmartCard:
        """
        Update a smart card.
        
        Args:
            card: The smart card to update
            
        Returns:
            The updated smart card
        """
        self.cards[card.id] = card
        
        await self._save_card(card)
        
        publish_event(
            EventType.CARD_UPDATED,
            {
                "card_id": card.id,
                "card_type": card.card_type.name,
                "service": "daily_planner",
            },
        )
        
        return card
    
    async def delete_card(self, card_id: str) -> bool:
        """
        Delete a smart card.
        
        Args:
            card_id: The ID of the card to delete
            
        Returns:
            True if the card was deleted, False otherwise
        """
        if card_id not in self.cards:
            return False
        
        card = self.cards.pop(card_id)
        
        if self.current_plan:
            self.current_plan.remove_card(card_id)
        
        card_path = self.cards_dir / f"card_{card_id}.json"
        if card_path.exists():
            try:
                os.remove(card_path)
            except Exception as e:
                publish_event(
                    EventType.ERROR,
                    {
                        "message": f"Failed to delete card file {card_id}",
                        "error": str(e),
                        "service": "daily_planner",
                    },
                )
                return False
        
        publish_event(
            EventType.CARD_DELETED,
            {
                "card_id": card_id,
                "card_type": card.card_type.name if card else "unknown",
                "service": "daily_planner",
            },
        )
        
        return True
    
    async def dismiss_card(self, card_id: str) -> Optional[SmartCard]:
        """
        Dismiss a smart card.
        
        Args:
            card_id: The ID of the card to dismiss
            
        Returns:
            The dismissed card, or None if not found
        """
        card = await self.get_card(card_id)
        if not card:
            return None
        
        card.dismiss()
        await self.update_card(card)
        
        return card
    
    async def complete_card(self, card_id: str) -> Optional[SmartCard]:
        """
        Mark a smart card as completed.
        
        Args:
            card_id: The ID of the card to complete
            
        Returns:
            The completed card, or None if not found
        """
        card = await self.get_card(card_id)
        if not card:
            return None
        
        card.complete()
        await self.update_card(card)
        
        return card
    
    async def snooze_card(self, card_id: str, duration: timedelta) -> Optional[SmartCard]:
        """
        Snooze a smart card for a specified duration.
        
        Args:
            card_id: The ID of the card to snooze
            duration: The duration to snooze for
            
        Returns:
            The snoozed card, or None if not found
        """
        card = await self.get_card(card_id)
        if not card:
            return None
        
        card.snooze(duration)
        await self.update_card(card)
        
        return card
    
    async def get_active_cards(self) -> List[SmartCard]:
        """
        Get all active cards.
        
        Returns:
            A list of active cards
        """
        active_cards = []
        
        for card in self.cards.values():
            if card.is_active():
                active_cards.append(card)
        
        return active_cards
    
    async def get_cards_by_type(self, card_type: CardType) -> List[SmartCard]:
        """
        Get all cards of a specific type.
        
        Args:
            card_type: The type of cards to get
            
        Returns:
            A list of cards of the specified type
        """
        return [card for card in self.cards.values() if card.card_type == card_type]
    
    async def get_cards_by_document(self, document_id: str) -> List[SmartCard]:
        """
        Get all cards related to a specific document.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A list of cards related to the specified document
        """
        return [card for card in self.cards.values() if document_id in card.related_document_ids]
    
    async def _load_cards(self):
        """Load all cards from disk."""
        self.cards = {}
        
        if not self.cards_dir.exists():
            return
        
        for card_file in self.cards_dir.glob("card_*.json"):
            try:
                with open(card_file, "r") as f:
                    card_data = json.load(f)
                
                card = SmartCard.from_dict(card_data)
                self.cards[card.id] = card
            except Exception as e:
                publish_event(
                    EventType.ERROR,
                    {
                        "message": f"Failed to load card from {card_file}",
                        "error": str(e),
                        "service": "daily_planner",
                    },
                )
    
    async def _load_plans(self):
        """Load all plans from disk."""
        self.plans_history = []
        self.current_plan = None
        
        if not self.plans_dir.exists():
            return
        
        today = date.today()
        
        for plan_file in self.plans_dir.glob("plan_*.json"):
            try:
                with open(plan_file, "r") as f:
                    plan_data = json.load(f)
                
                plan = DailyPlan.from_dict(plan_data)
                
                if plan.date == today:
                    self.current_plan = plan
                else:
                    self.plans_history.append(plan)
            except Exception as e:
                publish_event(
                    EventType.ERROR,
                    {
                        "message": f"Failed to load plan from {plan_file}",
                        "error": str(e),
                        "service": "daily_planner",
                    },
                )
        
        self.plans_history.sort(key=lambda p: p.date, reverse=True)
        
        if len(self.plans_history) > self.max_plans_history:
            self.plans_history = self.plans_history[:self.max_plans_history]
    
    async def _save_cards(self):
        """Save all cards to disk."""
        for card in self.cards.values():
            await self._save_card(card)
    
    async def _save_card(self, card: SmartCard):
        """
        Save a card to disk.
        
        Args:
            card: The card to save
        """
        card_path = self.cards_dir / f"card_{card.id}.json"
        
        try:
            with open(card_path, "w") as f:
                json.dump(card.to_dict(), f, indent=2)
        except Exception as e:
            publish_event(
                EventType.ERROR,
                {
                    "message": f"Failed to save card {card.id}",
                    "error": str(e),
                    "service": "daily_planner",
                },
            )
    
    async def _save_plans(self):
        """Save all plans to disk."""
        if self.current_plan:
            await self._save_plan(self.current_plan)
        
        for plan in self.plans_history:
            await self._save_plan(plan)
    
    async def _save_plan(self, plan: DailyPlan):
        """
        Save a plan to disk.
        
        Args:
            plan: The plan to save
        """
        plan_path = self.plans_dir / f"plan_{plan.date.isoformat()}.json"
        
        try:
            with open(plan_path, "w") as f:
                json.dump(plan.to_dict(), f, indent=2)
        except Exception as e:
            publish_event(
                EventType.ERROR,
                {
                    "message": f"Failed to save plan for date {plan.date.isoformat()}",
                    "error": str(e),
                    "service": "daily_planner",
                },
            )
    
    async def _create_daily_plan(self, plan_date: date) -> DailyPlan:
        """
        Create a new daily plan.
        
        Args:
            plan_date: The date for the plan
            
        Returns:
            The created daily plan
        """
        plan = DailyPlan.create(
            date=plan_date,
            metadata={
                "created_by": "daily_planner_service",
                "version": "1.0",
            },
        )
        
        if self.current_plan and self.current_plan.date < plan_date:
            for card in self.current_plan.get_active_cards():
                if not card.is_expired():
                    plan.add_card(card)
        
        await self._generate_cards_for_plan(plan)
        
        await self._save_plan(plan)
        
        publish_event(
            EventType.PLAN_CREATED,
            {
                "plan_id": plan.id,
                "plan_date": plan.date.isoformat(),
                "service": "daily_planner",
            },
        )
        
        return plan
    
    async def _generate_cards_for_plan(self, plan: DailyPlan):
        """
        Generate cards for a plan.
        
        Args:
            plan: The plan to generate cards for
        """
        await self._generate_document_reminder_cards(plan)
        
        await self._generate_similar_documents_cards(plan)
        
        await self._generate_signature_reminder_cards(plan)
        
        await self._generate_knowledge_insight_cards(plan)
        
        await self._generate_daily_summary(plan)
    
    async def _generate_document_reminder_cards(self, plan: DailyPlan):
        """
        Generate document reminder cards for a plan.
        
        Args:
            plan: The plan to generate cards for
        """
        if "document_processor" not in self.services:
            return
        
        document_processor = self.services["document_processor"]
        
        neglected_documents = await document_processor.get_neglected_documents(days=7)
        
        for document in neglected_documents[:5]:  # Limit to 5 neglected documents
            card = await self._create_document_reminder_card(document)
            if card:
                plan.add_card(card)
    
    async def _generate_similar_documents_cards(self, plan: DailyPlan):
        """
        Generate similar documents cards for a plan.
        
        Args:
            plan: The plan to generate cards for
        """
        if "document_processor" not in self.services or "knowledge_mesh" not in self.services:
            return
        
        document_processor = self.services["document_processor"]
        knowledge_mesh = self.services["knowledge_mesh"]
        
        recent_documents = await document_processor.get_recent_documents(limit=3)
        
        for document in recent_documents:
            similar_documents = await knowledge_mesh.get_similar_documents(document.id, limit=5)
            
            if similar_documents:
                card = await self._create_similar_documents_card(document, similar_documents)
                if card:
                    plan.add_card(card)
    
    async def _generate_signature_reminder_cards(self, plan: DailyPlan):
        """
        Generate signature reminder cards for a plan.
        
        Args:
            plan: The plan to generate cards for
        """
        if "docusign_integration" not in self.services:
            return
        
        docusign_integration = self.services["docusign_integration"]
        
        pending_requests = await docusign_integration.get_pending_signature_requests()
        
        for request in pending_requests:
            card = await self._create_signature_reminder_card(request)
            if card:
                plan.add_card(card)
    
    async def _generate_knowledge_insight_cards(self, plan: DailyPlan):
        """
        Generate knowledge insight cards for a plan.
        
        Args:
            plan: The plan to generate cards for
        """
        if "knowledge_mesh" not in self.services:
            return
        
        knowledge_mesh = self.services["knowledge_mesh"]
        
        insights = await knowledge_mesh.get_insights(limit=3)
        
        for insight in insights:
            card = await self._create_knowledge_insight_card(insight)
            if card:
                plan.add_card(card)
    
    async def _generate_daily_summary(self, plan: DailyPlan):
        """
        Generate a daily summary card for a plan.
        
        Args:
            plan: The plan to generate the summary for
        """
        summary_data = {
            "date": plan.date.isoformat(),
            "document_count": 0,
            "new_document_count": 0,
            "updated_document_count": 0,
            "signature_request_count": 0,
            "pending_signature_count": 0,
            "relationship_count": 0,
            "insight_count": 0,
        }
        
        if "document_processor" in self.services:
            document_processor = self.services["document_processor"]
            summary_data["document_count"] = await document_processor.get_document_count()
            summary_data["new_document_count"] = await document_processor.get_new_document_count(days=1)
            summary_data["updated_document_count"] = await document_processor.get_updated_document_count(days=1)
        
        if "docusign_integration" in self.services:
            docusign_integration = self.services["docusign_integration"]
            summary_data["signature_request_count"] = await docusign_integration.get_signature_request_count()
            summary_data["pending_signature_count"] = await docusign_integration.get_pending_signature_count()
        
        if "knowledge_mesh" in self.services:
            knowledge_mesh = self.services["knowledge_mesh"]
            summary_data["relationship_count"] = await knowledge_mesh.get_relationship_count()
            summary_data["insight_count"] = await knowledge_mesh.get_insight_count()
        
        card = SmartCard.create(
            title=f"Daily Summary for {plan.date.strftime('%B %d, %Y')}",
            description=f"Document count: {summary_data['document_count']}\n"
                        f"New documents: {summary_data['new_document_count']}\n"
                        f"Updated documents: {summary_data['updated_document_count']}\n"
                        f"Pending signatures: {summary_data['pending_signature_count']}\n"
                        f"Knowledge insights: {summary_data['insight_count']}",
            card_type=CardType.ACTIVITY_SUMMARY,
            priority=CardPriority.MEDIUM,
            metadata=summary_data,
        )
        
        plan.add_card(card)
        await self._save_card(card)
    
    async def _create_document_reminder_card(self, document: Document) -> Optional[SmartCard]:
        """
        Create a document reminder card.
        
        Args:
            document: The document to create a reminder for
            
        Returns:
            The created card, or None if creation failed
        """
        try:
            card = SmartCard.create(
                title=f"Document Reminder: {document.title}",
                description=f"You haven't accessed this document in a while. Last accessed: {document.last_accessed_at.strftime('%B %d, %Y')}",
                card_type=CardType.DOCUMENT_REMINDER,
                priority=CardPriority.MEDIUM,
                related_document_ids=[document.id],
                actions=[
                    {
                        "name": "Open Document",
                        "type": "open_document",
                        "document_id": document.id,
                    },
                    {
                        "name": "Dismiss",
                        "type": "dismiss_card",
                    },
                ],
                is_sensitive=document.is_sensitive,
            )
            
            await self._save_card(card)
            return card
        except Exception as e:
            publish_event(
                EventType.ERROR,
                {
                    "message": f"Failed to create document reminder card for {document.id}",
                    "error": str(e),
                    "service": "daily_planner",
                },
            )
            return None
    
    async def _create_similar_documents_card(self, document: Document, similar_documents: List[Document]) -> Optional[SmartCard]:
        """
        Create a similar documents card.
        
        Args:
            document: The reference document
            similar_documents: The similar documents
            
        Returns:
            The created card, or None if creation failed
        """
        try:
            description = f"Documents similar to '{document.title}':\n"
            
            for i, similar_doc in enumerate(similar_documents, 1):
                description += f"{i}. {similar_doc.title}\n"
            
            card = SmartCard.create(
                title=f"Similar Documents: {document.title}",
                description=description,
                card_type=CardType.SIMILAR_DOCUMENTS,
                priority=CardPriority.LOW,
                related_document_ids=[document.id] + [doc.id for doc in similar_documents],
                actions=[
                    {
                        "name": "Open Original",
                        "type": "open_document",
                        "document_id": document.id,
                    },
                    {
                        "name": "Dismiss",
                        "type": "dismiss_card",
                    },
                ],
                is_sensitive=document.is_sensitive or any(doc.is_sensitive for doc in similar_documents),
            )
            
            for i, similar_doc in enumerate(similar_documents):
                card.add_action({
                    "name": f"Open Similar {i+1}",
                    "type": "open_document",
                    "document_id": similar_doc.id,
                })
            
            await self._save_card(card)
            return card
        except Exception as e:
            publish_event(
                EventType.ERROR,
                {
                    "message": f"Failed to create similar documents card for {document.id}",
                    "error": str(e),
                    "service": "daily_planner",
                },
            )
            return None
    
    async def _create_signature_reminder_card(self, signature_request: SignatureRequest) -> Optional[SmartCard]:
        """
        Create a signature reminder card.
        
        Args:
            signature_request: The signature request
            
        Returns:
            The created card, or None if creation failed
        """
        try:
            document_id = signature_request.document_id
            
            card = SmartCard.create(
                title=f"Signature Required: {signature_request.document_name}",
                description=f"A signature is required for '{signature_request.document_name}'. Requested by: {signature_request.sender_name}",
                card_type=CardType.SIGNATURE_REMINDER,
                priority=CardPriority.HIGH,
                due_at=signature_request.expires_at if signature_request.expires_at else None,
                related_document_ids=[document_id] if document_id else [],
                actions=[
                    {
                        "name": "Sign Document",
                        "type": "sign_document",
                        "signature_request_id": signature_request.id,
                    },
                    {
                        "name": "Dismiss",
                        "type": "dismiss_card",
                    },
                ],
                is_sensitive=signature_request.is_sensitive,
            )
            
            await self._save_card(card)
            return card
        except Exception as e:
            publish_event(
                EventType.ERROR,
                {
                    "message": f"Failed to create signature reminder card for {signature_request.id}",
                    "error": str(e),
                    "service": "daily_planner",
                },
            )
            return None
    
    async def _create_knowledge_insight_card(self, insight: Dict[str, Any]) -> Optional[SmartCard]:
        """
        Create a knowledge insight card.
        
        Args:
            insight: The knowledge insight
            
        Returns:
            The created card, or None if creation failed
        """
        try:
            card = SmartCard.create(
                title=f"Knowledge Insight: {insight.get('title', 'Untitled')}",
                description=insight.get("description", ""),
                card_type=CardType.KNOWLEDGE_INSIGHT,
                priority=CardPriority.MEDIUM,
                related_document_ids=insight.get("document_ids", []),
                actions=[
                    {
                        "name": "Explore Insight",
                        "type": "explore_insight",
                        "insight_id": insight.get("id"),
                    },
                    {
                        "name": "Dismiss",
                        "type": "dismiss_card",
                    },
                ],
                is_sensitive=insight.get("is_sensitive", False),
            )
            
            await self._save_card(card)
            return card
        except Exception as e:
            publish_event(
                EventType.ERROR,
                {
                    "message": f"Failed to create knowledge insight card for {insight.get('id', 'unknown')}",
                    "error": str(e),
                    "service": "daily_planner",
                },
            )
            return None
    
    async def _card_generation_loop(self):
        """Background task for generating cards."""
        while self.is_running:
            try:
                if self.current_plan:
                    await self._generate_cards_for_plan(self.current_plan)
                    
                    await self._save_plan(self.current_plan)
            except Exception as e:
                publish_event(
                    EventType.ERROR,
                    {
                        "message": "Error in card generation loop",
                        "error": str(e),
                        "service": "daily_planner",
                    },
                )
            
            await asyncio.sleep(self.card_generation_interval)
    
    async def _plan_generation_loop(self):
        """Background task for generating plans."""
        while self.is_running:
            try:
                today = date.today()
                
                if not self.current_plan or self.current_plan.date != today:
                    if self.current_plan:
                        self.plans_history.insert(0, self.current_plan)
                        
                        if len(self.plans_history) > self.max_plans_history:
                            self.plans_history = self.plans_history[:self.max_plans_history]
                    
                    # Create a new plan for today
                    self.current_plan = await self._create_daily_plan(today)
            except Exception as e:
                publish_event(
                    EventType.ERROR,
                    {
                        "message": "Error in plan generation loop",
                        "error": str(e),
                        "service": "daily_planner",
                    },
                )
            
            await asyncio.sleep(self.plan_generation_interval)
    
    async def _handle_document_created(self, event: Event):
        """
        Handle document created events.
        
        Args:
            event: The event to handle
        """
        if not self.is_running or not self.current_plan:
            return
        
        document_id = event.data.get("document_id")
        if not document_id:
            return
        
        if "document_processor" not in self.services:
            return
        
        document_processor = self.services["document_processor"]
        document = await document_processor.get_document(document_id)
        
        if not document:
            return
        
        card = SmartCard.create(
            title=f"New Document: {document.title}",
            description=f"A new document has been added: {document.title}",
            card_type=CardType.DOCUMENT_REMINDER,
            priority=CardPriority.INFO,
            related_document_ids=[document.id],
            actions=[
                {
                    "name": "Open Document",
                    "type": "open_document",
                    "document_id": document.id,
                },
                {
                    "name": "Dismiss",
                    "type": "dismiss_card",
                },
            ],
            is_sensitive=document.is_sensitive,
        )
        
        self.current_plan.add_card(card)
        await self._save_card(card)
        await self._save_plan(self.current_plan)
    
    async def _handle_document_updated(self, event: Event):
        """
        Handle document updated events.
        
        Args:
            event: The event to handle
        """
        if not self.is_running:
            return
        
        document_id = event.data.get("document_id")
        if not document_id:
            return
        
        related_cards = await self.get_cards_by_document(document_id)
        
        for card in related_cards:
            if card.card_type == CardType.DOCUMENT_REMINDER:
                card.updated_at = datetime.utcnow()
                await self._save_card(card)
    
    async def _handle_document_deleted(self, event: Event):
        """
        Handle document deleted events.
        
        Args:
            event: The event to handle
        """
        if not self.is_running:
            return
        
        document_id = event.data.get("document_id")
        if not document_id:
            return
        
        related_cards = await self.get_cards_by_document(document_id)
        
        for card in related_cards:
            await self.delete_card(card.id)
    
    async def _handle_document_accessed(self, event: Event):
        """
        Handle document accessed events.
        
        Args:
            event: The event to handle
        """
        if not self.is_running:
            return
        
        document_id = event.data.get("document_id")
        if not document_id:
            return
        
        related_cards = await self.get_cards_by_document(document_id)
        
        for card in related_cards:
            if card.card_type == CardType.DOCUMENT_REMINDER:
                card.complete()
                await self._save_card(card)
    
    async def _handle_relationship_created(self, event: Event):
        """
        Handle relationship created events.
        
        Args:
            event: The event to handle
        """
        if not self.is_running or not self.current_plan:
            return
        
        relationship_id = event.data.get("relationship_id")
        if not relationship_id or "knowledge_mesh" not in self.services:
            return
        
        knowledge_mesh = self.services["knowledge_mesh"]
        relationship = await knowledge_mesh.get_relationship(relationship_id)
        
        if not relationship:
            return
        
        if relationship.confidence > 0.7:
            source_doc_id = relationship.source_id
            target_doc_id = relationship.target_id
            
            if "document_processor" not in self.services:
                return
            
            document_processor = self.services["document_processor"]
            source_doc = await document_processor.get_document(source_doc_id)
            target_doc = await document_processor.get_document(target_doc_id)
            
            if not source_doc or not target_doc:
                return
            
            card = SmartCard.create(
                title=f"New Connection Found",
                description=f"A strong connection was found between '{source_doc.title}' and '{target_doc.title}'.",
                card_type=CardType.KNOWLEDGE_INSIGHT,
                priority=CardPriority.MEDIUM,
                related_document_ids=[source_doc_id, target_doc_id],
                actions=[
                    {
                        "name": "Open Source",
                        "type": "open_document",
                        "document_id": source_doc_id,
                    },
                    {
                        "name": "Open Target",
                        "type": "open_document",
                        "document_id": target_doc_id,
                    },
                    {
                        "name": "Dismiss",
                        "type": "dismiss_card",
                    },
                ],
                is_sensitive=source_doc.is_sensitive or target_doc.is_sensitive,
            )
            
            self.current_plan.add_card(card)
            await self._save_card(card)
            await self._save_plan(self.current_plan)
    
    async def _handle_context_changed(self, event: Event):
        """
        Handle context changed events.
        
        Args:
            event: The event to handle
        """
        if not self.is_running or not self.current_plan:
            return
        
        context_id = event.data.get("context_id")
        if not context_id or "contextual_awareness" not in self.services:
            return
        
        contextual_awareness = self.services["contextual_awareness"]
        context = await contextual_awareness.get_context(context_id)
        
        if not context:
            return
        
        if context.focus_level == FocusLevel.SEEKING_INPUT:
            for card in self.cards.values():
                if context_id in card.related_context_ids and card.is_active():
                    if card.priority != CardPriority.HIGH:
                        card.priority = CardPriority.HIGH
                        await self._save_card(card)
    
    async def _handle_signature_request_created(self, event: Event):
        """
        Handle signature request created events.
        
        Args:
            event: The event to handle
        """
        if not self.is_running or not self.current_plan:
            return
        
        request_id = event.data.get("request_id")
        if not request_id or "docusign_integration" not in self.services:
            return
        
        docusign_integration = self.services["docusign_integration"]
        request = await docusign_integration.get_signature_request(request_id)
        
        if not request:
            return
        
        # Create a card for the new signature request
        card = await self._create_signature_reminder_card(request)
        if card:
            self.current_plan.add_card(card)
            await self._save_plan(self.current_plan)
    
    async def _handle_signature_request_updated(self, event: Event):
        """
        Handle signature request updated events.
        
        Args:
            event: The event to handle
        """
        if not self.is_running:
            return
        
        request_id = event.data.get("request_id")
        status = event.data.get("status")
        
        if not request_id or not status:
            return
        
        # Find any cards related to this signature request
        for card in self.cards.values():
            if card.card_type == CardType.SIGNATURE_REMINDER:
                for action in card.actions:
                    if action.get("type") == "sign_document" and action.get("signature_request_id") == request_id:
                        if status == SignatureStatus.COMPLETED.name:
                            card.complete()
                        elif status == SignatureStatus.DECLINED.name:
                            card.dismiss()
                        elif status == SignatureStatus.EXPIRED.name:
                            card.status = CardStatus.EXPIRED
                        
                        await self._save_card(card)
                        break

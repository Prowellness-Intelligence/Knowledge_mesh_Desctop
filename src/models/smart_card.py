"""
Smart card models for the Knowledge Mesh Desktop application.

This module defines the models for smart cards and daily planning.
"""

import os
import uuid
from datetime import datetime, date, time, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union, Set

from src.core.config import Config
from src.models.document import Document
from src.models.context import Context


class CardType(Enum):
    """Enum defining the types of smart cards."""
    
    DOCUMENT_REMINDER = auto()     # Reminder about a document
    SIMILAR_DOCUMENTS = auto()     # Similar documents to current context
    TASK_REMINDER = auto()         # Reminder about a task
    MEETING_REMINDER = auto()      # Reminder about a meeting
    KNOWLEDGE_INSIGHT = auto()     # Insight from knowledge mesh
    ACTIVITY_SUMMARY = auto()      # Summary of recent activity
    COLLABORATION_UPDATE = auto()  # Update on collaboration
    SIGNATURE_REMINDER = auto()    # Reminder about document signatures
    CUSTOM = auto()                # Custom card type


class CardPriority(Enum):
    """Enum defining the priority levels for smart cards."""
    
    CRITICAL = auto()    # Critical priority
    HIGH = auto()        # High priority
    MEDIUM = auto()      # Medium priority
    LOW = auto()         # Low priority
    INFO = auto()        # Informational only


class CardStatus(Enum):
    """Enum defining the status of smart cards."""
    
    ACTIVE = auto()      # Card is active
    DISMISSED = auto()   # Card has been dismissed
    COMPLETED = auto()   # Card has been completed
    SNOOZED = auto()     # Card has been snoozed
    EXPIRED = auto()     # Card has expired
    ARCHIVED = auto()    # Card has been archived


class SmartCard:
    """
    Represents a smart card in the Knowledge Mesh Desktop application.
    
    A smart card is a proactive notification or reminder that appears
    in the daily planner, providing context-aware information to the user.
    """
    
    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        card_type: CardType,
        priority: CardPriority = CardPriority.MEDIUM,
        status: CardStatus = CardStatus.ACTIVE,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        due_at: Optional[datetime] = None,
        snoozed_until: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        related_document_ids: Optional[List[str]] = None,
        related_context_ids: Optional[List[str]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        is_sensitive: bool = False,
    ):
        """
        Initialize a smart card.
        
        Args:
            id: The unique identifier for the card
            title: The title of the card
            description: The description of the card
            card_type: The type of the card
            priority: The priority level of the card
            status: The status of the card
            created_at: When the card was created
            updated_at: When the card was last updated
            due_at: When the card is due
            snoozed_until: When the card should reappear if snoozed
            metadata: Additional metadata for the card
            related_document_ids: IDs of related documents
            related_context_ids: IDs of related contexts
            actions: List of actions that can be taken on the card
            user_id: The ID of the user the card is for
            is_sensitive: Whether the card contains sensitive information
        """
        self.id = id
        self.title = title
        self.description = description
        self.card_type = card_type
        self.priority = priority
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.due_at = due_at
        self.snoozed_until = snoozed_until
        self.metadata = metadata or {}
        self.related_document_ids = related_document_ids or []
        self.related_context_ids = related_context_ids or []
        self.actions = actions or []
        self.user_id = user_id
        self.is_sensitive = is_sensitive
    
    @classmethod
    def create(
        cls,
        title: str,
        description: str,
        card_type: CardType,
        priority: CardPriority = CardPriority.MEDIUM,
        due_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        related_document_ids: Optional[List[str]] = None,
        related_context_ids: Optional[List[str]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        is_sensitive: bool = False,
    ) -> "SmartCard":
        """
        Create a new smart card.
        
        Args:
            title: The title of the card
            description: The description of the card
            card_type: The type of the card
            priority: The priority level of the card
            due_at: When the card is due
            metadata: Additional metadata for the card
            related_document_ids: IDs of related documents
            related_context_ids: IDs of related contexts
            actions: List of actions that can be taken on the card
            user_id: The ID of the user the card is for
            is_sensitive: Whether the card contains sensitive information
            
        Returns:
            A new SmartCard
        """
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            card_type=card_type,
            priority=priority,
            status=CardStatus.ACTIVE,
            due_at=due_at,
            metadata=metadata,
            related_document_ids=related_document_ids,
            related_context_ids=related_context_ids,
            actions=actions,
            user_id=user_id,
            is_sensitive=is_sensitive,
        )
    
    def update_status(self, status: CardStatus) -> "SmartCard":
        """
        Update the status of the card.
        
        Args:
            status: The new status
            
        Returns:
            The updated SmartCard
        """
        self.status = status
        self.updated_at = datetime.utcnow()
        
        if status == CardStatus.SNOOZED and not self.snoozed_until:
            self.snoozed_until = datetime.utcnow() + timedelta(hours=1)
        
        return self
    
    def snooze(self, duration: timedelta) -> "SmartCard":
        """
        Snooze the card for a specified duration.
        
        Args:
            duration: The duration to snooze for
            
        Returns:
            The updated SmartCard
        """
        self.status = CardStatus.SNOOZED
        self.snoozed_until = datetime.utcnow() + duration
        self.updated_at = datetime.utcnow()
        
        return self
    
    def dismiss(self) -> "SmartCard":
        """
        Dismiss the card.
        
        Returns:
            The updated SmartCard
        """
        self.status = CardStatus.DISMISSED
        self.updated_at = datetime.utcnow()
        
        return self
    
    def complete(self) -> "SmartCard":
        """
        Mark the card as completed.
        
        Returns:
            The updated SmartCard
        """
        self.status = CardStatus.COMPLETED
        self.updated_at = datetime.utcnow()
        
        return self
    
    def archive(self) -> "SmartCard":
        """
        Archive the card.
        
        Returns:
            The updated SmartCard
        """
        self.status = CardStatus.ARCHIVED
        self.updated_at = datetime.utcnow()
        
        return self
    
    def is_active(self) -> bool:
        """
        Check if the card is active.
        
        Returns:
            True if the card is active, False otherwise
        """
        if self.status == CardStatus.ACTIVE:
            return True
        
        if self.status == CardStatus.SNOOZED and self.snoozed_until and datetime.utcnow() >= self.snoozed_until:
            self.status = CardStatus.ACTIVE
            self.snoozed_until = None
            self.updated_at = datetime.utcnow()
            return True
        
        return False
    
    def is_due(self) -> bool:
        """
        Check if the card is due.
        
        Returns:
            True if the card is due, False otherwise
        """
        if not self.due_at:
            return False
        
        return datetime.utcnow() >= self.due_at
    
    def is_expired(self) -> bool:
        """
        Check if the card has expired.
        
        Returns:
            True if the card has expired, False otherwise
        """
        if self.status == CardStatus.EXPIRED:
            return True
        
        if self.due_at and datetime.utcnow() > self.due_at + timedelta(days=1):
            self.status = CardStatus.EXPIRED
            self.updated_at = datetime.utcnow()
            return True
        
        return False
    
    def add_action(self, action: Dict[str, Any]) -> "SmartCard":
        """
        Add an action to the card.
        
        Args:
            action: The action to add
            
        Returns:
            The updated SmartCard
        """
        self.actions.append(action)
        self.updated_at = datetime.utcnow()
        
        return self
    
    def add_related_document(self, document_id: str) -> "SmartCard":
        """
        Add a related document to the card.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            The updated SmartCard
        """
        if document_id not in self.related_document_ids:
            self.related_document_ids.append(document_id)
            self.updated_at = datetime.utcnow()
        
        return self
    
    def add_related_context(self, context_id: str) -> "SmartCard":
        """
        Add a related context to the card.
        
        Args:
            context_id: The ID of the context
            
        Returns:
            The updated SmartCard
        """
        if context_id not in self.related_context_ids:
            self.related_context_ids.append(context_id)
            self.updated_at = datetime.utcnow()
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the smart card to a dictionary.
        
        Returns:
            A dictionary representation of the smart card
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "card_type": self.card_type.name,
            "priority": self.priority.name,
            "status": self.status.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "metadata": self.metadata,
            "related_document_ids": self.related_document_ids,
            "related_context_ids": self.related_context_ids,
            "actions": self.actions,
            "user_id": self.user_id,
            "is_sensitive": self.is_sensitive,
            "is_active": self.is_active(),
            "is_due": self.is_due(),
            "is_expired": self.is_expired(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SmartCard":
        """
        Create a smart card from a dictionary.
        
        Args:
            data: The dictionary representation of the smart card
            
        Returns:
            A SmartCard object
        """
        card_type = CardType.CUSTOM
        if data.get("card_type"):
            try:
                card_type = CardType[data["card_type"]]
            except KeyError:
                card_type = CardType.CUSTOM
        
        priority = CardPriority.MEDIUM
        if data.get("priority"):
            try:
                priority = CardPriority[data["priority"]]
            except KeyError:
                priority = CardPriority.MEDIUM
        
        status = CardStatus.ACTIVE
        if data.get("status"):
            try:
                status = CardStatus[data["status"]]
            except KeyError:
                status = CardStatus.ACTIVE
        
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
        
        due_at = None
        if data.get("due_at") and data["due_at"] is not None:
            try:
                due_at = datetime.fromisoformat(data["due_at"])
            except ValueError:
                due_at = None
        
        snoozed_until = None
        if data.get("snoozed_until") and data["snoozed_until"] is not None:
            try:
                snoozed_until = datetime.fromisoformat(data["snoozed_until"])
            except ValueError:
                snoozed_until = None
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            description=data.get("description", ""),
            card_type=card_type,
            priority=priority,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            due_at=due_at,
            snoozed_until=snoozed_until,
            metadata=data.get("metadata", {}),
            related_document_ids=data.get("related_document_ids", []),
            related_context_ids=data.get("related_context_ids", []),
            actions=data.get("actions", []),
            user_id=data.get("user_id"),
            is_sensitive=data.get("is_sensitive", False),
        )


class DailyPlan:
    """
    Represents a daily plan in the Knowledge Mesh Desktop application.
    
    A daily plan is a collection of smart cards for a specific day,
    organized by priority and time.
    """
    
    def __init__(
        self,
        id: str,
        date: date,
        cards: List[SmartCard],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ):
        """
        Initialize a daily plan.
        
        Args:
            id: The unique identifier for the plan
            date: The date of the plan
            cards: The smart cards in the plan
            created_at: When the plan was created
            updated_at: When the plan was last updated
            metadata: Additional metadata for the plan
            user_id: The ID of the user the plan is for
        """
        self.id = id
        self.date = date
        self.cards = cards
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.metadata = metadata or {}
        self.user_id = user_id
    
    @classmethod
    def create(
        cls,
        date: date,
        cards: Optional[List[SmartCard]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> "DailyPlan":
        """
        Create a new daily plan.
        
        Args:
            date: The date of the plan
            cards: The smart cards in the plan
            metadata: Additional metadata for the plan
            user_id: The ID of the user the plan is for
            
        Returns:
            A new DailyPlan
        """
        return cls(
            id=str(uuid.uuid4()),
            date=date,
            cards=cards or [],
            metadata=metadata,
            user_id=user_id,
        )
    
    def add_card(self, card: SmartCard) -> "DailyPlan":
        """
        Add a card to the plan.
        
        Args:
            card: The card to add
            
        Returns:
            The updated DailyPlan
        """
        self.cards.append(card)
        self.updated_at = datetime.utcnow()
        
        return self
    
    def remove_card(self, card_id: str) -> "DailyPlan":
        """
        Remove a card from the plan.
        
        Args:
            card_id: The ID of the card to remove
            
        Returns:
            The updated DailyPlan
        """
        self.cards = [card for card in self.cards if card.id != card_id]
        self.updated_at = datetime.utcnow()
        
        return self
    
    def get_card(self, card_id: str) -> Optional[SmartCard]:
        """
        Get a card from the plan.
        
        Args:
            card_id: The ID of the card to get
            
        Returns:
            The card if found, None otherwise
        """
        for card in self.cards:
            if card.id == card_id:
                return card
        
        return None
    
    def get_active_cards(self) -> List[SmartCard]:
        """
        Get all active cards in the plan.
        
        Returns:
            A list of active cards
        """
        return [card for card in self.cards if card.is_active()]
    
    def get_cards_by_priority(self, priority: CardPriority) -> List[SmartCard]:
        """
        Get all cards with a specific priority.
        
        Args:
            priority: The priority to filter by
            
        Returns:
            A list of cards with the specified priority
        """
        return [card for card in self.cards if card.priority == priority]
    
    def get_cards_by_type(self, card_type: CardType) -> List[SmartCard]:
        """
        Get all cards of a specific type.
        
        Args:
            card_type: The type to filter by
            
        Returns:
            A list of cards of the specified type
        """
        return [card for card in self.cards if card.card_type == card_type]
    
    def get_cards_by_document(self, document_id: str) -> List[SmartCard]:
        """
        Get all cards related to a specific document.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A list of cards related to the specified document
        """
        return [card for card in self.cards if document_id in card.related_document_ids]
    
    def get_cards_by_context(self, context_id: str) -> List[SmartCard]:
        """
        Get all cards related to a specific context.
        
        Args:
            context_id: The ID of the context
            
        Returns:
            A list of cards related to the specified context
        """
        return [card for card in self.cards if context_id in card.related_context_ids]
    
    def get_due_cards(self) -> List[SmartCard]:
        """
        Get all due cards in the plan.
        
        Returns:
            A list of due cards
        """
        return [card for card in self.cards if card.is_due()]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the daily plan to a dictionary.
        
        Returns:
            A dictionary representation of the daily plan
        """
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "cards": [card.to_dict() for card in self.cards],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "user_id": self.user_id,
            "active_cards_count": len(self.get_active_cards()),
            "due_cards_count": len(self.get_due_cards()),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DailyPlan":
        """
        Create a daily plan from a dictionary.
        
        Args:
            data: The dictionary representation of the daily plan
            
        Returns:
            A DailyPlan object
        """
        plan_date = date.today()
        if data.get("date"):
            try:
                plan_date = date.fromisoformat(data["date"])
            except ValueError:
                plan_date = date.today()
        
        cards = []
        if data.get("cards"):
            for card_data in data["cards"]:
                cards.append(SmartCard.from_dict(card_data))
        
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
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            date=plan_date,
            cards=cards,
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata", {}),
            user_id=data.get("user_id"),
        )

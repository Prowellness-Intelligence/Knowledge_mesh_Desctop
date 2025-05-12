"""
Notification Panel for the Knowledge Mesh Desktop application.

This module provides a panel for displaying proactive notifications to the user.
"""

import asyncio
import logging
import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable
import time

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus

logger = logging.getLogger(__name__)


class NotificationPanel:
    """
    Panel for displaying proactive notifications.
    
    This class provides a panel for displaying proactive notifications to the user,
    including document suggestions, relationship suggestions, and work pattern
    insights.
    """
    
    def __init__(self, parent, config: Config, services: Dict[str, Any]):
        """
        Initialize the notification panel.
        
        Args:
            parent: The parent widget
            config: Application configuration
            services: Application services
        """
        self.parent = parent
        self.config = config
        self.services = services
        self.frame = None
        self.notifications = []
        self.current_notification = None
        self.notification_label = None
        self.notification_content = None
        self.notification_buttons = None
        self.is_visible = False
        self.auto_hide_task = None
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.notification_style = self.config.get("proactive.notification_style", "STANDARD")
        self.notification_timeout = self.config.get("proactive.notification_timeout", 10)
        self.max_notifications = self.config.get("proactive.max_notifications", 10)
        self.enabled = self.config.get("proactive.enabled", True)
    
    async def initialize(self):
        """Initialize the notification panel."""
        logger.info("Initializing notification panel")
        
        try:
            self.frame = ttk.Frame(self.parent)
            
            self._create_notification_content()
            
            event_bus.subscribe(EventType.PROACTIVE_INTERACTION, self._on_proactive_interaction)
            
            self.hide()
            
            logger.info("Notification panel initialized")
        except Exception as e:
            logger.error(f"Error initializing notification panel: {e}", exc_info=True)
            raise
    
    def _create_notification_content(self):
        """Create the notification content for the notification panel."""
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.notification_label = ttk.Label(content_frame, text="", font=("Arial", 12, "bold"))
        self.notification_label.pack(fill=tk.X, padx=5, pady=5)
        
        self.notification_content = ttk.Label(content_frame, text="", wraplength=400)
        self.notification_content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.notification_buttons = ttk.Frame(content_frame)
        self.notification_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        close_button = ttk.Button(self.notification_buttons, text="Close", command=self.hide)
        close_button.pack(side=tk.RIGHT, padx=5)
    
    async def start(self):
        """Start the notification panel."""
        logger.info("Starting notification panel")
        
        logger.info("Notification panel started")
    
    async def stop(self):
        """Stop the notification panel."""
        logger.info("Stopping notification panel")
        
        event_bus.unsubscribe(EventType.PROACTIVE_INTERACTION, self._on_proactive_interaction)
        
        self.hide()
        
        logger.info("Notification panel stopped")
    
    def show(self):
        """Show the notification panel."""
        if not self.is_visible and self.frame:
            self.frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
            self.is_visible = True
    
    def hide(self):
        """Hide the notification panel."""
        if self.is_visible and self.frame:
            self.frame.pack_forget()
            self.is_visible = False
            
            self.current_notification = None
            
            if self.auto_hide_task:
                self.auto_hide_task.cancel()
                self.auto_hide_task = None
    
    def show_notification(self, interaction_type: str, content: Dict[str, Any]):
        """
        Show a notification.
        
        Args:
            interaction_type: The type of interaction
            content: The notification content
        """
        if not self.enabled:
            logger.info(f"Notification panel is disabled, ignoring notification: {interaction_type}")
            return
        
        try:
            self.notifications.append({
                "type": interaction_type,
                "content": content,
                "timestamp": time.time(),
            })
            
            if len(self.notifications) > self.max_notifications:
                self.notifications = self.notifications[-self.max_notifications:]
            
            if not self.current_notification:
                self._show_next_notification()
        except Exception as e:
            logger.error(f"Error showing notification: {e}", exc_info=True)
    
    def _show_next_notification(self):
        """Show the next notification in the queue."""
        if not self.notifications:
            logger.debug("No notifications in the queue")
            return
        
        try:
            notification = self.notifications.pop(0)
            self.current_notification = notification
            
            interaction_type = notification["type"]
            content = notification["content"]
            
            if self.notification_label:
                self.notification_label.config(text=self._get_notification_title(interaction_type))
            
            if self.notification_content:
                self.notification_content.config(text=self._get_notification_text(interaction_type, content))
            
            if self.notification_buttons:
                for widget in self.notification_buttons.winfo_children():
                    if widget.winfo_name() != "!button":  # Keep the close button
                        widget.destroy()
                
                self._add_notification_buttons(interaction_type, content)
            
            self.show()
            
            if self.notification_timeout > 0:
                if self.auto_hide_task:
                    self.auto_hide_task.cancel()
                
                self.auto_hide_task = asyncio.create_task(self._auto_hide())
        except Exception as e:
            logger.error(f"Error showing next notification: {e}", exc_info=True)
    
    def _get_notification_title(self, interaction_type: str) -> str:
        """
        Get the notification title based on the interaction type.
        
        Args:
            interaction_type: The type of interaction
            
        Returns:
            The notification title
        """
        if interaction_type == "DOCUMENT_SUGGESTION":
            return "Document Suggestion"
        elif interaction_type == "RELATIONSHIP_SUGGESTION":
            return "Relationship Suggestion"
        elif interaction_type == "WORK_PATTERN_INSIGHT":
            return "Work Pattern Insight"
        else:
            return interaction_type.replace("_", " ").title()
    
    def _get_notification_text(self, interaction_type: str, content: Dict[str, Any]) -> str:
        """
        Get the notification text based on the interaction type and content.
        
        Args:
            interaction_type: The type of interaction
            content: The notification content
            
        Returns:
            The notification text
        """
        if interaction_type == "DOCUMENT_SUGGESTION":
            document_title = content.get("document_title", "")
            reason = content.get("reason", "")
            return f"You might be interested in the document '{document_title}'. {reason}"
        elif interaction_type == "RELATIONSHIP_SUGGESTION":
            source_title = content.get("source_title", "")
            target_title = content.get("target_title", "")
            relationship_type = content.get("relationship_type", "")
            return f"I found a {relationship_type} relationship between '{source_title}' and '{target_title}'."
        elif interaction_type == "WORK_PATTERN_INSIGHT":
            insight = content.get("insight", "")
            return insight
        else:
            return str(content.get("message", ""))
    
    def _add_notification_buttons(self, interaction_type: str, content: Dict[str, Any]):
        """
        Add buttons to the notification based on the interaction type and content.
        
        Args:
            interaction_type: The type of interaction
            content: The notification content
        """
        if interaction_type == "DOCUMENT_SUGGESTION":
            document_id = content.get("document_id", "")
            
            if document_id:
                open_button = ttk.Button(
                    self.notification_buttons,
                    text="Open Document",
                    command=lambda: self._open_document(document_id)
                )
                open_button.pack(side=tk.LEFT, padx=5)
        elif interaction_type == "RELATIONSHIP_SUGGESTION":
            relationship_id = content.get("relationship_id", "")
            
            if relationship_id:
                view_button = ttk.Button(
                    self.notification_buttons,
                    text="View Relationship",
                    command=lambda: self._view_relationship(relationship_id)
                )
                view_button.pack(side=tk.LEFT, padx=5)
        elif interaction_type == "WORK_PATTERN_INSIGHT":
            action = content.get("action", "")
            action_data = content.get("action_data", {})
            
            if action and action_data:
                action_button = ttk.Button(
                    self.notification_buttons,
                    text=action,
                    command=lambda: self._perform_action(action, action_data)
                )
                action_button.pack(side=tk.LEFT, padx=5)
    
    def _open_document(self, document_id: str):
        """
        Open a document.
        
        Args:
            document_id: The document ID
        """
        try:
            publish(
                EventType.OPEN_DOCUMENT,
                {
                    "document_id": document_id,
                },
            )
            
            self.hide()
        except Exception as e:
            logger.error(f"Error opening document: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error opening document: {e}")
    
    def _view_relationship(self, relationship_id: str):
        """
        View a relationship.
        
        Args:
            relationship_id: The relationship ID
        """
        try:
            publish(
                EventType.OPEN_RELATIONSHIP,
                {
                    "relationship_id": relationship_id,
                },
            )
            
            self.hide()
        except Exception as e:
            logger.error(f"Error viewing relationship: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error viewing relationship: {e}")
    
    def _perform_action(self, action: str, action_data: Dict[str, Any]):
        """
        Perform an action.
        
        Args:
            action: The action to perform
            action_data: The action data
        """
        try:
            publish(
                EventType.PERFORM_ACTION,
                {
                    "action": action,
                    "action_data": action_data,
                },
            )
            
            self.hide()
        except Exception as e:
            logger.error(f"Error performing action: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error performing action: {e}")
    
    async def _auto_hide(self):
        """Automatically hide the notification after a timeout."""
        try:
            await asyncio.sleep(self.notification_timeout)
            
            self.hide()
            
            if self.notifications:
                self._show_next_notification()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in auto-hide task: {e}", exc_info=True)
    
    def _on_proactive_interaction(self, event):
        """
        Handle proactive interaction events.
        
        Args:
            event: The proactive interaction event
        """
        interaction_type = event.data.get("interaction_type", "")
        content = event.data.get("content", {})
        
        self.show_notification(interaction_type, content)
    
    def refresh(self):
        """Refresh the notification panel."""
        pass

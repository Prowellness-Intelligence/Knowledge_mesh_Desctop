"""
Search Panel for the Knowledge Mesh Desktop application.

This module provides a panel for searching documents and relationships in the
application.
"""

import asyncio
import logging
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus
from ..models.document import Document

logger = logging.getLogger(__name__)


class SearchPanel:
    """
    Panel for searching documents and relationships.
    
    This class provides a panel for searching documents and relationships in the
    application.
    """
    
    def __init__(self, parent, config: Config, services: Dict[str, Any]):
        """
        Initialize the search panel.
        
        Args:
            parent: The parent widget
            config: Application configuration
            services: Application services
        """
        self.parent = parent
        self.config = config
        self.services = services
        self.frame = None
        self.search_entry = None
        self.search_button = None
        self.search_type_var = None
        self.search_results = None
        self.search_results_frame = None
        self.status_label = None
        self.progress_bar = None
        self.last_search_query = None
        self.last_search_type = None
        self.search_history = []
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.max_search_results = self.config.get("ui.max_search_results", 100)
        self.search_history_size = self.config.get("ui.search_history_size", 10)
        self.min_search_length = self.config.get("ui.min_search_length", 3)
        self.search_delay = self.config.get("ui.search_delay", 0.5)
        self.search_timeout = self.config.get("ui.search_timeout", 10.0)
    
    async def initialize(self):
        """Initialize the search panel."""
        logger.info("Initializing search panel")
        
        try:
            self.frame = ttk.Frame(self.parent)
            
            self._create_search_bar()
            
            self._create_search_results()
            
            self._create_status_bar()
            
            event_bus.subscribe(EventType.DOCUMENT_INDEXED, self._on_document_indexed)
            event_bus.subscribe(EventType.DOCUMENT_DELETED, self._on_document_deleted)
            event_bus.subscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
            event_bus.subscribe(EventType.RELATIONSHIP_DELETED, self._on_relationship_deleted)
            
            logger.info("Search panel initialized")
        except Exception as e:
            logger.error(f"Error initializing search panel: {e}", exc_info=True)
            raise
    
    def _create_search_bar(self):
        """Create the search bar for the search panel."""
        search_frame = ttk.Frame(self.frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        search_label = ttk.Label(search_frame, text="Search:")
        search_label.pack(side=tk.LEFT, padx=5)
        
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", self._on_search)
        
        self.search_button = ttk.Button(search_frame, text="Search", command=self._on_search)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        type_frame = ttk.Frame(search_frame)
        type_frame.pack(side=tk.LEFT, padx=5)
        
        self.search_type_var = tk.StringVar()
        self.search_type_var.set("All")
        
        ttk.Radiobutton(type_frame, text="All", variable=self.search_type_var, value="All").pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="Documents", variable=self.search_type_var, value="Documents").pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="Relationships", variable=self.search_type_var, value="Relationships").pack(side=tk.LEFT)
        
        advanced_button = ttk.Button(search_frame, text="Advanced", command=self._on_advanced_search)
        advanced_button.pack(side=tk.LEFT, padx=5)
        
        history_frame = ttk.Frame(self.frame)
        history_frame.pack(fill=tk.X, padx=5, pady=5)
        
        history_label = ttk.Label(history_frame, text="History:")
        history_label.pack(side=tk.LEFT, padx=5)
        
        self.history_var = tk.StringVar()
        
        self.history_dropdown = ttk.Combobox(history_frame, textvariable=self.history_var, width=40)
        self.history_dropdown.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.history_dropdown.bind("<<ComboboxSelected>>", self._on_history_selected)
    
    def _create_search_results(self):
        """Create the search results for the search panel."""
        self.search_results_frame = ttk.LabelFrame(self.frame, text="Search Results")
        self.search_results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.search_results_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.search_results = tk.Listbox(self.search_results_frame, yscrollcommand=scrollbar.set, selectmode=tk.SINGLE)
        self.search_results.pack(fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.search_results.yview)
        
        self.search_results.bind("<<ListboxSelect>>", self._on_result_selected)
    
    def _create_status_bar(self):
        """Create the status bar for the search panel."""
        status_frame = ttk.Frame(self.frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = ttk.Progressbar(status_frame, mode="indeterminate", length=100)
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
    
    async def start(self):
        """Start the search panel."""
        logger.info("Starting search panel")
        
        self._update_search_history()
        
        logger.info("Search panel started")
    
    async def stop(self):
        """Stop the search panel."""
        logger.info("Stopping search panel")
        
        event_bus.unsubscribe(EventType.DOCUMENT_INDEXED, self._on_document_indexed)
        event_bus.unsubscribe(EventType.DOCUMENT_DELETED, self._on_document_deleted)
        event_bus.unsubscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
        event_bus.unsubscribe(EventType.RELATIONSHIP_DELETED, self._on_relationship_deleted)
        
        logger.info("Search panel stopped")
    
    def _update_search_history(self):
        """Update the search history dropdown."""
        if self.history_dropdown:
            self.history_dropdown["values"] = self.search_history
    
    def _add_to_search_history(self, query: str):
        """
        Add a query to the search history.
        
        Args:
            query: The search query
        """
        if query and query not in self.search_history:
            self.search_history.insert(0, query)
            
            if len(self.search_history) > self.search_history_size:
                self.search_history = self.search_history[:self.search_history_size]
            
            self._update_search_history()
    
    def _on_search(self, event=None):
        """
        Handle the search button click or Enter key press.
        
        Args:
            event: The event that triggered the search
        """
        query = self.search_entry.get() if self.search_entry else ""
        
        if not query or len(query) < self.min_search_length:
            if self.status_label:
                self.status_label.config(text=f"Search query must be at least {self.min_search_length} characters")
            return
        
        search_type = self.search_type_var.get() if self.search_type_var else "All"
        
        self._add_to_search_history(query)
        
        asyncio.create_task(self._perform_search(query, search_type))
    
    async def _perform_search(self, query: str, search_type: str):
        """
        Perform a search.
        
        Args:
            query: The search query
            search_type: The search type
        """
        try:
            if self.status_label:
                self.status_label.config(text=f"Searching for '{query}'...")
            
            if self.progress_bar:
                self.progress_bar.start()
            
            if self.search_results:
                self.search_results.delete(0, tk.END)
            
            self.last_search_query = query
            self.last_search_type = search_type
            
            results = []
            
            if search_type in ["All", "Documents"]:
                if "document_processor" in self.services and "vector_store" in self.services:
                    document_results = await self.services["vector_store"].search_documents(query, limit=self.max_search_results)
                    
                    for result in document_results:
                        document = await self.services["document_processor"].get_document(result["id"])
                        if document:
                            results.append({
                                "type": "document",
                                "document": document,
                                "score": result["score"],
                            })
            
            if search_type in ["All", "Relationships"]:
                if "knowledge_mesh" in self.services:
                    relationship_results = await self.services["knowledge_mesh"].search_relationships(query, limit=self.max_search_results)
                    
                    for result in relationship_results:
                        results.append({
                            "type": "relationship",
                            "relationship": result["relationship"],
                            "score": result["score"],
                        })
            
            results.sort(key=lambda r: r["score"], reverse=True)
            
            for result in results:
                if result["type"] == "document":
                    document = result["document"]
                    self.search_results.insert(tk.END, f"[Document] {document.title} ({result['score']:.2f})")
                elif result["type"] == "relationship":
                    relationship = result["relationship"]
                    source_doc = await self._get_document(relationship.source_id)
                    target_doc = await self._get_document(relationship.target_id)
                    
                    source_title = source_doc.title if source_doc else "Unknown"
                    target_title = target_doc.title if target_doc else "Unknown"
                    
                    self.search_results.insert(
                        tk.END,
                        f"[Relationship] {source_title} -> {relationship.type.name} -> {target_title} ({result['score']:.2f})"
                    )
            
            if self.status_label:
                self.status_label.config(text=f"Found {len(results)} results for '{query}'")
            
            if self.search_results_frame:
                self.search_results_frame.config(text=f"Search Results ({len(results)})")
        except Exception as e:
            logger.error(f"Error performing search: {e}", exc_info=True)
            if self.status_label:
                self.status_label.config(text=f"Error performing search: {e}")
            if self.search_results:
                self.search_results.insert(tk.END, f"Error performing search: {e}")
        finally:
            if self.progress_bar:
                self.progress_bar.stop()
    
    async def _get_document(self, document_id: str) -> Optional[Document]:
        """
        Get a document by ID.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            The document, or None if not found
        """
        if "document_processor" in self.services:
            return await self.services["document_processor"].get_document(document_id)
        return None
    
    def _on_result_selected(self, event):
        """
        Handle the search result selection event.
        
        Args:
            event: The search result selection event
        """
        if self.search_results:
            selection = self.search_results.curselection()
            if selection:
                index = selection[0]
                result_text = self.search_results.get(index)
                
                if result_text.startswith("[Document]"):
                    self._open_document(result_text)
                elif result_text.startswith("[Relationship]"):
                    self._open_relationship(result_text)
    
    def _open_document(self, result_text: str):
        """
        Open a document from a search result.
        
        Args:
            result_text: The search result text
        """
        try:
            title_start = result_text.find("[Document] ") + len("[Document] ")
            title_end = result_text.rfind(" (")
            
            if title_start >= 0 and title_end >= 0:
                title = result_text[title_start:title_end]
                
                asyncio.create_task(self._find_and_open_document(title))
        except Exception as e:
            logger.error(f"Error opening document: {e}", exc_info=True)
            if self.status_label:
                self.status_label.config(text=f"Error opening document: {e}")
    
    async def _find_and_open_document(self, title: str):
        """
        Find and open a document by title.
        
        Args:
            title: The document title
        """
        try:
            if "document_processor" in self.services:
                documents = await self.services["document_processor"].get_documents()
                
                for document in documents:
                    if document.title == title:
                        publish(
                            EventType.OPEN_DOCUMENT,
                            {
                                "document_id": document.id,
                                "document": document,
                            },
                        )
                        
                        if self.status_label:
                            self.status_label.config(text=f"Opened document: {title}")
                        
                        return
                
                if self.status_label:
                    self.status_label.config(text=f"Document not found: {title}")
        except Exception as e:
            logger.error(f"Error finding and opening document: {e}", exc_info=True)
            if self.status_label:
                self.status_label.config(text=f"Error finding and opening document: {e}")
    
    def _open_relationship(self, result_text: str):
        """
        Open a relationship from a search result.
        
        Args:
            result_text: The search result text
        """
        try:
            source_start = result_text.find("[Relationship] ") + len("[Relationship] ")
            source_end = result_text.find(" -> ")
            
            type_start = source_end + len(" -> ")
            type_end = result_text.find(" -> ", type_start)
            
            target_start = type_end + len(" -> ")
            target_end = result_text.rfind(" (")
            
            if source_start >= 0 and source_end >= 0 and type_start >= 0 and type_end >= 0 and target_start >= 0 and target_end >= 0:
                source_title = result_text[source_start:source_end]
                relationship_type = result_text[type_start:type_end]
                target_title = result_text[target_start:target_end]
                
                asyncio.create_task(self._find_and_open_relationship(source_title, relationship_type, target_title))
        except Exception as e:
            logger.error(f"Error opening relationship: {e}", exc_info=True)
            if self.status_label:
                self.status_label.config(text=f"Error opening relationship: {e}")
    
    async def _find_and_open_relationship(self, source_title: str, relationship_type: str, target_title: str):
        """
        Find and open a relationship.
        
        Args:
            source_title: The source document title
            relationship_type: The relationship type
            target_title: The target document title
        """
        try:
            source_doc = None
            target_doc = None
            
            if "document_processor" in self.services:
                documents = await self.services["document_processor"].get_documents()
                
                for document in documents:
                    if document.title == source_title:
                        source_doc = document
                    elif document.title == target_title:
                        target_doc = document
                    
                    if source_doc and target_doc:
                        break
            
            if not source_doc or not target_doc:
                if self.status_label:
                    self.status_label.config(text=f"Document not found: {source_title} or {target_title}")
                return
            
            if "knowledge_mesh" in self.services:
                relationships = await self.services["knowledge_mesh"].get_relationships(source_doc.id)
                
                for relationship in relationships:
                    if relationship.target_id == target_doc.id and relationship.type.name == relationship_type:
                        publish(
                            EventType.OPEN_RELATIONSHIP,
                            {
                                "relationship": relationship,
                                "source_document": source_doc,
                                "target_document": target_doc,
                            },
                        )
                        
                        if self.status_label:
                            self.status_label.config(text=f"Opened relationship: {source_title} -> {relationship_type} -> {target_title}")
                        
                        return
                
                if self.status_label:
                    self.status_label.config(text=f"Relationship not found: {source_title} -> {relationship_type} -> {target_title}")
        except Exception as e:
            logger.error(f"Error finding and opening relationship: {e}", exc_info=True)
            if self.status_label:
                self.status_label.config(text=f"Error finding and opening relationship: {e}")
    
    def _on_advanced_search(self):
        """Handle the advanced search button click."""
        logger.info("Advanced search not implemented yet")
        if self.status_label:
            self.status_label.config(text="Advanced search not implemented yet")
    
    def _on_history_selected(self, event):
        """
        Handle the history dropdown selection change.
        
        Args:
            event: The history dropdown selection change event
        """
        selected_query = self.history_var.get()
        
        if self.search_entry and selected_query:
            self.search_entry.delete(0, tk.END)
            self.search_entry.insert(0, selected_query)
            
            self._on_search()
    
    def _on_document_indexed(self, event):
        """
        Handle the document indexed event.
        
        Args:
            event: The document indexed event
        """
        if self.last_search_query and self.last_search_type:
            asyncio.create_task(self._perform_search(self.last_search_query, self.last_search_type))
    
    def _on_document_deleted(self, event):
        """
        Handle the document deleted event.
        
        Args:
            event: The document deleted event
        """
        if self.last_search_query and self.last_search_type:
            asyncio.create_task(self._perform_search(self.last_search_query, self.last_search_type))
    
    def _on_relationship_detected(self, event):
        """
        Handle the relationship detected event.
        
        Args:
            event: The relationship detected event
        """
        if self.last_search_query and self.last_search_type:
            asyncio.create_task(self._perform_search(self.last_search_query, self.last_search_type))
    
    def _on_relationship_deleted(self, event):
        """
        Handle the relationship deleted event.
        
        Args:
            event: The relationship deleted event
        """
        if self.last_search_query and self.last_search_type:
            asyncio.create_task(self._perform_search(self.last_search_query, self.last_search_type))
    
    def refresh(self):
        """Refresh the search panel."""
        if self.last_search_query and self.last_search_type:
            asyncio.create_task(self._perform_search(self.last_search_query, self.last_search_type))

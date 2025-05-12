"""
Relationship Panel for the Knowledge Mesh Desktop application.

This module provides a panel for displaying and managing relationships between
documents in the application.
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
from ..models.relationship import Relationship, RelationshipType, RelationshipStrength

logger = logging.getLogger(__name__)


class RelationshipPanel:
    """
    Panel for displaying and managing relationships between documents.
    
    This class provides a panel for displaying and managing relationships between
    documents in the application.
    """
    
    def __init__(self, parent, config: Config, services: Dict[str, Any]):
        """
        Initialize the relationship panel.
        
        Args:
            parent: The parent widget
            config: Application configuration
            services: Application services
        """
        self.parent = parent
        self.config = config
        self.services = services
        self.frame = None
        self.relationships = []
        self.selected_relationship = None
        self.relationship_list = None
        self.relationship_details = None
        self.filter_var = None
        self.sort_var = None
        self.min_strength_var = None
        self.graph_canvas = None
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.graph_width = self.config.get("ui.graph_width", 800)
        self.graph_height = self.config.get("ui.graph_height", 600)
        self.node_radius = self.config.get("ui.node_radius", 20)
        self.edge_width = self.config.get("ui.edge_width", 2)
        self.min_strength = self.config.get("knowledge_mesh.min_strength", 0.3)
        self.max_relationships = self.config.get("ui.max_relationships", 1000)
    
    async def initialize(self):
        """Initialize the relationship panel."""
        logger.info("Initializing relationship panel")
        
        try:
            self.frame = ttk.Frame(self.parent)
            
            self._create_toolbar()
            
            self._create_relationship_list()
            
            self._create_relationship_details()
            
            event_bus.subscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
            event_bus.subscribe(EventType.RELATIONSHIP_DELETED, self._on_relationship_deleted)
            
            logger.info("Relationship panel initialized")
        except Exception as e:
            logger.error(f"Error initializing relationship panel: {e}", exc_info=True)
            raise
    
    def _create_toolbar(self):
        """Create the toolbar for the relationship panel."""
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        refresh_button = ttk.Button(toolbar, text="Refresh", command=self.refresh)
        refresh_button.pack(side=tk.LEFT, padx=5)
        
        filter_label = ttk.Label(toolbar, text="Filter:")
        filter_label.pack(side=tk.LEFT, padx=5)
        
        self.filter_var = tk.StringVar()
        self.filter_var.set("All")
        
        filter_values = ["All"] + [t.name for t in RelationshipType]
        filter_dropdown = ttk.Combobox(toolbar, textvariable=self.filter_var, values=filter_values)
        filter_dropdown.pack(side=tk.LEFT, padx=5)
        filter_dropdown.bind("<<ComboboxSelected>>", self._on_filter_changed)
        
        sort_label = ttk.Label(toolbar, text="Sort:")
        sort_label.pack(side=tk.LEFT, padx=5)
        
        self.sort_var = tk.StringVar()
        self.sort_var.set("Strength (Highest)")
        
        sort_dropdown = ttk.Combobox(toolbar, textvariable=self.sort_var, values=["Strength (Highest)", "Strength (Lowest)", "Type (A-Z)", "Type (Z-A)"])
        sort_dropdown.pack(side=tk.LEFT, padx=5)
        sort_dropdown.bind("<<ComboboxSelected>>", self._on_sort_changed)
        
        strength_label = ttk.Label(toolbar, text="Min Strength:")
        strength_label.pack(side=tk.LEFT, padx=5)
        
        self.min_strength_var = tk.DoubleVar()
        self.min_strength_var.set(self.min_strength)
        
        strength_slider = ttk.Scale(toolbar, from_=0.0, to=1.0, orient=tk.HORIZONTAL, variable=self.min_strength_var, length=100)
        strength_slider.pack(side=tk.LEFT, padx=5)
        strength_slider.bind("<ButtonRelease-1>", self._on_strength_changed)
        
        self.strength_value_label = ttk.Label(toolbar, text=f"{self.min_strength:.1f}")
        self.strength_value_label.pack(side=tk.LEFT, padx=5)
        
        view_label = ttk.Label(toolbar, text="View:")
        view_label.pack(side=tk.LEFT, padx=5)
        
        self.view_var = tk.StringVar()
        self.view_var.set("List")
        
        view_dropdown = ttk.Combobox(toolbar, textvariable=self.view_var, values=["List", "Graph"])
        view_dropdown.pack(side=tk.LEFT, padx=5)
        view_dropdown.bind("<<ComboboxSelected>>", self._on_view_changed)
    
    def _create_relationship_list(self):
        """Create the relationship list for the relationship panel."""
        list_frame = ttk.LabelFrame(self.frame, text="Relationships")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.relationship_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, selectmode=tk.SINGLE)
        self.relationship_list.pack(fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.relationship_list.yview)
        
        self.relationship_list.bind("<<ListboxSelect>>", self._on_relationship_selected)
    
    def _create_relationship_details(self):
        """Create the relationship details for the relationship panel."""
        details_frame = ttk.LabelFrame(self.frame, text="Relationship Details")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.RIGHT)
        
        self.relationship_details = ttk.Notebook(details_frame)
        self.relationship_details.pack(fill=tk.BOTH, expand=True)
        
        info_frame = ttk.Frame(self.relationship_details)
        self.relationship_details.add(info_frame, text="Info")
        
        graph_frame = ttk.Frame(self.relationship_details)
        self.relationship_details.add(graph_frame, text="Graph")
        
        self.graph_canvas = tk.Canvas(graph_frame, width=400, height=300, bg="white")
        self.graph_canvas.pack(fill=tk.BOTH, expand=True)
    
    async def start(self):
        """Start the relationship panel."""
        logger.info("Starting relationship panel")
        
        await self._load_relationships()
        
        logger.info("Relationship panel started")
    
    async def stop(self):
        """Stop the relationship panel."""
        logger.info("Stopping relationship panel")
        
        event_bus.unsubscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
        event_bus.unsubscribe(EventType.RELATIONSHIP_DELETED, self._on_relationship_deleted)
        
        logger.info("Relationship panel stopped")
    
    async def _load_relationships(self):
        """Load the relationships from the knowledge mesh service."""
        try:
            if self.relationship_list:
                self.relationship_list.delete(0, tk.END)
            self.relationships = []
            
            if "knowledge_mesh" in self.services:
                self.relationships = await self.services["knowledge_mesh"].get_all_relationships()
            
            self._sort_relationships()
            
            filtered_relationships = self._filter_relationships()
            
            if self.relationship_list:
                for relationship in filtered_relationships:
                    source_doc = await self._get_document(relationship.source_id)
                    target_doc = await self._get_document(relationship.target_id)
                    
                    source_title = source_doc.title if source_doc else "Unknown"
                    target_title = target_doc.title if target_doc else "Unknown"
                    
                    self.relationship_list.insert(
                        tk.END,
                        f"{source_title} -> {relationship.type.name} -> {target_title} ({relationship.strength:.2f})"
                    )
            
            self._update_relationship_count()
            
            if self.view_var.get() == "Graph":
                self._update_graph_view()
        except Exception as e:
            logger.error(f"Error loading relationships: {e}", exc_info=True)
            if self.relationship_list:
                self.relationship_list.insert(tk.END, f"Error loading relationships: {e}")
    
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
    
    def _sort_relationships(self):
        """Sort the relationships based on the sort dropdown."""
        sort_option = self.sort_var.get() if self.sort_var else "Strength (Highest)"
        
        if sort_option == "Strength (Highest)":
            self.relationships.sort(key=lambda rel: rel.strength, reverse=True)
        elif sort_option == "Strength (Lowest)":
            self.relationships.sort(key=lambda rel: rel.strength)
        elif sort_option == "Type (A-Z)":
            self.relationships.sort(key=lambda rel: rel.type.name)
        elif sort_option == "Type (Z-A)":
            self.relationships.sort(key=lambda rel: rel.type.name, reverse=True)
    
    def _filter_relationships(self) -> List[Relationship]:
        """
        Filter the relationships based on the filter dropdown and minimum strength.
        
        Returns:
            A list of filtered relationships
        """
        filter_option = self.filter_var.get() if self.filter_var else "All"
        min_strength = self.min_strength_var.get() if self.min_strength_var else self.min_strength
        
        filtered_relationships = []
        
        for relationship in self.relationships:
            if filter_option == "All" or filter_option == relationship.type.name:
                if relationship.strength >= min_strength:
                    filtered_relationships.append(relationship)
        
        return filtered_relationships
    
    def _update_relationship_count(self):
        """Update the relationship count in the relationship list frame."""
        if self.relationship_list:
            list_frame = self.relationship_list.master.master
            if list_frame:
                list_frame.config(text=f"Relationships ({self.relationship_list.size()})")
    
    def _on_relationship_selected(self, event):
        """
        Handle the relationship selection event.
        
        Args:
            event: The relationship selection event
        """
        if self.relationship_list:
            selection = self.relationship_list.curselection()
            if selection:
                index = selection[0]
                filtered_relationships = self._filter_relationships()
                if 0 <= index < len(filtered_relationships):
                    self.selected_relationship = filtered_relationships[index]
                    self._update_relationship_details()
    
    def _update_relationship_details(self):
        """Update the relationship details based on the selected relationship."""
        if not self.selected_relationship or not self.relationship_details:
            return
        
        info_frame = self.relationship_details.nametowidget(self.relationship_details.tabs()[0])
        for widget in info_frame.winfo_children():
            widget.destroy()
        
        asyncio.create_task(self._update_info_tab(info_frame))
        
        graph_frame = self.relationship_details.nametowidget(self.relationship_details.tabs()[1])
        for widget in graph_frame.winfo_children():
            widget.destroy()
        
        self.graph_canvas = tk.Canvas(graph_frame, width=400, height=300, bg="white")
        self.graph_canvas.pack(fill=tk.BOTH, expand=True)
        
        self._draw_relationship_graph()
    
    async def _update_info_tab(self, info_frame):
        """
        Update the info tab with the selected relationship details.
        
        Args:
            info_frame: The info tab frame
        """
        try:
            source_doc = await self._get_document(self.selected_relationship.source_id)
            target_doc = await self._get_document(self.selected_relationship.target_id)
            
            source_title = source_doc.title if source_doc else "Unknown"
            target_title = target_doc.title if target_doc else "Unknown"
            
            ttk.Label(info_frame, text="Type:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=self.selected_relationship.type.name).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(info_frame, text="Strength:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=f"{self.selected_relationship.strength:.2f}").grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(info_frame, text="Strength Category:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=self.selected_relationship.strength_category.name).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(info_frame, text="Source Document:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=source_title).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(info_frame, text="Target Document:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=target_title).grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(info_frame, text="Created:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=str(self.selected_relationship.created_at or "")).grid(row=5, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(info_frame, text="Updated:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=str(self.selected_relationship.updated_at or "")).grid(row=6, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(info_frame, text="Bidirectional:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=str(self.selected_relationship.is_bidirectional)).grid(row=7, column=1, sticky=tk.W, padx=5, pady=2)
            
            row = 8
            if self.selected_relationship.metadata:
                ttk.Label(info_frame, text="Metadata:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
                row += 1
                
                for key, value in self.selected_relationship.metadata.items():
                    ttk.Label(info_frame, text=f"  {key}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
                    ttk.Label(info_frame, text=str(value)).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
                    row += 1
        except Exception as e:
            logger.error(f"Error updating info tab: {e}", exc_info=True)
            ttk.Label(info_frame, text=f"Error updating info tab: {e}").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    
    def _draw_relationship_graph(self):
        """Draw the relationship graph for the selected relationship."""
        if not self.selected_relationship or not self.graph_canvas:
            return
        
        try:
            self.graph_canvas.delete("all")
            
            canvas_width = self.graph_canvas.winfo_width()
            canvas_height = self.graph_canvas.winfo_height()
            
            source_x = canvas_width * 0.25
            source_y = canvas_height * 0.5
            
            target_x = canvas_width * 0.75
            target_y = canvas_height * 0.5
            
            self.graph_canvas.create_oval(
                source_x - self.node_radius,
                source_y - self.node_radius,
                source_x + self.node_radius,
                source_y + self.node_radius,
                fill="lightblue",
                outline="blue",
                width=2,
                tags=("node", "source"),
            )
            
            self.graph_canvas.create_oval(
                target_x - self.node_radius,
                target_y - self.node_radius,
                target_x + self.node_radius,
                target_y + self.node_radius,
                fill="lightgreen",
                outline="green",
                width=2,
                tags=("node", "target"),
            )
            
            edge_color = "black"
            if self.selected_relationship.strength_category == RelationshipStrength.WEAK:
                edge_color = "gray"
            elif self.selected_relationship.strength_category == RelationshipStrength.MODERATE:
                edge_color = "blue"
            elif self.selected_relationship.strength_category == RelationshipStrength.STRONG:
                edge_color = "green"
            elif self.selected_relationship.strength_category == RelationshipStrength.VERY_STRONG:
                edge_color = "red"
            
            self.graph_canvas.create_line(
                source_x + self.node_radius,
                source_y,
                target_x - self.node_radius,
                target_y,
                fill=edge_color,
                width=self.edge_width * self.selected_relationship.strength,
                arrow=tk.LAST,
                tags=("edge",),
            )
            
            self.graph_canvas.create_text(
                (source_x + target_x) / 2,
                (source_y + target_y) / 2 - 20,
                text=self.selected_relationship.type.name,
                fill=edge_color,
                font=("Arial", 10, "bold"),
                tags=("label", "type"),
            )
            
            self.graph_canvas.create_text(
                (source_x + target_x) / 2,
                (source_y + target_y) / 2 + 20,
                text=f"{self.selected_relationship.strength:.2f}",
                fill=edge_color,
                font=("Arial", 10),
                tags=("label", "strength"),
            )
            
            asyncio.create_task(self._draw_node_labels(source_x, source_y, target_x, target_y))
        except Exception as e:
            logger.error(f"Error drawing relationship graph: {e}", exc_info=True)
            self.graph_canvas.create_text(
                self.graph_canvas.winfo_width() / 2,
                self.graph_canvas.winfo_height() / 2,
                text=f"Error drawing graph: {e}",
                fill="red",
                font=("Arial", 10),
            )
    
    async def _draw_node_labels(self, source_x, source_y, target_x, target_y):
        """
        Draw the node labels for the relationship graph.
        
        Args:
            source_x: The x-coordinate of the source node
            source_y: The y-coordinate of the source node
            target_x: The x-coordinate of the target node
            target_y: The y-coordinate of the target node
        """
        try:
            source_doc = await self._get_document(self.selected_relationship.source_id)
            target_doc = await self._get_document(self.selected_relationship.target_id)
            
            source_title = source_doc.title if source_doc else "Unknown"
            target_title = target_doc.title if target_doc else "Unknown"
            
            self.graph_canvas.create_text(
                source_x,
                source_y - self.node_radius - 10,
                text=source_title,
                fill="blue",
                font=("Arial", 10),
                tags=("label", "source"),
            )
            
            self.graph_canvas.create_text(
                target_x,
                target_y - self.node_radius - 10,
                text=target_title,
                fill="green",
                font=("Arial", 10),
                tags=("label", "target"),
            )
        except Exception as e:
            logger.error(f"Error drawing node labels: {e}", exc_info=True)
    
    def _update_graph_view(self):
        """Update the graph view with all relationships."""
        logger.info("Graph view not implemented yet")
    
    def _on_filter_changed(self, event):
        """
        Handle the filter dropdown selection change.
        
        Args:
            event: The filter dropdown selection change event
        """
        asyncio.create_task(self._load_relationships())
    
    def _on_sort_changed(self, event):
        """
        Handle the sort dropdown selection change.
        
        Args:
            event: The sort dropdown selection change event
        """
        asyncio.create_task(self._load_relationships())
    
    def _on_strength_changed(self, event):
        """
        Handle the strength slider change.
        
        Args:
            event: The strength slider change event
        """
        if self.strength_value_label and self.min_strength_var:
            self.strength_value_label.config(text=f"{self.min_strength_var.get():.1f}")
        
        asyncio.create_task(self._load_relationships())
    
    def _on_view_changed(self, event):
        """
        Handle the view dropdown selection change.
        
        Args:
            event: The view dropdown selection change event
        """
        if self.view_var.get() == "Graph":
            self._update_graph_view()
        else:
            asyncio.create_task(self._load_relationships())
    
    def _on_relationship_detected(self, event):
        """
        Handle the relationship detected event.
        
        Args:
            event: The relationship detected event
        """
        asyncio.create_task(self._load_relationships())
    
    def _on_relationship_deleted(self, event):
        """
        Handle the relationship deleted event.
        
        Args:
            event: The relationship deleted event
        """
        asyncio.create_task(self._load_relationships())
    
    def refresh(self):
        """Refresh the relationship panel."""
        asyncio.create_task(self._load_relationships())

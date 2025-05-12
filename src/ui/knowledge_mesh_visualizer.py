"""
Knowledge Mesh Visualizer for the Knowledge Mesh Desktop application.

This module provides a component for visualizing the knowledge mesh,
showing relationships between documents in an interactive graph.
"""

import asyncio
import logging
import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable
import math
import random
import time

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus
from ..models.document import Document
from ..models.relationship import Relationship, RelationshipType, RelationshipStrength

logger = logging.getLogger(__name__)


class KnowledgeMeshVisualizer:
    """
    Component for visualizing the knowledge mesh.
    
    This class provides a component for visualizing the knowledge mesh,
    showing relationships between documents in an interactive graph.
    """
    
    def __init__(self, parent, config: Config, services: Dict[str, Any]):
        """
        Initialize the knowledge mesh visualizer.
        
        Args:
            parent: The parent widget
            config: Application configuration
            services: Application services
        """
        self.parent = parent
        self.config = config
        self.services = services
        self.frame = None
        self.canvas = None
        self.toolbar = None
        self.status_bar = None
        self.nodes = {}  # document_id -> node info
        self.edges = {}  # (source_id, target_id) -> edge info
        self.selected_node = None
        self.selected_edge = None
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.zoom_level = 1.0
        self.center_x = 0
        self.center_y = 0
        self.layout_algorithm = "force_directed"
        self.show_labels = True
        self.show_edge_labels = True
        self.min_relationship_strength = 0.3
        self.max_visible_nodes = 50
        self.animation_task = None
        self.is_animating = False
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.canvas_width = self.config.get("ui.graph_width", 800)
        self.canvas_height = self.config.get("ui.graph_height", 600)
        self.node_radius = self.config.get("ui.node_radius", 20)
        self.edge_width = self.config.get("ui.edge_width", 2)
        self.min_relationship_strength = self.config.get("knowledge_mesh.min_strength", 0.3)
        self.max_visible_nodes = self.config.get("ui.max_visible_nodes", 50)
        self.layout_algorithm = self.config.get("ui.layout_algorithm", "force_directed")
        self.show_labels = self.config.get("ui.show_labels", True)
        self.show_edge_labels = self.config.get("ui.show_edge_labels", True)
        self.animation_speed = self.config.get("ui.animation_speed", 0.05)
    
    async def initialize(self):
        """Initialize the knowledge mesh visualizer."""
        logger.info("Initializing knowledge mesh visualizer")
        
        try:
            self.frame = ttk.Frame(self.parent)
            
            self._create_toolbar()
            
            self._create_canvas()
            
            self._create_status_bar()
            
            self._bind_events()
            
            event_bus.subscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
            event_bus.subscribe(EventType.RELATIONSHIP_DELETED, self._on_relationship_deleted)
            event_bus.subscribe(EventType.DOCUMENT_ADDED, self._on_document_added)
            event_bus.subscribe(EventType.DOCUMENT_DELETED, self._on_document_deleted)
            event_bus.subscribe(EventType.UI_DOCUMENT_SELECTED, self._on_document_selected)
            
            logger.info("Knowledge mesh visualizer initialized")
        except Exception as e:
            logger.error(f"Error initializing knowledge mesh visualizer: {e}", exc_info=True)
            raise
    
    def _create_toolbar(self):
        """Create the toolbar for the knowledge mesh visualizer."""
        self.toolbar = ttk.Frame(self.frame)
        self.toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        refresh_button = ttk.Button(self.toolbar, text="Refresh", command=self.refresh)
        refresh_button.pack(side=tk.LEFT, padx=5)
        
        layout_label = ttk.Label(self.toolbar, text="Layout:")
        layout_label.pack(side=tk.LEFT, padx=5)
        
        self.layout_var = tk.StringVar()
        self.layout_var.set(self.layout_algorithm)
        
        layout_dropdown = ttk.Combobox(self.toolbar, textvariable=self.layout_var, values=["force_directed", "circular", "hierarchical"])
        layout_dropdown.pack(side=tk.LEFT, padx=5)
        layout_dropdown.bind("<<ComboboxSelected>>", self._on_layout_changed)
        
        filter_label = ttk.Label(self.toolbar, text="Filter:")
        filter_label.pack(side=tk.LEFT, padx=5)
        
        self.filter_var = tk.StringVar()
        self.filter_var.set("All")
        
        filter_values = ["All"] + [t.name for t in RelationshipType]
        filter_dropdown = ttk.Combobox(self.toolbar, textvariable=self.filter_var, values=filter_values)
        filter_dropdown.pack(side=tk.LEFT, padx=5)
        filter_dropdown.bind("<<ComboboxSelected>>", self._on_filter_changed)
        
        strength_label = ttk.Label(self.toolbar, text="Min Strength:")
        strength_label.pack(side=tk.LEFT, padx=5)
        
        self.min_strength_var = tk.DoubleVar()
        self.min_strength_var.set(self.min_relationship_strength)
        
        strength_slider = ttk.Scale(self.toolbar, from_=0.0, to=1.0, orient=tk.HORIZONTAL, variable=self.min_strength_var, length=100)
        strength_slider.pack(side=tk.LEFT, padx=5)
        strength_slider.bind("<ButtonRelease-1>", self._on_strength_changed)
        
        self.strength_value_label = ttk.Label(self.toolbar, text=f"{self.min_relationship_strength:.1f}")
        self.strength_value_label.pack(side=tk.LEFT, padx=5)
        
        zoom_in_button = ttk.Button(self.toolbar, text="+", width=2, command=self._zoom_in)
        zoom_in_button.pack(side=tk.RIGHT, padx=5)
        
        zoom_out_button = ttk.Button(self.toolbar, text="-", width=2, command=self._zoom_out)
        zoom_out_button.pack(side=tk.RIGHT, padx=5)
        
        reset_button = ttk.Button(self.toolbar, text="Reset View", command=self._reset_view)
        reset_button.pack(side=tk.RIGHT, padx=5)
        
        self.labels_var = tk.BooleanVar()
        self.labels_var.set(self.show_labels)
        
        labels_check = ttk.Checkbutton(self.toolbar, text="Show Labels", variable=self.labels_var, command=self._on_labels_changed)
        labels_check.pack(side=tk.RIGHT, padx=5)
        
        self.edge_labels_var = tk.BooleanVar()
        self.edge_labels_var.set(self.show_edge_labels)
        
        edge_labels_check = ttk.Checkbutton(self.toolbar, text="Show Edge Labels", variable=self.edge_labels_var, command=self._on_edge_labels_changed)
        edge_labels_check.pack(side=tk.RIGHT, padx=5)
    
    def _create_canvas(self):
        """Create the canvas for the knowledge mesh visualizer."""
        canvas_frame = ttk.Frame(self.frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.pack(fill=tk.X, side=tk.BOTTOM)
        
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        self.canvas.configure(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
    
    def _create_status_bar(self):
        """Create the status bar for the knowledge mesh visualizer."""
        self.status_bar = ttk.Frame(self.frame)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)
        
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.node_count_label = ttk.Label(self.status_bar, text="Nodes: 0")
        self.node_count_label.pack(side=tk.RIGHT, padx=5)
        
        self.edge_count_label = ttk.Label(self.status_bar, text="Edges: 0")
        self.edge_count_label.pack(side=tk.RIGHT, padx=5)
    
    def _bind_events(self):
        """Bind events to the canvas."""
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)  # Windows and macOS
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)  # Linux scroll down
        self.canvas.bind("<Motion>", self._on_canvas_motion)
    
    async def start(self):
        """Start the knowledge mesh visualizer."""
        logger.info("Starting knowledge mesh visualizer")
        
        await self._load_mesh()
        
        logger.info("Knowledge mesh visualizer started")
    
    async def stop(self):
        """Stop the knowledge mesh visualizer."""
        logger.info("Stopping knowledge mesh visualizer")
        
        event_bus.unsubscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
        event_bus.unsubscribe(EventType.RELATIONSHIP_DELETED, self._on_relationship_deleted)
        event_bus.unsubscribe(EventType.DOCUMENT_ADDED, self._on_document_added)
        event_bus.unsubscribe(EventType.DOCUMENT_DELETED, self._on_document_deleted)
        event_bus.unsubscribe(EventType.UI_DOCUMENT_SELECTED, self._on_document_selected)
        
        if self.animation_task:
            self.animation_task.cancel()
            self.animation_task = None
        
        logger.info("Knowledge mesh visualizer stopped")
    
    async def _load_mesh(self):
        """Load the knowledge mesh from the knowledge mesh service."""
        try:
            self.nodes = {}
            self.edges = {}
            
            if "knowledge_mesh" in self.services:
                documents = await self.services["knowledge_mesh"].get_all_documents()
                
                if len(documents) > self.max_visible_nodes:
                    documents = documents[:self.max_visible_nodes]
                
                for document in documents:
                    self.nodes[document.id] = {
                        "id": document.id,
                        "title": document.title,
                        "x": random.uniform(100, self.canvas_width - 100),
                        "y": random.uniform(100, self.canvas_height - 100),
                        "vx": 0,
                        "vy": 0,
                        "color": "lightblue",
                        "document": document,
                    }
                
                relationships = await self.services["knowledge_mesh"].get_all_relationships()
                
                for relationship in relationships:
                    if relationship.strength >= self.min_relationship_strength and \
                       relationship.source_id in self.nodes and \
                       relationship.target_id in self.nodes:
                        edge_key = (relationship.source_id, relationship.target_id)
                        self.edges[edge_key] = {
                            "source": relationship.source_id,
                            "target": relationship.target_id,
                            "type": relationship.type,
                            "strength": relationship.strength,
                            "color": self._get_edge_color(relationship),
                            "relationship": relationship,
                        }
            
            await self._apply_layout()
            
            self._draw_mesh()
            
            self._update_status_bar()
        except Exception as e:
            logger.error(f"Error loading knowledge mesh: {e}", exc_info=True)
            self._set_status(f"Error loading knowledge mesh: {e}")
    
    async def _apply_layout(self):
        """Apply the selected layout algorithm to the mesh."""
        if self.layout_algorithm == "force_directed":
            await self._apply_force_directed_layout()
        elif self.layout_algorithm == "circular":
            self._apply_circular_layout()
        elif self.layout_algorithm == "hierarchical":
            self._apply_hierarchical_layout()
    
    async def _apply_force_directed_layout(self):
        """Apply the force-directed layout algorithm to the mesh."""
        if not self.nodes:
            return
        
        for node_id, node in self.nodes.items():
            if "x" not in node or "y" not in node:
                node["x"] = random.uniform(100, self.canvas_width - 100)
                node["y"] = random.uniform(100, self.canvas_height - 100)
            node["vx"] = 0
            node["vy"] = 0
        
        iterations = 100
        temperature = 0.9
        
        for i in range(iterations):
            for node1_id, node1 in self.nodes.items():
                for node2_id, node2 in self.nodes.items():
                    if node1_id != node2_id:
                        dx = node2["x"] - node1["x"]
                        dy = node2["y"] - node1["y"]
                        distance = max(1, math.sqrt(dx * dx + dy * dy))
                        
                        force = 1000 / (distance * distance)
                        
                        angle = math.atan2(dy, dx)
                        node1["vx"] -= force * math.cos(angle)
                        node1["vy"] -= force * math.sin(angle)
                        node2["vx"] += force * math.cos(angle)
                        node2["vy"] += force * math.sin(angle)
            
            for edge_key, edge in self.edges.items():
                source_id, target_id = edge_key
                source = self.nodes[source_id]
                target = self.nodes[target_id]
                
                dx = target["x"] - source["x"]
                dy = target["y"] - source["y"]
                distance = max(1, math.sqrt(dx * dx + dy * dy))
                
                force = 0.1 * distance
                
                angle = math.atan2(dy, dx)
                source["vx"] += force * math.cos(angle)
                source["vy"] += force * math.sin(angle)
                target["vx"] -= force * math.cos(angle)
                target["vy"] -= force * math.sin(angle)
            
            for node_id, node in self.nodes.items():
                node["x"] += node["vx"] * temperature
                node["y"] += node["vy"] * temperature
                
                node["x"] = max(50, min(self.canvas_width - 50, node["x"]))
                node["y"] = max(50, min(self.canvas_height - 50, node["y"]))
                
                node["vx"] *= 0.9
                node["vy"] *= 0.9
            
            temperature *= 0.99
            
            if i % 10 == 0 and not self.is_animating:
                self._draw_mesh()
                await asyncio.sleep(0.01)
    
    def _apply_circular_layout(self):
        """Apply the circular layout algorithm to the mesh."""
        if not self.nodes:
            return
        
        center_x = self.canvas_width / 2
        center_y = self.canvas_height / 2
        
        radius = min(self.canvas_width, self.canvas_height) / 2 - 50
        
        node_count = len(self.nodes)
        i = 0
        
        for node_id, node in self.nodes.items():
            angle = 2 * math.pi * i / node_count
            node["x"] = center_x + radius * math.cos(angle)
            node["y"] = center_y + radius * math.sin(angle)
            i += 1
    
    def _apply_hierarchical_layout(self):
        """Apply the hierarchical layout algorithm to the mesh."""
        if not self.nodes:
            return
        
        incoming_edges = {node_id: 0 for node_id in self.nodes}
        
        for edge_key in self.edges:
            source_id, target_id = edge_key
            incoming_edges[target_id] = incoming_edges.get(target_id, 0) + 1
        
        root_nodes = [node_id for node_id, count in incoming_edges.items() if count == 0]
        
        if not root_nodes and self.nodes:
            root_nodes = [next(iter(self.nodes))]
        
        levels = {}
        visited = set()
        
        def assign_level(node_id, level):
            if node_id in visited:
                return
            
            visited.add(node_id)
            levels[node_id] = max(levels.get(node_id, 0), level)
            
            for edge_key in self.edges:
                source_id, target_id = edge_key
                if source_id == node_id:
                    assign_level(target_id, level + 1)
        
        for root_node in root_nodes:
            assign_level(root_node, 0)
        
        max_level = max(levels.values()) if levels else 0
        level_counts = {}
        
        for node_id, level in levels.items():
            level_counts[level] = level_counts.get(level, 0) + 1
        
        level_positions = {}
        
        for node_id, level in levels.items():
            if level not in level_positions:
                level_positions[level] = 0
            
            x_spacing = self.canvas_width / (level_counts[level] + 1)
            x = x_spacing * (level_positions[level] + 1)
            
            y_spacing = self.canvas_height / (max_level + 1)
            y = y_spacing * (level + 0.5)
            
            self.nodes[node_id]["x"] = x
            self.nodes[node_id]["y"] = y
            
            level_positions[level] += 1
    
    def _draw_mesh(self):
        """Draw the knowledge mesh on the canvas."""
        if not self.canvas:
            return
        
        try:
            self.canvas.delete("all")
            
            for edge_key, edge in self.edges.items():
                source_id, target_id = edge_key
                source = self.nodes.get(source_id)
                target = self.nodes.get(target_id)
                
                if source and target:
                    source_x = source["x"] * self.zoom_level + self.center_x
                    source_y = source["y"] * self.zoom_level + self.center_y
                    target_x = target["x"] * self.zoom_level + self.center_x
                    target_y = target["y"] * self.zoom_level + self.center_y
                    
                    dx = target_x - source_x
                    dy = target_y - source_y
                    length = math.sqrt(dx * dx + dy * dy)
                    
                    if length > 0:
                        dx /= length
                        dy /= length
                        
                        start_x = source_x + dx * self.node_radius * self.zoom_level
                        start_y = source_y + dy * self.node_radius * self.zoom_level
                        end_x = target_x - dx * self.node_radius * self.zoom_level
                        end_y = target_y - dy * self.node_radius * self.zoom_level
                        
                        edge_width = max(1, self.edge_width * edge["strength"] * self.zoom_level)
                        edge_id = self.canvas.create_line(
                            start_x, start_y, end_x, end_y,
                            fill=edge["color"],
                            width=edge_width,
                            arrow=tk.LAST,
                            tags=("edge", f"edge_{source_id}_{target_id}"),
                        )
                        
                        edge["canvas_id"] = edge_id
                        
                        if self.show_edge_labels:
                            label_x = (start_x + end_x) / 2
                            label_y = (start_y + end_y) / 2 - 10 * self.zoom_level
                            
                            label_id = self.canvas.create_text(
                                label_x, label_y,
                                text=edge["type"].name,
                                fill=edge["color"],
                                font=("Arial", int(8 * self.zoom_level)),
                                tags=("edge_label", f"edge_label_{source_id}_{target_id}"),
                            )
                            
                            edge["label_id"] = label_id
            
            for node_id, node in self.nodes.items():
                x = node["x"] * self.zoom_level + self.center_x
                y = node["y"] * self.zoom_level + self.center_y
                
                radius = self.node_radius * self.zoom_level
                node_id_canvas = self.canvas.create_oval(
                    x - radius, y - radius, x + radius, y + radius,
                    fill=node["color"],
                    outline="blue",
                    width=2 * self.zoom_level,
                    tags=("node", f"node_{node_id}"),
                )
                
                node["canvas_id"] = node_id_canvas
                
                if self.show_labels:
                    label_id = self.canvas.create_text(
                        x, y + radius + 10 * self.zoom_level,
                        text=node["title"],
                        fill="black",
                        font=("Arial", int(10 * self.zoom_level)),
                        tags=("node_label", f"node_label_{node_id}"),
                    )
                    
                    node["label_id"] = label_id
            
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception as e:
            logger.error(f"Error drawing mesh: {e}", exc_info=True)
            self._set_status(f"Error drawing mesh: {e}")
    
    def _get_edge_color(self, relationship: Relationship) -> str:
        """
        Get the color for an edge based on the relationship type and strength.
        
        Args:
            relationship: The relationship
            
        Returns:
            The edge color
        """
        if relationship.strength_category == RelationshipStrength.WEAK:
            return "gray"
        elif relationship.strength_category == RelationshipStrength.MODERATE:
            return "blue"
        elif relationship.strength_category == RelationshipStrength.STRONG:
            return "green"
        elif relationship.strength_category == RelationshipStrength.VERY_STRONG:
            return "red"
        else:
            return "black"
    
    def _update_status_bar(self):
        """Update the status bar with mesh statistics."""
        if self.node_count_label:
            self.node_count_label.config(text=f"Nodes: {len(self.nodes)}")
        
        if self.edge_count_label:
            self.edge_count_label.config(text=f"Edges: {len(self.edges)}")
    
    def _set_status(self, message: str):
        """
        Set the status message.
        
        Args:
            message: The status message
        """
        if self.status_label:
            self.status_label.config(text=message)
    
    def _on_canvas_click(self, event):
        """
        Handle canvas click events.
        
        Args:
            event: The click event
        """
        self.dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        item = self.canvas.find_closest(event.x, event.y)
        if item:
            tags = self.canvas.gettags(item)
            if "node" in tags:
                for tag in tags:
                    if tag.startswith("node_"):
                        node_id = tag[5:]
                        self._select_node(node_id)
                        break
            elif "edge" in tags:
                for tag in tags:
                    if tag.startswith("edge_"):
                        source_id, target_id = tag[5:].split("_")
                        self._select_edge(source_id, target_id)
                        break
    
    def _on_canvas_release(self, event):
        """
        Handle canvas release events.
        
        Args:
            event: The release event
        """
        self.dragging = False
    
    def _on_canvas_drag(self, event):
        """
        Handle canvas drag events.
        
        Args:
            event: The drag event
        """
        if self.dragging:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            
            if self.selected_node:
                node = self.nodes.get(self.selected_node)
                if node:
                    node["x"] += dx / self.zoom_level
                    node["y"] += dy / self.zoom_level
                    
                    node["x"] = max(50, min(self.canvas_width - 50, node["x"]))
                    node["y"] = max(50, min(self.canvas_height - 50, node["y"]))
                    
                    self._draw_mesh()
            else:
                self.center_x += dx
                self.center_y += dy
                
                self._draw_mesh()
    
    def _on_canvas_motion(self, event):
        """
        Handle canvas motion events.
        
        Args:
            event: The motion event
        """
        item = self.canvas.find_closest(event.x, event.y)
        if item:
            tags = self.canvas.gettags(item)
            if "node" in tags:
                for tag in tags:
                    if tag.startswith("node_"):
                        node_id = tag[5:]
                        node = self.nodes.get(node_id)
                        if node:
                            self._set_status(f"Node: {node['title']}")
                        break
            elif "edge" in tags:
                for tag in tags:
                    if tag.startswith("edge_"):
                        source_id, target_id = tag[5:].split("_")
                        edge = self.edges.get((source_id, target_id))
                        if edge:
                            source = self.nodes.get(source_id)
                            target = self.nodes.get(target_id)
                            if source and target:
                                self._set_status(f"Edge: {source['title']} -> {edge['type'].name} -> {target['title']} ({edge['strength']:.2f})")
                        break
            else:
                self._set_status("Ready")
        else:
            self._set_status("Ready")
    
    def _on_mouse_wheel(self, event):
        """
        Handle mouse wheel events.
        
        Args:
            event: The mouse wheel event
        """
        if event.num == 4 or event.delta > 0:
            self._zoom_in()
        elif event.num == 5 or event.delta < 0:
            self._zoom_out()
    
    def _zoom_in(self):
        """Zoom in on the canvas."""
        self.zoom_level *= 1.1
        self._draw_mesh()
    
    def _zoom_out(self):
        """Zoom out on the canvas."""
        self.zoom_level /= 1.1
        self._draw_mesh()
    
    def _reset_view(self):
        """Reset the canvas view."""
        self.zoom_level = 1.0
        self.center_x = 0
        self.center_y = 0
        self._draw_mesh()
    
    def _select_node(self, node_id: str):
        """
        Select a node.
        
        Args:
            node_id: The node ID
        """
        if self.selected_node and self.selected_node in self.nodes:
            node = self.nodes[self.selected_node]
            if "canvas_id" in node:
                self.canvas.itemconfig(node["canvas_id"], outline="blue", width=2 * self.zoom_level)
        
        self.selected_node = node_id
        
        if node_id in self.nodes:
            node = self.nodes[node_id]
            if "canvas_id" in node:
                self.canvas.itemconfig(node["canvas_id"], outline="red", width=3 * self.zoom_level)
            
            publish(
                EventType.UI_DOCUMENT_SELECTED,
                {
                    "document_id": node_id,
                },
            )
    
    def _select_edge(self, source_id: str, target_id: str):
        """
        Select an edge.
        
        Args:
            source_id: The source node ID
            target_id: The target node ID
        """
        if self.selected_edge:
            source_id_prev, target_id_prev = self.selected_edge
            edge = self.edges.get((source_id_prev, target_id_prev))
            if edge and "canvas_id" in edge:
                self.canvas.itemconfig(edge["canvas_id"], width=max(1, self.edge_width * edge["strength"] * self.zoom_level))
        
        self.selected_edge = (source_id, target_id)
        
        edge = self.edges.get((source_id, target_id))
        if edge and "canvas_id" in edge:
            self.canvas.itemconfig(edge["canvas_id"], width=max(2, self.edge_width * edge["strength"] * self.zoom_level + 2))
            
            publish(
                EventType.UI_RELATIONSHIP_SELECTED,
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "relationship_type": edge["type"].name,
                },
            )
    
    def _on_layout_changed(self, event):
        """
        Handle layout algorithm change events.
        
        Args:
            event: The change event
        """
        self.layout_algorithm = self.layout_var.get()
        asyncio.create_task(self._apply_layout())
        self._draw_mesh()
    
    def _on_filter_changed(self, event):
        """
        Handle filter change events.
        
        Args:
            event: The change event
        """
        asyncio.create_task(self.refresh())
    
    def _on_strength_changed(self, event):
        """
        Handle minimum strength change events.
        
        Args:
            event: The change event
        """
        self.min_relationship_strength = self.min_strength_var.get()
        self.strength_value_label.config(text=f"{self.min_relationship_strength:.1f}")
        asyncio.create_task(self.refresh())
    
    def _on_labels_changed(self):
        """Handle label visibility change events."""
        self.show_labels = self.labels_var.get()
        self._draw_mesh()
    
    def _on_edge_labels_changed(self):
        """Handle edge label visibility change events."""
        self.show_edge_labels = self.edge_labels_var.get()
        self._draw_mesh()
    
    def _on_relationship_detected(self, event):
        """
        Handle relationship detected events.
        
        Args:
            event: The relationship detected event
        """
        asyncio.create_task(self.refresh())
    
    def _on_relationship_deleted(self, event):
        """
        Handle relationship deleted events.
        
        Args:
            event: The relationship deleted event
        """
        asyncio.create_task(self.refresh())
    
    def _on_document_added(self, event):
        """
        Handle document added events.
        
        Args:
            event: The document added event
        """
        asyncio.create_task(self.refresh())
    
    def _on_document_deleted(self, event):
        """
        Handle document deleted events.
        
        Args:
            event: The document deleted event
        """
        asyncio.create_task(self.refresh())
    
    def _on_document_selected(self, event):
        """
        Handle document selected events.
        
        Args:
            event: The document selected event
        """
        document_id = event.data.get("document_id")
        if document_id and document_id in self.nodes:
            self._select_node(document_id)
    
    async def refresh(self):
        """Refresh the knowledge mesh visualizer."""
        await self._load_mesh()

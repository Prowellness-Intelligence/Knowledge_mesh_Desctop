"""
Main Window for the Knowledge Mesh Desktop application.

This module provides the main window for the application, which contains
all the UI components and manages the overall layout.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus
from .document_panel import DocumentPanel
from .relationship_panel import RelationshipPanel
from .search_panel import SearchPanel
from .settings_panel import SettingsPanel
from .notification_panel import NotificationPanel

logger = logging.getLogger(__name__)


class MainWindow:
    """
    Main window for the Knowledge Mesh Desktop application.
    
    This class provides the main window for the application, which contains
    all the UI components and manages the overall layout.
    """
    
    def __init__(self, config: Config, services: Dict[str, Any]):
        """
        Initialize the main window.
        
        Args:
            config: Application configuration
            services: Application services
        """
        self.config = config
        self.services = services
        self.root = None
        self.panels = {}
        self.menu = None
        self.status_bar = None
        self.is_running = False
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.title = self.config.get("ui.title", "Knowledge Mesh Desktop")
        self.width = self.config.get("ui.width", 1200)
        self.height = self.config.get("ui.height", 800)
        self.icon_path = self.config.get("ui.icon_path")
        self.theme = self.config.get("ui.theme", "light")
        self.font_family = self.config.get("ui.font_family", "Arial")
        self.font_size = self.config.get("ui.font_size", 10)
    
    async def initialize(self):
        """Initialize the main window."""
        logger.info("Initializing main window")
        
        try:
            self.root = tk.Tk()
            self.root.title(self.title)
            self.root.geometry(f"{self.width}x{self.height}")
            
            if self.icon_path and os.path.exists(self.icon_path):
                self.root.iconbitmap(self.icon_path)
            
            self._configure_theme()
            
            self._create_menu()
            
            self.main_frame = ttk.Frame(self.root)
            self.main_frame.pack(fill=tk.BOTH, expand=True)
            
            await self._create_panels()
            
            self._create_status_bar()
            
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            
            event_bus.subscribe(EventType.DOCUMENT_INDEXED, self._on_document_indexed)
            event_bus.subscribe(EventType.RELATIONSHIP_DETECTED, self._on_relationship_detected)
            event_bus.subscribe(EventType.PROACTIVE_INTERACTION, self._on_proactive_interaction)
            
            logger.info("Main window initialized")
        except Exception as e:
            logger.error(f"Error initializing main window: {e}", exc_info=True)
            raise
    
    def _configure_theme(self):
        """Configure the theme for the application."""
        if self.theme == "dark":
            self.root.configure(bg="#2d2d2d")
            style = ttk.Style()
            style.theme_use("clam")
            style.configure(".", background="#2d2d2d", foreground="#ffffff")
            style.configure("TFrame", background="#2d2d2d")
            style.configure("TLabel", background="#2d2d2d", foreground="#ffffff")
            style.configure("TButton", background="#3d3d3d", foreground="#ffffff")
            style.configure("TEntry", fieldbackground="#3d3d3d", foreground="#ffffff")
            style.configure("TNotebook", background="#2d2d2d")
            style.configure("TNotebook.Tab", background="#3d3d3d", foreground="#ffffff")
        else:
            self.root.configure(bg="#f0f0f0")
            style = ttk.Style()
            style.theme_use("clam")
            style.configure(".", background="#f0f0f0", foreground="#000000")
            style.configure("TFrame", background="#f0f0f0")
            style.configure("TLabel", background="#f0f0f0", foreground="#000000")
            style.configure("TButton", background="#e0e0e0", foreground="#000000")
            style.configure("TEntry", fieldbackground="#ffffff", foreground="#000000")
            style.configure("TNotebook", background="#f0f0f0")
            style.configure("TNotebook.Tab", background="#e0e0e0", foreground="#000000")
        
        default_font = (self.font_family, self.font_size)
        self.root.option_add("*Font", default_font)
    
    def _create_menu(self):
        """Create the menu for the application."""
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)
        
        file_menu = tk.Menu(self.menu, tearoff=0)
        file_menu.add_command(label="New Document", command=self._on_new_document)
        file_menu.add_command(label="Open Document", command=self._on_open_document)
        file_menu.add_separator()
        file_menu.add_command(label="Import Documents", command=self._on_import_documents)
        file_menu.add_command(label="Export Documents", command=self._on_export_documents)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        self.menu.add_cascade(label="File", menu=file_menu)
        
        edit_menu = tk.Menu(self.menu, tearoff=0)
        edit_menu.add_command(label="Cut", command=lambda: self.root.focus_get().event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", command=lambda: self.root.focus_get().event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", command=lambda: self.root.focus_get().event_generate("<<Paste>>"))
        self.menu.add_cascade(label="Edit", menu=edit_menu)
        
        view_menu = tk.Menu(self.menu, tearoff=0)
        view_menu.add_command(label="Documents", command=lambda: self._show_panel("document"))
        view_menu.add_command(label="Relationships", command=lambda: self._show_panel("relationship"))
        view_menu.add_command(label="Search", command=lambda: self._show_panel("search"))
        view_menu.add_separator()
        view_menu.add_command(label="Refresh", command=self._on_refresh)
        self.menu.add_cascade(label="View", menu=view_menu)
        
        tools_menu = tk.Menu(self.menu, tearoff=0)
        tools_menu.add_command(label="Settings", command=lambda: self._show_panel("settings"))
        tools_menu.add_separator()
        tools_menu.add_command(label="Start Monitoring", command=self._on_start_monitoring)
        tools_menu.add_command(label="Stop Monitoring", command=self._on_stop_monitoring)
        self.menu.add_cascade(label="Tools", menu=tools_menu)
        
        help_menu = tk.Menu(self.menu, tearoff=0)
        help_menu.add_command(label="Documentation", command=self._on_documentation)
        help_menu.add_command(label="About", command=self._on_about)
        self.menu.add_cascade(label="Help", menu=help_menu)
    
    async def _create_panels(self):
        """Create the panels for the application."""
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.panels["document"] = DocumentPanel(self.notebook, self.config, self.services)
        await self.panels["document"].initialize()
        self.notebook.add(self.panels["document"].frame, text="Documents")
        
        self.panels["relationship"] = RelationshipPanel(self.notebook, self.config, self.services)
        await self.panels["relationship"].initialize()
        self.notebook.add(self.panels["relationship"].frame, text="Relationships")
        
        self.panels["search"] = SearchPanel(self.notebook, self.config, self.services)
        await self.panels["search"].initialize()
        self.notebook.add(self.panels["search"].frame, text="Search")
        
        self.panels["settings"] = SettingsPanel(self.notebook, self.config, self.services)
        await self.panels["settings"].initialize()
        self.notebook.add(self.panels["settings"].frame, text="Settings")
        
        self.panels["notification"] = NotificationPanel(self.main_frame, self.config, self.services)
        await self.panels["notification"].initialize()
        self.panels["notification"].frame.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _create_status_bar(self):
        """Create the status bar for the application."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = ttk.Progressbar(self.status_bar, mode="indeterminate", length=100)
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
    
    def _show_panel(self, panel_name: str):
        """
        Show a specific panel.
        
        Args:
            panel_name: The name of the panel to show
        """
        if panel_name in self.panels:
            panel_index = list(self.panels.keys()).index(panel_name)
            self.notebook.select(panel_index)
    
    async def start(self):
        """Start the main window."""
        if self.is_running:
            logger.warning("Main window is already running")
            return
        
        logger.info("Starting main window")
        
        self.is_running = True
        
        for panel_name, panel in self.panels.items():
            await panel.start()
        
        self.root.mainloop()
        
        logger.info("Main window started")
    
    async def stop(self):
        """Stop the main window."""
        if not self.is_running:
            logger.warning("Main window is not running")
            return
        
        logger.info("Stopping main window")
        
        self.is_running = False
        
        for panel_name, panel in self.panels.items():
            await panel.stop()
        
        if self.root:
            self.root.destroy()
        
        logger.info("Main window stopped")
    
    def _on_close(self):
        """Handle the window close event."""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            publish(EventType.APP_STOPPING)
            
            asyncio.create_task(self.stop())
    
    def _on_new_document(self):
        """Handle the new document event."""
        self._show_panel("document")
        
        if "document" in self.panels:
            self.panels["document"].create_document()
    
    def _on_open_document(self):
        """Handle the open document event."""
        file_path = filedialog.askopenfilename(
            title="Open Document",
            filetypes=[
                ("PDF Files", "*.pdf"),
                ("Word Documents", "*.docx"),
                ("Text Files", "*.txt"),
                ("All Files", "*.*"),
            ],
        )
        
        if file_path:
            self._show_panel("document")
            
            if "document" in self.panels:
                self.panels["document"].open_document(file_path)
    
    def _on_import_documents(self):
        """Handle the import documents event."""
        directory = filedialog.askdirectory(title="Import Documents")
        
        if directory:
            self._show_panel("document")
            
            if "document" in self.panels:
                self.panels["document"].import_documents(directory)
    
    def _on_export_documents(self):
        """Handle the export documents event."""
        directory = filedialog.askdirectory(title="Export Documents")
        
        if directory:
            self._show_panel("document")
            
            if "document" in self.panels:
                self.panels["document"].export_documents(directory)
    
    def _on_refresh(self):
        """Handle the refresh event."""
        current_panel = self.notebook.select()
        panel_index = self.notebook.index(current_panel)
        panel_name = list(self.panels.keys())[panel_index]
        
        if panel_name in self.panels:
            self.panels[panel_name].refresh()
    
    def _on_start_monitoring(self):
        """Handle the start monitoring event."""
        if "file_monitor" in self.services:
            asyncio.create_task(self.services["file_monitor"].start_monitoring())
            
            self.status_label.config(text="Monitoring started")
    
    def _on_stop_monitoring(self):
        """Handle the stop monitoring event."""
        if "file_monitor" in self.services:
            asyncio.create_task(self.services["file_monitor"].stop_monitoring())
            
            self.status_label.config(text="Monitoring stopped")
    
    def _on_documentation(self):
        """Handle the documentation event."""
        import webbrowser
        
        documentation_url = self.config.get("ui.documentation_url", "https://github.com/yourusername/knowledge-mesh-desktop")
        webbrowser.open(documentation_url)
    
    def _on_about(self):
        """Handle the about event."""
        messagebox.showinfo(
            "About",
            f"{self.title}\n\nVersion: {self.config.get('app.version', '1.0.0')}\n\n"
            "A desktop application for knowledge management and discovery.",
        )
    
    def _on_document_indexed(self, event):
        """
        Handle document indexed events.
        
        Args:
            event: The document indexed event
        """
        if "document" in self.panels:
            self.panels["document"].refresh()
        
        document_id = event.data.get("document_id", "")
        document_title = event.data.get("document_title", "")
        self.status_label.config(text=f"Document indexed: {document_title}")
    
    def _on_relationship_detected(self, event):
        """
        Handle relationship detected events.
        
        Args:
            event: The relationship detected event
        """
        if "relationship" in self.panels:
            self.panels["relationship"].refresh()
        
        relationship_type = event.data.get("relationship_type", "")
        source_title = event.data.get("source_title", "")
        target_title = event.data.get("target_title", "")
        self.status_label.config(text=f"Relationship detected: {source_title} -> {target_title}")
    
    def _on_proactive_interaction(self, event):
        """
        Handle proactive interaction events.
        
        Args:
            event: The proactive interaction event
        """
        if "notification" in self.panels:
            self.panels["notification"].show_notification(
                event.data.get("interaction_type", ""),
                event.data.get("content", {}),
            )
        
        interaction_type = event.data.get("interaction_type", "")
        self.status_label.config(text=f"Proactive interaction: {interaction_type}")
    
    def set_status(self, text: str):
        """
        Set the status text.
        
        Args:
            text: The status text
        """
        if self.status_label:
            self.status_label.config(text=text)
    
    def start_progress(self):
        """Start the progress bar."""
        if self.progress_bar:
            self.progress_bar.start()
    
    def stop_progress(self):
        """Stop the progress bar."""
        if self.progress_bar:
            self.progress_bar.stop()

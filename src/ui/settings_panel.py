"""
Settings Panel for the Knowledge Mesh Desktop application.

This module provides a panel for configuring the application settings.
"""

import asyncio
import json
import logging
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus

logger = logging.getLogger(__name__)


class SettingsPanel:
    """
    Panel for configuring application settings.
    
    This class provides a panel for configuring the application settings,
    including file monitoring, document processing, knowledge mesh, and UI
    settings.
    """
    
    def __init__(self, parent, config: Config, services: Dict[str, Any]):
        """
        Initialize the settings panel.
        
        Args:
            parent: The parent widget
            config: Application configuration
            services: Application services
        """
        self.parent = parent
        self.config = config
        self.services = services
        self.frame = None
        self.settings_notebook = None
        self.modified_settings = {}
        self.original_settings = {}
        self.settings_widgets = {}
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.settings = self.config.get_all()
        
        self.original_settings = self.settings.copy()
    
    async def initialize(self):
        """Initialize the settings panel."""
        logger.info("Initializing settings panel")
        
        try:
            self.frame = ttk.Frame(self.parent)
            
            self._create_toolbar()
            
            self._create_settings_notebook()
            
            self._create_general_settings()
            self._create_file_monitor_settings()
            self._create_document_processor_settings()
            self._create_knowledge_mesh_settings()
            self._create_proactive_settings()
            self._create_ui_settings()
            self._create_advanced_settings()
            
            event_bus.subscribe(EventType.CONFIG_CHANGED, self._on_config_changed)
            
            logger.info("Settings panel initialized")
        except Exception as e:
            logger.error(f"Error initializing settings panel: {e}", exc_info=True)
            raise
    
    def _create_toolbar(self):
        """Create the toolbar for the settings panel."""
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        save_button = ttk.Button(toolbar, text="Save", command=self._on_save)
        save_button.pack(side=tk.LEFT, padx=5)
        
        reset_button = ttk.Button(toolbar, text="Reset", command=self._on_reset)
        reset_button.pack(side=tk.LEFT, padx=5)
        
        import_button = ttk.Button(toolbar, text="Import", command=self._on_import)
        import_button.pack(side=tk.LEFT, padx=5)
        
        export_button = ttk.Button(toolbar, text="Export", command=self._on_export)
        export_button.pack(side=tk.LEFT, padx=5)
    
    def _create_settings_notebook(self):
        """Create the settings notebook for the settings panel."""
        self.settings_notebook = ttk.Notebook(self.frame)
        self.settings_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_general_settings(self):
        """Create the general settings tab."""
        general_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(general_frame, text="General")
        
        canvas = tk.Canvas(general_frame)
        scrollbar = ttk.Scrollbar(general_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._add_setting(
            scrollable_frame,
            "app.name",
            "Application Name",
            "The name of the application",
            "string",
            0
        )
        
        self._add_setting(
            scrollable_frame,
            "app.version",
            "Application Version",
            "The version of the application",
            "string",
            1
        )
        
        self._add_setting(
            scrollable_frame,
            "app.data_dir",
            "Data Directory",
            "The directory where application data is stored",
            "directory",
            2
        )
        
        self._add_setting(
            scrollable_frame,
            "app.log_level",
            "Log Level",
            "The log level for the application",
            "choice",
            3,
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        
        self._add_setting(
            scrollable_frame,
            "app.auto_save",
            "Auto-save",
            "Whether to automatically save changes",
            "boolean",
            4
        )
        
        self._add_setting(
            scrollable_frame,
            "app.auto_save_interval",
            "Auto-save Interval (seconds)",
            "The interval between auto-saves",
            "integer",
            5,
            min_value=1,
            max_value=3600
        )
    
    def _create_file_monitor_settings(self):
        """Create the file monitor settings tab."""
        file_monitor_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(file_monitor_frame, text="File Monitor")
        
        canvas = tk.Canvas(file_monitor_frame)
        scrollbar = ttk.Scrollbar(file_monitor_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._add_setting(
            scrollable_frame,
            "file_monitor.directories",
            "Monitored Directories",
            "The directories to monitor for file changes",
            "directory_list",
            0
        )
        
        self._add_setting(
            scrollable_frame,
            "file_monitor.extensions",
            "Monitored Extensions",
            "The file extensions to monitor",
            "string_list",
            1,
            default_value=[".pdf", ".docx", ".txt", ".md"]
        )
        
        self._add_setting(
            scrollable_frame,
            "file_monitor.recursive",
            "Recursive Monitoring",
            "Whether to monitor subdirectories recursively",
            "boolean",
            2,
            default_value=True
        )
        
        self._add_setting(
            scrollable_frame,
            "file_monitor.ignore_patterns",
            "Ignore Patterns",
            "Patterns to ignore when monitoring files",
            "string_list",
            3,
            default_value=[".*", "~*", "Thumbs.db", "desktop.ini"]
        )
        
        self._add_setting(
            scrollable_frame,
            "file_monitor.auto_process",
            "Auto-process",
            "Whether to automatically process new files",
            "boolean",
            4,
            default_value=True
        )
        
        self._add_setting(
            scrollable_frame,
            "file_monitor.polling_interval",
            "Polling Interval (seconds)",
            "The interval between file system polls",
            "integer",
            5,
            min_value=1,
            max_value=3600,
            default_value=5
        )
    
    def _create_document_processor_settings(self):
        """Create the document processor settings tab."""
        document_processor_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(document_processor_frame, text="Document Processor")
        
        canvas = tk.Canvas(document_processor_frame)
        scrollbar = ttk.Scrollbar(document_processor_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._add_setting(
            scrollable_frame,
            "document_processor.chunk_size",
            "Chunk Size",
            "The size of document chunks for processing",
            "integer",
            0,
            min_value=100,
            max_value=10000,
            default_value=1000
        )
        
        self._add_setting(
            scrollable_frame,
            "document_processor.chunk_overlap",
            "Chunk Overlap",
            "The overlap between document chunks",
            "integer",
            1,
            min_value=0,
            max_value=1000,
            default_value=200
        )
        
        self._add_setting(
            scrollable_frame,
            "document_processor.extract_metadata",
            "Extract Metadata",
            "Whether to extract metadata from documents",
            "boolean",
            2,
            default_value=True
        )
        
        self._add_setting(
            scrollable_frame,
            "document_processor.generate_summaries",
            "Generate Summaries",
            "Whether to generate summaries for documents",
            "boolean",
            3,
            default_value=True
        )
        
        self._add_setting(
            scrollable_frame,
            "document_processor.summary_length",
            "Summary Length",
            "The maximum length of document summaries",
            "integer",
            4,
            min_value=50,
            max_value=1000,
            default_value=200
        )
        
        self._add_setting(
            scrollable_frame,
            "document_processor.ocr_enabled",
            "OCR Enabled",
            "Whether to use OCR for image-based documents",
            "boolean",
            5,
            default_value=True
        )
        
        self._add_setting(
            scrollable_frame,
            "document_processor.ocr_language",
            "OCR Language",
            "The language to use for OCR",
            "string",
            6,
            default_value="eng"
        )
    
    def _create_knowledge_mesh_settings(self):
        """Create the knowledge mesh settings tab."""
        knowledge_mesh_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(knowledge_mesh_frame, text="Knowledge Mesh")
        
        canvas = tk.Canvas(knowledge_mesh_frame)
        scrollbar = ttk.Scrollbar(knowledge_mesh_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._add_setting(
            scrollable_frame,
            "knowledge_mesh.embedding_model",
            "Embedding Model",
            "The model to use for document embeddings",
            "string",
            0,
            default_value="all-MiniLM-L6-v2"
        )
        
        self._add_setting(
            scrollable_frame,
            "knowledge_mesh.similarity_threshold",
            "Similarity Threshold",
            "The threshold for document similarity",
            "float",
            1,
            min_value=0.0,
            max_value=1.0,
            default_value=0.7
        )
        
        self._add_setting(
            scrollable_frame,
            "knowledge_mesh.min_strength",
            "Minimum Relationship Strength",
            "The minimum strength for relationships",
            "float",
            2,
            min_value=0.0,
            max_value=1.0,
            default_value=0.3
        )
        
        self._add_setting(
            scrollable_frame,
            "knowledge_mesh.auto_detect",
            "Auto-detect Relationships",
            "Whether to automatically detect relationships",
            "boolean",
            3,
            default_value=True
        )
        
        self._add_setting(
            scrollable_frame,
            "knowledge_mesh.relationship_types",
            "Relationship Types",
            "The types of relationships to detect",
            "string_list",
            4,
            default_value=["SEMANTIC_SIMILARITY", "KEYWORD_OVERLAP", "TEMPORAL_PROXIMITY"]
        )
        
        self._add_setting(
            scrollable_frame,
            "knowledge_mesh.max_relationships",
            "Maximum Relationships per Document",
            "The maximum number of relationships per document",
            "integer",
            5,
            min_value=1,
            max_value=1000,
            default_value=50
        )
    
    def _create_proactive_settings(self):
        """Create the proactive settings tab."""
        proactive_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(proactive_frame, text="Proactive Assistant")
        
        canvas = tk.Canvas(proactive_frame)
        scrollbar = ttk.Scrollbar(proactive_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._add_setting(
            scrollable_frame,
            "proactive.enabled",
            "Enabled",
            "Whether the proactive assistant is enabled",
            "boolean",
            0,
            default_value=True
        )
        
        self._add_setting(
            scrollable_frame,
            "proactive.min_interaction_interval",
            "Minimum Interaction Interval (minutes)",
            "The minimum time between proactive interactions",
            "integer",
            1,
            min_value=1,
            max_value=1440,
            default_value=15
        )
        
        self._add_setting(
            scrollable_frame,
            "proactive.max_daily_interactions",
            "Maximum Daily Interactions",
            "The maximum number of proactive interactions per day",
            "integer",
            2,
            min_value=1,
            max_value=100,
            default_value=20
        )
        
        self._add_setting(
            scrollable_frame,
            "proactive.interaction_types",
            "Interaction Types",
            "The types of proactive interactions to enable",
            "string_list",
            3,
            default_value=["DOCUMENT_SUGGESTION", "RELATIONSHIP_SUGGESTION", "WORK_PATTERN_INSIGHT"]
        )
        
        self._add_setting(
            scrollable_frame,
            "proactive.work_pattern_learning",
            "Work Pattern Learning",
            "Whether to learn from user work patterns",
            "boolean",
            4,
            default_value=True
        )
        
        self._add_setting(
            scrollable_frame,
            "proactive.privacy_level",
            "Privacy Level",
            "The privacy level for proactive interactions",
            "choice",
            5,
            choices=["LOW", "MEDIUM", "HIGH"],
            default_value="MEDIUM"
        )
        
        self._add_setting(
            scrollable_frame,
            "proactive.notification_style",
            "Notification Style",
            "The style of proactive notifications",
            "choice",
            6,
            choices=["SUBTLE", "STANDARD", "PROMINENT"],
            default_value="STANDARD"
        )
    
    def _create_ui_settings(self):
        """Create the UI settings tab."""
        ui_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(ui_frame, text="UI")
        
        canvas = tk.Canvas(ui_frame)
        scrollbar = ttk.Scrollbar(ui_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._add_setting(
            scrollable_frame,
            "ui.theme",
            "Theme",
            "The UI theme",
            "choice",
            0,
            choices=["light", "dark"],
            default_value="light"
        )
        
        self._add_setting(
            scrollable_frame,
            "ui.font_family",
            "Font Family",
            "The font family for the UI",
            "string",
            1,
            default_value="Arial"
        )
        
        self._add_setting(
            scrollable_frame,
            "ui.font_size",
            "Font Size",
            "The font size for the UI",
            "integer",
            2,
            min_value=8,
            max_value=24,
            default_value=10
        )
        
        self._add_setting(
            scrollable_frame,
            "ui.width",
            "Window Width",
            "The width of the application window",
            "integer",
            3,
            min_value=800,
            max_value=3840,
            default_value=1200
        )
        
        self._add_setting(
            scrollable_frame,
            "ui.height",
            "Window Height",
            "The height of the application window",
            "integer",
            4,
            min_value=600,
            max_value=2160,
            default_value=800
        )
        
        self._add_setting(
            scrollable_frame,
            "ui.graph_width",
            "Graph Width",
            "The width of relationship graphs",
            "integer",
            5,
            min_value=400,
            max_value=2000,
            default_value=800
        )
        
        self._add_setting(
            scrollable_frame,
            "ui.graph_height",
            "Graph Height",
            "The height of relationship graphs",
            "integer",
            6,
            min_value=300,
            max_value=1500,
            default_value=600
        )
        
        self._add_setting(
            scrollable_frame,
            "ui.node_radius",
            "Node Radius",
            "The radius of nodes in relationship graphs",
            "integer",
            7,
            min_value=5,
            max_value=50,
            default_value=20
        )
        
        self._add_setting(
            scrollable_frame,
            "ui.edge_width",
            "Edge Width",
            "The width of edges in relationship graphs",
            "integer",
            8,
            min_value=1,
            max_value=10,
            default_value=2
        )
    
    def _create_advanced_settings(self):
        """Create the advanced settings tab."""
        advanced_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(advanced_frame, text="Advanced")
        
        canvas = tk.Canvas(advanced_frame)
        scrollbar = ttk.Scrollbar(advanced_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._add_setting(
            scrollable_frame,
            "advanced.debug_mode",
            "Debug Mode",
            "Whether debug mode is enabled",
            "boolean",
            0,
            default_value=False
        )
        
        self._add_setting(
            scrollable_frame,
            "advanced.cache_dir",
            "Cache Directory",
            "The directory where cache files are stored",
            "directory",
            1,
            default_value="~/.knowledge_mesh/cache"
        )
        
        self._add_setting(
            scrollable_frame,
            "advanced.cache_size",
            "Cache Size (MB)",
            "The maximum size of the cache",
            "integer",
            2,
            min_value=10,
            max_value=10000,
            default_value=1000
        )
        
        self._add_setting(
            scrollable_frame,
            "advanced.parallel_processing",
            "Parallel Processing",
            "Whether to use parallel processing",
            "boolean",
            3,
            default_value=True
        )
        
        self._add_setting(
            scrollable_frame,
            "advanced.num_workers",
            "Number of Workers",
            "The number of worker threads for parallel processing",
            "integer",
            4,
            min_value=1,
            max_value=32,
            default_value=4
        )
        
        self._add_setting(
            scrollable_frame,
            "advanced.api_timeout",
            "API Timeout (seconds)",
            "The timeout for API requests",
            "integer",
            5,
            min_value=1,
            max_value=300,
            default_value=30
        )
        
        self._add_setting(
            scrollable_frame,
            "advanced.enable_telemetry",
            "Enable Telemetry",
            "Whether to send anonymous usage data",
            "boolean",
            6,
            default_value=False
        )
    
    def _add_setting(self, parent, key, label, description, type, row, **kwargs):
        """
        Add a setting to a settings tab.
        
        Args:
            parent: The parent widget
            key: The setting key
            label: The setting label
            description: The setting description
            type: The setting type
            row: The row in the grid
            **kwargs: Additional arguments for the setting
        """
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, sticky=tk.W+tk.E, padx=5, pady=5)
        
        label_widget = ttk.Label(frame, text=label)
        label_widget.grid(row=0, column=0, sticky=tk.W)
        
        description_widget = ttk.Label(frame, text=description, foreground="gray")
        description_widget.grid(row=1, column=0, sticky=tk.W)
        
        value = self.settings.get(key)
        
        if type == "string":
            var = tk.StringVar()
            var.set(value or kwargs.get("default_value", ""))
            
            widget = ttk.Entry(frame, textvariable=var)
            widget.grid(row=0, column=1, sticky=tk.W+tk.E)
            
            self.settings_widgets[key] = (var, widget)
        
        elif type == "integer":
            var = tk.IntVar()
            var.set(value or kwargs.get("default_value", 0))
            
            min_value = kwargs.get("min_value", 0)
            max_value = kwargs.get("max_value", 100)
            
            widget = ttk.Spinbox(
                frame,
                from_=min_value,
                to=max_value,
                textvariable=var
            )
            widget.grid(row=0, column=1, sticky=tk.W+tk.E)
            
            self.settings_widgets[key] = (var, widget)
        
        elif type == "float":
            var = tk.DoubleVar()
            var.set(value or kwargs.get("default_value", 0.0))
            
            min_value = kwargs.get("min_value", 0.0)
            max_value = kwargs.get("max_value", 1.0)
            
            widget = ttk.Spinbox(
                frame,
                from_=min_value,
                to=max_value,
                increment=0.1,
                textvariable=var
            )
            widget.grid(row=0, column=1, sticky=tk.W+tk.E)
            
            self.settings_widgets[key] = (var, widget)
        
        elif type == "boolean":
            var = tk.BooleanVar()
            var.set(value if value is not None else kwargs.get("default_value", False))
            
            widget = ttk.Checkbutton(frame, variable=var)
            widget.grid(row=0, column=1, sticky=tk.W)
            
            self.settings_widgets[key] = (var, widget)
        
        elif type == "choice":
            var = tk.StringVar()
            var.set(value or kwargs.get("default_value", ""))
            
            choices = kwargs.get("choices", [])
            
            widget = ttk.Combobox(frame, textvariable=var, values=choices)
            widget.grid(row=0, column=1, sticky=tk.W+tk.E)
            
            self.settings_widgets[key] = (var, widget)
        
        elif type == "directory":
            var = tk.StringVar()
            var.set(value or kwargs.get("default_value", ""))
            
            input_frame = ttk.Frame(frame)
            input_frame.grid(row=0, column=1, sticky=tk.W+tk.E)
            
            widget = ttk.Entry(input_frame, textvariable=var)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            browse_button = ttk.Button(
                input_frame,
                text="Browse",
                command=lambda: self._browse_directory(var)
            )
            browse_button.pack(side=tk.RIGHT)
            
            self.settings_widgets[key] = (var, widget)
        
        elif type == "file":
            var = tk.StringVar()
            var.set(value or kwargs.get("default_value", ""))
            
            input_frame = ttk.Frame(frame)
            input_frame.grid(row=0, column=1, sticky=tk.W+tk.E)
            
            widget = ttk.Entry(input_frame, textvariable=var)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            browse_button = ttk.Button(
                input_frame,
                text="Browse",
                command=lambda: self._browse_file(var)
            )
            browse_button.pack(side=tk.RIGHT)
            
            self.settings_widgets[key] = (var, widget)
        
        elif type == "color":
            var = tk.StringVar()
            var.set(value or kwargs.get("default_value", "#000000"))
            
            input_frame = ttk.Frame(frame)
            input_frame.grid(row=0, column=1, sticky=tk.W+tk.E)
            
            widget = ttk.Entry(input_frame, textvariable=var)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            color_button = ttk.Button(
                input_frame,
                text="Choose",
                command=lambda: self._choose_color(var)
            )
            color_button.pack(side=tk.RIGHT)
            
            self.settings_widgets[key] = (var, widget)
        
        elif type == "string_list":
            var = tk.StringVar()
            
            if value:
                var.set(", ".join(value))
            else:
                default_value = kwargs.get("default_value", [])
                var.set(", ".join(default_value))
            
            widget = ttk.Entry(frame, textvariable=var)
            widget.grid(row=0, column=1, sticky=tk.W+tk.E)
            
            self.settings_widgets[key] = (var, widget)
        
        elif type == "directory_list":
            var = tk.StringVar()
            
            if value:
                var.set(", ".join(value))
            else:
                default_value = kwargs.get("default_value", [])
                var.set(", ".join(default_value))
            
            input_frame = ttk.Frame(frame)
            input_frame.grid(row=0, column=1, sticky=tk.W+tk.E)
            
            widget = ttk.Entry(input_frame, textvariable=var)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            browse_button = ttk.Button(
                input_frame,
                text="Add",
                command=lambda: self._add_directory(var)
            )
            browse_button.pack(side=tk.RIGHT)
            
            self.settings_widgets[key] = (var, widget)
    
    def _browse_directory(self, var):
        """
        Browse for a directory.
        
        Args:
            var: The variable to set
        """
        directory = filedialog.askdirectory()
        if directory:
            var.set(directory)
    
    def _browse_file(self, var):
        """
        Browse for a file.
        
        Args:
            var: The variable to set
        """
        file = filedialog.askopenfilename()
        if file:
            var.set(file)
    
    def _choose_color(self, var):
        """
        Choose a color.
        
        Args:
            var: The variable to set
        """
        color = colorchooser.askcolor(var.get())[1]
        if color:
            var.set(color)
    
    def _add_directory(self, var):
        """
        Add a directory to a list.
        
        Args:
            var: The variable to set
        """
        directory = filedialog.askdirectory()
        if directory:
            current = var.get()
            if current:
                var.set(f"{current}, {directory}")
            else:
                var.set(directory)
    
    async def start(self):
        """Start the settings panel."""
        logger.info("Starting settings panel")
        
        logger.info("Settings panel started")
    
    async def stop(self):
        """Stop the settings panel."""
        logger.info("Stopping settings panel")
        
        event_bus.unsubscribe(EventType.CONFIG_CHANGED, self._on_config_changed)
        
        logger.info("Settings panel stopped")
    
    def _on_save(self):
        """Handle the save button click."""
        try:
            for key, (var, widget) in self.settings_widgets.items():
                value = var.get()
                
                if key.endswith("_list") and isinstance(value, str):
                    value = [item.strip() for item in value.split(",") if item.strip()]
                
                self.modified_settings[key] = value
            
            self.config.update(self.modified_settings)
            
            publish(EventType.CONFIG_CHANGED, {"settings": self.modified_settings})
            
            messagebox.showinfo("Settings", "Settings saved successfully")
            
            self.modified_settings = {}
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error saving settings: {e}")
    
    def _on_reset(self):
        """Handle the reset button click."""
        try:
            if not messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to their default values?"):
                return
            
            self.config.reset()
            
            self._load_config()
            
            for key, (var, widget) in self.settings_widgets.items():
                value = self.settings.get(key)
                
                if key.endswith("_list") and isinstance(value, list):
                    var.set(", ".join(value))
                else:
                    var.set(value)
            
            publish(EventType.CONFIG_CHANGED, {"settings": self.settings})
            
            messagebox.showinfo("Settings", "Settings reset successfully")
        except Exception as e:
            logger.error(f"Error resetting settings: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error resetting settings: {e}")
    
    def _on_import(self):
        """Handle the import button click."""
        try:
            file = filedialog.askopenfilename(
                title="Import Settings",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            
            if not file:
                return
            
            with open(file, "r") as f:
                settings = json.load(f)
            
            self.config.update(settings)
            
            self._load_config()
            
            for key, (var, widget) in self.settings_widgets.items():
                value = self.settings.get(key)
                
                if key.endswith("_list") and isinstance(value, list):
                    var.set(", ".join(value))
                else:
                    var.set(value)
            
            publish(EventType.CONFIG_CHANGED, {"settings": self.settings})
            
            messagebox.showinfo("Settings", "Settings imported successfully")
        except Exception as e:
            logger.error(f"Error importing settings: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error importing settings: {e}")
    
    def _on_export(self):
        """Handle the export button click."""
        try:
            file = filedialog.asksaveasfilename(
                title="Export Settings",
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            
            if not file:
                return
            
            with open(file, "w") as f:
                json.dump(self.settings, f, indent=4)
            
            messagebox.showinfo("Settings", "Settings exported successfully")
        except Exception as e:
            logger.error(f"Error exporting settings: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error exporting settings: {e}")
    
    def _on_config_changed(self, event):
        """
        Handle the config changed event.
        
        Args:
            event: The config changed event
        """
        self._load_config()
        
        for key, (var, widget) in self.settings_widgets.items():
            value = self.settings.get(key)
            
            if key.endswith("_list") and isinstance(value, list):
                var.set(", ".join(value))
            else:
                var.set(value)
    
    def refresh(self):
        """Refresh the settings panel."""
        self._load_config()
        
        for key, (var, widget) in self.settings_widgets.items():
            value = self.settings.get(key)
            
            if key.endswith("_list") and isinstance(value, list):
                var.set(", ".join(value))
            else:
                var.set(value)

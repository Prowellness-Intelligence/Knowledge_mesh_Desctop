"""
Document Panel for the Knowledge Mesh Desktop application.

This module provides a panel for displaying and managing documents in the
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
from ..models.document import Document, DocumentType

logger = logging.getLogger(__name__)


class DocumentPanel:
    """
    Panel for displaying and managing documents.
    
    This class provides a panel for displaying and managing documents in the
    application.
    """
    
    def __init__(self, parent, config: Config, services: Dict[str, Any]):
        """
        Initialize the document panel.
        
        Args:
            parent: The parent widget
            config: Application configuration
            services: Application services
        """
        self.parent = parent
        self.config = config
        self.services = services
        self.frame = None
        self.documents = []
        self.selected_document = None
        self.document_list = None
        self.document_details = None
        self.search_entry = None
        self.filter_var = None
        self.sort_var = None
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from the config object."""
        self.monitored_directories = self.config.get("file_monitor.directories", [])
        self.monitored_extensions = self.config.get("file_monitor.extensions", [])
        self.thumbnail_size = self.config.get("ui.thumbnail_size", 100)
        self.preview_size = self.config.get("ui.preview_size", 300)
        self.max_documents = self.config.get("ui.max_documents", 1000)
    
    async def initialize(self):
        """Initialize the document panel."""
        logger.info("Initializing document panel")
        
        try:
            self.frame = ttk.Frame(self.parent)
            
            self._create_toolbar()
            
            self._create_document_list()
            
            self._create_document_details()
            
            event_bus.subscribe(EventType.DOCUMENT_INDEXED, self._on_document_indexed)
            event_bus.subscribe(EventType.DOCUMENT_DELETED, self._on_document_deleted)
            
            logger.info("Document panel initialized")
        except Exception as e:
            logger.error(f"Error initializing document panel: {e}", exc_info=True)
            raise
    
    def _create_toolbar(self):
        """Create the toolbar for the document panel."""
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        add_button = ttk.Button(toolbar, text="Add Document", command=self._on_add_document)
        add_button.pack(side=tk.LEFT, padx=5)
        
        import_button = ttk.Button(toolbar, text="Import Documents", command=self._on_import_documents)
        import_button.pack(side=tk.LEFT, padx=5)
        
        refresh_button = ttk.Button(toolbar, text="Refresh", command=self.refresh)
        refresh_button.pack(side=tk.LEFT, padx=5)
        
        search_label = ttk.Label(toolbar, text="Search:")
        search_label.pack(side=tk.LEFT, padx=5)
        
        self.search_entry = ttk.Entry(toolbar, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", self._on_search)
        
        search_button = ttk.Button(toolbar, text="Search", command=self._on_search)
        search_button.pack(side=tk.LEFT, padx=5)
        
        filter_label = ttk.Label(toolbar, text="Filter:")
        filter_label.pack(side=tk.LEFT, padx=5)
        
        self.filter_var = tk.StringVar()
        self.filter_var.set("All")
        
        filter_dropdown = ttk.Combobox(toolbar, textvariable=self.filter_var, values=["All", "PDF", "Word", "Text", "Image"])
        filter_dropdown.pack(side=tk.LEFT, padx=5)
        filter_dropdown.bind("<<ComboboxSelected>>", self._on_filter_changed)
        
        sort_label = ttk.Label(toolbar, text="Sort:")
        sort_label.pack(side=tk.LEFT, padx=5)
        
        self.sort_var = tk.StringVar()
        self.sort_var.set("Date (Newest)")
        
        sort_dropdown = ttk.Combobox(toolbar, textvariable=self.sort_var, values=["Date (Newest)", "Date (Oldest)", "Name (A-Z)", "Name (Z-A)", "Size (Largest)", "Size (Smallest)"])
        sort_dropdown.pack(side=tk.LEFT, padx=5)
        sort_dropdown.bind("<<ComboboxSelected>>", self._on_sort_changed)
    
    def _create_document_list(self):
        """Create the document list for the document panel."""
        list_frame = ttk.LabelFrame(self.frame, text="Documents")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.document_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, selectmode=tk.SINGLE)
        self.document_list.pack(fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.document_list.yview)
        
        self.document_list.bind("<<ListboxSelect>>", self._on_document_selected)
    
    def _create_document_details(self):
        """Create the document details for the document panel."""
        details_frame = ttk.LabelFrame(self.frame, text="Document Details")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.RIGHT)
        
        self.document_details = ttk.Notebook(details_frame)
        self.document_details.pack(fill=tk.BOTH, expand=True)
        
        info_frame = ttk.Frame(self.document_details)
        self.document_details.add(info_frame, text="Info")
        
        content_frame = ttk.Frame(self.document_details)
        self.document_details.add(content_frame, text="Content")
        
        relationships_frame = ttk.Frame(self.document_details)
        self.document_details.add(relationships_frame, text="Relationships")
        
        preview_frame = ttk.Frame(self.document_details)
        self.document_details.add(preview_frame, text="Preview")
    
    async def start(self):
        """Start the document panel."""
        logger.info("Starting document panel")
        
        await self._load_documents()
        
        logger.info("Document panel started")
    
    async def stop(self):
        """Stop the document panel."""
        logger.info("Stopping document panel")
        
        event_bus.unsubscribe(EventType.DOCUMENT_INDEXED, self._on_document_indexed)
        event_bus.unsubscribe(EventType.DOCUMENT_DELETED, self._on_document_deleted)
        
        logger.info("Document panel stopped")
    
    async def _load_documents(self):
        """Load the documents from the document processor service."""
        try:
            self.document_list.delete(0, tk.END)
            self.documents = []
            
            if "document_processor" in self.services:
                self.documents = await self.services["document_processor"].get_documents()
            
            self._sort_documents()
            
            filtered_documents = self._filter_documents()
            
            for document in filtered_documents:
                self.document_list.insert(tk.END, document.title)
            
            self._update_document_count()
        except Exception as e:
            logger.error(f"Error loading documents: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error loading documents: {e}")
    
    def _sort_documents(self):
        """Sort the documents based on the sort dropdown."""
        sort_option = self.sort_var.get()
        
        if sort_option == "Date (Newest)":
            self.documents.sort(key=lambda doc: doc.created_at or doc.updated_at or "", reverse=True)
        elif sort_option == "Date (Oldest)":
            self.documents.sort(key=lambda doc: doc.created_at or doc.updated_at or "")
        elif sort_option == "Name (A-Z)":
            self.documents.sort(key=lambda doc: doc.title.lower())
        elif sort_option == "Name (Z-A)":
            self.documents.sort(key=lambda doc: doc.title.lower(), reverse=True)
        elif sort_option == "Size (Largest)":
            self.documents.sort(key=lambda doc: doc.size or 0, reverse=True)
        elif sort_option == "Size (Smallest)":
            self.documents.sort(key=lambda doc: doc.size or 0)
    
    def _filter_documents(self) -> List[Document]:
        """
        Filter the documents based on the filter dropdown and search entry.
        
        Returns:
            A list of filtered documents
        """
        filter_option = self.filter_var.get()
        search_text = self.search_entry.get().lower()
        
        filtered_documents = []
        
        for document in self.documents:
            if filter_option == "All" or filter_option == document.file_type.name:
                if not search_text or search_text in document.title.lower() or search_text in (document.content or "").lower():
                    filtered_documents.append(document)
        
        return filtered_documents
    
    def _update_document_count(self):
        """Update the document count in the document list frame."""
        list_frame = self.document_list.master.master
        list_frame.config(text=f"Documents ({self.document_list.size()})")
    
    def _on_document_selected(self, event):
        """
        Handle the document selection event.
        
        Args:
            event: The document selection event
        """
        selection = self.document_list.curselection()
        if selection:
            index = selection[0]
            filtered_documents = self._filter_documents()
            if 0 <= index < len(filtered_documents):
                self.selected_document = filtered_documents[index]
                self._update_document_details()
    
    def _update_document_details(self):
        """Update the document details based on the selected document."""
        if not self.selected_document:
            return
        
        info_frame = self.document_details.nametowidget(self.document_details.tabs()[0])
        for widget in info_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(info_frame, text="Title:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=self.selected_document.title).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Type:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=self.selected_document.file_type.name).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Size:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=f"{self.selected_document.size or 0} bytes").grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Created:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=str(self.selected_document.created_at or "")).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Updated:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=str(self.selected_document.updated_at or "")).grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Path:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=self.selected_document.file_path or "").grid(row=5, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Word Count:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=str(self.selected_document.word_count or 0)).grid(row=6, column=1, sticky=tk.W, padx=5, pady=2)
        
        content_frame = self.document_details.nametowidget(self.document_details.tabs()[1])
        for widget in content_frame.winfo_children():
            widget.destroy()
        
        content_text = tk.Text(content_frame, wrap=tk.WORD)
        content_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(content_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        content_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=content_text.yview)
        
        content_text.insert(tk.END, self.selected_document.content or "")
        content_text.config(state=tk.DISABLED)
        
        relationships_frame = self.document_details.nametowidget(self.document_details.tabs()[2])
        for widget in relationships_frame.winfo_children():
            widget.destroy()
        
        relationships_listbox = tk.Listbox(relationships_frame)
        relationships_listbox.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(relationships_listbox)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        relationships_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=relationships_listbox.yview)
        
        if "knowledge_mesh" in self.services:
            asyncio.create_task(self._load_relationships(relationships_listbox))
        
        preview_frame = self.document_details.nametowidget(self.document_details.tabs()[3])
        for widget in preview_frame.winfo_children():
            widget.destroy()
        
        preview_label = ttk.Label(preview_frame, text="Preview not available")
        preview_label.pack(fill=tk.BOTH, expand=True)
        
        if self.selected_document.file_path and os.path.exists(self.selected_document.file_path):
            if self.selected_document.file_type == DocumentType.PDF:
                preview_label.config(text="PDF preview not implemented yet")
            elif self.selected_document.file_type == DocumentType.IMAGE:
                preview_label.config(text="Image preview not implemented yet")
            else:
                preview_label.config(text="Preview not available for this file type")
    
    async def _load_relationships(self, listbox):
        """
        Load the relationships for the selected document.
        
        Args:
            listbox: The listbox to add the relationships to
        """
        try:
            listbox.delete(0, tk.END)
            
            relationships = await self.services["knowledge_mesh"].get_relationships(self.selected_document.id)
            
            for relationship in relationships:
                target_document = None
                for document in self.documents:
                    if document.id == relationship.target_id:
                        target_document = document
                        break
                
                if target_document:
                    listbox.insert(tk.END, f"{relationship.type.name} -> {target_document.title} ({relationship.strength:.2f})")
        except Exception as e:
            logger.error(f"Error loading relationships: {e}", exc_info=True)
            listbox.insert(tk.END, f"Error loading relationships: {e}")
    
    def _on_add_document(self):
        """Handle the add document button click."""
        file_path = filedialog.askopenfilename(
            title="Add Document",
            filetypes=[
                ("PDF Files", "*.pdf"),
                ("Word Documents", "*.docx"),
                ("Text Files", "*.txt"),
                ("Image Files", "*.jpg;*.jpeg;*.png;*.gif"),
                ("All Files", "*.*"),
            ],
        )
        
        if file_path:
            self.add_document(file_path)
    
    def _on_import_documents(self):
        """Handle the import documents button click."""
        directory = filedialog.askdirectory(title="Import Documents")
        
        if directory:
            self.import_documents(directory)
    
    def _on_search(self, event=None):
        """
        Handle the search button click or Enter key press.
        
        Args:
            event: The event that triggered the search
        """
        asyncio.create_task(self._load_documents())
    
    def _on_filter_changed(self, event):
        """
        Handle the filter dropdown selection change.
        
        Args:
            event: The filter dropdown selection change event
        """
        asyncio.create_task(self._load_documents())
    
    def _on_sort_changed(self, event):
        """
        Handle the sort dropdown selection change.
        
        Args:
            event: The sort dropdown selection change event
        """
        asyncio.create_task(self._load_documents())
    
    def _on_document_indexed(self, event):
        """
        Handle the document indexed event.
        
        Args:
            event: The document indexed event
        """
        asyncio.create_task(self._load_documents())
    
    def _on_document_deleted(self, event):
        """
        Handle the document deleted event.
        
        Args:
            event: The document deleted event
        """
        asyncio.create_task(self._load_documents())
    
    def refresh(self):
        """Refresh the document panel."""
        asyncio.create_task(self._load_documents())
    
    def add_document(self, file_path: str):
        """
        Add a document to the system.
        
        Args:
            file_path: The path to the document file
        """
        try:
            if "document_processor" not in self.services:
                messagebox.showerror("Error", "Document processor service not available")
                return
            
            asyncio.create_task(self._process_document(file_path))
        except Exception as e:
            logger.error(f"Error adding document: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error adding document: {e}")
    
    async def _process_document(self, file_path: str):
        """
        Process a document.
        
        Args:
            file_path: The path to the document file
        """
        try:
            document = await self.services["document_processor"].process_document(file_path)
            
            await self._load_documents()
            
            for i, doc in enumerate(self._filter_documents()):
                if doc.id == document.id:
                    self.document_list.selection_clear(0, tk.END)
                    self.document_list.selection_set(i)
                    self.document_list.see(i)
                    self._on_document_selected(None)
                    break
        except Exception as e:
            logger.error(f"Error processing document: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error processing document: {e}")
    
    def import_documents(self, directory: str):
        """
        Import documents from a directory.
        
        Args:
            directory: The directory to import documents from
        """
        try:
            if "document_processor" not in self.services:
                messagebox.showerror("Error", "Document processor service not available")
                return
            
            asyncio.create_task(self._import_documents(directory))
        except Exception as e:
            logger.error(f"Error importing documents: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error importing documents: {e}")
    
    async def _import_documents(self, directory: str):
        """
        Import documents from a directory.
        
        Args:
            directory: The directory to import documents from
        """
        try:
            documents = await self.services["document_processor"].import_documents(directory)
            
            await self._load_documents()
            
            messagebox.showinfo("Import Documents", f"Imported {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error importing documents: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error importing documents: {e}")
    
    def export_documents(self, directory: str):
        """
        Export documents to a directory.
        
        Args:
            directory: The directory to export documents to
        """
        try:
            if "document_processor" not in self.services:
                messagebox.showerror("Error", "Document processor service not available")
                return
            
            asyncio.create_task(self._export_documents(directory))
        except Exception as e:
            logger.error(f"Error exporting documents: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error exporting documents: {e}")
    
    async def _export_documents(self, directory: str):
        """
        Export documents to a directory.
        
        Args:
            directory: The directory to export documents to
        """
        try:
            count = await self.services["document_processor"].export_documents(directory)
            
            messagebox.showinfo("Export Documents", f"Exported {count} documents")
        except Exception as e:
            logger.error(f"Error exporting documents: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error exporting documents: {e}")
    
    def create_document(self):
        """Create a new document."""
        messagebox.showinfo("Create Document", "Document creation not implemented yet")
    
    def open_document(self, file_path: str):
        """
        Open a document.
        
        Args:
            file_path: The path to the document file
        """
        self.add_document(file_path)

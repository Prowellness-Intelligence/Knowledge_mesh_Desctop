"""
Configuration management for the Knowledge Mesh Desktop application.

This module handles loading, validating, and accessing configuration settings
from various sources (default config, user config, environment variables).
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union

DEFAULT_CONFIG = {
    "app": {
        "name": "Knowledge Mesh Desktop",
        "version": "0.1.0",
        "log_level": "INFO",
        "data_dir": "~/knowledge_mesh_data",
        "max_concurrent_tasks": 4,
    },
    
    "file_monitor": {
        "directories": ["~/Documents", "~/Downloads"],
        "extensions": [".pdf", ".docx", ".doc", ".txt", ".md", ".pptx", ".xlsx", ".csv"],
        "ignore_patterns": ["~$*", ".*", "*.tmp"],
        "scan_interval_seconds": 60,
    },
    
    "document_processor": {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "max_file_size_mb": 50,
        "extract_images": True,
        "ocr_enabled": True,
        "summarization_enabled": True,
        "max_summary_length": 500,
    },
    
    "vector_store": {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "collection_name": "knowledge_mesh",
        "persist_directory": "~/knowledge_mesh_data/vector_db",
        "distance_metric": "cosine",
    },
    
    "knowledge_mesh": {
        "min_similarity": 0.7,
        "max_similar_docs": 20,
        "relationship_types": ["similar", "related", "cites", "temporal_sequence"],
        "maintenance_interval_seconds": 3600,
    },
    
    "proactive": {
        "enabled": True,
        "suggestion_check_interval_seconds": 30,
        "min_suggestion_interval_minutes": 15,
        "max_suggestions": 3,
        "min_suggestion_relevance": 0.7,
        "work_pattern_analysis_enabled": True,
        "pattern_analysis_interval_seconds": 3600,
    },
    
    "calendar": {
        "enabled": True,
        "providers": ["google", "outlook", "local"],
        "sync_interval_minutes": 15,
        "look_ahead_days": 7,
    },
    
    "email": {
        "enabled": True,
        "providers": ["gmail", "outlook"],
        "sync_interval_minutes": 15,
        "max_emails_per_sync": 100,
        "process_attachments": True,
    },
    
    "voice": {
        "enabled": True,
        "wake_word": "mesh",
        "voice_id": "en-US-Neural2-F",
        "speech_recognition_engine": "whisper",
        "text_to_speech_engine": "pyttsx3",
    },
    
    "ui": {
        "theme": "light",
        "font_size": "medium",
        "enable_animations": True,
        "sidebar_width": 250,
        "document_preview_height": 400,
        "mesh_visualization_type": "force_directed",
    },
}


class Config:
    """Configuration manager for the Knowledge Mesh Desktop application."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Optional directory containing configuration files.
                        Defaults to the config directory in the project root.
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path(__file__).parent.parent.parent / "config"
        
        self.config = DEFAULT_CONFIG.copy()
        
        self._load_config()
        
        self._load_env_vars()
        
        self._expand_paths()

    def _load_config(self):
        """Load configuration from YAML files."""
        default_config_path = self.config_dir / "default.yaml"
        if default_config_path.exists():
            with open(default_config_path, "r") as f:
                default_config = yaml.safe_load(f)
                if default_config:
                    self._merge_config(default_config)
        
        user_config_path = self.config_dir / "user.yaml"
        if user_config_path.exists():
            with open(user_config_path, "r") as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    self._merge_config(user_config)

    def _load_env_vars(self):
        """Override configuration with environment variables."""
        for env_var, value in os.environ.items():
            if env_var.startswith("KM_"):
                parts = env_var[3:].lower().split("_", 1)
                if len(parts) == 2:
                    section, key = parts
                    if section in self.config and key in self.config[section]:
                        default_value = self.config[section][key]
                        if isinstance(default_value, bool):
                            value = value.lower() in ("true", "yes", "1")
                        elif isinstance(default_value, int):
                            value = int(value)
                        elif isinstance(default_value, float):
                            value = float(value)
                        
                        self.config[section][key] = value

    def _merge_config(self, config: Dict[str, Any]):
        """
        Merge configuration dictionary into the current configuration.
        
        Args:
            config: Configuration dictionary to merge
        """
        for section, section_config in config.items():
            if section in self.config:
                if isinstance(section_config, dict) and isinstance(self.config[section], dict):
                    self.config[section].update(section_config)
                else:
                    self.config[section] = section_config
            else:
                self.config[section] = section_config

    def _expand_paths(self):
        """Expand paths in configuration."""
        data_dir = self.config["app"]["data_dir"]
        self.config["app"]["data_dir"] = os.path.expanduser(data_dir)
        
        vector_dir = self.config["vector_store"]["persist_directory"]
        self.config["vector_store"]["persist_directory"] = os.path.expanduser(vector_dir)
        
        self.config["file_monitor"]["directories"] = [
            os.path.expanduser(d) for d in self.config["file_monitor"]["directories"]
        ]

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key in the format "section.key"
            default: Default value to return if the key is not found
            
        Returns:
            Configuration value or default
        """
        parts = key.split(".", 1)
        if len(parts) != 2:
            return default
        
        section, key = parts
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        
        return default

    def set(self, key: str, value: Any):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key in the format "section.key"
            value: Value to set
        """
        parts = key.split(".", 1)
        if len(parts) != 2:
            return
        
        section, key = parts
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value

    def save_user_config(self):
        """Save user configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        user_config_path = self.config_dir / "user.yaml"
        with open(user_config_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get a configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Section configuration dictionary
        """
        return self.config.get(section, {})

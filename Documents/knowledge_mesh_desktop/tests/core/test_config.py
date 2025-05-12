"""
Tests for the configuration system.

This module contains tests for the configuration system.
"""

import os
import json
import tempfile
import pytest
from pathlib import Path

from src.core.config import Config


@pytest.fixture
def temp_config_file():
    """Create a temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
        json.dump(
            {
                "app": {
                    "name": "Test App",
                    "version": "1.0.0",
                    "data_dir": "~/test_data",
                },
                "file_monitor": {
                    "directories": ["~/Documents", "~/Downloads"],
                    "extensions": [".pdf", ".docx", ".txt"],
                    "recursive": True,
                },
            },
            f,
        )
        f.flush()
        yield f.name
    
    os.unlink(f.name)


def test_config_load(temp_config_file):
    """Test loading configuration from a file."""
    config = Config(config_dir=str(Path(temp_config_file).parent))
    
    assert config.get("app.name") == "Test App"
    assert config.get("app.version") == "1.0.0"
    assert config.get("app.data_dir") == "~/test_data"
    assert config.get("file_monitor.directories") == ["~/Documents", "~/Downloads"]
    assert config.get("file_monitor.extensions") == [".pdf", ".docx", ".txt"]
    assert config.get("file_monitor.recursive") is True


def test_config_get_default():
    """Test getting a configuration value with a default."""
    config = Config()
    
    assert config.get("app.name", "Default App") == "Default App"
    assert config.get("app.version", "0.1.0") == "0.1.0"
    assert config.get("app.data_dir", "~/data") == "~/data"


def test_config_set():
    """Test setting a configuration value."""
    config = Config()
    
    config.set("app.name", "New App")
    config.set("app.version", "2.0.0")
    config.set("app.data_dir", "~/new_data")
    
    assert config.get("app.name") == "New App"
    assert config.get("app.version") == "2.0.0"
    assert config.get("app.data_dir") == "~/new_data"


def test_config_update():
    """Test updating multiple configuration values."""
    config = Config()
    
    config.update({
        "app.name": "Updated App",
        "app.version": "3.0.0",
        "app.data_dir": "~/updated_data",
    })
    
    assert config.get("app.name") == "Updated App"
    assert config.get("app.version") == "3.0.0"
    assert config.get("app.data_dir") == "~/updated_data"


def test_config_reset():
    """Test resetting configuration to defaults."""
    config = Config()
    
    config.set("app.name", "Custom App")
    config.set("app.version", "4.0.0")
    
    assert config.get("app.name") == "Custom App"
    assert config.get("app.version") == "4.0.0"
    
    config.reset()
    
    assert config.get("app.name") != "Custom App"
    assert config.get("app.version") != "4.0.0"


def test_config_get_all():
    """Test getting all configuration values."""
    config = Config()
    
    config.set("app.name", "All App")
    config.set("app.version", "5.0.0")
    config.set("app.data_dir", "~/all_data")
    
    all_config = config.get_all()
    
    assert all_config["app"]["name"] == "All App"
    assert all_config["app"]["version"] == "5.0.0"
    assert all_config["app"]["data_dir"] == "~/all_data"

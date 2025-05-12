"""
Test file for the Multi-modal Knowledge Integration of the Knowledge Mesh Desktop application.

This module provides tests for the Media models and Media Processor Service.
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.core.config import Config
from src.core.events import EventType, Event, event_bus
from src.models.media import Media, Image, Audio, Video, MediaType, MediaFormat
from src.services.media_processor import MediaProcessorService


class TestMediaModels(unittest.TestCase):
    """Test the Media models."""
    
    def setUp(self):
        """Set up the test environment."""
        os.makedirs("./test_data", exist_ok=True)
        
        self.image_path = "./test_data/test_image.jpg"
        self.audio_path = "./test_data/test_audio.mp3"
        self.video_path = "./test_data/test_video.mp4"
        
        for path in [self.image_path, self.audio_path, self.video_path]:
            if not os.path.exists(path):
                with open(path, "wb") as f:
                    f.write(b"test")
    
    def tearDown(self):
        """Clean up the test environment."""
        import shutil
        if os.path.exists("./test_data"):
            shutil.rmtree("./test_data")
    
    def test_media_format_from_extension(self):
        """Test getting media format from extension."""
        self.assertEqual(MediaFormat.from_extension("jpg"), MediaFormat.JPG)
        self.assertEqual(MediaFormat.from_extension("jpeg"), MediaFormat.JPG)
        self.assertEqual(MediaFormat.from_extension("png"), MediaFormat.PNG)
        self.assertEqual(MediaFormat.from_extension("mp3"), MediaFormat.MP3)
        self.assertEqual(MediaFormat.from_extension("wav"), MediaFormat.WAV)
        self.assertEqual(MediaFormat.from_extension("mp4"), MediaFormat.MP4)
        self.assertEqual(MediaFormat.from_extension("avi"), MediaFormat.AVI)
        self.assertEqual(MediaFormat.from_extension("unknown"), MediaFormat.UNKNOWN)
    
    def test_media_format_properties(self):
        """Test media format properties."""
        self.assertEqual(MediaFormat.JPG.media_type, MediaType.IMAGE)
        self.assertEqual(MediaFormat.PNG.media_type, MediaType.IMAGE)
        self.assertEqual(MediaFormat.MP3.media_type, MediaType.AUDIO)
        self.assertEqual(MediaFormat.WAV.media_type, MediaType.AUDIO)
        self.assertEqual(MediaFormat.MP4.media_type, MediaType.VIDEO)
        self.assertEqual(MediaFormat.AVI.media_type, MediaType.VIDEO)
        
        self.assertEqual(MediaFormat.JPG.extension, "jpg")
        self.assertEqual(MediaFormat.PNG.extension, "png")
        self.assertEqual(MediaFormat.MP3.extension, "mp3")
        self.assertEqual(MediaFormat.WAV.extension, "wav")
        self.assertEqual(MediaFormat.MP4.extension, "mp4")
        self.assertEqual(MediaFormat.AVI.extension, "avi")
    
    def test_media_from_file(self):
        """Test creating media from file."""
        media = Media.from_file(self.image_path)
        self.assertEqual(media.media_type, MediaType.IMAGE)
        self.assertEqual(media.media_format, MediaFormat.JPG)
        
        media = Media.from_file(self.audio_path)
        self.assertEqual(media.media_type, MediaType.AUDIO)
        self.assertEqual(media.media_format, MediaFormat.MP3)
        
        media = Media.from_file(self.video_path)
        self.assertEqual(media.media_type, MediaType.VIDEO)
        self.assertEqual(media.media_format, MediaFormat.MP4)
    
    def test_media_to_dict(self):
        """Test converting media to dictionary."""
        media = Media.from_file(self.image_path)
        media_dict = media.to_dict()
        
        self.assertEqual(media_dict["id"], Path(self.image_path).stem)
        self.assertEqual(media_dict["path"], self.image_path)
        self.assertEqual(media_dict["media_type"], MediaType.IMAGE.name)
        self.assertEqual(media_dict["media_format"], MediaFormat.JPG.name)
        self.assertIn("created_at", media_dict)
        self.assertIn("modified_at", media_dict)
        self.assertIn("size_bytes", media_dict)
        self.assertIn("metadata", media_dict)
        self.assertIn("has_embedding", media_dict)
    
    def test_media_from_dict(self):
        """Test creating media from dictionary."""
        media_dict = {
            "id": "test_media",
            "path": self.image_path,
            "media_type": MediaType.IMAGE.name,
            "media_format": MediaFormat.JPG.name,
            "created_at": datetime.utcnow().isoformat(),
            "modified_at": datetime.utcnow().isoformat(),
            "size_bytes": 100,
            "metadata": {"test": "data"},
        }
        
        media = Media.from_dict(media_dict)
        
        self.assertEqual(media.id, "test_media")
        self.assertEqual(media.path, self.image_path)
        self.assertEqual(media.media_type, MediaType.IMAGE)
        self.assertEqual(media.media_format, MediaFormat.JPG)
        self.assertEqual(media.metadata, {"test": "data"})
    
    def test_image_from_file(self):
        """Test creating image from file."""
        image = Image.from_file(self.image_path)
        
        self.assertEqual(image.media_type, MediaType.IMAGE)
        self.assertEqual(image.media_format, MediaFormat.JPG)
        
        with self.assertRaises(ValueError):
            Image.from_file(self.audio_path)
    
    def test_audio_from_file(self):
        """Test creating audio from file."""
        audio = Audio.from_file(self.audio_path)
        
        self.assertEqual(audio.media_type, MediaType.AUDIO)
        self.assertEqual(audio.media_format, MediaFormat.MP3)
        
        with self.assertRaises(ValueError):
            Audio.from_file(self.image_path)
    
    def test_video_from_file(self):
        """Test creating video from file."""
        video = Video.from_file(self.video_path)
        
        self.assertEqual(video.media_type, MediaType.VIDEO)
        self.assertEqual(video.media_format, MediaFormat.MP4)
        
        with self.assertRaises(ValueError):
            Video.from_file(self.image_path)


class TestMediaProcessorService(unittest.TestCase):
    """Test the Media Processor Service."""
    
    def setUp(self):
        """Set up the test environment."""
        self.config = Config({
            "app.data_dir": "./test_data",
            "media_processor.enabled": True,
        })
        
        self.services = {
            "vector_store": MagicMock(),
            "document_processor": MagicMock(),
            "knowledge_mesh": MagicMock(),
        }
        
        self.service = MediaProcessorService(self.config, self.services)
        
        os.makedirs("./test_data/media", exist_ok=True)
        
        self.image_path = "./test_data/test_image.jpg"
        self.audio_path = "./test_data/test_audio.mp3"
        self.video_path = "./test_data/test_video.mp4"
        
        for path in [self.image_path, self.audio_path, self.video_path]:
            if not os.path.exists(path):
                with open(path, "wb") as f:
                    f.write(b"test")
    
    def tearDown(self):
        """Clean up the test environment."""
        import shutil
        if os.path.exists("./test_data"):
            shutil.rmtree("./test_data")
    
    def test_initialization(self):
        """Test service initialization."""
        self.assertEqual(self.service.config, self.config)
        self.assertEqual(self.service.services, self.services)
        self.assertFalse(self.service.is_running)
        self.assertEqual(self.service.data_dir, Path("./test_data"))
        self.assertEqual(self.service.media_dir, Path("./test_data/media"))
        self.assertTrue(self.service.media_dir.exists())
        
        self.assertIn(MediaType.IMAGE, self.service.processors)
        self.assertIn(MediaType.AUDIO, self.service.processors)
        self.assertIn(MediaType.VIDEO, self.service.processors)
        
        self.assertIn(MediaFormat.JPG, self.service.format_handlers)
        self.assertIn(MediaFormat.PNG, self.service.format_handlers)
        self.assertIn(MediaFormat.MP3, self.service.format_handlers)
        self.assertIn(MediaFormat.WAV, self.service.format_handlers)
        self.assertIn(MediaFormat.MP4, self.service.format_handlers)
        self.assertIn(MediaFormat.AVI, self.service.format_handlers)
    
    def test_process_media(self):
        """Test processing media."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        self.service._process_image = MagicMock(return_value=Image.from_file(self.image_path))
        self.service._process_audio = MagicMock(return_value=Audio.from_file(self.audio_path))
        self.service._process_video = MagicMock(return_value=Video.from_file(self.video_path))
        
        self.service._save_media = MagicMock(return_value=True)
        
        media = loop.run_until_complete(self.service.process_media(self.image_path))
        
        self.assertIsNotNone(media)
        self.assertEqual(media.media_type, MediaType.IMAGE)
        self.assertEqual(media.media_format, MediaFormat.JPG)
        self.service._process_image.assert_called_once_with(self.image_path)
        self.service._save_media.assert_called_once()
        
        self.service._process_image.reset_mock()
        self.service._save_media.reset_mock()
        
        media = loop.run_until_complete(self.service.process_media(self.audio_path))
        
        self.assertIsNotNone(media)
        self.assertEqual(media.media_type, MediaType.AUDIO)
        self.assertEqual(media.media_format, MediaFormat.MP3)
        self.service._process_audio.assert_called_once_with(self.audio_path)
        self.service._save_media.assert_called_once()
        
        self.service._process_audio.reset_mock()
        self.service._save_media.reset_mock()
        
        media = loop.run_until_complete(self.service.process_media(self.video_path))
        
        self.assertIsNotNone(media)
        self.assertEqual(media.media_type, MediaType.VIDEO)
        self.assertEqual(media.media_format, MediaFormat.MP4)
        self.service._process_video.assert_called_once_with(self.video_path)
        self.service._save_media.assert_called_once()
    
    def test_save_and_get_media(self):
        """Test saving and getting media."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        media = Media.from_file(self.image_path, id="test_media")
        
        result = loop.run_until_complete(self.service._save_media(media))
        
        self.assertTrue(result)
        self.assertTrue((self.service.media_dir / "test_media.pkl").exists())
        
        retrieved_media = loop.run_until_complete(self.service.get_media("test_media"))
        
        self.assertIsNotNone(retrieved_media)
        self.assertEqual(retrieved_media.id, "test_media")
        self.assertEqual(retrieved_media.path, self.image_path)
        self.assertEqual(retrieved_media.media_type, MediaType.IMAGE)
        self.assertEqual(retrieved_media.media_format, MediaFormat.JPG)
    
    def test_generate_embedding(self):
        """Test generating embedding."""
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(self.service.initialize())
        loop.run_until_complete(self.service.start())
        
        media = Media.from_file(self.image_path, id="test_media")
        
        self.service.vector_store_service.add_embedding = MagicMock(return_value=True)
        
        embedding = np.random.rand(512)
        self.service._generate_image_embedding = MagicMock(return_value=embedding)
        self.service._generate_audio_embedding = MagicMock(return_value=embedding)
        self.service._generate_video_embedding = MagicMock(return_value=embedding)
        
        self.service._save_media = MagicMock(return_value=True)
        
        result = loop.run_until_complete(self.service._generate_embedding(media))
        
        self.assertTrue(result)
        self.service._generate_image_embedding.assert_called_once_with(media)
        self.service.vector_store_service.add_embedding.assert_called_once()
        self.service._save_media.assert_called_once()
        self.assertEqual(media.embedding.shape, embedding.shape)
    
    def test_file_event_handlers(self):
        """Test file event handlers."""
        self.service.process_media = MagicMock()
        
        self.service.is_running = True
        
        event = Event(
            EventType.FILE_CREATED,
            {"path": self.image_path},
            "test",
        )
        
        self.service._on_file_created(event)
        
        
        event = Event(
            EventType.FILE_MODIFIED,
            {"path": self.image_path},
            "test",
        )
        
        self.service._on_file_modified(event)
        


if __name__ == "__main__":
    unittest.main()

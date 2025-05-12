"""
Media Processor Service for the Knowledge Mesh Desktop application.

This module provides services for processing different types of media files,
including images, audio, and video.
"""

import asyncio
import logging
import os
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable
import numpy as np

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus
from ..models.media import Media, Image, Audio, Video, MediaType, MediaFormat

logger = logging.getLogger(__name__)


class MediaProcessorService:
    """
    Service for processing media files.
    
    This service handles the processing of different types of media files,
    including images, audio, and video. It extracts content, generates
    embeddings, and stores the processed media.
    """
    
    def __init__(self, config: Config, services: Optional[Dict[str, Any]] = None):
        """
        Initialize the media processor service.
        
        Args:
            config: Application configuration
            services: Other services that this service depends on
        """
        self.config = config
        self.services = services or {}
        self.is_running = False
        self.data_dir = Path(self.config.get("app.data_dir", "."))
        self.media_dir = self.data_dir / "media"
        self.media_dir.mkdir(parents=True, exist_ok=True)
        
        self.processors = {
            MediaType.IMAGE: self._process_image,
            MediaType.AUDIO: self._process_audio,
            MediaType.VIDEO: self._process_video,
        }
        
        self.format_handlers = {}
        
        self._init_format_handlers()
        
        event_bus.subscribe(EventType.FILE_CREATED, self._on_file_created)
        event_bus.subscribe(EventType.FILE_MODIFIED, self._on_file_modified)
    
    def _init_format_handlers(self):
        """Initialize format handlers for different media formats."""
        self.format_handlers[MediaFormat.JPG] = self._handle_image
        self.format_handlers[MediaFormat.PNG] = self._handle_image
        self.format_handlers[MediaFormat.GIF] = self._handle_image
        self.format_handlers[MediaFormat.WEBP] = self._handle_image
        self.format_handlers[MediaFormat.SVG] = self._handle_image
        
        self.format_handlers[MediaFormat.MP3] = self._handle_audio
        self.format_handlers[MediaFormat.WAV] = self._handle_audio
        self.format_handlers[MediaFormat.OGG] = self._handle_audio
        self.format_handlers[MediaFormat.FLAC] = self._handle_audio
        
        self.format_handlers[MediaFormat.MP4] = self._handle_video
        self.format_handlers[MediaFormat.AVI] = self._handle_video
        self.format_handlers[MediaFormat.MOV] = self._handle_video
        self.format_handlers[MediaFormat.MKV] = self._handle_video
        self.format_handlers[MediaFormat.WEBM] = self._handle_video
    
    async def initialize(self):
        """Initialize the media processor service."""
        logger.info("Initializing media processor service")
        
        self.media_dir.mkdir(parents=True, exist_ok=True)
        
        self.vector_store_service = self.services.get("vector_store")
        self.document_processor_service = self.services.get("document_processor")
        self.knowledge_mesh_service = self.services.get("knowledge_mesh")
        
        logger.info("Media processor service initialized")
    
    async def start(self):
        """Start the media processor service."""
        logger.info("Starting media processor service")
        self.is_running = True
        logger.info("Media processor service started")
    
    async def stop(self):
        """Stop the media processor service."""
        logger.info("Stopping media processor service")
        self.is_running = False
        logger.info("Media processor service stopped")
    
    async def process_media(self, file_path: str) -> Optional[Media]:
        """
        Process a media file.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            The processed media, or None if processing failed
        """
        if not self.is_running:
            logger.warning("Media processor service is not running")
            return None
        
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
            
            extension = path.suffix.lstrip(".")
            if not extension:
                logger.warning(f"File has no extension: {file_path}")
                return None
            
            media_format = MediaFormat.from_extension(extension)
            if media_format == MediaFormat.UNKNOWN:
                logger.warning(f"Unsupported media format: {extension}")
                return None
            
            media_type = media_format.media_type
            
            if media_type not in self.processors:
                logger.warning(f"No processor for media type: {media_type}")
                return None
            
            processor = self.processors[media_type]
            media = await processor(file_path)
            
            if media:
                await self._save_media(media)
                
                if self.vector_store_service:
                    await self._generate_embedding(media)
                
                if self.knowledge_mesh_service:
                    await self._analyze_relationships(media)
                
                logger.info(f"Processed media: {media}")
                return media
            
            logger.warning(f"Failed to process media: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error processing media: {e}", exc_info=True)
            return None
    
    async def get_media(self, media_id: str) -> Optional[Media]:
        """
        Get a media by ID.
        
        Args:
            media_id: The ID of the media
            
        Returns:
            The media, or None if not found
        """
        try:
            media_path = self.media_dir / f"{media_id}.pkl"
            
            if not media_path.exists():
                logger.warning(f"Media not found: {media_id}")
                return None
            
            with open(media_path, "rb") as f:
                media_dict = pickle.load(f)
            
            media_type = media_dict.get("media_type")
            
            if media_type == MediaType.IMAGE.name:
                return Image.from_dict(media_dict)
            elif media_type == MediaType.AUDIO.name:
                return Audio.from_dict(media_dict)
            elif media_type == MediaType.VIDEO.name:
                return Video.from_dict(media_dict)
            else:
                return Media.from_dict(media_dict)
        except Exception as e:
            logger.error(f"Error getting media: {e}", exc_info=True)
            return None
    
    async def search_media(self, query: str, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Search for media by content.
        
        Args:
            query: The search query
            limit: Maximum number of results
            
        Returns:
            A list of (media_id, similarity) tuples
        """
        if not self.vector_store_service:
            logger.warning("Vector store service not available")
            return []
        
        try:
            results = await self.vector_store_service.search(
                query, collection="media", limit=limit
            )
            
            return results
        except Exception as e:
            logger.error(f"Error searching media: {e}", exc_info=True)
            return []
    
    async def get_media_by_type(self, media_type: MediaType) -> List[Media]:
        """
        Get all media of a specific type.
        
        Args:
            media_type: The type of media to get
            
        Returns:
            A list of media objects
        """
        try:
            media_list = []
            
            for media_path in self.media_dir.glob("*.pkl"):
                try:
                    with open(media_path, "rb") as f:
                        media_dict = pickle.load(f)
                    
                    if media_dict.get("media_type") == media_type.name:
                        if media_type == MediaType.IMAGE:
                            media = Image.from_dict(media_dict)
                        elif media_type == MediaType.AUDIO:
                            media = Audio.from_dict(media_dict)
                        elif media_type == MediaType.VIDEO:
                            media = Video.from_dict(media_dict)
                        else:
                            media = Media.from_dict(media_dict)
                        
                        media_list.append(media)
                except Exception as e:
                    logger.error(f"Error loading media: {e}", exc_info=True)
            
            return media_list
        except Exception as e:
            logger.error(f"Error getting media by type: {e}", exc_info=True)
            return []
    
    async def _save_media(self, media: Media) -> bool:
        """
        Save a media object.
        
        Args:
            media: The media to save
            
        Returns:
            True if the media was saved successfully, False otherwise
        """
        try:
            media_path = self.media_dir / f"{media.id}.pkl"
            
            with open(media_path, "wb") as f:
                pickle.dump(media.to_dict(), f)
            
            logger.info(f"Saved media: {media.id}")
            return True
        except Exception as e:
            logger.error(f"Error saving media: {e}", exc_info=True)
            return False
    
    async def _generate_embedding(self, media: Media) -> bool:
        """
        Generate an embedding for a media object.
        
        Args:
            media: The media to generate an embedding for
            
        Returns:
            True if the embedding was generated successfully, False otherwise
        """
        if not self.vector_store_service:
            logger.warning("Vector store service not available")
            return False
        
        try:
            if media.media_type == MediaType.IMAGE:
                embedding = await self._generate_image_embedding(media)
            elif media.media_type == MediaType.AUDIO:
                embedding = await self._generate_audio_embedding(media)
            elif media.media_type == MediaType.VIDEO:
                embedding = await self._generate_video_embedding(media)
            else:
                logger.warning(f"Unsupported media type for embedding: {media.media_type}")
                return False
            
            if embedding is None:
                logger.warning(f"Failed to generate embedding for media: {media.id}")
                return False
            
            await self.vector_store_service.add_embedding(
                media.id, embedding, collection="media"
            )
            
            media.embedding = embedding
            await self._save_media(media)
            
            logger.info(f"Generated embedding for media: {media.id}")
            return True
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            return False
    
    async def _generate_image_embedding(self, media: Media) -> Optional[np.ndarray]:
        """
        Generate an embedding for an image.
        
        Args:
            media: The image to generate an embedding for
            
        Returns:
            The embedding, or None if generation failed
        """
        try:
            if not self.vector_store_service or not hasattr(self.vector_store_service, "embed_image"):
                logger.warning("No image embedding model available, using placeholder")
                return np.random.rand(512)
            
            embedding = await self.vector_store_service.embed_image(media.path)
            return embedding
        except Exception as e:
            logger.error(f"Error generating image embedding: {e}", exc_info=True)
            return None
    
    async def _generate_audio_embedding(self, media: Media) -> Optional[np.ndarray]:
        """
        Generate an embedding for an audio file.
        
        Args:
            media: The audio file to generate an embedding for
            
        Returns:
            The embedding, or None if generation failed
        """
        try:
            if not self.vector_store_service or not hasattr(self.vector_store_service, "embed_audio"):
                if hasattr(self, "_transcribe_audio"):
                    transcript = await self._transcribe_audio(media.path)
                    if transcript:
                        return await self.vector_store_service.embed_text(transcript)
                
                logger.warning("No audio embedding model available, using placeholder")
                return np.random.rand(512)
            
            embedding = await self.vector_store_service.embed_audio(media.path)
            return embedding
        except Exception as e:
            logger.error(f"Error generating audio embedding: {e}", exc_info=True)
            return None
    
    async def _generate_video_embedding(self, media: Media) -> Optional[np.ndarray]:
        """
        Generate an embedding for a video file.
        
        Args:
            media: The video file to generate an embedding for
            
        Returns:
            The embedding, or None if generation failed
        """
        try:
            if not self.vector_store_service or not hasattr(self.vector_store_service, "embed_video"):
                frames_embedding = None
                audio_embedding = None
                
                if hasattr(self, "_extract_video_frames"):
                    frames = await self._extract_video_frames(media.path)
                    if frames and len(frames) > 0:
                        frame_embeddings = []
                        for frame in frames:
                            frame_embedding = await self._generate_image_embedding(frame)
                            if frame_embedding is not None:
                                frame_embeddings.append(frame_embedding)
                        
                        if len(frame_embeddings) > 0:
                            frames_embedding = np.mean(frame_embeddings, axis=0)
                
                if hasattr(self, "_extract_video_audio"):
                    audio = await self._extract_video_audio(media.path)
                    if audio:
                        audio_embedding = await self._generate_audio_embedding(audio)
                
                if frames_embedding is not None and audio_embedding is not None:
                    return np.concatenate([frames_embedding, audio_embedding])
                elif frames_embedding is not None:
                    return frames_embedding
                elif audio_embedding is not None:
                    return audio_embedding
                
                logger.warning("No video embedding model available, using placeholder")
                return np.random.rand(512)
            
            embedding = await self.vector_store_service.embed_video(media.path)
            return embedding
        except Exception as e:
            logger.error(f"Error generating video embedding: {e}", exc_info=True)
            return None
    
    async def _analyze_relationships(self, media: Media) -> bool:
        """
        Analyze relationships for a media object.
        
        Args:
            media: The media to analyze relationships for
            
        Returns:
            True if relationships were analyzed successfully, False otherwise
        """
        if not self.knowledge_mesh_service:
            logger.warning("Knowledge mesh service not available")
            return False
        
        try:
            document_id = f"media_{media.id}"
            document_title = media.metadata.get("title", f"{media.media_type.name} {media.id}")
            document_content = media.metadata.get("description", "")
            
            document_content += f"\nMedia Type: {media.media_type.name}\nMedia Format: {media.media_format.name}"
            
            if "extracted_text" in media.metadata:
                document_content += f"\n{media.metadata['extracted_text']}"
            
            if "transcript" in media.metadata:
                document_content += f"\n{media.metadata['transcript']}"
            
            await self.knowledge_mesh_service.analyze_document_relationships(
                document_id, document_title, document_content, media.embedding
            )
            
            logger.info(f"Analyzed relationships for media: {media.id}")
            return True
        except Exception as e:
            logger.error(f"Error analyzing relationships: {e}", exc_info=True)
            return False
    
    async def _process_image(self, file_path: str) -> Optional[Image]:
        """
        Process an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            The processed image, or None if processing failed
        """
        try:
            image = Image.from_file(file_path)
            
            extracted_text = await self._extract_text_from_image(file_path)
            if extracted_text:
                image.metadata["extracted_text"] = extracted_text
            
            detected_objects = await self._detect_objects_in_image(file_path)
            if detected_objects:
                image.metadata["detected_objects"] = detected_objects
            
            return image
        except Exception as e:
            logger.error(f"Error processing image: {e}", exc_info=True)
            return None
    
    async def _process_audio(self, file_path: str) -> Optional[Audio]:
        """
        Process an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            The processed audio, or None if processing failed
        """
        try:
            audio = Audio.from_file(file_path)
            
            transcript = await self._transcribe_audio(file_path)
            if transcript:
                audio.metadata["transcript"] = transcript
            
            return audio
        except Exception as e:
            logger.error(f"Error processing audio: {e}", exc_info=True)
            return None
    
    async def _process_video(self, file_path: str) -> Optional[Video]:
        """
        Process a video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            The processed video, or None if processing failed
        """
        try:
            video = Video.from_file(file_path)
            
            transcript = await self._transcribe_video(file_path)
            if transcript:
                video.metadata["transcript"] = transcript
            
            key_frames = await self._extract_key_frames(file_path)
            if key_frames:
                video.metadata["key_frames"] = key_frames
            
            return video
        except Exception as e:
            logger.error(f"Error processing video: {e}", exc_info=True)
            return None
    
    async def _extract_text_from_image(self, file_path: str) -> Optional[str]:
        """
        Extract text from an image using OCR.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            The extracted text, or None if extraction failed
        """
        try:
            try:
                import pytesseract
                from PIL import Image as PILImage
                
                with PILImage.open(file_path) as img:
                    text = pytesseract.image_to_string(img)
                    
                    if text and text.strip():
                        logger.info(f"Extracted text from image: {file_path}")
                        return text.strip()
                    
                    logger.info(f"No text found in image: {file_path}")
                    return None
            except ImportError:
                logger.warning("pytesseract not installed, cannot extract text from image")
                return None
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}", exc_info=True)
            return None
    
    async def _detect_objects_in_image(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        Detect objects in an image.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            A list of detected objects, or None if detection failed
        """
        logger.info(f"Object detection not implemented for image: {file_path}")
        return None
    
    async def _transcribe_audio(self, file_path: str) -> Optional[str]:
        """
        Transcribe an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            The transcription, or None if transcription failed
        """
        logger.info(f"Audio transcription not implemented for: {file_path}")
        return None
    
    async def _transcribe_video(self, file_path: str) -> Optional[str]:
        """
        Transcribe a video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            The transcription, or None if transcription failed
        """
        logger.info(f"Video transcription not implemented for: {file_path}")
        return None
    
    async def _extract_key_frames(self, file_path: str) -> Optional[List[str]]:
        """
        Extract key frames from a video.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            A list of paths to extracted key frames, or None if extraction failed
        """
        logger.info(f"Key frame extraction not implemented for: {file_path}")
        return None
    
    def _handle_image(self, file_path: str) -> bool:
        """
        Handle an image file event.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            True if the file was handled, False otherwise
        """
        asyncio.create_task(self.process_media(file_path))
        return True
    
    def _handle_audio(self, file_path: str) -> bool:
        """
        Handle an audio file event.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            True if the file was handled, False otherwise
        """
        asyncio.create_task(self.process_media(file_path))
        return True
    
    def _handle_video(self, file_path: str) -> bool:
        """
        Handle a video file event.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            True if the file was handled, False otherwise
        """
        asyncio.create_task(self.process_media(file_path))
        return True
    
    def _on_file_created(self, event):
        """
        Handle file created events.
        
        Args:
            event: The file created event
        """
        if not self.is_running:
            return
        
        file_path = event.data.get("path")
        if not file_path:
            return
        
        path = Path(file_path)
        extension = path.suffix.lstrip(".")
        if not extension:
            return
        
        media_format = MediaFormat.from_extension(extension)
        if media_format == MediaFormat.UNKNOWN:
            return
        
        if media_format in self.format_handlers:
            handler = self.format_handlers[media_format]
            handler(file_path)
    
    def _on_file_modified(self, event):
        """
        Handle file modified events.
        
        Args:
            event: The file modified event
        """
        if not self.is_running:
            return
        
        file_path = event.data.get("path")
        if not file_path:
            return
        
        path = Path(file_path)
        extension = path.suffix.lstrip(".")
        if not extension:
            return
        
        media_format = MediaFormat.from_extension(extension)
        if media_format == MediaFormat.UNKNOWN:
            return
        
        if media_format in self.format_handlers:
            handler = self.format_handlers[media_format]
            handler(file_path)

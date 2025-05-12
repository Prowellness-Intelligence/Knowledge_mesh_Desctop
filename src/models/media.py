"""
Media models for the Knowledge Mesh Desktop application.

This module defines models for different types of media content
that can be processed by the application, including images, audio,
and video files.
"""

import os
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set
import numpy as np


class MediaType(Enum):
    """Enum defining the types of media."""
    
    IMAGE = auto()       # Image files (jpg, png, etc.)
    AUDIO = auto()       # Audio files (mp3, wav, etc.)
    VIDEO = auto()       # Video files (mp4, avi, etc.)
    DOCUMENT = auto()    # Document files (pdf, docx, etc.)
    CUSTOM = auto()      # Custom media type


class MediaFormat(Enum):
    """Enum defining the formats of media."""
    
    JPG = auto()
    PNG = auto()
    GIF = auto()
    WEBP = auto()
    SVG = auto()
    
    MP3 = auto()
    WAV = auto()
    OGG = auto()
    FLAC = auto()
    
    MP4 = auto()
    AVI = auto()
    MOV = auto()
    MKV = auto()
    WEBM = auto()
    
    PDF = auto()
    DOCX = auto()
    TXT = auto()
    MARKDOWN = auto()
    
    UNKNOWN = auto()
    
    @classmethod
    def from_extension(cls, extension: str) -> "MediaFormat":
        """
        Get the media format from a file extension.
        
        Args:
            extension: The file extension (without the dot)
            
        Returns:
            The corresponding MediaFormat
        """
        extension = extension.lower()
        
        if extension in ["jpg", "jpeg"]:
            return cls.JPG
        elif extension == "png":
            return cls.PNG
        elif extension == "gif":
            return cls.GIF
        elif extension == "webp":
            return cls.WEBP
        elif extension == "svg":
            return cls.SVG
        
        elif extension == "mp3":
            return cls.MP3
        elif extension == "wav":
            return cls.WAV
        elif extension == "ogg":
            return cls.OGG
        elif extension == "flac":
            return cls.FLAC
        
        elif extension == "mp4":
            return cls.MP4
        elif extension == "avi":
            return cls.AVI
        elif extension == "mov":
            return cls.MOV
        elif extension == "mkv":
            return cls.MKV
        elif extension == "webm":
            return cls.WEBM
        
        elif extension == "pdf":
            return cls.PDF
        elif extension == "docx":
            return cls.DOCX
        elif extension == "txt":
            return cls.TXT
        elif extension in ["md", "markdown"]:
            return cls.MARKDOWN
        
        else:
            return cls.UNKNOWN
    
    @property
    def media_type(self) -> MediaType:
        """Get the media type for this format."""
        if self in [self.JPG, self.PNG, self.GIF, self.WEBP, self.SVG]:
            return MediaType.IMAGE
        elif self in [self.MP3, self.WAV, self.OGG, self.FLAC]:
            return MediaType.AUDIO
        elif self in [self.MP4, self.AVI, self.MOV, self.MKV, self.WEBM]:
            return MediaType.VIDEO
        elif self in [self.PDF, self.DOCX, self.TXT, self.MARKDOWN]:
            return MediaType.DOCUMENT
        else:
            return MediaType.CUSTOM
    
    @property
    def extension(self) -> str:
        """Get the file extension for this format."""
        if self == self.JPG:
            return "jpg"
        elif self == self.PNG:
            return "png"
        elif self == self.GIF:
            return "gif"
        elif self == self.WEBP:
            return "webp"
        elif self == self.SVG:
            return "svg"
        elif self == self.MP3:
            return "mp3"
        elif self == self.WAV:
            return "wav"
        elif self == self.OGG:
            return "ogg"
        elif self == self.FLAC:
            return "flac"
        elif self == self.MP4:
            return "mp4"
        elif self == self.AVI:
            return "avi"
        elif self == self.MOV:
            return "mov"
        elif self == self.MKV:
            return "mkv"
        elif self == self.WEBM:
            return "webm"
        elif self == self.PDF:
            return "pdf"
        elif self == self.DOCX:
            return "docx"
        elif self == self.TXT:
            return "txt"
        elif self == self.MARKDOWN:
            return "md"
        else:
            return "unknown"


class Media:
    """
    Base class for all media types.
    
    This class represents a media file that can be processed by the
    application, including its metadata and content.
    """
    
    def __init__(
        self,
        id: str,
        path: str,
        media_type: MediaType,
        media_format: MediaFormat,
        created_at: Optional[datetime] = None,
        modified_at: Optional[datetime] = None,
        size_bytes: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[np.ndarray] = None,
    ):
        """
        Initialize a media object.
        
        Args:
            id: The unique identifier for the media
            path: The path to the media file
            media_type: The type of the media
            media_format: The format of the media
            created_at: When the media was created
            modified_at: When the media was last modified
            size_bytes: The size of the media in bytes
            metadata: Additional metadata for the media
            embedding: Vector embedding of the media content
        """
        self.id = id
        self.path = path
        self.media_type = media_type
        self.media_format = media_format
        self.created_at = created_at or datetime.utcnow()
        self.modified_at = modified_at or datetime.utcnow()
        self.size_bytes = size_bytes
        self.metadata = metadata or {}
        self.embedding = embedding
    
    @classmethod
    def from_file(cls, file_path: str, id: Optional[str] = None) -> "Media":
        """
        Create a media object from a file.
        
        Args:
            file_path: The path to the file
            id: Optional ID for the media (defaults to filename)
            
        Returns:
            A Media object
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stats = path.stat()
        created_at = datetime.fromtimestamp(stats.st_ctime)
        modified_at = datetime.fromtimestamp(stats.st_mtime)
        size_bytes = stats.st_size
        
        extension = path.suffix.lstrip(".")
        media_format = MediaFormat.from_extension(extension)
        media_type = media_format.media_type
        
        if id is None:
            id = path.stem
        
        return cls(
            id=id,
            path=str(path),
            media_type=media_type,
            media_format=media_format,
            created_at=created_at,
            modified_at=modified_at,
            size_bytes=size_bytes,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the media to a dictionary.
        
        Returns:
            A dictionary representation of the media
        """
        return {
            "id": self.id,
            "path": self.path,
            "media_type": self.media_type.name,
            "media_format": self.media_format.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
            "has_embedding": self.embedding is not None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Media":
        """
        Create a media object from a dictionary.
        
        Args:
            data: The dictionary representation of the media
            
        Returns:
            A Media object
        """
        media_type = MediaType.CUSTOM
        if data.get("media_type"):
            try:
                media_type = MediaType[data["media_type"]]
            except KeyError:
                media_type = MediaType.CUSTOM
        
        media_format = MediaFormat.UNKNOWN
        if data.get("media_format"):
            try:
                media_format = MediaFormat[data["media_format"]]
            except KeyError:
                media_format = MediaFormat.UNKNOWN
        
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                created_at = datetime.utcnow()
        
        modified_at = None
        if data.get("modified_at"):
            try:
                modified_at = datetime.fromisoformat(data["modified_at"])
            except ValueError:
                modified_at = datetime.utcnow()
        
        return cls(
            id=data.get("id", ""),
            path=data.get("path", ""),
            media_type=media_type,
            media_format=media_format,
            created_at=created_at,
            modified_at=modified_at,
            size_bytes=data.get("size_bytes"),
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the media."""
        return (
            f"Media(id={self.id}, type={self.media_type.name}, "
            f"format={self.media_format.name})"
        )
    
    def __repr__(self) -> str:
        """Get a string representation of the media."""
        return self.__str__()


class Image(Media):
    """
    Represents an image file.
    
    This class extends the Media class with image-specific properties
    and methods.
    """
    
    def __init__(
        self,
        id: str,
        path: str,
        media_format: MediaFormat,
        width: Optional[int] = None,
        height: Optional[int] = None,
        channels: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize an image.
        
        Args:
            id: The unique identifier for the image
            path: The path to the image file
            media_format: The format of the image
            width: The width of the image in pixels
            height: The height of the image in pixels
            channels: The number of color channels
            **kwargs: Additional arguments for the Media constructor
        """
        super().__init__(
            id=id,
            path=path,
            media_type=MediaType.IMAGE,
            media_format=media_format,
            **kwargs,
        )
        
        self.width = width
        self.height = height
        self.channels = channels
    
    @classmethod
    def from_file(cls, file_path: str, id: Optional[str] = None) -> "Image":
        """
        Create an image object from a file.
        
        Args:
            file_path: The path to the file
            id: Optional ID for the image (defaults to filename)
            
        Returns:
            An Image object
        """
        media = super().from_file(file_path, id)
        
        if media.media_type != MediaType.IMAGE:
            raise ValueError(f"File is not an image: {file_path}")
        
        width = None
        height = None
        channels = None
        
        try:
            from PIL import Image as PILImage
            
            with PILImage.open(file_path) as img:
                width, height = img.size
                channels = len(img.getbands())
        except ImportError:
            pass  # PIL not available
        except Exception:
            pass  # Error reading image
        
        return cls(
            id=media.id,
            path=media.path,
            media_format=media.media_format,
            created_at=media.created_at,
            modified_at=media.modified_at,
            size_bytes=media.size_bytes,
            metadata=media.metadata,
            embedding=media.embedding,
            width=width,
            height=height,
            channels=channels,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the image to a dictionary.
        
        Returns:
            A dictionary representation of the image
        """
        data = super().to_dict()
        data.update({
            "width": self.width,
            "height": self.height,
            "channels": self.channels,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Image":
        """
        Create an image object from a dictionary.
        
        Args:
            data: The dictionary representation of the image
            
        Returns:
            An Image object
        """
        media = Media.from_dict(data)
        
        return cls(
            id=media.id,
            path=media.path,
            media_format=media.media_format,
            created_at=media.created_at,
            modified_at=media.modified_at,
            size_bytes=media.size_bytes,
            metadata=media.metadata,
            embedding=media.embedding,
            width=data.get("width"),
            height=data.get("height"),
            channels=data.get("channels"),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the image."""
        return (
            f"Image(id={self.id}, format={self.media_format.name}, "
            f"dimensions={self.width}x{self.height})"
        )


class Audio(Media):
    """
    Represents an audio file.
    
    This class extends the Media class with audio-specific properties
    and methods.
    """
    
    def __init__(
        self,
        id: str,
        path: str,
        media_format: MediaFormat,
        duration_seconds: Optional[float] = None,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        bit_rate: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize an audio file.
        
        Args:
            id: The unique identifier for the audio
            path: The path to the audio file
            media_format: The format of the audio
            duration_seconds: The duration of the audio in seconds
            sample_rate: The sample rate in Hz
            channels: The number of audio channels
            bit_rate: The bit rate in bits per second
            **kwargs: Additional arguments for the Media constructor
        """
        super().__init__(
            id=id,
            path=path,
            media_type=MediaType.AUDIO,
            media_format=media_format,
            **kwargs,
        )
        
        self.duration_seconds = duration_seconds
        self.sample_rate = sample_rate
        self.channels = channels
        self.bit_rate = bit_rate
    
    @classmethod
    def from_file(cls, file_path: str, id: Optional[str] = None) -> "Audio":
        """
        Create an audio object from a file.
        
        Args:
            file_path: The path to the file
            id: Optional ID for the audio (defaults to filename)
            
        Returns:
            An Audio object
        """
        media = super().from_file(file_path, id)
        
        if media.media_type != MediaType.AUDIO:
            raise ValueError(f"File is not an audio file: {file_path}")
        
        duration_seconds = None
        sample_rate = None
        channels = None
        bit_rate = None
        
        try:
            import librosa
            
            y, sr = librosa.load(file_path, sr=None)
            duration_seconds = librosa.get_duration(y=y, sr=sr)
            sample_rate = sr
            channels = 1 if y.ndim == 1 else y.shape[0]
        except ImportError:
            pass  # librosa not available
        except Exception:
            pass  # Error reading audio
        
        return cls(
            id=media.id,
            path=media.path,
            media_format=media.media_format,
            created_at=media.created_at,
            modified_at=media.modified_at,
            size_bytes=media.size_bytes,
            metadata=media.metadata,
            embedding=media.embedding,
            duration_seconds=duration_seconds,
            sample_rate=sample_rate,
            channels=channels,
            bit_rate=bit_rate,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the audio to a dictionary.
        
        Returns:
            A dictionary representation of the audio
        """
        data = super().to_dict()
        data.update({
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bit_rate": self.bit_rate,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Audio":
        """
        Create an audio object from a dictionary.
        
        Args:
            data: The dictionary representation of the audio
            
        Returns:
            An Audio object
        """
        media = Media.from_dict(data)
        
        return cls(
            id=media.id,
            path=media.path,
            media_format=media.media_format,
            created_at=media.created_at,
            modified_at=media.modified_at,
            size_bytes=media.size_bytes,
            metadata=media.metadata,
            embedding=media.embedding,
            duration_seconds=data.get("duration_seconds"),
            sample_rate=data.get("sample_rate"),
            channels=data.get("channels"),
            bit_rate=data.get("bit_rate"),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the audio."""
        return (
            f"Audio(id={self.id}, format={self.media_format.name}, "
            f"duration={self.duration_seconds:.2f}s)"
        )


class Video(Media):
    """
    Represents a video file.
    
    This class extends the Media class with video-specific properties
    and methods.
    """
    
    def __init__(
        self,
        id: str,
        path: str,
        media_format: MediaFormat,
        duration_seconds: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        audio_channels: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize a video file.
        
        Args:
            id: The unique identifier for the video
            path: The path to the video file
            media_format: The format of the video
            duration_seconds: The duration of the video in seconds
            width: The width of the video in pixels
            height: The height of the video in pixels
            fps: The frames per second
            audio_channels: The number of audio channels
            **kwargs: Additional arguments for the Media constructor
        """
        super().__init__(
            id=id,
            path=path,
            media_type=MediaType.VIDEO,
            media_format=media_format,
            **kwargs,
        )
        
        self.duration_seconds = duration_seconds
        self.width = width
        self.height = height
        self.fps = fps
        self.audio_channels = audio_channels
    
    @classmethod
    def from_file(cls, file_path: str, id: Optional[str] = None) -> "Video":
        """
        Create a video object from a file.
        
        Args:
            file_path: The path to the file
            id: Optional ID for the video (defaults to filename)
            
        Returns:
            A Video object
        """
        media = super().from_file(file_path, id)
        
        if media.media_type != MediaType.VIDEO:
            raise ValueError(f"File is not a video file: {file_path}")
        
        duration_seconds = None
        width = None
        height = None
        fps = None
        audio_channels = None
        
        try:
            import cv2
            
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration_seconds = frame_count / fps if fps > 0 else None
                cap.release()
        except ImportError:
            pass  # cv2 not available
        except Exception:
            pass  # Error reading video
        
        return cls(
            id=media.id,
            path=media.path,
            media_format=media.media_format,
            created_at=media.created_at,
            modified_at=media.modified_at,
            size_bytes=media.size_bytes,
            metadata=media.metadata,
            embedding=media.embedding,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            fps=fps,
            audio_channels=audio_channels,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the video to a dictionary.
        
        Returns:
            A dictionary representation of the video
        """
        data = super().to_dict()
        data.update({
            "duration_seconds": self.duration_seconds,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "audio_channels": self.audio_channels,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Video":
        """
        Create a video object from a dictionary.
        
        Args:
            data: The dictionary representation of the video
            
        Returns:
            A Video object
        """
        media = Media.from_dict(data)
        
        return cls(
            id=media.id,
            path=media.path,
            media_format=media.media_format,
            created_at=media.created_at,
            modified_at=media.modified_at,
            size_bytes=media.size_bytes,
            metadata=media.metadata,
            embedding=media.embedding,
            duration_seconds=data.get("duration_seconds"),
            width=data.get("width"),
            height=data.get("height"),
            fps=data.get("fps"),
            audio_channels=data.get("audio_channels"),
        )
    
    def __str__(self) -> str:
        """Get a string representation of the video."""
        return (
            f"Video(id={self.id}, format={self.media_format.name}, "
            f"dimensions={self.width}x{self.height}, duration={self.duration_seconds:.2f}s)"
        )

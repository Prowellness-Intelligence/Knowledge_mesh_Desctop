"""
Image generation service for the Knowledge Mesh Desktop application.

This module provides a service for generating images using AI services
based on text prompts and document content.
"""

import os
import json
import asyncio
import logging
import base64
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
from datetime import datetime

import aiohttp

from src.core.config import Config
from src.core.events import EventType, publish_event
from src.services.vault_integration import VaultIntegrationService


logger = logging.getLogger(__name__)


class ImageGenerationModel(str, Enum):
    """Enum for image generation models."""
    
    DALL_E_2 = "dall-e-2"
    DALL_E_3 = "dall-e-3"
    STABLE_DIFFUSION = "stable-diffusion"
    MIDJOURNEY = "midjourney"
    CUSTOM = "custom"


class ImageSize(str, Enum):
    """Enum for image sizes."""
    
    SMALL = "256x256"
    MEDIUM = "512x512"
    LARGE = "1024x1024"
    WIDE = "1024x576"
    TALL = "576x1024"
    CUSTOM = "custom"


class ImageFormat(str, Enum):
    """Enum for image formats."""
    
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"


class ImageGenerationStatus(str, Enum):
    """Enum for image generation status."""
    
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageGenerationRequest:
    """Class representing an image generation request."""
    
    def __init__(
        self,
        id: str,
        prompt: str,
        model: ImageGenerationModel = ImageGenerationModel.DALL_E_3,
        size: ImageSize = ImageSize.MEDIUM,
        format: ImageFormat = ImageFormat.PNG,
        num_images: int = 1,
        negative_prompt: Optional[str] = None,
        reference_image: Optional[str] = None,
        style_preset: Optional[str] = None,
        seed: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        status: ImageGenerationStatus = ImageGenerationStatus.PENDING,
        status_message: Optional[str] = None,
        output_images: Optional[List[str]] = None,
    ):
        """Initialize an image generation request.
        
        Args:
            id: The unique identifier for the request
            prompt: The text prompt for image generation
            model: The image generation model to use
            size: The size of the generated image
            format: The format of the generated image
            num_images: The number of images to generate
            negative_prompt: Text prompt for what to avoid in the image
            reference_image: Path to a reference image to use
            style_preset: Style preset to use
            seed: Random seed for reproducibility
            metadata: Additional metadata for the request
            created_at: When the request was created
            status: The status of the request
            status_message: A message describing the status
            output_images: Paths to the generated images
        """
        self.id = id
        self.prompt = prompt
        self.model = model
        self.size = size
        self.format = format
        self.num_images = num_images
        self.negative_prompt = negative_prompt
        self.reference_image = reference_image
        self.style_preset = style_preset
        self.seed = seed
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.status = status
        self.status_message = status_message
        self.output_images = output_images or []
    
    @classmethod
    def create(
        cls,
        prompt: str,
        model: ImageGenerationModel = ImageGenerationModel.DALL_E_3,
        size: ImageSize = ImageSize.MEDIUM,
        format: ImageFormat = ImageFormat.PNG,
        num_images: int = 1,
        negative_prompt: Optional[str] = None,
        reference_image: Optional[str] = None,
        style_preset: Optional[str] = None,
        seed: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ImageGenerationRequest":
        """Create a new image generation request.
        
        Args:
            prompt: The text prompt for image generation
            model: The image generation model to use
            size: The size of the generated image
            format: The format of the generated image
            num_images: The number of images to generate
            negative_prompt: Text prompt for what to avoid in the image
            reference_image: Path to a reference image to use
            style_preset: Style preset to use
            seed: Random seed for reproducibility
            metadata: Additional metadata for the request
            
        Returns:
            A new image generation request
        """
        return cls(
            id=str(uuid.uuid4()),
            prompt=prompt,
            model=model,
            size=size,
            format=format,
            num_images=num_images,
            negative_prompt=negative_prompt,
            reference_image=reference_image,
            style_preset=style_preset,
            seed=seed,
            metadata=metadata,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the request to a dictionary.
        
        Returns:
            A dictionary representation of the request
        """
        return {
            "id": self.id,
            "prompt": self.prompt,
            "model": self.model.value,
            "size": self.size.value,
            "format": self.format.value,
            "num_images": self.num_images,
            "negative_prompt": self.negative_prompt,
            "reference_image": self.reference_image,
            "style_preset": self.style_preset,
            "seed": self.seed,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "status_message": self.status_message,
            "output_images": self.output_images,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageGenerationRequest":
        """Create a request from a dictionary.
        
        Args:
            data: The dictionary representation of the request
            
        Returns:
            An image generation request
        """
        return cls(
            id=data["id"],
            prompt=data["prompt"],
            model=ImageGenerationModel(data["model"]),
            size=ImageSize(data["size"]),
            format=ImageFormat(data["format"]),
            num_images=data["num_images"],
            negative_prompt=data.get("negative_prompt"),
            reference_image=data.get("reference_image"),
            style_preset=data.get("style_preset"),
            seed=data.get("seed"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            status=ImageGenerationStatus(data["status"]),
            status_message=data.get("status_message"),
            output_images=data.get("output_images", []),
        )


class ImageGenerationService:
    """Service for generating images using AI services."""
    
    def __init__(
        self,
        config: Config,
        vault_service: VaultIntegrationService,
    ):
        """Initialize the image generation service.
        
        Args:
            config: The application configuration
            vault_service: The vault integration service for secure storage
        """
        self.config = config
        self.vault_service = vault_service
        
        self.api_keys = {}
        self.default_model = ImageGenerationModel(
            self.config.get("image_generation.default_model", ImageGenerationModel.DALL_E_3.value)
        )
        self.default_size = ImageSize(
            self.config.get("image_generation.default_size", ImageSize.MEDIUM.value)
        )
        self.default_format = ImageFormat(
            self.config.get("image_generation.default_format", ImageFormat.PNG.value)
        )
        
        self.requests: Dict[str, ImageGenerationRequest] = {}
        self.active_requests: Set[str] = set()
        self.max_concurrent_requests = int(self.config.get("image_generation.max_concurrent_requests", 3))
        
        self.request_queue = asyncio.Queue()
        self.queue_processor_task = None
        
        self.output_dir = Path(self.config.get("app.data_dir", "./data")) / "generated_images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize the image generation service."""
        logger.info("Initializing image generation service")
        
        try:
            api_keys = await self.vault_service.get_secret("image_generation_api_keys")
            if api_keys:
                self.api_keys = api_keys
        except Exception as e:
            logger.error(f"Error loading API keys from vault: {e}")
        
        requests_file = self.output_dir / "requests.json"
        if requests_file.exists():
            try:
                with open(requests_file, "r") as f:
                    requests_data = json.load(f)
                    
                    for request_data in requests_data:
                        request = ImageGenerationRequest.from_dict(request_data)
                        self.requests[request.id] = request
            except Exception as e:
                logger.error(f"Error loading saved requests: {e}")
    
    async def start(self):
        """Start the image generation service."""
        logger.info("Starting image generation service")
        
        self.queue_processor_task = asyncio.create_task(self._process_queue())
    
    async def stop(self):
        """Stop the image generation service."""
        logger.info("Stopping image generation service")
        
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass
            
            self.queue_processor_task = None
        
        await self._save_requests()
    
    async def set_api_key(self, model: ImageGenerationModel, api_key: str):
        """Set the API key for a model.
        
        Args:
            model: The model to set the API key for
            api_key: The API key
            
        Returns:
            A boolean indicating whether the API key was set successfully
        """
        logger.info(f"Setting API key for model: {model.value}")
        
        self.api_keys[model.value] = api_key
        
        try:
            await self.vault_service.set_secret("image_generation_api_keys", self.api_keys)
            return True
        except Exception as e:
            logger.error(f"Error saving API key to vault: {e}")
            return False
    
    async def get_api_key(self, model: ImageGenerationModel) -> Optional[str]:
        """Get the API key for a model.
        
        Args:
            model: The model to get the API key for
            
        Returns:
            The API key, or None if not set
        """
        return self.api_keys.get(model.value)
    
    async def generate_image(
        self,
        prompt: str,
        model: Optional[ImageGenerationModel] = None,
        size: Optional[ImageSize] = None,
        format: Optional[ImageFormat] = None,
        num_images: int = 1,
        negative_prompt: Optional[str] = None,
        reference_image: Optional[str] = None,
        style_preset: Optional[str] = None,
        seed: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ImageGenerationRequest:
        """Generate an image from a text prompt.
        
        Args:
            prompt: The text prompt for image generation
            model: The image generation model to use
            size: The size of the generated image
            format: The format of the generated image
            num_images: The number of images to generate
            negative_prompt: Text prompt for what to avoid in the image
            reference_image: Path to a reference image to use
            style_preset: Style preset to use
            seed: Random seed for reproducibility
            metadata: Additional metadata for the request
            
        Returns:
            The image generation request
        """
        logger.info(f"Generating image with prompt: {prompt}")
        
        request = ImageGenerationRequest.create(
            prompt=prompt,
            model=model or self.default_model,
            size=size or self.default_size,
            format=format or self.default_format,
            num_images=num_images,
            negative_prompt=negative_prompt,
            reference_image=reference_image,
            style_preset=style_preset,
            seed=seed,
            metadata=metadata,
        )
        
        self.requests[request.id] = request
        
        await self.request_queue.put(request.id)
        
        publish_event(
            EventType.IMAGE_GENERATION_REQUESTED,
            {
                "request_id": request.id,
                "prompt": prompt,
                "model": request.model.value,
            },
        )
        
        return request
    
    async def get_request(self, request_id: str) -> Optional[ImageGenerationRequest]:
        """Get an image generation request.
        
        Args:
            request_id: The ID of the request
            
        Returns:
            The request, or None if not found
        """
        return self.requests.get(request_id)
    
    async def get_requests(
        self,
        status: Optional[ImageGenerationStatus] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[ImageGenerationRequest]:
        """Get image generation requests.
        
        Args:
            status: Filter by status
            limit: Maximum number of requests to return
            offset: Offset for pagination
            
        Returns:
            A list of requests
        """
        requests = list(self.requests.values())
        
        requests.sort(key=lambda r: r.created_at, reverse=True)
        
        if status:
            requests = [r for r in requests if r.status == status]
        
        return requests[offset:offset + limit]
    
    async def cancel_request(self, request_id: str) -> bool:
        """Cancel an image generation request.
        
        Args:
            request_id: The ID of the request
            
        Returns:
            A boolean indicating whether the request was cancelled successfully
        """
        logger.info(f"Cancelling image generation request: {request_id}")
        
        if request_id not in self.requests:
            logger.warning(f"Request not found: {request_id}")
            return False
        
        request = self.requests[request_id]
        
        if request.status in [
            ImageGenerationStatus.COMPLETED,
            ImageGenerationStatus.FAILED,
            ImageGenerationStatus.CANCELLED,
        ]:
            logger.warning(f"Request already in final state: {request.status.value}")
            return False
        
        request.status = ImageGenerationStatus.CANCELLED
        request.status_message = "Request cancelled by user"
        
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
        
        publish_event(
            EventType.IMAGE_GENERATION_FAILED,
            {
                "request_id": request_id,
                "error": "Request cancelled by user",
            },
        )
        
        return True
    
    async def delete_request(self, request_id: str) -> bool:
        """Delete an image generation request.
        
        Args:
            request_id: The ID of the request
            
        Returns:
            A boolean indicating whether the request was deleted successfully
        """
        logger.info(f"Deleting image generation request: {request_id}")
        
        if request_id not in self.requests:
            logger.warning(f"Request not found: {request_id}")
            return False
        
        request = self.requests[request_id]
        
        for image_path in request.output_images:
            try:
                image_file = Path(image_path)
                if image_file.exists():
                    image_file.unlink()
            except Exception as e:
                logger.error(f"Error deleting output image: {e}")
        
        del self.requests[request_id]
        
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
        
        return True
    
    async def _process_queue(self):
        """Process the request queue."""
        logger.info("Starting image generation queue processor")
        
        while True:
            try:
                request_id = await self.request_queue.get()
                
                while len(self.active_requests) >= self.max_concurrent_requests:
                    await asyncio.sleep(1)
                
                self.active_requests.add(request_id)
                asyncio.create_task(self._process_request(request_id))
                
                self.request_queue.task_done()
            except asyncio.CancelledError:
                logger.info("Image generation queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in image generation queue processor: {e}")
                await asyncio.sleep(1)
    
    async def _process_request(self, request_id: str):
        """Process an image generation request.
        
        Args:
            request_id: The ID of the request
        """
        logger.info(f"Processing image generation request: {request_id}")
        
        if request_id not in self.requests:
            logger.warning(f"Request not found: {request_id}")
            return
        
        request = self.requests[request_id]
        
        request.status = ImageGenerationStatus.GENERATING
        request.status_message = "Generating image"
        
        try:
            api_key = self.api_keys.get(request.model.value)
            if not api_key:
                raise ValueError(f"No API key available for model: {request.model.value}")
            
            if request.model == ImageGenerationModel.DALL_E_2 or request.model == ImageGenerationModel.DALL_E_3:
                output_images = await self._generate_dalle(request, api_key)
            elif request.model == ImageGenerationModel.STABLE_DIFFUSION:
                output_images = await self._generate_stable_diffusion(request, api_key)
            elif request.model == ImageGenerationModel.MIDJOURNEY:
                output_images = await self._generate_midjourney(request, api_key)
            else:
                raise ValueError(f"Unsupported model: {request.model.value}")
            
            request.status = ImageGenerationStatus.COMPLETED
            request.status_message = "Image generation completed"
            request.output_images = output_images
            
            publish_event(
                EventType.IMAGE_GENERATION_COMPLETED,
                {
                    "request_id": request_id,
                    "output_images": output_images,
                },
            )
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            
            request.status = ImageGenerationStatus.FAILED
            request.status_message = f"Error generating image: {str(e)}"
            
            publish_event(
                EventType.IMAGE_GENERATION_FAILED,
                {
                    "request_id": request_id,
                    "error": str(e),
                },
            )
        finally:
            if request_id in self.active_requests:
                self.active_requests.remove(request_id)
            
            await self._save_requests()
    
    async def _generate_dalle(self, request: ImageGenerationRequest, api_key: str) -> List[str]:
        """Generate an image using DALL-E.
        
        Args:
            request: The image generation request
            api_key: The API key for the OpenAI API
            
        Returns:
            A list of paths to the generated images
        """
        logger.info(f"Generating image with DALL-E: {request.model.value}")
        
        url = "https://api.openai.com/v1/images/generations"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        data = {
            "prompt": request.prompt,
            "n": request.num_images,
            "size": request.size.value,
            "response_format": "b64_json",
        }
        
        if request.model == ImageGenerationModel.DALL_E_3:
            data["model"] = "dall-e-3"
            data["quality"] = "standard"
            data["style"] = request.style_preset or "vivid"
        else:
            data["model"] = "dall-e-2"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_data = await response.json()
                    raise ValueError(f"Error generating image: {error_data.get('error', {}).get('message', 'Unknown error')}")
                
                response_data = await response.json()
                
                output_images = []
                for i, image_data in enumerate(response_data.get("data", [])):
                    if "b64_json" in image_data:
                        image_bytes = base64.b64decode(image_data["b64_json"])
                    elif "url" in image_data:
                        async with session.get(image_data["url"]) as img_response:
                            if img_response.status != 200:
                                logger.error(f"Error downloading image: {img_response.status}")
                                continue
                            
                            image_bytes = await img_response.read()
                    else:
                        logger.error("No image data found in response")
                        continue
                    
                    output_path = self.output_dir / f"{request.id}_{i}.{request.format.value}"
                    with open(output_path, "wb") as f:
                        f.write(image_bytes)
                    
                    output_images.append(str(output_path))
                
                return output_images
    
    async def _generate_stable_diffusion(self, request: ImageGenerationRequest, api_key: str) -> List[str]:
        """Generate an image using Stable Diffusion.
        
        Args:
            request: The image generation request
            api_key: The API key for the Stability AI API
            
        Returns:
            A list of paths to the generated images
        """
        logger.info("Generating image with Stable Diffusion")
        
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        width, height = 1024, 1024
        if request.size != ImageSize.CUSTOM:
            width_str, height_str = request.size.value.split("x")
            width, height = int(width_str), int(height_str)
        
        data = {
            "text_prompts": [
                {
                    "text": request.prompt,
                    "weight": 1.0,
                },
            ],
            "cfg_scale": 7.0,
            "height": height,
            "width": width,
            "samples": request.num_images,
            "steps": 30,
        }
        
        if request.negative_prompt:
            data["text_prompts"].append({
                "text": request.negative_prompt,
                "weight": -1.0,
            })
        
        if request.seed:
            data["seed"] = request.seed
        
        if request.style_preset:
            data["style_preset"] = request.style_preset
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"Error generating image: {error_text}")
                
                response_data = await response.json()
                
                output_images = []
                for i, image_data in enumerate(response_data.get("artifacts", [])):
                    image_bytes = base64.b64decode(image_data["base64"])
                    
                    output_path = self.output_dir / f"{request.id}_{i}.{request.format.value}"
                    with open(output_path, "wb") as f:
                        f.write(image_bytes)
                    
                    output_images.append(str(output_path))
                
                return output_images
    
    async def _generate_midjourney(self, request: ImageGenerationRequest, api_key: str) -> List[str]:
        """Generate an image using Midjourney.
        
        Args:
            request: The image generation request
            api_key: The API key for the Midjourney API
            
        Returns:
            A list of paths to the generated images
        """
        logger.info("Generating image with Midjourney")
        
        
        placeholder_path = self.output_dir / f"{request.id}_placeholder.{request.format.value}"
        
        with open(placeholder_path, "wb") as f:
            f.write(b"Placeholder for Midjourney image")
        
        return [str(placeholder_path)]
    
    async def _save_requests(self):
        """Save requests to disk."""
        logger.info("Saving image generation requests")
        
        requests_file = self.output_dir / "requests.json"
        
        try:
            requests_data = [request.to_dict() for request in self.requests.values()]
            
            with open(requests_file, "w") as f:
                json.dump(requests_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving requests: {e}")

"""
Document Generation Service for the Knowledge Mesh Desktop application.

This module provides services for AI-powered document generation based on
the knowledge mesh.
"""

import asyncio
import logging
import os
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable
import uuid

from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus
from ..models.document import Document, DocumentType, DocumentStatus
from ..models.document_generation import (
    GenerationRequest, GeneratedContent, GenerationFormat, 
    GenerationTemplate, GenerationStatus
)
from ..models.relationship import Relationship, RelationshipType

logger = logging.getLogger(__name__)


class DocumentGenerationService:
    """
    Service for AI-powered document generation.
    
    This service generates documents based on the knowledge mesh,
    using AI to create summaries, reports, and other document types.
    """
    
    def __init__(self, config: Config, services: Optional[Dict[str, Any]] = None):
        """
        Initialize the document generation service.
        
        Args:
            config: Application configuration
            services: Other services that this service depends on
        """
        self.config = config
        self.services = services or {}
        self.is_running = False
        self.data_dir = Path(self.config.get("app.data_dir", "."))
        self.requests_dir = self.data_dir / "document_generation" / "requests"
        self.content_dir = self.data_dir / "document_generation" / "content"
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        self.requests_cache = {}
        self.content_cache = {}
        
        self.generation_queue = asyncio.Queue()
        self.generation_task = None
        
        self.max_concurrent_generations = self.config.get(
            "document_generation.max_concurrent_generations", 2
        )
        
        self.current_generations = set()
        
        self.ai_model = self.config.get("document_generation.ai_model", "gpt-4")
        self.ai_temperature = self.config.get("document_generation.ai_temperature", 0.7)
        self.ai_max_tokens = self.config.get("document_generation.ai_max_tokens", 4000)
        
        self.templates = {
            GenerationTemplate.SUMMARY: {
                "system_prompt": "You are an AI assistant that creates concise summaries of documents. "
                                "Your summaries should capture the key points and main ideas.",
                "user_prompt": "Please summarize the following documents:\n\n{document_content}",
            },
            GenerationTemplate.REPORT: {
                "system_prompt": "You are an AI assistant that creates detailed reports based on documents. "
                                "Your reports should be well-structured with sections, headings, and a "
                                "professional tone.",
                "user_prompt": "Please create a detailed report based on the following documents:\n\n{document_content}",
            },
            GenerationTemplate.NOTES: {
                "system_prompt": "You are an AI assistant that creates organized notes from documents. "
                                "Your notes should be clear, concise, and easy to reference.",
                "user_prompt": "Please create organized notes from the following documents:\n\n{document_content}",
            },
            GenerationTemplate.PRESENTATION: {
                "system_prompt": "You are an AI assistant that creates presentation outlines from documents. "
                                "Your outlines should include slide titles, bullet points, and speaker notes.",
                "user_prompt": "Please create a presentation outline based on the following documents:\n\n{document_content}",
            },
            GenerationTemplate.ARTICLE: {
                "system_prompt": "You are an AI assistant that creates well-written articles from documents. "
                                "Your articles should be engaging, informative, and have a clear structure.",
                "user_prompt": "Please create an article based on the following documents:\n\n{document_content}",
            },
            GenerationTemplate.EMAIL: {
                "system_prompt": "You are an AI assistant that creates professional emails from documents. "
                                "Your emails should be concise, clear, and have an appropriate tone.",
                "user_prompt": "Please create a professional email based on the following documents:\n\n{document_content}",
            },
            GenerationTemplate.CUSTOM: {
                "system_prompt": "You are an AI assistant that creates custom content based on documents. "
                                "Follow the user's instructions carefully.",
                "user_prompt": "{custom_prompt}",
            },
        }
    
    async def initialize(self):
        """Initialize the document generation service."""
        logger.info("Initializing document generation service")
        
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        self.document_processor_service = self.services.get("document_processor")
        self.knowledge_mesh_service = self.services.get("knowledge_mesh")
        self.vector_store_service = self.services.get("vector_store")
        self.llm_service = self.services.get("llm")
        
        await self._load_requests()
        await self._load_content()
        
        logger.info("Document generation service initialized")
    
    async def start(self):
        """Start the document generation service."""
        logger.info("Starting document generation service")
        self.is_running = True
        
        self.generation_task = asyncio.create_task(self._process_generation_queue())
        
        logger.info("Document generation service started")
    
    async def stop(self):
        """Stop the document generation service."""
        logger.info("Stopping document generation service")
        self.is_running = False
        
        if self.generation_task:
            self.generation_task.cancel()
            try:
                await self.generation_task
            except asyncio.CancelledError:
                pass
            self.generation_task = None
        
        for task in self.current_generations:
            task.cancel()
        
        self.current_generations.clear()
        
        logger.info("Document generation service stopped")
    
    async def _load_requests(self):
        """Load generation requests from disk."""
        logger.info("Loading generation requests")
        
        try:
            for request_file in self.requests_dir.glob("*.pkl"):
                try:
                    with open(request_file, "rb") as f:
                        request_dict = pickle.load(f)
                    
                    request = GenerationRequest.from_dict(request_dict)
                    self.requests_cache[request.id] = request
                    logger.debug(f"Loaded request: {request}")
                    
                    if request.status == GenerationStatus.PENDING:
                        await self.generation_queue.put(request.id)
                except Exception as e:
                    logger.error(f"Error loading request {request_file}: {e}", exc_info=True)
            
            logger.info(f"Loaded {len(self.requests_cache)} generation requests")
        except Exception as e:
            logger.error(f"Error loading requests: {e}", exc_info=True)
    
    async def _load_content(self):
        """Load generated content from disk."""
        logger.info("Loading generated content")
        
        try:
            for content_file in self.content_dir.glob("*.pkl"):
                try:
                    with open(content_file, "rb") as f:
                        content_dict = pickle.load(f)
                    
                    content = GeneratedContent.from_dict(content_dict)
                    self.content_cache[content.id] = content
                    logger.debug(f"Loaded content: {content}")
                except Exception as e:
                    logger.error(f"Error loading content {content_file}: {e}", exc_info=True)
            
            logger.info(f"Loaded {len(self.content_cache)} generated content items")
        except Exception as e:
            logger.error(f"Error loading content: {e}", exc_info=True)
    
    async def _save_request(self, request: GenerationRequest) -> bool:
        """
        Save a generation request to disk.
        
        Args:
            request: The request to save
            
        Returns:
            True if the request was saved successfully, False otherwise
        """
        try:
            request_path = self.requests_dir / f"{request.id}.pkl"
            
            with open(request_path, "wb") as f:
                pickle.dump(request.to_dict(), f)
            
            self.requests_cache[request.id] = request
            
            logger.info(f"Saved request: {request.id}")
            return True
        except Exception as e:
            logger.error(f"Error saving request: {e}", exc_info=True)
            return False
    
    async def _save_content(self, content: GeneratedContent) -> bool:
        """
        Save generated content to disk.
        
        Args:
            content: The content to save
            
        Returns:
            True if the content was saved successfully, False otherwise
        """
        try:
            content_path = self.content_dir / f"{content.id}.pkl"
            
            with open(content_path, "wb") as f:
                pickle.dump(content.to_dict(), f)
            
            self.content_cache[content.id] = content
            
            logger.info(f"Saved content: {content.id}")
            return True
        except Exception as e:
            logger.error(f"Error saving content: {e}", exc_info=True)
            return False
    
    async def create_generation_request(
        self,
        user_id: str,
        title: str,
        source_document_ids: List[str],
        format: Union[GenerationFormat, str],
        template: Union[GenerationTemplate, str],
        prompt: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[GenerationRequest]:
        """
        Create a new document generation request.
        
        Args:
            user_id: The ID of the user creating the request
            title: The title of the generated document
            source_document_ids: The IDs of the source documents
            format: The format of the generated document
            template: The template to use for generation
            prompt: Optional prompt to guide the generation
            parameters: Additional parameters for the generation
            metadata: Additional metadata for the request
            
        Returns:
            The created request, or None if creation failed
        """
        if not self.is_running:
            logger.warning("Document generation service is not running")
            return None
        
        try:
            if self.document_processor_service:
                for doc_id in source_document_ids:
                    document = await self.document_processor_service.get_document(doc_id)
                    
                    if not document:
                        logger.warning(f"Source document not found: {doc_id}")
                        return None
            
            request = GenerationRequest.create(
                user_id=user_id,
                title=title,
                source_document_ids=source_document_ids,
                format=format,
                template=template,
                prompt=prompt,
                parameters=parameters,
                metadata=metadata,
            )
            
            if await self._save_request(request):
                await self.generation_queue.put(request.id)
                
                publish(
                    EventType.DOCUMENT_GENERATION_REQUESTED,
                    {
                        "request_id": request.id,
                        "user_id": user_id,
                        "title": title,
                    },
                )
                
                logger.info(f"Created generation request: {request}")
                return request
            
            logger.warning(f"Failed to save generation request: {title}")
            return None
        except Exception as e:
            logger.error(f"Error creating generation request: {e}", exc_info=True)
            return None
    
    async def get_generation_request(self, request_id: str) -> Optional[GenerationRequest]:
        """
        Get a generation request by ID.
        
        Args:
            request_id: The ID of the request
            
        Returns:
            The request, or None if not found
        """
        if not self.is_running:
            logger.warning("Document generation service is not running")
            return None
        
        try:
            if request_id in self.requests_cache:
                return self.requests_cache[request_id]
            
            request_path = self.requests_dir / f"{request_id}.pkl"
            
            if not request_path.exists():
                logger.warning(f"Generation request not found: {request_id}")
                return None
            
            with open(request_path, "rb") as f:
                request_dict = pickle.load(f)
            
            request = GenerationRequest.from_dict(request_dict)
            
            self.requests_cache[request.id] = request
            
            return request
        except Exception as e:
            logger.error(f"Error getting generation request: {e}", exc_info=True)
            return None
    
    async def get_generated_content(self, content_id: str) -> Optional[GeneratedContent]:
        """
        Get generated content by ID.
        
        Args:
            content_id: The ID of the content
            
        Returns:
            The content, or None if not found
        """
        if not self.is_running:
            logger.warning("Document generation service is not running")
            return None
        
        try:
            if content_id in self.content_cache:
                return self.content_cache[content_id]
            
            content_path = self.content_dir / f"{content_id}.pkl"
            
            if not content_path.exists():
                logger.warning(f"Generated content not found: {content_id}")
                return None
            
            with open(content_path, "rb") as f:
                content_dict = pickle.load(f)
            
            content = GeneratedContent.from_dict(content_dict)
            
            self.content_cache[content.id] = content
            
            return content
        except Exception as e:
            logger.error(f"Error getting generated content: {e}", exc_info=True)
            return None
    
    async def get_request_content(self, request_id: str) -> Optional[GeneratedContent]:
        """
        Get the content for a generation request.
        
        Args:
            request_id: The ID of the request
            
        Returns:
            The content, or None if not found
        """
        if not self.is_running:
            logger.warning("Document generation service is not running")
            return None
        
        try:
            request = await self.get_generation_request(request_id)
            
            if not request:
                logger.warning(f"Generation request not found: {request_id}")
                return None
            
            if not request.result_document_id:
                logger.warning(f"Generation request has no result: {request_id}")
                return None
            
            for content in self.content_cache.values():
                if content.id == request.result_document_id:
                    return content
            
            content_path = self.content_dir / f"{request.result_document_id}.pkl"
            
            if not content_path.exists():
                logger.warning(f"Generated content not found: {request.result_document_id}")
                return None
            
            with open(content_path, "rb") as f:
                content_dict = pickle.load(f)
            
            content = GeneratedContent.from_dict(content_dict)
            
            self.content_cache[content.id] = content
            
            return content
        except Exception as e:
            logger.error(f"Error getting request content: {e}", exc_info=True)
            return None
    
    async def cancel_generation_request(self, request_id: str) -> bool:
        """
        Cancel a generation request.
        
        Args:
            request_id: The ID of the request to cancel
            
        Returns:
            True if the request was cancelled, False otherwise
        """
        if not self.is_running:
            logger.warning("Document generation service is not running")
            return False
        
        try:
            request = await self.get_generation_request(request_id)
            
            if not request:
                logger.warning(f"Generation request not found: {request_id}")
                return False
            
            if request.status != GenerationStatus.PENDING and request.status != GenerationStatus.PROCESSING:
                logger.warning(f"Generation request cannot be cancelled: {request_id}")
                return False
            
            request.update_status(GenerationStatus.CANCELLED)
            
            if await self._save_request(request):
                publish(
                    EventType.DOCUMENT_GENERATION_CANCELLED,
                    {
                        "request_id": request.id,
                        "user_id": request.user_id,
                        "title": request.title,
                    },
                )
                
                logger.info(f"Cancelled generation request: {request_id}")
                return True
            
            logger.warning(f"Failed to save generation request after cancellation: {request_id}")
            return False
        except Exception as e:
            logger.error(f"Error cancelling generation request: {e}", exc_info=True)
            return False
    
    async def get_user_requests(
        self,
        user_id: str,
        status: Optional[GenerationStatus] = None,
    ) -> List[GenerationRequest]:
        """
        Get generation requests for a user.
        
        Args:
            user_id: The ID of the user
            status: Filter by request status
            
        Returns:
            A list of requests
        """
        if not self.is_running:
            logger.warning("Document generation service is not running")
            return []
        
        try:
            requests = []
            
            for request in self.requests_cache.values():
                if request.user_id != user_id:
                    continue
                
                if status and request.status != status:
                    continue
                
                requests.append(request)
            
            requests.sort(key=lambda r: r.created_at, reverse=True)
            
            return requests
        except Exception as e:
            logger.error(f"Error getting user requests: {e}", exc_info=True)
            return []
    
    async def _process_generation_queue(self):
        """Process the generation queue."""
        logger.info("Starting generation queue processor")
        
        while self.is_running:
            try:
                request_id = await self.generation_queue.get()
                
                request = await self.get_generation_request(request_id)
                
                if not request:
                    logger.warning(f"Generation request not found: {request_id}")
                    self.generation_queue.task_done()
                    continue
                
                if request.status != GenerationStatus.PENDING:
                    logger.warning(f"Generation request is not pending: {request_id}")
                    self.generation_queue.task_done()
                    continue
                
                while (
                    len(self.current_generations) >= self.max_concurrent_generations
                    and self.is_running
                ):
                    self.current_generations = {
                        task for task in self.current_generations if not task.done()
                    }
                    
                    if len(self.current_generations) >= self.max_concurrent_generations:
                        await asyncio.sleep(1)
                
                if not self.is_running:
                    break
                
                generation_task = asyncio.create_task(
                    self._generate_document(request_id)
                )
                
                self.current_generations.add(generation_task)
                
                self.generation_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing generation queue: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info("Generation queue processor stopped")
    
    async def _generate_document(self, request_id: str):
        """
        Generate a document for a request.
        
        Args:
            request_id: The ID of the request
        """
        try:
            request = await self.get_generation_request(request_id)
            
            if not request:
                logger.warning(f"Generation request not found: {request_id}")
                return
            
            request.update_status(GenerationStatus.PROCESSING)
            await self._save_request(request)
            
            publish(
                EventType.DOCUMENT_GENERATION_STARTED,
                {
                    "request_id": request.id,
                    "user_id": request.user_id,
                    "title": request.title,
                },
            )
            
            logger.info(f"Starting document generation: {request_id}")
            
            source_documents = []
            
            for doc_id in request.source_document_ids:
                if self.document_processor_service:
                    document = await self.document_processor_service.get_document(doc_id)
                    
                    if document:
                        source_documents.append(document)
                    else:
                        logger.warning(f"Source document not found: {doc_id}")
            
            if not source_documents:
                logger.warning(f"No valid source documents for request: {request_id}")
                request.update_status(
                    GenerationStatus.FAILED,
                    error_message="No valid source documents found",
                )
                await self._save_request(request)
                return
            
            try:
                content = await self._generate_content(request, source_documents)
                
                if not content:
                    logger.warning(f"Failed to generate content for request: {request_id}")
                    request.update_status(
                        GenerationStatus.FAILED,
                        error_message="Failed to generate content",
                    )
                    await self._save_request(request)
                    return
                
                if await self._save_content(content):
                    request.update_status(
                        GenerationStatus.COMPLETED,
                        result_document_id=content.id,
                    )
                    await self._save_request(request)
                    
                    if self.document_processor_service:
                        document = await self._create_document_from_content(request, content)
                        
                        if document:
                            request.metadata["document_id"] = document.id
                            await self._save_request(request)
                    
                    publish(
                        EventType.DOCUMENT_GENERATION_COMPLETED,
                        {
                            "request_id": request.id,
                            "user_id": request.user_id,
                            "title": request.title,
                            "content_id": content.id,
                        },
                    )
                    
                    logger.info(f"Completed document generation: {request_id}")
                else:
                    logger.warning(f"Failed to save content for request: {request_id}")
                    request.update_status(
                        GenerationStatus.FAILED,
                        error_message="Failed to save generated content",
                    )
                    await self._save_request(request)
            except Exception as e:
                logger.error(f"Error generating document: {e}", exc_info=True)
                request.update_status(
                    GenerationStatus.FAILED,
                    error_message=str(e),
                )
                await self._save_request(request)
        except Exception as e:
            logger.error(f"Error in document generation task: {e}", exc_info=True)
    
    async def _generate_content(
        self,
        request: GenerationRequest,
        source_documents: List[Document],
    ) -> Optional[GeneratedContent]:
        """
        Generate content for a request.
        
        Args:
            request: The generation request
            source_documents: The source documents
            
        Returns:
            The generated content, or None if generation failed
        """
        try:
            template = self.templates.get(
                request.template, self.templates[GenerationTemplate.CUSTOM]
            )
            
            document_content = ""
            
            for doc in source_documents:
                document_content += f"--- Document: {doc.title} ---\n\n"
                document_content += doc.content
                document_content += "\n\n"
            
            system_prompt = template["system_prompt"]
            
            if request.template == GenerationTemplate.CUSTOM and request.prompt:
                user_prompt = request.prompt
            else:
                user_prompt = template["user_prompt"].format(
                    document_content=document_content,
                    custom_prompt=request.prompt or "",
                )
            
            if self.llm_service:
                generated_text = await self.llm_service.generate_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=self.ai_model,
                    temperature=self.ai_temperature,
                    max_tokens=self.ai_max_tokens,
                )
            else:
                logger.warning("LLM service not available, using fallback generation")
                generated_text = self._fallback_generation(request, source_documents)
            
            if not generated_text:
                logger.warning(f"Failed to generate text for request: {request.id}")
                return None
            
            content = GeneratedContent.create(
                request_id=request.id,
                content=generated_text,
                format=request.format,
                metadata={
                    "source_document_ids": request.source_document_ids,
                    "template": request.template.name,
                    "ai_model": self.ai_model,
                    "ai_temperature": self.ai_temperature,
                    "ai_max_tokens": self.ai_max_tokens,
                },
            )
            
            return content
        except Exception as e:
            logger.error(f"Error generating content: {e}", exc_info=True)
            return None
    
    def _fallback_generation(
        self,
        request: GenerationRequest,
        source_documents: List[Document],
    ) -> str:
        """
        Fallback generation when LLM service is not available.
        
        Args:
            request: The generation request
            source_documents: The source documents
            
        Returns:
            The generated text
        """
        result = f"# {request.title}\n\n"
        result += f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        result += "## Summary\n\n"
        result += "This document was generated based on the following sources:\n\n"
        
        for doc in source_documents:
            result += f"- {doc.title}\n"
        
        result += "\n"
        
        result += "## Document Contents\n\n"
        
        for doc in source_documents:
            result += f"### {doc.title}\n\n"
            
            content = doc.content
            if len(content) > 500:
                content = content[:500] + "...\n\n(content truncated)"
            
            result += content
            result += "\n\n"
        
        return result
    
    async def _create_document_from_content(
        self,
        request: GenerationRequest,
        content: GeneratedContent,
    ) -> Optional[Document]:
        """
        Create a document from generated content.
        
        Args:
            request: The generation request
            content: The generated content
            
        Returns:
            The created document, or None if creation failed
        """
        if not self.document_processor_service:
            logger.warning("Document processor service not available")
            return None
        
        try:
            doc_type = DocumentType.TXT
            
            if request.format == GenerationFormat.MARKDOWN:
                doc_type = DocumentType.MARKDOWN
            elif request.format == GenerationFormat.HTML:
                doc_type = DocumentType.HTML
            elif request.format == GenerationFormat.PDF:
                doc_type = DocumentType.PDF
            elif request.format == GenerationFormat.DOCX:
                doc_type = DocumentType.DOCX
            
            content_dir = self.data_dir / "temp"
            content_dir.mkdir(parents=True, exist_ok=True)
            
            file_extension = ".txt"
            
            if request.format == GenerationFormat.MARKDOWN:
                file_extension = ".md"
            elif request.format == GenerationFormat.HTML:
                file_extension = ".html"
            elif request.format == GenerationFormat.PDF:
                file_extension = ".pdf"
            elif request.format == GenerationFormat.DOCX:
                file_extension = ".docx"
            
            file_path = content_dir / f"{content.id}{file_extension}"
            
            with open(file_path, "w") as f:
                f.write(content.content)
            
            document = await self.document_processor_service.create_document(
                title=request.title,
                file_path=str(file_path),
                file_type=doc_type,
                metadata={
                    "generated": True,
                    "generation_request_id": request.id,
                    "source_document_ids": request.source_document_ids,
                    "template": request.template.name,
                    "format": request.format.name,
                },
            )
            
            if document:
                if self.knowledge_mesh_service:
                    for source_id in request.source_document_ids:
                        await self.knowledge_mesh_service.create_relationship(
                            document.id,
                            source_id,
                            RelationshipType.DERIVED_FROM,
                            metadata={
                                "generation_request_id": request.id,
                                "template": request.template.name,
                            },
                        )
                
                logger.info(f"Created document from generated content: {document.id}")
                return document
            
            logger.warning(f"Failed to create document from content: {content.id}")
            return None
        except Exception as e:
            logger.error(f"Error creating document from content: {e}", exc_info=True)
            return None

"""
Email search service for the Knowledge Mesh Desktop application.

This module provides services for searching emails using vector embeddings and metadata.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set, Callable, Union
import json

from src.core.config import Config
from src.core.events import EventType, publish_event
from src.models.email import Email, EmailFolder, EmailSearchQuery, EmailSearchResult
from src.services.vector_store import VectorStoreService


logger = logging.getLogger(__name__)


class EmailSearchService:
    """Service for searching emails using vector embeddings and metadata."""
    
    def __init__(self, config: Config, vector_store: VectorStoreService):
        """Initialize the email search service."""
        self.config = config
        self.vector_store = vector_store
        self.collection_name = "emails"
        self.search_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        asyncio.create_task(self._initialize_collection())
    
    async def _initialize_collection(self):
        """Initialize the vector store collection for emails."""
        try:
            collections = await self.vector_store.list_collections()
            
            if self.collection_name not in collections:
                await self.vector_store.create_collection(
                    name=self.collection_name,
                    dimension=384,  # Default embedding size
                    metadata_config={
                        "indexed": ["message_id", "subject", "from", "date", "folder", "document_id"]
                    }
                )
                
                logger.info(f"Created vector store collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store collection: {str(e)}")
    
    async def search(self, query: EmailSearchQuery) -> EmailSearchResult:
        """Search for emails using vector embeddings and metadata."""
        try:
            cache_key = self._get_cache_key(query)
            cached_result = self._get_from_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            query_embedding = await self.vector_store.generate_embedding(query.query_text)
            
            filter_expr = self._build_filter_expression(query)
            
            search_results = await self.vector_store.search_vectors(
                collection=self.collection_name,
                query_vector=query_embedding,
                limit=query.limit,
                offset=query.offset,
                filter_expr=filter_expr
            )
            
            emails = []
            for result in search_results.get("matches", []):
                email_id = result.get("id")
                if not email_id:
                    continue
                    
                email = await self._get_email_by_id(email_id)
                
                if email:
                    emails.append(email)
            
            result = EmailSearchResult.create(
                emails=emails,
                total_count=search_results.get("total", len(emails)),
                query=query
            )
            
            self._add_to_cache(cache_key, result)
            
            publish_event(EventType.EMAIL_SEARCH_COMPLETED, {
                "query": query.query_text,
                "result_count": len(emails),
                "total_count": search_results.get("total", len(emails)),
            })
            
            return result
        except Exception as e:
            logger.error(f"Failed to search emails: {str(e)}")
            return EmailSearchResult.create(emails=[], total_count=0, query=query)
    
    def _build_filter_expression(self, query: EmailSearchQuery) -> Dict[str, Any]:
        """Build filter expression for vector store search."""
        filter_expr = {}
        
        if query.folder is not None:
            filter_expr["folder"] = query.folder.name
        
        date_filter = {}
        if query.date_from is not None:
            date_filter["$gte"] = query.date_from.isoformat()
        if query.date_to is not None:
            date_filter["$lte"] = query.date_to.isoformat()
        
        if date_filter:
            filter_expr["date"] = date_filter
        
        if query.from_address is not None:
            filter_expr["from"] = {"$contains": query.from_address}
        
        if query.subject is not None:
            filter_expr["subject"] = {"$contains": query.subject}
        
        return filter_expr
    
    async def _get_email_by_id(self, email_id: str) -> Optional[Email]:
        """Get email by ID from database."""
        try:
            return None
        except Exception as e:
            logger.error(f"Failed to get email by ID: {str(e)}")
            return None
    
    def _get_cache_key(self, query: EmailSearchQuery) -> str:
        """Generate cache key for query."""
        query_dict = query.to_dict()
        return json.dumps(query_dict, sort_keys=True)
    
    def _get_from_cache(self, cache_key: str) -> Optional[EmailSearchResult]:
        """Get search result from cache."""
        if cache_key not in self.search_cache:
            return None
            
        cache_entry = self.search_cache[cache_key]
        
        if time.time() - cache_entry["timestamp"] > self.cache_ttl:
            del self.search_cache[cache_key]
            return None
            
        return cache_entry["result"]
    
    def _add_to_cache(self, cache_key: str, result: EmailSearchResult):
        """Add search result to cache."""
        self.search_cache[cache_key] = {
            "timestamp": time.time(),
            "result": result,
        }
        
        if len(self.search_cache) > 100:
            sorted_keys = sorted(self.search_cache.keys(), 
                                key=lambda k: self.search_cache[k]["timestamp"])
            
            for key in sorted_keys[:10]:
                del self.search_cache[key]
    
    async def get_recent_emails(self, limit: int = 10, folder: Optional[EmailFolder] = None) -> List[Email]:
        """Get recent emails."""
        try:
            filter_expr = {}
            
            if folder is not None:
                filter_expr["folder"] = folder.name
            
            search_results = await self.vector_store.search_vectors(
                collection=self.collection_name,
                query_vector=None,  # No query vector for metadata-only search
                limit=limit,
                filter_expr=filter_expr,
                sort_by="date",
                sort_order="desc"
            )
            
            emails = []
            for result in search_results.get("matches", []):
                email_id = result.get("id")
                if not email_id:
                    continue
                    
                email = await self._get_email_by_id(email_id)
                
                if email:
                    emails.append(email)
            
            return emails
        except Exception as e:
            logger.error(f"Failed to get recent emails: {str(e)}")
            return []
    
    async def get_similar_emails(self, email: Email, limit: int = 10) -> List[Email]:
        """Get emails similar to the given email."""
        try:
            if not email.vector_embedding:
                from src.services.email_processor import EmailProcessorService
                email_processor = EmailProcessorService(self.config, None, None, self.vector_store)
                email.vector_embedding = await email_processor.generate_embedding(email)
            
            search_results = await self.vector_store.search_vectors(
                collection=self.collection_name,
                query_vector=email.vector_embedding,
                limit=limit + 1,  # Add 1 to exclude the email itself
                filter_expr={}
            )
            
            emails = []
            for result in search_results.get("matches", []):
                email_id = result.get("id")
                if not email_id or email_id == str(email.id):
                    continue
                    
                similar_email = await self._get_email_by_id(email_id)
                
                if similar_email:
                    emails.append(similar_email)
                    
                    if len(emails) >= limit:
                        break
            
            return emails
        except Exception as e:
            logger.error(f"Failed to get similar emails: {str(e)}")
            return []
    
    async def get_email_threads(self, conversation_id: str, limit: int = 100) -> List[Email]:
        """Get emails in the same thread."""
        try:
            filter_expr = {
                "conversation_id": conversation_id
            }
            
            search_results = await self.vector_store.search_vectors(
                collection=self.collection_name,
                query_vector=None,  # No query vector for metadata-only search
                limit=limit,
                filter_expr=filter_expr,
                sort_by="date",
                sort_order="asc"
            )
            
            emails = []
            for result in search_results.get("matches", []):
                email_id = result.get("id")
                if not email_id:
                    continue
                    
                email = await self._get_email_by_id(email_id)
                
                if email:
                    emails.append(email)
            
            return emails
        except Exception as e:
            logger.error(f"Failed to get email thread: {str(e)}")
            return []
    
    async def get_email_stats(self) -> Dict[str, Any]:
        """Get email statistics."""
        try:
            total_count = await self.vector_store.get_collection_count(self.collection_name)
            
            folder_counts = {}
            for folder in EmailFolder:
                count = await self.vector_store.get_collection_count(
                    self.collection_name,
                    filter_expr={"folder": folder.name}
                )
                folder_counts[folder.name] = count
            
            date_ranges = [
                ("today", datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), datetime.now()),
                ("yesterday", (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0), 
                 datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)),
                ("this_week", (datetime.now() - timedelta(days=datetime.now().weekday())).replace(hour=0, minute=0, second=0, microsecond=0), 
                 datetime.now()),
                ("last_week", (datetime.now() - timedelta(days=datetime.now().weekday() + 7)).replace(hour=0, minute=0, second=0, microsecond=0), 
                 (datetime.now() - timedelta(days=datetime.now().weekday())).replace(hour=0, minute=0, second=0, microsecond=0)),
                ("this_month", datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0), 
                 datetime.now()),
                ("last_month", (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0), 
                 datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)),
            ]
            
            date_counts = {}
            for name, start_date, end_date in date_ranges:
                count = await self.vector_store.get_collection_count(
                    self.collection_name,
                    filter_expr={
                        "date": {
                            "$gte": start_date.isoformat(),
                            "$lt": end_date.isoformat(),
                        }
                    }
                )
                date_counts[name] = count
            
            return {
                "total_count": total_count,
                "folder_counts": folder_counts,
                "date_counts": date_counts,
            }
        except Exception as e:
            logger.error(f"Failed to get email stats: {str(e)}")
            return {
                "total_count": 0,
                "folder_counts": {},
                "date_counts": {},
            }

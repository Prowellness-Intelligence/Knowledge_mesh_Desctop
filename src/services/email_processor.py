"""
Email processor service for the Knowledge Mesh Desktop application.

This module provides services for processing emails, extracting content, and preparing for indexing.
"""

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set, Callable
from uuid import UUID

from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
import numpy as np

from src.core.config import Config
from src.core.events import EventType, publish_event
from src.models.document import Document
from src.models.email import Email, EmailAttachment, EmailFolder
from src.services.document_processor import DocumentProcessorService
from src.services.email_connector import EmailConnectorService
from src.services.vector_store import VectorStoreService


logger = logging.getLogger(__name__)


class EmailProcessorService:
    """Service for processing emails, extracting content, and preparing for indexing."""
    
    def __init__(self, config: Config, email_connector: EmailConnectorService, 
                document_processor: DocumentProcessorService, vector_store: VectorStoreService):
        """Initialize the email processor service."""
        self.config = config
        self.email_connector = email_connector
        self.document_processor = document_processor
        self.vector_store = vector_store
        
        self.email_connector.register_email_processor(self.process_email)
        
        self._initialize_nltk()
        
        self.processed_emails = set()
    
    def _initialize_nltk(self):
        """Initialize NLTK resources."""
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
        except Exception as e:
            logger.warning(f"Failed to download NLTK resources: {str(e)}")
    
    async def process_email(self, email_obj: Email):
        """Process an email for indexing."""
        if str(email_obj.id) in self.processed_emails:
            return
            
        try:
            document = email_obj.to_document()
            
            processed_document = await self.document_processor.process_document(document)
            
            email_obj.document_id = processed_document.id
            
            embedding = await self.generate_embedding(email_obj)
            email_obj.vector_embedding = embedding
            
            await self.vector_store.store_vectors(
                collection="emails",
                ids=[str(email_obj.id)],
                vectors=[embedding],
                metadata=[{
                    "message_id": email_obj.message_id,
                    "subject": email_obj.subject,
                    "from": email_obj.from_address.address if email_obj.from_address else "",
                    "date": email_obj.date.isoformat(),
                    "folder": email_obj.folder.name,
                    "document_id": str(email_obj.document_id) if email_obj.document_id else "",
                }]
            )
            
            self.processed_emails.add(str(email_obj.id))
            
            publish_event(EventType.EMAIL_PROCESSED, {
                "email_id": str(email_obj.id),
                "document_id": str(email_obj.document_id) if email_obj.document_id else None,
            })
            
            logger.info(f"Processed email: {email_obj.subject}")
        except Exception as e:
            logger.error(f"Failed to process email: {str(e)}")
    
    async def process_emails(self, emails: List[Email]):
        """Process multiple emails for indexing."""
        for email in emails:
            await self.process_email(email)
    
    async def generate_embedding(self, email_obj: Email) -> List[float]:
        """Generate vector embedding for an email."""
        try:
            text = self._prepare_text_for_embedding(email_obj)
            
            embedding = await self.vector_store.generate_embedding(text)
            
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding for email: {str(e)}")
            return [0.0] * 384  # Default embedding size
    
    def _prepare_text_for_embedding(self, email_obj: Email) -> str:
        """Prepare email text for embedding generation."""
        text_parts = [
            f"Subject: {email_obj.subject}",
            f"From: {email_obj.from_address.name if email_obj.from_address and email_obj.from_address.name else ''} {email_obj.from_address.address if email_obj.from_address else ''}",
        ]
        
        if email_obj.to_addresses:
            to_text = "To: " + ", ".join([f"{addr.name if addr.name else ''} {addr.address}" for addr in email_obj.to_addresses])
            text_parts.append(to_text)
        
        if email_obj.body_text:
            clean_text = self._clean_text(email_obj.body_text)
            text_parts.append(clean_text)
        elif email_obj.body_html:
            text = self._html_to_text(email_obj.body_html)
            clean_text = self._clean_text(text)
            text_parts.append(clean_text)
        
        full_text = "\n\n".join(text_parts)
        
        return full_text
    
    def _clean_text(self, text: str) -> str:
        """Clean text for embedding generation."""
        text = re.sub(r'\s+', ' ', text)
        
        text = re.sub(r'--+\s*\n.*', '', text, flags=re.DOTALL)
        text = re.sub(r'Sent from my .*', '', text)
        
        text = re.sub(r'On .* wrote:.*', '', text, flags=re.DOTALL)
        text = re.sub(r'>.+', '', text)
        
        text = re.sub(r'https?://\S+', '', text)
        
        return text.strip()
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            for script in soup(["script", "style"]):
                script.extract()
            
            text = soup.get_text()
            
            lines = (line.strip() for line in text.splitlines())
            
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Failed to convert HTML to text: {str(e)}")
            return ""
    
    async def extract_entities(self, email_obj: Email) -> Dict[str, List[str]]:
        """Extract entities from an email."""
        try:
            text = self._prepare_text_for_embedding(email_obj)
            
            tokens = word_tokenize(text)
            
            stop_words = set(stopwords.words('english'))
            filtered_tokens = [w for w in tokens if w.lower() not in stop_words]
            
            lemmatizer = WordNetLemmatizer()
            lemmatized_tokens = [lemmatizer.lemmatize(w) for w in filtered_tokens]
            
            entities = {
                "people": [],
                "organizations": [],
                "locations": [],
                "dates": [],
                "keywords": [],
            }
            
            token_freq = {}
            for token in lemmatized_tokens:
                if token.isalnum() and len(token) > 2:
                    token_freq[token] = token_freq.get(token, 0) + 1
            
            keywords = sorted(token_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            entities["keywords"] = [k[0] for k in keywords]
            
            return entities
        except Exception as e:
            logger.error(f"Failed to extract entities from email: {str(e)}")
            return {
                "people": [],
                "organizations": [],
                "locations": [],
                "dates": [],
                "keywords": [],
            }
    
    async def analyze_sentiment(self, email_obj: Email) -> Dict[str, Any]:
        """Analyze sentiment of an email."""
        try:
            text = self._prepare_text_for_embedding(email_obj)
            
            positive_words = {"good", "great", "excellent", "happy", "positive", "thanks", "thank", "appreciate"}
            negative_words = {"bad", "poor", "terrible", "unhappy", "negative", "problem", "issue", "complaint"}
            
            tokens = word_tokenize(text.lower())
            
            positive_count = sum(1 for token in tokens if token in positive_words)
            negative_count = sum(1 for token in tokens if token in negative_words)
            
            total = positive_count + negative_count
            if total == 0:
                sentiment_score = 0.0
            else:
                sentiment_score = (positive_count - negative_count) / total
            
            if sentiment_score > 0.2:
                sentiment = "positive"
            elif sentiment_score < -0.2:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            return {
                "sentiment": sentiment,
                "score": sentiment_score,
                "positive_count": positive_count,
                "negative_count": negative_count,
            }
        except Exception as e:
            logger.error(f"Failed to analyze sentiment of email: {str(e)}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "positive_count": 0,
                "negative_count": 0,
            }
    
    async def extract_attachments(self, email_obj: Email) -> List[Document]:
        """Extract and process attachments from an email."""
        if not email_obj.has_attachments or not email_obj.attachments:
            return []
            
        documents = []
        
        for attachment in email_obj.attachments:
            try:
                if attachment.document_id:
                    continue
                    
                
                from src.models.document import DocumentType, DocumentMetadata
                
                metadata = DocumentMetadata(
                    title=attachment.filename,
                    author=email_obj.from_address.name if email_obj.from_address and email_obj.from_address.name else 
                           email_obj.from_address.address if email_obj.from_address else "Unknown",
                    created_date=email_obj.date,
                    modified_date=email_obj.received_date,
                    source_type="email_attachment",
                    source_id=str(email_obj.id),
                    custom_metadata={
                        "email_id": str(email_obj.id),
                        "email_subject": email_obj.subject,
                        "content_type": attachment.content_type,
                        "size": str(attachment.size),
                    }
                )
                
                document = Document.create(
                    title=attachment.filename,
                    content=f"Attachment from email: {email_obj.subject}",
                    document_type=DocumentType.ATTACHMENT,
                    metadata=metadata,
                )
                
                processed_document = await self.document_processor.process_document(document)
                
                attachment.document_id = processed_document.id
                
                documents.append(processed_document)
            except Exception as e:
                logger.error(f"Failed to extract attachment: {str(e)}")
        
        return documents

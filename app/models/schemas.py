"""Pydantic request/response schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


# --- Chat Schemas ---

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User query text")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of chunks to retrieve")


class SourceReference(BaseModel):
    document_id: str
    filename: str
    page: Optional[int] = None
    source_url: Optional[str] = None
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    conversation_id: str


# --- Document Schemas ---

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    chunk_count: int
    upload_date: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


# --- Conversation Schemas ---

class ConversationResponse(BaseModel):
    conversation_id: str
    messages: list["MessageResponse"]


class MessageResponse(BaseModel):
    role: str
    content: str
    sources: list[SourceReference] = []
    created_at: datetime


# --- Health ---

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"

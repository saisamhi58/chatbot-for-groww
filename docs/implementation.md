# Implementation Guide — RAG Chatbot

| Field | Value |
|---|---|
| **Product Name** | RAG Chatbot |
| **Document Version** | 1.0 |
| **Date** | 2026-10-01 |
| **Author** | — |
| **Status** | Draft |
| **References** | [PRD](./prd.md) · [Architecture](./architecture.md) |

---

## How to Use This Document

This guide is designed to be used with **Cursor** (AI coding assistant). Each phase provides:

- **Objective** — What to accomplish
- **Files to Create** — Exact file paths
- **Step-by-Step Instructions** — Detailed implementation steps with code patterns
- **Verification** — How to confirm the phase works
- **Cursor Prompt** — A ready-to-paste prompt for Cursor

### Cursor Usage Pattern

For each phase, paste the **Cursor Prompt** into Cursor's chat. Cursor will generate the code. Then verify using the **Verification** steps.

---

## Phase 1: Foundation — Project Setup, Configuration & Database

### Objective

Set up the project structure, install dependencies, configure environment variables, define database models, and run initial migrations.

### Files to Create

```
ragchatbot/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   └── __init__.py
│   │   ├── dependencies.py
│   │   └── middleware.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── schemas.py
│   ├── services/
│   │   └── __init__.py
│   ├── ingestion/
│   │   └── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── vector_client.py
│   └── worker/
│       └── __init__.py
├── alembic/
│   └── env.py
├── tests/
│   └── __init__.py
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

### Step-by-Step Instructions

#### Step 1.1: Create `requirements.txt`

```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
sqlalchemy==2.0.23
alembic==1.12.1
asyncpg==0.29.0
psycopg2-binary==2.9.9
chromadb==0.4.18
openai==1.3.7
celery==5.3.4
redis==5.0.1
python-multipart==0.0.6
python-dotenv==1.0.0
structlog==23.2.0
pdfplumber==0.10.3
python-docx==1.1.0
beautifulsoup4==4.12.2
tiktoken==0.5.1
tenacity==8.2.3
prometheus-client==0.19.0
```

#### Step 1.2: Create `.env.example`

```env
# .env.example
ENVIRONMENT=dev
DEBUG=true
SECRET_KEY=change-me-in-production

DATABASE_URL=postgresql://ragchatbot:ragchatbot@localhost:5432/ragchatbot
REDIS_URL=redis://localhost:6379/0

VECTOR_DB_HOST=localhost
VECTOR_DB_PORT=8001
VECTOR_DB_COLLECTION=knowledge_base

OPENAI_API_KEY=sk-your-key-here
OPENAI_LLM_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

STORAGE_TYPE=local
STORAGE_PATH=./data/documents

CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=5
SIMILARITY_THRESHOLD=0.7
MAX_CONTEXT_TOKENS=8000

RATE_LIMIT_RPM=60
```

#### Step 1.3: Create `app/config.py`

```python
# app/config.py
"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    environment: str = "dev"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql://ragchatbot:ragchatbot@localhost:5432/ragchatbot"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Vector DB
    vector_db_host: str = "localhost"
    vector_db_port: int = 8001
    vector_db_collection: str = "knowledge_base"

    # OpenAI
    openai_api_key: str = ""
    openai_llm_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # Storage
    storage_type: str = "local"
    storage_path: str = "./data/documents"

    # RAG Config
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    similarity_threshold: float = 0.7
    max_context_tokens: int = 8000

    # Rate Limiting
    rate_limit_rpm: int = 60

    # CORS
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

#### Step 1.4: Create `app/models/database.py`

```python
# app/models/database.py
"""SQLAlchemy database models."""

import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    BigInteger,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    storage_path = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)
    uploaded_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=list)
    feedback = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=60)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### Step 1.5: Create `app/models/schemas.py`

```python
# app/models/schemas.py
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
```

#### Step 1.6: Create `app/db/session.py`

```python
# app/db/session.py
"""Database session management."""

from app.models.database import SessionLocal, engine, Base


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Get a new database session."""
    return SessionLocal()
```

#### Step 1.7: Create `app/db/vector_client.py`

```python
# app/db/vector_client.py
"""ChromaDB vector database client."""

import chromadb
from chromadb.config import Settings
from app.config import get_settings

settings = get_settings()


def get_chroma_client():
    """Get or create a ChromaDB client."""
    client = chromadb.HttpClient(
        host=settings.vector_db_host,
        port=settings.vector_db_port,
    )
    return client


def get_or_create_collection():
    """Get or create the knowledge base collection."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=settings.vector_db_collection,
        metadata={"hnsw:space": "cosine"},
    )
    return collection
```

#### Step 1.8: Create `app/core/exceptions.py`

```python
# app/core/exceptions.py
"""Custom application exceptions."""


class RAGException(Exception):
    """Base exception for RAG application."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(RAGException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class AuthenticationError(RAGException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class RateLimitError(RAGException):
    def __init__(self, message: str = "Too many requests"):
        super().__init__(message, status_code=429)


class NotFoundError(RAGException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class LLMServiceError(RAGException):
    def __init__(self, message: str = "AI service unavailable"):
        super().__init__(message, status_code=502)


class VectorDBError(RAGException):
    def __init__(self, message: str = "Search service unavailable"):
        super().__init__(message, status_code=503)
```

#### Step 1.9: Create `app/core/logging.py`

```python
# app/core/logging.py
"""Structured logging configuration."""

import structlog
import logging
import sys


def setup_logging():
    """Configure structured logging."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "ragchatbot"):
    """Get a structured logger."""
    return structlog.get_logger(name)
```

#### Step 1.10: Create `app/core/security.py`

```python
# app/core/security.py
"""Security utilities: auth, rate limiting, input sanitization."""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional

from app.models.database import APIKey, SessionLocal
from app.core.exceptions import AuthenticationError, RateLimitError


# --- API Key Authentication ---

def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(api_key: str) -> Optional[APIKey]:
    """Verify an API key against the database."""
    if not api_key:
        raise AuthenticationError("API key is required")

    key_hash = hash_api_key(api_key)
    db = SessionLocal()
    try:
        db_key = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        ).first()

        if not db_key:
            raise AuthenticationError("Invalid API key")

        if db_key.expires_at and db_key.expires_at < datetime.utcnow():
            raise AuthenticationError("API key has expired")

        return db_key
    finally:
        db.close()


# --- Rate Limiting (simple in-memory, use Redis in production) ---

_rate_limit_store: dict[str, list[datetime]] = {}


def check_rate_limit(api_key: str, rpm: int = 60):
    """Check if the request is within rate limits."""
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=1)

    if api_key not in _rate_limit_store:
        _rate_limit_store[api_key] = []

    # Remove old entries
    _rate_limit_store[api_key] = [
        t for t in _rate_limit_store[api_key] if t > window_start
    ]

    if len(_rate_limit_store[api_key]) >= rpm:
        raise RateLimitError(f"Rate limit exceeded: {rpm} requests per minute")

    _rate_limit_store[api_key].append(now)


# --- Input Sanitization ---

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?prior\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"human\s*:\s*",
    r"<\s*system\s*>",
    r"<\s*/\s*system\s*>",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
]


def sanitize_input(text: str) -> str:
    """Remove potential prompt injection patterns from user input."""
    sanitized = text
    for pattern in PROMPT_INJECTION_PATTERNS:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
    return sanitized.strip()


def validate_query(query: str) -> str:
    """Validate and sanitize a user query."""
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    if len(query) > 2000:
        raise ValueError("Query exceeds maximum length of 2000 characters")
    return sanitize_input(query)
```

#### Step 1.11: Create `app/api/dependencies.py`

```python
# app/api/dependencies.py
"""FastAPI dependencies."""

from fastapi import Header, Request
from app.core.security import verify_api_key, check_rate_limit
from app.models.database import APIKey


async def get_current_api_key(x_api_key: str = Header(None)) -> APIKey:
    """Dependency to validate API key from header."""
    api_key = verify_api_key(x_api_key)
    check_rate_limit(x_api_key, api_key.rate_limit)
    return api_key
```

#### Step 1.12: Create `app/api/middleware.py`

```python
# app/api/middleware.py
"""Custom FastAPI middleware."""

import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import get_logger

logger = get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing and request ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        logger.info(
            "request_processed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )

        response.headers["X-Request-ID"] = request_id
        return response
```

#### Step 1.13: Create `app/main.py`

```python
# app/main.py
"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.exceptions import RAGException
from app.core.logging import setup_logging, get_logger
from app.api.middleware import RequestLoggingMiddleware
from app.api.routes import chat, documents, conversations, health
from app.db.session import init_db

settings = get_settings()
setup_logging()
logger = get_logger()

app = FastAPI(
    title="RAG Chatbot API",
    description="Retrieval-Augmented Generation Chatbot",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging
app.add_middleware(RequestLoggingMiddleware)

# Exception handler
@app.exception_handler(RAGException)
async def rag_exception_handler(request: Request, exc: RAGException):
    logger.error(
        "request_error",
        request_id=getattr(request.state, "request_id", "unknown"),
        error=exc.message,
        status_code=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "request_id": getattr(request.state, "request_id", None)},
    )

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(conversations.router, prefix="/api", tags=["Conversations"])


@app.on_event("startup")
async def startup_event():
    logger.info("application_starting", environment=settings.environment)
    init_db()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("application_shutting_down")
```

#### Step 1.14: Create `app/api/routes/health.py`

```python
# app/api/routes/health.py
"""Health check endpoints."""

from fastapi import APIRouter
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy")
```

#### Step 1.15: Create `docker-compose.yml`

```yaml
# docker-compose.yml
version: "3.9"

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: ragchatbot
      POSTGRES_PASSWORD: ragchatbot
      POSTGRES_DB: ragchatbot
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

volumes:
  postgres_data:
  chroma_data:
```

#### Step 1.16: Create `Dockerfile`

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Step 1.17: Create placeholder route files

```python
# app/api/routes/chat.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/chat")
async def chat():
    return {"message": "Chat endpoint - to be implemented in Phase 4"}
```

```python
# app/api/routes/documents.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/documents")
async def upload_document():
    return {"message": "Document upload - to be implemented in Phase 2"}

@router.get("/documents")
async def list_documents():
    return {"documents": []}
```

```python
# app/api/routes/conversations.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    return {"conversation_id": conversation_id, "messages": []}
```

### Verification

```bash
# 1. Start infrastructure
docker-compose up -d postgres redis chroma

# 2. Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Copy environment file
cp .env.example .env
# Edit .env with your OpenAI API key

# 4. Start the application
uvicorn app.main:app --reload --port 8000

# 5. Test health endpoint
curl http://localhost:8000/health
# Expected: {"status": "healthy", "version": "1.0.0"}

# 6. Check API docs
# Open http://localhost:8000/docs in browser
```

### Cursor Prompt for Phase 1

```
I'm building a RAG Chatbot using FastAPI, PostgreSQL, ChromaDB, and OpenAI.
Please implement Phase 1: Foundation — Project Setup, Configuration & Database.

Create the following files with the exact content I specify:

1. requirements.txt — with FastAPI, SQLAlchemy, ChromaDB, OpenAI, Celery, Redis, pdfplumber, python-docx, beautifulsoup4, tiktoken, tenacity, structlog, prometheus-client
2. .env.example — with all environment variables (DATABASE_URL, REDIS_URL, OPENAI_API_KEY, VECTOR_DB settings, RAG config, etc.)
3. app/config.py — Pydantic Settings class that loads from .env
4. app/models/database.py — SQLAlchemy models: Document, Conversation, Message, APIKey tables with proper columns and relationships
5. app/models/schemas.py — Pydantic schemas: ChatRequest, ChatResponse, SourceReference, DocumentUploadResponse, DocumentResponse, HealthResponse
6. app/db/session.py — init_db() and get_session() functions
7. app/db/vector_client.py — ChromaDB client with get_chroma_client() and get_or_create_collection()
8. app/core/exceptions.py — Custom exceptions: RAGException, ValidationError, AuthenticationError, RateLimitError, NotFoundError, LLMServiceError, VectorDBError
9. app/core/logging.py — structlog configuration with JSON renderer
10. app/core/security.py — API key hashing/verification, rate limiting, input sanitization with prompt injection patterns
11. app/api/dependencies.py — FastAPI dependency for API key validation
12. app/api/middleware.py — Request logging middleware with request ID and timing
13. app/main.py — FastAPI app with CORS, exception handler, middleware, router includes, startup/shutdown events
14. app/api/routes/health.py — GET /health endpoint
15. app/api/routes/chat.py — placeholder POST /chat endpoint
16. app/api/routes/documents.py — placeholder POST /documents and GET /documents endpoints
17. app/api/routes/conversations.py — placeholder GET /conversations/{id} endpoint
18. docker-compose.yml — postgres:15, redis:7, chromadb/chroma:latest
19. Dockerfile — python:3.11-slim based
20. All __init__.py files for packages

Make sure all imports are correct and the project structure is clean.
```

---

## Phase 2: Document Ingestion Pipeline

### Objective

Implement the full document ingestion pipeline: file upload, text extraction, chunking, embedding generation, and vector DB indexing.

### Files to Create/Modify

```
app/ingestion/
├── __init__.py
├── parser.py          # NEW
├── chunker.py         # NEW
├── embedder.py        # NEW
└── indexer.py         # NEW

app/worker/
├── __init__.py
└── tasks.py           # NEW

app/api/routes/
└── documents.py       # MODIFY
```

### Step-by-Step Instructions

#### Step 2.1: Create `app/ingestion/parser.py`

```python
# app/ingestion/parser.py
"""Document text extraction for multiple file types."""

import os
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    """Result of parsing a document."""
    text: str
    pages: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class DocumentParser:
    """Parse various document formats into plain text."""

    SUPPORTED_TYPES = {"pdf", "docx", "txt", "md", "html"}

    def parse(self, file_path: str, file_type: str) -> ParsedDocument:
        """Parse a file based on its type."""
        if file_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported file type: {file_type}")

        parser_method = getattr(self, f"_parse_{file_type}")
        return parser_method(file_path)

    def _parse_pdf(self, file_path: str) -> ParsedDocument:
        import pdfplumber

        pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)

        return ParsedDocument(
            text="\n\n".join(pages),
            pages=pages,
            metadata={"page_count": len(pages)},
        )

    def _parse_docx(self, file_path: str) -> ParsedDocument:
        from docx import Document as DocxDocument

        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        return ParsedDocument(
            text="\n\n".join(paragraphs),
            pages=[],
            metadata={"paragraph_count": len(paragraphs)},
        )

    def _parse_txt(self, file_path: str) -> ParsedDocument:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        return ParsedDocument(
            text=text,
            pages=[text],
            metadata={},
        )

    def _parse_md(self, file_path: str) -> ParsedDocument:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        return ParsedDocument(
            text=text,
            pages=[text],
            metadata={},
        )

    def _parse_html(self, file_path: str) -> ParsedDocument:
        from bs4 import BeautifulSoup

        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text(separator="\n", strip=True)

        return ParsedDocument(
            text=text,
            pages=[text],
            metadata={},
        )
```

#### Step 2.2: Create `app/ingestion/chunker.py`

```python
# app/ingestion/chunker.py
"""Text chunking strategy for document segmentation."""

from dataclasses import dataclass, field
from typing import Optional
import re


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    text: str
    chunk_index: int
    token_count: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None


class RecursiveTextChunker:
    """Split text into overlapping chunks using recursive character splitting."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(
        self,
        text: str,
        pages: Optional[list[str]] = None,
    ) -> list[TextChunk]:
        """Split text into chunks with overlap."""
        # Split into paragraphs first
        paragraphs = self._split_paragraphs(text)

        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            if current_size + para_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        chunk_index=chunk_index,
                        token_count=self._count_tokens(chunk_text),
                    )
                )
                chunk_index += 1

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = [overlap_text] if overlap_text else []
                current_size = self._count_tokens(overlap_text) if overlap_text else 0

            current_chunk.append(para)
            current_size += para_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(
                TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    token_count=self._count_tokens(chunk_text),
                )
            )

        # Add page numbers if pages are provided
        if pages:
            chunks = self._assign_page_numbers(chunks, pages)

        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        # Split on double newlines or more
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken (cl100k_base for OpenAI models)."""
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            # Fallback: approximate 1 token = 4 characters
            return len(text) // 4

    def _get_overlap_text(self, current_chunk: list[str]) -> str:
        """Get overlap text from the end of the current chunk."""
        if not current_chunk:
            return ""

        overlap_tokens = 0
        overlap_parts = []

        for para in reversed(current_chunk):
            para_tokens = self._count_tokens(para)
            if overlap_tokens + para_tokens > self.chunk_overlap:
                break
            overlap_parts.insert(0, para)
            overlap_tokens += para_tokens

        return "\n\n".join(overlap_parts)

    def _assign_page_numbers(
        self, chunks: list[TextChunk], pages: list[str]
    ) -> list[TextChunk]:
        """Assign page numbers to chunks based on content matching."""
        page_texts = pages

        for chunk in chunks:
            chunk_start = chunk.text[:100]  # Use first 100 chars for matching
            for i, page_text in enumerate(page_texts):
                if chunk_start in page_text:
                    chunk.page_number = i + 1
                    break

        return chunks
```

#### Step 2.3: Create `app/ingestion/embedder.py`

```python
# app/ingestion/embedder.py
"""OpenAI embedding generation."""

from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import get_settings

settings = get_settings()


class OpenAIEmbedder:
    """Generate embeddings using OpenAI's embedding API."""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings
```

#### Step 2.4: Create `app/ingestion/indexer.py`

```python
# app/ingestion/indexer.py
"""Index document chunks into the vector database."""

import uuid
from datetime import datetime
from app.db.vector_client import get_or_create_collection
from app.ingestion.embedder import OpenAIEmbedder
from app.ingestion.chunker import TextChunk


class VectorIndexer:
    """Index text chunks into ChromaDB."""

    def __init__(self):
        self.collection = get_or_create_collection()
        self.embedder = OpenAIEmbedder()

    def index_chunks(
        self,
        chunks: list[TextChunk],
        document_id: str,
        filename: str,
    ) -> int:
        """Index a list of chunks into the vector database."""
        if not chunks:
            return 0

        # Generate embeddings in batch
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedder.embed_batch(texts)

        # Prepare records for ChromaDB
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = []
        for chunk in chunks:
            metadatas.append({
                "document_id": document_id,
                "filename": filename,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number or 0,
                "section_title": chunk.section_title or "",
                "token_count": chunk.token_count,
                "created_at": datetime.utcnow().isoformat(),
            })

        # Upsert into ChromaDB
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        return len(chunks)

    def delete_document_chunks(self, document_id: str) -> int:
        """Delete all chunks associated with a document."""
        result = self.collection.get(where={"document_id": document_id})
        ids = result.get("ids", [])
        if ids:
            self.collection.delete(ids=ids)
        return len(ids)
```

#### Step 2.5: Create `app/worker/tasks.py`

```python
# app/worker/tasks.py
"""Celery tasks for async document ingestion."""

import os
import shutil
from celery import Celery
from app.config import get_settings
from app.models.database import SessionLocal, Document
from app.ingestion.parser import DocumentParser
from app.ingestion.chunker import RecursiveTextChunker
from app.ingestion.indexer import VectorIndexer

settings = get_settings()

celery_app = Celery(
    "ragchatbot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


@celery_app.task(bind=True, max_retries=3)
def process_document(self, document_id: str, file_path: str, file_type: str):
    """Process and index a document."""
    db = SessionLocal()
    try:
        # Update status to processing
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        document.status = "processing"
        db.commit()

        # Parse document
        parser = DocumentParser()
        parsed = parser.parse(file_path, file_type)

        # Chunk text
        chunker = RecursiveTextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunks = chunker.chunk_text(parsed.text, parsed.pages)

        # Index chunks
        indexer = VectorIndexer()
        chunk_count = indexer.index_chunks(
            chunks=chunks,
            document_id=str(document_id),
            filename=document.filename,
        )

        # Update document status
        document.status = "indexed"
        document.chunk_count = chunk_count
        db.commit()

        # Clean up uploaded file (optional)
        # os.remove(file_path)

        return {"document_id": document_id, "chunk_count": chunk_count}

    except Exception as exc:
        document.status = "failed"
        document.error_message = str(exc)
        db.commit()

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()
```

#### Step 2.6: Modify `app/api/routes/documents.py`

```python
# app/api/routes/documents.py
"""Document management endpoints."""

import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.models.database import Document, get_db
from app.models.schemas import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
)
from app.api.dependencies import get_current_api_key
from app.worker.tasks import process_document
from app.config import get_settings

settings = get_settings()
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".html"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: str = Form("{}"),
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Upload a document for ingestion."""
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(f"File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB")

    # Store file
    file_type = ext.lstrip(".")
    doc_id = str(uuid.uuid4())
    storage_path = os.path.join(settings.storage_path, f"{doc_id}{ext}")

    os.makedirs(settings.storage_path, exist_ok=True)
    with open(storage_path, "wb") as f:
        f.write(content)

    # Create database record
    document = Document(
        id=doc_id,
        filename=file.filename,
        file_type=file_type,
        file_size=len(content),
        storage_path=storage_path,
        status="pending",
        metadata={},
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Queue async processing
    process_document.delay(doc_id, storage_path, file_type)

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=file.filename,
        status="pending",
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """List all documents."""
    documents = db.query(Document).order_by(Document.created_at.desc()).all()
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                document_id=str(doc.id),
                filename=doc.filename,
                status=doc.status,
                chunk_count=doc.chunk_count,
                upload_date=doc.created_at,
            )
            for doc in documents
        ]
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Get document details."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError("Document not found")

    return DocumentResponse(
        document_id=str(doc.id),
        filename=doc.filename,
        status=doc.status,
        chunk_count=doc.chunk_count,
        upload_date=doc.created_at,
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Delete a document and its embeddings."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError("Document not found")

    # Delete from vector DB
    from app.ingestion.indexer import VectorIndexer
    indexer = VectorIndexer()
    indexer.delete_document_chunks(document_id)

    # Delete file
    if os.path.exists(doc.storage_path):
        os.remove(doc.storage_path)

    # Delete from database
    db.delete(doc)
    db.commit()

    return {"message": "Document deleted successfully"}
```

### Verification

```bash
# 1. Start Celery worker
celery -A app.worker.tasks worker --loglevel=info

# 2. Upload a test document
curl -X POST http://localhost:8000/api/documents \
  -H "X-API-Key: your-key" \
  -F "file=@test.pdf" \
  -F "metadata={}"

# 3. Check document status
curl http://localhost:8000/api/documents \
  -H "X-API-Key: your-key"

# 4. Verify chunks in ChromaDB
# Check ChromaDB collection count via its API or UI
```

### Cursor Prompt for Phase 2

```
I'm building a RAG Chatbot. Please implement Phase 2: Document Ingestion Pipeline.

Create the following files:

1. app/ingestion/parser.py — DocumentParser class that handles PDF (pdfplumber), DOCX (python-docx), TXT, MD, and HTML (BeautifulSoup). Returns a ParsedDocument dataclass with text, pages list, and metadata.

2. app/ingestion/chunker.py — RecursiveTextChunker class with configurable chunk_size (default 500) and chunk_overlap (default 50). Uses tiktoken for token counting. Splits on paragraph boundaries, maintains overlap between chunks, and assigns page numbers when page text is available.

3. app/ingestion/embedder.py — OpenAIEmbedder class using OpenAI's embeddings API. Has embed_text() for single text and embed_batch() for multiple texts (batch_size=100). Uses tenacity for retry with exponential backoff.

4. app/ingestion/indexer.py — VectorIndexer class that takes TextChunk objects, generates embeddings in batch, and upserts them into ChromaDB with metadata (document_id, filename, chunk_index, page_number, section_title, token_count, created_at). Also has delete_document_chunks() to remove all chunks for a document.

5. app/worker/tasks.py — Celery task process_document(document_id, file_path, file_type) that: updates status to processing, parses the document, chunks the text, indexes chunks into vector DB, updates status to indexed. On failure, updates status to failed and retries with exponential backoff.

6. Update app/api/routes/documents.py — Full implementation with:
   - POST /api/documents: file upload with validation (extension, size), store file, create DB record, queue Celery task
   - GET /api/documents: list all documents
   - GET /api/documents/{id}: get single document
   - DELETE /api/documents/{id}: delete document, its file, and its vector embeddings

Make sure all imports are correct and consistent with the Phase 1 foundation.
```

---

## Phase 3: RAG Pipeline — Query Processing, Retrieval & Response Generation

### Objective

Implement the core RAG pipeline: query embedding, vector search, context assembly, prompt construction, and LLM response generation with streaming.

### Files to Create/Modify

```
app/services/
├── __init__.py
├── query_processor.py    # NEW
├── retriever.py          # NEW
├── context_assembler.py  # NEW
├── prompt_builder.py     # NEW
├── response_generator.py # NEW
└── rag_pipeline.py       # NEW
```

### Step-by-Step Instructions

#### Step 3.1: Create `app/services/query_processor.py`

```python
# app/services/query_processor.py
"""Query processing: validation, sanitization, and embedding."""

from app.core.security import validate_query, sanitize_input
from app.ingestion.embedder import OpenAIEmbedder


class QueryProcessor:
    """Process and validate user queries."""

    def __init__(self):
        self.embedder = OpenAIEmbedder()

    def process(self, query: str) -> dict:
        """Process a raw query string."""
        # Validate and sanitize
        sanitized = validate_query(query)

        # Generate embedding
        embedding = self.embedder.embed_text(sanitized)

        return {
            "original_query": query,
            "sanitized_query": sanitized,
            "embedding": embedding,
        }
```

#### Step 3.2: Create `app/services/retriever.py`

```python
# app/services/retriever.py
"""Vector search and chunk retrieval."""

from dataclasses import dataclass, field
from typing import Optional
from app.db.vector_client import get_or_create_collection
from app.config import get_settings

settings = get_settings()


@dataclass
class RetrievedChunk:
    """A retrieved chunk with relevance score."""
    text: str
    score: float
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    section_title: str = ""


class VectorRetriever:
    """Retrieve relevant chunks from the vector database."""

    def __init__(self):
        self.collection = get_or_create_collection()

    def retrieve(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        metadata_filter: Optional[dict] = None,
    ) -> list[RetrievedChunk]:
        """Retrieve top-k most similar chunks."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=metadata_filter,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        if not results["ids"] or not results["ids"][0]:
            return chunks

        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i]
            # Convert distance to similarity score (cosine: 1 - distance)
            similarity = 1 - distance

            if similarity < similarity_threshold:
                continue

            metadata = results["metadatas"][0][i]
            text = results["documents"][0][i]

            chunks.append(
                RetrievedChunk(
                    text=text,
                    score=similarity,
                    document_id=metadata.get("document_id", ""),
                    filename=metadata.get("filename", ""),
                    page_number=metadata.get("page_number", 0),
                    chunk_index=metadata.get("chunk_index", 0),
                    section_title=metadata.get("section_title", ""),
                )
            )

        # Sort by score descending
        chunks.sort(key=lambda c: c.score, reverse=True)

        # Deduplicate: remove chunks from same document with very similar content
        chunks = self._deduplicate(chunks)

        return chunks

    def _deduplicate(
        self, chunks: list[RetrievedChunk], threshold: float = 0.95
    ) -> list[RetrievedChunk]:
        """Remove near-duplicate chunks."""
        seen = set()
        unique = []

        for chunk in chunks:
            key = (chunk.document_id, chunk.chunk_index)
            if key not in seen:
                seen.add(key)
                unique.append(chunk)

        return unique
```

#### Step 3.3: Create `app/services/context_assembler.py`

```python
# app/services/context_assembler.py
"""Assemble retrieved chunks and conversation history into context."""

from dataclasses import dataclass, field
from typing import Optional
from app.services.retriever import RetrievedChunk
from app.config import get_settings

settings = get_settings()


@dataclass
class AssembledContext:
    """Assembled context for the LLM."""
    context_text: str
    sources: list[dict]
    total_tokens: int
    chunk_count: int


class ContextAssembler:
    """Assemble retrieved chunks into a coherent context for the LLM."""

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens

    def assemble(
        self,
        chunks: list[RetrievedChunk],
        conversation_history: Optional[list[dict]] = None,
    ) -> AssembledContext:
        """Assemble context from retrieved chunks and conversation history."""
        context_parts = []
        sources = []
        total_tokens = 0

        for i, chunk in enumerate(chunks):
            chunk_tokens = self._count_tokens(chunk.text)

            if total_tokens + chunk_tokens > self.max_tokens:
                break

            source_label = f"[Source {i + 1}: {chunk.filename}"
            if chunk.page_number:
                source_label += f", Page {chunk.page_number}"
            source_label += "]"

            context_parts.append(f"{source_label}\n{chunk.text}")
            sources.append({
                "document_id": chunk.document_id,
                "filename": chunk.filename,
                "page": chunk.page_number,
                "excerpt": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
            })
            total_tokens += chunk_tokens

        context_text = "\n\n---\n\n".join(context_parts)

        # Add conversation history if provided
        if conversation_history:
            history_text = self._format_history(conversation_history)
            context_text = f"{history_text}\n\n{context_text}"

        return AssembledContext(
            context_text=context_text,
            sources=sources,
            total_tokens=total_tokens,
            chunk_count=len(context_parts),
        )

    def _format_history(self, history: list[dict]) -> str:
        """Format conversation history."""
        parts = ["Conversation History:"]
        for msg in history[-5:]:  # Last 5 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role.capitalize()}: {content}")
        return "\n".join(parts)

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return len(text) // 4
```

#### Step 3.4: Create `app/services/prompt_builder.py`

```python
# app/services/prompt_builder.py
"""Build prompts for the LLM."""

from app.services.context_assembler import AssembledContext


class PromptBuilder:
    """Build structured prompts for the LLM."""

    SYSTEM_PROMPT = """You are a helpful, knowledgeable assistant. Answer the user's question using ONLY the provided context below.

Rules:
1. Base your answer strictly on the provided context.
2. If the context does not contain enough information, say: "I don't have enough information in my knowledge base to answer that."
3. Always cite sources using [Source N] notation matching the context labels.
4. Be concise, accurate, and professional.
5. Do not make up information or use knowledge outside the context.
6. Format your response using markdown when appropriate."""

    def build(
        self,
        query: str,
        context: AssembledContext,
    ) -> list[dict]:
        """Build the full message array for the LLM API."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
        ]

        if context.context_text:
            messages.append({
                "role": "user",
                "content": f"--- CONTEXT ---\n{context.context_text}\n--- END CONTEXT ---\n\nUser Question: {query}\n\nAssistant Answer:",
            })
        else:
            messages.append({
                "role": "user",
                "content": f"User Question: {query}\n\nAssistant Answer:",
            })

        return messages
```

#### Step 3.5: Create `app/services/response_generator.py`

```python
# app/services/response_generator.py
"""Generate responses using the LLM with streaming support."""

from typing import Generator
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import get_settings

settings = get_settings()


class ResponseGenerator:
    """Generate responses using OpenAI's LLM."""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_llm_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def generate(self, messages: list[dict]) -> str:
        """Generate a complete response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
        )
        return response.choices[0].message.content

    def generate_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        """Generate a streaming response."""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

#### Step 3.6: Create `app/services/rag_pipeline.py`

```python
# app/services/rag_pipeline.py
"""Main RAG pipeline orchestrator."""

from dataclasses import dataclass, field
from typing import Optional, Generator
from app.services.query_processor import QueryProcessor
from app.services.retriever import VectorRetriever
from app.services.context_assembler import ContextAssembler
from app.services.prompt_builder import PromptBuilder
from app.services.response_generator import ResponseGenerator
from app.config import get_settings

settings = get_settings()


@dataclass
class RAGResult:
    """Result of the RAG pipeline."""
    answer: str
    sources: list[dict]
    retrieval_scores: list[float] = field(default_factory=list)


class RAGPipeline:
    """Orchestrate the full RAG pipeline."""

    def __init__(self):
        self.query_processor = QueryProcessor()
        self.retriever = VectorRetriever()
        self.context_assembler = ContextAssembler(max_tokens=settings.max_context_tokens)
        self.prompt_builder = PromptBuilder()
        self.response_generator = ResponseGenerator()

    def run(
        self,
        query: str,
        conversation_history: Optional[list[dict]] = None,
        top_k: Optional[int] = None,
    ) -> RAGResult:
        """Execute the full RAG pipeline."""
        # Step 1: Process query
        processed = self.query_processor.process(query)

        # Step 2: Retrieve relevant chunks
        chunks = self.retriever.retrieve(
            query_embedding=processed["embedding"],
            top_k=top_k or settings.top_k,
            similarity_threshold=settings.similarity_threshold,
        )

        # Step 3: Check if we have relevant context
        if not chunks:
            return RAGResult(
                answer="I don't have enough information in my knowledge base to answer that.",
                sources=[],
                retrieval_scores=[],
            )

        # Step 4: Assemble context
        context = self.context_assembler.assemble(chunks, conversation_history)

        # Step 5: Build prompt
        messages = self.prompt_builder.build(query, context)

        # Step 6: Generate response
        answer = self.response_generator.generate(messages)

        return RAGResult(
            answer=answer,
            sources=context.sources,
            retrieval_scores=[chunk.score for chunk in chunks],
        )

    def run_stream(
        self,
        query: str,
        conversation_history: Optional[list[dict]] = None,
        top_k: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """Execute the RAG pipeline with streaming response."""
        # Step 1: Process query
        processed = self.query_processor.process(query)

        # Step 2: Retrieve relevant chunks
        chunks = self.retriever.retrieve(
            query_embedding=processed["embedding"],
            top_k=top_k or settings.top_k,
            similarity_threshold=settings.similarity_threshold,
        )

        # Step 3: Check if we have relevant context
        if not chunks:
            yield "I don't have enough information in my knowledge base to answer that."
            return

        # Step 4: Assemble context
        context = self.context_assembler.assemble(chunks, conversation_history)

        # Step 5: Build prompt
        messages = self.prompt_builder.build(query, context)

        # Step 6: Stream response
        for token in self.response_generator.generate_stream(messages):
            yield token
```

### Verification

```bash
# 1. Test the RAG pipeline directly (add a test script)
python -c "
from app.services.rag_pipeline import RAGPipeline
pipeline = RAGPipeline()
result = pipeline.run('What is the refund policy?')
print('Answer:', result.answer)
print('Sources:', result.sources)
"

# 2. Test streaming
python -c "
from app.services.rag_pipeline import RAGPipeline
pipeline = RAGPipeline()
for token in pipeline.run_stream('What is the refund policy?'):
    print(token, end='', flush=True)
"
```

### Cursor Prompt for Phase 3

```
I'm building a RAG Chatbot. Please implement Phase 3: RAG Pipeline.

Create the following files:

1. app/services/query_processor.py — QueryProcessor class that validates/sanitizes the query and generates its embedding using OpenAIEmbedder.

2. app/services/retriever.py — VectorRetriever class that queries ChromaDB with the query embedding, filters by similarity threshold (default 0.7), converts distances to similarity scores, and returns RetrievedChunk objects with text, score, document_id, filename, page_number. Includes deduplication logic.

3. app/services/context_assembler.py — ContextAssembler class that takes retrieved chunks and assembles them into a formatted context string with [Source N: filename, Page X] labels. Respects max token budget (default 8000). Also formats and includes conversation history (last 5 messages). Returns AssembledContext with context_text, sources list, total_tokens, and chunk_count.

4. app/services/prompt_builder.py — PromptBuilder class with a SYSTEM_PROMPT that instructs the LLM to only use provided context, cite sources with [Source N], and say "I don't have enough information" when context is insufficient. Returns a messages array for the OpenAI API.

5. app/services/response_generator.py — ResponseGenerator class using OpenAI's chat completions API. Has generate() for complete responses and generate_stream() for token-by-token streaming. Uses tenacity for retry with exponential backoff. Temperature=0.1, max_tokens=2000.

6. app/services/rag_pipeline.py — RAGPipeline class that orchestrates the full pipeline: query processing → retrieval → context assembly → prompt building → response generation. Has run() for complete responses and run_stream() for streaming. Returns RAGResult with answer, sources, and retrieval_scores. Returns fallback message when no relevant chunks are found.

Make sure all imports are correct and consistent with Phases 1 and 2.
```

---

## Phase 4: API Layer — Chat Endpoints & Conversation Management

### Objective

Implement the chat API endpoints (sync and streaming), conversation management, and wire everything together.

### Files to Create/Modify

```
app/api/routes/
├── chat.py             # MODIFY
└── conversations.py    # MODIFY
```

### Step-by-Step Instructions

#### Step 4.1: Modify `app/api/routes/chat.py`

```python
# app/api/routes/chat.py
"""Chat endpoints."""

import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.database import Conversation, Message, get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.api.dependencies import get_current_api_key
from app.services.rag_pipeline import RAGPipeline

router = APIRouter()
rag_pipeline = RAGPipeline()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Submit a query and receive a grounded response."""
    # Get or create conversation
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id
        ).first()
        if not conversation:
            conversation = Conversation(
                id=request.conversation_id,
                user_id=str(api_key.id),
            )
            db.add(conversation)
            db.commit()
    else:
        conversation = Conversation(
            user_id=str(api_key.id),
        )
        db.add(conversation)
        db.commit()

    # Get conversation history
    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at).all()

    history = [{"role": m.role, "content": m.content} for m in messages]

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.query,
    )
    db.add(user_message)
    db.commit()

    # Run RAG pipeline
    result = rag_pipeline.run(
        query=request.query,
        conversation_history=history,
        top_k=request.top_k,
    )

    # Save assistant message
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result.answer,
        sources=result.sources,
    )
    db.add(assistant_message)
    db.commit()

    return ChatResponse(
        answer=result.answer,
        sources=result.sources,
        conversation_id=str(conversation.id),
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Submit a query and receive a streamed response (SSE)."""
    # Get or create conversation
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id
        ).first()
        if not conversation:
            conversation = Conversation(
                id=request.conversation_id,
                user_id=str(api_key.id),
            )
            db.add(conversation)
            db.commit()
    else:
        conversation = Conversation(
            user_id=str(api_key.id),
        )
        db.add(conversation)
        db.commit()

    # Get conversation history
    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at).all()

    history = [{"role": m.role, "content": m.content} for m in messages]

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.query,
    )
    db.add(user_message)
    db.commit()

    # Stream response
    async def event_generator():
        full_response = ""
        sources = []

        for token in rag_pipeline.run_stream(
            query=request.query,
            conversation_history=history,
            top_k=request.top_k,
        ):
            full_response += token
            yield f"data: {token}\n\n"

        # Save assistant message after streaming completes
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=full_response,
            sources=sources,
        )
        db.add(assistant_message)
        db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
```

#### Step 4.2: Modify `app/api/routes/conversations.py`

```python
# app/api/routes/conversations.py
"""Conversation management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import Conversation, Message, get_db
from app.models.schemas import ConversationResponse, MessageResponse
from app.api.dependencies import get_current_api_key

router = APIRouter()


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Get conversation history."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise ValueError("Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    return ConversationResponse(
        conversation_id=str(conversation.id),
        messages=[
            MessageResponse(
                role=m.role,
                content=m.content,
                sources=m.sources or [],
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Delete a conversation and all its messages."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise ValueError("Conversation not found")

    db.delete(conversation)
    db.commit()

    return {"message": "Conversation deleted successfully"}
```

### Verification

```bash
# 1. Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"query": "What is the refund policy?"}'

# 2. Test streaming endpoint
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"query": "What is the refund policy?"}'

# 3. Test conversation history
curl http://localhost:8000/api/conversations/{conversation_id} \
  -H "X-API-Key: your-key"
```

### Cursor Prompt for Phase 4

```
I'm building a RAG Chatbot. Please implement Phase 4: API Layer — Chat Endpoints.

Update the following files:

1. app/api/routes/chat.py — Full implementation with:
   - POST /api/chat: Accepts ChatRequest (query, conversation_id, top_k). Gets or creates conversation, retrieves history, saves user message, runs RAGPipeline.run(), saves assistant message, returns ChatResponse with answer, sources, conversation_id.
   - POST /api/chat/stream: Same logic but uses StreamingResponse with SSE. Streams tokens from RAGPipeline.run_stream(). Saves assistant message after streaming completes. Ends with "data: [DONE]".

2. app/api/routes/conversations.py — Full implementation with:
   - GET /api/conversations/{id}: Returns conversation with all messages (role, content, sources, created_at).
   - DELETE /api/conversations/{id}: Deletes conversation and all associated messages.

Make sure all imports are correct and consistent with Phases 1-3.
```

---

## Phase 5: Frontend — Chat UI & Admin Panel

### Objective

Implement the React-based web chat interface and admin panel.

### Files to Create

```
frontend/
├── package.json
├── tailwind.config.js
├── postcss.config.js
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── components/
    │   ├── Chat/
    │   │   ├── ChatPage.tsx
    │   │   ├── ChatHeader.tsx
    │   │   ├── MessageList.tsx
    │   │   ├── MessageBubble.tsx
    │   │   ├── SourceCitations.tsx
    │   │   ├── TypingIndicator.tsx
    │   │   └── ChatInput.tsx
    │   ├── Admin/
    │   │   ├── AdminPage.tsx
    │   │   ├── DocumentList.tsx
    │   │   ├── UploadZone.tsx
    │   │   └── StatusBadge.tsx
    │   └── Common/
    │       └── Layout.tsx
    ├── pages/
    │   ├── ChatPage.tsx
    │   └── AdminPage.tsx
    ├── hooks/
    │   └── useChat.ts
    ├── services/
    │   └── api.ts
    └── store/
        └── chatStore.ts
```

### Step-by-Step Instructions

#### Step 5.1: Create `frontend/package.json`

```json
{
  "name": "ragchatbot-frontend",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0",
    "zustand": "^4.4.7",
    "axios": "^1.6.2",
    "react-dropzone": "^14.2.3",
    "@tanstack/react-table": "^8.11.2"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.3",
    "vite": "^5.0.8"
  }
}
```

#### Step 5.2: Create `frontend/src/services/api.ts`

```typescript
// frontend/src/services/api.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
});

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceReference[];
}

export interface SourceReference {
  document_id: string;
  filename: string;
  page?: number;
  excerpt: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceReference[];
  conversation_id: string;
}

export interface Document {
  document_id: string;
  filename: string;
  status: string;
  chunk_count: number;
  upload_date: string;
}

export const chatAPI = {
  sendQuery: async (query: string, conversationId?: string): Promise<ChatResponse> => {
    const response = await api.post('/api/chat', {
      query,
      conversation_id: conversationId || null,
    });
    return response.data;
  },

  streamQuery: async (
    query: string,
    conversationId: string | null,
    onToken: (token: string) => void,
    onDone: () => void,
  ): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: JSON.stringify({ query, conversation_id: conversationId }),
    });

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            onDone();
            return;
          }
          onToken(data);
        }
      }
    }
  },
};

export const documentAPI = {
  upload: async (file: File): Promise<{ document_id: string; filename: string; status: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', '{}');
    const response = await api.post('/api/documents', formData);
    return response.data;
  },

  list: async (): Promise<{ documents: Document[] }> => {
    const response = await api.get('/api/documents');
    return response.data;
  },

  delete: async (documentId: string): Promise<void> => {
    await api.delete(`/api/documents/${documentId}`);
  },
};
```

#### Step 5.3: Create `frontend/src/store/chatStore.ts`

```typescript
// frontend/src/store/chatStore.ts
import { create } from 'zustand';
import { chatAPI, ChatMessage } from '../services/api';

interface ChatState {
  messages: ChatMessage[];
  conversationId: string | null;
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;

  sendMessage: (query: string) => Promise<void>;
  startNewChat: () => void;
  clearError: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  conversationId: null,
  isLoading: false,
  isStreaming: false,
  error: null,

  sendMessage: async (query: string) => {
    const { conversationId } = get();

    // Add user message
    const userMessage: ChatMessage = { role: 'user', content: query };
    set((state) => ({
      messages: [...state.messages, userMessage],
      isLoading: true,
      isStreaming: true,
      error: null,
    }));

    try {
      let fullResponse = '';

      await chatAPI.streamQuery(
        query,
        conversationId,
        (token) => {
          fullResponse += token;
          set((state) => ({
            messages: [
              ...state.messages.slice(0, -1),
              { role: 'assistant', content: fullResponse },
            ],
          }));
        },
        () => {
          set({ isStreaming: false, isLoading: false });
        },
      );

      // Get conversation ID from the first response if new chat
      if (!conversationId) {
        // We need to get the conversation ID from the API
        // For now, we'll use a workaround
      }
    } catch (err: any) {
      set({
        error: err.message || 'An error occurred',
        isLoading: false,
        isStreaming: false,
      });
    }
  },

  startNewChat: () => {
    set({
      messages: [],
      conversationId: null,
      isLoading: false,
      isStreaming: false,
      error: null,
    });
  },

  clearError: () => set({ error: null }),
}));
```

#### Step 5.4: Create `frontend/src/components/Chat/ChatPage.tsx`

```tsx
// frontend/src/components/Chat/ChatPage.tsx
import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../../store/chatStore';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

const ChatPage: React.FC = () => {
  const { messages, isLoading, sendMessage } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <ChatHeader />
      <MessageList messages={messages} />
      <div ref={messagesEndRef} />
      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
};

export default ChatPage;
```

#### Step 5.5: Create `frontend/src/components/Chat/MessageBubble.tsx`

```tsx
// frontend/src/components/Chat/MessageBubble.tsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChatMessage } from '../../services/api';
import SourceCitations from './SourceCitations';

interface MessageBubbleProps {
  message: ChatMessage;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white border border-gray-200 text-gray-800'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
            {message.sources && message.sources.length > 0 && (
              <SourceCitations sources={message.sources} />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
```

#### Step 5.6: Create `frontend/src/components/Chat/SourceCitations.tsx`

```tsx
// frontend/src/components/Chat/SourceCitations.tsx
import React from 'react';
import { SourceReference } from '../../services/api';

interface SourceCitationsProps {
  sources: SourceReference[];
}

const SourceCitations: React.FC<SourceCitationsProps> = ({ sources }) => {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-gray-200">
      <p className="text-xs font-semibold text-gray-500 mb-2">Sources:</p>
      <div className="flex flex-wrap gap-2">
        {sources.map((source, index) => (
          <a
            key={index}
            href="#"
            onClick={(e) => e.preventDefault()}
            className="inline-flex items-center px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
            title={source.excerpt}
          >
            <span className="font-medium">{source.filename}</span>
            {source.page && (
              <span className="ml-1 text-gray-500">p.{source.page}</span>
            )}
          </a>
        ))}
      </div>
    </div>
  );
};

export default SourceCitations;
```

#### Step 5.7: Create `frontend/src/components/Chat/ChatInput.tsx`

```tsx
// frontend/src/components/Chat/ChatInput.tsx
import React, { useState } from 'react';

interface ChatInputProps {
  onSend: (query: string) => void;
  disabled: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-200 bg-white p-4">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={disabled}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </div>
    </form>
  );
};

export default ChatInput;
```

#### Step 5.8: Create `frontend/src/components/Admin/AdminPage.tsx`

```tsx
// frontend/src/components/Admin/AdminPage.tsx
import React, { useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { documentAPI, Document } from '../../services/api';

const AdminPage: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await documentAPI.list();
      setDocuments(response.documents);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const onDrop = async (acceptedFiles: File[]) => {
    setUploading(true);
    setError(null);

    for (const file of acceptedFiles) {
      try {
        await documentAPI.upload(file);
      } catch (err: any) {
        setError(`Failed to upload ${file.name}: ${err.message}`);
      }
    }

    setUploading(false);
    loadDocuments();
  };

  const handleDelete = async (documentId: string) => {
    try {
      await documentAPI.delete(documentId);
      loadDocuments();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/html': ['.html'],
    },
    multiple: true,
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'indexed': return 'bg-green-100 text-green-800';
      case 'processing': return 'bg-yellow-100 text-yellow-800';
      case 'pending': return 'bg-blue-100 text-blue-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Document Management</h1>

      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors mb-6 ${
          isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <p className="text-gray-500">Uploading...</p>
        ) : isDragActive ? (
          <p className="text-blue-500">Drop files here...</p>
        ) : (
          <p className="text-gray-500">
            Drag & drop files here, or click to select.
            <br />
            <span className="text-sm">Supported: PDF, DOCX, TXT, MD, HTML</span>
          </p>
        )}
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-lg mb-4">{error}</div>
      )}

      {/* Document List */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Filename</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Status</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Chunks</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Upload Date</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.document_id} className="border-t border-gray-100">
                <td className="px-4 py-3 text-sm text-gray-800">{doc.filename}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(doc.status)}`}>
                    {doc.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">{doc.chunk_count}</td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {new Date(doc.upload_date).toLocaleDateString()}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleDelete(doc.document_id)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminPage;
```

#### Step 5.9: Create `frontend/src/App.tsx`

```tsx
// frontend/src/App.tsx
import React, { useState } from 'react';
import ChatPage from './components/Chat/ChatPage';
import AdminPage from './components/Admin/AdminPage';

type Page = 'chat' | 'admin';

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<Page>('chat');

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="flex gap-4">
          <button
            onClick={() => setCurrentPage('chat')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              currentPage === 'chat'
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Chat
          </button>
          <button
            onClick={() => setCurrentPage('admin')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              currentPage === 'admin'
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Admin
          </button>
        </div>
      </nav>

      <main>
        {currentPage === 'chat' && <ChatPage />}
        {currentPage === 'admin' && <AdminPage />}
      </main>
    </div>
  );
};

export default App;
```

### Verification

```bash
# 1. Install frontend dependencies
cd frontend
npm install

# 2. Start development server
npm run dev

# 3. Open browser to http://localhost:5173
# 4. Test chat: type a question and verify response with sources
# 5. Test admin: upload a document, verify it appears in the list
```

### Cursor Prompt for Phase 5

```
I'm building a RAG Chatbot. Please implement Phase 5: Frontend — Chat UI & Admin Panel.

Create a React + TypeScript + Vite + Tailwind CSS frontend with:

1. frontend/package.json — with React 18, react-markdown, remark-gfm, zustand, axios, react-dropzone, @tanstack/react-table, Tailwind CSS, Vite, TypeScript

2. frontend/src/services/api.ts — Axios client with API key header. chatAPI with sendQuery() and streamQuery() (using fetch for SSE streaming). documentAPI with upload(), list(), delete().

3. frontend/src/store/chatStore.ts — Zustand store with messages array, conversationId, isLoading, isStreaming, error. sendMessage() that adds user message, streams assistant response token-by-token, updates store. startNewChat() to reset.

4. frontend/src/components/Chat/ChatPage.tsx — Main chat layout with header, message list, input. Auto-scrolls to bottom.

5. frontend/src/components/Chat/MessageBubble.tsx — Renders user messages (blue, right-aligned) and assistant messages (white, left-aligned) with ReactMarkdown for formatting. Shows SourceCitations for assistant messages.

6. frontend/src/components/Chat/SourceCitations.tsx — Displays source references as clickable badges with filename and page number.

7. frontend/src/components/Chat/ChatInput.tsx — Text input with send button. Disabled while loading.

8. frontend/src/components/Admin/AdminPage.tsx — Document management with drag-and-drop upload zone (react-dropzone), document table with status badges, delete button.

9. frontend/src/App.tsx — Simple navigation between Chat and Admin pages.

10. frontend/tailwind.config.js, postcss.config.js, tsconfig.json, index.html, src/main.tsx, src/index.css

Make sure all components are properly typed with TypeScript and styled with Tailwind CSS.
```

---

## Phase 6: Integration, Testing & Hardening

### Objective

Add comprehensive tests, error handling improvements, monitoring, and prepare for production deployment.

### Files to Create/Modify

```
tests/
├── __init__.py
├── conftest.py              # NEW
├── test_chat.py             # NEW
├── test_documents.py        # NEW
└── test_rag_pipeline.py     # NEW

app/main.py                  # MODIFY (add metrics)
```

### Step-by-Step Instructions

#### Step 6.1: Create `tests/conftest.py`

```python
# tests/conftest.py
"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import SessionLocal, Base, engine


@pytest.fixture(scope="session")
def client():
    """Create a test client."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "test.pdf"
    # Create a minimal PDF content
    pdf_path.write_bytes(b"%PDF-1.4 test content")
    return str(pdf_path)
```

#### Step 6.2: Create `tests/test_chat.py`

```python
# tests/test_chat.py
"""Tests for chat endpoints."""

from fastapi.testclient import TestClient


def test_chat_endpoint(client: TestClient):
    """Test basic chat query."""
    response = client.post(
        "/api/chat",
        json={"query": "What is the refund policy?"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "conversation_id" in data


def test_chat_empty_query(client: TestClient):
    """Test chat with empty query returns error."""
    response = client.post(
        "/api/chat",
        json={"query": ""},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 422


def test_chat_missing_api_key(client: TestClient):
    """Test chat without API key returns 401."""
    response = client.post(
        "/api/chat",
        json={"query": "test"},
    )
    assert response.status_code == 401


def test_chat_stream(client: TestClient):
    """Test streaming chat endpoint."""
    response = client.post(
        "/api/chat/stream",
        json={"query": "test query"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
```

#### Step 6.3: Create `tests/test_documents.py`

```python
# tests/test_documents.py
"""Tests for document endpoints."""

from fastapi.testclient import TestClient


def test_upload_document(client: TestClient, sample_pdf):
    """Test document upload."""
    with open(sample_pdf, "rb") as f:
        response = client.post(
            "/api/documents",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"metadata": "{}"},
            headers={"X-API-Key": "test-key"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "test.pdf"
    assert data["status"] == "pending"


def test_list_documents(client: TestClient):
    """Test listing documents."""
    response = client.get(
        "/api/documents",
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert isinstance(data["documents"], list)


def test_delete_document(client: TestClient):
    """Test deleting a document."""
    # First upload
    response = client.post(
        "/api/documents",
        files={"file": ("test.txt", b"test content", "text/plain")},
        data={"metadata": "{}"},
        headers={"X-API-Key": "test-key"},
    )
    doc_id = response.json()["document_id"]

    # Then delete
    response = client.delete(
        f"/api/documents/{doc_id}",
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
```

#### Step 6.4: Create `tests/test_rag_pipeline.py`

```python
# tests/test_rag_pipeline.py
"""Tests for RAG pipeline components."""

from app.services.query_processor import QueryProcessor
from app.services.retriever import VectorRetriever
from app.services.context_assembler import ContextAssembler
from app.services.prompt_builder import PromptBuilder


def test_query_processor():
    """Test query processing."""
    processor = QueryProcessor()
    result = processor.process("What is the refund policy?")
    assert "original_query" in result
    assert "sanitized_query" in result
    assert "embedding" in result
    assert len(result["embedding"]) > 0


def test_context_assembler():
    """Test context assembly."""
    from app.services.retriever import RetrievedChunk

    chunks = [
        RetrievedChunk(
            text="Test chunk 1",
            score=0.9,
            document_id="doc-1",
            filename="test.pdf",
            page_number=1,
            chunk_index=0,
        ),
        RetrievedChunk(
            text="Test chunk 2",
            score=0.8,
            document_id="doc-2",
            filename="test2.pdf",
            page_number=2,
            chunk_index=1,
        ),
    ]

    assembler = ContextAssembler(max_tokens=8000)
    context = assembler.assemble(chunks)

    assert context.context_text != ""
    assert len(context.sources) == 2
    assert context.chunk_count == 2


def test_prompt_builder():
    """Test prompt building."""
    from app.services.context_assembler import AssembledContext

    context = AssembledContext(
        context_text="[Source 1: test.pdf, Page 1]\nTest content",
        sources=[{"document_id": "doc-1", "filename": "test.pdf", "page": 1, "excerpt": "Test content"}],
        total_tokens=10,
        chunk_count=1,
    )

    builder = PromptBuilder()
    messages = builder.build("What is this?", context)

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "What is this?" in messages[1]["content"]
```

#### Step 6.5: Modify `app/main.py` — Add metrics endpoint

```python
# Add to app/main.py
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

@app.get("/api/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
```

### Verification

```bash
# 1. Run all tests
pytest tests/ -v

# 2. Run with coverage
pytest tests/ --cov=app --cov-report=html

# 3. Test the full flow
# - Upload a document via API
# - Wait for indexing to complete
# - Send a chat query
# - Verify response includes sources

# 4. Check metrics
curl http://localhost:8000/api/metrics
```

### Cursor Prompt for Phase 6

```
I'm building a RAG Chatbot. Please implement Phase 6: Integration, Testing & Hardening.

Create the following test files:

1. tests/conftest.py — Pytest fixtures: test client (TestClient), database session, sample PDF file fixture.

2. tests/test_chat.py — Tests for chat endpoints: test basic chat query, empty query validation, missing API key, streaming endpoint.

3. tests/test_documents.py — Tests for document endpoints: upload document, list documents, delete document.

4. tests/test_rag_pipeline.py — Tests for RAG pipeline components: query processor, context assembler, prompt builder.

5. Update app/main.py — Add Prometheus metrics endpoint at /api/metrics using prometheus_client.

Make sure all tests can run with `pytest tests/ -v` and pass.
```

---

## Summary: Phase Completion Checklist

| Phase | Key Deliverable | Status |
|---|---|---|
| **Phase 1** | Project setup, config, database models, migrations | ☐ |
| **Phase 2** | Document ingestion pipeline (parse, chunk, embed, index) | ☐ |
| **Phase 3** | RAG pipeline (query, retrieve, assemble, prompt, generate) | ☐ |
| **Phase 4** | Chat API endpoints (sync + streaming), conversation management | ☐ |
| **Phase 5** | React frontend (chat UI + admin panel) | ☐ |
| **Phase 6** | Tests, monitoring, production readiness | ☐ |

---

## Quick Reference: Running the Full System

```bash
# Terminal 1: Infrastructure
docker-compose up -d postgres redis chroma

# Terminal 2: Backend API
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 3: Celery Worker
celery -A app.worker.tasks worker --loglevel=info

# Terminal 4: Frontend
cd frontend
npm install
npm run dev

# Access:
# - API Docs: http://localhost:8000/docs
# - Chat UI: http://localhost:5173
# - Health:  http://localhost:8000/health
```

---

*End of Document*

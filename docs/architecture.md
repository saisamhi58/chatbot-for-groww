# Architecture Document — RAG Chatbot

| Field | Value |
|---|---|
| **Product Name** | RAG Chatbot |
| **Document Version** | 1.0 |
| **Date** | 2026-10-01 |
| **Author** | — |
| **Status** | Draft |
| **References** | [PRD](./prd.md) |

---

## 1. Architecture Overview

### 1.1 Purpose

This document describes the technical architecture of the RAG Chatbot system. It translates the product requirements defined in the PRD into concrete technology choices, component designs, data flows, and deployment strategies.

### 1.2 Design Principles

| Principle | Description |
|---|---|
| **Modularity** | Each component (ingestion, retrieval, generation) is independently deployable and replaceable. |
| **Statelessness** | Application servers hold no session state; all state is externalized to databases. |
| **Configurability** | All models, prompts, and parameters are configurable via environment variables or config files — no code changes required. |
| **Observability** | Every request is logged, traced, and measured. |
| **Graceful Degradation** | If a downstream service (LLM, vector DB) fails, the system returns informative errors rather than crashing. |
| **Security by Default** | All communications are encrypted; inputs are validated; PII is handled carefully. |

### 1.3 Architecture Style

The system follows a **layered microservices-inspired architecture** with a modular monolith deployment target for v1:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Web Chat UI │  │  Admin Panel │  │  External Systems (API)  │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘  │
└─────────┼──────────────────┼───────────────────────┼────────────────┘
          │                  │                       │
          ▼                  ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API Gateway / Load Balancer                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     Application Layer (FastAPI)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ Auth &      │  │  Chat        │  │  Document Management      │  │
│  │ Rate Limit  │  │  Controller  │  │  Controller               │  │
│  └─────────────┘  └──────┬───────┘  └─────────────┬─────────────┘  │
│                          │                        │                 │
│  ┌───────────────────────▼────────────────────────▼─────────────┐  │
│  │                    RAG Pipeline Service                       │  │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐  │  │
│  │  │ Query    │  │ Context   │  │ Prompt   │  │ Response   │  │  │
│  │  │ Processor│→ │ Assembler │→ │ Builder  │→ │ Generator  │  │  │
│  │  └──────────┘  └───────────┘  └──────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        Data & ML Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Vector DB    │  │ Relational DB│  │  Object Storage          │  │
│  │ (Chroma)     │  │ (PostgreSQL) │  │  (S3 / Local)            │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Embedding    │  │ LLM Service  │  │  Cache                   │  │
│  │ Model        │  │ (OpenAI API) │  │  (Redis)                 │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Frontend Layer

#### 2.1.1 Web Chat Interface

| Aspect | Detail |
|---|---|
| **Technology** | React 18+ with TypeScript |
| **State Management** | React Context API or Zustand |
| **Styling** | Tailwind CSS |
| **Markdown Rendering** | `react-markdown` with `remark-gfm` |
| **HTTP Client** | Axios or Fetch API |
| **Real-time** | Server-Sent Events (SSE) for streaming responses |

**Component Hierarchy:**

```
App
├── ChatPage
│   ├── ChatHeader
│   │   ├── Title
│   │   └── NewChatButton
│   ├── MessageList
│   │   ├── MessageBubble (user)
│   │   └── MessageBubble (assistant)
│   │       ├── MarkdownContent
│   │       └── SourceCitations
│   ├── TypingIndicator
│   └── ChatInput
│       ├── TextInput
│       └── SendButton
├── AdminPage
│   ├── DocumentList
│   │   └── DocumentRow[]
│   ├── UploadZone
│   └── StatusBadge
└── Layout
    ├── Navigation
    └── PageRouter
```

#### 2.1.2 Admin Panel

| Aspect | Detail |
|---|---|
| **Technology** | React (shared with Chat UI) |
| **Table** | `@tanstack/react-table` |
| **File Upload** | `react-dropzone` |

---

### 2.2 API Layer

#### 2.2.1 Technology Choice

| Aspect | Detail |
|---|---|
| **Framework** | FastAPI (Python) |
| **Why FastAPI** | Async-native, automatic OpenAPI docs, Pydantic validation, high performance |
| **ASGI Server** | Uvicorn |
| **API Documentation** | Auto-generated Swagger UI at `/docs` |

#### 2.2.2 API Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/chat` | Submit a query and receive a grounded response | API Key |
| `POST` | `/api/chat/stream` | Submit a query and receive a streamed response (SSE) | API Key |
| `POST` | `/api/documents` | Upload a document for ingestion | API Key |
| `GET` | `/api/documents` | List all indexed documents | API Key |
| `GET` | `/api/documents/{id}` | Get document details and status | API Key |
| `DELETE` | `/api/documents/{id}` | Delete a document and its embeddings | API Key |
| `GET` | `/api/conversations/{id}` | Get conversation history | API Key |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation | API Key |
| `GET` | `/api/health` | Health check | None |
| `GET` | `/api/metrics` | Prometheus metrics | None |

#### 2.2.3 Middleware Stack

```
Request
  │
  ▼
┌─────────────────────┐
│  CORS Middleware     │  (allow configured origins)
├─────────────────────┤
│  Rate Limiter        │  (token bucket per API key)
├─────────────────────┤
│  Auth Middleware     │  (API key validation)
├─────────────────────┤
│  Request ID          │  (UUID for tracing)
├─────────────────────┤
│  Logging Middleware  │  (structured request/response logs)
├─────────────────────┤
│  Error Handler       │  (uniform error responses)
└─────────────────────┘
  │
  ▼
Route Handler
```

---

### 2.3 RAG Pipeline Service

This is the core of the system. It orchestrates the flow from query to response.

#### 2.3.1 Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RAG Pipeline                                  │
│                                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐    │
│  │  Query   │──▶│ Retrieval│──▶│ Context  │──▶│  Generation  │    │
│  │Processing│   │          │   │ Assembly │   │              │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘    │
│       │              │              │               │               │
│       ▼              ▼              ▼               ▼               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐    │
│  │ Sanitize │   │ Embed    │   │ Deduplicate│  │ Build Prompt │    │
│  │ Validate │   │ Query    │   │ Rank       │  │ Call LLM     │    │
│  │ Transform│   │ Search   │   │ Filter     │  │ Stream       │    │
│  │          │   │ Vector DB│   │ Assemble   │  │ Post-process │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.3.2 Stage 1: Query Processing

| Step | Description |
|---|---|
| **Input Validation** | Validate query length (1–2000 chars), reject empty/malicious input. |
| **Sanitization** | Strip potential prompt injection patterns; escape special characters. |
| **Query Transformation** | Optionally rewrite/expand the query for better retrieval (v2). |
| **Conversation Context** | Fetch recent messages from the conversation to maintain context. |

#### 2.3.3 Stage 2: Retrieval

| Step | Description |
|---|---|
| **Query Embedding** | Convert the query text to a vector using the configured embedding model. |
| **Vector Search** | Query the vector database for the top-k most similar chunks (cosine similarity). |
| **Metadata Filter** | Apply optional filters (document type, date range, category). |
| **Threshold Filter** | Discard results below a configurable similarity threshold (e.g., 0.7). |
| **Deduplication** | Remove near-duplicate chunks (same document, overlapping content). |

**Retrieval Configuration:**

```yaml
retrieval:
  top_k: 5                    # Number of chunks to retrieve
  similarity_threshold: 0.7   # Minimum cosine similarity score
  score_ranking: cosine       # Options: cosine, dot_product, euclidean
  metadata_filter: {}         # Optional key-value filters
  deduplication:
    enabled: true
    similarity_threshold: 0.95  # Chunks above this are considered duplicates
```

#### 2.3.4 Stage 3: Context Assembly

| Step | Description |
|---|---|
| **Chunk Ordering** | Order retrieved chunks by relevance score (highest first). |
| **Token Budget** | Fit as many chunks as possible within the LLM's context window (reserve space for query + system prompt + response). |
| **Source Tracking** | Maintain mapping from each chunk to its source document for citation. |
| **History Integration** | Include recent conversation messages (configurable window, e.g., last 5 turns). |

**Context Window Budget:**

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Context Window                        │
│                    (e.g., 128K tokens)                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  System Prompt          │  ~500 tokens               │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  Conversation History   │  ~2,000 tokens (5 turns)   │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  Retrieved Context      │  ~8,000 tokens (top-k)     │   │
│  │  (with source metadata)                             │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  User Query             │  ~100 tokens               │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  Response Space         │  ~4,000 tokens             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Total: ~14,600 tokens used, ~113,400 tokens headroom       │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3.5 Stage 4: Prompt Construction

**System Prompt Template:**

```
You are a helpful assistant for [ORGANIZATION]. Answer the user's question
using ONLY the provided context below. Follow these rules:

1. Base your answer strictly on the provided context.
2. If the context does not contain enough information to answer the question,
   say: "I don't have enough information in my knowledge base to answer that."
3. Always cite sources using [Source N] notation.
4. Be concise, accurate, and professional.
5. Do not make up information or use knowledge outside the context.

--- CONTEXT ---
[Source 1: {filename}, Page {page}]
{chunk_text}

[Source 2: {filename}, Page {page}]
{chunk_text}

... (more sources)

--- END CONTEXT ---

Conversation History:
{history}

User Question: {query}

Assistant Answer:
```

#### 2.3.6 Stage 5: Response Generation

| Step | Description |
|---|---|
| **LLM Call** | Send the constructed prompt to the configured LLM with streaming enabled. |
| **Token Streaming** | Stream response tokens back to the client via SSE for real-time display. |
| **Source Extraction** | Parse [Source N] citations from the response and map to document references. |
| **Post-processing** | Format markdown, validate citations, apply content filters. |
| **Fallback Handling** | If no relevant context was retrieved, return a clear fallback message. |

---

### 2.4 Document Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Document Ingestion Pipeline                         │
│                                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐    │
│  │  Upload   │──▶│  Parse   │──▶│  Chunk   │──▶│   Embed      │    │
│  │  & Store  │   │  Document│   │  Text    │   │   & Store    │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘    │
│       │              │              │               │               │
│       ▼              ▼              ▼               ▼               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐    │
│  │ Validate │   │ Extract  │   │ Split    │   │ Generate     │    │
│  │ File     │   │ Raw Text │   │ Overlap  │   │ Embeddings   │    │
│  │ Store    │   │ Per Page │   │ 500/50   │   │ Batch Insert │    │
│  │ Original │   │          │   │          │   │ Vector DB    │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.4.1 Ingestion Stages

| Stage | Component | Details |
|---|---|---|
| **Upload** | API Controller | Accept multipart file upload, validate file type/size, store original file in object storage. |
| **Parse** | Document Parser | Extract text from PDF (PyPDF2/pdfplumber), DOCX (python-docx), TXT/MD/HTML (direct read). Preserve page numbers and section headers. |
| **Chunk** | Text Splitte | `RecursiveCharacterTextSplitter` with 500-token chunks, 50-token overlap. Respect paragraph and section boundaries. |
| **Embed** | Embedding Model | Generate embeddings in batches (e.g., 100 chunks per API call). Store in vector DB with metadata. |
| **Index** | Vector DB | Upsert chunks with metadata: `document_id`, `chunk_index`, `page_number`, `section_title`, `token_count`. |

#### 2.4.2 Supported File Parsers

| File Type | Parser | Notes |
|---|---|---|
| PDF | `pdfplumber` or `PyMuPDF` | Preserves page numbers; handles tables. |
| DOCX | `python-docx` | Extracts paragraphs and headings. |
| TXT | Direct read | Splits by lines. |
| Markdown | Direct read | Preserves heading structure. |
| HTML | `BeautifulSoup` | Strips tags, preserves text content. |

---

## 3. Data Architecture

### 3.1 Database Schema

#### 3.1.1 Relational Database (PostgreSQL)

```sql
-- Documents table
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        VARCHAR(255) NOT NULL,
    file_type       VARCHAR(10) NOT NULL,  -- pdf, docx, txt, md, html
    file_size       BIGINT NOT NULL,        -- bytes
    storage_path    VARCHAR(500) NOT NULL,  -- S3 key or local path
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending, processing, indexed, failed
    chunk_count     INTEGER DEFAULT 0,
    error_message   TEXT,
    metadata        JSONB DEFAULT '{}',
    uploaded_by     VARCHAR(255),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversations table
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(255) NOT NULL,
    title           VARCHAR(255),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages table
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(10) NOT NULL,  -- user, assistant, system
    content         TEXT NOT NULL,
    sources         JSONB DEFAULT '[]',    -- list of source references
    feedback        VARCHAR(10),           -- thumbs_up, thumbs_down, null
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API keys table
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash        VARCHAR(255) NOT NULL UNIQUE,
    name            VARCHAR(255),
    is_active       BOOLEAN DEFAULT TRUE,
    rate_limit      INTEGER DEFAULT 60,    -- requests per minute
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at      TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

#### 3.1.2 Vector Database Schema (Chroma)

```
Collection: "knowledge_base"

Record:
├── id: string (UUID)
├── embedding: float32[1536]  (OpenAI text-embedding-3-small)
├── document: string          (chunk text)
└── metadata: dict
    ├── document_id: string (UUID)
    ├── filename: string
    ├── chunk_index: int
    ├── page_number: int
    ├── section_title: string
    ├── token_count: int
    └── created_at: string (ISO 8601)
```

### 3.2 Data Flow

#### 3.2.1 Ingestion Flow

```
User/Admin
    │
    │  POST /api/documents (file + metadata)
    ▼
┌─────────────────┐
│  API Server     │
│  - Validate     │
│  - Store file   │
│  - Create DB    │
│    record       │
│  - Queue task   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Worker         │
│  (Celery/       │
│   Background    │
│   Task)         │
│                 │
│  1. Parse file  │
│  2. Chunk text  │
│  3. Embed       │
│  4. Store in    │
│     Vector DB   │
│  5. Update DB   │
│     status      │
└─────────────────┘
```

#### 3.2.2 Query Flow

```
User
    │
    │  POST /api/chat (query, conversation_id)
    ▼
┌─────────────────┐
│  API Server     │
│  - Auth check   │
│  - Rate limit   │
│  - Validate     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RAG Pipeline   │
│                 │
│  1. Embed query │
│  2. Search DB   │
│  3. Assemble    │
│     context     │
│  4. Build prompt│
│  5. Call LLM    │
│  6. Stream      │
│     response    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Response       │
│  - answer       │
│  - sources      │
│  - conversation │
│    _id          │
└─────────────────┘
```

---

## 4. Technology Stack

### 4.1 Complete Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Frontend** | React + TypeScript | 18+ | Chat UI, Admin panel |
| **Styling** | Tailwind CSS | 3.x | Utility-first CSS |
| **State** | Zustand | 4.x | Lightweight state management |
| **Markdown** | react-markdown + remark-gfm | latest | Render formatted responses |
| **Backend** | FastAPI | 0.100+ | REST API framework |
| **ASGI Server** | Uvicorn | 0.20+ | ASGI server |
| **Validation** | Pydantic | 2.x | Request/response validation |
| **Task Queue** | Celery + Redis | 5.x / 7.x | Async document processing |
| **Relational DB** | PostgreSQL | 15+ | Structured data storage |
| **Vector DB** | Chroma | 0.4+ | Embedding storage & search |
| **Embedding** | OpenAI text-embedding-3-small | — | Text → vector |
| **LLM** | OpenAI GPT-4o | — | Response generation |
| **Cache** | Redis | 7.x | Query caching, rate limiting |
| **Object Storage** | AWS S3 / Local | — | Original file storage |
| **Monitoring** | Prometheus + Grafana | — | Metrics & dashboards |
| **Logging** | structlog + ELK | — | Structured logging |
| **Containerization** | Docker + Docker Compose | — | Development & deployment |
| **CI/CD** | GitHub Actions | — | Automated testing & deployment |

### 4.2 Technology Alternatives

| Component | Primary Choice | Alternative 1 | Alternative 2 |
|---|---|---|---|
| Vector DB | Chroma (local) | Pinecone (cloud) | Weaviate (self-hosted) |
| LLM | OpenAI GPT-4o | Anthropic Claude 3.5 | Meta Llama 3 (self-hosted) |
| Embedding | OpenAI text-embedding-3-small | sentence-transformers/all-MiniLM-L6-v2 | Cohere embed-v3 |
| Backend | FastAPI | Flask + Flask-RESTful | Django REST Framework |
| Frontend | React | Next.js | Streamlit (rapid prototyping) |
| Task Queue | Celery + Redis | RQ (Redis Queue) | In-process asyncio tasks |

---

## 5. Deployment Architecture

### 5.1 Development Environment

```
┌─────────────────────────────────────────────────────┐
│                  Docker Compose                      │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Web UI  │  │  API     │  │  Worker          │  │
│  │  :3000   │  │  :8000   │  │  (Celery)        │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Postgres │  │  Redis   │  │  Chroma          │  │
│  │  :5432   │  │  :6379   │  │  :8001           │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 5.2 Production Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS / Cloud                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                      CloudFront CDN                           │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                              │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │                    Application Load Balancer                   │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                              │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │              ECS / EKS (Fargate / Kubernetes)                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │  API Server │  │  API Server │  │  Celery Worker      │  │   │
│  │  │  (Task 1)   │  │  (Task 2)   │  │  (Document Ingest)  │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  RDS         │  │  ElastiCache │  │  OpenSearch / Pinecone   │  │
│  │  PostgreSQL  │  │  (Redis)     │  │  (Vector Search)         │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  S3 Bucket   │  │  CloudWatch  │  │  Secrets Manager         │  │
│  │  (Documents) │  │  (Monitoring)│  │  (API Keys, LLM Keys)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.3 Environment Configuration

| Variable | Development | Staging | Production |
|---|---|---|---|
| `ENVIRONMENT` | `dev` | `staging` | `prod` |
| `DEBUG` | `true` | `false` | `false` |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `WARNING` |
| `DATABASE_URL` | localhost | RDS endpoint | RDS endpoint |
| `VECTOR_DB_HOST` | localhost | Pinecone | Pinecone |
| `LLM_MODEL` | `gpt-4o-mini` | `gpt-4o` | `gpt-4o` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | `text-embedding-3-small` | `text-embedding-3-small` |
| `RATE_LIMIT_RPM` | 100 | 60 | 30 |
| `CORS_ORIGINS` | `*` | staging domain | production domain |

---

## 6. Security Architecture

### 6.1 Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                           │
│                                                              │
│  Layer 1: Network                                            │
│  ├── TLS 1.2+ for all communications                        │
│  ├── VPC isolation for production                           │
│  └── Security groups / firewall rules                       │
│                                                              │
│  Layer 2: Application                                        │
│  ├── API key authentication                                  │
│  ├── Rate limiting (per key, per IP)                        │
│  ├── Input validation (Pydantic models)                    │
│  ├── CORS policy enforcement                                │
│  └── Request size limits                                    │
│                                                              │
│  Layer 3: Data                                               │
│  ├── Encryption at rest (AES-256)                           │
│  ├── Encryption in transit (TLS)                            │
│  ├── PII redaction in logs                                  │
│  └── Secure secrets management (AWS Secrets Manager)        │
│                                                              │
│  Layer 4: LLM Safety                                         │
│  ├── Prompt injection prevention                            │
│  ├── System prompt hardening                                │
│  ├── Output content filtering                               │
│  └── Context boundary enforcement                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Authentication & Authorization

| Mechanism | Implementation |
|---|---|
| **API Authentication** | API key passed via `X-API-Key` header; validated against `api_keys` table. |
| **Key Storage** | Keys are hashed (bcrypt/SHA-256) before storage; only shown once at creation. |
| **Rate Limiting** | Token bucket algorithm; configurable per key; enforced via Redis. |
| **Admin Access** | v1: shared admin key; v2: OAuth 2.0 / SSO integration. |

### 6.3 Prompt Injection Mitigation

| Strategy | Implementation |
|---|---|
| **Input Sanitization** | Strip known injection patterns (`ignore previous instructions`, `system:`, etc.). |
| **System Prompt Hardening** | Explicit instructions to ignore user attempts to override system behavior. |
| **Context Boundary** | Clearly delimit retrieved context from user input in the prompt. |
| **Output Validation** | Check response for leaked system prompt or suspicious content. |

---

## 7. Scalability & Performance

### 7.1 Scaling Strategy

| Component | Scaling Approach | Trigger |
|---|---|---|
| **API Servers** | Horizontal (add more tasks/containers) | CPU > 70%, latency > 2s |
| **Celery Workers** | Horizontal (add more workers) | Queue depth > 100 |
| **PostgreSQL** | Vertical (larger instance) + Read replicas | CPU > 80%, connections > 80% |
| **Vector DB** | Migrate from Chroma (local) to Pinecone (cloud) | Document count > 10K |
| **Redis** | Vertical or Redis Cluster | Memory > 80% |

### 7.2 Caching Strategy

| Cache Key | TTL | Purpose |
|---|---|---|
| `query:{hash}` | 5 minutes | Cache frequent query results |
| `embedding:{text_hash}` | 24 hours | Avoid re-embedding identical text |
| `document:{id}:status` | 1 minute | Cache document ingestion status |
| `rate_limit:{api_key}` | 1 minute | Rate limit counter |

### 7.3 Performance Targets

| Metric | Target | Measurement |
|---|---|---|
| Query embedding | < 200ms | Time to convert query to vector |
| Vector search | < 500ms | Time to retrieve top-k chunks |
| LLM first token | < 2s | Time to first token from LLM |
| End-to-end response | < 10s | Total time to full response |
| Document ingestion | < 30s/page | Time from upload to indexed |

---

## 8. Monitoring & Observability

### 8.1 Metrics (Prometheus)

| Metric | Type | Description |
|---|---|---|
| `rag_query_total` | Counter | Total queries processed |
| `rag_query_duration_seconds` | Histogram | End-to-end query latency |
| `rag_retrieval_duration_seconds` | Histogram | Vector search latency |
| `rag_llm_duration_seconds` | Histogram | LLM call latency |
| `rag_retrieval_score` | Histogram | Average similarity score of retrieved chunks |
| `rag_fallback_total` | Counter | Total fallback responses (no context found) |
| `rag_document_ingest_total` | Counter | Total documents ingested |
| `rag_document_ingest_duration_seconds` | Histogram | Document ingestion time |
| `rag_llm_tokens_total` | Counter | Total LLM tokens consumed |
| `rag_errors_total` | Counter | Total errors by type |

### 8.2 Logging

| Log Level | Events |
|---|---|
| **DEBUG** | Detailed pipeline stage outputs, prompt content (dev only) |
| **INFO** | Request received, response sent, document uploaded/indexed |
| **WARNING** | Low similarity scores, rate limit approached, retry attempts |
| **ERROR** | LLM call failures, vector DB errors, ingestion failures |
| **CRITICAL** | Service unavailable, data corruption detected |

**Log Format (JSON):**

```json
{
  "timestamp": "2026-10-01T12:00:00Z",
  "level": "INFO",
  "request_id": "uuid",
  "user_id": "user-123",
  "event": "query_processed",
  "query": "What is the refund policy?",
  "response_time_ms": 3200,
  "retrieval_score": 0.87,
  "sources_count": 3,
  "llm_tokens": 1200
}
```

### 8.3 Alerting

| Alert | Condition | Severity |
|---|---|---|
| High error rate | `rag_errors_total / rag_query_total > 5%` | P1 |
| High latency | `p95(rag_query_duration_seconds) > 10` | P2 |
| LLM service down | LLM API health check fails | P1 |
| Vector DB down | Vector DB health check fails | P1 |
| Queue backlog | Celery queue depth > 500 | P2 |
| Disk usage | > 85% | P2 |

### 8.4 Tracing

- **Request ID**: UUID generated at API entry, propagated through all pipeline stages.
- **Distributed Tracing**: OpenTelemetry for tracing across API → Worker → LLM → Vector DB.
- **Trace Visualization**: Jaeger or AWS X-Ray.

---

## 9. Error Handling

### 9.1 Error Categories

| Category | HTTP Status | Example | User-Facing Message |
|---|---|---|---|
| **Validation Error** | 400 | Empty query, invalid file type | "Please provide a valid query." |
| **Authentication Error** | 401 | Missing/invalid API key | "Authentication required." |
| **Rate Limit Error** | 429 | Too many requests | "Too many requests. Please try again later." |
| **Not Found Error** | 404 | Document not found | "Document not found." |
| **LLM Service Error** | 502 | LLM API unavailable | "AI service is temporarily unavailable. Please try again." |
| **Vector DB Error** | 503 | Vector DB unavailable | "Search service is temporarily unavailable." |
| **Internal Error** | 500 | Unexpected exception | "An unexpected error occurred. Please try again." |

### 9.2 Retry Strategy

| Service | Max Retries | Backoff | Timeout |
|---|---|---|---|
| LLM API | 3 | Exponential (1s, 2s, 4s) | 30s |
| Vector DB | 2 | Linear (1s, 2s) | 10s |
| Embedding API | 3 | Exponential (1s, 2s, 4s) | 15s |
| PostgreSQL | 3 | Exponential (0.5s, 1s, 2s) | 5s |

---

## 10. Development Setup

### 10.1 Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

### 10.2 Quick Start

```bash
# Clone repository
git clone <repo-url>
cd ragchatbot

# Start infrastructure services
docker-compose up -d postgres redis chroma

# Set up environment
cp .env.example .env
# Edit .env with your OpenAI API key and other config

# Install Python dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.worker worker --loglevel=info

# Start frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### 10.3 Environment Variables

```env
# Application
ENVIRONMENT=dev
DEBUG=true
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ragchatbot

# Redis
REDIS_URL=redis://localhost:6379/0

# Vector DB
VECTOR_DB_HOST=localhost
VECTOR_DB_PORT=8001
VECTOR_DB_COLLECTION=knowledge_base

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_LLM_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Storage
STORAGE_TYPE=local
STORAGE_PATH=./data/documents
# For S3:
# STORAGE_TYPE=s3
# S3_BUCKET=ragchatbot-documents
# S3_REGION=us-east-1

# RAG Config
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=5
SIMILARITY_THRESHOLD=0.7
MAX_CONTEXT_TOKENS=8000

# Rate Limiting
RATE_LIMIT_RPM=60
```

---

## 11. Testing Strategy

### 11.1 Test Levels

| Level | Scope | Tools |
|---|---|---|
| **Unit Tests** | Individual functions, models, utilities | pytest |
| **Integration Tests** | API endpoints, DB operations, vector search | pytest + TestClient |
| **E2E Tests** | Full user flows (upload → query → response) | Playwright |
| **Performance Tests** | Load testing, latency benchmarks | Locust |
| **LLM Evaluation** | Response quality, accuracy, hallucination rate | Custom eval framework |

### 11.2 Test Data

- **Golden Query Set**: 50+ curated queries with expected answers and sources.
- **Test Documents**: Sample PDFs, DOCX, TXT files for ingestion testing.
- **Adversarial Queries**: Prompt injection attempts, edge cases, very long/short queries.

### 11.3 CI/CD Pipeline

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐
│  Code    │──▶│  Lint &  │──▶│  Unit    │──▶│  Integration │
│  Push    │   │  Format  │   │  Tests   │   │  Tests       │
└──────────┘   └──────────┘   └──────────┘   └──────┬───────┘
                                                     │
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────▼───────┐
│  Deploy  │◀──│  Build   │◀──│  E2E     │◀──│  Performance │
│  to Stg  │   │  Docker  │   │  Tests   │   │  Tests       │
└──────────┘   └──────────┘   └──────────┘   └──────────────┘
```

---

## 12. Project Structure

```
ragchatbot/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Configuration management
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py          # Chat endpoints
│   │   │   ├── documents.py     # Document management endpoints
│   │   │   ├── conversations.py # Conversation endpoints
│   │   │   └── health.py        # Health check endpoints
│   │   ├── dependencies.py      # FastAPI dependencies (auth, DB, etc.)
│   │   └── middleware.py         # Custom middleware
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py          # Auth, rate limiting, sanitization
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── logging.py           # Structured logging setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py          # SQLAlchemy models
│   │   └── schemas.py           # Pydantic request/response models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rag_pipeline.py      # Main RAG orchestration
│   │   ├── query_processor.py   # Query processing logic
│   │   ├── retriever.py         # Vector search logic
│   │   ├── context_assembler.py # Context assembly logic
│   │   ├── prompt_builder.py    # Prompt construction
│   │   └── response_generator.py # LLM call and post-processing
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── parser.py            # Document parsing
│   │   ├── chunker.py           # Text chunking
│   │   ├── embedder.py          # Embedding generation
│   │   └── indexer.py           # Vector DB indexing
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py           # Database session management
│   │   └── vector_client.py     # Vector DB client
│   └── worker/
│       ├── __init__.py
│       └── tasks.py             # Celery tasks for document ingestion
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat/
│   │   │   ├── Admin/
│   │   │   └── Common/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   └── App.tsx
│   ├── package.json
│   └── tailwind.config.js
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── alembic/                     # Database migrations
├── docs/
│   ├── prd.md
│   └── architecture.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 13. Design Decisions & Trade-offs

### 13.1 Key Decisions

| # | Decision | Alternatives Considered | Rationale |
|---|---|---|---|
| 1 | **FastAPI over Flask** | Flask, Django REST | Async-native, automatic validation, OpenAPI docs, better performance. |
| 2 | **Chroma for v1 vector DB** | Pinecone, Weaviate, FAISS | Zero-infrastructure, easy local development, sufficient for <10K documents. |
| 3 | **OpenAI for LLM & embeddings** | Anthropic, self-hosted Llama | Best quality, fastest time-to-market, simple API. |
| 4 | **Celery for async ingestion** | In-process asyncio, RQ | Robust task queue, retry support, monitoring. |
| 5 | **PostgreSQL for relational data** | SQLite, MySQL | Production-grade, JSONB support, mature ecosystem. |
| 6 | **SSE over WebSockets** | WebSockets, polling | Simpler, unidirectional (server→client), works through proxies. |
| 7 | **React over Streamlit** | Streamlit, Vue | Production-ready, customizable, scalable. |

### 13.2 Trade-offs

| Trade-off | Choice Made | Cost | Benefit |
|---|---|---|---|
| **Local vector DB vs cloud** | Local (Chroma) for v1 | Limited scalability | Zero infra cost, fast local dev |
| **Managed LLM vs self-hosted** | Managed (OpenAI) | Ongoing API cost | Best quality, no GPU maintenance |
| **Sync vs async ingestion** | Async (Celery) | Added complexity | Non-blocking API, better UX |
| **Monolith vs microservices** | Modular monolith | Less independent deployability | Simpler deployment, faster development |

---

## 14. Future Architecture Evolution

### 14.1 v2.0 Target Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        v2.0 Architecture                             │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  Web UI  │  │  Mobile  │  │  API     │  │  Admin           │   │
│  │  (React) │  │  (React  │  │  Clients │  │  Dashboard       │   │
│  │          │  │  Native) │  │          │  │                  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │              │                  │             │
│       └──────────────┴──────────────┴──────────────────┘             │
│                              │                                       │
│                    ┌─────────▼──────────┐                            │
│                    │  API Gateway        │                            │
│                    │  (Kong / AWS API    │                            │
│                    │   Gateway)          │                            │
│                    └─────────┬──────────┘                            │
│                              │                                       │
│              ┌───────────────┼───────────────┐                       │
│              │               │               │                       │
│       ┌──────▼─────┐  ┌─────▼──────┐  ┌────▼──────┐               │
│       │  Chat      │  │  Document  │  │  Analytics │               │
│       │  Service   │  │  Service   │  │  Service   │               │
│       │  (FastAPI) │  │  (FastAPI) │  │  (FastAPI) │               │
│       └──────┬─────┘  └─────┬──────┘  └────────────┘               │
│              │               │                                       │
│       ┌──────▼─────┐  ┌─────▼──────┐                                │
│       │  Hybrid    │  │  Multi-    │                                │
│       │  Search    │  │  modal     │                                │
│       │  (BM25 +   │  │  Parser    │                                │
│       │  Vector)   │  │  (Images,  │                                │
│       │            │  │  Tables)   │                                │
│       └──────┬─────┘  └────────────┘                                │
│              │                                                       │
│       ┌──────▼─────────────────────────────────┐                    │
│       │  Re-ranking & Query Expansion          │                    │
│       │  (Cross-encoder, Query Rewriting)      │                    │
│       └──────┬─────────────────────────────────┘                    │
│              │                                                       │
│  ┌───────────▼───────────────────────────────────────────────────┐  │
│  │  Pinecone / Weaviate (Vector)  │  Elasticsearch (Full-text)  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 14.2 Migration Path

| From | To | Trigger | Effort |
|---|---|---|---|
| Chroma (local) | Pinecone (cloud) | > 10K documents | Low — config change |
| OpenAI GPT-4o | Self-hosted Llama 3 | Data sensitivity / cost | Medium — GPU infra |
| Modular monolith | Microservices | Team growth / scale | High — infrastructure |
| SSE streaming | WebSockets | Need bidirectional comm | Low — client change |

---

*End of Document*

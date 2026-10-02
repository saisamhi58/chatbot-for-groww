# RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot built with FastAPI, React, ChromaDB, and OpenAI.

## Project Scope (College Project)

- **AMC:** HDFC Mutual Fund
- **Schemes:** Large Cap, Flexi Cap, ELSS, Small Cap, Balanced Advantage (5 schemes/50+ pages)
- **Sources:** Groww public pages (listed in [docs/sources.md](./docs/sources.md))
- **Embedding model:** sentence-transformers/all-MiniLM-L6-v2 (384-dim, local)
- **Vector DB:** ChromaDB, persisted to `./data/chroma`
- **LLM:** Groq (`openai/gpt-oss-120b`, key in `.env`)
- **UI:** `app/web_demo.py` (tiny demo UI) + React frontend (planned)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- OpenAI API key

### Setup

1. **Clone and configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

2. **Start infrastructure:**
   ```bash
   docker-compose up -d postgres redis chroma
   ```

3. **Install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Start the API server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. **Start the Celery worker (separate terminal):**
   ```bash
   celery -A app.worker.tasks worker --loglevel=info
   ```

6. **Start the frontend (separate terminal):**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Access

| Service | URL |
|---|---|
| API Docs (Swagger) | http://localhost:8000/docs |
| Chat UI | http://localhost:5173 |
| Health Check | http://localhost:8000/health |

## Project Structure

```
ragchatbot/
├── app/                    # Backend application
│   ├── api/                # API routes and middleware
│   ├── core/               # Security, logging, exceptions
│   ├── db/                 # Database and vector DB clients
│   ├── ingestion/          # Document parsing, chunking, embedding
│   ├── models/             # SQLAlchemy models and Pydantic schemas
│   ├── services/           # RAG pipeline services
│   └── worker/             # Celery background tasks
├── frontend/               # React frontend
├── tests/                  # Test suite
├── alembic/                # Database migrations
├── docker-compose.yml      # Infrastructure services
└── requirements.txt        # Python dependencies
```

## How to Run (College Project Demo)

```powershell
# 1. Install deps
py -m pip install -r requirements.txt

# 2. Ingest the 5 Groww URLs (one time)
py scripts/ingest_urls.py

# 3. Export chunks to a readable txt for inspection
py scripts/export_chunks.py
# -> data/chunks.txt

# 4. Start the web UI
py -m uvicorn app.web_demo:app --port 8002
# Open http://localhost:8002
```

## Known Limitations

- Answers depend on the public pages' text; JS-heavy pages may extract noisy text.
- Embedding threshold tuned to 0.3 for these pages.
- No PII collection; no investment advice; no performance calculations.

## Documentation

- [PRD](./docs/prd.md) — Product Requirements Document
- [Architecture](./docs/architecture.md) — System Architecture
- [Implementation Guide](./docs/implementation.md) — Phase-by-phase implementation

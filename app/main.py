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

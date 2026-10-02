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
        doc_metadata={},
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


@router.post("/documents/url", response_model=DocumentUploadResponse)
async def ingest_url(
    url: str,
    title: str = "",
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Ingest a public web page by URL (fetches, chunks, embeds, indexes)."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL — must start with http:// or https://")

    doc_id = str(uuid.uuid4())
    document = Document(
        id=doc_id,
        filename=title or url,
        file_type="url",
        file_size=0,
        storage_path=url,
        status="pending",
        doc_metadata={"source_url": url},
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    process_document.delay(doc_id, url, "url")

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=title or url,
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

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
        source_url = (document.doc_metadata or {}).get("source_url", "")
        chunk_count = indexer.index_chunks(
            chunks=chunks,
            document_id=str(document_id),
            filename=document.filename,
            source_url=source_url,
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

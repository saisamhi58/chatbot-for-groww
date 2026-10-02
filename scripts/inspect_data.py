"""Inspect stored data: files, chunks, and ChromaDB contents."""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings
from app.db.vector_client import get_chroma_client

settings = get_settings()


def inspect_files():
    """List raw uploaded files."""
    print("=" * 60)
    print("RAW UPLOADED FILES")
    print("=" * 60)

    storage_path = settings.storage_path
    if not os.path.exists(storage_path):
        print(f"  Storage path does not exist: {storage_path}")
        print("  Upload a document first via POST /api/documents")
        return

    files = os.listdir(storage_path)
    if not files:
        print(f"  No files found in {storage_path}")
        return

    for f in files:
        file_path = os.path.join(storage_path, f)
        size = os.path.getsize(file_path)
        print(f"  {f} ({size:,} bytes)")


def inspect_chunks():
    """List chunks stored in ChromaDB."""
    print("\n" + "=" * 60)
    print("CHUNKS IN CHROMADB")
    print("=" * 60)

    try:
        client = get_chroma_client()
        collection = client.get_collection(settings.vector_db_collection)

        count = collection.count()
        print(f"  Total chunks: {count}")

        if count == 0:
            print("  No chunks found. Upload and process a document first.")
            return

        # Get sample chunks
        results = collection.get(
            include=["documents", "metadatas"],
            limit=min(5, count),
        )

        print(f"\n  Showing up to 5 sample chunks:")
        for i, (doc_id, doc, metadata) in enumerate(
            zip(results["ids"], results["documents"], results["metadatas"])
        ):
            print(f"\n  --- Chunk {i + 1} (ID: {doc_id[:8]}...) ---")
            print(f"  File: {metadata.get('filename', 'unknown')}")
            print(f"  Page: {metadata.get('page_number', 'N/A')}")
            print(f"  Chunk Index: {metadata.get('chunk_index', 'N/A')}")
            print(f"  Tokens: {metadata.get('token_count', 'N/A')}")
            preview = doc[:150].replace("\n", " ")
            print(f"  Preview: {preview}...")

    except Exception as e:
        print(f"  Error connecting to ChromaDB: {e}")
        print("  Make sure ChromaDB is running: docker-compose up -d chroma")


def inspect_documents_db():
    """List documents from PostgreSQL."""
    print("\n" + "=" * 60)
    print("DOCUMENTS IN POSTGRESQL")
    print("=" * 60)

    try:
        from app.models.database import SessionLocal, Document

        db = SessionLocal()
        documents = db.query(Document).order_by(Document.created_at.desc()).all()

        if not documents:
            print("  No documents found in database.")
            return

        for doc in documents:
            print(f"\n  ID: {doc.id}")
            print(f"  Filename: {doc.filename}")
            print(f"  Type: {doc.file_type}")
            print(f"  Size: {doc.file_size:,} bytes")
            print(f"  Status: {doc.status}")
            print(f"  Chunks: {doc.chunk_count}")
            print(f"  Uploaded: {doc.created_at}")
            if doc.error_message:
                print(f"  Error: {doc.error_message}")

        db.close()

    except Exception as e:
        print(f"  Error connecting to PostgreSQL: {e}")
        print("  Make sure PostgreSQL is running: docker-compose up -d postgres")


if __name__ == "__main__":
    import argparse

    print("\n" + "#" * 60)
    print("# RAG CHATBOT DATA INSPECTOR")
    print("#" * 60)

    parser = argparse.ArgumentParser(description="Inspect stored data")
    parser.add_argument("--collection", default=None, help="ChromaDB collection to inspect (default from .env)")
    parser.add_argument("--files-only", action="store_true", help="Only list uploaded files")
    parser.add_argument("--chunks-only", action="store_true", help="Only list ChromaDB chunks")
    parser.add_argument("--docs-only", action="store_true", help="Only list PostgreSQL documents")
    args = parser.parse_args()

    if args.collection:
        settings.vector_db_collection = args.collection

    if args.files_only:
        inspect_files()
    elif args.chunks_only:
        inspect_chunks()
    elif args.docs_only:
        inspect_documents_db()
    else:
        inspect_files()
        inspect_chunks()
        inspect_documents_db()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Storage path: {settings.storage_path}")
    print(f"  Vector DB: {settings.vector_db_host}:{settings.vector_db_port}")
    print(f"  Collection: {settings.vector_db_collection}")
    print(f"  Chunk size: {settings.chunk_size} tokens")
    print(f"  Chunk overlap: {settings.chunk_overlap} tokens")
    print()

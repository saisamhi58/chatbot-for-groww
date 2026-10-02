"""ChromaDB vector database client."""

import chromadb
from chromadb.config import Settings
from app.config import get_settings

settings = get_settings()


def get_chroma_client():
    """Get or create a ChromaDB client.

    Falls back to a local on-disk persistent client (./data/chroma) when the
    HTTP server (Docker) is not reachable.
    """
    import os
    persist_dir = os.path.join("data", "chroma")
    os.makedirs(persist_dir, exist_ok=True)
    print(f"Using local ChromaDB at {persist_dir}")
    return chromadb.PersistentClient(path=persist_dir)


def get_or_create_collection():
    """Get or create the knowledge base collection."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=settings.vector_db_collection,
        metadata={"hnsw:space": "cosine"},
    )
    return collection

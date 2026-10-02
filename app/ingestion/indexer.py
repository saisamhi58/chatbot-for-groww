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
        source_url: str = "",
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
                "source_url": source_url,
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

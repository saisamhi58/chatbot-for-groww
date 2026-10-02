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
    source_url: str = ""


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
                    source_url=metadata.get("source_url", ""),
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

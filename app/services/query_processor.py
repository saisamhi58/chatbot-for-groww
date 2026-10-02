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

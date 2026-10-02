"""Embedding generation using HuggingFace sentence-transformers (local)."""

from app.config import get_settings

settings = get_settings()


class HuggingFaceEmbedder:
    """Generate embeddings using a local HuggingFace sentence-transformers model."""

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model_name = settings.hf_embedding_model
        self.model = SentenceTransformer(self.model_name)

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [e.tolist() for e in embeddings]


# Backwards-compatible alias (imports elsewhere still work)
OpenAIEmbedder = HuggingFaceEmbedder

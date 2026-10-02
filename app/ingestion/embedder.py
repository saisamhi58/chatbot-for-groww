"""Embedding generation using HuggingFace sentence-transformers (local)."""

from app.config import get_settings

settings = get_settings()


class HuggingFaceEmbedder:
    """Generate embeddings using a local ONNX-based all-MiniLM-L6-v2 model
    (much lighter on memory than the full torch-based sentence-transformers)."""

    def __init__(self):
        import chromadb.utils.embedding_functions as ef
        self._ef = ef.DefaultEmbeddingFunction()

    def embed_text(self, text: str) -> list[float]:
        return self._ef([text])[0]

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        return self._ef(texts)


# Backwards-compatible alias (imports elsewhere still work)
OpenAIEmbedder = HuggingFaceEmbedder

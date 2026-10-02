"""Assemble retrieved chunks and conversation history into context."""

from dataclasses import dataclass, field
from typing import Optional
from app.services.retriever import RetrievedChunk
from app.config import get_settings

settings = get_settings()


@dataclass
class AssembledContext:
    """Assembled context for the LLM."""
    context_text: str
    sources: list[dict]
    total_tokens: int
    chunk_count: int


class ContextAssembler:
    """Assemble retrieved chunks into a coherent context for the LLM."""

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens

    def assemble(
        self,
        chunks: list[RetrievedChunk],
        conversation_history: Optional[list[dict]] = None,
    ) -> AssembledContext:
        """Assemble context from retrieved chunks and conversation history."""
        context_parts = []
        sources = []
        total_tokens = 0

        for i, chunk in enumerate(chunks):
            chunk_tokens = self._count_tokens(chunk.text)

            if total_tokens + chunk_tokens > self.max_tokens:
                break

            source_label = f"[Source {i + 1}: {chunk.filename}"
            if chunk.page_number:
                source_label += f", Page {chunk.page_number}"
            if chunk.source_url:
                source_label += f", {chunk.source_url}"
            source_label += "]"

            context_parts.append(f"{source_label}\n{chunk.text}")
            sources.append({
                "document_id": chunk.document_id,
                "filename": chunk.filename,
                "page": chunk.page_number,
                "source_url": chunk.source_url,
                "excerpt": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
            })
            total_tokens += chunk_tokens

        context_text = "\n\n---\n\n".join(context_parts)

        # Add conversation history if provided
        if conversation_history:
            history_text = self._format_history(conversation_history)
            context_text = f"{history_text}\n\n{context_text}"

        return AssembledContext(
            context_text=context_text,
            sources=sources,
            total_tokens=total_tokens,
            chunk_count=len(context_parts),
        )

    def _format_history(self, history: list[dict]) -> str:
        """Format conversation history."""
        parts = ["Conversation History:"]
        for msg in history[-5:]:  # Last 5 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role.capitalize()}: {content}")
        return "\n".join(parts)

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return len(text) // 4

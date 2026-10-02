"""Text chunking strategy for document segmentation."""

from dataclasses import dataclass, field
from typing import Optional
import re


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    text: str
    chunk_index: int
    token_count: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None


class RecursiveTextChunker:
    """Split text into overlapping chunks using recursive character splitting."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(
        self,
        text: str,
        pages: Optional[list[str]] = None,
    ) -> list[TextChunk]:
        """Split text into chunks with overlap."""
        # Split into paragraphs first
        paragraphs = self._split_paragraphs(text)

        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            if current_size + para_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        chunk_index=chunk_index,
                        token_count=self._count_tokens(chunk_text),
                    )
                )
                chunk_index += 1

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = [overlap_text] if overlap_text else []
                current_size = self._count_tokens(overlap_text) if overlap_text else 0

            current_chunk.append(para)
            current_size += para_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(
                TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    token_count=self._count_tokens(chunk_text),
                )
            )

        # Add page numbers if pages are provided
        if pages:
            chunks = self._assign_page_numbers(chunks, pages)

        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        paragraphs = re.split(r"\n+", text)
        return [p.strip() for p in paragraphs if p.strip()]
        return [p.strip() for p in paragraphs if p.strip()]

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken (cl100k_base for OpenAI models)."""
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            # Fallback: approximate 1 token = 4 characters
            return len(text) // 4

    def _get_overlap_text(self, current_chunk: list[str]) -> str:
        """Get overlap text from the end of the current chunk."""
        if not current_chunk:
            return ""

        overlap_tokens = 0
        overlap_parts = []

        for para in reversed(current_chunk):
            para_tokens = self._count_tokens(para)
            if overlap_tokens + para_tokens > self.chunk_overlap:
                break
            overlap_parts.insert(0, para)
            overlap_tokens += para_tokens

        return "\n\n".join(overlap_parts)

    def _assign_page_numbers(
        self, chunks: list[TextChunk], pages: list[str]
    ) -> list[TextChunk]:
        """Assign page numbers to chunks based on content matching."""
        page_texts = pages

        for chunk in chunks:
            chunk_start = chunk.text[:100]  # Use first 100 chars for matching
            for i, page_text in enumerate(page_texts):
                if chunk_start in page_text:
                    chunk.page_number = i + 1
                    break

        return chunks

"""Main RAG pipeline orchestrator."""

from dataclasses import dataclass, field
from typing import Optional, Generator
from app.services.query_processor import QueryProcessor
from app.services.retriever import VectorRetriever
from app.services.context_assembler import ContextAssembler
from app.services.prompt_builder import PromptBuilder
from app.services.response_generator import ResponseGenerator
from app.config import get_settings

settings = get_settings()


@dataclass
class RAGResult:
    """Result of the RAG pipeline."""
    answer: str
    sources: list[dict]
    retrieval_scores: list[float] = field(default_factory=list)


class RAGPipeline:
    """Orchestrate the full RAG pipeline."""

    def __init__(self):
        self.query_processor = QueryProcessor()
        self.retriever = VectorRetriever()
        self.context_assembler = ContextAssembler(max_tokens=settings.max_context_tokens)
        self.prompt_builder = PromptBuilder()
        self.response_generator = ResponseGenerator()

    def run(
        self,
        query: str,
        conversation_history: Optional[list[dict]] = None,
        top_k: Optional[int] = None,
    ) -> RAGResult:
        """Execute the full RAG pipeline."""
        # Step 1: Process query
        processed = self.query_processor.process(query)

        # Step 2: Retrieve relevant chunks
        chunks = self.retriever.retrieve(
            query_embedding=processed["embedding"],
            top_k=top_k or settings.top_k,
            similarity_threshold=settings.similarity_threshold,
        )

        # Step 3: Check if we have relevant context
        if not chunks:
            return RAGResult(
                answer="I don't have enough information in my knowledge base to answer that.",
                sources=[],
                retrieval_scores=[],
            )

        # Step 4: Assemble context
        context = self.context_assembler.assemble(chunks, conversation_history)

        # Step 5: Build prompt
        messages = self.prompt_builder.build(query, context)

        # Step 6: Generate response
        answer = self.response_generator.generate(messages)

        return RAGResult(
            answer=answer,
            sources=context.sources,
            retrieval_scores=[chunk.score for chunk in chunks],
        )

    def run_stream(
        self,
        query: str,
        conversation_history: Optional[list[dict]] = None,
        top_k: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """Execute the RAG pipeline with streaming response."""
        # Step 1: Process query
        processed = self.query_processor.process(query)

        # Step 2: Retrieve relevant chunks
        chunks = self.retriever.retrieve(
            query_embedding=processed["embedding"],
            top_k=top_k or settings.top_k,
            similarity_threshold=settings.similarity_threshold,
        )

        # Step 3: Check if we have relevant context
        if not chunks:
            yield "I don't have enough information in my knowledge base to answer that."
            return

        # Step 4: Assemble context
        context = self.context_assembler.assemble(chunks, conversation_history)

        # Step 5: Build prompt
        messages = self.prompt_builder.build(query, context)

        # Step 6: Stream response
        for token in self.response_generator.generate_stream(messages):
            yield token

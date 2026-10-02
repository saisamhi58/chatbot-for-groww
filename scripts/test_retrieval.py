"""Test the retrieval pipeline — query embedding, vector search, and chunk retrieval."""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.query_processor import QueryProcessor
from app.services.retriever import VectorRetriever
from app.services.context_assembler import ContextAssembler
from app.config import get_settings

settings = get_settings()


def test_retrieval(query: str, top_k: int = 5):
    """Test the full retrieval pipeline for a given query."""
    print("\n" + "=" * 80)
    print("RETRIEVAL TEST")
    print("=" * 80)
    print(f"\nQuery: {query}")
    print(f"Top K: {top_k}")
    print(f"Similarity Threshold: {settings.similarity_threshold}")

    # Step 1: Process query
    print("\n" + "-" * 80)
    print("STEP 1: Query Processing")
    print("-" * 80)

    processor = QueryProcessor()
    processed = processor.process(query)

    print(f"  Original Query: {processed['original_query']}")
    print(f"  Sanitized Query: {processed['sanitized_query']}")
    print(f"  Embedding Dimensions: {len(processed['embedding'])}")
    print(f"  Embedding Preview: {processed['embedding'][:5]}...")

    # Step 2: Retrieve chunks
    print("\n" + "-" * 80)
    print("STEP 2: Vector Retrieval")
    print("-" * 80)

    retriever = VectorRetriever()
    chunks = retriever.retrieve(
        query_embedding=processed["embedding"],
        top_k=top_k,
        similarity_threshold=settings.similarity_threshold,
    )

    if not chunks:
        print("  No chunks retrieved! Try lowering the similarity threshold or uploading documents.")
        return

    print(f"  Chunks Retrieved: {len(chunks)}")

    for i, chunk in enumerate(chunks):
        print(f"\n  --- Chunk {i + 1} ---")
        print(f"  Score: {chunk.score:.4f}")
        print(f"  Document: {chunk.filename}")
        print(f"  Page: {chunk.page_number}")
        print(f"  Chunk Index: {chunk.chunk_index}")
        preview = chunk.text[:200].replace("\n", " ")
        print(f"  Preview: {preview}...")

    # Step 3: Assemble context
    print("\n" + "-" * 80)
    print("STEP 3: Context Assembly")
    print("-" * 80)

    assembler = ContextAssembler(max_tokens=settings.max_context_tokens)
    context = assembler.assemble(chunks)

    print(f"  Total Tokens: {context.total_tokens}")
    print(f"  Chunk Count: {context.chunk_count}")
    print(f"  Sources: {len(context.sources)}")
    print(f"\n  Context Preview (first 500 chars):")
    print(f"  {context.context_text[:500]}...")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Query: {query}")
    print(f"  Chunks Retrieved: {len(chunks)}")
    print(f"  Avg Score: {sum(c.score for c in chunks) / len(chunks):.4f}")
    print(f"  Context Tokens: {context.total_tokens}")
    print(f"  Sources: {len(context.sources)}")
    print("=" * 80)


def test_multiple_queries():
    """Test retrieval with multiple sample queries."""
    queries = [
        "What is the refund policy?",
        "How do I reset my password?",
        "What are the shipping options?",
        "How do I contact customer support?",
        "What is the warranty period?",
    ]

    print("\n" + "#" * 80)
    print("# BATCH RETRIEVAL TEST")
    print("#" * 80)

    processor = QueryProcessor()
    retriever = VectorRetriever()

    for query in queries:
        print(f"\n{'─' * 60}")
        print(f"Query: {query}")
        print(f"{'─' * 60}")

        processed = processor.process(query)
        chunks = retriever.retrieve(
            query_embedding=processed["embedding"],
            top_k=3,
            similarity_threshold=0.5,  # Lower threshold for testing
        )

        if chunks:
            print(f"  Retrieved {len(chunks)} chunks:")
            for i, chunk in enumerate(chunks):
                print(f"    {i + 1}. Score: {chunk.score:.4f} | {chunk.filename} (p.{chunk.page_number})")
        else:
            print("  No chunks retrieved.")


if __name__ == "__main__":
    import argparse

    print("\n" + "#" * 80)
    print("# RAG CHATBOT — RETRIEVAL TEST")
    print("#" * 80)

    parser = argparse.ArgumentParser(description="Test the retrieval pipeline")
    parser.add_argument("query", nargs="?", help="Query text to test")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    parser.add_argument("--threshold", type=float, default=None, help="Similarity threshold override")
    parser.add_argument("--batch", action="store_true", help="Run multiple sample queries")
    args = parser.parse_args()

    if args.batch:
        test_multiple_queries()
    elif args.query:
        if args.threshold is not None:
            settings.similarity_threshold = args.threshold
        test_retrieval(args.query, top_k=args.top_k)
    else:
        print("\nChoose test mode:")
        print("  1. Single query test (detailed)")
        print("  2. Multiple queries test (batch)")
        print()

        choice = input("Enter choice (1 or 2, default=1): ").strip() or "1"

        if choice == "1":
            query = input("\nEnter your query: ").strip()
            if not query:
                query = "What is the refund policy?"
            test_retrieval(query)
        elif choice == "2":
            test_multiple_queries()
        else:
            print("Invalid choice. Running single query test.")
            test_retrieval("What is the refund policy?")

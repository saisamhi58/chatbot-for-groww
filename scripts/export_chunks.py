"""Export chunks and embeddings from ChromaDB to a text file."""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings
from app.db.vector_client import get_chroma_client

settings = get_settings()


def export_to_txt(output_path: str = None):
    """Export all chunks and embeddings to a text file."""
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "chunks.txt"
        )

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        client = get_chroma_client()
        collection = client.get_collection(settings.vector_db_collection)
        count = collection.count()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("RAG CHATBOT — CHUNKS & EMBEDDINGS EXPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Collection: {settings.vector_db_collection}\n")
            f.write(f"Total Chunks: {count}\n")
            f.write(f"Embedding Model: {settings.hf_embedding_model}\n")
            f.write(f"Chunk Size: {settings.chunk_size} tokens\n")
            f.write(f"Chunk Overlap: {settings.chunk_overlap} tokens\n")
            f.write("=" * 80 + "\n\n")

            if count == 0:
                f.write("No chunks found in the database.\n")
                f.write("Upload and process a document first.\n")
                print(f"Export saved to: {output_path}")
                return

            # Fetch all chunks in batches
            batch_size = 100
            offset = 0
            chunk_num = 0

            while offset < count:
                results = collection.get(
                    include=["documents", "metadatas", "embeddings"],
                    limit=batch_size,
                    offset=offset,
                )

                for i, (doc_id, doc, metadata, embedding) in enumerate(
                    zip(
                        results["ids"],
                        results["documents"],
                        results["metadatas"],
                        results["embeddings"],
                    )
                ):
                    chunk_num += 1
                    f.write(f"\n{'─' * 80}\n")
                    f.write(f"CHUNK #{chunk_num}\n")
                    f.write(f"{'─' * 80}\n")
                    f.write(f"ID:           {doc_id}\n")
                    f.write(f"Document ID:  {metadata.get('document_id', 'N/A')}\n")
                    f.write(f"Filename:     {metadata.get('filename', 'N/A')}\n")
                    f.write(f"Page Number:  {metadata.get('page_number', 'N/A')}\n")
                    f.write(f"Chunk Index:  {metadata.get('chunk_index', 'N/A')}\n")
                    f.write(f"Token Count:  {metadata.get('token_count', 'N/A')}\n")
                    f.write(f"Created At:   {metadata.get('created_at', 'N/A')}\n")
                    f.write(f"\n--- TEXT CONTENT ---\n")
                    f.write(f"{doc}\n")
                    f.write(f"\n--- EMBEDDING (first 20 dimensions) ---\n")
                    if embedding:
                        # Show first 20 dimensions
                        preview = embedding[:20]
                        f.write(f"Dimensions: {len(embedding)}\n")
                        f.write(f"Values: {preview}\n")
                        f.write(f"... ({len(embedding) - 20} more dimensions)\n")
                    else:
                        f.write("No embedding data available\n")

                offset += batch_size

            f.write(f"\n{'=' * 80}\n")
            f.write("END OF EXPORT\n")
            f.write(f"Total chunks exported: {chunk_num}\n")
            f.write(f"{'=' * 80}\n")

        print(f"Export saved to: {output_path}")
        print(f"Total chunks exported: {chunk_num}")

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure ChromaDB is running: docker-compose up -d chroma")


def export_to_json(output_path: str = None):
    """Export all chunks and embeddings to a JSON file."""
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            os.path.dirname(__file__), "..", "data", f"chunks_export_{timestamp}.json"
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        client = get_chroma_client()
        collection = client.get_collection(settings.vector_db_collection)
        count = collection.count()

        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "collection": settings.vector_db_collection,
                "total_chunks": count,
                "embedding_model": settings.hf_embedding_model,
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap,
            },
            "chunks": [],
        }

        batch_size = 100
        offset = 0

        while offset < count:
            results = collection.get(
                include=["documents", "metadatas", "embeddings"],
                limit=batch_size,
                offset=offset,
            )

            for doc_id, doc, metadata, embedding in zip(
                results["ids"],
                results["documents"],
                results["metadatas"],
                results["embeddings"],
            ):
                data["chunks"].append({
                    "id": doc_id,
                    "text": doc,
                    "metadata": metadata,
                    "embedding": embedding.tolist() if embedding is not None else None,
                })

            offset += batch_size

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"JSON export saved to: {output_path}")
        print(f"Total chunks exported: {len(data['chunks'])}")

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure ChromaDB is running: docker-compose up -d chroma")


if __name__ == "__main__":
    import argparse

    print("\n" + "#" * 60)
    print("# RAG CHATBOT — CHUNK & EMBEDDING EXPORTER")
    print("#" * 60 + "\n")

    parser = argparse.ArgumentParser(description="Export chunks and embeddings")
    parser.add_argument("--txt", action="store_true", help="Export as txt (default)")
    parser.add_argument("--json", action="store_true", help="Export as JSON")
    parser.add_argument("--output", "-o", default=None, help="Output file path")
    args = parser.parse_args()

    if args.json:
        export_to_json(args.output)
    else:
        # Default: txt export to data/chunks.txt (or --output path)
        export_to_txt(args.output)

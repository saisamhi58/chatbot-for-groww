"""One-time ingestion of the mutual fund FAQ source URLs into ChromaDB.

Run once (no Celery/Redis/Postgres needed):
    python scripts/ingest_urls.py

After this, ChromaDB persists the vectors to disk (docker volume), so you
don't need to re-ingest on restart.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings
from app.ingestion.parser import DocumentParser
from app.ingestion.chunker import RecursiveTextChunker
from app.ingestion.indexer import VectorIndexer

settings = get_settings()

SOURCE_URLS = [
    ("HDFC Large Cap Fund (Direct, Growth)", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    ("HDFC Equity Fund - Flexi Cap (Direct, Growth)", "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth"),
    ("HDFC ELSS Tax Saver Fund (Direct, Growth)", "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth"),
    ("HDFC Small Cap Fund (Direct, Growth)", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    ("HDFC Balanced Advantage Fund (Direct, Growth)", "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth"),
]

if __name__ == "__main__":
    parser = DocumentParser()
    chunker = RecursiveTextChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    indexer = VectorIndexer()

    for title, url in SOURCE_URLS:
        print(f"\nIngesting: {title}")
        try:
            parsed = parser.parse(url, "url")
            chunks = chunker.chunk_text(parsed.text, parsed.pages)
            n = indexer.index_chunks(chunks, document_id=url, filename=title, source_url=url)
            print(f"  -> {n} chunks indexed")
        except Exception as e:
            print(f"  !! Failed: {e}")

    print("\nDone. Run `python scripts/export_chunks.py` to inspect chunks.txt.")

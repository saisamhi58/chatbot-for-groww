from app.ingestion.chunker import RecursiveTextChunker


def test_chunker_creates_chunks():
    chunker = RecursiveTextChunker(chunk_size=50, chunk_overlap=10)
    text = "\n".join([f"Paragraph {i} with some text." for i in range(20)])
    chunks = chunker.chunk_text(text)
    assert len(chunks) > 1
    assert all(c.token_count > 0 for c in chunks)


def test_chunker_single_small_text():
    chunker = RecursiveTextChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_text("Short text.")
    assert len(chunks) == 1

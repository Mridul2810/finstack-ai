"""Tests: chunking behavior (offline-safe, no network)."""

from app import chunking

TEXT = ("Apple designs and sells iPhone, Mac, iPad, and services. " * 400)


def test_chunking_splits_long_text_with_metadata():
    chunks = chunking.chunk_text(TEXT, {"ticker": "AAPL", "filing": "10-K"})
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk["text"].strip()
        assert chunk["metadata"]["ticker"] == "AAPL"
        assert chunk["metadata"]["page_num"] >= 1
        assert chunk["metadata"]["page_estimated"] is True


def test_chunking_overlap_and_page_growth():
    chunks = chunking.chunk_text(TEXT, {"ticker": "AAPL"})
    pages = [c["metadata"]["page_num"] for c in chunks]
    assert pages == sorted(pages)
    assert pages[-1] > pages[0]
    # Overlap: consecutive chunks share some words
    first_words = set(chunks[0]["text"].split())
    second_words = set(chunks[1]["text"].split())
    assert first_words & second_words

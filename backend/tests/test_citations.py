"""Tests: citation formatting and source payloads."""

from app.rag import format_citation, format_sources


def test_format_citation():
    meta = {"ticker": "AAPL", "filing": "10-K", "filing_year": "2024",
            "page_num": 12}
    assert format_citation(meta) == "[AAPL 10-K 2024 p.12]"


def test_format_sources_shape():
    docs = [{"text": "x" * 600, "metadata": {"ticker": "MSFT",
            "filing": "10-K", "filing_year": "2024", "page_num": 9}}]
    sources = format_sources(docs)
    assert sources[0]["page"] == 9
    assert sources[0]["filing"] == "MSFT 10-K 2024"
    assert sources[0]["citation"] == "[MSFT 10-K 2024 p.9]"
    assert len(sources[0]["text"]) == 500  # truncated excerpt

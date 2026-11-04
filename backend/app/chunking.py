"""Chunking with LangChain's RecursiveCharacterTextSplitter.

Spec: 1000 tokens with 200 overlap, via from_tiktoken_encoder. Page numbers
are ESTIMATED from character offset (~3,000 chars per page) because EDGAR
HTML filings carry no page markers — the estimate is labelled as such in
the metadata so citations never pretend to be exact.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
CHARS_PER_PAGE_ESTIMATE = 3000


def get_splitter() -> RecursiveCharacterTextSplitter:
    """Tiktoken-based splitter; char-based fallback when offline.

    The spec is 1000 tokens / 200 overlap. tiktoken downloads its BPE
    table on first use, so environments without network fall back to an
    approximately equivalent character splitter (4000 chars / 800 overlap)
    instead of failing.
    """
    try:
        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
    except Exception:
        return RecursiveCharacterTextSplitter(
            chunk_size=4000, chunk_overlap=800
        )


def chunk_text(text: str, metadata: dict) -> list[dict]:
    """Split text into chunks, each with ticker/filing metadata + page estimate."""
    splitter = get_splitter()
    chunks = []
    offset = 0
    for piece in splitter.split_text(text):
        start = text.find(piece[:80], offset)
        if start == -1:
            start = offset
        offset = start + len(piece)
        chunks.append(
            {
                "text": piece,
                "metadata": {
                    **metadata,
                    "page_num": start // CHARS_PER_PAGE_ESTIMATE + 1,
                    "page_estimated": True,
                },
            }
        )
    return chunks

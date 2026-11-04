"""Ingestion pipeline: EDGAR 10-K -> S3 raw -> chunks -> Titan -> OpenSearch.

Also stores per-chunk metadata in DynamoDB (ticker, filing_date,
page_num). In demo mode every AWS call is replaced by local equivalents
(S3 -> local dict, DynamoDB -> JSONL) so the pipeline runs offline.
"""

import json
import os

from app import chunking, edgar, embeddings
from app.config import Settings, boto_session
from app.vectorstore import get_store

TICKERS = ["AAPL", "MSFT", "NVDA"]


class MetadataStore:
    """DynamoDB metadata in production, JSONL file in demo mode."""

    def __init__(self, settings: Settings, path: str = "filing_meta.jsonl"):
        self.settings = settings
        self.path = path
        self.table = None
        if not settings.demo and settings.filing_meta_table:
            self.table = boto_session(settings).resource("dynamodb").Table(
                settings.filing_meta_table
            )

    def put(self, item: dict) -> None:
        if self.table is not None:
            self.table.put_item(Item=item)
        else:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(item) + "\n")


def store_raw_filing(settings: Settings, ticker: str, text: str,
                     filing_date: str) -> str:
    """Persist the raw filing: S3 in production, local file in demo."""
    key = f"raw/{ticker}/{filing_date}.txt"
    if not settings.demo and settings.s3_bucket:
        boto_session(settings).client("s3").put_object(
            Bucket=settings.s3_bucket, Key=key, Body=text.encode()
        )
        return f"s3://{settings.s3_bucket}/{key}"
    os.makedirs("raw_filings", exist_ok=True)
    path = os.path.join("raw_filings", f"{ticker}_{filing_date}.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def ingest_ticker(ticker: str, settings: Settings, store=None,
                  meta: MetadataStore | None = None) -> dict:
    """Ingest the latest 10-K for one ticker. Returns chunk/index counts."""
    cik, company = edgar.resolve_ticker(ticker, settings)
    filing = edgar.latest_10k(cik, settings)
    text = edgar.download_filing_text(filing["url"], settings)
    location = store_raw_filing(settings, ticker, text, filing["filing_date"])
    base_meta = {
        "ticker": ticker.upper(),
        "company": company,
        "filing": "10-K",
        "filing_date": filing["filing_date"],
        "filing_year": filing["filing_date"][:4],
    }
    chunks = chunking.chunk_text(text, base_meta)
    store = store if store is not None else get_store(settings)
    vecs = embeddings.embed_texts([c["text"] for c in chunks], settings)
    store.add(
        [c["text"] for c in chunks], vecs, [c["metadata"] for c in chunks]
    )
    meta = meta if meta is not None else MetadataStore(settings)
    for chunk in chunks:
        meta.put({k: str(v) for k, v in chunk["metadata"].items()})
    return {
        "ticker": ticker.upper(),
        "company": company,
        "filing_date": filing["filing_date"],
        "raw_location": location,
        "chunks": len(chunks),
    }


def ingest_all(settings: Settings, tickers: list[str] | None = None) -> list[dict]:
    store = get_store(settings)
    meta = MetadataStore(settings)
    return [
        ingest_ticker(t, settings, store=store, meta=meta)
        for t in (tickers or TICKERS)
    ]

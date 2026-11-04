"""Lambda handler: S3 upload of a raw filing triggers ingestion.

In production the SAM template wires S3 ObjectCreated events to this
function. The handler downloads the object and runs the chunk/embed/index
steps for the ticker encoded in the key (raw/<TICKER>/<date>.txt).
"""

import json
import os

from app import chunking, embeddings
from app.config import Settings, boto_session
from app.vectorstore import get_store
from app.ingestion import MetadataStore


def lambda_handler(event, context):
    settings = Settings.from_env()
    store = get_store(settings)
    meta = MetadataStore(settings)
    results = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        parts = key.split("/")
        ticker = parts[1].upper() if len(parts) > 1 else "UNKNOWN"
        obj = boto_session(settings).client("s3").get_object(
            Bucket=bucket, Key=key
        )
        text = obj["Body"].read().decode("utf-8", errors="ignore")
        base_meta = {"ticker": ticker, "filing": "10-K", "s3_key": key}
        chunks = chunking.chunk_text(text, base_meta)
        vecs = embeddings.embed_texts([c["text"] for c in chunks], settings)
        store.add(
            [c["text"] for c in chunks], vecs, [c["metadata"] for c in chunks]
        )
        for chunk in chunks:
            meta.put({k: str(v) for k, v in chunk["metadata"].items()})
        results.append({"ticker": ticker, "chunks": len(chunks)})
    return {"statusCode": 200, "body": json.dumps(results)}

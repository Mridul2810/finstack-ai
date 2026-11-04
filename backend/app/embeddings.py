"""Embeddings: Bedrock Titan Embed v2 (real) + deterministic demo fallback.

Real path calls bedrock-runtime invoke_model with
amazon.titan-embed-text-v2:0. Demo path hashes tokens into a fixed-size
vector so the in-memory store works offline with no credentials.
"""

import hashlib
import json
import math

from app.config import Settings, boto_session

DEMO_DIM = 128


def embed_texts_bedrock(texts: list[str], settings: Settings) -> list[list[float]]:
    """Real Titan Embed v2 embeddings via boto3 (requires AWS credentials)."""
    client = boto_session(settings).client("bedrock-runtime")
    out = []
    for text in texts:
        resp = client.invoke_model(
            modelId=settings.bedrock_embed_model_id,
            body=json.dumps({"inputText": text}),
        )
        out.append(json.loads(resp["body"].read())["embedding"])
    return out


def embed_texts_demo(texts: list[str], dim: int = DEMO_DIM) -> list[list[float]]:
    """Deterministic bag-of-words-hash embeddings for offline demo/tests."""
    vectors = []
    for text in texts:
        vec = [0.0] * dim
        for token in text.lower().split():
            vec[int(hashlib.md5(token.encode()).hexdigest(), 16) % dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        vectors.append([v / norm for v in vec])
    return vectors


def embed_texts(texts: list[str], settings: Settings) -> list[list[float]]:
    if settings.demo:
        return embed_texts_demo(texts)
    return embed_texts_bedrock(texts, settings)

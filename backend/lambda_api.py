"""Lambda handler for the RAG API behind API Gateway (SAM template).

Routes POST /ask and POST /memo to the same logic as the FastAPI app,
without the FastAPI dependency, so the Lambda package stays small.
"""

import json

from app import demo_store, memo as memo_mod, rag
from app.config import Settings


def _body(event) -> dict:
    try:
        return json.loads(event.get("body") or "{}")
    except Exception:
        return {}


def lambda_handler(event, context):
    settings = Settings.from_env()
    store = demo_store.seeded_demo_store() if settings.demo else None
    path = event.get("rawPath") or event.get("path") or ""
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    params = event.get("queryStringParameters") or {}

    if path.endswith("/ask") and method == "POST":
        data = _body(event)
        result = rag.answer_question(
            data.get("query", ""), data.get("ticker"),
            data.get("chat_history", []), settings, store=store,
        )
        return {"statusCode": 200, "body": json.dumps({
            "answer": result["answer"], "sources": result["sources"],
            "latency_ms": result["latency_ms"], "cost": result["cost_usd"],
        })}
    if path.endswith("/memo") and method == "POST":
        import base64

        data = _body(event)
        result = rag.answer_question(
            data.get("query", "Summarize this company's latest 10-K."),
            data.get("ticker"), [], settings, store=store,
        )
        pdf = memo_mod.build_memo_pdf(
            data.get("ticker") or "", data.get("query", ""),
            result["answer"], result["sources"],
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/pdf"},
            "body": base64.b64encode(pdf).decode(),
            "isBase64Encoded": True,
        }
    if path.endswith("/health"):
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}
    return {"statusCode": 404, "body": json.dumps({"error": "not found"})}

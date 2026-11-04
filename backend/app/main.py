"""FastAPI RAG API: /ask, /ask/stream (SSE), /memo (PDF), /eval, /feedback.

Run locally in demo mode (no keys, no AWS):
    cd backend && DEMO=1 PYTHONPATH=. uvicorn app.main:app --reload
"""

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app import demo_store, memo as memo_mod, observability, rag
from app.config import Settings
from app.eval import get_dashboard
from app.history import get_history_store


class AskRequest(BaseModel):
    query: str
    ticker: str | None = None
    chat_history: list[dict] = []
    session_id: str = "default"


class MemoRequest(BaseModel):
    ticker: str | None = None
    query: str = "Summarize this company's latest 10-K."


class FeedbackRequest(BaseModel):
    value: str
    run_id: str | None = None
    comment: str = ""


def create_app(settings: Settings | None = None,
               store=None, history_store=None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = store if store is not None else (
        demo_store.seeded_demo_store() if settings.demo else None
    )
    history = history_store if history_store is not None \
        else get_history_store(settings)
    app = FastAPI(title="FinStack AI - Equity Research Copilot")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "demo" if settings.demo else "bedrock"}

    @app.post("/ask")
    def ask(req: AskRequest):
        history.append(req.session_id, "user", req.query)
        result = rag.answer_question(
            req.query, req.ticker, req.chat_history, settings, store=store
        )
        history.append(req.session_id, "assistant", result["answer"])
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "latency_ms": result["latency_ms"],
            "cost": result["cost_usd"],
            "cost_usd": result["cost_usd"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
        }

    @app.get("/ask/stream")
    def ask_stream(query: str, ticker: str | None = None):
        def gen():
            result = rag.answer_question(
                query, ticker, [], settings, store=store
            )
            text = result["answer"]
            for i in range(0, len(text), 120):
                yield f"data: {json.dumps({'token': text[i:i + 120]})}\n\n"
            yield f"data: {json.dumps({'sources': result['sources'], 'latency_ms': result['latency_ms'], 'cost': result['cost_usd']})}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.post("/memo")
    def make_memo(req: MemoRequest):
        result = rag.answer_question(
            req.query, req.ticker, [], settings, store=store
        )
        pdf = memo_mod.build_memo_pdf(
            req.ticker or "", req.query, result["answer"], result["sources"]
        )
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=memo.pdf"},
        )

    @app.get("/eval")
    def eval_dashboard():
        return get_dashboard()

    @app.post("/feedback")
    def feedback(req: FeedbackRequest):
        return observability.log_feedback(req.value, req.run_id, req.comment)

    return app


app = create_app()

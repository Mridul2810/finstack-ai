"""Tests: FastAPI endpoints in demo mode (TestClient, no network)."""

from fastapi.testclient import TestClient

from app import demo_store
from app.config import Settings
from app.history import InMemoryHistoryStore
from app.main import create_app


def _client():
    settings = Settings(demo=True)
    app = create_app(
        settings=settings,
        store=demo_store.seeded_demo_store(),
        history_store=InMemoryHistoryStore(),
    )
    return TestClient(app)


def test_health():
    assert _client().get("/health").json()["mode"] == "demo"


def test_ask_returns_answer_sources_latency_cost():
    resp = _client().post("/ask", json={
        "query": "What are Apple's risk factors?",
        "ticker": "AAPL",
        "chat_history": [],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "10-K 2024 p." in data["answer"]
    assert data["sources"]
    assert data["sources"][0]["citation"].startswith("[AAPL")
    assert isinstance(data["latency_ms"], int)
    assert isinstance(data["cost"], float)


def test_ask_stream_sse():
    resp = _client().get("/ask/stream",
                         params={"query": "NVDA growth?", "ticker": "NVDA"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "data:" in resp.text
    assert "sources" in resp.text


def test_memo_returns_pdf():
    resp = _client().post("/memo", json={
        "ticker": "MSFT", "query": "Summarize Microsoft's cloud business.",
    })
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_eval_no_run_yet(monkeypatch, tmp_path):
    monkeypatch.setenv("EVAL_RESULTS_PATH", str(tmp_path / "none.json"))
    assert _client().get("/eval").json() == {"status": "no eval run yet"}


def test_feedback_local_fallback(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    resp = _client().post("/feedback", json={"value": "up"})
    assert resp.json()["stored"] == "local"
    assert (tmp_path / "feedback.jsonl").exists()

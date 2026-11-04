"""Tests: eval metric computation (never hardcoded)."""

from app import eval as eval_mod


def _fake_answer_factory():
    def answer_fn(question, ticker):
        return {
            "answer": f"{ticker} growth is led by cloud and AI. "
                      f"[{ticker} 10-K 2024 p.9]",
            "sources": [{"filing": f"{ticker} 10-K 2024", "text": "x"}],
            "latency_ms": 100,
            "cost_usd": 0.001,
        }
    return answer_fn


def test_score_item_computes_precision_and_citation():
    item = {"id": "t1", "ticker": "MSFT", "expected_keywords": ["cloud"]}
    result = _fake_answer_factory()("q", "MSFT")
    scored = eval_mod.score_item(item, result)
    assert scored["citation_present"] is True
    assert scored["retrieval_precision"] == 1.0
    assert scored["keyword_rate"] == 1.0


def test_run_eval_aggregates_and_labels_mode():
    items = [
        {"id": "t1", "question": "q", "ticker": "MSFT", "expected_keywords": ["cloud"]},
        {"id": "t2", "question": "q", "ticker": "AAPL", "expected_keywords": ["nope"]},
    ]
    metrics = eval_mod.run_eval(_fake_answer_factory(), items,
                                mode="local-mock")
    assert metrics["mode"] == "local-mock"
    assert metrics["n"] == 2
    assert metrics["citation_rate"] == 1.0
    assert metrics["avg_retrieval_precision"] == 1.0
    assert 0.0 <= metrics["avg_keyword_rate"] <= 1.0


def test_dashboard_no_run_yet(monkeypatch, tmp_path):
    monkeypatch.setenv("EVAL_RESULTS_PATH", str(tmp_path / "none.json"))
    assert eval_mod.get_dashboard() == {"status": "no eval run yet"}

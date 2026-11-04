"""Evaluation harness: runs datasets/equity_qa_eval.json and COMPUTES metrics.

No metric is ever hardcoded. Before any run the dashboard reports
"no eval run yet". A local run (--demo) uses the fake retriever/LLM and
its output is labelled mode="local-mock" — it proves the pipeline works
and must never be presented as production accuracy.
"""

import json
import os
import re
import time
from pathlib import Path

CITATION_RE = re.compile(r"\[[A-Z]+ 10-K \d{4} p\.\d+\]")


def dataset_path() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "datasets" / "equity_qa_eval.json"
        if candidate.exists():
            return candidate
    return Path("datasets/equity_qa_eval.json")


def load_dataset(path: str | None = None) -> list[dict]:
    with open(path or dataset_path(), encoding="utf-8") as fh:
        return json.load(fh)["items"]


def score_item(item: dict, result: dict) -> dict:
    answer = result.get("answer", "")
    sources = result.get("sources", [])
    citation_present = bool(CITATION_RE.search(answer))
    matched = sum(
        1 for s in sources
        if s.get("filing", "").startswith(item["ticker"])
    )
    precision = matched / len(sources) if sources else 0.0
    keyword_hits = sum(
        1 for kw in item.get("expected_keywords", [])
        if kw.lower() in answer.lower()
    )
    keyword_rate = (
        keyword_hits / len(item["expected_keywords"])
        if item.get("expected_keywords") else 0.0
    )
    return {
        "id": item["id"],
        "citation_present": citation_present,
        "retrieval_precision": round(precision, 4),
        "keyword_rate": round(keyword_rate, 4),
        "latency_ms": result.get("latency_ms", 0),
        "cost_usd": result.get("cost_usd", 0.0),
    }


def run_eval(answer_fn, items: list[dict], mode: str) -> dict:
    """answer_fn(question, ticker) -> result dict with answer/sources."""
    scored = []
    for item in items:
        started = time.time()
        result = answer_fn(item["question"], item["ticker"])
        if "latency_ms" not in result:
            result["latency_ms"] = int((time.time() - started) * 1000)
        scored.append(score_item(item, result))
    n = len(scored) or 1
    return {
        "mode": mode,
        "n": len(scored),
        "citation_rate": round(
            sum(s["citation_present"] for s in scored) / n, 4
        ),
        "avg_retrieval_precision": round(
            sum(s["retrieval_precision"] for s in scored) / n, 4
        ),
        "avg_keyword_rate": round(
            sum(s["keyword_rate"] for s in scored) / n, 4
        ),
        "avg_latency_ms": round(
            sum(s["latency_ms"] for s in scored) / n, 1
        ),
        "avg_cost_usd": round(sum(s["cost_usd"] for s in scored) / n, 6),
        "items": scored,
    }


def results_path() -> str:
    return os.getenv("EVAL_RESULTS_PATH", "eval_results.json")


def get_dashboard() -> dict:
    path = results_path()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"status": "no eval run yet"}


def main() -> None:
    import argparse

    from app import demo_store
    from app.config import Settings
    from app.rag import answer_question

    parser = argparse.ArgumentParser(description="Run the equity QA eval.")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--out", default=results_path())
    args = parser.parse_args()
    settings = Settings.from_env()
    settings.demo = settings.demo or args.demo
    store = demo_store.seeded_demo_store() if settings.demo else None

    def answer_fn(question, ticker):
        return answer_question(question, ticker, [], settings, store=store)

    metrics = run_eval(
        answer_fn, load_dataset(),
        mode="local-mock" if settings.demo else "bedrock",
    )
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    print(json.dumps({k: v for k, v in metrics.items() if k != "items"},
                     indent=2))


if __name__ == "__main__":
    main()

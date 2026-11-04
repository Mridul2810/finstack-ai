"""Observability: LangSmith tracing + Langfuse as an alternative sink.

@traceable is real only when LANGCHAIN_API_KEY is set; otherwise it is an
identity decorator so tests and demo runs never need credentials.
Langfuse attaches as a callback when its keys are present (guarded import).
"""

import os
import warnings

try:
    from langsmith import traceable as _ls_traceable
except Exception:
    _ls_traceable = None


def traceable(func):
    """LangSmith @traceable when configured, identity otherwise."""
    if _ls_traceable is not None and os.getenv("LANGCHAIN_API_KEY"):
        return _ls_traceable(func)
    return func


def get_langfuse_callback(settings) -> object | None:
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            from langfuse.langchain import CallbackHandler

            return CallbackHandler()
        except Exception as exc:
            warnings.warn(f"Langfuse callback unavailable: {exc}")
    return None


def log_feedback(value: str, run_id: str | None = None,
                 comment: str = "", path: str = "feedback.jsonl") -> dict:
    """Thumbs up/down: LangSmith when configured, local JSONL otherwise."""
    import json

    entry = {"value": value, "run_id": run_id, "comment": comment}
    if os.getenv("LANGCHAIN_API_KEY") and run_id:
        try:
            from langsmith import Client

            Client().create_feedback(
                run_id=run_id,
                key="user-feedback",
                score=1 if value == "up" else 0,
                comment=comment,
            )
            return {"stored": "langsmith", **entry}
        except Exception:
            pass
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return {"stored": "local", **entry}

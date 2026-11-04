"""Compliance guardrails.

Two layers: (1) Bedrock Guardrails when BEDROCK_GUARDRAIL_ID is configured
(real AWS path, via the ApplyGuardrail API); (2) a local pre-filter that
ALWAYS runs — PII-pattern redaction plus a not-financial-advice disclaimer
— so demo mode and guardrail outages still stay compliant.
"""

import re

from app.config import Settings, boto_session

DISCLAIMER = "This is a factual summary, not financial advice."

PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "[REDACTED-EMAIL]"),
    (re.compile(r"\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b"), "[REDACTED-CARD]"),
    (re.compile(r"\b\d{3}[- ]\d{3}[- ]\d{4}\b"), "[REDACTED-PHONE]"),
]


def redact_pii(text: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def apply_local_filter(text: str) -> str:
    """Redact PII and append the advice disclaimer when missing."""
    text = redact_pii(text)
    if DISCLAIMER not in text:
        text = f"{text}\n\n{DISCLAIMER}"
    return text


def apply_bedrock_guardrail(text: str, settings: Settings) -> str | None:
    """Return None when the text passes, or a block message when intervened.

    Returns the original text when no guardrail is configured or the call
    fails, so the local filter (which always runs) remains the backstop.
    """
    if settings.demo or not settings.bedrock_guardrail_id:
        return text
    try:
        client = boto_session(settings).client("bedrock-runtime")
        resp = client.apply_guardrail(
            guardrailIdentifier=settings.bedrock_guardrail_id,
            guardrailVersion="DRAFT",
            source="INPUT",
            content=[{"text": {"text": text}}],
        )
        if resp.get("action") == "GUARDRAIL_INTERVENED":
            return (
                "This request was blocked by the compliance guardrail. "
                f"{DISCLAIMER}"
            )
    except Exception:
        pass
    return text

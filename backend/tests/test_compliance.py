"""Tests: compliance filter (PII redaction + disclaimer)."""

from app import compliance


def test_redacts_pii_patterns():
    text = ("Contact john@example.com or 555-123-4567, SSN 123-45-6789, "
            "card 4111-1111-1111-1111.")
    out = compliance.apply_local_filter(text)
    assert "john@example.com" not in out
    assert "123-45-6789" not in out
    assert "4111-1111-1111-1111" not in out
    assert "[REDACTED-EMAIL]" in out
    assert "[REDACTED-PHONE]" in out
    assert "[REDACTED-SSN]" in out
    assert "[REDACTED-CARD]" in out


def test_disclaimer_appended_once():
    once = compliance.apply_local_filter("hello")
    assert once.count(compliance.DISCLAIMER) == 1
    twice = compliance.apply_local_filter(once)
    assert twice.count(compliance.DISCLAIMER) == 1


def test_guardrail_passthrough_without_config():
    from app.config import Settings

    assert compliance.apply_bedrock_guardrail("hello", Settings(demo=True)) \
        == "hello"

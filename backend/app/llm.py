"""LLM access: Bedrock Claude 3.5 Sonnet (real) + demo fallback."""

from app.config import Settings

SYSTEM_PROMPT = (
    "You are a DriveWealth compliance-aware equity analyst. "
    "Always cite sources as [Ticker 10-K 2024 p.X]. "
    "Flag any risk factors. "
    "Never give financial advice, only factual summary."
)


def get_chat_model(settings: Settings):
    """ChatBedrock in production; a canned Runnable in demo mode."""
    if settings.demo:
        from langchain_core.messages import AIMessage
        from langchain_core.runnables import RunnableLambda

        return RunnableLambda(
            lambda prompt: AIMessage(content="Demo response (see rag.answer).")
        )
    from langchain_aws import ChatBedrock

    kwargs = {
        "model_id": settings.bedrock_model_id,
        "region_name": settings.aws_region,
        "model_kwargs": {"temperature": 0, "max_tokens": 2000},
    }
    if settings.bedrock_guardrail_id:
        # Guarded: older langchain-aws versions lack the guardrails kwarg.
        try:
            return ChatBedrock(
                **kwargs,
                guardrails={
                    "guardrailIdentifier": settings.bedrock_guardrail_id,
                    "guardrailVersion": "DRAFT",
                    "trace": "enabled",
                },
            )
        except TypeError:
            pass
    return ChatBedrock(**kwargs)

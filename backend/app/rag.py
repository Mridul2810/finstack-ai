"""RAG agent: history-aware retrieval + LCEL chain over 10-K chunks.

Real path: LangChain history-aware retriever -> stuff-documents chain ->
retrieval chain, running on Bedrock Claude 3.5 Sonnet. Demo path: the
seeded in-memory store + canned answers, so the API works with no keys.

Cost figures are ESTIMATES from public Bedrock list prices (Claude 3.5
Sonnet ~$3/1M input tokens, ~$15/1M output tokens, Titan Embed v2 ~$0.20/1M
tokens) and are labelled as such wherever surfaced.
"""

import time

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from app import compliance, demo_store, embeddings
from app.config import Settings
from app.llm import SYSTEM_PROMPT, get_chat_model
from app.observability import traceable

CLAUDE_INPUT_PER_1M = 3.00
CLAUDE_OUTPUT_PER_1M = 15.00
TITAN_PER_1M = 0.20


def format_citation(metadata: dict) -> str:
    """[Ticker 10-K YEAR p.PAGE] — the citation format used everywhere."""
    return (
        f"[{metadata.get('ticker', 'UNK')} "
        f"{metadata.get('filing', '10-K')} "
        f"{metadata.get('filing_year', '2024')} "
        f"p.{metadata.get('page_num', '?')}]"
    )


def format_sources(docs: list[dict]) -> list[dict]:
    return [
        {
            "text": d["text"][:500],
            "page": d["metadata"].get("page_num"),
            "filing": (
                f"{d['metadata'].get('ticker', '')} "
                f"{d['metadata'].get('filing', '10-K')} "
                f"{d['metadata'].get('filing_year', '')}"
            ),
            "citation": format_citation(d["metadata"]),
        }
        for d in docs
    ]


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Rough cost estimate (see module docstring for the price basis)."""
    return round(
        input_tokens / 1_000_000 * CLAUDE_INPUT_PER_1M
        + output_tokens / 1_000_000 * CLAUDE_OUTPUT_PER_1M,
        6,
    )


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class StoreRetriever(BaseRetriever):
    """LangChain retriever over any store with .search(embedding, k, ticker)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    store: object
    settings: object
    ticker: str | None = None
    k: int = 4

    def _get_relevant_documents(self, query, *, run_manager=None):
        emb = embeddings.embed_texts([query], self.settings)[0]
        docs = self.store.search(emb, k=self.k, ticker=self.ticker)
        return [
            Document(page_content=d["text"], metadata=d["metadata"])
            for d in docs
        ]


def build_chain(settings: Settings, retriever):
    """History-aware retriever + stuff-documents LCEL retrieval chain."""
    from langchain.chains.combine_documents import create_stuff_documents_chain
    from langchain.chains.history_aware_retriever import (
        create_history_aware_retriever,
    )
    from langchain.chains.retrieval import create_retrieval_chain

    llm = get_chat_model(settings)
    condense_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Given the chat history and a follow-up question, "
                        "rephrase the follow-up as a standalone question."),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware = create_history_aware_retriever(
        llm, retriever, condense_prompt
    )
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT + "\n\nContext:\n{context}"),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    qa_chain = create_stuff_documents_chain(llm, qa_prompt)
    return create_retrieval_chain(history_aware, qa_chain)


def _to_messages(chat_history: list[dict]):
    out = []
    for msg in chat_history or []:
        if msg.get("role") == "user":
            out.append(HumanMessage(content=msg.get("content", "")))
        else:
            out.append(AIMessage(content=msg.get("content", "")))
    return out


@traceable
def answer_question(question: str, ticker: str | None,
                    chat_history: list[dict], settings: Settings,
                    store=None) -> dict:
    """Answer with citations. Returns answer/sources/latency_ms/cost."""
    started = time.time()
    question = compliance.apply_bedrock_guardrail(question, settings)
    if settings.demo:
        store = store if store is not None else demo_store.seeded_demo_store()
        emb = embeddings.embed_texts_demo([question])[0]
        docs = store.search(emb, k=4, ticker=ticker)
        sources = format_sources(docs)
        base = demo_store.DEMO_ANSWERS.get(
            (ticker or "").upper(),
            "No demo answer for this ticker. "
            + (" ".join(s["citation"] for s in sources)),
        )
        answer = compliance.apply_local_filter(base)
        return {
            "answer": answer,
            "sources": sources,
            "latency_ms": int((time.time() - started) * 1000),
            "cost_usd": estimate_cost_usd(
                estimate_tokens(question), estimate_tokens(answer)
            ),
            "input_tokens": estimate_tokens(question),
            "output_tokens": estimate_tokens(answer),
            "mode": "demo",
        }
    retriever = StoreRetriever(store=store, settings=settings, ticker=ticker)
    chain = build_chain(settings, retriever)
    result = chain.invoke(
        {"input": question, "chat_history": _to_messages(chat_history)}
    )
    answer = compliance.apply_local_filter(result["answer"])
    docs = [
        {"text": d.page_content, "metadata": d.metadata}
        for d in result.get("context", [])
    ]
    latency_ms = int((time.time() - started) * 1000)
    usage = result.get("answer_usage", {}) or {}
    in_tokens = usage.get("input_tokens", estimate_tokens(question))
    out_tokens = usage.get("output_tokens", estimate_tokens(answer))
    return {
        "answer": answer,
        "sources": format_sources(docs),
        "latency_ms": latency_ms,
        "cost_usd": estimate_cost_usd(in_tokens, out_tokens),
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "mode": "bedrock",
    }


def stream_answer(question: str, ticker: str | None,
                  chat_history: list[dict], settings: Settings,
                  store=None):
    """Yield answer chunks (SSE-friendly). Demo mode chunks the canned text."""
    result = answer_question(question, ticker, chat_history, settings, store)
    text = result["answer"]
    for i in range(0, len(text), 120):
        yield text[i:i + 120]
    yield ""  # terminator chunk; the API appends the sources payload

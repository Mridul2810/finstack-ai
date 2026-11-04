"""Tests: retriever over the fake in-memory store."""

from app import demo_store, embeddings


def test_retriever_filters_by_ticker():
    store = demo_store.seeded_demo_store()
    emb = embeddings.embed_texts_demo(["Azure cloud growth"])[0]
    docs = store.search(emb, k=4, ticker="MSFT")
    assert docs
    assert all(d["metadata"]["ticker"] == "MSFT" for d in docs)


def test_retriever_returns_most_relevant_first():
    store = demo_store.seeded_demo_store()
    emb = embeddings.embed_texts_demo(["GPU data center AI training"])[0]
    docs = store.search(emb, k=2)
    assert docs[0]["metadata"]["ticker"] == "NVDA"


def test_retriever_empty_store_returns_empty():
    from app.vectorstore import InMemoryVectorStore

    store = InMemoryVectorStore()
    emb = embeddings.embed_texts_demo(["anything"])[0]
    assert store.search(emb) == []

"""Demo fixtures: seeded 10-K-style passages for AAPL/MSFT/NVDA.

Used by demo mode and tests. These are short illustrative passages in the
style of 10-K disclosures — not verbatim filing text — so the demo runs
offline without implying real filing quotes.
"""

from app import embeddings
from app.vectorstore import InMemoryVectorStore

DEMO_DOCS = [
    {
        "ticker": "AAPL",
        "text": (
            "Apple designs and sells iPhone, Mac, iPad, and services. The "
            "company's risk factors include intense competition in consumer "
            "electronics, dependence on a concentrated supplier base, and "
            "exposure to foreign exchange fluctuations."
        ),
        "page_num": 12,
    },
    {
        "ticker": "AAPL",
        "text": (
            "Apple's services segment, including the App Store, licensing, "
            "and subscriptions, has grown as a share of total net sales, "
            "while hardware remains the largest contributor."
        ),
        "page_num": 24,
    },
    {
        "ticker": "MSFT",
        "text": (
            "Microsoft's cloud segment, led by Azure, is a primary growth "
            "driver. Risk factors include cybersecurity threats, competition "
            "in cloud services, and the pace of AI infrastructure investment."
        ),
        "page_num": 9,
    },
    {
        "ticker": "MSFT",
        "text": (
            "Microsoft reports revenue across Productivity and Business "
            "Processes, Intelligent Cloud, and More Personal Computing, with "
            "commercial cloud offerings spanning Azure and Microsoft 365."
        ),
        "page_num": 21,
    },
    {
        "ticker": "NVDA",
        "text": (
            "NVIDIA's data center platform, built on GPU accelerated "
            "computing, serves AI training and inference workloads. Risk "
            "factors include customer concentration, export controls, and "
            "supply constraints in advanced chip manufacturing."
        ),
        "page_num": 7,
    },
    {
        "ticker": "NVDA",
        "text": (
            "NVIDIA's gaming, professional visualization, and automotive "
            "segments complement data center revenue, with AI infrastructure "
            "demand cited as the dominant growth theme."
        ),
        "page_num": 18,
    },
]


def seeded_demo_store() -> InMemoryVectorStore:
    """In-memory store pre-loaded with the demo passages."""
    from app.config import Settings

    settings = Settings(demo=True)
    store = InMemoryVectorStore()
    texts = [d["text"] for d in DEMO_DOCS]
    vecs = embeddings.embed_texts_demo(texts)
    metas = [
        {
            "ticker": d["ticker"],
            "filing": "10-K",
            "filing_year": "2024",
            "page_num": d["page_num"],
            "page_estimated": False,
        }
        for d in DEMO_DOCS
    ]
    store.add(texts, vecs, metas)
    return store


DEMO_ANSWERS = {
    "AAPL": (
        "Apple's business spans iPhone, Mac, iPad, and a growing services "
        "segment. Key risk factors flagged in its disclosures include intense "
        "competition, supplier concentration, and foreign exchange exposure. "
        "[AAPL 10-K 2024 p.12]"
    ),
    "MSFT": (
        "Microsoft's growth is led by its cloud segment, with Azure at the "
        "center, alongside Microsoft 365. Disclosed risk factors include "
        "cybersecurity threats and cloud competition. [MSFT 10-K 2024 p.9]"
    ),
    "NVDA": (
        "NVIDIA's data center platform for AI training and inference is its "
        "dominant growth theme. Disclosed risk factors include customer "
        "concentration, export controls, and chip supply constraints. "
        "[NVDA 10-K 2024 p.7]"
    ),
}

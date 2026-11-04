"""SEC EDGAR access: resolve tickers and download the latest 10-K.

Free, no API key. SEC requires a descriptive User-Agent header — set
SEC_USER_AGENT to something identifying you.
"""

import re

import requests

from app.config import Settings

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"


def _headers(settings: Settings) -> dict:
    return {"User-Agent": settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}


def resolve_ticker(ticker: str, settings: Settings) -> tuple[int, str]:
    """Return (CIK, company name) for a ticker, or raise ValueError."""
    resp = requests.get(TICKERS_URL, headers=_headers(settings), timeout=30)
    resp.raise_for_status()
    for entry in resp.json().values():
        if str(entry.get("ticker", "")).upper() == ticker.upper():
            return int(entry["cik_str"]), str(entry["title"])
    raise ValueError(f"Ticker {ticker!r} not found in SEC company tickers")


def latest_10k(cik: int, settings: Settings) -> dict:
    """Metadata for the most recent 10-K filing of a CIK."""
    resp = requests.get(
        SUBMISSIONS_URL.format(cik=cik), headers=_headers(settings), timeout=30
    )
    resp.raise_for_status()
    recent = resp.json().get("filings", {}).get("recent", {})
    for form, filed, accession, doc in zip(
        recent.get("form", []),
        recent.get("filingDate", []),
        recent.get("accessionNumber", []),
        recent.get("primaryDocument", []),
    ):
        if form == "10-K":
            return {
                "form": form,
                "filing_date": filed,
                "accession": accession,
                "url": ARCHIVE_URL.format(
                    cik=cik, accession=accession.replace("-", ""), doc=doc
                ),
            }
    raise ValueError(f"No 10-K found for CIK {cik}")


def download_filing_text(url: str, settings: Settings) -> str:
    """Download a filing document and strip it to plain text."""
    resp = requests.get(url, headers=_headers(settings), timeout=60)
    resp.raise_for_status()
    text = re.sub(r"<[^>]+>", " ", resp.text)
    return re.sub(r"\s+", " ", text).strip()

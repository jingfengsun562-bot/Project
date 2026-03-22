"""
scraper.py — Pure Python web fetching (zero AI tokens).

Fetches text from:
  A) Investment bank URLs listed in Investment_Outlook_url.txt
     - Scrapes HTML text from each page
     - Detects PDF links and extracts text with pdfplumber
  B) Financial news RSS feeds (Reuters, CNBC, Bloomberg)
"""

import io
import re
import warnings
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import pdfplumber
import requests
from bs4 import BeautifulSoup

# ── constants ────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 15          # seconds
MAX_CHARS_PER_SOURCE = 3000   # truncation limit per source
MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_RSS_ITEMS = 10

RSS_FEEDS = {
    "Reuters": "https://feeds.reuters.com/reuters/topNews",
    "CNBC": "https://search.cnbc.com/rs/search/combinedcombined/view.aspx?partnerId=wrss01&id=10000664",
    "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
}

# Known subdomain prefixes to strip when deriving source names
_SUBDOMAIN_STRIP = {"www", "am", "us", "research-center", "feeds"}

# Manual overrides for well-known domains
_DOMAIN_NAMES = {
    "blackrock": "BlackRock",
    "jpmorgan": "JPMorgan",
    "morganstanley": "Morgan Stanley",
    "goldmansachs": "Goldman Sachs",
    "gs": "Goldman Sachs",
    "amundi": "Amundi",
    "hsbc": "HSBC",
    "kbmeter": "KBMeter",
    "eatonvance": "Eaton Vance",
    "generali": "Generali",
    "reuters": "Reuters",
    "cnbc": "CNBC",
    "bloomberg": "Bloomberg",
    "blackrock": "BlackRock",
    "msci": "MSCI",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe_get(url: str, stream: bool = False) -> requests.Response | None:
    """GET with timeout and error handling. Returns None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=stream)
        resp.raise_for_status()
        return resp
    except Exception as exc:
        print(f"  [WARN] Could not fetch {url}: {exc}")
        return None


def _extract_html_text(html: str) -> str:
    """Extract readable paragraph text from HTML, stripping boilerplate."""
    soup = BeautifulSoup(html, "lxml")
    # Remove noise tags
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript", "iframe"]):
        tag.decompose()
    paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
    return " ".join(p for p in paragraphs if len(p) > 40)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    text_parts = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages[:15]:  # first 15 pages max
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
        except Exception as exc:
            print(f"  [WARN] PDF extraction error: {exc}")
    return "\n".join(text_parts)


def _find_pdf_links(html: str, base_url: str) -> list[str]:
    """Return absolute URLs of PDF links found on a page."""
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf") or "pdf" in href.lower():
            full = urljoin(base_url, href)
            links.append(full)
    return links[:3]  # at most 3 PDFs per page


def _source_name_from_url(url: str) -> str:
    """Derive a human-readable source name from a URL."""
    parts = urlparse(url).netloc.split(".")
    # Drop known subdomain prefixes to find the brand name
    for part in parts:
        if part.lower() not in _SUBDOMAIN_STRIP and part.lower() != "com":
            key = part.lower()
            return _DOMAIN_NAMES.get(key, part.capitalize())
    return parts[0].capitalize()


# ── public API ────────────────────────────────────────────────────────────────

def fetch_investment_bank_urls(url_file: str) -> list[dict]:
    """
    Fetch and extract text from the URLs listed in url_file.
    Returns list of {source_name, url, content} dicts.
    """
    with open(url_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip().startswith("http")]

    sources = []
    for url in urls:
        source_name = _source_name_from_url(url)
        print(f"  Fetching {source_name} ({url[:60]}...)")

        resp = _safe_get(url)
        if resp is None:
            continue

        html = resp.text
        html_text = _extract_html_text(html)

        # Try PDF links if HTML content is thin
        pdf_text = ""
        if len(html_text) < 500:
            pdf_links = _find_pdf_links(html, url)
            for pdf_url in pdf_links:
                print(f"    ->Downloading PDF: {pdf_url[:70]}...")
                pdf_resp = _safe_get(pdf_url, stream=True)
                if pdf_resp is None:
                    continue
                # Check size before downloading
                content_length = int(pdf_resp.headers.get("Content-Length", 0))
                if content_length > MAX_PDF_BYTES:
                    print(f"    [SKIP] PDF too large ({content_length // 1024} KB)")
                    continue
                pdf_bytes = pdf_resp.content
                extracted = _extract_pdf_text(pdf_bytes)
                if extracted:
                    pdf_text += extracted
                    break  # use first successful PDF

        # Prefer PDF text if richer
        content = pdf_text if len(pdf_text) > len(html_text) else html_text
        content = content[:MAX_CHARS_PER_SOURCE]

        if content.strip():
            sources.append({"source_name": source_name, "url": url, "content": content})
        else:
            print(f"  [WARN] No usable content from {source_name}")

    return sources


def fetch_rss_news() -> dict | None:
    """
    Fetch headlines + summaries from financial news RSS feeds.
    Returns a single {source_name, url, content} dict combining all feeds,
    or None if all feeds fail.
    """
    all_items = []

    for feed_name, feed_url in RSS_FEEDS.items():
        print(f"  Fetching RSS: {feed_name}")
        resp = _safe_get(feed_url)
        if resp is None:
            continue
        try:
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:MAX_RSS_ITEMS]
            for item in items:
                title = (item.findtext("title") or "").strip()
                desc = (item.findtext("description") or "").strip()
                # Strip HTML tags from description
                desc = re.sub(r"<[^>]+>", "", desc)
                if title:
                    all_items.append(f"{feed_name}: {title}. {desc}")
        except Exception as exc:
            print(f"  [WARN] RSS parse error for {feed_name}: {exc}")

    if not all_items:
        return None

    content = "\n".join(all_items)[:MAX_CHARS_PER_SOURCE]
    return {
        "source_name": "Financial News (RSS)",
        "url": "RSS feeds: Reuters, CNBC, Bloomberg",
        "content": content,
    }


def fetch_all(url_file: str) -> list[dict]:
    """
    Fetch all sources: investment bank pages + news RSS feeds.
    Returns combined list of source dicts.
    """
    print("\n[Scraper] Fetching investment bank sources...")
    sources = fetch_investment_bank_urls(url_file)
    print(f"  -> {len(sources)} sources fetched")

    print("\n[Scraper] Fetching news RSS feeds...")
    news = fetch_rss_news()
    if news:
        sources.append(news)
        print("  ->RSS news added")
    else:
        print("  [WARN] No RSS news fetched")

    return sources

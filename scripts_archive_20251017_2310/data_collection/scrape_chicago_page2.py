#!/usr/bin/env python3
"""Collect 5 more articles from Chicago Law Review page 2."""

import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://lawreview.uchicago.edu"
RATE_LIMIT_DELAY = 2.5

# Output directories
BASE_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing")
HTML_DIR = BASE_DIR / "data" / "raw_html"
PDF_DIR = BASE_DIR / "data" / "raw_pdf"
LOG_DIR = BASE_DIR / "data" / "collection_logs" / "chicago_law_review"

# Articles from page 2
ARTICLES = [
    "venue-transfers-administrative-litigation-and-neglected-percolation-argument",
    "specter-circuit-split-isaacson-bankshot-and-ss-1983",
    "who-are-they-judge-scope-absolute-immunity-applied-parole-psychologists",
    "snow-rain-and-theft-limits-us-postal-service-liability-under-federal-tort-claims-act",
    "ai-business-judgment-rule-heightened-information-duty",
]

session = requests.Session()
session.headers.update(
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Research Bot"}
)


def log_message(message):
    print(message)
    with open(LOG_DIR / "collection.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


successful = 0
failed = []

for i, slug in enumerate(ARTICLES):
    log_message(f"\n[{i + 1}/5] Processing: {slug}")

    # Fetch HTML
    article_url = f"{BASE_URL}/online-archive/{slug}"
    html_path = HTML_DIR / f"chicago_law_review_{slug}.html"

    try:
        time.sleep(RATE_LIMIT_DELAY)
        response = session.get(article_url, timeout=30)
        response.raise_for_status()
        html_path.write_text(response.text, encoding="utf-8")
        log_message(f"  Saved HTML ({len(response.text)} chars)")

        # Extract PDF URL
        soup = BeautifulSoup(response.text, "html.parser")
        pdf_url = None
        for link in soup.find_all("a", href=True):
            if ".pdf" in link["href"].lower():
                pdf_url = urljoin(BASE_URL, link["href"])
                break

        if not pdf_url:
            log_message("  WARNING: No PDF link found")
            failed.append((slug, "No PDF"))
            continue

        # Fetch PDF
        pdf_path = PDF_DIR / f"chicago_law_review_{slug}.pdf"
        time.sleep(RATE_LIMIT_DELAY)
        pdf_response = session.get(pdf_url, timeout=60)
        pdf_response.raise_for_status()
        pdf_path.write_bytes(pdf_response.content)
        log_message(f"  Saved PDF ({len(pdf_response.content)} bytes)")

        successful += 1
        log_message(f"  SUCCESS: Pair {successful} complete")

    except Exception as e:
        log_message(f"  ERROR: {e}")
        failed.append((slug, str(e)))

log_message(f"\n\nPage 2 collection complete: {successful}/5 successful")
if failed:
    log_message(f"Failed: {failed}")

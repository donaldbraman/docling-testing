#!/usr/bin/env python3
"""
Scrape HTML-PDF pairs from University of Chicago Law Review Online Archive.

Usage:
    python scrape_chicago_law_review.py
"""

import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://lawreview.uchicago.edu"
ONLINE_ARCHIVE_URL = f"{BASE_URL}/online-archive"
RATE_LIMIT_DELAY = 2.5  # seconds between requests

# Output directories
BASE_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing")
HTML_DIR = BASE_DIR / "data" / "raw_html"
PDF_DIR = BASE_DIR / "data" / "raw_pdf"
LOG_DIR = BASE_DIR / "data" / "collection_logs" / "chicago_law_review"

# Ensure directories exist
HTML_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Session for connection pooling
session = requests.Session()
session.headers.update(
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Research Bot"}
)


def log_message(message):
    """Print and log a message."""
    print(message)
    with open(LOG_DIR / "collection.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


def get_article_slugs(max_articles=15):
    """Get article slugs from the online archive."""
    log_message(f"Fetching article list from {ONLINE_ARCHIVE_URL}")

    try:
        response = session.get(ONLINE_ARCHIVE_URL, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find article links
        article_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/online-archive/" in href and href != "/online-archive":
                # Extract slug
                slug = href.split("/online-archive/")[-1].strip("/")
                if slug and slug not in article_links:
                    article_links.append(slug)

        log_message(f"Found {len(article_links)} article slugs")
        return article_links[:max_articles]

    except Exception as e:
        log_message(f"ERROR fetching article list: {e}")
        return []


def fetch_html(article_slug):
    """Fetch and save article HTML."""
    article_url = f"{BASE_URL}/online-archive/{article_slug}"
    html_path = HTML_DIR / f"chicago_law_review_{article_slug}.html"

    log_message(f"Fetching HTML: {article_url}")

    try:
        response = session.get(article_url, timeout=30)
        response.raise_for_status()

        # Check content length (should be substantial)
        content_length = len(response.text)
        if content_length < 5000:
            log_message(f"  WARNING: HTML only {content_length} chars - may be too short")

        # Save HTML
        html_path.write_text(response.text, encoding="utf-8")
        log_message(f"  Saved HTML ({content_length} chars) to {html_path.name}")

        return response.text, True

    except Exception as e:
        log_message(f"  ERROR fetching HTML: {e}")
        return None, False


def extract_pdf_url(html_content, article_slug):
    """Extract PDF URL from article HTML."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Look for PDF download links
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if ".pdf" in href.lower():
            # Make absolute URL
            if href.startswith("http"):
                return href
            else:
                return urljoin(BASE_URL, href)

    log_message(f"  WARNING: No PDF link found for {article_slug}")
    return None


def fetch_pdf(pdf_url, article_slug):
    """Fetch and save article PDF."""
    pdf_path = PDF_DIR / f"chicago_law_review_{article_slug}.pdf"

    log_message(f"Fetching PDF: {pdf_url}")

    try:
        response = session.get(pdf_url, timeout=60)
        response.raise_for_status()

        # Verify it's actually a PDF
        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower():
            log_message(f"  WARNING: Content-Type is {content_type}, not PDF")

        # Check size
        content_length = len(response.content)
        if content_length < 50000:  # Less than 50KB is suspicious
            log_message(f"  WARNING: PDF only {content_length} bytes - may be invalid")

        # Save PDF
        pdf_path.write_bytes(response.content)
        log_message(f"  Saved PDF ({content_length} bytes) to {pdf_path.name}")

        return True

    except Exception as e:
        log_message(f"  ERROR fetching PDF: {e}")
        return False


def collect_articles(target_count=15):
    """Main collection function."""
    log_message("=" * 60)
    log_message("Starting Chicago Law Review collection")
    log_message(f"Target: {target_count} HTML-PDF pairs")
    log_message("=" * 60)

    # Get article slugs
    article_slugs = get_article_slugs(max_articles=target_count + 5)  # Get extras in case some fail

    if not article_slugs:
        log_message("ERROR: No articles found. Exiting.")
        return

    successful_pairs = 0
    failed_articles = []

    for i, slug in enumerate(article_slugs):
        if successful_pairs >= target_count:
            log_message(f"\nReached target of {target_count} pairs. Stopping.")
            break

        log_message(f"\n[{i + 1}/{len(article_slugs)}] Processing: {slug}")

        # Fetch HTML
        time.sleep(RATE_LIMIT_DELAY)
        html_content, html_success = fetch_html(slug)

        if not html_success:
            failed_articles.append((slug, "HTML fetch failed"))
            continue

        # Extract PDF URL
        pdf_url = extract_pdf_url(html_content, slug)

        if not pdf_url:
            failed_articles.append((slug, "No PDF link found"))
            continue

        # Fetch PDF
        time.sleep(RATE_LIMIT_DELAY)
        pdf_success = fetch_pdf(pdf_url, slug)

        if not pdf_success:
            failed_articles.append((slug, "PDF fetch failed"))
            continue

        # Success!
        successful_pairs += 1
        log_message(f"  SUCCESS: Pair {successful_pairs} complete")

    # Summary
    log_message("\n" + "=" * 60)
    log_message("COLLECTION COMPLETE")
    log_message("=" * 60)
    log_message(f"Successful pairs: {successful_pairs}/{target_count}")
    log_message(f"Failed articles: {len(failed_articles)}")

    if failed_articles:
        log_message("\nFailed articles:")
        for slug, reason in failed_articles:
            log_message(f"  - {slug}: {reason}")

    # Save summary to progress.txt
    with open(LOG_DIR / "progress.txt", "w") as f:
        f.write("University of Chicago Law Review - Collection Progress\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Collection Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Target: {target_count} HTML-PDF pairs\n")
        f.write(f"Successful: {successful_pairs}\n")
        f.write(f"Failed: {len(failed_articles)}\n\n")

        f.write("Strategy Used:\n")
        f.write("- Source: UCLR Online Archive (https://lawreview.uchicago.edu/online-archive)\n")
        f.write("- Method: Direct scraping of article pages\n")
        f.write("- Content: Online essays and case notes with full HTML text\n")
        f.write(f"- Rate limiting: {RATE_LIMIT_DELAY}s between requests\n\n")

        if successful_pairs > 0:
            f.write("Successful Articles:\n")
            for i, slug in enumerate(article_slugs[:successful_pairs]):
                if slug not in [s for s, _ in failed_articles]:
                    f.write(f"{i + 1}. {slug}\n")

        if failed_articles:
            f.write("\nFailed Articles:\n")
            for slug, reason in failed_articles:
                f.write(f"- {slug}: {reason}\n")

    log_message(f"\nProgress report saved to {LOG_DIR / 'progress.txt'}")


if __name__ == "__main__":
    try:
        collect_articles(target_count=15)
    except KeyboardInterrupt:
        log_message("\n\nCollection interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_message(f"\n\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Indiana Law Journal HTML-PDF Pair Collection Script
Collects article pairs from Digital Repository @ Maurer Law
"""

import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://www.repository.law.indiana.edu"
JOURNAL_URL = f"{BASE_URL}/ilj/"
OUTPUT_DIR_HTML = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_html")
OUTPUT_DIR_PDF = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_pdf")
LOG_DIR = Path(
    "/Users/donaldbraman/Documents/GitHub/docling-testing/data/collection_logs/indiana_law_journal"
)
TARGET_PAIRS = 10
RATE_LIMIT_DELAY = 3  # seconds between requests

# Create output directories
OUTPUT_DIR_HTML.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR_PDF.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# User agent for polite scraping - needs to look like a browser for institutional repos
HEADERS_HTML = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

HEADERS_PDF = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
}

# Create session for cookie persistence
session = requests.Session()


def log_message(message):
    """Log message to console and file"""
    print(message)
    with open(LOG_DIR / "progress.txt", "a") as f:
        f.write(f"{message}\n")


def slugify(text):
    """Convert text to filename-safe slug"""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text[:100]  # limit length


def get_articles_from_journal_home():
    """Extract article URLs from journal homepage"""
    log_message(f"  Fetching journal homepage: {JOURNAL_URL}")
    time.sleep(RATE_LIMIT_DELAY)

    try:
        response = session.get(JOURNAL_URL, headers=HEADERS_HTML, timeout=15)
        if response.status_code != 200:
            log_message(f"  ERROR: Got status {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        articles = []

        # Find all article links - BePress pattern
        # They can be full URLs or relative paths
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Match pattern: /ilj/vol{X}/iss{Y}/{Z} or full URL
            if re.search(r"/ilj/vol\d+/iss\d+/\d+$", href):
                full_url = href if href.startswith("http") else BASE_URL + href

                if full_url not in articles:
                    articles.append(full_url)

        log_message(f"  Found {len(articles)} article URLs")
        return articles

    except Exception as e:
        log_message(f"  ERROR: {str(e)}")
        return []


def extract_pdf_url_from_article_page(article_url):
    """Extract PDF download URL from article page"""
    time.sleep(RATE_LIMIT_DELAY)

    try:
        response = session.get(article_url, headers=HEADERS_HTML, timeout=15, allow_redirects=True)
        if response.status_code != 200:
            log_message(f"    ERROR: Article page returned {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Method 1: Find PDF link in meta tag (BePress standard)
        meta_pdf = soup.find("meta", {"name": "bepress_citation_pdf_url"})
        if meta_pdf and meta_pdf.get("content"):
            return meta_pdf["content"]

        # Method 2: Find download button
        download_link = soup.find("a", {"id": "pdf"})
        if download_link and download_link.get("href"):
            pdf_url = download_link["href"]
            if not pdf_url.startswith("http"):
                pdf_url = BASE_URL + pdf_url
            return pdf_url

        # Method 3: Search for viewcontent.cgi link
        for link in soup.find_all("a", href=True):
            if "viewcontent.cgi" in link["href"]:
                pdf_url = link["href"]
                if not pdf_url.startswith("http"):
                    pdf_url = BASE_URL + pdf_url
                return pdf_url

        log_message("    WARNING: Could not find PDF URL")
        return None

    except Exception as e:
        log_message(f"    ERROR: {str(e)}")
        return None


def download_file(url, output_path, referer=None):
    """Download file from URL to output path"""
    time.sleep(RATE_LIMIT_DELAY)

    try:
        # Determine file type and use appropriate headers
        is_pdf = url.endswith(".pdf") or "viewcontent.cgi" in url
        headers = HEADERS_PDF.copy() if is_pdf else HEADERS_HTML.copy()

        # Add referer for PDF downloads (important for institutional repos)
        if referer:
            headers["Referer"] = referer

        response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
        if response.status_code != 200:
            log_message(f"    ERROR: Download returned {response.status_code}")
            return False

        with open(output_path, "wb") as f:
            f.write(response.content)

        # Verify file size
        file_size = output_path.stat().st_size
        if file_size < 5000:  # Less than 5KB is suspicious
            log_message(f"    WARNING: File size is only {file_size} bytes")
            return False

        return True

    except Exception as e:
        log_message(f"    ERROR: {str(e)}")
        return False


def get_article_title(article_url):
    """Get article title for filename"""
    try:
        response = session.get(article_url, headers=HEADERS_HTML, timeout=15, allow_redirects=True)
        soup = BeautifulSoup(response.text, "html.parser")

        # Try to find title
        title_elem = soup.find("h1")
        if title_elem:
            return slugify(title_elem.get_text(strip=True))

        # Fallback to URL pattern
        match = re.search(r"/vol(\d+)/iss(\d+)/(\d+)", article_url)
        if match:
            return f"vol{match.group(1)}_iss{match.group(2)}_art{match.group(3)}"

        return "unknown_article"
    except:
        # Last resort fallback
        match = re.search(r"/vol(\d+)/iss(\d+)/(\d+)", article_url)
        if match:
            return f"vol{match.group(1)}_iss{match.group(2)}_art{match.group(3)}"
        return "unknown_article"


def main():
    log_message("=" * 70)
    log_message("Indiana Law Journal HTML-PDF Pair Collection")
    log_message(f"Target: {TARGET_PAIRS} complete pairs")
    log_message(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message("=" * 70)

    collected_pairs = []

    # Strategy: Get articles from journal homepage (current issue)
    log_message("\nFetching articles from journal homepage...")
    articles = get_articles_from_journal_home()

    if not articles:
        log_message("ERROR: No articles found on homepage!")
        return 1

    log_message(f"Found {len(articles)} total articles on homepage")
    log_message(f"Will process first {min(len(articles), TARGET_PAIRS + 5)} articles")

    # Process articles
    for article_url in articles[: TARGET_PAIRS + 5]:  # Try a few extra in case some fail
        if len(collected_pairs) >= TARGET_PAIRS:
            break

        log_message(f"\nArticle: {article_url}")

        # Get article title for filename
        article_slug = get_article_title(article_url)
        log_message(f"  Slug: {article_slug}")

        # Extract PDF URL
        pdf_url = extract_pdf_url_from_article_page(article_url)
        if not pdf_url:
            log_message("  SKIP: No PDF found")
            continue

        log_message(f"  PDF: {pdf_url}")

        # Define output paths
        html_path = OUTPUT_DIR_HTML / f"indiana_law_journal_{article_slug}.html"
        pdf_path = OUTPUT_DIR_PDF / f"indiana_law_journal_{article_slug}.pdf"

        # Download HTML
        log_message("  Downloading HTML...")
        if not download_file(article_url, html_path):
            log_message("  SKIP: HTML download failed")
            continue

        # Download PDF (use article URL as referer)
        log_message("  Downloading PDF...")
        if not download_file(pdf_url, pdf_path, referer=article_url):
            log_message("  SKIP: PDF download failed")
            html_path.unlink()  # Clean up HTML if PDF failed
            continue

        # Success!
        collected_pairs.append(
            {
                "article_url": article_url,
                "pdf_url": pdf_url,
                "html_file": html_path.name,
                "pdf_file": pdf_path.name,
            }
        )

        log_message(f"  SUCCESS! ({len(collected_pairs)}/{TARGET_PAIRS})")

    # Final report
    log_message("\n" + "=" * 70)
    log_message("COLLECTION COMPLETE")
    log_message(f"Pairs collected: {len(collected_pairs)}/{TARGET_PAIRS}")
    log_message(f"End Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message("=" * 70)

    # Write summary file
    with open(LOG_DIR / "collected_articles.txt", "w") as f:
        for pair in collected_pairs:
            f.write(f"Article: {pair['article_url']}\n")
            f.write(f"PDF: {pair['pdf_url']}\n")
            f.write(f"HTML File: {pair['html_file']}\n")
            f.write(f"PDF File: {pair['pdf_file']}\n")
            f.write("-" * 70 + "\n")

    if len(collected_pairs) >= TARGET_PAIRS:
        log_message("\nSUCCESS: Target reached!")
        return 0
    else:
        log_message(f"\nPARTIAL: Only collected {len(collected_pairs)} of {TARGET_PAIRS}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Virginia Law Review HTML-PDF Pair Collection Script

Collects matched HTML-PDF pairs from Virginia Law Review for ML training corpus.
Target: Minimum 10 complete pairs, stretch goal 15.

Author: Claude Code
Date: 2025-10-16
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://virginialawreview.org"
DATA_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data")
RAW_HTML_DIR = DATA_DIR / "raw_html"
RAW_PDF_DIR = DATA_DIR / "raw_pdf"
LOG_DIR = DATA_DIR / "collection_logs" / "virginia_law_review"

RATE_LIMIT_DELAY = 2.5  # seconds between requests
REQUEST_TIMEOUT = 30  # seconds
MIN_WORD_COUNT = 1000  # minimum words for article preview page (full text is in PDF)
TARGET_PAIRS = 10
STRETCH_GOAL = 15

# User agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def ensure_directories():
    """Create necessary directories if they don't exist."""
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def create_slug(url: str) -> str:
    """Extract slug from article URL."""
    # Extract last part of URL path
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    return parts[-1] if parts else "unknown"


def fetch_with_retry(url: str, is_pdf: bool = False) -> requests.Response | None:
    """Fetch URL with retry logic and rate limiting."""
    time.sleep(RATE_LIMIT_DELAY)

    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=is_pdf)

        if response.status_code == 200:
            return response
        elif response.status_code == 429:
            print("  ⚠️  Rate limited (429). Waiting 1 hour...")
            time.sleep(3600)
            return None
        elif response.status_code == 403:
            print("  ⚠️  Access forbidden (403). Skipping...")
            return None
        else:
            print(f"  ⚠️  HTTP {response.status_code} for {url}")
            return None

    except requests.exceptions.Timeout:
        print(f"  ⚠️  Timeout fetching {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️  Error fetching {url}: {e}")
        return None


def extract_pdf_url(html_content: str, article_url: str) -> str | None:
    """Extract PDF download URL from article HTML."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Look for PDF link patterns
    # Pattern 1: Link with "Download PDF" text
    pdf_link = soup.find("a", string=re.compile(r"Download\s+PDF", re.I))
    if pdf_link and pdf_link.get("href"):
        return urljoin(article_url, pdf_link["href"])

    # Pattern 2: Link containing .pdf in href
    pdf_link = soup.find("a", href=re.compile(r"\.pdf$", re.I))
    if pdf_link:
        return urljoin(article_url, pdf_link["href"])

    # Pattern 3: Look in wp-content/uploads directory
    all_links = soup.find_all("a", href=True)
    for link in all_links:
        href = link["href"]
        if "wp-content/uploads" in href and href.endswith(".pdf"):
            return urljoin(article_url, href)

    return None


def estimate_word_count(html_content: str) -> int:
    """Estimate word count from HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style", "nav", "header", "footer"]):
        script.decompose()

    # Get text and count words
    text = soup.get_text()
    words = text.split()
    return len(words)


def download_article_pair(article_url: str, slug: str) -> tuple[bool, str]:
    """
    Download HTML-PDF pair for a single article.

    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"\n📄 Processing: {slug}")
    print(f"   URL: {article_url}")

    # Fetch HTML
    html_response = fetch_with_retry(article_url)
    if not html_response:
        return False, "Failed to fetch HTML"

    html_content = html_response.text

    # Check word count
    word_count = estimate_word_count(html_content)
    print(f"   Word count: {word_count:,}")

    if word_count < MIN_WORD_COUNT:
        return False, f"Insufficient word count ({word_count} < {MIN_WORD_COUNT})"

    # Extract PDF URL
    pdf_url = extract_pdf_url(html_content, article_url)
    if not pdf_url:
        return False, "No PDF link found"

    print(f"   PDF URL: {pdf_url}")

    # Verify PDF accessibility
    pdf_response = fetch_with_retry(pdf_url, is_pdf=True)
    if not pdf_response:
        return False, "Failed to fetch PDF"

    # Check PDF size
    pdf_size = len(pdf_response.content)
    print(f"   PDF size: {pdf_size:,} bytes")

    if pdf_size < 10000:  # Less than 10KB is suspicious
        return False, f"PDF too small ({pdf_size} bytes)"

    # Save HTML
    html_filename = f"virginia_law_review_{slug}.html"
    html_path = RAW_HTML_DIR / html_filename
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"   ✓ Saved HTML: {html_filename}")

    # Save PDF
    pdf_filename = f"virginia_law_review_{slug}.pdf"
    pdf_path = RAW_PDF_DIR / pdf_filename
    with open(pdf_path, "wb") as f:
        f.write(pdf_response.content)
    print(f"   ✓ Saved PDF: {pdf_filename}")

    return True, f"Success (HTML: {word_count} words, PDF: {pdf_size} bytes)"


def main():
    """Main collection workflow."""
    print("=" * 80)
    print("Virginia Law Review HTML-PDF Collection")
    print("=" * 80)

    ensure_directories()

    # Article URLs from sitemap (most recent first)
    # Note: Already downloaded: the-unenumerated-power, solitary-confinement-human-dignity-and-the-eighth-amendment
    article_urls = [
        "https://virginialawreview.org/articles/free-speech-breathing-space-and-liability-insurance/",
        "https://virginialawreview.org/articles/deterring-unenforceable-terms/",
        "https://virginialawreview.org/articles/the-association-game-applying-noscitur-a-sociis-and-ejusdem-generis/",
        "https://virginialawreview.org/articles/neo-brandeis-goes-to-washington-a-provisional-assessment-of-the-biden-administrations-antitrust-record/",
        "https://virginialawreview.org/articles/fourth-amendment-trespass-and-internet-search-history/",
        "https://virginialawreview.org/articles/political-mootness/",
        "https://virginialawreview.org/articles/the-right-thing-in-the-wrong-place-unstable-dicta-and-aesthetics-gradual-incursion-into-the-traditional-police-power-justifications/",
        "https://virginialawreview.org/articles/antitrusts-interdependence-paradox/",
        "https://virginialawreview.org/articles/free-speech-as-white-privilege-racialization-suppression-and-the-palestine-exception/",
        "https://virginialawreview.org/articles/abortions-new-criminalization-a-history-and-tradition-right-to-health-care-access-after-dobbs/",
        "https://virginialawreview.org/articles/the-radical-fair-housing-act/",
        "https://virginialawreview.org/articles/an-alternative-to-constraining-judges-with-constitutional-theories-the-internal-goods-approach/",
        "https://virginialawreview.org/articles/the-limits-of-evidence-based-policymaking/",
        "https://virginialawreview.org/articles/plea-bargaining-in-the-shadow-of-big-data/",
        "https://virginialawreview.org/articles/why-do-we-regulate-insider-trading/",
        "https://virginialawreview.org/articles/tax-as-far-less-than-perfect-substitutes/",
        "https://virginialawreview.org/articles/the-new-election-contestation/",
        "https://virginialawreview.org/articles/the-modern-day-literacy-test-felon-disenfranchisement-and-race-discrimination/",
        "https://virginialawreview.org/articles/trade-secret-damages/",
        "https://virginialawreview.org/articles/how-administrative-law-can-save-the-separation-of-powers/",
        "https://virginialawreview.org/articles/reframing-rights-in-social-enterprise/",
        "https://virginialawreview.org/articles/judging-agency-action/",
        "https://virginialawreview.org/articles/the-corporate-contract-in-changing-times-is-the-law-keeping-up/",
        "https://virginialawreview.org/articles/property-beyond-exclusion/",
        "https://virginialawreview.org/articles/the-law-of-lawless-courts/",
    ]

    results = {
        "successful": [],
        "failed": [],
        "total_attempted": 0,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    print(f"\nTarget: {TARGET_PAIRS} pairs (stretch: {STRETCH_GOAL})")
    print(f"Attempting up to {len(article_urls)} articles")
    print(f"Rate limit: {RATE_LIMIT_DELAY}s between requests\n")

    for url in article_urls:
        # Check if we've reached stretch goal
        if len(results["successful"]) >= STRETCH_GOAL:
            print(f"\n🎉 Reached stretch goal of {STRETCH_GOAL} pairs!")
            break

        slug = create_slug(url)
        results["total_attempted"] += 1

        success, message = download_article_pair(url, slug)

        if success:
            results["successful"].append({"url": url, "slug": slug, "message": message})
            print(f"   ✅ Success! ({len(results['successful'])}/{TARGET_PAIRS})")
        else:
            results["failed"].append({"url": url, "slug": slug, "message": message})
            print(f"   ❌ Failed: {message}")

    # Generate report
    print("\n" + "=" * 80)
    print("COLLECTION SUMMARY")
    print("=" * 80)
    print(f"Successful pairs: {len(results['successful'])}")
    print(f"Failed attempts: {len(results['failed'])}")
    print(f"Total attempted: {results['total_attempted']}")
    print(f"Success rate: {len(results['successful']) / results['total_attempted'] * 100:.1f}%")

    if len(results["successful"]) >= TARGET_PAIRS:
        print(f"\n✅ TARGET ACHIEVED: {len(results['successful'])}/{TARGET_PAIRS} pairs")
    else:
        print(f"\n⚠️  TARGET MISSED: {len(results['successful'])}/{TARGET_PAIRS} pairs")

    # Save detailed report
    report_path = LOG_DIR / "progress.txt"
    with open(report_path, "w") as f:
        f.write("Virginia Law Review Collection Progress Report\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {results['timestamp']}\n")
        f.write(f"Target: {TARGET_PAIRS} pairs (stretch: {STRETCH_GOAL})\n\n")

        f.write("SUMMARY\n")
        f.write("-------\n")
        f.write(f"Successful: {len(results['successful'])}\n")
        f.write(f"Failed: {len(results['failed'])}\n")
        f.write(f"Total attempted: {results['total_attempted']}\n")
        f.write(
            f"Success rate: {len(results['successful']) / results['total_attempted'] * 100:.1f}%\n\n"
        )

        f.write("SUCCESSFUL PAIRS\n")
        f.write("----------------\n")
        for i, item in enumerate(results["successful"], 1):
            f.write(f"{i}. {item['slug']}\n")
            f.write(f"   URL: {item['url']}\n")
            f.write(f"   Status: {item['message']}\n\n")

        if results["failed"]:
            f.write("\nFAILED ATTEMPTS\n")
            f.write("---------------\n")
            for i, item in enumerate(results["failed"], 1):
                f.write(f"{i}. {item['slug']}\n")
                f.write(f"   URL: {item['url']}\n")
                f.write(f"   Reason: {item['message']}\n\n")

    print(f"\n📝 Report saved: {report_path}")

    # Save JSON results
    json_path = LOG_DIR / "results.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"📊 JSON results: {json_path}")

    return len(results["successful"]) >= TARGET_PAIRS


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

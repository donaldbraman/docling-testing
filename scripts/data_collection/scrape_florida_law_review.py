#!/usr/bin/env python3
"""
Scrape Florida Law Review articles from scholarship.law.ufl.edu

Collects HTML-PDF pairs for machine learning training.
Target: Minimum 10 complete pairs, stretch goal 15.

Usage:
    python scripts/data_collection/scrape_florida_law_review.py
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://scholarship.law.ufl.edu"
DATA_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data")
HTML_DIR = DATA_DIR / "raw_html"
PDF_DIR = DATA_DIR / "raw_pdf"
LOG_DIR = DATA_DIR / "collection_logs" / "florida_law_review"
DELAY = 2.5  # seconds between requests
MAX_RETRIES = 3

# Article list: (volume, issue, article_num, title_slug)
ARTICLES = [
    # Volume 77, Issue 2 (2025)
    (77, 2, 1, "chilling-effects-dobbs"),
    (77, 2, 2, "future-antitrust-populism"),
    (77, 2, 3, "big-cost-small-farms"),
    (77, 2, 4, "originalist-case-insular-cases"),
    (77, 2, 5, "katz-imperfect-circle"),
    (77, 2, 6, "tribal-courts-general-jurisdiction"),
    # Volume 77, Issue 1 (2025)
    (77, 1, 1, "artificial-intelligence-privacy"),
    (77, 1, 2, "expressive-discrimination-universities"),
    (77, 1, 3, "transunion-vermont-agency-statutory-damages"),
    (77, 1, 4, "going-en-banc"),
    (77, 1, 5, "clayton-act-cipher"),
    # Volume 76, Issue 6 (2024)
    (76, 6, 1, "combatting-extremism"),
    (76, 6, 2, "originalism-election-law"),
    (76, 6, 3, "power-electorate-state-constitutions"),
    (76, 6, 4, "maximum-convergence-voting"),
    (76, 6, 5, "voting-rights-materiality"),
]


def create_slug(title):
    """Create a safe filename slug from title."""
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug[:80]  # Limit length


def fetch_with_retry(url, timeout=30):
    """Fetch URL with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                print("  Rate limited (429), waiting 1 hour...")
                time.sleep(3600)
            else:
                print(f"  HTTP {response.status_code}, attempt {attempt + 1}/{MAX_RETRIES}")
        except requests.RequestException as e:
            print(f"  Error: {e}, attempt {attempt + 1}/{MAX_RETRIES}")

        if attempt < MAX_RETRIES - 1:
            time.sleep(DELAY * (attempt + 1))

    return None


def extract_pdf_url(html_content, html_url):
    """Extract PDF download URL from article HTML page."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Look for PDF download link
    # Pattern: href="/cgi/viewcontent.cgi?article=XXXX&context=flr"
    pdf_links = soup.find_all(
        "a", href=re.compile(r"/cgi/viewcontent\.cgi\?article=\d+&context=flr")
    )

    if pdf_links:
        pdf_path = pdf_links[0]["href"]
        return urljoin(BASE_URL, pdf_path)

    # Alternative: look for download link
    for link in soup.find_all("a", href=True):
        if "download" in link.get("class", []) or "pdf" in link["href"].lower():
            return urljoin(html_url, link["href"])

    return None


def download_article_pair(vol, issue, article_num, slug):
    """Download HTML and PDF for a single article."""
    html_url = f"{BASE_URL}/flr/vol{vol}/iss{issue}/{article_num}/"
    filename_base = f"florida_law_review_vol{vol}_iss{issue}_art{article_num}_{slug}"

    print(f"\n[{vol}.{issue}.{article_num}] {slug}")

    # Download HTML
    html_path = HTML_DIR / f"{filename_base}.html"
    if html_path.exists():
        print(f"  HTML already exists: {html_path.name}")
        html_content = html_path.read_text()
    else:
        print(f"  Fetching HTML: {html_url}")
        response = fetch_with_retry(html_url)
        if not response:
            print("  FAILED to fetch HTML")
            return False

        html_content = response.text
        html_path.write_text(html_content)
        print(f"  Saved HTML: {html_path.name} ({len(html_content)} bytes)")

    time.sleep(DELAY)

    # Extract PDF URL
    pdf_url = extract_pdf_url(html_content, html_url)
    if not pdf_url:
        print("  FAILED to find PDF URL in HTML")
        return False

    # Download PDF
    pdf_path = PDF_DIR / f"{filename_base}.pdf"
    if pdf_path.exists():
        print(f"  PDF already exists: {pdf_path.name}")
    else:
        print(f"  Fetching PDF: {pdf_url}")
        response = fetch_with_retry(pdf_url)
        if not response:
            print("  FAILED to fetch PDF")
            return False

        pdf_path.write_bytes(response.content)
        print(f"  Saved PDF: {pdf_path.name} ({len(response.content)} bytes)")

    # Verify PDF
    pdf_size = pdf_path.stat().st_size
    if pdf_size < 10000:  # Less than 10 KB is suspicious
        print(f"  WARNING: PDF size is only {pdf_size} bytes")
        return False

    print(f"  SUCCESS: {filename_base}")
    return True


def main():
    """Main collection script."""
    print("=" * 70)
    print("Florida Law Review Collection")
    print("=" * 70)
    print(f"Target: {len(ARTICLES)} articles")
    print(f"HTML directory: {HTML_DIR}")
    print(f"PDF directory: {PDF_DIR}")
    print(f"Log directory: {LOG_DIR}")

    # Ensure directories exist
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Collect articles
    results = []
    successful = 0
    failed = 0

    for vol, issue, article_num, slug in ARTICLES:
        success = download_article_pair(vol, issue, article_num, slug)

        results.append(
            {
                "volume": vol,
                "issue": issue,
                "article": article_num,
                "slug": slug,
                "success": success,
            }
        )

        if success:
            successful += 1
        else:
            failed += 1

        # Rate limiting
        time.sleep(DELAY)

    # Generate report
    print("\n" + "=" * 70)
    print("COLLECTION SUMMARY")
    print("=" * 70)
    print(f"Successful: {successful}/{len(ARTICLES)}")
    print(f"Failed: {failed}/{len(ARTICLES)}")

    # Save progress report
    report_path = LOG_DIR / "progress.txt"
    with open(report_path, "w") as f:
        f.write("Florida Law Review Collection Progress\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Target: {len(ARTICLES)} articles\n")
        f.write(f"Successful: {successful}\n")
        f.write(f"Failed: {failed}\n\n")

        f.write("Successful Downloads:\n")
        for r in results:
            if r["success"]:
                f.write(
                    f"  ✓ Vol {r['volume']}, Issue {r['issue']}, Article {r['article']}: {r['slug']}\n"
                )

        if failed > 0:
            f.write("\nFailed Downloads:\n")
            for r in results:
                if not r["success"]:
                    f.write(
                        f"  ✗ Vol {r['volume']}, Issue {r['issue']}, Article {r['article']}: {r['slug']}\n"
                    )

    print(f"\nProgress report saved: {report_path}")

    # Save JSON metadata
    metadata_path = LOG_DIR / "collection_metadata.json"
    metadata = {
        "journal": "Florida Law Review",
        "base_url": BASE_URL,
        "collection_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_articles": len(ARTICLES),
        "successful": successful,
        "failed": failed,
        "articles": results,
    }

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved: {metadata_path}")

    if successful >= 10:
        print(f"\n✓ SUCCESS: Collected {successful} article pairs (target: 10)")
    else:
        print(f"\n✗ INCOMPLETE: Only {successful} article pairs (target: 10)")


if __name__ == "__main__":
    main()

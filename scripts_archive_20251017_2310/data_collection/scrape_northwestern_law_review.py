#!/usr/bin/env python3
"""
Northwestern Law Review Article Collector
Collects HTML-PDF pairs from scholarlycommons.law.northwestern.edu

Usage:
    python scrape_northwestern_law_review.py
"""

import time
from pathlib import Path

import requests

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent
HTML_DIR = BASE_DIR / "data" / "raw_html"
PDF_DIR = BASE_DIR / "data" / "raw_pdf"
LOG_DIR = BASE_DIR / "data" / "collection_logs" / "northwestern_law_review"

RATE_LIMIT_DELAY = 10  # 10 seconds per robots.txt
MAX_ARTICLES = 15  # Target 15 articles

# Article list: (title_slug, article_url, pdf_id, volume, issue, article_num)
ARTICLES = [
    # Vol 119, Issue 6
    (
        "renaissance_private_law",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss6/1",
        "1597",
        119,
        6,
        1,
    ),
    (
        "against_monetary_primacy",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss6/2",
        "1598",
        119,
        6,
        2,
    ),
    (
        "climate_exceptionalism_court",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss6/3",
        "1599",
        119,
        6,
        3,
    ),
    # Vol 119, Issue 5
    (
        "racial_discrimination_returns",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss5/1",
        "1593",
        119,
        5,
        1,
    ),
    (
        "market_value_partisan_balance",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss5/2",
        "1594",
        119,
        5,
        2,
    ),
    (
        "constraining_executive_branch",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss5/3",
        "1595",
        119,
        5,
        3,
    ),
    (
        "statutes_special_interests",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss5/4",
        "1596",
        119,
        5,
        4,
    ),
    # Vol 119, Issue 4
    (
        "forgotten_fundamental_right_movement",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss4/1",
        "1587",
        119,
        4,
        1,
    ),
    (
        "louboutin_lawfare",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss4/2",
        "1588",
        119,
        4,
        2,
    ),
    (
        "healing_power_antitrust",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss4/3",
        "1589",
        119,
        4,
        3,
    ),
    (
        "ais_dream_electric_boards",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss4/4",
        "1590",
        119,
        4,
        4,
    ),
    # Vol 119, Issue 3
    (
        "accommodating_incompetency_immigration",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss3/1",
        "1581",
        119,
        3,
        1,
    ),
    (
        "taxations_limits",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss3/2",
        "1582",
        119,
        3,
        2,
    ),
    (
        "legally_magic_words",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss3/3",
        "1583",
        119,
        3,
        3,
    ),
    (
        "sec_entrepreneurial_enforcer",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss3/4",
        "1584",
        119,
        3,
        4,
    ),
    # Vol 119, Issue 2
    (
        "obstructing_precedent",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss2/1",
        "1576",
        119,
        2,
        1,
    ),
    (
        "majority_rules",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss2/2",
        "1577",
        119,
        2,
        2,
    ),
    (
        "false_choice_digital_regulation",
        "https://scholarlycommons.law.northwestern.edu/nulr/vol119/iss2/3",
        "1578",
        119,
        2,
        3,
    ),
]


def verify_url(url: str) -> tuple[bool, int]:
    """Verify URL is accessible. Returns (success, status_code)."""
    try:
        response = requests.head(url, timeout=30, allow_redirects=True)
        return response.status_code == 200, response.status_code
    except Exception as e:
        print(f"    Error verifying {url}: {e}")
        return False, 0


def download_html(url: str, output_path: Path) -> bool:
    """Download HTML article page."""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            output_path.write_text(response.text, encoding="utf-8")
            print(f"    ✓ HTML saved: {output_path.name}")
            return True
        else:
            print(f"    ✗ HTML download failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ✗ HTML download error: {e}")
        return False


def download_pdf(pdf_id: str, output_path: Path) -> bool:
    """Download PDF using BePress viewcontent.cgi URL."""
    pdf_url = f"https://scholarlycommons.law.northwestern.edu/cgi/viewcontent.cgi?article={pdf_id}&context=nulr"

    try:
        response = requests.get(pdf_url, timeout=60, stream=True)
        if response.status_code == 200:
            output_path.write_bytes(response.content)
            file_size = output_path.stat().st_size
            print(f"    ✓ PDF saved: {output_path.name} ({file_size:,} bytes)")
            return True
        else:
            print(f"    ✗ PDF download failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ✗ PDF download error: {e}")
        return False


def collect_article(slug: str, html_url: str, pdf_id: str, vol: int, iss: int, art: int) -> bool:
    """Collect a single HTML-PDF pair."""
    print(f"\n[{slug}]")
    print(f"  Vol {vol}, Issue {iss}, Article {art}")
    print(f"  HTML: {html_url}")

    # Define output paths
    html_path = HTML_DIR / f"northwestern_law_review_{slug}.html"
    pdf_path = PDF_DIR / f"northwestern_law_review_{slug}.pdf"

    # Check if already downloaded
    if html_path.exists() and pdf_path.exists():
        print("  ✓ Already downloaded, skipping")
        return True

    # Verify HTML accessibility
    print("  Verifying HTML...")
    html_ok, html_status = verify_url(html_url)
    if not html_ok:
        print(f"  ✗ HTML not accessible (status: {html_status})")
        return False

    # Verify PDF accessibility
    pdf_url = f"https://scholarlycommons.law.northwestern.edu/cgi/viewcontent.cgi?article={pdf_id}&context=nulr"
    print("  Verifying PDF...")
    pdf_ok, pdf_status = verify_url(pdf_url)
    if not pdf_ok:
        print(f"  ✗ PDF not accessible (status: {pdf_status})")
        return False

    print("  ✓ Both HTML and PDF accessible")

    # Download HTML
    if not html_path.exists():
        print("  Downloading HTML...")
        if not download_html(html_url, html_path):
            return False
    else:
        print("  ✓ HTML already exists")

    time.sleep(2)  # Brief delay between requests

    # Download PDF
    if not pdf_path.exists():
        print("  Downloading PDF...")
        if not download_pdf(pdf_id, pdf_path):
            return False
    else:
        print("  ✓ PDF already exists")

    print("  ✓ SUCCESS: Complete pair downloaded")
    return True


def main():
    """Main collection routine."""
    print("=" * 70)
    print("Northwestern Law Review Article Collection")
    print("=" * 70)
    print(f"Target: {MAX_ARTICLES} articles")
    print(f"Rate limit: {RATE_LIMIT_DELAY} seconds between articles")
    print(f"HTML output: {HTML_DIR}")
    print(f"PDF output: {PDF_DIR}")
    print("=" * 70)

    # Ensure directories exist
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failure_count = 0

    for i, (slug, html_url, pdf_id, vol, iss, art) in enumerate(ARTICLES[:MAX_ARTICLES], 1):
        print(f"\n{'=' * 70}")
        print(f"Article {i}/{min(MAX_ARTICLES, len(ARTICLES))}")

        success = collect_article(slug, html_url, pdf_id, vol, iss, art)

        if success:
            success_count += 1
        else:
            failure_count += 1

        # Rate limiting (robots.txt specifies 10 seconds)
        if i < min(MAX_ARTICLES, len(ARTICLES)):
            print(f"\n  Waiting {RATE_LIMIT_DELAY} seconds (rate limit)...")
            time.sleep(RATE_LIMIT_DELAY)

    # Summary
    print("\n" + "=" * 70)
    print("COLLECTION SUMMARY")
    print("=" * 70)
    print(f"Successfully collected: {success_count}/{MAX_ARTICLES} pairs")
    print(f"Failed: {failure_count}/{MAX_ARTICLES}")
    print(f"\nHTML files: {HTML_DIR}")
    print(f"PDF files: {PDF_DIR}")

    # Write progress report
    progress_file = LOG_DIR / "progress.txt"
    with open(progress_file, "w") as f:
        f.write("Northwestern Law Review Collection Progress\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Target: {MAX_ARTICLES} articles\n")
        f.write(f"Success: {success_count}/{MAX_ARTICLES}\n")
        f.write(f"Failed: {failure_count}/{MAX_ARTICLES}\n\n")
        f.write("Articles collected:\n")
        for slug, _, _, vol, iss, art in ARTICLES[:success_count]:
            f.write(f"  - Vol {vol}, Iss {iss}, Art {art}: {slug}\n")

    print(f"\nProgress report: {progress_file}")
    print("=" * 70)

    return success_count >= 10  # Success if we got at least 10 pairs


if __name__ == "__main__":
    import sys

    sys.exit(0 if main() else 1)

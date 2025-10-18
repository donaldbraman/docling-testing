#!/usr/bin/env python3
"""
Collect HTML-PDF pairs from California Law Review (UC Berkeley).

This script downloads article HTML pages and corresponding PDFs from
californialawreview.org for ML training corpus.

Target: Minimum 10 complete HTML-PDF pairs
Rate limiting: 2-3 second delay between requests
"""

import sys
import time
from pathlib import Path

import requests

# Configuration
BASE_URL = "https://www.californialawreview.org"
DATA_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data")
HTML_DIR = DATA_DIR / "raw_html"
PDF_DIR = DATA_DIR / "raw_pdf"
LOG_DIR = DATA_DIR / "collection_logs" / "california_law_review"

# Ensure directories exist
HTML_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Article list: (slug, pdf_path)
# All articles from California Law Review Volume 113 (2025)
ARTICLES = [
    ("judiciary-ada", "/s/7-Mahajan-FINAL-yksw.pdf"),
    ("morgan-democracy", "/s/6-BPearce-FINAL.pdf"),
    ("new-conservationism", "/s/5-Jacewicz-FINAL.pdf"),
    ("social-justice-conflicts", "/s/4-Havasy-FINAL.pdf"),
    ("indeterminacy-separation", "/s/3-MaceyRichardson-FINAL.pdf"),
    ("amazon-trademark", "/s/2-FromerMMcKenna-FINAL.pdf"),
    ("affirmative-asylum", "/s/1-Sayed-FINAL.pdf"),
    ("loving-borders", "/s/11-Chacon-FINAL.pdf"),
    ("incoherence-colorblind-constitution", "/s/9-Robinson-FINAL.pdf"),
    ("voter-pay", "/s/4-Albright-FINAL.pdf"),
]

# Request headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def download_html(slug: str) -> tuple[bool, str]:
    """Download article HTML page."""
    url = f"{BASE_URL}/print/{slug}"
    html_path = HTML_DIR / f"california_law_review_{slug}.html"

    print(f"Downloading HTML: {slug}...", end=" ", flush=True)

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)

        if response.status_code == 200:
            html_path.write_text(response.text, encoding="utf-8")
            print(f"✓ ({len(response.text)} bytes)")
            return True, url
        else:
            print(f"✗ (HTTP {response.status_code})")
            return False, f"HTTP {response.status_code}"

    except Exception as e:
        print(f"✗ ({str(e)})")
        return False, str(e)


def download_pdf(slug: str, pdf_path: str) -> tuple[bool, str]:
    """Download article PDF."""
    if not pdf_path:
        print("  PDF: No PDF path provided, skipping")
        return False, "No PDF path"

    url = f"{BASE_URL}{pdf_path}"
    local_path = PDF_DIR / f"california_law_review_{slug}.pdf"

    print("  PDF: Downloading...", end=" ", flush=True)

    try:
        response = requests.get(url, headers=HEADERS, timeout=30, stream=True)

        if response.status_code == 200:
            local_path.write_bytes(response.content)
            size_mb = len(response.content) / (1024 * 1024)
            print(f"✓ ({size_mb:.2f} MB)")
            return True, url
        else:
            print(f"✗ (HTTP {response.status_code})")
            return False, f"HTTP {response.status_code}"

    except Exception as e:
        print(f"✗ ({str(e)})")
        return False, str(e)


def main():
    """Main collection loop."""
    print("=" * 70)
    print("California Law Review HTML-PDF Collection")
    print("=" * 70)
    print(f"Target: {len(ARTICLES)} articles")
    print(f"HTML directory: {HTML_DIR}")
    print(f"PDF directory: {PDF_DIR}")
    print(f"Log directory: {LOG_DIR}")
    print("=" * 70)
    print()

    results = []
    successful_pairs = 0

    for i, (slug, pdf_path) in enumerate(ARTICLES, 1):
        print(f"\n[{i}/{len(ARTICLES)}] Article: {slug}")
        print("-" * 70)

        # Download HTML
        html_success, html_info = download_html(slug)
        time.sleep(2.5)  # Rate limiting: 2.5 seconds between requests

        # Download PDF
        pdf_success = False
        pdf_info = ""
        if html_success:
            pdf_success, pdf_info = download_pdf(slug, pdf_path)
            time.sleep(2.5)  # Rate limiting

        # Record results
        pair_complete = html_success and pdf_success
        if pair_complete:
            successful_pairs += 1
            status = "✓ COMPLETE"
        else:
            status = "✗ INCOMPLETE"

        results.append(
            {
                "slug": slug,
                "html_success": html_success,
                "pdf_success": pdf_success,
                "pair_complete": pair_complete,
                "html_info": html_info,
                "pdf_info": pdf_info,
            }
        )

        print(f"Status: {status} ({successful_pairs} pairs collected)")

    # Write progress report
    report_path = LOG_DIR / "progress.txt"
    with open(report_path, "w") as f:
        f.write("California Law Review Collection Progress\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Collection Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Target: {len(ARTICLES)} articles\n")
        f.write(f"Successful pairs: {successful_pairs}\n")
        f.write(f"Success rate: {successful_pairs / len(ARTICLES) * 100:.1f}%\n")
        f.write("\n" + "=" * 70 + "\n")
        f.write("Individual Results:\n")
        f.write("=" * 70 + "\n\n")

        for r in results:
            f.write(f"Article: {r['slug']}\n")
            f.write(f"  HTML: {'✓' if r['html_success'] else '✗'} {r['html_info']}\n")
            f.write(f"  PDF:  {'✓' if r['pdf_success'] else '✗'} {r['pdf_info']}\n")
            f.write(f"  Pair: {'✓ COMPLETE' if r['pair_complete'] else '✗ INCOMPLETE'}\n")
            f.write("\n")

    print("\n" + "=" * 70)
    print("COLLECTION SUMMARY")
    print("=" * 70)
    print(f"Successful pairs: {successful_pairs}/{len(ARTICLES)}")
    print(f"Success rate: {successful_pairs / len(ARTICLES) * 100:.1f}%")
    print(f"Report saved to: {report_path}")
    print("=" * 70)

    if successful_pairs >= 10:
        print("✓ SUCCESS: Minimum target of 10 pairs achieved!")
        return 0
    else:
        print(f"⚠ WARNING: Only {successful_pairs} pairs collected (target: 10)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

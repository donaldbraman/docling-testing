#!/usr/bin/env python3
"""
Collect HTML-PDF pairs from Penn Law Review (UPenn ScholarlyCommons)

Downloads article metadata pages (HTML) and corresponding PDFs from the
University of Pennsylvania Law School's ScholarlyCommons repository.
"""

import time
from pathlib import Path

import requests

# Configuration
BASE_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing")
HTML_DIR = BASE_DIR / "data/raw_html"
PDF_DIR = BASE_DIR / "data/raw_pdf"
LOG_DIR = BASE_DIR / "data/collection_logs/penn_law_review"

# Ensure directories exist
HTML_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiting: 2-3 seconds between requests
DELAY_SECONDS = 2.5

# Article list: (title_slug, article_url, pdf_url)
ARTICLES = [
    # Vol 173, Issue 6
    (
        "super_dicta",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss6/1",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9894&context=penn_law_review",
    ),
    (
        "unwritten_administrative_law",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss6/2",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9895&context=penn_law_review",
    ),
    (
        "policing_as_general_warrants",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss6/3",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9896&context=penn_law_review",
    ),
    # Vol 173, Issue 5
    (
        "ancillary_rights",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss5/1",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9889&context=penn_law_review",
    ),
    (
        "original_meaning_of_treaties",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss5/2",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9890&context=penn_law_review",
    ),
    (
        "default_procedures",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss5/3",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9891&context=penn_law_review",
    ),
    # Vol 173, Issue 4
    (
        "spirit",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss4/1",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9884&context=penn_law_review",
    ),
    (
        "prosecuting_families",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss4/2",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9885&context=penn_law_review",
    ),
    (
        "debt_tokens",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss4/3",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9886&context=penn_law_review",
    ),
    # Vol 173, Issue 3
    (
        "control_and_its_discontents",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss3/1",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9879&context=penn_law_review",
    ),
    (
        "lessons_in_climate_derisking",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss3/2",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9880&context=penn_law_review",
    ),
    (
        "realism_about_criminal_justice_localism",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss3/3",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9881&context=penn_law_review",
    ),
]


def download_file(url, output_path, file_type="HTML"):
    """Download a file with error handling and status checking."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Research Bot; +https://github.com/donaldbraman/docling-testing)"
        }
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            size_kb = len(response.content) / 1024
            print(f"  ✓ Downloaded {file_type}: {output_path.name} ({size_kb:.1f} KB)")
            return True
        elif response.status_code == 429:
            print(f"  ✗ Rate limited (429) for {file_type}: {url}")
            print("    Waiting 1 hour before retry...")
            return False
        elif response.status_code == 403:
            print(f"  ✗ Forbidden (403) for {file_type}: {url}")
            return False
        else:
            print(f"  ✗ HTTP {response.status_code} for {file_type}: {url}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error downloading {file_type}: {e}")
        return False


def main():
    """Main collection function."""
    print("=" * 70)
    print("Penn Law Review Collection")
    print("Source: UPenn ScholarlyCommons")
    print("=" * 70)
    print()

    success_count = 0
    failed_articles = []

    for i, (slug, html_url, pdf_url) in enumerate(ARTICLES, 1):
        print(f"[{i}/{len(ARTICLES)}] Processing: {slug}")

        html_path = HTML_DIR / f"penn_law_review_{slug}.html"
        pdf_path = PDF_DIR / f"penn_law_review_{slug}.pdf"

        # Download HTML
        html_success = download_file(html_url, html_path, "HTML")
        time.sleep(DELAY_SECONDS)

        # Download PDF
        pdf_success = download_file(pdf_url, pdf_path, "PDF")

        if html_success and pdf_success:
            success_count += 1
            print("  ✓ Complete pair saved")
        else:
            failed_articles.append(slug)
            print("  ✗ Failed to download complete pair")

        print()

        # Rate limiting between articles
        if i < len(ARTICLES):
            time.sleep(DELAY_SECONDS)

    # Summary
    print("=" * 70)
    print("Collection Summary")
    print("=" * 70)
    print(f"Total articles attempted: {len(ARTICLES)}")
    print(f"Successful pairs: {success_count}")
    print(f"Failed: {len(failed_articles)}")

    if failed_articles:
        print(f"\nFailed articles: {', '.join(failed_articles)}")

    # Write progress report
    progress_file = LOG_DIR / "progress.txt"
    with open(progress_file, "w") as f:
        f.write("Penn Law Review Collection Progress\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Collection Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("Source: UPenn ScholarlyCommons\n")
        f.write("Base URL: https://scholarship.law.upenn.edu/penn_law_review/\n\n")
        f.write(f"Total Attempted: {len(ARTICLES)}\n")
        f.write(f"Successful Pairs: {success_count}\n")
        f.write(f"Failed: {len(failed_articles)}\n\n")

        if failed_articles:
            f.write("Failed Articles:\n")
            for slug in failed_articles:
                f.write(f"  - {slug}\n")
            f.write("\n")

        f.write("Article List:\n")
        f.write("-" * 70 + "\n")
        for i, (slug, html_url, pdf_url) in enumerate(ARTICLES, 1):
            status = "✓" if slug not in failed_articles else "✗"
            f.write(f"{i}. [{status}] {slug}\n")
            f.write(f"   HTML: {html_url}\n")
            f.write(f"   PDF:  {pdf_url}\n\n")

    print(f"\nProgress report saved to: {progress_file}")
    print()

    if success_count >= 10:
        print("✓ SUCCESS: Collected minimum 10 complete HTML-PDF pairs!")
    else:
        print(f"✗ WARNING: Only collected {success_count} pairs (target: 10)")


if __name__ == "__main__":
    main()

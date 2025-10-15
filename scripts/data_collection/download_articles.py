#!/usr/bin/env python3
"""
Download HTML-PDF article pairs from law review repositories.
"""

import time
from pathlib import Path

import requests

# Output directories
HTML_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_html")
PDF_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_pdf")

# Create directories if they don't exist
HTML_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

# Cornell Law Review articles (Volume 105, 2020)
CORNELL_ARTICLES = [
    # Volume 105, Issue 6
    (
        "cornell_against_prosecutors",
        "https://scholarship.law.cornell.edu/clr/vol105/iss6/2",
        "https://scholarship.law.cornell.edu/cgi/viewcontent.cgi?article=4857&context=clr",
    ),
    (
        "cornell_equity_punishment",
        "https://scholarship.law.cornell.edu/clr/vol105/iss6/3",
        "https://scholarship.law.cornell.edu/cgi/viewcontent.cgi?article=4858&context=clr",
    ),
    (
        "cornell_frand_antitrust",
        "https://scholarship.law.cornell.edu/clr/vol105/iss6/4",
        "https://scholarship.law.cornell.edu/cgi/viewcontent.cgi?article=4859&context=clr",
    ),
    # Volume 105, Issue 5
    (
        "cornell_mdl_as_category",
        "https://scholarship.law.cornell.edu/clr/vol105/iss5/2",
        "https://scholarship.law.cornell.edu/cgi/viewcontent.cgi?article=4849&context=clr",
    ),
    (
        "cornell_antitrust_workers",
        "https://scholarship.law.cornell.edu/clr/vol105/iss5/3",
        "https://scholarship.law.cornell.edu/cgi/viewcontent.cgi?article=4851&context=clr",
    ),
    (
        "cornell_legitimate_interpretation",
        "https://scholarship.law.cornell.edu/clr/vol105/iss5/4",
        "https://scholarship.law.cornell.edu/cgi/viewcontent.cgi?article=4852&context=clr",
    ),
    (
        "cornell_chevron_construction",
        "https://scholarship.law.cornell.edu/clr/vol105/iss5/5",
        "https://scholarship.law.cornell.edu/cgi/viewcontent.cgi?article=4853&context=clr",
    ),
    # Volume 105, Issue 4
    (
        "cornell_scalia_legislative_history",
        "https://scholarship.law.cornell.edu/clr/vol105/iss4/2",
        "https://scholarship.law.cornell.edu/cgi/viewcontent.cgi?article=4843&context=clr",
    ),
    (
        "cornell_tort_private_administration",
        "https://scholarship.law.cornell.edu/clr/vol105/iss4/3",
        "https://scholarship.law.cornell.edu/cgi/viewcontent.cgi?article=4844&context=clr",
    ),
    (
        "cornell_corporate_privacy_proxy",
        "https://scholarship.law.cornell.edu/clr/vol105/iss4/4",
        "https://scholarship.law.cornell.edu/cgi/viewcontent.cgi?article=4845&context=clr",
    ),
]

# UPenn Law Review articles
UPENN_ARTICLES = [
    # Volume 173, Issue 7 (2024-2025)
    (
        "upenn_ninos_paradox",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss7/1",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9899&context=penn_law_review",
    ),
    (
        "upenn_past_is_changing",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss7/2",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9900&context=penn_law_review",
    ),
    (
        "upenn_originalist_framing",
        "https://scholarship.law.upenn.edu/penn_law_review/vol173/iss7/3",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9901&context=penn_law_review",
    ),
    # Volume 172, Issue 1 (2024)
    (
        "upenn_failure_to_appear",
        "https://scholarship.law.upenn.edu/penn_law_review/vol172/iss1/1",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9833&context=penn_law_review",
    ),
    (
        "upenn_private_enforcement",
        "https://scholarship.law.upenn.edu/penn_law_review/vol172/iss1/2",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9834&context=penn_law_review",
    ),
    (
        "upenn_cbdc_public_money",
        "https://scholarship.law.upenn.edu/penn_law_review/vol172/iss1/3",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9835&context=penn_law_review",
    ),
    (
        "upenn_corporate_tokenism",
        "https://scholarship.law.upenn.edu/penn_law_review/vol172/iss1/4",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9836&context=penn_law_review",
    ),
    # Volume 172, Issue 2 (2024)
    (
        "upenn_terms_of_service_fourth_amendment",
        "https://scholarship.law.upenn.edu/penn_law_review/vol172/iss2/1",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9838&context=penn_law_review",
    ),
    (
        "upenn_false_analogies_predatory_pricing",
        "https://scholarship.law.upenn.edu/penn_law_review/vol172/iss2/2",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9839&context=penn_law_review",
    ),
    (
        "upenn_conflicts_of_law_abortion",
        "https://scholarship.law.upenn.edu/penn_law_review/vol172/iss2/3",
        "https://scholarship.law.upenn.edu/cgi/viewcontent.cgi?article=9840&context=penn_law_review",
    ),
]


def download_file(url: str, output_path: Path, file_type: str) -> bool:
    """Download a file from a URL."""
    try:
        print(f"Downloading {file_type}: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        output_path.write_bytes(response.content)
        print(f"  Saved to: {output_path}")
        return True
    except Exception as e:
        print(f"  Error downloading {url}: {e}")
        return False


def download_article_pair(
    slug: str, html_url: str, pdf_url: str, delay: int = 4
) -> tuple[bool, bool]:
    """Download both HTML and PDF versions of an article."""
    print(f"\n{'=' * 60}")
    print(f"Article: {slug}")
    print(f"{'=' * 60}")

    # Download HTML
    html_path = HTML_DIR / f"{slug}.html"
    html_success = download_file(html_url, html_path, "HTML")

    # Wait between requests
    time.sleep(delay)

    # Download PDF
    pdf_path = PDF_DIR / f"{slug}.pdf"
    pdf_success = download_file(pdf_url, pdf_path, "PDF")

    # Wait before next article
    time.sleep(delay)

    return html_success, pdf_success


def main():
    """Download all articles."""
    print("Starting article downloads...")
    print(f"HTML output: {HTML_DIR}")
    print(f"PDF output: {PDF_DIR}")

    cornell_success = 0
    upenn_success = 0

    # Download Cornell articles
    print("\n" + "=" * 60)
    print("CORNELL LAW REVIEW")
    print("=" * 60)
    for slug, html_url, pdf_url in CORNELL_ARTICLES:
        html_ok, pdf_ok = download_article_pair(slug, html_url, pdf_url)
        if html_ok and pdf_ok:
            cornell_success += 1

    # Download UPenn articles
    print("\n" + "=" * 60)
    print("UNIVERSITY OF PENNSYLVANIA LAW REVIEW")
    print("=" * 60)
    for slug, html_url, pdf_url in UPENN_ARTICLES:
        html_ok, pdf_ok = download_article_pair(slug, html_url, pdf_url)
        if html_ok and pdf_ok:
            upenn_success += 1

    # Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Cornell Law Review: {cornell_success}/{len(CORNELL_ARTICLES)} pairs")
    print(f"UPenn Law Review: {upenn_success}/{len(UPENN_ARTICLES)} pairs")
    print(
        f"Total: {cornell_success + upenn_success}/{len(CORNELL_ARTICLES) + len(UPENN_ARTICLES)} pairs"
    )


if __name__ == "__main__":
    main()

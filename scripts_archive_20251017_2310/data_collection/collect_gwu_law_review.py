#!/usr/bin/env python3
"""
GWU Law Review Article Collection Script

Collects HTML-PDF pairs from George Washington University Law Review.
Based on site reconnaissance:
- Base URL: https://www.gwlr.org/
- PDF pattern: https://www.gwlr.org/wp-content/uploads/[year]/[month]/[citation].pdf
- Article URLs: https://www.gwlr.org/[article-slug]/
"""

import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://www.gwlr.org"
SITEMAP_URL = f"{BASE_URL}/post-sitemap.xml"
DELAY = 2.5  # seconds between requests
OUTPUT_HTML = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_html")
OUTPUT_PDF = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_pdf")
LOG_DIR = Path(
    "/Users/donaldbraman/Documents/GitHub/docling-testing/data/collection_logs/gwu_law_review"
)

# Ensure directories exist
OUTPUT_HTML.mkdir(parents=True, exist_ok=True)
OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_article_urls_from_sitemap(limit=20):
    """Get article URLs from curated list (sitemap blocked by ModSecurity)."""
    # Manually curated list from recent issues and administrative law section
    all_urls = [
        "https://www.gwlr.org/coercive-settlements/",
        "https://www.gwlr.org/criminal-investors/",
        "https://www.gwlr.org/non-universal-response-to-the-universal-injunction-problem/",
        "https://www.gwlr.org/chenery-ii-revisited/",
        "https://www.gwlr.org/chevron-bias/",
        "https://www.gwlr.org/contextual-interpretation-applying-civil-rights-to-healthcare-in-section-1557-of-the-affordable-care-act/",
        "https://www.gwlr.org/drawing-a-line-how-energy-law-can-provide-a-practical-boundary-for-the-rapidly-expanding-major-questions-doctrine/",
        "https://www.gwlr.org/good-cause-is-cause-for-concern/",
        "https://www.gwlr.org/how-chevron-deference-fits-into-article-iii/",
        "https://www.gwlr.org/lying-in-wait-how-a-court-should-handle-the-first-pretextual-for-cause-removal/",
        "https://www.gwlr.org/nondelegation-as-constitutional-symbolism/",
        "https://www.gwlr.org/optimal-ossification/",
        "https://www.gwlr.org/overseeing-agency-enforcement/",
        "https://www.gwlr.org/remand-and-dialogue-in-administrative-law/",
        "https://www.gwlr.org/the-ambiguity-fallacy/",
        "https://www.gwlr.org/the-american-nondelegation-doctrine/",
        "https://www.gwlr.org/the-future-of-deference/",
        "https://www.gwlr.org/the-ordinary-questions-doctrine/",
        "https://www.gwlr.org/the-power-to-vacate-a-rule/",
        "https://www.gwlr.org/what-the-new-major-questions-doctrine-is-not/",
        "https://www.gwlr.org/delegating-and-regulating-the-presidents-section-232-and-ieepa-trade-powers/",
        "https://www.gwlr.org/chartering-fintech-the-occs-newest-nonbank-proposal/",
        "https://www.gwlr.org/a-new-cfius-refining-the-committees-multimember-structure-with-for-cause-protections/",
        "https://www.gwlr.org/set-up-to-fail-national-labor-relations-board/",
        "https://www.gwlr.org/supporting-the-agency-designed-to-do-nothing-creating-a-regulatory-safety-net-for-the-fec/",
    ]

    print(f"Using curated list of {len(all_urls)} article URLs")
    return all_urls[:limit]


def extract_pdf_url(html_content, article_url):
    """Extract PDF URL from article HTML."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Look for PDF links in various possible locations
    pdf_patterns = [
        r'https://www\.gwlr\.org/wp-content/[^"\']*\.pdf',
        r'/wp-content/uploads/[^"\']*\.pdf',
    ]

    for pattern in pdf_patterns:
        matches = re.findall(pattern, html_content)
        if matches:
            pdf_url = matches[0]
            if not pdf_url.startswith("http"):
                pdf_url = urljoin(BASE_URL, pdf_url)
            return pdf_url

    # Try finding link with text containing "Full Article" or "PDF"
    for link in soup.find_all("a", href=True):
        if "pdf" in link["href"].lower() or "full article" in link.get_text().lower():
            return urljoin(BASE_URL, link["href"])

    return None


def get_word_count_estimate(html_content):
    """Estimate word count from HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    text = soup.get_text()
    words = text.split()
    return len(words)


def download_pair(article_url, index):
    """Download HTML and PDF for a single article."""
    print(f"\n[{index}] Processing: {article_url}")

    try:
        # Download HTML
        print("  Fetching HTML...")
        response = requests.get(article_url, timeout=15)
        response.raise_for_status()
        html_content = response.text

        # Check word count (must be substantial article)
        word_count = get_word_count_estimate(html_content)
        print(f"  Word count estimate: {word_count}")

        if word_count < 500:
            print("  ⚠ Skipping: Too short (likely not a full article)")
            return False

        # Extract PDF URL
        pdf_url = extract_pdf_url(html_content, article_url)
        if not pdf_url:
            print("  ⚠ No PDF link found, skipping")
            return False

        print(f"  Found PDF: {pdf_url}")

        # Verify PDF is accessible
        time.sleep(DELAY)
        pdf_response = requests.head(pdf_url, timeout=10, allow_redirects=True)
        if pdf_response.status_code != 200:
            print(f"  ⚠ PDF not accessible (status {pdf_response.status_code})")
            return False

        # Generate filename from article URL
        article_slug = article_url.rstrip("/").split("/")[-1]
        base_filename = f"gwu_law_review_{article_slug}"

        # Save HTML
        html_path = OUTPUT_HTML / f"{base_filename}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"  ✓ Saved HTML: {html_path.name}")

        # Download and save PDF
        time.sleep(DELAY)
        pdf_response = requests.get(pdf_url, timeout=30)
        pdf_response.raise_for_status()

        pdf_path = OUTPUT_PDF / f"{base_filename}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_response.content)
        print(f"  ✓ Saved PDF: {pdf_path.name} ({len(pdf_response.content)} bytes)")

        return True

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return False


def main():
    """Main collection routine."""
    print("=" * 70)
    print("GWU Law Review Collection Script")
    print("=" * 70)
    print("Target: 10-15 complete HTML-PDF pairs")
    print(f"Rate limit: {DELAY}s delay between requests")
    print()

    # Get article URLs from sitemap
    article_urls = get_article_urls_from_sitemap(limit=30)

    successful = 0
    failed = 0
    progress_log = []

    for i, url in enumerate(article_urls, 1):
        if successful >= 15:
            print("\n✓ Reached target of 15 pairs, stopping")
            break

        success = download_pair(url, i)

        if success:
            successful += 1
            progress_log.append(f"✓ {url}")
        else:
            failed += 1
            progress_log.append(f"✗ {url}")

        # Rate limiting
        if i < len(article_urls):
            time.sleep(DELAY)

    # Write progress report
    print("\n" + "=" * 70)
    print("Collection Complete")
    print("=" * 70)
    print(f"Successful pairs: {successful}")
    print(f"Failed attempts: {failed}")
    print(f"Success rate: {successful / (successful + failed) * 100:.1f}%")

    report_path = LOG_DIR / "progress.txt"
    with open(report_path, "w") as f:
        f.write("GWU Law Review Collection Report\n")
        f.write("=" * 70 + "\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Successful pairs: {successful}\n")
        f.write(f"Failed attempts: {failed}\n")
        f.write(f"Success rate: {successful / (successful + failed) * 100:.1f}%\n\n")
        f.write("Details:\n")
        for entry in progress_log:
            f.write(f"{entry}\n")

    print(f"\nProgress report saved to: {report_path}")

    if successful >= 10:
        print("\n✓ SUCCESS: Met minimum target of 10 pairs")
    else:
        print(f"\n⚠ WARNING: Only collected {successful} pairs (target: 10)")


if __name__ == "__main__":
    main()

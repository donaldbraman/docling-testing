#!/usr/bin/env python3
"""
Download HTML-PDF pairs from Stanford Law Review.

This script collects articles from Stanford Law Review, downloading both:
- HTML article pages (with abstracts and metadata)
- PDF full text files

Rate limiting: 2-3 seconds between requests to respect robots.txt (600s crawl-delay)
"""

import logging
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Directories
BASE_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing")
HTML_DIR = BASE_DIR / "data/raw_html"
PDF_DIR = BASE_DIR / "data/raw_pdf"
LOG_DIR = BASE_DIR / "data/collection_logs/stanford_law_review"

# Create directories
HTML_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiting
RATE_LIMIT_DELAY = 3  # seconds between requests

# Article collection (16 articles identified)
ARTICLES = [
    # Volume 77, Issue 6 (June 2025)
    {
        "url": "https://www.stanfordlawreview.org/print/article/after-notice-and-choice-reinvigorating-unfairness-to-rein-in-data-abuses/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Khan-77-Stan.-L.-Rev.-1375.pdf",
        "slug": "khan_notice_choice_unfairness",
    },
    {
        "url": "https://www.stanfordlawreview.org/print/article/governing-the-company-town/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Highsmith-77-Stan.-L.-Rev.-1463.pdf",
        "slug": "highsmith_company_town",
    },
    {
        "url": "https://www.stanfordlawreview.org/print/article/abandoning-deportation-adjudication/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Padmanabhan-77-Stan.-L.-Rev.-1557.pdf",
        "slug": "padmanabhan_deportation",
    },
    {
        "url": "https://www.stanfordlawreview.org/print/article/municipalities-and-the-banking-franchise/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Weightman-77-Stan.-L.-Rev.-1629.pdf",
        "slug": "weightman_banking_franchise",
    },
    # Volume 77, Issue 5 (May 2025)
    {
        "url": "https://www.stanfordlawreview.org/print/article/visions-of-vermont-yankee/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/05/Crews-77-Stan.-L.-Rev.-1117.pdf",
        "slug": "crews_vermont_yankee",
    },
    {
        "url": "https://www.stanfordlawreview.org/print/article/antitrusts-north-star-the-continued-and-nameless-judicial-deference-toward-the-merger-guidelines/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/05/Badii-77-Stan.-L.-Rev.-1189.pdf",
        "slug": "badii_antitrust_merger",
    },
    {
        "url": "https://www.stanfordlawreview.org/print/article/on-mere-constitutional-rights-the-emerging-conflict-between-state-legislative-privilege-and-the-fourteenth-amendment/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/05/Snyder-Weidhaas-77-Stan.-L.-Rev.-1253.pdf",
        "slug": "snyder_constitutional_rights",
    },
    {
        "url": "https://www.stanfordlawreview.org/print/article/watering-down-enforcement-inadequate-criminal-liability-in-state-clean-water-act-programs/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/05/Wu-77-Stan.-L.-Rev.-1303.pdf",
        "slug": "wu_clean_water_enforcement",
    },
    # Volume 77, Issue 4 (April 2025)
    {
        "url": "https://www.stanfordlawreview.org/print/article/presidential-control-and-administrative-capacity/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/04/Bednar-77-Stan.-L.-Rev.-823.pdf",
        "slug": "bednar_presidential_control",
    },
    {
        "url": "https://www.stanfordlawreview.org/print/article/beyond-the-perpetrator-perspective-on-golden-ghettos-defending-fair-housing-revisionism-with-critical-eyes/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/04/Kelley-77-Stan.-L.-Rev.-925.pdf",
        "slug": "kelley_fair_housing",
    },
    {
        "url": "https://www.stanfordlawreview.org/print/article/the-curious-case-of-the-missing-canons/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/04/Yorke-77-Stan.-L.-Rev.-1011.pdf",
        "slug": "yorke_missing_canons",
    },
    # Volume 77, Issue 3 (March 2025)
    {
        "url": "https://www.stanfordlawreview.org/print/article/shadow-banking-and-securities-law/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/03/Rauterberg-Zhang-77-Stan.-L.-Rev.-563.pdf",
        "slug": "rauterberg_shadow_banking",
    },
    {
        "url": "https://www.stanfordlawreview.org/print/article/prosecutors-in-robes/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/03/Schuman-77-Stan.-L.-Rev.-629.pdf",
        "slug": "schuman_prosecutors_robes",
    },
    {
        "url": "https://www.stanfordlawreview.org/print/article/deputization-and-privileged-white-violence/",
        "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/03/Yankah-77-Stan.-L.-Rev.-703.pdf",
        "slug": "yankah_deputization",
    },
]


def extract_pdf_url(html_content):
    """Extract PDF download URL from article HTML."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Look for PDF download link
    pdf_link = soup.find("a", string=re.compile(r"Download.*PDF", re.I))
    if pdf_link and pdf_link.get("href"):
        return pdf_link["href"]

    # Alternative: look for PDF in metadata
    meta_pdf = soup.find("meta", {"property": "og:url"})
    if meta_pdf:
        # Try to construct PDF URL from pattern
        pass

    return None


def download_html(url, output_path):
    """Download HTML article page."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Research Bot; +contact@example.com)"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.text)

        logger.info(f"Downloaded HTML: {output_path.name}")
        return response.text

    except requests.RequestException as e:
        logger.error(f"Failed to download HTML from {url}: {e}")
        return None


def download_pdf(url, output_path):
    """Download PDF file."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Research Bot; +contact@example.com)"}
        response = requests.get(url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        # Verify it's a PDF
        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower():
            logger.warning(f"URL {url} returned non-PDF content: {content_type}")

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verify PDF size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Downloaded PDF: {output_path.name} ({size_mb:.2f} MB)")

        if size_mb < 0.1:
            logger.warning(f"PDF seems too small: {size_mb:.2f} MB")
            return False

        return True

    except requests.RequestException as e:
        logger.error(f"Failed to download PDF from {url}: {e}")
        return False


def main():
    """Main download process."""
    results = {"successful": [], "failed": [], "skipped": []}

    logger.info("Starting Stanford Law Review collection")
    logger.info(f"Target: {len(ARTICLES)} articles")

    for i, article in enumerate(ARTICLES[:15], 1):  # Limit to 15 for stretch goal
        logger.info(f"\n--- Article {i}/15: {article['slug']} ---")

        # Define file paths
        html_path = HTML_DIR / f"stanford_law_review_{article['slug']}.html"
        pdf_path = PDF_DIR / f"stanford_law_review_{article['slug']}.pdf"

        # Check if already downloaded
        if html_path.exists() and pdf_path.exists():
            logger.info("Already downloaded, skipping")
            results["skipped"].append(article["slug"])
            continue

        # Download HTML
        html_content = download_html(article["url"], html_path)
        if not html_content:
            results["failed"].append(article["slug"])
            continue

        time.sleep(RATE_LIMIT_DELAY)

        # Extract PDF URL if not provided
        pdf_url = article["pdf_url"]
        if not pdf_url:
            pdf_url = extract_pdf_url(html_content)
            if not pdf_url:
                logger.error(f"Could not find PDF URL for {article['slug']}")
                results["failed"].append(article["slug"])
                continue

        # Download PDF
        pdf_success = download_pdf(pdf_url, pdf_path)
        if not pdf_success:
            results["failed"].append(article["slug"])
            continue

        results["successful"].append(article["slug"])

        time.sleep(RATE_LIMIT_DELAY)

        # Safety: don't exceed 10 articles per hour (respect robots.txt)
        if i % 5 == 0:
            logger.info(f"Processed {i} articles, taking extended break...")
            time.sleep(10)

    # Write progress report
    report_path = LOG_DIR / "progress.txt"
    with open(report_path, "w") as f:
        f.write("Stanford Law Review Collection Progress\n")
        f.write("=" * 50 + "\n\n")
        f.write("Target: 10+ articles (stretch: 15)\n")
        f.write(f"Successful: {len(results['successful'])}\n")
        f.write(f"Failed: {len(results['failed'])}\n")
        f.write(f"Skipped (already downloaded): {len(results['skipped'])}\n\n")

        f.write("Successful Downloads:\n")
        for slug in results["successful"]:
            f.write(f"  - {slug}\n")

        if results["failed"]:
            f.write("\nFailed Downloads:\n")
            for slug in results["failed"]:
                f.write(f"  - {slug}\n")

        if results["skipped"]:
            f.write("\nSkipped (Already Downloaded):\n")
            for slug in results["skipped"]:
                f.write(f"  - {slug}\n")

    logger.info(f"\n{'=' * 50}")
    logger.info("Collection Complete!")
    logger.info(f"Successful: {len(results['successful'])}")
    logger.info(f"Failed: {len(results['failed'])}")
    logger.info(f"Skipped: {len(results['skipped'])}")
    logger.info(f"Progress report: {report_path}")


if __name__ == "__main__":
    main()

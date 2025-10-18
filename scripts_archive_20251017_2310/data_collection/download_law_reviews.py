#!/usr/bin/env python3
"""
Download HTML-PDF article pairs from Harvard Law Review and Stanford Law Review.
Implements respectful web scraping with rate limiting and error handling.
"""

import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
BASE_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing")
HTML_DIR = BASE_DIR / "data" / "raw_html"
PDF_DIR = BASE_DIR / "data" / "raw_pdf"
DELAY_SECONDS = 4  # Respectful rate limiting

# User-Agent to identify ourselves
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Article lists
HARVARD_ARTICLES = [
    {
        "title": "Unwarranted Warrants? An Empirical Analysis of Judicial Review in Search and Seizure",
        "url": "https://harvardlawreview.org/print/vol-138/unwarranted-warrants-an-empirical-analysis-of-judicial-review-in-search-and-seizure/",
        "slug": "unwarranted-warrants",
    },
    {
        "title": "The Forgotten History of Prison Law",
        "url": "https://harvardlawreview.org/print/vol-138/the-forgotten-history-of-prison-law-judicial-oversight-of-detention-facilities-in-the-nations-early-years/",
        "slug": "forgotten-history-prison-law",
    },
    {
        "title": "Excited Delirium, Policing, and the Law of Evidence",
        "url": "https://harvardlawreview.org/print/vol-138/excited-delirium-policing-and-the-law-of-evidence/",
        "slug": "excited-delirium-policing",
    },
    {
        "title": "The Law and Lawlessness of U.S. Immigration Detention",
        "url": "https://harvardlawreview.org/print/vol-138/the-law-and-lawlessness-of-u-s-immigration-detention/",
        "slug": "immigration-detention",
    },
    {
        "title": "Waste, Property, and Useless Things",
        "url": "https://harvardlawreview.org/print/vol-138/waste-property-and-useless-things/",
        "slug": "waste-property-useless-things",
    },
    {
        "title": "Fighting Words at the Founding",
        "url": "https://harvardlawreview.org/print/vol-138/fighting-words-at-the-founding/",
        "slug": "fighting-words-founding",
    },
    {
        "title": "Background Principles and the General Law of Property",
        "url": "https://harvardlawreview.org/print/vol-138/background-principles-and-the-general-law-of-property/",
        "slug": "background-principles-property",
    },
    {
        "title": "Codify Gardner",
        "url": "https://harvardlawreview.org/print/vol-138/codify-gardner/",
        "slug": "codify-gardner",
    },
    {
        "title": "Making Equal Protection Protect",
        "url": "https://harvardlawreview.org/print/vol-138/making-equal-protection-protect/",
        "slug": "equal-protection-protect",
    },
    {
        "title": "Pragmatism or Textualism",
        "url": "https://harvardlawreview.org/print/vol-138/pragmatism-or-textualism/",
        "slug": "pragmatism-textualism",
    },
]

STANFORD_ARTICLES = [
    {
        "title": "After Notice and Choice: Reinvigorating Unfairness to Rein In Data Abuses",
        "url": "https://www.stanfordlawreview.org/print/article/after-notice-and-choice-reinvigorating-unfairness-to-rein-in-data-abuses/",
        "pdf": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Khan-77-Stan.-L.-Rev.-1375.pdf",
        "slug": "notice-choice-unfairness",
    },
    {
        "title": "Governing the Company Town",
        "url": "https://www.stanfordlawreview.org/print/article/governing-the-company-town/",
        "pdf": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Highsmith-77-Stan.-L.-Rev.-1463.pdf",
        "slug": "governing-company-town",
    },
    {
        "title": "Abandoning Deportation Adjudication",
        "url": "https://www.stanfordlawreview.org/print/article/abandoning-deportation-adjudication/",
        "pdf": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Padmanabhan-77-Stan.-L.-Rev.-1557.pdf",
        "slug": "abandoning-deportation-adjudication",
    },
    {
        "title": "The Invisible Driver of Policing",
        "url": "https://www.stanfordlawreview.org/print/article/the-invisible-driver-of-policing/",
        "pdf": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2024/01/Heydari-76-Stan.-L.-Rev.-1.pdf",
        "slug": "invisible-driver-policing",
    },
    {
        "title": "General Law and the Fourteenth Amendment",
        "url": "https://www.stanfordlawreview.org/print/article/general-law-and-the-fourteenth-amendment/",
        "pdf": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2024/06/Baude-et-al.-76-Stan.-L.-Rev.-1185.pdf",
        "slug": "general-law-fourteenth-amendment",
    },
    {
        "title": "Private Equity and the Corporatization of Health Care",
        "url": "https://www.stanfordlawreview.org/print/article/private-equity-and-the-corporatization-of-health-care/",
        "pdf": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2024/03/Fuse-Brown-Hall-76-Stan.-L.-Rev.-527.pdf",
        "slug": "private-equity-health-care",
    },
    {
        "title": "Uncommon Carriage",
        "url": "https://www.stanfordlawreview.org/print/article/uncommon-carriage/",
        "pdf": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2024/01/Reid-76-Stan.-L.-Rev.-89.pdf",
        "slug": "uncommon-carriage",
    },
    {
        "title": "War Reparations: The Case for Countermeasures",
        "url": "https://www.stanfordlawreview.org/print/article/war-reparations-the-case-for-countermeasures/",
        "pdf": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2024/05/Hathaway-et-al.-76-Stan.-L.-Rev.-971.pdf",
        "slug": "war-reparations-countermeasures",
    },
    {
        "title": "The Great Writ of Popular Sovereignty",
        "url": "https://www.stanfordlawreview.org/print/article/the-great-writ-of-popular-sovereignty/",
        "pdf": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/02/Kamin-77-Stan.-L.-Rev.-297.pdf",
        "slug": "great-writ-popular-sovereignty",
    },
    {
        "title": "Second Amendment Federalism",
        "url": "https://www.stanfordlawreview.org/print/article/second-amendment-federalism/",
        "pdf": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2024/04/Blocher-Miller-76-Stan.-L.-Rev.-745.pdf",
        "slug": "second-amendment-federalism",
    },
]


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def download_file(url: str, filepath: Path, file_type: str = "HTML") -> bool:
    """Download a file from URL to filepath."""
    try:
        logger.info(f"Downloading {file_type}: {url}")
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        filepath.write_bytes(response.content)
        logger.info(f"✓ Saved to: {filepath}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"✗ Failed to download {url}: {e}")
        return False


def extract_pdf_link_from_html(html_url: str) -> str:
    """Extract PDF download link from Harvard Law Review article page."""
    try:
        response = requests.get(html_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Strategy 1: Look for links with text "Download" (Harvard's pattern)
        for link in soup.find_all("a"):
            text = link.get_text(strip=True).lower()
            href = link.get("href", "")
            if text == "download" and ".pdf" in href.lower():
                if not href.startswith("http"):
                    href = urljoin(html_url, href)
                logger.info(f"Found PDF via 'Download' link: {href}")
                return href

        # Strategy 2: Look for any PDF link
        pdf_link = soup.find("a", href=re.compile(r"\.pdf$", re.I))
        if pdf_link:
            pdf_url = pdf_link.get("href")
            if not pdf_url.startswith("http"):
                pdf_url = urljoin(html_url, pdf_url)
            logger.info(f"Found PDF via direct link: {pdf_url}")
            return pdf_url

        # Strategy 3: Look for links containing 'download' or 'pdf' in text
        for link in soup.find_all("a"):
            href = link.get("href", "")
            text = link.get_text().lower()
            if ("pdf" in text or "download" in text) and ".pdf" in href.lower():
                if not href.startswith("http"):
                    href = urljoin(html_url, href)
                logger.info(f"Found PDF via text search: {href}")
                return href

        logger.warning(f"No PDF link found on page: {html_url}")
        return None

    except Exception as e:
        logger.error(f"Error extracting PDF link from {html_url}: {e}")
        return None


def download_harvard_article(article: dict) -> tuple[bool, bool]:
    """Download both HTML and PDF for a Harvard Law Review article."""
    journal_slug = "harvard-law-review"
    article_slug = article["slug"]

    # Download HTML
    html_path = HTML_DIR / f"{journal_slug}_{article_slug}.html"
    html_success = download_file(article["url"], html_path, "HTML")

    time.sleep(DELAY_SECONDS)

    # Extract and download PDF
    pdf_success = False
    if html_success:
        pdf_url = extract_pdf_link_from_html(article["url"])
        if pdf_url:
            pdf_path = PDF_DIR / f"{journal_slug}_{article_slug}.pdf"
            pdf_success = download_file(pdf_url, pdf_path, "PDF")
            time.sleep(DELAY_SECONDS)

    return html_success, pdf_success


def download_stanford_article(article: dict) -> tuple[bool, bool]:
    """Download both HTML and PDF for a Stanford Law Review article."""
    journal_slug = "stanford-law-review"
    article_slug = article["slug"]

    # Download HTML
    html_path = HTML_DIR / f"{journal_slug}_{article_slug}.html"
    html_success = download_file(article["url"], html_path, "HTML")

    time.sleep(DELAY_SECONDS)

    # Download PDF (direct link available)
    pdf_success = False
    if "pdf" in article and article["pdf"]:
        pdf_path = PDF_DIR / f"{journal_slug}_{article_slug}.pdf"
        pdf_success = download_file(article["pdf"], pdf_path, "PDF")
        time.sleep(DELAY_SECONDS)

    return html_success, pdf_success


def main():
    """Main download process."""
    logger.info("Starting Harvard Law Review and Stanford Law Review article downloads")
    logger.info(f"HTML directory: {HTML_DIR}")
    logger.info(f"PDF directory: {PDF_DIR}")

    # Ensure directories exist
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    # Track statistics
    stats = {
        "harvard": {"html": 0, "pdf": 0, "pairs": 0},
        "stanford": {"html": 0, "pdf": 0, "pairs": 0},
    }

    # Download Harvard articles
    logger.info("\n" + "=" * 80)
    logger.info("HARVARD LAW REVIEW")
    logger.info("=" * 80)

    for i, article in enumerate(HARVARD_ARTICLES, 1):
        logger.info(f"\n[{i}/{len(HARVARD_ARTICLES)}] {article['title']}")
        html_ok, pdf_ok = download_harvard_article(article)

        if html_ok:
            stats["harvard"]["html"] += 1
        if pdf_ok:
            stats["harvard"]["pdf"] += 1
        if html_ok and pdf_ok:
            stats["harvard"]["pairs"] += 1

    # Download Stanford articles
    logger.info("\n" + "=" * 80)
    logger.info("STANFORD LAW REVIEW")
    logger.info("=" * 80)

    for i, article in enumerate(STANFORD_ARTICLES, 1):
        logger.info(f"\n[{i}/{len(STANFORD_ARTICLES)}] {article['title']}")
        html_ok, pdf_ok = download_stanford_article(article)

        if html_ok:
            stats["stanford"]["html"] += 1
        if pdf_ok:
            stats["stanford"]["pdf"] += 1
        if html_ok and pdf_ok:
            stats["stanford"]["pairs"] += 1

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 80)
    logger.info("\nHarvard Law Review:")
    logger.info(f"  HTML files: {stats['harvard']['html']}")
    logger.info(f"  PDF files: {stats['harvard']['pdf']}")
    logger.info(f"  Complete pairs: {stats['harvard']['pairs']}")

    logger.info("\nStanford Law Review:")
    logger.info(f"  HTML files: {stats['stanford']['html']}")
    logger.info(f"  PDF files: {stats['stanford']['pdf']}")
    logger.info(f"  Complete pairs: {stats['stanford']['pairs']}")

    logger.info(f"\nTotal complete pairs: {stats['harvard']['pairs'] + stats['stanford']['pairs']}")
    logger.info("Target: 20 pairs (10 from each journal)")

    if stats["harvard"]["pairs"] + stats["stanford"]["pairs"] >= 20:
        logger.info("\n✓ Target achieved!")
    else:
        logger.info(
            f"\n⚠ Need {20 - stats['harvard']['pairs'] - stats['stanford']['pairs']} more pairs"
        )


if __name__ == "__main__":
    main()

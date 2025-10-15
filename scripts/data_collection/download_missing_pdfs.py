#!/usr/bin/env python3
"""
Download missing PDF files for Harvard Law Review articles using direct URLs.
"""

import logging
import time
from pathlib import Path

import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
BASE_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing")
PDF_DIR = BASE_DIR / "data" / "raw_pdf"
DELAY_SECONDS = 4

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/pdf",
}

# Harvard Law Review PDFs - using discovered citation patterns
HARVARD_PDFS = [
    {
        "slug": "unwarranted-warrants",
        "url": "https://harvardlawreview.org/wp-content/uploads/2025/05/138-Harv.-L.-Rev.-1959.pdf",
        "title": "Unwarranted Warrants",
    },
    {
        "slug": "forgotten-history-prison-law",
        "url": "https://harvardlawreview.org/wp-content/uploads/2025/04/138-Harv.-L.-Rev.-1763.pdf",
        "title": "The Forgotten History of Prison Law",
    },
    {
        "slug": "excited-delirium-policing",
        "url": "https://harvardlawreview.org/wp-content/uploads/2025/03/138-Harv.-L.-Rev.-1497.pdf",
        "title": "Excited Delirium, Policing, and the Law of Evidence",
    },
    {
        "slug": "immigration-detention",
        "url": "https://harvardlawreview.org/wp-content/uploads/2025/02/138-Harv.-L.-Rev.-1186.pdf",
        "title": "The Law and Lawlessness of U.S. Immigration Detention",
    },
    {
        "slug": "waste-property-useless-things",
        "url": "https://harvardlawreview.org/wp-content/uploads/2024/11/138-Harv.-L.-Rev.-416.pdf",
        "title": "Waste, Property, and Useless Things",
    },
    {
        "slug": "fighting-words-founding",
        "url": "https://harvardlawreview.org/wp-content/uploads/2024/11/138-Harv.-L.-Rev.-325.pdf",
        "title": "Fighting Words at the Founding",
    },
    {
        "slug": "background-principles-property",
        "url": "https://harvardlawreview.org/wp-content/uploads/2024/11/138-Harv.-L.-Rev.-654.pdf",
        "title": "Background Principles and the General Law of Property",
    },
    {
        "slug": "codify-gardner",
        "url": "https://harvardlawreview.org/wp-content/uploads/2025/02/138-Harv.-L.-Rev.-1363.pdf",
        "title": "Codify Gardner",
    },
    {
        "slug": "equal-protection-protect",
        "url": "https://harvardlawreview.org/wp-content/uploads/2025/01/138-Harv.-L.-Rev.-1161.pdf",
        "title": "Making Equal Protection Protect",
    },
    {
        "slug": "pragmatism-textualism",
        "url": "https://harvardlawreview.org/wp-content/uploads/2024/12/138-Harv.-L.-Rev.-717.pdf",
        "title": "Pragmatism or Textualism",
    },
]

# Stanford PDF with correct URL
STANFORD_PDFS = [
    {
        "slug": "second-amendment-federalism",
        "url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2024/03/Blocher-Miller-76-Stan.-L.-Rev.-745.pdf",
        "title": "Second Amendment Federalism",
    },
]


def download_pdf(url: str, slug: str, journal: str, title: str) -> bool:
    """Download a PDF file."""
    try:
        filepath = PDF_DIR / f"{journal}_{slug}.pdf"

        if filepath.exists():
            logger.info(f"✓ Already exists: {filepath.name}")
            return True

        logger.info(f"Downloading: {title}")
        logger.info(f"  URL: {url}")

        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        filepath.write_bytes(response.content)
        logger.info(f"✓ Saved to: {filepath.name}")
        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"✗ PDF not found (404): {url}")
        else:
            logger.error(f"✗ HTTP error {e.response.status_code}: {url}")
        return False
    except Exception as e:
        logger.error(f"✗ Failed to download: {e}")
        return False


def main():
    """Download all missing PDFs."""
    logger.info("Downloading missing PDF files")
    logger.info(f"PDF directory: {PDF_DIR}")

    PDF_DIR.mkdir(parents=True, exist_ok=True)

    stats = {"harvard": 0, "stanford": 0, "failed": 0}

    # Download Harvard PDFs
    logger.info("\n" + "=" * 80)
    logger.info("HARVARD LAW REVIEW PDFs")
    logger.info("=" * 80)

    for i, pdf in enumerate(HARVARD_PDFS, 1):
        logger.info(f"\n[{i}/{len(HARVARD_PDFS)}]")
        success = download_pdf(pdf["url"], pdf["slug"], "harvard-law-review", pdf["title"])
        if success:
            stats["harvard"] += 1
        else:
            stats["failed"] += 1
        time.sleep(DELAY_SECONDS)

    # Download Stanford PDFs
    logger.info("\n" + "=" * 80)
    logger.info("STANFORD LAW REVIEW PDFs")
    logger.info("=" * 80)

    for i, pdf in enumerate(STANFORD_PDFS, 1):
        logger.info(f"\n[{i}/{len(STANFORD_PDFS)}]")
        success = download_pdf(pdf["url"], pdf["slug"], "stanford-law-review", pdf["title"])
        if success:
            stats["stanford"] += 1
        else:
            stats["failed"] += 1
        time.sleep(DELAY_SECONDS)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Harvard PDFs downloaded: {stats['harvard']}/{len(HARVARD_PDFS)}")
    logger.info(f"Stanford PDFs downloaded: {stats['stanford']}/{len(STANFORD_PDFS)}")
    logger.info(f"Failed downloads: {stats['failed']}")
    logger.info(f"\nTotal PDFs: {stats['harvard'] + stats['stanford']}")


if __name__ == "__main__":
    main()

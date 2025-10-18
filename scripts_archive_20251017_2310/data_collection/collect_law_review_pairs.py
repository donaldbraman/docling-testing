#!/usr/bin/env python3
"""
Collect HTML-PDF pairs from Michigan Law Review and Virginia Law Review.
Uses institutional repositories with proper delays between requests.
"""

import re
import time
from pathlib import Path

import requests

# Base directories
DATA_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data")
HTML_DIR = DATA_DIR / "raw_html"
PDF_DIR = DATA_DIR / "raw_pdf"

# Create directories if they don't exist
HTML_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

# Request headers to appear as a regular browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def slugify(text):
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    return text[:100]  # Limit length


def download_file(url, filepath, delay=4):
    """Download a file from URL to filepath with delay."""
    try:
        print(f"  Downloading: {url}")
        response = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        print(f"  ✓ Saved to: {filepath}")
        time.sleep(delay)  # Respectful delay
        return True
    except Exception as e:
        print(f"  ✗ Error downloading {url}: {e}")
        return False


def download_michigan_article(article_info):
    """Download both HTML and PDF for a Michigan Law Review article."""
    journal_slug = "michigan_law_review"
    article_slug = slugify(article_info["title"])

    # Construct PDF URL (from repository pattern)
    pdf_url = f"https://repository.law.umich.edu/cgi/viewcontent.cgi?article={article_info['article_id']}&context=mlr"

    # HTML page URL
    html_url = article_info["html_url"]

    # File paths
    pdf_path = PDF_DIR / f"{journal_slug}_{article_slug}.pdf"
    html_path = HTML_DIR / f"{journal_slug}_{article_slug}.html"

    print(f"\nArticle: {article_info['title']}")
    print(f"Author: {article_info['author']}")

    # Download PDF
    pdf_success = download_file(pdf_url, pdf_path)

    # Download HTML page
    html_success = download_file(html_url, html_path)

    return pdf_success and html_success


def download_virginia_article(article_info):
    """Download both HTML and PDF for a Virginia Law Review article."""
    journal_slug = "virginia_law_review"
    article_slug = slugify(article_info["title"])

    # File paths
    pdf_path = PDF_DIR / f"{journal_slug}_{article_slug}.pdf"
    html_path = HTML_DIR / f"{journal_slug}_{article_slug}.html"

    print(f"\nArticle: {article_info['title']}")
    print(f"Author: {article_info['author']}")

    # Download PDF
    pdf_success = download_file(article_info["pdf_url"], pdf_path)

    # Download HTML page
    html_success = download_file(article_info["html_url"], html_path)

    return pdf_success and html_success


# Michigan Law Review Articles
michigan_articles = [
    {
        "title": "Revocation at the Founding",
        "author": "Jacob Schuman",
        "article_id": "13806",
        "html_url": "https://repository.law.umich.edu/mlr/vol122/iss7/1/",
    },
    {
        "title": "Original Public Meaning and Pregnancy's Ambiguities",
        "author": "Evan D. Bernick and Jill Wieber Lens",
        "article_id": "13808",
        "html_url": "https://repository.law.umich.edu/mlr/vol122/iss7/3/",
    },
    {
        "title": "Orders Without Law",
        "author": "Thomas P. Schmidt",
        "article_id": "13798",
        "html_url": "https://repository.law.umich.edu/mlr/vol122/iss6/3/",
    },
    {
        "title": "The Shadow of the Law of the Police",
        "author": "Adam A. Davidson",
        "article_id": "13799",
        "html_url": "https://repository.law.umich.edu/mlr/vol122/iss6/4/",
    },
    {
        "title": "Beyond Profit Motives",
        "author": "William J. Moon",
        "article_id": "13800",
        "html_url": "https://repository.law.umich.edu/mlr/vol122/iss6/5/",
    },
    {
        "title": "Of Might and Men",
        "author": "Leah M. Litman, Melissa Murray, and Katherine Shaw",
        "article_id": "13801",
        "html_url": "https://repository.law.umich.edu/mlr/vol122/iss6/6/",
    },
    {
        "title": "On the Genealogy of Intimate Digital Harm",
        "author": "Aziz Z. Huq",
        "article_id": "13802",
        "html_url": "https://repository.law.umich.edu/mlr/vol122/iss6/7/",
    },
    {
        "title": "What Is a Prison?",
        "author": "Grace Y. Li",
        "article_id": "13803",
        "html_url": "https://repository.law.umich.edu/mlr/vol122/iss6/8/",
    },
    {
        "title": "Consumerist Waste: Looking Beyond Repair",
        "author": "Roy Shapira",
        "article_id": "13804",
        "html_url": "https://repository.law.umich.edu/mlr/vol122/iss6/9/",
    },
    {
        "title": "Wrongs to Us",
        "author": "Steven Schaus",
        "article_id": "13738",
        "html_url": "https://repository.law.umich.edu/mlr/vol121/iss7/2/",
    },
]

# Virginia Law Review Articles
virginia_articles = [
    {
        "title": "Frictionless Government and Foreign Relations",
        "author": "Ashley Deeks & Kristen E. Eichensehr",
        "pdf_url": "https://virginialawreview.org/wp-content/uploads/2024/12/DeeksEichensehr_Revised.pdf",
        "html_url": "https://virginialawreview.org/articles/frictionless-government-and-foreign-relations/",
    },
    {
        "title": "Constraining Legislative Expulsion",
        "author": "David Fontana & Donald Tobin",
        "pdf_url": "https://virginialawreview.org/wp-content/uploads/2025/03/FontanaTobin_Revised.pdf",
        "html_url": "https://virginialawreview.org/articles/constraining-legislative-expulsion/",
    },
    {
        "title": "Consent and Compensation: Resolving Generative AI's Copyright Crisis",
        "author": "Jacqueline Charlesworth",
        "pdf_url": "https://virginialawreview.org/wp-content/uploads/2024/08/Charlesworth_Revised.pdf",
        "html_url": "https://virginialawreview.org/articles/consent-and-compensation-resolving-generative-ais-copyright-crisis/",
    },
    {
        "title": "Standing Shoulder Pad to Shoulder Pad: Collective Bargaining in College Athletics",
        "author": "Michael McCann & Ryan Rodenberg",
        "pdf_url": "https://virginialawreview.org/wp-content/uploads/2024/07/McCannRodenberg_Revised.pdf",
        "html_url": "https://virginialawreview.org/articles/standing-shoulder-pad-to-shoulder-pad-collective-bargaining-in-college-athletics/",
    },
    {
        "title": "Editing Classic Books: A Threat to the Public Domain?",
        "author": "Jennifer Rothman",
        "pdf_url": "https://virginialawreview.org/wp-content/uploads/2024/03/Rothman_Revised.pdf",
        "html_url": "https://virginialawreview.org/articles/editing-classic-books-a-threat-to-the-public-domain/",
    },
    {
        "title": "Medicaid Act Protections for Gender-Affirming Care",
        "author": "Katherine Wood",
        "pdf_url": "https://virginialawreview.org/wp-content/uploads/2025/02/Wood_Book.pdf",
        "html_url": "https://virginialawreview.org/articles/medicaid-act-protections-for-gender-affirming-care/",
    },
    {
        "title": "The Founders' Purse",
        "author": "Christine Kexel Chabot",
        "pdf_url": "https://virginialawreview.org/wp-content/uploads/2024/09/Chabot_Revised.pdf",
        "html_url": "https://virginialawreview.org/articles/the-founders-purse/",
    },
    {
        "title": "United States v. Rahimi: We Do Not Resolve Any of Those Questions Because We Cannot",
        "author": "Jimmy Donlon",
        "pdf_url": "https://virginialawreview.org/wp-content/uploads/2025/01/Donlon_Book.pdf",
        "html_url": "https://virginialawreview.org/articles/united-states-v-rahimi-we-do-not-resolve-any-of-those-questions-because-we-cannot/",
    },
    {
        "title": "Adapting Conservation Governance Under Climate Change: Lessons from Indian Country",
        "author": "Alejandro E. Camacho, Elizabeth Kronk Warner, Jason McLachlan, Nathan Kroeze",
        "pdf_url": "https://virginialawreview.org/wp-content/uploads/2024/11/CamachoKronkWarnerMcLachlanKroeze_Revised.pdf",
        "html_url": "https://virginialawreview.org/articles/adapting-conservation-governance-under-climate-change-lessons-from-indian-country/",
    },
    {
        "title": "Criminal Violations",
        "author": "Jacob Schuman",
        "pdf_url": "https://virginialawreview.org/wp-content/uploads/2022/12/Schuman__Book.pdf",
        "html_url": "https://virginialawreview.org/articles/criminal-violations/",
    },
]


def main():
    """Main function to download all articles."""
    print("=" * 80)
    print("COLLECTING LAW REVIEW ARTICLE PAIRS")
    print("=" * 80)

    # Download Michigan Law Review articles
    print("\n\n" + "=" * 80)
    print("MICHIGAN LAW REVIEW")
    print("=" * 80)
    michigan_success = 0
    for article in michigan_articles:
        if download_michigan_article(article):
            michigan_success += 1

    print(
        f"\n✓ Successfully collected {michigan_success}/{len(michigan_articles)} Michigan Law Review pairs"
    )

    # Wait before switching to Virginia Law Review
    print("\nWaiting 10 seconds before switching to Virginia Law Review...")
    time.sleep(10)

    # Download Virginia Law Review articles
    print("\n\n" + "=" * 80)
    print("VIRGINIA LAW REVIEW")
    print("=" * 80)
    virginia_success = 0
    for article in virginia_articles:
        if download_virginia_article(article):
            virginia_success += 1

    print(
        f"\n✓ Successfully collected {virginia_success}/{len(virginia_articles)} Virginia Law Review pairs"
    )

    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Michigan Law Review: {michigan_success}/{len(michigan_articles)} pairs")
    print(f"Virginia Law Review: {virginia_success}/{len(virginia_articles)} pairs")
    print(
        f"Total: {michigan_success + virginia_success}/{len(michigan_articles) + len(virginia_articles)} pairs"
    )
    print("\nFiles saved to:")
    print(f"  HTML: {HTML_DIR}")
    print(f"  PDF:  {PDF_DIR}")


if __name__ == "__main__":
    main()

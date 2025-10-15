#!/usr/bin/env python3
"""
Script to collect HTML-PDF pairs from Georgetown Law Journal
Target: 10 pairs from recent volumes (2020-2025)
"""

import json
import time
from pathlib import Path

import requests

# Base directories
DATA_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data")
HTML_DIR = DATA_DIR / "raw_html"
PDF_DIR = DATA_DIR / "raw_pdf"

# Ensure directories exist
HTML_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

# Georgetown Law Journal articles with HTML and PDF URLs
GEORGETOWN_ARTICLES = [
    {
        "title": "The New Sexual Deviancy",
        "author": "Jordan Blair Woods",
        "volume": "113",
        "issue": "5",
        "year": "2025",
        "html_url": "https://www.law.georgetown.edu/georgetown-law-journal/in-print/volume-113/volume-113-issue-5-may-2025/the-new-sexual-deviancy/",
        "pdf_url": "https://www.law.georgetown.edu/georgetown-law-journal/wp-content/uploads/sites/26/2025/07/Woods_The-New-Sexual-Deviancy.pdf",
        "slug": "georgetown_woods_sexual_deviancy",
    },
    {
        "title": "A Faster Way to Yes: Re-Balancing American Asylum Procedures",
        "author": "Michael Kagan",
        "volume": "113",
        "issue": "5",
        "year": "2025",
        "html_url": "https://www.law.georgetown.edu/georgetown-law-journal/in-print/volume-113/volume-113-issue-5-may-2025/a-faster-way-to-yes-re-balancing-american-asylum-procedures/",
        "pdf_url": "https://www.law.georgetown.edu/georgetown-law-journal/wp-content/uploads/sites/26/2025/07/Kagan_A-FASTER-WAY-TO-YES-Re-Balancing-American-Asylum-Procedures.pdf",
        "slug": "georgetown_kagan_asylum_procedures",
    },
    {
        "title": "The Sheriff's Constitution",
        "author": "Farhang Heydari",
        "volume": "113",
        "issue": "5",
        "year": "2025",
        "html_url": "https://www.law.georgetown.edu/georgetown-law-journal/in-print/volume-113/volume-113-issue-5-may-2025/the-sheriffs-constitution/",
        "pdf_url": "https://www.law.georgetown.edu/georgetown-law-journal/wp-content/uploads/sites/26/2025/07/Heydari_The-Sheriffs-Constitution.pdf",
        "slug": "georgetown_heydari_sheriffs_constitution",
    },
    {
        "title": "Renters' Tax Credits",
        "author": "Michelle D. Layser",
        "volume": "113",
        "issue": "5",
        "year": "2025",
        "html_url": "https://www.law.georgetown.edu/georgetown-law-journal/in-print/volume-113/volume-113-issue-5-may-2025/renters-tax-credits/",
        "pdf_url": "https://www.law.georgetown.edu/georgetown-law-journal/wp-content/uploads/sites/26/2025/07/Layser_Renters-Tax-Credits.pdf",
        "slug": "georgetown_layser_renters_tax_credits",
    },
    {
        "title": "Selective Enforcement",
        "author": "Kristelia García",
        "volume": "113",
        "issue": "5",
        "year": "2025",
        "html_url": "https://www.law.georgetown.edu/georgetown-law-journal/in-print/volume-113/volume-113-issue-5-may-2025/selective-enforcement/",
        "pdf_url": "https://www.law.georgetown.edu/georgetown-law-journal/wp-content/uploads/sites/26/2025/07/Garcia_Selective-Enforcement.pdf",
        "slug": "georgetown_garcia_selective_enforcement",
    },
    {
        "title": "Afrofuturism and the Law: A Manifesto",
        "author": "I. Bennett Capers",
        "volume": "112",
        "issue": "6",
        "year": "2024",
        "html_url": "https://www.law.georgetown.edu/georgetown-law-journal/in-print/volume-112/volume-112-issue-6-june-2024/afrofuturism-and-the-law-a-manifesto/",
        "pdf_url": "https://www.law.georgetown.edu/georgetown-law-journal/wp-content/uploads/sites/26/2024/09/Capers_AManifesto.pdf",
        "slug": "georgetown_capers_afrofuturism_manifesto",
    },
    {
        "title": "Taxing the Metaverse",
        "author": "Young Ran (Christine) Kim",
        "volume": "112",
        "issue": "4",
        "year": "2024",
        "html_url": "https://www.law.georgetown.edu/georgetown-law-journal/in-print/volume-112/volume-112-issue-4-april-2024/taxing-the-metaverse/",
        "pdf_url": "https://www.law.georgetown.edu/georgetown-law-journal/wp-content/uploads/sites/26/2024/08/Kim_Taxing.pdf",
        "slug": "georgetown_kim_taxing_metaverse",
    },
    {
        "title": "An Information Commission",
        "author": "Margaret B. Kwoka",
        "volume": "112",
        "issue": "4",
        "year": "2024",
        "html_url": "https://www.law.georgetown.edu/georgetown-law-journal/in-print/volume-112/volume-112-issue-4-april-2024/an-information-commission/",
        "pdf_url": "https://www.law.georgetown.edu/georgetown-law-journal/wp-content/uploads/sites/26/2024/08/Kwoka_Info-Commission.pdf",
        "slug": "georgetown_kwoka_information_commission",
    },
    {
        "title": "The Bias Presumption",
        "author": "Dave Hall & Brad Areheart",
        "volume": "112",
        "issue": "4",
        "year": "2024",
        "html_url": "https://www.law.georgetown.edu/georgetown-law-journal/in-print/volume-112/volume-112-issue-4-april-2024/the-bias-presumption/",
        "pdf_url": "https://www.law.georgetown.edu/georgetown-law-journal/wp-content/uploads/sites/26/2024/08/Hall-Areheart_Bias-Presumption.pdf",
        "slug": "georgetown_hall_areheart_bias_presumption",
    },
    {
        "title": "Data as Likeness",
        "author": "Zahra Takhshid",
        "volume": "112",
        "issue": "5",
        "year": "2024",
        "html_url": "https://www.law.georgetown.edu/georgetown-law-journal/in-print/volume-112/volume-112-issue-5-may-2024/data-as-likeness/",
        "pdf_url": "https://www.law.georgetown.edu/georgetown-law-journal/wp-content/uploads/sites/26/2024/08/Takhshid_Data.pdf",
        "slug": "georgetown_takhshid_data_likeness",
    },
]


def download_file(url, filepath, delay=4):
    """Download a file from URL to filepath with delay"""
    try:
        print(f"  Downloading from: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        print(f"  ✓ Saved to: {filepath}")
        time.sleep(delay)  # Be respectful with delays
        return True
    except Exception as e:
        print(f"  ✗ Error downloading {url}: {e}")
        return False


def collect_articles():
    """Collect HTML and PDF pairs for Georgetown Law Journal articles"""
    results = {
        "journal": "Georgetown Law Journal",
        "collection_date": time.strftime("%Y-%m-%d"),
        "successful_pairs": [],
        "failed_pairs": [],
        "total_attempted": len(GEORGETOWN_ARTICLES),
    }

    for i, article in enumerate(GEORGETOWN_ARTICLES, 1):
        print(f"\n[{i}/{len(GEORGETOWN_ARTICLES)}] Processing: {article['title']}")
        print(f"  Author: {article['author']}")
        print(f"  Volume {article['volume']}, Issue {article['issue']} ({article['year']})")

        html_path = HTML_DIR / f"{article['slug']}.html"
        pdf_path = PDF_DIR / f"{article['slug']}.pdf"

        html_success = download_file(article["html_url"], html_path)
        pdf_success = download_file(article["pdf_url"], pdf_path)

        if html_success and pdf_success:
            results["successful_pairs"].append(
                {
                    "slug": article["slug"],
                    "title": article["title"],
                    "author": article["author"],
                    "volume": article["volume"],
                    "issue": article["issue"],
                    "year": article["year"],
                    "html_url": article["html_url"],
                    "pdf_url": article["pdf_url"],
                    "html_file": str(html_path),
                    "pdf_file": str(pdf_path),
                }
            )
        else:
            results["failed_pairs"].append(
                {
                    "slug": article["slug"],
                    "title": article["title"],
                    "html_success": html_success,
                    "pdf_success": pdf_success,
                }
            )

    # Save results
    results_file = DATA_DIR / "georgetown_collection_results.json"
    with open(results_file, "w") as f:
        json.dump(results, indent=2, fp=f)

    print(f"\n{'=' * 70}")
    print("COLLECTION COMPLETE - Georgetown Law Journal")
    print(f"{'=' * 70}")
    print(f"Total attempted: {results['total_attempted']}")
    print(f"Successful pairs: {len(results['successful_pairs'])}")
    print(f"Failed pairs: {len(results['failed_pairs'])}")
    print(f"\nResults saved to: {results_file}")

    return results


if __name__ == "__main__":
    results = collect_articles()

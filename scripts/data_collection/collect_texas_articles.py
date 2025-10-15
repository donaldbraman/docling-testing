#!/usr/bin/env python3
"""
Script to collect HTML-PDF pairs from Texas Law Review
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

# Texas Law Review articles with HTML and PDF URLs
TEXAS_ARTICLES = [
    {
        "title": "The Beleaguered Sovereign: Judicial Restraints on Public Enforcement",
        "author": "Helen Hershkoff & Luke P. Norris",
        "volume": "103",
        "year": "2025",
        "html_url": "https://texaslawreview.org/the-beleaguered-sovereign-judicial-restraints-on-public-enforcement/",
        "pdf_url": "https://texaslawreview.org/wp-content/uploads/2025/04/Hershkoff-The-Beleaguered-Sovereign.pdf",
        "slug": "texas_hershkoff_beleaguered_sovereign",
    },
    {
        "title": "A Law and Political Economy of Intellectual Property",
        "author": "Oren Bracha & Talha Syed",
        "volume": "103",
        "year": "2025",
        "html_url": "https://texaslawreview.org/a-law-and-political-economy-of-intellectual-property/",
        "pdf_url": "https://texaslawreview.org/wp-content/uploads/2025/06/Bracha.A-Law-and-Political-Economy.pdf",
        "slug": "texas_bracha_syed_ip_political_economy",
    },
    {
        "title": "Corporate Democracy and the Intermediary Voting Dilemma",
        "author": "Jill Fisch & Jeff Schwartz",
        "volume": "103",
        "year": "2024",
        "html_url": "https://texaslawreview.org/corporate-democracy-and-the-intermediary-voting-dilemma/",
        "pdf_url": "https://texaslawreview.org/wp-content/uploads/2024/01/FischSchwartz.Printer.pdf",
        "slug": "texas_fisch_schwartz_corporate_democracy",
    },
    {
        "title": "Big Data Searches and the Future of Criminal Procedure",
        "author": "Mary D. Fan",
        "volume": "103",
        "year": "2024",
        "html_url": "https://texaslawreview.org/big-data-searches-and-the-future-of-criminal-procedure/",
        "pdf_url": "https://texaslawreview.org/wp-content/uploads/2024/04/Fan.printer.pdf",
        "slug": "texas_fan_big_data_searches",
    },
    {
        "title": "The Constitutional Case Against Exclusionary Zoning",
        "author": "Joshua Braver & Ilya Somin",
        "volume": "103",
        "year": "2024",
        "html_url": "https://texaslawreview.org/the-constitutional-case-against-exclusionary-zoning/",
        "pdf_url": "https://texaslawreview.org/wp-content/uploads/2024/11/Braver.Printer.pdf",
        "slug": "texas_braver_somin_exclusionary_zoning",
    },
    {
        "title": "Selective Originalism and Judicial Role Morality",
        "author": "Richard H. Fallon, Jr.",
        "volume": "103",
        "year": "2024",
        "html_url": "https://texaslawreview.org/selective-originalism-and-judicial-role-morality/",
        "pdf_url": "https://texaslawreview.org/wp-content/uploads/2024/01/Fallon.printer.pdf",
        "slug": "texas_fallon_selective_originalism",
    },
    {
        "title": "Judicial Review of Unconventional Enforcement Regimes",
        "author": "James E. Pfander",
        "volume": "103",
        "year": "2024",
        "html_url": "https://texaslawreview.org/judicial-review-of-unconventional-enforcement-regimes/",
        "pdf_url": "https://texaslawreview.org/wp-content/uploads/2024/04/Pfander.printer.pdf",
        "slug": "texas_pfander_judicial_review",
    },
    {
        "title": "Second Amendment Exceptionalism: Public Expression and Public Carry",
        "author": "Timothy Zick",
        "volume": "103",
        "year": "2024",
        "html_url": "https://texaslawreview.org/second-amendment-exceptionalism-public-expression-and-public-carry/",
        "pdf_url": "https://texaslawreview.org/wp-content/uploads/2024/01/Zick.Printer.pdf",
        "slug": "texas_zick_second_amendment",
    },
    {
        "title": "Technologies of Violence: Law, Markets, and Innovation for Gun Safety",
        "author": "Leah Litman & Pratheepan Gulasekaram",
        "volume": "103",
        "year": "2025",
        "html_url": "https://texaslawreview.org/technologies-of-violence-law-markets-and-innovation-for-gun-safety/",
        "pdf_url": "https://texaslawreview.org/wp-content/uploads/2025/05/LitmanGulasekaram.Printer.pdf",
        "slug": "texas_litman_gulasekaram_gun_safety",
    },
    {
        "title": "Video Analytics and Fourth Amendment Vision",
        "author": "Matthew Tokson",
        "volume": "103",
        "year": "2025",
        "html_url": "https://texaslawreview.org/video-analytics-and-fourth-amendment-vision/",
        "pdf_url": "https://texaslawreview.org/wp-content/uploads/2025/05/Tokson.Printer.pdf",
        "slug": "texas_tokson_video_analytics",
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
    """Collect HTML and PDF pairs for Texas Law Review articles"""
    results = {
        "journal": "Texas Law Review",
        "collection_date": time.strftime("%Y-%m-%d"),
        "successful_pairs": [],
        "failed_pairs": [],
        "total_attempted": len(TEXAS_ARTICLES),
    }

    for i, article in enumerate(TEXAS_ARTICLES, 1):
        print(f"\n[{i}/{len(TEXAS_ARTICLES)}] Processing: {article['title']}")
        print(f"  Author: {article['author']}")
        print(f"  Volume {article['volume']} ({article['year']})")

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
    results_file = DATA_DIR / "texas_collection_results.json"
    with open(results_file, "w") as f:
        json.dump(results, indent=2, fp=f)

    print(f"\n{'=' * 70}")
    print("COLLECTION COMPLETE - Texas Law Review")
    print(f"{'=' * 70}")
    print(f"Total attempted: {results['total_attempted']}")
    print(f"Successful pairs: {len(results['successful_pairs'])}")
    print(f"Failed pairs: {len(results['failed_pairs'])}")
    print(f"\nResults saved to: {results_file}")

    return results


if __name__ == "__main__":
    results = collect_articles()

#!/usr/bin/env python3
"""
PubMed Central (PMC) HTML-PDF Pair Collection Script

Collects medical/biomedical article pairs from PubMed Central open-access repository.
Target: 40-50 complete HTML-PDF pairs
Domain: Medical, biomedical, life sciences

Usage:
    uv run python scripts/data_collection/collect_pubmed_central.py --target 50

Author: Claude Code
Date: October 17, 2025
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import requests

# Configuration
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
PMC_BASE = "https://www.ncbi.nlm.nih.gov/pmc/"
REQUEST_DELAY = 0.4  # 2.5 req/s (under 3 req/s limit)
EXTENDED_PAUSE = 5  # 5s pause every 20 requests
USER_AGENT = "Research Bot (mailto:research@example.com)"  # Replace with real contact

# Output directories
OUTPUT_DIR = Path("data/raw_html_pdf_pairs/pubmed_central")
HTML_DIR = Path("data/raw_html")
PDF_DIR = Path("data/raw_pdf")
LOG_DIR = Path("data/collection_logs/pubmed_central")


def setup_directories():
    """Create output directories if they don't exist."""
    for directory in [HTML_DIR, PDF_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    print("✓ Output directories ready")


def search_pmc_articles(max_results=100):
    """
    Search for recent open-access PMC articles.

    Args:
        max_results: Maximum number of articles to retrieve

    Returns:
        list: PMC IDs of candidate articles
    """
    print("\nPhase 1: Searching PMC for recent open-access articles...")

    search_url = f"{BASE_URL}esearch.fcgi"
    params = {
        "db": "pmc",
        "term": "hasabstract AND ffrft[filter] AND 2024[pdat]",  # 2024 full-text articles
        "retmax": max_results,
        "retmode": "json",
        "sort": "pub_date",
        "email": USER_AGENT,
    }

    try:
        response = requests.get(search_url, params=params, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        data = response.json()

        pmc_ids = data.get("esearchresult", {}).get("idlist", [])
        print(f"  Found {len(pmc_ids)} candidate articles")

        time.sleep(REQUEST_DELAY)
        return pmc_ids

    except Exception as e:
        print(f"  ✗ Error searching PMC: {e}")
        return []


def fetch_article_summaries(pmc_ids):
    """
    Fetch article metadata for PMC IDs.

    Args:
        pmc_ids: List of PMC IDs

    Returns:
        dict: Article metadata by PMC ID
    """
    print("\nPhase 2: Fetching article metadata...")

    articles = {}
    summary_url = f"{BASE_URL}esummary.fcgi"

    # Process in batches of 20
    for i in range(0, len(pmc_ids), 20):
        batch_ids = pmc_ids[i : i + 20]
        id_str = ",".join(batch_ids)

        params = {"db": "pmc", "id": id_str, "retmode": "json"}

        try:
            response = requests.get(summary_url, params=params, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            data = response.json()

            for pmc_id in batch_ids:
                if pmc_id in data.get("result", {}):
                    article_data = data["result"][pmc_id]
                    articles[pmc_id] = {
                        "pmc_id": pmc_id,
                        "title": article_data.get("title", "Unknown"),
                        "authors": article_data.get("authors", []),
                        "journal": article_data.get("fulljournalname", "Unknown"),
                        "pub_date": article_data.get("pubdate", "Unknown"),
                    }

            print(f"  Processed {min(i + 20, len(pmc_ids))}/{len(pmc_ids)} articles...")
            time.sleep(REQUEST_DELAY)

            # Extended pause every 20 requests
            if (i // 20 + 1) % 5 == 0:
                print(f"  [Extended pause: {EXTENDED_PAUSE}s]")
                time.sleep(EXTENDED_PAUSE)

        except Exception as e:
            print(f"  ✗ Error fetching metadata for batch {i // 20 + 1}: {e}")
            continue

    print(f"  Retrieved metadata for {len(articles)} articles")
    return articles


def download_html(pmc_id, output_path):
    """
    Download HTML version of PMC article.

    Args:
        pmc_id: PMC ID (without 'PMC' prefix)
        output_path: Path to save HTML file

    Returns:
        bool: Success status
    """
    html_url = f"{PMC_BASE}articles/PMC{pmc_id}/"

    try:
        response = requests.get(html_url, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()

        # Check if we got HTML (not error page)
        if len(response.text) > 10000:  # Reasonable article length
            output_path.write_text(response.text, encoding="utf-8")
            return True
        else:
            return False

    except Exception as e:
        print(f"    ✗ HTML error: {e}")
        return False


def download_pdf(pmc_id, output_path):
    """
    Download PDF version of PMC article.

    Args:
        pmc_id: PMC ID (without 'PMC' prefix)
        output_path: Path to save PDF file

    Returns:
        bool: Success status
    """
    pdf_url = f"{PMC_BASE}articles/PMC{pmc_id}/pdf/"

    try:
        response = requests.get(pdf_url, headers={"User-Agent": USER_AGENT}, timeout=60)
        response.raise_for_status()

        # Check if we got PDF (not error page)
        if response.content[:4] == b"%PDF" and len(response.content) > 100000:
            output_path.write_bytes(response.content)
            return True
        else:
            return False

    except Exception as e:
        print(f"    ✗ PDF error: {e}")
        return False


def validate_pair(html_path, pdf_path):
    """
    Validate HTML-PDF pair quality.

    Args:
        html_path: Path to HTML file
        pdf_path: Path to PDF file

    Returns:
        dict: Validation results
    """
    validation = {
        "html_exists": html_path.exists(),
        "pdf_exists": pdf_path.exists(),
        "html_size": html_path.stat().st_size if html_path.exists() else 0,
        "pdf_size": pdf_path.stat().st_size if pdf_path.exists() else 0,
        "valid": False,
    }

    # Check minimum sizes
    if validation["html_size"] > 10000 and validation["pdf_size"] > 100000:
        validation["valid"] = True

    return validation


def generate_report(collected, failed, start_time):
    """
    Generate collection report.

    Args:
        collected: List of successfully collected articles
        failed: List of failed articles
        start_time: Collection start time
    """
    report_path = LOG_DIR / "COLLECTION_REPORT.md"
    duration = (datetime.now() - start_time).total_seconds() / 60

    with open(report_path, "w") as f:
        f.write("# PubMed Central Collection Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("**Source:** PubMed Central (PMC)\n")
        f.write("**Target:** 40-50 pairs\n")
        f.write(f"**Achieved:** {len(collected)} complete pairs\n")
        f.write(f"**Duration:** {duration:.1f} minutes\n\n")

        f.write("## Collection Results\n\n")
        f.write("### Success Metrics\n")
        f.write("- Target: 40 pairs minimum\n")
        f.write(f"- Achieved: {len(collected)} complete pairs\n")
        f.write(f"- Failed: {len(failed)} attempts\n")
        f.write(f"- Success Rate: {100 * len(collected) / (len(collected) + len(failed)):.1f}%\n\n")

        f.write("### Files Collected\n")
        total_html_size = sum(a["html_size"] for a in collected) / 1024 / 1024
        total_pdf_size = sum(a["pdf_size"] for a in collected) / 1024 / 1024
        f.write(f"- HTML files: {len(collected)} articles (total: {total_html_size:.1f} MB)\n")
        f.write(f"- PDF files: {len(collected)} PDFs (total: {total_pdf_size:.1f} MB)\n")
        f.write(f"- Total data: {total_html_size + total_pdf_size:.1f} MB\n\n")

        f.write("## Articles Collected\n\n")
        for i, article in enumerate(collected, 1):
            f.write(f'{i}. PMC{article["pmc_id"]}: "{article["title"]}"\n')
            f.write(f"   - Journal: {article['journal']}\n")
            f.write(f"   - Date: {article['pub_date']}\n")
            f.write(f"   - HTML: {article['html_size'] / 1024:.1f} KB\n")
            f.write(f"   - PDF: {article['pdf_size'] / 1024:.1f} KB\n\n")

        f.write("## Success Criteria Check\n\n")
        f.write(f"- {'✓' if len(collected) >= 40 else '✗'} Minimum 40 complete pairs\n")
        f.write(f"- {'✓' if len(failed) == 0 else '✗'} No blocking incidents\n")
        f.write("- ✓ Progress documented\n")

    print(f"\n✓ Report saved to: {report_path}")

    # Save JSON manifest
    json_path = LOG_DIR / "collected_articles.json"
    with open(json_path, "w") as f:
        json.dump(collected, f, indent=2)
    print(f"✓ JSON manifest saved to: {json_path}")


def main():
    """Main collection workflow."""
    parser = argparse.ArgumentParser(description="Collect PubMed Central HTML-PDF pairs")
    parser.add_argument(
        "--target", type=int, default=50, help="Target number of pairs to collect (default: 50)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("PubMed Central (PMC) HTML-PDF Pair Collection")
    print("=" * 80)
    print(f"\nTarget: {args.target} complete pairs")
    print(f"Rate limit: {REQUEST_DELAY}s between requests")
    print()

    start_time = datetime.now()

    # Setup
    setup_directories()

    # Discovery
    pmc_ids = search_pmc_articles(max_results=args.target + 20)  # Extra for failures
    if not pmc_ids:
        print("\n✗ No articles found. Exiting.")
        return

    articles_metadata = fetch_article_summaries(pmc_ids)

    # Collection
    print("\nPhase 3: Downloading HTML-PDF pairs...")
    collected = []
    failed = []

    for i, (pmc_id, metadata) in enumerate(articles_metadata.items(), 1):
        print(f"\n[{i}/{len(articles_metadata)}] PMC{pmc_id}: {metadata['title'][:60]}...")

        # File paths
        html_path = HTML_DIR / f"pmc_{pmc_id}.html"
        pdf_path = PDF_DIR / f"pmc_{pmc_id}.pdf"

        # Download HTML
        print("  Downloading HTML...", end="")
        html_success = download_html(pmc_id, html_path)
        print(f" {'✓' if html_success else '✗'}")
        time.sleep(REQUEST_DELAY)

        # Download PDF
        print("  Downloading PDF...", end="")
        pdf_success = download_pdf(pmc_id, pdf_path)
        print(f" {'✓' if pdf_success else '✗'}")
        time.sleep(REQUEST_DELAY)

        # Validate
        if html_success and pdf_success:
            validation = validate_pair(html_path, pdf_path)
            if validation["valid"]:
                metadata.update(
                    {
                        "html_path": str(html_path),
                        "pdf_path": str(pdf_path),
                        "html_size": validation["html_size"],
                        "pdf_size": validation["pdf_size"],
                        "validated": True,
                    }
                )
                collected.append(metadata)
                print(f"  ✓ Success ({len(collected)}/{args.target})")
            else:
                failed.append(metadata)
                print("  ✗ Validation failed")
        else:
            failed.append(metadata)
            print("  ✗ Download failed")

        # Stop if target reached
        if len(collected) >= args.target:
            print(f"\n✓ Target reached! Collected {len(collected)} pairs.")
            break

        # Progress pause
        if i % 20 == 0 and i < len(articles_metadata):
            print(f"\n  [Extended pause: {EXTENDED_PAUSE}s]")
            time.sleep(EXTENDED_PAUSE)

    # Reporting
    print("\nPhase 4: Generating report...")
    generate_report(collected, failed, start_time)

    # Summary
    print()
    print("=" * 80)
    print("COLLECTION COMPLETE")
    print("=" * 80)
    print(f"  Successful: {len(collected)} pairs")
    print(f"  Failed: {len(failed)} attempts")
    print(f"  Success rate: {100 * len(collected) / (len(collected) + len(failed)):.1f}%")
    print(f"  Duration: {(datetime.now() - start_time).total_seconds() / 60:.1f} minutes")
    print("=" * 80)

    # Save progress log
    progress_path = LOG_DIR / "progress.txt"
    with open(progress_path, "a") as f:
        f.write(f"\n{datetime.now()}: Collected {len(collected)} pairs, {len(failed)} failed\n")


if __name__ == "__main__":
    main()

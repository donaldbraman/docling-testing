#!/usr/bin/env python3
"""
arXiv HTML-PDF Pair Collection Script

Collects STEM preprint pairs from arXiv with LaTeX-rendered HTML from ar5iv.
Target: 40-50 complete HTML-PDF pairs
Domain: Computer Science, Physics, Mathematics, Economics

Usage:
    uv run python scripts/data_collection/collect_arxiv_papers.py --target 50

Author: Claude Code
Date: October 17, 2025
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

import requests

# Configuration
ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_PDF_BASE = "https://arxiv.org/pdf/"
AR5IV_HTML_BASE = "https://ar5iv.org/html/"
API_DELAY = 3  # 3 seconds between API requests (mandatory)
DOWNLOAD_DELAY = 2  # 2 seconds between PDF/HTML downloads
USER_AGENT = "Research Bot (mailto:research@example.com)"

# arXiv categories for diversity
CATEGORIES = [
    "cs.AI",  # Artificial Intelligence
    "cs.LG",  # Machine Learning
    "cs.CL",  # Computation and Language
    "physics.comp-ph",  # Computational Physics
    "math.ST",  # Statistics Theory
    "econ.GN",  # General Economics
]

# Output directories
HTML_DIR = Path("data/raw_html")
PDF_DIR = Path("data/raw_pdf")
LOG_DIR = Path("data/collection_logs/arxiv")


def setup_directories():
    """Create output directories if they don't exist."""
    for directory in [HTML_DIR, PDF_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    print("✓ Output directories ready")


def search_arxiv_category(category, max_results=10):
    """
    Search arXiv for recent papers in a category.

    Args:
        category: arXiv category (e.g., 'cs.AI')
        max_results: Number of results to retrieve

    Returns:
        list: Paper metadata
    """
    params = {
        "search_query": f"cat:{category} AND submittedDate:[202401* TO 202412*]",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    try:
        response = requests.get(ARXIV_API, params=params, timeout=30)
        response.raise_for_status()

        # Parse Atom XML
        root = ElementTree.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        papers = []
        for entry in root.findall("atom:entry", ns):
            arxiv_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
            # Remove version suffix (v1, v2, etc.)
            arxiv_id = arxiv_id.split("v")[0]

            title = entry.find("atom:title", ns).text.strip()
            summary = entry.find("atom:summary", ns).text.strip()
            published = entry.find("atom:published", ns).text

            # Extract authors
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns).text
                authors.append(name)

            papers.append(
                {
                    "arxiv_id": arxiv_id,
                    "title": title,
                    "authors": authors,
                    "summary": summary[:200],  # First 200 chars
                    "published": published,
                    "category": category,
                }
            )

        return papers

    except Exception as e:
        print(f"  ✗ Error searching {category}: {e}")
        return []


def discover_papers(papers_per_category=8):
    """
    Discover papers across multiple categories.

    Args:
        papers_per_category: Number of papers to collect per category

    Returns:
        list: All discovered papers
    """
    print(f"\nPhase 1: Discovering papers across {len(CATEGORIES)} categories...")

    all_papers = []

    for category in CATEGORIES:
        print(f"  Searching {category}...", end="")
        papers = search_arxiv_category(category, max_results=papers_per_category)
        all_papers.extend(papers)
        print(f" found {len(papers)} papers")

        time.sleep(API_DELAY)  # MANDATORY 3-second delay

    print(f"  Total discovered: {len(all_papers)} papers")
    return all_papers


def download_pdf(arxiv_id, output_path):
    """
    Download PDF from arXiv.

    Args:
        arxiv_id: arXiv ID (e.g., '2401.12345')
        output_path: Path to save PDF

    Returns:
        bool: Success status
    """
    pdf_url = f"{ARXIV_PDF_BASE}{arxiv_id}.pdf"

    try:
        response = requests.get(pdf_url, headers={"User-Agent": USER_AGENT}, timeout=60)
        response.raise_for_status()

        # Verify it's a PDF
        if response.content[:4] == b"%PDF" and len(response.content) > 100000:
            output_path.write_bytes(response.content)
            return True
        else:
            return False

    except Exception as e:
        print(f"    ✗ PDF error: {e}")
        return False


def download_html(arxiv_id, output_path):
    """
    Download HTML from ar5iv (LaTeX rendering service).

    Args:
        arxiv_id: arXiv ID
        output_path: Path to save HTML

    Returns:
        bool: Success status
    """
    html_url = f"{AR5IV_HTML_BASE}{arxiv_id}"

    try:
        response = requests.get(html_url, headers={"User-Agent": USER_AGENT}, timeout=60)
        response.raise_for_status()

        # Check if HTML is rendered (not error page)
        if len(response.text) > 10000 and "ltx_document" in response.text:
            output_path.write_text(response.text, encoding="utf-8")
            return True
        else:
            # Try alternative: native arXiv HTML
            alt_url = f"https://arxiv.org/html/{arxiv_id}"
            alt_response = requests.get(alt_url, headers={"User-Agent": USER_AGENT}, timeout=60)
            if alt_response.status_code == 200 and len(alt_response.text) > 10000:
                output_path.write_text(alt_response.text, encoding="utf-8")
                return True
            return False

    except Exception as e:
        print(f"    ✗ HTML error: {e}")
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
    # arXiv papers tend to be longer, so PDF should be >200KB
    if validation["html_size"] > 15000 and validation["pdf_size"] > 200000:
        validation["valid"] = True

    return validation


def generate_report(collected, failed, start_time):
    """
    Generate collection report.

    Args:
        collected: List of successfully collected papers
        failed: List of failed papers
        start_time: Collection start time
    """
    report_path = LOG_DIR / "COLLECTION_REPORT.md"
    duration = (datetime.now() - start_time).total_seconds() / 60

    with open(report_path, "w") as f:
        f.write("# arXiv Collection Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("**Source:** arXiv + ar5iv\n")
        f.write("**Target:** 40-50 pairs\n")
        f.write(f"**Achieved:** {len(collected)} complete pairs\n")
        f.write(f"**Duration:** {duration:.1f} minutes\n\n")

        f.write("## Collection Results\n\n")
        f.write("### Success Metrics\n")
        f.write("- Target: 40 pairs minimum\n")
        f.write(f"- Achieved: {len(collected)} complete pairs\n")
        f.write(f"- Failed: {len(failed)} attempts\n")
        f.write(
            f"- Success Rate: {100 * len(collected) / (len(collected) + len(failed)) if (len(collected) + len(failed)) > 0 else 0:.1f}%\n\n"
        )

        # Category distribution
        from collections import Counter

        categories = Counter(p["category"] for p in collected)
        f.write("### Category Distribution\n")
        for cat, count in categories.items():
            f.write(f"- {cat}: {count} papers\n")
        f.write("\n")

        f.write("### Files Collected\n")
        total_html_size = sum(p["html_size"] for p in collected) / 1024 / 1024
        total_pdf_size = sum(p["pdf_size"] for p in collected) / 1024 / 1024
        f.write(f"- HTML files: {len(collected)} papers (total: {total_html_size:.1f} MB)\n")
        f.write(f"- PDF files: {len(collected)} papers (total: {total_pdf_size:.1f} MB)\n")
        f.write(f"- Total data: {total_html_size + total_pdf_size:.1f} MB\n\n")

        f.write("## Papers Collected\n\n")
        for i, paper in enumerate(collected, 1):
            f.write(f"{i}. [{paper['arxiv_id']}] {paper['title']}\n")
            f.write(f"   - Category: {paper['category']}\n")
            f.write(f"   - Authors: {', '.join(paper['authors'][:3])}\n")
            f.write(f"   - HTML: {paper['html_size'] / 1024:.1f} KB\n")
            f.write(f"   - PDF: {paper['pdf_size'] / 1024:.1f} KB\n\n")

        f.write("## Success Criteria Check\n\n")
        f.write(f"- {'✓' if len(collected) >= 40 else '✗'} Minimum 40 complete pairs\n")
        f.write(f"- {'✓' if len(categories) >= 4 else '✗'} At least 4 categories\n")
        f.write("- ✓ Progress documented\n")

    print(f"\n✓ Report saved to: {report_path}")

    # Save JSON
    json_path = LOG_DIR / "collected_papers.json"
    with open(json_path, "w") as f:
        json.dump(collected, f, indent=2)
    print(f"✓ JSON manifest saved to: {json_path}")


def main():
    """Main collection workflow."""
    parser = argparse.ArgumentParser(description="Collect arXiv HTML-PDF pairs")
    parser.add_argument(
        "--target", type=int, default=50, help="Target number of pairs to collect (default: 50)"
    )
    parser.add_argument(
        "--per-category", type=int, default=10, help="Papers per category (default: 10)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("arXiv HTML-PDF Pair Collection")
    print("=" * 80)
    print(f"\nTarget: {args.target} complete pairs")
    print(f"Categories: {len(CATEGORIES)}")
    print(f"API delay: {API_DELAY}s between requests")
    print(f"Download delay: {DOWNLOAD_DELAY}s between files")
    print()

    start_time = datetime.now()

    # Setup
    setup_directories()

    # Discovery
    papers = discover_papers(papers_per_category=args.per_category)
    if not papers:
        print("\n✗ No papers found. Exiting.")
        return

    # Collection
    print("\nPhase 2: Downloading HTML-PDF pairs...")
    collected = []
    failed = []

    for i, paper in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}] {paper['arxiv_id']}: {paper['title'][:60]}...")

        # File paths (sanitize arxiv_id for filename)
        safe_id = paper["arxiv_id"].replace(".", "_")
        html_path = HTML_DIR / f"arxiv_{safe_id}.html"
        pdf_path = PDF_DIR / f"arxiv_{safe_id}.pdf"

        # Download PDF
        print("  Downloading PDF...", end="")
        pdf_success = download_pdf(paper["arxiv_id"], pdf_path)
        print(f" {'✓' if pdf_success else '✗'}")
        time.sleep(DOWNLOAD_DELAY)

        # Download HTML
        print("  Downloading HTML...", end="")
        html_success = download_html(paper["arxiv_id"], html_path)
        print(f" {'✓' if html_success else '✗'}")
        time.sleep(DOWNLOAD_DELAY)

        # Validate
        if html_success and pdf_success:
            validation = validate_pair(html_path, pdf_path)
            if validation["valid"]:
                paper.update(
                    {
                        "html_path": str(html_path),
                        "pdf_path": str(pdf_path),
                        "html_size": validation["html_size"],
                        "pdf_size": validation["pdf_size"],
                        "validated": True,
                    }
                )
                collected.append(paper)
                print(f"  ✓ Success ({len(collected)}/{args.target})")
            else:
                failed.append(paper)
                print("  ✗ Validation failed")
        else:
            failed.append(paper)
            print("  ✗ Download failed")

        # Stop if target reached
        if len(collected) >= args.target:
            print(f"\n✓ Target reached! Collected {len(collected)} pairs.")
            break

    # Reporting
    print("\nPhase 3: Generating report...")
    generate_report(collected, failed, start_time)

    # Summary
    print()
    print("=" * 80)
    print("COLLECTION COMPLETE")
    print("=" * 80)
    print(f"  Successful: {len(collected)} pairs")
    print(f"  Failed: {len(failed)} attempts")
    print(
        f"  Success rate: {100 * len(collected) / (len(collected) + len(failed)) if (len(collected) + len(failed)) > 0 else 0:.1f}%"
    )
    print(f"  Duration: {(datetime.now() - start_time).total_seconds() / 60:.1f} minutes")
    print("=" * 80)


if __name__ == "__main__":
    main()

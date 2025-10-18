#!/usr/bin/env python3
"""
Categorize HTML files as full-text articles vs abstract-only pages.

This script analyzes HTML files to determine if they contain full article text
or just abstracts with links to PDFs. It uses multiple heuristics:
- Word count (full-text typically 8000+ words)
- Presence of PDF download links
- Article structure indicators

Results are saved to data/html_categorization_results.csv
"""

import argparse
import csv
import re
from pathlib import Path

from bs4 import BeautifulSoup


def count_words_in_html(html_content: str) -> int:
    """
    Count words in HTML content, excluding script/style tags.

    Args:
        html_content: Raw HTML string

    Returns:
        Word count
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style", "head"]):
        script.decompose()

    # Get text and count words
    text = soup.get_text()
    words = text.split()
    return len(words)


def has_pdf_download_link(html_content: str) -> bool:
    """
    Check if HTML contains PDF download links.

    Args:
        html_content: Raw HTML string

    Returns:
        True if PDF download link found
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Look for common PDF download patterns
    patterns = [
        r"download.*pdf",
        r"view.*pdf",
        r"full.*text",
        r"viewcontent\.cgi",
        r"\.pdf",
    ]

    # Check links and button text
    for link in soup.find_all(["a", "button"]):
        text = link.get_text().lower()
        href = str(link.get("href", "")).lower()
        title = str(link.get("title", "")).lower()

        for pattern in patterns:
            if (
                re.search(pattern, text, re.IGNORECASE)
                or re.search(pattern, href, re.IGNORECASE)
                or re.search(pattern, title, re.IGNORECASE)
            ):
                return True

    # Check for PDF meta tags
    for meta in soup.find_all("meta"):
        content = str(meta.get("content", "")).lower()
        if ".pdf" in content or "viewcontent" in content:
            return True

    return False


def categorize_html(html_path: Path) -> dict[str, any]:
    """
    Categorize a single HTML file.

    Args:
        html_path: Path to HTML file

    Returns:
        Dictionary with categorization results
    """
    try:
        html_content = html_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"Error reading {html_path.name}: {e}")
        return {
            "basename": html_path.stem,
            "category": "error",
            "word_count": 0,
            "has_pdf_download_link": False,
            "confidence": "low",
        }

    word_count = count_words_in_html(html_content)
    has_pdf_link = has_pdf_download_link(html_content)

    # Categorization logic based on word count thresholds
    # Abstract-only: typically 1,600-5,000 words
    # Full-text: typically 8,000+ words
    # Gray area: 5,000-8,000 words

    if word_count < 5000:
        category = "abstract_only"
        confidence = "high" if has_pdf_link else "medium"
    elif word_count > 8000:
        category = "full_text"
        confidence = "high"
    else:
        # Gray area - use PDF link as tiebreaker
        if has_pdf_link:
            category = "abstract_only"
            confidence = "medium"
        else:
            category = "full_text"
            confidence = "medium"

    return {
        "basename": html_path.stem,
        "category": category,
        "word_count": word_count,
        "has_pdf_download_link": has_pdf_link,
        "confidence": confidence,
    }


def analyze_directory(html_dir: Path, exclude_arxiv: bool = True) -> list[dict]:
    """
    Analyze all HTML files in a directory.

    Args:
        html_dir: Directory containing HTML files
        exclude_arxiv: Whether to exclude arxiv_*.html files

    Returns:
        List of categorization results
    """
    results = []
    html_files = sorted(html_dir.glob("*.html"))

    for html_path in html_files:
        if exclude_arxiv and html_path.name.startswith("arxiv_"):
            continue

        result = categorize_html(html_path)
        results.append(result)

        # Print progress
        category_symbol = "✓" if result["category"] == "full_text" else "✗"
        print(
            f"{category_symbol} {html_path.name}: {result['word_count']:,} words -> {result['category']}"
        )

    return results


def save_results(results: list[dict], output_path: Path):
    """
    Save categorization results to CSV.

    Args:
        results: List of categorization dictionaries
        output_path: Output CSV path
    """
    with output_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["basename", "category", "word_count", "has_pdf_download_link", "confidence"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to: {output_path}")


def print_summary(results: list[dict]):
    """
    Print summary statistics.

    Args:
        results: List of categorization dictionaries
    """
    total = len(results)
    full_text = sum(1 for r in results if r["category"] == "full_text")
    abstract_only = sum(1 for r in results if r["category"] == "abstract_only")
    errors = sum(1 for r in results if r["category"] == "error")

    high_confidence = sum(1 for r in results if r["confidence"] == "high")
    medium_confidence = sum(1 for r in results if r["confidence"] == "medium")
    low_confidence = sum(1 for r in results if r["confidence"] == "low")

    print("\n" + "=" * 60)
    print("HTML CATEGORIZATION SUMMARY")
    print("=" * 60)
    print(f"Total files analyzed: {total}")
    print("\nCategories:")
    print(f"  Full-text articles:  {full_text:3d} ({full_text / total * 100:.1f}%)")
    print(f"  Abstract-only pages: {abstract_only:3d} ({abstract_only / total * 100:.1f}%)")
    print(f"  Errors:              {errors:3d} ({errors / total * 100:.1f}%)")
    print("\nConfidence levels:")
    print(f"  High:   {high_confidence:3d} ({high_confidence / total * 100:.1f}%)")
    print(f"  Medium: {medium_confidence:3d} ({medium_confidence / total * 100:.1f}%)")
    print(f"  Low:    {low_confidence:3d} ({low_confidence / total * 100:.1f}%)")

    # Print word count statistics
    word_counts = [r["word_count"] for r in results if r["category"] != "error"]
    if word_counts:
        print("\nWord count statistics:")
        print(f"  Min:    {min(word_counts):,}")
        print(f"  Max:    {max(word_counts):,}")
        print(f"  Median: {sorted(word_counts)[len(word_counts) // 2]:,}")

    # List full-text files
    full_text_files = [r["basename"] for r in results if r["category"] == "full_text"]
    if full_text_files:
        print(f"\n{len(full_text_files)} Full-text HTML files (usable for training):")
        for basename in sorted(full_text_files):
            print(f"  - {basename}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Categorize HTML files as full-text vs abstract-only"
    )
    parser.add_argument(
        "--html-dir",
        type=Path,
        default=Path("data/raw_html"),
        help="Directory containing HTML files (default: data/raw_html)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/html_categorization_results.csv"),
        help="Output CSV path (default: data/html_categorization_results.csv)",
    )
    parser.add_argument(
        "--include-arxiv",
        action="store_true",
        help="Include arxiv_*.html files (excluded by default)",
    )

    args = parser.parse_args()

    # Validate input directory
    if not args.html_dir.exists():
        print(f"Error: HTML directory not found: {args.html_dir}")
        return 1

    print(f"Analyzing HTML files in: {args.html_dir}")
    print(f"Excluding arxiv files: {not args.include_arxiv}")
    print("-" * 60)

    # Analyze files
    results = analyze_directory(args.html_dir, exclude_arxiv=not args.include_arxiv)

    # Save results
    save_results(results, args.output)

    # Print summary
    print_summary(results)

    return 0


if __name__ == "__main__":
    exit(main())

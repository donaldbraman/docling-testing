#!/usr/bin/env python3
"""
Flag PDF extractions that need alternative methods.

Detection heuristic:
- If PDF word count < 50% of HTML word count → FLAG for review
- Complete failures (0 words) → CRITICAL
- Partial failures (< 50%) → WARNING

Author: Claude Code
Date: 2025-01-19
"""

import json
from pathlib import Path


def count_words_in_docling(docling_file: Path) -> int:
    """Count total words in Docling extraction (excluding furniture)."""
    with open(docling_file) as f:
        data = json.load(f)

    total_words = 0
    for item in data.get("texts", []):
        if item.get("content_layer") == "furniture":
            continue
        text = item.get("text", "")
        total_words += len(text.split())

    return total_words


def count_words_in_html(html_file: Path) -> int:
    """Count total words in HTML extraction."""
    with open(html_file) as f:
        data = json.load(f)

    return data.get("stats", {}).get("total_words", 0)


def flag_extraction_issues():
    """Check all articles and flag extraction problems."""

    docling_dir = Path("data/v3_data/docling_extraction")
    html_dir = Path("data/v3_data/processed_html")

    # Get all HTML files (our ground truth)
    html_files = sorted(html_dir.glob("*.json"))

    critical_failures = []  # 0 words extracted
    warnings = []  # < 50% extraction
    good = []  # >= 50% extraction

    print("=" * 80)
    print("EXTRACTION QUALITY REPORT")
    print("=" * 80)
    print(f"Checking {len(html_files)} articles...\n")

    for html_file in html_files:
        basename = html_file.stem
        docling_file = docling_dir / f"{basename}.json"

        if not docling_file.exists():
            print(f"⚠️  Skipping {basename}: no Docling extraction found")
            continue

        html_words = count_words_in_html(html_file)
        pdf_words = count_words_in_docling(docling_file)

        # Calculate extraction rate
        extraction_rate = 0 if html_words == 0 else (pdf_words / html_words) * 100

        # Categorize
        if pdf_words == 0:
            critical_failures.append(
                {
                    "basename": basename,
                    "html_words": html_words,
                    "pdf_words": pdf_words,
                    "rate": extraction_rate,
                }
            )
        elif extraction_rate < 50:
            warnings.append(
                {
                    "basename": basename,
                    "html_words": html_words,
                    "pdf_words": pdf_words,
                    "rate": extraction_rate,
                }
            )
        else:
            good.append(
                {
                    "basename": basename,
                    "html_words": html_words,
                    "pdf_words": pdf_words,
                    "rate": extraction_rate,
                }
            )

    # Print results
    print("\n" + "=" * 80)
    print("CRITICAL: Complete Extraction Failures (0 words)")
    print("=" * 80)
    print(f"Count: {len(critical_failures)}\n")

    if critical_failures:
        print("Article                                                      HTML Words  PDF Words")
        print("-" * 80)
        for item in critical_failures:
            print(f"{item['basename']:<60} {item['html_words']:>8}  {item['pdf_words']:>8}")
        print("\n✅ ACTION: Try alternative extraction (PyMuPDF, pdfplumber, OCR)")

    print("\n" + "=" * 80)
    print("WARNING: Partial Extraction Failures (< 50%)")
    print("=" * 80)
    print(f"Count: {len(warnings)}\n")

    if warnings:
        print(
            "Article                                                      HTML Words  PDF Words    Rate"
        )
        print("-" * 90)
        for item in warnings:
            print(
                f"{item['basename']:<60} {item['html_words']:>8}  {item['pdf_words']:>8}  {item['rate']:>6.1f}%"
            )
        print("\n✅ ACTION: Review and potentially re-extract")

    print("\n" + "=" * 80)
    print("GOOD: Adequate Extraction (>= 50%)")
    print("=" * 80)
    print(f"Count: {len(good)}\n")

    # Statistics
    total = len(critical_failures) + len(warnings) + len(good)
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total articles: {total}")
    print(
        f"Critical failures: {len(critical_failures)} ({len(critical_failures) / total * 100:.1f}%)"
    )
    print(f"Warnings: {len(warnings)} ({len(warnings) / total * 100:.1f}%)")
    print(f"Good: {len(good)} ({len(good) / total * 100:.1f}%)")
    print(
        f"\nArticles needing attention: {len(critical_failures) + len(warnings)} ({(len(critical_failures) + len(warnings)) / total * 100:.1f}%)"
    )

    # Save flagged list
    output_file = Path("data/v3_data/flagged_extractions.json")
    output = {
        "critical": critical_failures,
        "warnings": warnings,
        "summary": {
            "total": total,
            "critical_count": len(critical_failures),
            "warning_count": len(warnings),
            "good_count": len(good),
        },
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Flagged articles saved to: {output_file}")


if __name__ == "__main__":
    flag_extraction_issues()

#!/usr/bin/env python3
"""Check if PDF headers are matching in article-only HTML."""

import json
from pathlib import Path

from rapidfuzz import fuzz

CACHE_DIR = Path("data/extraction_cache")
LABELED_HTML_DIR = Path("data/labeled_html")


def load_page_structure(basename: str) -> list[dict]:
    """Load cached page structure."""
    cache_file = CACHE_DIR / f"{basename}_pages.json"

    if not cache_file.exists():
        return []

    with open(cache_file, encoding="utf-8") as f:
        return json.load(f)


def load_labeled_html(basename: str) -> str:
    """Load labeled HTML as normalized text."""
    labeled_file = LABELED_HTML_DIR / f"{basename}.json"

    if not labeled_file.exists():
        return ""

    with open(labeled_file, encoding="utf-8") as f:
        data = json.load(f)

    paragraphs = data.get("paragraphs", [])
    text = " ".join(p["text"] for p in paragraphs)
    return text.lower()


def normalize_header(header: str) -> str:
    """Normalize header text for matching."""
    return header.lower().strip()


def check_headers_in_html():
    """Check if PDF headers match in article HTML."""
    # PDFs with repeated headers
    pdfs_with_headers = [
        "michigan_law_review_citizen_shareholders_the_state_as_a_fiduciary_in_international_investment_law",
        "michigan_law_review_good_cause_for_goodness_sake_a_new_approach_to_notice_and_comment_rulemaking",
        "michigan_law_review_law_enforcement_privilege",
        "michigan_law_review_spending_clause_standing",
        "michigan_law_review_tort_law_in_a_world_of_scarce_compensatory_resources",
    ]

    print("🔍 CHECKING IF PDF HEADERS MATCH IN ARTICLE HTML")
    print("=" * 80)
    print()

    for basename in pdfs_with_headers:
        print(f"PDF: {basename}")
        print("-" * 80)

        # Load page structure
        pages = load_page_structure(basename)
        if not pages:
            print("  ⚠️  No page structure found")
            print()
            continue

        # Load HTML
        html_text = load_labeled_html(basename)
        if not html_text:
            print("  ⚠️  No HTML text found")
            print()
            continue

        # Find repeated first lines
        first_lines = [p["first_line"] for p in pages]
        from collections import Counter

        first_line_counts = Counter(first_lines)

        repeated_headers = [(line, count) for line, count in first_line_counts.items() if count > 1]

        if not repeated_headers:
            print("  ✅ No repeated headers")
            print()
            continue

        # Check each repeated header
        for header, count in repeated_headers:
            norm_header = normalize_header(header)

            # Check exact match
            if norm_header in html_text:
                print("  ❌ HEADER FOUND IN HTML (exact match)")
                print(f"     Header: {header[:100]}...")
                print(f"     Appears {count}x in PDF")
                print()
            else:
                # Check fuzzy match
                # Split HTML into windows
                words = html_text.split()
                window_size = len(norm_header.split()) + 5
                best_score = 0

                for i in range(0, len(words) - window_size, 50):
                    window = " ".join(words[i : i + window_size])
                    score = fuzz.ratio(norm_header, window) / 100.0
                    if score > best_score:
                        best_score = score

                if best_score >= 0.80:
                    print(f"  ⚠️  HEADER LIKELY IN HTML (fuzzy match {best_score:.1%})")
                    print(f"     Header: {header[:100]}...")
                    print(f"     Appears {count}x in PDF")
                    print()
                else:
                    print(f"  ✅ Header NOT in HTML (best match: {best_score:.1%})")
                    print(f"     Header: {header[:100]}...")
                    print(f"     Appears {count}x in PDF")
                    print()


if __name__ == "__main__":
    check_headers_in_html()

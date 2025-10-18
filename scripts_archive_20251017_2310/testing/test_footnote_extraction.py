#!/usr/bin/env python3
"""
Test improved footnote extraction from HTML files.
Tests multiple law review footnote patterns.
"""

import re
from pathlib import Path

from bs4 import BeautifulSoup


def extract_footnotes_new(html_file: Path):
    """
    Extract footnotes using multiple patterns for different law reviews.

    Patterns supported:
    1. Inline footnotes: <cite class="footnote"> (Columbia Law Review)
    2. List footnotes: <li id="footnote-ref-N"> (Harvard Law Review)
    3. Container footnotes: <div class="footnote">, <aside>, etc. (Others)
    """
    # Try multiple encodings
    encodings = ["utf-8", "latin-1", "windows-1252", "iso-8859-1"]
    soup = None

    for encoding in encodings:
        try:
            with open(html_file, encoding=encoding) as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if soup is None:
        print(f"Could not decode {html_file.name}")
        return []

    footnotes = []

    # Pattern 1: Inline <cite class="footnote"> (Columbia Law Review)
    for cite in soup.find_all("cite", class_="footnote"):
        text_span = cite.find("span", class_="footnote-text")
        if text_span:
            text = text_span.get_text(strip=True)
            # Remove footnote number prefix (e.g., "1. " or "1 ")
            text = re.sub(r"^\d+[\.\s]+", "", text)
            if len(text) > 20:
                footnotes.append(
                    {
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "pattern": "inline_cite",
                    }
                )

    # Pattern 2: List items <li id="footnote-ref-N"> (Harvard Law Review)
    for li in soup.find_all("li", id=re.compile(r"footnote-ref-\d+")):
        content = li.find("p", class_="single-article-footnotes-list__item-content")
        if content:
            text = content.get_text(strip=True)
            # Remove footnote number prefix
            text = re.sub(r"^\d+[\.\s]+", "", text)
            if len(text) > 20:
                footnotes.append(
                    {
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "pattern": "list_item",
                    }
                )

    # Pattern 3: Container-based (traditional)
    footnote_containers = [
        ".footnote",
        "aside",
        '[role="note"]',
        ".note",
        "#footnotes",
        "#footnote_wrapper",
    ]
    for selector in footnote_containers:
        for container in soup.select(selector):
            # Skip if already captured by other patterns
            if container.find("cite", class_="footnote") or container.find(
                "li", id=re.compile(r"footnote-ref-")
            ):
                continue

            text = container.get_text(strip=True)
            text = re.sub(r"^\d+[\.\s]+", "", text)
            if len(text) > 20:
                footnotes.append(
                    {
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "pattern": "container",
                    }
                )

    return footnotes


# Test on sample files
base_dir = Path(__file__).parent
html_dir = base_dir / "data" / "raw_html"

test_files = [
    "columbia_law_review_a_right_of_peaceable_assembly.html",
    "harvard_law_review_Background_Principles_And_The_General_Law_Of_Property.html",
    "georgetown_law_journal_a_faster_way_to_yes.html",
]

for filename in test_files:
    filepath = html_dir / filename
    if filepath.exists():
        print(f"\n{'=' * 80}")
        print(f"Testing: {filename}")
        print(f"{'=' * 80}")

        footnotes = extract_footnotes_new(filepath)

        # Count by pattern
        pattern_counts = {}
        for fn in footnotes:
            pattern = fn["pattern"]
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        print(f"\nTotal footnotes found: {len(footnotes)}")
        for pattern, count in pattern_counts.items():
            print(f"  {pattern}: {count}")

        # Show first 3 footnotes
        print("\nFirst 3 footnotes:")
        for i, fn in enumerate(footnotes[:3], 1):
            print(f"  {i}. [{fn['pattern']}] {fn['text']}")
    else:
        print(f"\n⚠️  File not found: {filename}")

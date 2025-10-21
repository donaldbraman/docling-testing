#!/usr/bin/env python3
"""
Parse Docling extraction JSON to extract structured data from repr strings.

Docling output is saved as string representations of Python objects.
This module parses those strings to extract:
- text content
- label (DocItemLabel)
- bounding box coordinates
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractedItem:
    """A single extracted text item with metadata."""

    text: str
    label: str  # e.g., "TEXT", "FOOTNOTE", "SECTION_HEADER"
    page_num: int
    bbox: tuple[float, float, float, float] | None  # (x0, y0, x1, y1)
    original_docling_label: str  # Full label like "DocItemLabel.TEXT: 'text'"


def parse_docling_repr(repr_string: str) -> ExtractedItem | None:
    """
    Parse a Docling object repr string to extract structured data.

    Example input:
        self_ref='#/texts/13' ... label=<DocItemLabel.TEXT: 'text'> ...
        text="Every year, police perform..." ... page_no=2 ...
        bbox=BoundingBox(l=474.57, t=1877.83, r=1441.69, b=1730.34, ...)

    Returns:
        ExtractedItem or None if parsing fails
    """
    # Extract label
    label_match = re.search(r"label=<DocItemLabel\.([A-Z_]+):", repr_string)
    if not label_match:
        return None
    label = label_match.group(1)

    # Extract text content - handle both text= and orig= fields
    # Try text= first (handle both single and double quotes)
    text_match = re.search(r"text='(.*?)'(?:\s+formatting=)", repr_string, re.DOTALL)
    if not text_match:
        text_match = re.search(r'text="(.*?)"(?:\s+formatting=)', repr_string, re.DOTALL)
    if not text_match:
        # Try orig= as fallback
        text_match = re.search(r"orig='(.*?)'(?:\s+text=)", repr_string, re.DOTALL)
    if not text_match:
        text_match = re.search(r'orig="(.*?)"(?:\s+text=)', repr_string, re.DOTALL)

    if not text_match:
        return None
    text = text_match.group(1)

    # Extract page number
    page_match = re.search(r"page_no=(\d+)", repr_string)
    page_num = int(page_match.group(1)) if page_match else 0

    # Extract bounding box
    bbox_match = re.search(
        r"bbox=BoundingBox\(l=([\d.]+),\s*t=([\d.]+),\s*r=([\d.]+),\s*b=([\d.]+)", repr_string
    )
    bbox = None
    if bbox_match:
        l, t, r, b = map(float, bbox_match.groups())
        bbox = (l, t, r, b)

    return ExtractedItem(
        text=text,
        label=label,
        page_num=page_num,
        bbox=bbox,
        original_docling_label=label_match.group(0),
    )


def load_extraction(json_path: Path) -> list[ExtractedItem]:
    """
    Load and parse an extraction JSON file.

    Args:
        json_path: Path to extraction JSON file

    Returns:
        List of parsed ExtractedItem objects
    """
    with open(json_path) as f:
        data = json.load(f)

    texts = data.get("texts", [])
    items = []

    for text_repr in texts:
        item = parse_docling_repr(text_repr)
        if item:
            items.append(item)

    return items


def main():
    """Test the parser on a sample extraction file."""
    test_file = Path(
        "results/ocr_pipeline_evaluation/extractions/harvard_law_review_unwarranted_warrants_baseline_extraction.json"
    )

    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return 1

    print(f"Parsing: {test_file.name}")
    items = load_extraction(test_file)

    print(f"\nTotal items parsed: {len(items)}")
    print("\nFirst 5 items:")
    for i, item in enumerate(items[:5], 1):
        print(f"\n[{i}] {item.label} (page {item.page_num})")
        print(f"    Text: {item.text[:80]}...")
        if item.bbox:
            print(f"    BBox: {item.bbox}")

    # Show label distribution
    from collections import Counter

    label_counts = Counter(item.label for item in items)
    print("\nLabel distribution:")
    for label, count in label_counts.most_common():
        print(f"  {label}: {count}")

    return 0


if __name__ == "__main__":
    exit(main())

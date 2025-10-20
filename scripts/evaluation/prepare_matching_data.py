#!/usr/bin/env python3
"""
Prepare extraction and ground truth data for fuzzy matching.

This module:
1. Loads extraction items (already "line-level" - 111 short fragments)
2. Loads HTML ground truth paragraphs (24 long paragraphs)
3. Prepares both for line-by-line fuzzy matching
"""

import json
from dataclasses import dataclass
from pathlib import Path

# Import our parser
from parse_extraction import load_extraction


@dataclass
class HTMLLine:
    """A line of text from HTML ground truth."""

    text: str
    label: str  # "body-text" or "footnote-text"
    paragraph_index: int  # Which paragraph this came from
    source: str  # "processed_html"


def load_html_ground_truth(pdf_name: str) -> tuple[list[HTMLLine], list[HTMLLine]]:
    """
    Load HTML ground truth and separate into body text and footnotes.

    Args:
        pdf_name: PDF name (without extension)

    Returns:
        Tuple of (body_text_lines, footnote_lines)
    """
    html_file = Path(f"data/v3_data/processed_html/{pdf_name}.json")

    with open(html_file) as f:
        data = json.load(f)

    body_lines = []
    footnote_lines = []

    for para in data.get("paragraphs", []):
        text = para.get("text", "").strip()
        label = para.get("label", "")

        if not text:
            continue

        if label == "body-text":
            body_lines.append(
                HTMLLine(
                    text=text, label=label, paragraph_index=len(body_lines), source="processed_html"
                )
            )
        elif label == "footnote-text":
            footnote_lines.append(
                HTMLLine(
                    text=text,
                    label=label,
                    paragraph_index=len(footnote_lines),
                    source="processed_html",
                )
            )

    return body_lines, footnote_lines


def normalize_text(text: str) -> str:
    """
    Normalize text for fuzzy matching.

    - Lowercase
    - Remove extra whitespace
    - Preserve word boundaries
    """
    # Lowercase
    text = text.lower()

    # Normalize whitespace (collapse multiple spaces)
    import re

    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def main():
    """Test data preparation."""
    # Load extraction
    ext_file = Path(
        "results/ocr_pipeline_evaluation/extractions/harvard_law_review_unwarranted_warrants_baseline_extraction.json"
    )
    items = load_extraction(ext_file)

    print(f"Extraction items: {len(items)}")
    print(f"  TEXT: {sum(1 for i in items if i.label == 'TEXT')}")
    print(f"  FOOTNOTE: {sum(1 for i in items if i.label == 'FOOTNOTE')}")

    # Load HTML ground truth
    body_lines, footnote_lines = load_html_ground_truth("harvard_law_review_unwarranted_warrants")

    print("\nHTML Ground Truth:")
    print(f"  Body text paragraphs: {len(body_lines)}")
    print(f"  Footnote paragraphs: {len(footnote_lines)}")

    # Show fragmentation ratio
    text_items = [i for i in items if i.label == "TEXT"]
    footnote_items = [i for i in items if i.label == "FOOTNOTE"]

    print("\nFragmentation:")
    print(
        f"  Body text: {len(text_items)} extraction items / {len(body_lines)} GT paragraphs = {len(text_items) / len(body_lines):.1f}x"
    )
    print(
        f"  Footnotes: {len(footnote_items)} extraction items / {len(footnote_lines)} GT paragraphs = {len(footnote_items) / len(footnote_lines):.1f}x"
    )

    # Test normalization
    print("\nNormalization test:")
    original = "  Every  Year,   POLICE perform   searches  "
    normalized = normalize_text(original)
    print(f"  Original: '{original}'")
    print(f"  Normalized: '{normalized}'")

    return 0


if __name__ == "__main__":
    exit(main())

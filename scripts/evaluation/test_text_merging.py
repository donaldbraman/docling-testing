#!/usr/bin/env python3
"""
Test if missing paragraphs are actually merged into other text blocks.
"""

import json
import re
from pathlib import Path


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text).strip().lower()


def main():
    """Test if missing text is merged into other blocks."""
    # Load data
    gt_path = Path("data/v3_data/processed_html/usc_law_review_in_the_name_of_accountability.json")
    ocr_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only_baseline_extraction.json"
    )

    with open(gt_path) as f:
        gt_data = json.load(f)

    with open(ocr_path) as f:
        ocr_data = json.load(f)

    # Get the first missing paragraph
    search_text = "Given the growing importance of UE theory and government speech doctrine in both legal and political realms"
    search_normalized = normalize_text(search_text)

    print(f"Searching for: {search_text[:60]}...")
    print(f"\nChecking {len(ocr_data['texts'])} OCR text blocks...\n")

    # Search in OCR blocks
    for i, text_block in enumerate(ocr_data["texts"]):
        text_normalized = normalize_text(text_block)

        # Check if search text appears anywhere in this block
        if search_normalized in text_normalized:
            print(f"✓ FOUND in block {i}!")
            print(f"\nBlock length: {len(text_block)} chars, {len(text_block.split())} words")
            print("\nFull block text:")
            print("-" * 80)
            print(text_block)
            print("-" * 80)
            return

        # Also check for partial matches (first 30 chars)
        if len(search_normalized) > 30:
            partial = search_normalized[:30]
            if partial in text_normalized:
                print(f"✓ Partial match in block {i} (first 30 chars)")
                print("\nBlock preview:")
                print(text_block[:200])
                print("...")

    print("✗ Text not found in any OCR block")
    print("\nThis confirms the text is genuinely missing from OCR, not just merged.")


if __name__ == "__main__":
    main()

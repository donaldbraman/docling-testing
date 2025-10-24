#!/usr/bin/env python3
"""
Search for the test paragraph in different OCR extractions.
"""

import json
import re
from pathlib import Path


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text).strip().lower()


def search_in_extraction(extraction_path: Path, search_text: str, method_name: str):
    """Search for text in extraction JSON."""
    print(f"\n{'=' * 80}")
    print(f"Method: {method_name}")
    print(f"File: {extraction_path.name}")
    print(f"{'=' * 80}")

    if not extraction_path.exists():
        print("✗ File not found")
        return False, None, 0

    with open(extraction_path) as f:
        data = json.load(f)

    texts = data.get("texts", [])
    print(f"Total text blocks: {len(texts)}")

    # Search for the test paragraph
    search_normalized = normalize_text(search_text)
    found = False
    found_in_block = None

    for i, text in enumerate(texts):
        if search_normalized in normalize_text(text):
            found = True
            found_in_block = i
            print(f"\n✓ FOUND test paragraph in block {i}!")
            print("\nBlock preview:")
            print(f"  {text[:300]}...")
            break

    if not found:
        print("\n✗ Test paragraph NOT FOUND")

        # Check for partial matches
        print("\nSearching for partial matches (first 50 chars)...")
        partial = search_normalized[:50]
        found_partial = False

        for i, text in enumerate(texts):
            if partial in normalize_text(text):
                found_partial = True
                print(f"  Partial match in block {i}: {text[:150]}...")

        if not found_partial:
            print("  No partial matches found either")

    return found, found_in_block, len(texts)


def main():
    """Compare OCR methods."""
    # Test paragraph from missing text
    search_text = "Given the growing importance of UE theory and government speech doctrine in both legal and political realms"

    print("=" * 80)
    print("SEARCHING FOR TEST PARAGRAPH IN OCR EXTRACTIONS")
    print("=" * 80)
    print(f"\nTest paragraph: {search_text[:60]}...")

    results_dir = Path("results/ocr_pipeline_test")

    # Test all available extractions
    extractions = [
        (
            results_dir
            / "usc_law_review_in_the_name_of_accountability_image_only_baseline_extraction.json",
            "Baseline (ocrmac)",
        ),
        (
            results_dir
            / "usc_law_review_in_the_name_of_accountability_image_only_ocr_ocrmypdf_extraction.json",
            "OCRmyPDF (Tesseract)",
        ),
        (results_dir / "original_pdf_extraction.json", "Original PDF (native text)"),
    ]

    results = []
    for extraction_path, method_name in extractions:
        found, block_num, total_blocks = search_in_extraction(
            extraction_path, search_text, method_name
        )
        results.append(
            {
                "method": method_name,
                "found": found,
                "block": block_num,
                "total_blocks": total_blocks,
            }
        )

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"{'Method':<35} {'Blocks':<10} {'Test Para Found'}")
    print("-" * 80)

    for result in results:
        found_str = "✓ YES" if result["found"] else "✗ NO"
        print(f"{result['method']:<35} {result['total_blocks']:<10} {found_str}")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    if results[0]["found"] or results[1]["found"]:
        print("At least one OCR method successfully extracted the test paragraph!")
        print("This suggests OCR quality varies between methods.")
    else:
        print("Neither OCR method found the test paragraph.")
        print("This is a fundamental OCR limitation across methods.")

    if results[2]["found"]:
        print("\nThe paragraph IS present in the original PDF with native text.")
        print("This confirms the issue is OCR-related, not source content.")


if __name__ == "__main__":
    main()

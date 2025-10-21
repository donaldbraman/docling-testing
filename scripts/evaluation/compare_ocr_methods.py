#!/usr/bin/env python3
"""
Compare full text output from different OCR methods.

Extracts and diffs the complete text from Docling baseline vs OCRmyPDF.
"""

import argparse
import difflib
import json
import re
from pathlib import Path


def extract_text_from_repr(text_repr: str) -> str:
    """Extract text content from Docling repr string."""
    match = re.search(r"text='([^']*(?:''[^']*)*)'", text_repr)
    return match.group(1).replace("\\'", "'") if match else ""


def load_extraction_text(extraction_path: Path) -> tuple[list[str], str]:
    """Load extraction and return (blocks, full_text).

    Args:
        extraction_path: Path to extraction JSON

    Returns:
        Tuple of (text_blocks, full_text_joined)
    """
    with open(extraction_path) as f:
        data = json.load(f)

    blocks = [extract_text_from_repr(t) for t in data["texts"]]
    full_text = "\n\n".join(blocks)

    return blocks, full_text


def main():
    """Compare OCR method outputs."""
    parser = argparse.ArgumentParser(description="Compare OCR method text outputs")
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline extraction JSON",
    )
    parser.add_argument(
        "--ocrmypdf",
        type=Path,
        required=True,
        help="Path to OCRmyPDF extraction JSON",
    )
    parser.add_argument(
        "--output-diff",
        type=Path,
        default=None,
        help="Output path for diff file (optional)",
    )

    args = parser.parse_args()

    print("=" * 100)
    print("OCR METHOD COMPARISON")
    print("=" * 100)
    print(f"\nBaseline (Docling internal OCR): {args.baseline.name}")
    print(f"OCRmyPDF (Tesseract):            {args.ocrmypdf.name}\n")

    # Load extractions
    baseline_blocks, baseline_text = load_extraction_text(args.baseline)
    ocrmypdf_blocks, ocrmypdf_text = load_extraction_text(args.ocrmypdf)

    # Statistics
    print("-" * 100)
    print("TEXT STATISTICS")
    print("-" * 100)
    print("\nBaseline (Docling):")
    print(f"  Text blocks:   {len(baseline_blocks):,}")
    print(f"  Total chars:   {len(baseline_text):,}")
    print(f"  Total words:   {len(baseline_text.split()):,}")

    print("\nOCRmyPDF (Tesseract):")
    print(f"  Text blocks:   {len(ocrmypdf_blocks):,}")
    print(f"  Total chars:   {len(ocrmypdf_text):,}")
    print(f"  Total words:   {len(ocrmypdf_text.split()):,}")

    # Comparison
    char_diff = len(ocrmypdf_text) - len(baseline_text)
    char_diff_pct = 100 * char_diff / len(baseline_text) if len(baseline_text) > 0 else 0

    print("\nDifference:")
    print(f"  Character count: {char_diff:+,} ({char_diff_pct:+.1f}%)")
    print(f"  Block count:     {len(ocrmypdf_blocks) - len(baseline_blocks):+,}")

    # Generate unified diff
    print("\n" + "=" * 100)
    print("TEXT DIFF (first 100 lines)")
    print("=" * 100)

    baseline_lines = baseline_text.split("\n")
    ocrmypdf_lines = ocrmypdf_text.split("\n")

    diff = difflib.unified_diff(
        baseline_lines,
        ocrmypdf_lines,
        fromfile="baseline_docling",
        tofile="ocrmypdf_tesseract",
        lineterm="",
    )

    diff_lines = list(diff)

    # Show first 100 lines of diff
    for line in diff_lines[:100]:
        print(line)

    if len(diff_lines) > 100:
        print(f"\n... ({len(diff_lines) - 100} more diff lines)")

    # Save full diff if requested
    if args.output_diff:
        with open(args.output_diff, "w") as f:
            f.write("\n".join(diff_lines))
        print(f"\n✓ Full diff saved to: {args.output_diff}")

    # Similarity metrics
    from rapidfuzz import fuzz

    similarity = fuzz.ratio(baseline_text, ocrmypdf_text)

    print("\n" + "=" * 100)
    print("SIMILARITY METRICS")
    print("=" * 100)
    print(f"\nFuzzy similarity (fuzz.ratio): {similarity:.1f}%")

    if similarity >= 95:
        print("  ✓ Very high similarity - methods produce nearly identical output")
    elif similarity >= 85:
        print("  ✓ High similarity - minor differences in OCR quality")
    elif similarity >= 70:
        print("  ⚠️  Moderate similarity - notable differences in OCR quality")
    else:
        print("  ✗ Low similarity - significant differences in OCR output")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Compare HTML ground truth body text vs Docling OCR output.

Usage:
  python3 scripts/evaluation/compare_ground_truth_vs_ocr.py
"""

import json
import re
from pathlib import Path


def load_json(path: Path) -> dict:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main():
    """Compare ground truth vs OCR."""
    # Paths
    ground_truth_path = Path(
        "data/v3_data/processed_html/usc_law_review_in_the_name_of_accountability.json"
    )
    ocr_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only_baseline_extraction.json"
    )
    output_path = Path("results/ground_truth_vs_ocr_diff.txt")

    print("Loading ground truth...")
    gt_data = load_json(ground_truth_path)

    print("Loading Docling OCR output...")
    ocr_data = load_json(ocr_path)

    # Extract body text from ground truth
    body_paragraphs = [p["text"] for p in gt_data["paragraphs"] if p.get("label") == "body-text"]

    # Get Docling texts
    ocr_texts = ocr_data.get("texts", [])

    # Concatenate to full text
    gt_full = " ".join(body_paragraphs)
    ocr_full = " ".join(ocr_texts)

    # Normalize
    gt_normalized = normalize_text(gt_full)
    ocr_normalized = normalize_text(ocr_full)

    # Calculate stats
    gt_words = len(gt_normalized.split())
    ocr_words = len(ocr_normalized.split())
    gt_chars = len(gt_normalized)
    ocr_chars = len(ocr_normalized)

    # Calculate similarity (simple)
    from difflib import SequenceMatcher

    similarity = SequenceMatcher(None, gt_normalized, ocr_normalized).ratio()

    print(f"\n{'=' * 80}")
    print("GROUND TRUTH vs OCR COMPARISON")
    print(f"{'=' * 80}\n")

    print("Ground Truth (HTML body-text):")
    print(f"  Paragraphs: {len(body_paragraphs)}")
    print(f"  Words: {gt_words:,}")
    print(f"  Characters: {gt_chars:,}\n")

    print("Docling OCR:")
    print(f"  Text blocks: {len(ocr_texts)}")
    print(f"  Words: {ocr_words:,}")
    print(f"  Characters: {ocr_chars:,}\n")

    print("Difference:")
    print(
        f"  Words: {abs(gt_words - ocr_words):,} ({abs(gt_words - ocr_words) / gt_words * 100:.1f}%)"
    )
    print(
        f"  Characters: {abs(gt_chars - ocr_chars):,} ({abs(gt_chars - ocr_chars) / gt_chars * 100:.1f}%)"
    )
    print(f"  Similarity: {similarity * 100:.1f}%\n")

    # Generate diff
    print("Generating character-level diff...")
    from difflib import unified_diff

    # Split into lines for diff (every 100 words)
    words_per_line = 100
    gt_lines = []
    ocr_lines = []

    gt_words_list = gt_normalized.split()
    ocr_words_list = ocr_normalized.split()

    for i in range(0, len(gt_words_list), words_per_line):
        gt_lines.append(" ".join(gt_words_list[i : i + words_per_line]))

    for i in range(0, len(ocr_words_list), words_per_line):
        ocr_lines.append(" ".join(ocr_words_list[i : i + words_per_line]))

    diff = unified_diff(
        gt_lines,
        ocr_lines,
        fromfile="Ground_Truth_HTML_Body_Text",
        tofile="Docling_OCR_Output",
        lineterm="",
        n=1,  # Context lines
    )

    # Save diff
    with open(output_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("GROUND TRUTH (HTML) vs DOCLING OCR COMPARISON\n")
        f.write("=" * 80 + "\n\n")

        f.write("Ground Truth Source: HTML body-text paragraphs from Westlaw\n")
        f.write("OCR Source: Docling OCR on image-only PDF (ocrmac engine)\n\n")

        f.write("STATISTICS:\n")
        f.write("-" * 80 + "\n")
        f.write(
            f"Ground Truth: {gt_words:,} words, {gt_chars:,} chars, {len(body_paragraphs)} paragraphs\n"
        )
        f.write(
            f"Docling OCR:  {ocr_words:,} words, {ocr_chars:,} chars, {len(ocr_texts)} text blocks\n"
        )
        f.write(
            f"Difference:   {abs(gt_words - ocr_words):,} words ({abs(gt_words - ocr_words) / gt_words * 100:.1f}%), "
        )
        f.write(
            f"{abs(gt_chars - ocr_chars):,} chars ({abs(gt_chars - ocr_chars) / gt_chars * 100:.1f}%)\n"
        )
        f.write(f"Similarity:   {similarity * 100:.1f}%\n\n")

        f.write("=" * 80 + "\n")
        f.write("UNIFIED DIFF (100 words per line)\n")
        f.write("=" * 80 + "\n\n")

        f.write("\n".join(diff))

    print(f"✓ Diff saved to: {output_path}")


if __name__ == "__main__":
    main()

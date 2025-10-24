#!/usr/bin/env python3
"""
Compare the last words in HTML ground truth vs PDF extraction.

For documents with over-extraction, this helps identify if the problem
is repeated reading of footers/page numbers or other duplication patterns.
"""

import json
from pathlib import Path

from docling_testing import create_image_only_pdf, create_ocr_converter


def get_ground_truth_words(
    json_path: Path, last_n: int = 100, label_filter: str | None = None
) -> list[str]:
    """Get last N words from ground truth.

    Args:
        json_path: Path to ground truth JSON
        last_n: Number of words to extract from end
        label_filter: If provided, only include paragraphs with this label (e.g., "body-text", "footnote-text")
    """
    with open(json_path) as f:
        data = json.load(f)

    # Collect text, optionally filtered by label
    all_text = []
    for para in data.get("paragraphs", []):
        # Apply label filter if specified
        if label_filter and para.get("label") != label_filter:
            continue

        text = para.get("text", "").strip()
        if text:
            all_text.append(text)

    # Join and extract words
    full_text = " ".join(all_text)
    words = full_text.split()

    return words[-last_n:] if len(words) >= last_n else words


def get_ocr_words(doc, last_n: int = 100) -> list[str]:
    """Get last N words from OCR extraction."""
    # Collect all text
    all_text = []
    if doc.document.texts:
        for item in doc.document.texts:
            if item.text:
                all_text.append(item.text.strip())

    # Join and extract words
    full_text = " ".join(all_text)
    words = full_text.split()

    return words[-last_n:] if len(words) >= last_n else words


def analyze_last_words(pdf_name: str, last_n: int = 100):
    """Compare last words for a PDF with over-extraction."""

    print(f"\n{'=' * 80}")
    print(f"Analyzing: {pdf_name}")
    print(f"{'=' * 80}")

    # Paths
    pdf_path = Path(f"data/v3_data/raw_pdf/{pdf_name}.pdf")
    gt_path = Path(f"data/v3_data/processed_html/{pdf_name}.json")
    img_pdf_path = Path(f"results/ocr_engine_comparison/{pdf_name}_image_only.pdf")

    # Get ground truth last words - ALL, body-text, and footnote-text
    print(f"\n[1/3] Loading ground truth last {last_n} words...")
    gt_all_words = get_ground_truth_words(gt_path, last_n, label_filter=None)
    gt_body_words = get_ground_truth_words(gt_path, last_n, label_filter="body-text")
    gt_fn_words = get_ground_truth_words(gt_path, last_n, label_filter="footnote-text")

    print(f"  All text: {len(gt_all_words)} words")
    print(f"  Body text only: {len(gt_body_words)} words")
    print(f"  Footnote text only: {len(gt_fn_words)} words")

    # Check if image PDF exists, create if needed
    if not img_pdf_path.exists():
        print("\n[2/3] Creating image-only PDF (not cached)...")
        create_image_only_pdf(pdf_path, img_pdf_path, dpi=300, grayscale=True)
    else:
        print("\n[2/3] Using cached image-only PDF")

    # Run OCR
    print("\n[3/3] Running OCR with ocrmac...")
    converter = create_ocr_converter("ocrmac")
    doc = converter.convert(str(img_pdf_path))
    ocr_words = get_ocr_words(doc, last_n)
    print(f"  OCR extracted: {len(ocr_words)} words")
    print(f"  Last 20 words: {' '.join(ocr_words[-20:])}")

    # Compare endings
    print(f"\n{'=' * 80}")
    print("COMPARISON: OCR vs Ground Truth Sections")
    print(f"{'=' * 80}")

    ocr_last_20 = set(ocr_words[-20:])

    # Compare against ALL text
    print("\n[1] OCR vs ALL Ground Truth Text:")
    gt_all_last_20 = set(gt_all_words[-20:])
    common_all = gt_all_last_20 & ocr_last_20
    print(f"  Common words: {len(common_all)}/20")
    print(f"  GT last 20: {' '.join(gt_all_words[-20:])}")

    # Compare against BODY TEXT only
    print("\n[2] OCR vs Body Text Only:")
    gt_body_last_20 = set(gt_body_words[-20:])
    common_body = gt_body_last_20 & ocr_last_20
    print(f"  Common words: {len(common_body)}/20")
    print(f"  GT last 20: {' '.join(gt_body_words[-20:])}")

    # Compare against FOOTNOTE TEXT only
    print("\n[3] OCR vs Footnote Text Only:")
    gt_fn_last_20 = set(gt_fn_words[-20:])
    common_fn = gt_fn_last_20 & ocr_last_20
    print(f"  Common words: {len(common_fn)}/20")
    print(f"  GT last 20: {' '.join(gt_fn_words[-20:])}")

    # Show full last 100 words
    print(f"\n{'=' * 80}")
    print(f"FULL LAST {last_n} WORDS")
    print(f"{'=' * 80}")

    print(f"\nOCR Extraction ({len(ocr_words)} words):")
    print(" ".join(ocr_words))

    print(f"\nGround Truth - ALL ({len(gt_all_words)} words):")
    print(" ".join(gt_all_words))

    print(f"\nGround Truth - Body Text Only ({len(gt_body_words)} words):")
    print(" ".join(gt_body_words))

    print(f"\nGround Truth - Footnote Text Only ({len(gt_fn_words)} words):")
    print(" ".join(gt_fn_words))


def main():
    """Compare last words for over-extraction cases."""

    print("=" * 80)
    print("LAST WORDS COMPARISON - Over-Extraction Analysis")
    print("=" * 80)

    # Analyze both over-extraction cases
    pdfs = [
        "policing_campus_protest",  # 3.1x over-extraction
        "overbroad_protest_laws",  # 4.8x over-extraction
    ]

    for pdf in pdfs:
        analyze_last_words(pdf, last_n=100)

    print(f"\n{'=' * 80}")
    print("ANALYSIS COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()

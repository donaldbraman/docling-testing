#!/usr/bin/env python3
"""
Generate detailed report of missing paragraphs from Docling OCR.
"""

import json
import re
from pathlib import Path


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text).lower()


def is_para_in_docling(para_text: str, docling_text_normalized: str) -> bool:
    """Check if paragraph exists in Docling OCR."""
    normalized = normalize_text(para_text)

    # Check if first 50 chars appear in Docling
    sample = normalized[:50] if len(normalized) > 50 else normalized

    return sample in docling_text_normalized


def main():
    """Generate missing paragraphs report."""
    # Paths
    gt_path = Path("data/v3_data/processed_html/usc_law_review_in_the_name_of_accountability.json")
    docling_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only_baseline_extraction.json"
    )
    output_path = Path("results/missing_paragraphs_report.txt")

    print("Loading data...")

    # Load ground truth
    with open(gt_path) as f:
        gt_data = json.load(f)

    # Load Docling OCR
    with open(docling_path) as f:
        docling_data = json.load(f)

    # Normalize Docling text
    docling_text = " ".join(docling_data["texts"])
    docling_normalized = normalize_text(docling_text)

    # Classify paragraphs
    found_paras = []
    missing_paras = []

    for para in gt_data["paragraphs"]:
        if is_para_in_docling(para["text"], docling_normalized):
            found_paras.append(para)
        else:
            missing_paras.append(para)

    # Calculate statistics
    from collections import Counter

    missing_labels = Counter(p.get("label", "unknown") for p in missing_paras)
    missing_words = sum(len(p["text"].split()) for p in missing_paras)
    found_words = sum(len(p["text"].split()) for p in found_paras)

    # Generate report
    with open(output_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("MISSING PARAGRAPHS REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write("Document: usc_law_review_in_the_name_of_accountability.pdf\n")
        f.write("Ground Truth: Westlaw HTML\n")
        f.write("OCR: Docling (ocrmac engine) on image-only PDF\n\n")

        f.write("SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total paragraphs in ground truth: {len(gt_data['paragraphs'])}\n")
        f.write(
            f"Found in Docling OCR: {len(found_paras)} ({len(found_paras) / len(gt_data['paragraphs']) * 100:.1f}%)\n"
        )
        f.write(
            f"Missing from Docling OCR: {len(missing_paras)} ({len(missing_paras) / len(gt_data['paragraphs']) * 100:.1f}%)\n\n"
        )

        f.write(f"Words found: {found_words:,}\n")
        f.write(f"Words missing: {missing_words:,}\n")
        f.write(f"Total words: {found_words + missing_words:,}\n\n")

        f.write("MISSING BY LABEL\n")
        f.write("-" * 80 + "\n")
        for label, count in sorted(missing_labels.items()):
            total_label = len([p for p in gt_data["paragraphs"] if p.get("label") == label])
            pct = count / total_label * 100 if total_label > 0 else 0
            f.write(f"{label}: {count}/{total_label} ({pct:.1f}%)\n")

        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("MISSING PARAGRAPHS DETAIL\n")
        f.write("=" * 80 + "\n\n")

        for i, para in enumerate(missing_paras, 1):
            label = para.get("label", "unknown")
            text = para["text"]
            word_count = len(text.split())

            f.write(f"[{i}/{len(missing_paras)}] {label.upper()} ({word_count} words)\n")
            f.write("-" * 80 + "\n")
            f.write(text[:500])
            if len(text) > 500:
                f.write("...")
            f.write("\n\n")

    print(f"\n✓ Report saved to: {output_path}")
    print("\nSummary:")
    print(f"  Total paragraphs: {len(gt_data['paragraphs'])}")
    print(
        f"  Found: {len(found_paras)} ({len(found_paras) / len(gt_data['paragraphs']) * 100:.1f}%)"
    )
    print(
        f"  Missing: {len(missing_paras)} ({len(missing_paras) / len(gt_data['paragraphs']) * 100:.1f}%)"
    )
    print(f"\n  Words found: {found_words:,}")
    print(f"  Words missing: {missing_words:,}")
    print("\nMissing by label:")
    for label, count in sorted(missing_labels.items()):
        total_label = len([p for p in gt_data["paragraphs"] if p.get("label") == label])
        pct = count / total_label * 100 if total_label > 0 else 0
        print(f"  {label}: {count}/{total_label} ({pct:.1f}%)")


if __name__ == "__main__":
    main()

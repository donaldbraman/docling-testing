#!/usr/bin/env python3
"""
Test fixed baseline (with one-to-one enforcement) on Amazon paper.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fuzzy_matcher import match_all_lines_with_locality
from parse_extraction import ExtractedItem
from prepare_matching_data import load_html_ground_truth


def extract_line_level_items(pdf_path: Path) -> list[ExtractedItem]:
    """Extract line-level text from PDF."""
    import fitz

    doc = fitz.open(pdf_path)
    items = []

    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                text = " ".join([span["text"] for span in line["spans"]])
                bbox = line["bbox"]

                if text.strip():
                    items.append(
                        ExtractedItem(
                            text=text.strip(),
                            label="TEXT",
                            page_num=page_num,
                            bbox=bbox,
                            original_docling_label="DocItemLabel.TEXT",
                        )
                    )

    doc.close()
    return items


def calculate_metrics(matches, body_html, footnote_html):
    """Calculate precision, recall, F1 for body and footnote."""
    body_html_texts = {h.text for h in body_html}
    footnote_html_texts = {h.text for h in footnote_html}

    # Body metrics
    body_tp = sum(
        1
        for m in matches
        if m.matched_html
        and m.matched_html.text in body_html_texts
        and m.corrected_label == "body-text"
    )
    body_fp = sum(
        1
        for m in matches
        if m.matched_html
        and m.matched_html.text in footnote_html_texts
        and m.corrected_label == "body-text"
    )
    body_fn = len(body_html) - body_tp

    body_precision = body_tp / (body_tp + body_fp) if (body_tp + body_fp) > 0 else 0.0
    body_recall = body_tp / (body_tp + body_fn) if (body_tp + body_fn) > 0 else 0.0
    body_f1 = (
        2 * (body_precision * body_recall) / (body_precision + body_recall)
        if (body_precision + body_recall) > 0
        else 0.0
    )

    # Footnote metrics
    footnote_tp = sum(
        1
        for m in matches
        if m.matched_html
        and m.matched_html.text in footnote_html_texts
        and m.corrected_label == "footnote-text"
    )
    footnote_fp = sum(
        1
        for m in matches
        if m.matched_html
        and m.matched_html.text in body_html_texts
        and m.corrected_label == "footnote-text"
    )
    footnote_fn = len(footnote_html) - footnote_tp

    footnote_precision = (
        footnote_tp / (footnote_tp + footnote_fp) if (footnote_tp + footnote_fp) > 0 else 0.0
    )
    footnote_recall = (
        footnote_tp / (footnote_tp + footnote_fn) if (footnote_tp + footnote_fn) > 0 else 0.0
    )
    footnote_f1 = (
        2 * (footnote_precision * footnote_recall) / (footnote_precision + footnote_recall)
        if (footnote_precision + footnote_recall) > 0
        else 0.0
    )

    macro_f1 = (body_f1 + footnote_f1) / 2.0

    return {
        "body_precision": body_precision,
        "body_recall": body_recall,
        "body_f1": body_f1,
        "footnote_precision": footnote_precision,
        "footnote_recall": footnote_recall,
        "footnote_f1": footnote_f1,
        "macro_f1": macro_f1,
    }


def main():
    """Test fixed baseline on Amazon paper."""
    pdf_name = "california_law_review_amazon-trademark"
    threshold = 0.3

    print("=" * 80)
    print(f"TESTING FIXED BASELINE ON: {pdf_name}")
    print("=" * 80)

    # Find PDF
    pdf_path = None
    for pdf_dir in [Path("data/v3_data/raw_pdf"), Path("data/raw_pdf")]:
        candidate = pdf_dir / f"{pdf_name}.pdf"
        if candidate.exists():
            pdf_path = candidate
            break

    if not pdf_path:
        print("❌ PDF not found")
        return 1

    # Load data
    print("\n📂 Loading data...")
    items = extract_line_level_items(pdf_path)
    body_html, footnote_html = load_html_ground_truth(pdf_name)

    print(f"  PDF lines: {len(items)}")
    print(f"  Body HTML ground truth: {len(body_html)} items")
    print(f"  Footnote HTML ground truth: {len(footnote_html)} items")

    # Test baseline WITHOUT one-to-one enforcement (old behavior)
    print("\n🔄 Running BASELINE (old, allows duplicates)...")
    old_matches = match_all_lines_with_locality(
        items, body_html, footnote_html, threshold, enforce_one_to_one=False
    )
    old_metrics = calculate_metrics(old_matches, body_html, footnote_html)

    old_body = sum(1 for m in old_matches if m.corrected_label == "body-text")
    old_footnote = sum(1 for m in old_matches if m.corrected_label == "footnote-text")
    old_unmatched = sum(1 for m in old_matches if m.matched_html is None)

    # Test baseline WITH one-to-one enforcement (new behavior)
    print("\n🔄 Running BASELINE (fixed, one-to-one)...")
    new_matches = match_all_lines_with_locality(
        items, body_html, footnote_html, threshold, enforce_one_to_one=True
    )
    new_metrics = calculate_metrics(new_matches, body_html, footnote_html)

    new_body = sum(1 for m in new_matches if m.corrected_label == "body-text")
    new_footnote = sum(1 for m in new_matches if m.corrected_label == "footnote-text")
    new_unmatched = sum(1 for m in new_matches if m.matched_html is None)

    # Compare results
    print("\n" + "=" * 80)
    print("RESULTS COMPARISON")
    print("=" * 80)

    print("\n📊 BASELINE (old, allows duplicates):")
    print(
        f"  Body F1:     {old_metrics['body_f1']:.3f} (P={old_metrics['body_precision']:.3f}, R={old_metrics['body_recall']:.3f})"
    )
    print(
        f"  Footnote F1: {old_metrics['footnote_f1']:.3f} (P={old_metrics['footnote_precision']:.3f}, R={old_metrics['footnote_recall']:.3f})"
    )
    print(f"  Macro F1:    {old_metrics['macro_f1']:.3f}")
    print(f"  Assignments: {old_body} body, {old_footnote} footnote, {old_unmatched} unmatched")

    print("\n📊 BASELINE (fixed, one-to-one):")
    print(
        f"  Body F1:     {new_metrics['body_f1']:.3f} (P={new_metrics['body_precision']:.3f}, R={new_metrics['body_recall']:.3f})"
    )
    print(
        f"  Footnote F1: {new_metrics['footnote_f1']:.3f} (P={new_metrics['footnote_precision']:.3f}, R={new_metrics['footnote_recall']:.3f})"
    )
    print(f"  Macro F1:    {new_metrics['macro_f1']:.3f}")
    print(f"  Assignments: {new_body} body, {new_footnote} footnote, {new_unmatched} unmatched")

    # Delta
    print("\n📈 IMPACT OF ONE-TO-ONE ENFORCEMENT:")
    print(f"  Body F1:     {new_metrics['body_f1'] - old_metrics['body_f1']:+.3f}")
    print(f"  Footnote F1: {new_metrics['footnote_f1'] - old_metrics['footnote_f1']:+.3f}")
    print(f"  Macro F1:    {new_metrics['macro_f1'] - old_metrics['macro_f1']:+.3f}")
    print(f"  Body matches:     {new_body - old_body:+d}")
    print(f"  Footnote matches: {new_footnote - old_footnote:+d}")
    print(f"  Unmatched:        {new_unmatched - old_unmatched:+d}")

    # Check if metrics are valid (F1 <= 1.0)
    print("\n🔍 VALIDATION:")
    if old_metrics["body_f1"] > 1.0 or old_metrics["footnote_f1"] > 1.0:
        print("  ⚠️  OLD baseline has invalid metrics (F1 > 1.0) - confirms duplicate matching bug")
    else:
        print("  ✅ OLD baseline metrics are valid")

    if new_metrics["body_f1"] > 1.0 or new_metrics["footnote_f1"] > 1.0:
        print("  ❌ FIXED baseline still has invalid metrics!")
    else:
        print("  ✅ FIXED baseline metrics are valid (F1 <= 1.0)")

    print("\n" + "=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())

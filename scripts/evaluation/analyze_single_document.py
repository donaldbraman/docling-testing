#!/usr/bin/env python3
"""
Analyze classification results for a single document in detail.

Shows exact counts of TP, FP, FN, TN for body and footnote classifications.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fuzzy_matcher import match_all_lines_with_locality
from parse_extraction import ExtractedItem
from prepare_matching_data import load_html_ground_truth


def extract_line_level_items(pdf_path: Path) -> list:
    """Extract line-level text from PDF as ExtractedItem objects."""
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


def main():
    """Analyze a single document."""
    pdf_name = "michigan_law_review_tort_law_in_a_world_of_scarce_compensatory_resources"
    threshold = 0.3

    print("=" * 80)
    print(f"DETAILED ANALYSIS: {pdf_name}")
    print("=" * 80)

    # Find PDF
    pdf_path = None
    for pdf_dir in [Path("data/v3_data/raw_pdf"), Path("data/raw_pdf")]:
        candidate = pdf_dir / f"{pdf_name}.pdf"
        if candidate.exists():
            pdf_path = candidate
            break

    if not pdf_path:
        print("PDF not found")
        return 1

    # Load data
    print("\n📂 Loading data...")
    items = extract_line_level_items(pdf_path)
    body_html, footnote_html = load_html_ground_truth(pdf_name)

    print(f"  PDF lines: {len(items)}")
    print(f"  Body HTML ground truth: {len(body_html)} items")
    print(f"  Footnote HTML ground truth: {len(footnote_html)} items")

    # Run matching
    print(f"\n🔄 Running baseline matching (threshold={threshold})...")

    class BaselineMatch:
        def __init__(self, fuzzy_match):
            self.extraction_item = fuzzy_match.extraction_item
            self.matched_html = fuzzy_match.matched_html
            self.similarity_score = fuzzy_match.similarity_score
            self.corrected_label = fuzzy_match.corrected_label
            if fuzzy_match.corrected_label == "body-text":
                self.assignment = "body"
            elif fuzzy_match.corrected_label == "footnote-text":
                self.assignment = "footnote"
            else:
                self.assignment = "original"

    raw_matches = match_all_lines_with_locality(items, body_html, footnote_html, threshold)
    matches = [BaselineMatch(m) for m in raw_matches]

    # Detailed classification breakdown
    print("\n" + "=" * 80)
    print("CLASSIFICATION BREAKDOWN")
    print("=" * 80)

    body_classified = [m for m in matches if m.assignment == "body"]
    footnote_classified = [m for m in matches if m.assignment == "footnote"]
    original_classified = [m for m in matches if m.assignment == "original"]

    print("\n📊 PDF Lines Classification:")
    print(f"  Classified as BODY:     {len(body_classified):4d} lines")
    print(f"  Classified as FOOTNOTE: {len(footnote_classified):4d} lines")
    print(f"  No match (ORIGINAL):    {len(original_classified):4d} lines")
    print(f"  Total:                  {len(matches):4d} lines")

    # HTML ground truth usage
    body_html_matched = set()
    footnote_html_matched = set()

    for m in matches:
        if m.matched_html is not None:
            if m.assignment == "body":
                body_html_matched.add(m.matched_html.text)
            elif m.assignment == "footnote":
                footnote_html_matched.add(m.matched_html.text)

    print("\n📊 HTML Ground Truth Usage:")
    print(
        f"  Body HTML matched:     {len(body_html_matched):3d} / {len(body_html)} ({len(body_html_matched) / len(body_html) * 100:.1f}%)"
    )
    print(
        f"  Footnote HTML matched: {len(footnote_html_matched):3d} / {len(footnote_html)} ({len(footnote_html_matched) / len(footnote_html) * 100:.1f}%)"
    )

    # Confusion matrix from HTML perspective
    print("\n" + "=" * 80)
    print("CONFUSION MATRIX (Ground Truth Perspective)")
    print("=" * 80)

    # For each HTML ground truth item, see how PDF lines were classified
    body_html_texts = {h.text for h in body_html}
    footnote_html_texts = {h.text for h in footnote_html}

    # Body HTML classification
    body_gt_as_body = 0  # True Positives for body
    body_gt_as_footnote = 0  # False Negatives for body (classified as footnote)
    body_gt_unmatched = 0  # False Negatives for body (no match)

    for m in matches:
        if m.matched_html and m.matched_html.text in body_html_texts:
            if m.assignment == "body":
                body_gt_as_body += 1
            elif m.assignment == "footnote":
                body_gt_as_footnote += 1

    body_gt_unmatched = len(body_html) - body_gt_as_body - body_gt_as_footnote

    # Footnote HTML classification
    footnote_gt_as_footnote = 0  # True Positives for footnote
    footnote_gt_as_body = 0  # False Positives for body (footnote classified as body)
    footnote_gt_unmatched = 0  # False Negatives for footnote (no match)

    for m in matches:
        if m.matched_html and m.matched_html.text in footnote_html_texts:
            if m.assignment == "footnote":
                footnote_gt_as_footnote += 1
            elif m.assignment == "body":
                footnote_gt_as_body += 1

    footnote_gt_unmatched = len(footnote_html) - footnote_gt_as_footnote - footnote_gt_as_body

    print(f"\n📊 Body HTML Ground Truth ({len(body_html)} items):")
    print(
        f"  ✅ Correctly classified as BODY:      {body_gt_as_body:3d} ({body_gt_as_body / len(body_html) * 100:.1f}%)"
    )
    print(
        f"  ❌ Incorrectly classified as FOOTNOTE: {body_gt_as_footnote:3d} ({body_gt_as_footnote / len(body_html) * 100:.1f}%)"
    )
    print(
        f"  ⚪ No match (unclassified):            {body_gt_unmatched:3d} ({body_gt_unmatched / len(body_html) * 100:.1f}%)"
    )

    print(f"\n📊 Footnote HTML Ground Truth ({len(footnote_html)} items):")
    print(
        f"  ✅ Correctly classified as FOOTNOTE:  {footnote_gt_as_footnote:3d} ({footnote_gt_as_footnote / len(footnote_html) * 100:.1f}%)"
    )
    print(
        f"  ❌ Incorrectly classified as BODY:     {footnote_gt_as_body:3d} ({footnote_gt_as_body / len(footnote_html) * 100:.1f}%)"
    )
    print(
        f"  ⚪ No match (unclassified):            {footnote_gt_unmatched:3d} ({footnote_gt_unmatched / len(footnote_html) * 100:.1f}%)"
    )

    # Calculate FALSE POSITIVE RATE for body classifier
    print("\n" + "=" * 80)
    print("BODY TEXT FALSE POSITIVE ANALYSIS")
    print("=" * 80)

    print("\n⚠️  BODY CLASSIFIER FALSE POSITIVES:")
    print(f"  Footnotes incorrectly classified as body: {footnote_gt_as_body}")
    print(f"  Total actual footnotes in ground truth: {len(footnote_html)}")
    print(f"  False Positive Rate: {footnote_gt_as_body / len(footnote_html) * 100:.1f}%")

    # Show some examples
    if footnote_gt_as_body > 0:
        print("\n📝 Sample footnotes incorrectly classified as body:")
        count = 0
        for m in matches:
            if (
                m.matched_html
                and m.matched_html.text in footnote_html_texts
                and m.assignment == "body"
            ):
                print(f"\n  Match {count + 1}:")
                print(f"    Footnote text: {m.matched_html.text[:100]}...")
                print(f"    Similarity: {m.similarity_score:.3f}")
                count += 1
                if count >= 5:
                    break

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())

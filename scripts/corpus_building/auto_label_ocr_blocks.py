#!/usr/bin/env python3
"""
Auto-label OCR-extracted text blocks using HTML ground truth fuzzy matching.

This is Stage 3 of the active learning pipeline:
1. Load v1 CSV from OCR extraction
2. Load HTML ground truth (body_text + footnotes)
3. Fuzzy match blocks against HTML (80% threshold)
4. Auto-label matched blocks
5. Mark unmatched as NEEDS_REVIEW
6. Output v2_predicted CSV

Usage:
    uv run python scripts/corpus_building/auto_label_ocr_blocks.py --pdf texas_law_review_extraterritoriality-patent-infringement
"""

import argparse
import json
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz


def normalize_text_for_matching(text: str) -> str:
    """Normalize text for fuzzy matching (remove extra whitespace)."""
    import re

    return re.sub(r"\s+", " ", text).strip().lower()


def load_html_ground_truth(pdf_name: str) -> dict:
    """Load HTML ground truth for body_text and footnotes.

    Returns dict with:
        - body_paragraphs: list[str] (individual body paragraphs)
        - footnotes: list[str] (individual footnotes)
    """
    html_path = Path(f"data/v3_data/processed_html/{pdf_name}.json")

    if not html_path.exists():
        return None

    with open(html_path) as f:
        data = json.load(f)

    # Parse paragraphs structure
    paragraphs = data.get("paragraphs", [])

    body_paragraphs = []
    footnotes = []

    for para in paragraphs:
        text = para.get("text", "")
        label = para.get("label", "")

        if label == "body-text":
            body_paragraphs.append(text)
        elif label == "footnote-text":
            footnotes.append(text)

    return {
        "body_paragraphs": body_paragraphs,
        "footnotes": footnotes,
    }


def auto_label_with_html(
    df: pd.DataFrame, html_data: dict, match_threshold: int = 80
) -> pd.DataFrame:
    """Auto-label blocks using fuzzy matching against HTML ground truth.

    Args:
        df: DataFrame with columns [page_number, y_position_normalized, normalized_font_size, text, confidence]
        html_data: Dict with body_paragraphs and footnotes from HTML
        match_threshold: Minimum fuzzy match score (0-100)

    Returns:
        DataFrame with added 'suggested_label' column
    """
    df = df.copy()
    df["suggested_label"] = "NEEDS_REVIEW"
    df["match_score"] = 0.0

    # Normalize HTML paragraphs for matching
    body_paragraphs_normalized = [
        normalize_text_for_matching(p) for p in html_data["body_paragraphs"]
    ]
    footnotes_normalized = [normalize_text_for_matching(fn) for fn in html_data["footnotes"]]

    # Match each block
    for idx, row in df.iterrows():
        block_text = normalize_text_for_matching(row["text"])

        if len(block_text) < 10:  # Skip very short blocks
            continue

        # Try matching against body paragraphs
        best_body_score = 0
        if body_paragraphs_normalized:
            body_scores = [fuzz.partial_ratio(block_text, p) for p in body_paragraphs_normalized]
            best_body_score = max(body_scores) if body_scores else 0

        # Try matching against footnotes
        best_footnote_score = 0
        if footnotes_normalized:
            footnote_scores = [fuzz.partial_ratio(block_text, fn) for fn in footnotes_normalized]
            best_footnote_score = max(footnote_scores) if footnote_scores else 0

        # Assign label based on best match
        if best_body_score >= match_threshold and best_body_score >= best_footnote_score:
            df.at[idx, "suggested_label"] = "body_text"
            df.at[idx, "match_score"] = best_body_score
        elif best_footnote_score >= match_threshold:
            df.at[idx, "suggested_label"] = "footnote"
            df.at[idx, "match_score"] = best_footnote_score

    return df


def apply_positional_heuristics(df: pd.DataFrame) -> pd.DataFrame:
    """Apply positional heuristics to NEEDS_REVIEW blocks.

    Rules:
    - Top of page (y < 0.1) → header
    - Bottom of page 1 (y > 0.9, page=1) → front_matter
    - Bottom of other pages (y > 0.9, page>1) → footnote
    - Large font (normalized_font_size > 1.3) → front_matter
    """
    df = df.copy()

    # Headers at top of page
    mask_header = (df["suggested_label"] == "NEEDS_REVIEW") & (df["y_position_normalized"] < 0.1)
    df.loc[mask_header, "suggested_label"] = "header"

    # Page 1 footers → front_matter
    mask_p1_footer = (
        (df["suggested_label"] == "NEEDS_REVIEW")
        & (df["page_number"] == 1)
        & (df["y_position_normalized"] > 0.9)
    )
    df.loc[mask_p1_footer, "suggested_label"] = "front_matter"

    # Other page footers → footnote
    mask_other_footer = (
        (df["suggested_label"] == "NEEDS_REVIEW")
        & (df["page_number"] > 1)
        & (df["y_position_normalized"] > 0.9)
    )
    df.loc[mask_other_footer, "suggested_label"] = "footnote"

    # Large font → front_matter (titles, headings)
    mask_large_font = (df["suggested_label"] == "NEEDS_REVIEW") & (df["normalized_font_size"] > 1.3)
    df.loc[mask_large_font, "suggested_label"] = "front_matter"

    return df


def main():
    parser = argparse.ArgumentParser(description="Auto-label OCR blocks using HTML ground truth")
    parser.add_argument("--pdf", required=True, help="PDF name (without .pdf extension)")
    parser.add_argument(
        "--dpi", type=int, default=600, help="DPI used for extraction (default: 600)"
    )
    parser.add_argument(
        "--threshold", type=int, default=80, help="Fuzzy match threshold (default: 80)"
    )
    parser.add_argument(
        "--suffix", default="", help="File suffix (e.g., '_pymupdf' for PyMuPDF OCR)"
    )
    args = parser.parse_args()

    # Paths
    input_csv = Path(
        f"results/text_block_extraction/{args.pdf}_{args.dpi}dpi_blocks_v1{args.suffix}.csv"
    )
    output_csv = Path(
        f"results/text_block_extraction/{args.pdf}_{args.dpi}dpi_blocks_v2_predicted{args.suffix}.csv"
    )

    if not input_csv.exists():
        print(f"Error: Input CSV not found: {input_csv}")
        print(f"Run: uv run python scripts/corpus_building/extract_with_ocr.py --pdf {args.pdf}")
        return

    print(f"\n{'=' * 60}")
    print("Auto-Labeling OCR Blocks")
    print(f"{'=' * 60}")
    print(f"PDF: {args.pdf}")
    print(f"Input: {input_csv.name}")
    print()

    # Load OCR blocks
    print("[Stage 1] Loading OCR blocks...")
    df = pd.read_csv(input_csv)
    print(f"  ✓ Loaded {len(df):,} blocks")

    # Load HTML ground truth
    print("\n[Stage 2] Loading HTML ground truth...")
    html_data = load_html_ground_truth(args.pdf)

    if html_data is None:
        print(f"  ⚠️  No HTML ground truth found for {args.pdf}")
        print("  Skipping fuzzy matching, using positional heuristics only")
        df["suggested_label"] = "NEEDS_REVIEW"
        df["match_score"] = 0.0
    else:
        body_count = len(html_data["body_paragraphs"])
        footnote_count = len(html_data["footnotes"])
        print(f"  ✓ Body paragraphs: {body_count}")
        print(f"  ✓ Footnotes: {footnote_count}")

        # Auto-label with fuzzy matching
        print(f"\n[Stage 3] Fuzzy matching (threshold: {args.threshold}%)...")
        df = auto_label_with_html(df, html_data, args.threshold)

        # Report matching stats
        body_count = len(df[df["suggested_label"] == "body_text"])
        footnote_count = len(df[df["suggested_label"] == "footnote"])
        needs_review = len(df[df["suggested_label"] == "NEEDS_REVIEW"])

        print(f"  ✓ Matched {body_count} body_text blocks")
        print(f"  ✓ Matched {footnote_count} footnote blocks")
        print(f"  ✓ {needs_review} blocks need review ({needs_review / len(df) * 100:.1f}%)")

    # Apply positional heuristics
    print("\n[Stage 4] Applying positional heuristics...")
    df = apply_positional_heuristics(df)

    # Final stats
    label_counts = df["suggested_label"].value_counts()

    print(f"\n{'=' * 60}")
    print("Auto-Labeling Results")
    print(f"{'=' * 60}")
    for label, count in label_counts.items():
        pct = count / len(df) * 100
        print(f"  {label:20s}: {count:4d} ({pct:5.1f}%)")

    # Reorder columns to put suggested_label and match_score at the end
    # Keep all original columns plus the new ones
    original_cols = pd.read_csv(input_csv).columns.tolist()
    new_cols = ["suggested_label", "match_score"]
    column_order = original_cols + [col for col in new_cols if col not in original_cols]
    df = df[column_order]

    # Save to CSV
    df.to_csv(output_csv, index=False)

    print(f"\n✓ Saved to: {output_csv}")
    print()
    print("Next step: Generate visualization (Stage 4)")
    print("  Then manually review and correct labels")


if __name__ == "__main__":
    main()

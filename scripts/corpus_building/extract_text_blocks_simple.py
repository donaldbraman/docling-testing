#!/usr/bin/env python3
"""
Extract text blocks with 4 simple features for classification.

Features:
1. page_number - Absolute page number (1-indexed)
2. y_position_normalized - Vertical position [0.0, 1.0]
3. normalized_font_size - Font size relative to page median
4. text - Text content for ModernBERT

Auto-labels body_text/footnote using HTML matching, marks rest for manual review.

Usage:
    uv run python scripts/corpus_building/extract_text_blocks_simple.py --pdf political_mootness
"""

import argparse
import json
import re
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
import pandas as pd
from rapidfuzz import fuzz


def normalize_text_for_rag(text: str) -> str:
    """Normalize text for RAG: keep only letters, numbers, basic punctuation.

    Keeps:
    - English letters (a-z, A-Z)
    - Numbers (0-9)
    - Basic punctuation: . , ! ? : ; ' " - ( ) / &
    - Legal symbols: § ¶
    - Brackets: [ ] (heading indicators)
    - Accented Latin characters (proper names)
    - Whitespace

    Normalizes:
    - Smart quotes (' ' " ") → straight quotes (' ")
    - Em/en dashes (— –) → hyphen (-)

    Removes:
    - Emoji
    - Control characters
    - Other unicode symbols
    """
    # Normalize smart quotes and dashes
    text = text.replace(""", "'").replace(""", "'")  # U+2018, U+2019 → '
    text = text.replace('"', '"').replace('"', '"')  # U+201C, U+201D → "
    text = text.replace("—", "-").replace("–", "-")  # U+2014, U+2013 → -

    # Remove control characters (keep normal whitespace)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

    # Keep only allowed characters:
    # - Letters (including accented Latin: á é í ó ú ñ ä ö ü etc.)
    # - Numbers
    # - Basic punctuation: . , ! ? : ; ' " - ( ) / &
    # - Legal symbols: § ¶
    # - Brackets: [ ]
    # - Whitespace
    allowed_chars = []
    for char in text:
        # Keep ASCII letters, numbers, basic punctuation, whitespace
        if char.isascii() and (char.isalnum() or char in " .,!?:;'\"-()[]/&\n\t") or char in "§¶":
            allowed_chars.append(char)
        # Keep accented Latin characters (for proper names)
        elif unicodedata.category(char).startswith("L"):  # Letter category
            # Check if it's Latin-based (common in European names)
            try:
                # If it decomposes to Latin base + accent, keep it
                decomposed = unicodedata.normalize("NFD", char)
                if decomposed[0].isascii():
                    allowed_chars.append(char)
            except:
                pass

    text = "".join(allowed_chars)

    # Normalize whitespace (collapse multiple spaces, tabs, newlines)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_text_blocks(pdf_path: Path) -> list[dict]:
    """Extract text blocks with 4 features from PDF.

    Returns list of dicts with: text, page_number, y_position_normalized,
    font_size_raw, normalized_font_size, suggested_label
    """
    doc = fitz.open(pdf_path)
    all_blocks = []

    print(f"\nExtracting from: {pdf_path.name}")
    print(f"Total pages: {len(doc)}")

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_dict = page.get_text("dict")
        page_height = page.rect.height

        # Collect all font sizes on this page for normalization
        page_font_sizes = []
        for block in page_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["size"] > 0:
                            page_font_sizes.append(span["size"])

        # Calculate median font size (body text baseline)
        median_font_size = (
            np.median(page_font_sizes) if page_font_sizes else 10.0
        )  # Default fallback

        # Extract text blocks
        for block in page_dict["blocks"]:
            if "lines" not in block:
                continue  # Skip image blocks

            # Combine all lines in block
            block_text = ""
            block_font_sizes = []

            for line in block["lines"]:
                line_text = ""
                for span in line["spans"]:
                    line_text += span["text"]
                    if span["size"] > 0:
                        block_font_sizes.append(span["size"])
                block_text += line_text + " "

            block_text = block_text.strip()

            # Normalize text for RAG (remove non-standard characters)
            block_text = normalize_text_for_rag(block_text)

            # Skip empty blocks
            if not block_text:
                continue

            # Get bounding box
            bbox = block["bbox"]  # [x0, y0, x1, y1]
            y_top = bbox[1]

            # Calculate features
            y_position_normalized = y_top / page_height if page_height > 0 else 0.0

            # Average font size for this block
            block_font_size = np.mean(block_font_sizes) if block_font_sizes else median_font_size

            # Normalize font size relative to page median
            normalized_font_size = (
                block_font_size / median_font_size if median_font_size > 0 else 1.0
            )

            all_blocks.append(
                {
                    "text": block_text,
                    "page_number": page_num + 1,  # 1-indexed
                    "y_position_normalized": round(y_position_normalized, 4),
                    "font_size_raw": round(block_font_size, 2),
                    "normalized_font_size": round(normalized_font_size, 3),
                    "suggested_label": None,  # To be filled by auto-labeling
                }
            )

    doc.close()

    print(f"Extracted {len(all_blocks)} text blocks")
    return all_blocks


def load_ground_truth(ground_truth_path: Path) -> tuple[list[str], list[str]]:
    """Load ground truth body_text and footnotes.

    Returns: (body_text_list, footnotes_list)
    """
    with open(ground_truth_path) as f:
        gt = json.load(f)

    # Extract body text
    body_texts = [p["text"] for p in gt.get("body_text_paragraphs", [])]

    # Extract footnotes
    footnotes = [fn["text"] for fn in gt.get("footnotes", [])]

    print("\nGround truth loaded:")
    print(f"  Body paragraphs: {len(body_texts)}")
    print(f"  Footnotes: {len(footnotes)}")

    return body_texts, footnotes


def fuzzy_match_text(block_text: str, ground_truth_texts: list[str], threshold: int = 80) -> bool:
    """Check if block_text fuzzy matches any ground truth text.

    Uses rapidfuzz for efficient fuzzy matching.
    """
    for gt_text in ground_truth_texts:
        # Normalize whitespace
        block_normalized = " ".join(block_text.split())
        gt_normalized = " ".join(gt_text.split())

        # Try partial ratio (substring matching)
        score = fuzz.partial_ratio(block_normalized, gt_normalized)
        if score >= threshold:
            return True

    return False


def auto_label_blocks(
    blocks: list[dict], body_texts: list[str], footnotes: list[str], threshold: int = 80
) -> list[dict]:
    """Auto-label blocks using HTML matching.

    Labels:
    - body_text: Matches HTML body paragraphs
    - footnote: Matches HTML footnotes
    - NEEDS_REVIEW: No match found
    """
    print("\nAuto-labeling blocks...")

    label_counts = {"body_text": 0, "footnote": 0, "NEEDS_REVIEW": 0}

    for block in blocks:
        text = block["text"]

        # Check body text match
        if fuzzy_match_text(text, body_texts, threshold):
            block["suggested_label"] = "body_text"
            label_counts["body_text"] += 1
        # Check footnote match
        elif fuzzy_match_text(text, footnotes, threshold):
            block["suggested_label"] = "footnote"
            label_counts["footnote"] += 1
        # Needs manual review
        else:
            block["suggested_label"] = "NEEDS_REVIEW"
            label_counts["NEEDS_REVIEW"] += 1

    print("\nAuto-labeling results:")
    total = len(blocks)
    for label, count in label_counts.items():
        pct = 100 * count / total if total > 0 else 0
        print(f"  {label:20s} {count:5d} ({pct:5.1f}%)")

    return blocks


def main():
    parser = argparse.ArgumentParser(description="Extract text blocks with simple features")
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="PDF name (without .pdf extension)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=80,
        help="Fuzzy matching threshold (0-100, default: 80)",
    )

    args = parser.parse_args()

    # Setup paths
    pdf_path = Path(f"data/v3_data/raw_pdf/{args.pdf}.pdf")
    ground_truth_path = Path(
        f"results/ocr_pipeline_evaluation/ground_truth/{args.pdf}_ground_truth.json"
    )
    output_dir = Path("results/text_block_extraction")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return 1

    if not ground_truth_path.exists():
        print(f"Error: Ground truth not found: {ground_truth_path}")
        return 1

    print("=" * 80)
    print("TEXT BLOCK EXTRACTION WITH SIMPLE FEATURES")
    print("=" * 80)

    # Step 1: Extract text blocks
    blocks = extract_text_blocks(pdf_path)

    # Step 2: Load ground truth
    body_texts, footnotes = load_ground_truth(ground_truth_path)

    # Step 3: Auto-label using fuzzy matching
    blocks = auto_label_blocks(blocks, body_texts, footnotes, args.threshold)

    # Step 4: Save to CSV for manual review (v1 = HTML auto-labeling only)
    output_path = output_dir / f"{args.pdf}_blocks_v1.csv"
    df = pd.DataFrame(blocks)
    df.to_csv(output_path, index=False)

    print(f"\n✓ Saved to: {output_path}")
    print("\nNext steps:")
    print("1. Run predict_and_extract.py to get model predictions (creates v2)")
    print("2. Review v2 predictions in spreadsheet editor")
    print("3. Correct any errors and save as v3_labeled.csv")
    print("4. Use v3_labeled.csv for training")

    # Show sample NEEDS_REVIEW blocks
    needs_review = df[df["suggested_label"] == "NEEDS_REVIEW"]
    if len(needs_review) > 0:
        print(f"\nSample blocks needing review ({len(needs_review)} total):")
        print("-" * 80)
        for idx, row in needs_review.head(5).iterrows():
            print(
                f"Page {row['page_number']}, y={row['y_position_normalized']:.2f}, "
                f"font={row['normalized_font_size']:.2f}x"
            )
            print(f"Text: {row['text'][:100]}...")
            print()

    return 0


if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
"""
Create PDF with color-coded overlays showing text block classifications.

Each text block gets a colored rectangle overlay based on its label:
- body_text: Green
- footnote: Blue
- front_matter: Purple
- header: Yellow/Gold
- footer: Gray
- NEEDS_REVIEW: Red (semi-transparent, not a training class)

Usage:
    uv run python scripts/visualization/visualize_text_block_classes.py --pdf political_mootness
"""

import argparse
from pathlib import Path

import fitz  # PyMuPDF
import pandas as pd

# Color scheme (RGB, 0-1 scale, alpha)
COLORS = {
    "body_text": (0.0, 0.8, 0.0, 0.2),  # Green
    "footnote": (0.0, 0.0, 0.8, 0.2),  # Blue (includes page footers)
    "front_matter": (0.6, 0.0, 0.8, 0.2),  # Purple
    "header": (1.0, 0.8, 0.0, 0.2),  # Yellow/Gold
    "NEEDS_REVIEW": (1.0, 0.0, 0.0, 0.3),  # Red (more opaque)
}


def extract_block_bboxes(pdf_path: Path, blocks_df: pd.DataFrame) -> dict:
    """Match extracted blocks to PDF bboxes by text matching.

    Returns dict: {page_num: [(bbox, label), ...]}
    """
    doc = fitz.open(pdf_path)
    page_blocks = {}

    print("\nMatching blocks to PDF bboxes...")

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_dict = page.get_text("dict")
        page_height = page.rect.height

        # Get blocks for this page from dataframe
        page_df = blocks_df[blocks_df["page_number"] == page_num + 1]

        matched_blocks = []

        # Match PDF blocks to extracted blocks
        for block in page_dict["blocks"]:
            if "lines" not in block:
                continue

            # Get block text
            block_text = ""
            for line in block["lines"]:
                for span in line["spans"]:
                    block_text += span["text"]
                block_text += " "
            block_text = block_text.strip()

            if not block_text:
                continue

            # Find matching row in dataframe
            # Normalize text for comparison
            block_normalized = " ".join(block_text.split())

            for _, row in page_df.iterrows():
                row_normalized = " ".join(str(row["text"]).split())

                # Check if texts match (allow for minor differences)
                if block_normalized[:100] == row_normalized[:100]:  # Match first 100 chars
                    bbox = block["bbox"]  # [x0, y0, x1, y1]
                    label = row["suggested_label"]
                    matched_blocks.append((bbox, label))
                    break

        page_blocks[page_num] = matched_blocks

        if (page_num + 1) % 10 == 0:
            print(f"  Processed {page_num + 1} pages...")

    doc.close()
    return page_blocks


def create_annotated_pdf(pdf_path: Path, blocks_df: pd.DataFrame, output_path: Path):
    """Create annotated PDF with color-coded block overlays."""

    print("\nCreating annotated PDF...")
    print(f"Input: {pdf_path.name}")
    print(f"Output: {output_path.name}")

    # Open source PDF
    doc = fitz.open(pdf_path)

    # Match blocks to PDF
    page_blocks = extract_block_bboxes(pdf_path, blocks_df)

    # Annotate each page
    print("\nAdding color overlays...")
    for page_num in range(len(doc)):
        page = doc[page_num]

        # Add legend on first page
        if page_num == 0:
            add_legend(page)

        # Get blocks for this page
        blocks = page_blocks.get(page_num, [])

        # Draw colored rectangles
        for bbox, label in blocks:
            if label not in COLORS:
                continue

            color = COLORS[label]
            rect = fitz.Rect(bbox)

            # Draw semi-transparent rectangle
            page.draw_rect(
                rect,
                color=color[:3],
                fill=color[:3],
                fill_opacity=color[3],
                width=0.5,
            )

        if (page_num + 1) % 10 == 0:
            print(f"  Annotated {page_num + 1} pages...")

    # Save annotated PDF
    doc.save(output_path)
    doc.close()

    print(f"\n✓ Saved annotated PDF: {output_path}")


def add_legend(page: fitz.Page):
    """Add color legend to top-left corner of page."""

    # Legend box position (top-left)
    x_start = 20
    y_start = 20
    box_width = 15
    box_height = 12
    text_offset = 20

    # White background for legend
    legend_bg = fitz.Rect(
        x_start - 5, y_start - 5, x_start + 200, y_start + len(COLORS) * (box_height + 5) + 10
    )
    page.draw_rect(legend_bg, color=(1, 1, 1), fill=(1, 1, 1), width=0.5)

    # Title
    page.insert_text(
        (x_start, y_start), "Classification Legend:", fontsize=10, fontname="helv", color=(0, 0, 0)
    )

    y_current = y_start + 15

    # Draw each label
    for label, color in COLORS.items():
        # Color box
        rect = fitz.Rect(x_start, y_current, x_start + box_width, y_current + box_height)
        page.draw_rect(rect, color=color[:3], fill=color[:3], fill_opacity=color[3], width=0.5)

        # Label text
        page.insert_text(
            (x_start + text_offset, y_current + 10),
            label,
            fontsize=9,
            fontname="helv",
            color=(0, 0, 0),
        )

        y_current += box_height + 5


def main():
    parser = argparse.ArgumentParser(
        description="Create PDF with color-coded text block classifications"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="PDF name (without .pdf extension)",
    )

    args = parser.parse_args()

    # Setup paths
    pdf_path = Path(f"data/v3_data/raw_pdf/{args.pdf}.pdf")

    # Try to find the most recent version (v3 > v2 > v1)
    extraction_dir = Path("results/text_block_extraction")
    blocks_path = None
    for version in ["v3_labeled", "v2_predicted", "v1"]:
        candidate = extraction_dir / f"{args.pdf}_blocks_{version}.csv"
        if candidate.exists():
            blocks_path = candidate
            break

    if blocks_path is None:
        print(f"Error: No blocks CSV found for {args.pdf}")
        print(f"Looking for: {args.pdf}_blocks_v1.csv, v2_predicted.csv, or v3_labeled.csv")
        return 1

    output_dir = Path("results/text_block_visualization")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{args.pdf}_annotated.pdf"

    print(f"Using: {blocks_path.name}")

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return 1

    if not blocks_path.exists():
        print(f"Error: Blocks CSV not found: {blocks_path}")
        print("Run extract_text_blocks_simple.py first")
        return 1

    print("=" * 80)
    print("TEXT BLOCK VISUALIZATION")
    print("=" * 80)

    # Load blocks
    blocks_df = pd.read_csv(blocks_path)
    print(f"\nLoaded {len(blocks_df)} text blocks")

    # Show label distribution
    print("\nLabel distribution:")
    for label in blocks_df["suggested_label"].unique():
        count = (blocks_df["suggested_label"] == label).sum()
        pct = 100 * count / len(blocks_df)
        color_desc = f"({COLORS.get(label, 'unknown')[:3]})" if label in COLORS else ""
        print(f"  {label:20s} {count:5d} ({pct:5.1f}%) {color_desc}")

    # Create annotated PDF
    create_annotated_pdf(pdf_path, blocks_df, output_path)

    print("\n" + "=" * 80)
    print("VISUALIZATION COMPLETE")
    print("=" * 80)
    print("\nOpen the annotated PDF to review classifications:")
    print(f"  {output_path}")
    print("\n🔴 Red blocks = NEEDS_REVIEW (manual labeling needed)")
    print("🟢 Green blocks = body_text (auto-labeled)")
    print("🔵 Blue blocks = footnote (includes page footers)")
    print("🟣 Purple blocks = front_matter")
    print("🟡 Yellow blocks = header")

    return 0


if __name__ == "__main__":
    exit(main())

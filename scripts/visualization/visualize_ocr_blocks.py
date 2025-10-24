#!/usr/bin/env python3
"""
Generate color-coded PDF overlay for OCR text block classifications.

This is Stage 4 of the active learning pipeline:
1. Load v2_predicted CSV with auto-labels
2. Load original PDF
3. Draw colored rectangles over each text block
4. Save annotated PDF

Color scheme:
- Green: body_text
- Blue: footnote
- Purple: front_matter
- Yellow: header
- Red: NEEDS_REVIEW

Usage:
    uv run python scripts/visualization/visualize_ocr_blocks.py --pdf texas_law_review_extraterritoriality-patent-infringement
"""

import argparse
import sys
from pathlib import Path

import fitz  # PyMuPDF
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utilities.bbox_utils import ocrmac_to_pymupdf

# Color scheme for labels
LABEL_COLORS = {
    "body_text": (0, 1, 0),  # Green
    "footnote": (0, 0, 1),  # Blue
    "front_matter": (0.5, 0, 0.5),  # Purple
    "header": (1, 1, 0),  # Yellow
    "NEEDS_REVIEW": (1, 0, 0),  # Red
}


def create_annotated_pdf(
    original_pdf: Path, blocks_csv: Path, output_pdf: Path, use_pymupdf_coords: bool = False
):
    """Create annotated PDF with color-coded bounding boxes.

    Args:
        original_pdf: Path to original PDF
        blocks_csv: Path to CSV with blocks and labels
        output_pdf: Path to save annotated PDF
        use_pymupdf_coords: If True, coordinates are already in PyMuPDF format (top-origin).
                           If False (default), coordinates are from ocrmac (bottom-origin) and need flipping.
    """
    # Load blocks
    df = pd.read_csv(blocks_csv)

    # Open PDF
    doc = fitz.open(str(original_pdf))

    # Group blocks by page
    blocks_by_page = df.groupby("page_number")

    total_blocks = len(df)
    blocks_drawn = 0

    for page_num, page_blocks in blocks_by_page:
        page_idx = page_num - 1  # Convert to 0-indexed

        if page_idx >= len(doc):
            print(
                f"  Warning: Page {page_num} not found in PDF (skipping {len(page_blocks)} blocks)"
            )
            continue

        page = doc[page_idx]
        page_width = page.rect.width
        page_height = page.rect.height

        # Draw each block
        for _, block in page_blocks.iterrows():
            if use_pymupdf_coords:
                # PyMuPDF OCR: coordinates are already top-origin, just scale
                x0 = block["x0"] * page_width
                y0 = block["y0"] * page_height
                x1 = block["x1"] * page_width
                y1 = block["y1"] * page_height
            else:
                # ocrmac: bottom-origin, needs flipping to PyMuPDF top-origin
                x0, y0, x1, y1 = ocrmac_to_pymupdf(
                    block["x0"], block["y0"], block["x1"], block["y1"], page_width, page_height
                )

            # Create rectangle
            rect = fitz.Rect(x0, y0, x1, y1)

            # Get color for label
            label = block["suggested_label"]
            color = LABEL_COLORS.get(label, (0.5, 0.5, 0.5))  # Gray for unknown

            # Draw rectangle with transparency (border same as fill)
            page.draw_rect(rect, color=color, width=0.5, fill=color, fill_opacity=0.2)

            blocks_drawn += 1

        if (page_num) % 10 == 0:
            print(f"    Page {page_num}/{len(doc)}: {len(page_blocks)} blocks annotated")

    # Print summary before closing
    total_pages = len(doc)
    print(f"\n  ✓ Annotated {blocks_drawn}/{total_blocks} blocks across {total_pages} pages")

    # Save annotated PDF
    doc.save(str(output_pdf))
    doc.close()


def main():
    parser = argparse.ArgumentParser(description="Generate color-coded PDF overlay for text blocks")
    parser.add_argument("--pdf", required=True, help="PDF name (without .pdf extension)")
    parser.add_argument(
        "--dpi", type=int, default=600, help="DPI used for extraction (default: 600)"
    )
    parser.add_argument(
        "--suffix", default="", help="File suffix (e.g., '_pymupdf' for PyMuPDF OCR)"
    )
    args = parser.parse_args()

    # Paths - use image-only PDF since that's what we OCR'd
    image_only_pdf = Path(
        f"results/text_block_extraction/{args.pdf}_image_only_{args.dpi}dpi{args.suffix}.pdf"
    )
    blocks_csv = Path(
        f"results/text_block_extraction/{args.pdf}_{args.dpi}dpi_blocks_v2_predicted{args.suffix}.csv"
    )
    output_pdf = Path(
        f"results/text_block_extraction/{args.pdf}_{args.dpi}dpi_annotated{args.suffix}.pdf"
    )

    if not image_only_pdf.exists():
        print(f"Error: Image-only PDF not found: {image_only_pdf}")
        print(f"Run: uv run python scripts/corpus_building/extract_with_ocr.py --pdf {args.pdf}")
        return

    if not blocks_csv.exists():
        print(f"Error: Blocks CSV not found: {blocks_csv}")
        print(
            f"Run: uv run python scripts/corpus_building/auto_label_ocr_blocks.py --pdf {args.pdf}"
        )
        return

    print(f"\n{'=' * 60}")
    print("Generating Annotated PDF")
    print(f"{'=' * 60}")
    print(f"PDF: {args.pdf}")
    print(f"Input CSV: {blocks_csv.name}")
    print()
    print("Color Legend:")
    print("  🟢 Green  = body_text")
    print("  🔵 Blue   = footnote")
    print("  🟣 Purple = front_matter")
    print("  🟡 Yellow = header")
    print("  🔴 Red    = NEEDS_REVIEW")
    print()

    # Generate annotated PDF
    print("Annotating image-only PDF (what we OCR'd)...")
    # Both PyMuPDF and EasyOCR use top-origin coordinates (y=0 at top)
    # ocrmac uses bottom-origin coordinates (y=0 at bottom)
    use_pymupdf_coords = "_pymupdf" in args.suffix or "_easyocr" in args.suffix
    create_annotated_pdf(image_only_pdf, blocks_csv, output_pdf, use_pymupdf_coords)

    # Print label statistics
    df = pd.read_csv(blocks_csv)
    label_counts = df["suggested_label"].value_counts()

    print(f"\n{'=' * 60}")
    print("Label Distribution")
    print(f"{'=' * 60}")
    for label, count in label_counts.items():
        pct = count / len(df) * 100
        color_name = {
            "body_text": "🟢 Green ",
            "footnote": "🔵 Blue  ",
            "front_matter": "🟣 Purple",
            "header": "🟡 Yellow",
            "NEEDS_REVIEW": "🔴 Red   ",
        }.get(label, "⚪ Gray  ")
        print(f"  {color_name} {label:20s}: {count:4d} ({pct:5.1f}%)")

    print(f"\n✓ Annotated PDF saved to: {output_pdf}")
    print("\nNote: Annotations are on the image-only PDF (what we OCR'd)")
    print("      Bounding boxes now align correctly with the OCR'd text")
    print()
    print("Next steps:")
    print(f"  1. Open: {output_pdf}")
    print("  2. Review 🔴 NEEDS_REVIEW blocks")
    print("  3. Edit CSV to correct labels")
    print(f"  4. Save as: {args.pdf}_{args.dpi}dpi_blocks_v3_labeled.csv")


if __name__ == "__main__":
    main()

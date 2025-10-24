#!/usr/bin/env python3
"""
Generate simple color-coded overlays showing Docling's OCR classifications.

This shows what Docling classified as body text, footnotes, headers, etc.
without any ground truth comparison.
"""

from pathlib import Path

import fitz  # PyMuPDF

from docling_testing import create_image_only_pdf, create_ocr_converter

# Color scheme (RGB 0-255) - matching Docling's classification colors
ITEM_TYPE_COLORS = {
    "TextItem": (0, 0, 255, 80),  # Blue with alpha
    "SectionHeaderItem": (0, 255, 0, 80),  # Green with alpha
    "ListItem": (255, 165, 0, 80),  # Orange with alpha
    "Title": (160, 32, 240, 80),  # Purple with alpha
    "Caption": (255, 255, 0, 80),  # Yellow with alpha
    "Footnote": (255, 0, 0, 80),  # Red with alpha
    "PageHeader": (128, 128, 128, 60),  # Gray with alpha
    "PageFooter": (128, 128, 128, 60),  # Gray with alpha
    "other": (200, 200, 200, 60),  # Light gray with alpha
}


def rgb_to_fitz(rgba):
    """Convert RGBA (0-255) to PyMuPDF format (0-1)."""
    return (rgba[0] / 255, rgba[1] / 255, rgba[2] / 255), rgba[3] / 255


def generate_ocr_overlay(pdf_name: str, engine: str = "ocrmac"):
    """
    Generate color-coded overlay PDF showing Docling's classifications.

    Args:
        pdf_name: PDF basename without extension
        engine: OCR engine to use (ocrmac or tesseract)
    """
    print(f"\n{'=' * 80}")
    print(f"Generating {engine} overlay for: {pdf_name}")
    print(f"{'=' * 80}")

    # Paths
    pdf_path = Path(f"data/v3_data/raw_pdf/{pdf_name}.pdf")
    img_pdf_path = Path(f"results/ocr_engine_comparison/{pdf_name}_image_only.pdf")
    output_path = Path(f"results/ocr_engine_comparison/overlays/{pdf_name}_{engine}_overlay.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return

    # Check if image PDF exists, create if needed
    if not img_pdf_path.exists():
        print("\n[1/3] Creating image-only PDF (300 DPI, grayscale)...")
        create_image_only_pdf(pdf_path, img_pdf_path, dpi=300, grayscale=True)
    else:
        print("\n[1/3] Using cached image-only PDF")

    # Run OCR
    print(f"\n[2/3] Running Docling with {engine}...")
    converter = create_ocr_converter(engine)
    doc = converter.convert(str(img_pdf_path))

    # Count items by type
    item_counts = {}
    for item in doc.document.texts:
        item_type = type(item).__name__
        item_counts[item_type] = item_counts.get(item_type, 0) + 1

    print(f"  Extracted {len(doc.document.texts)} items:")
    for item_type, count in sorted(item_counts.items()):
        print(f"    {item_type}: {count}")

    # Create overlay PDF
    print("\n[3/3] Creating overlay PDF...")
    pdf_doc = fitz.open(img_pdf_path)

    for item in doc.document.texts:
        if not hasattr(item, "prov") or not item.prov:
            continue

        # Get item type for color
        item_type = type(item).__name__
        color_rgba = ITEM_TYPE_COLORS.get(item_type, ITEM_TYPE_COLORS["other"])
        color, alpha = rgb_to_fitz(color_rgba)

        # Get bounding box from first provenance entry
        prov = item.prov[0]
        page_idx = prov.page_no - 1  # Convert to 0-indexed

        if page_idx < 0 or page_idx >= len(pdf_doc):
            continue

        page = pdf_doc[page_idx]
        bbox = prov.bbox

        # Create rectangle
        rect = fitz.Rect(bbox.l, bbox.t, bbox.r, bbox.b)

        # Draw filled rectangle with transparency
        page.draw_rect(rect, fill=color, fill_opacity=alpha)

    # Add legend
    add_legend(pdf_doc[0], engine)

    # Save
    pdf_doc.save(output_path)
    pdf_doc.close()

    print(f"\n✅ Created overlay: {output_path}")


def add_legend(page, engine):
    """Add color legend to page."""
    page_rect = page.rect
    legend_x = page_rect.width - 220
    legend_y = 50

    # White background
    bg_rect = fitz.Rect(legend_x - 10, legend_y - 10, page_rect.width - 10, legend_y + 200)
    page.draw_rect(bg_rect, color=(1, 1, 1), fill=(1, 1, 1), width=1)
    page.draw_rect(bg_rect, color=(0, 0, 0), width=1)

    # Title
    page.insert_text(
        (legend_x, legend_y + 5), f"Docling ({engine})", fontsize=10, fontname="helv", fontfile=None
    )

    # Labels
    y_offset = 20
    for item_type, rgba in ITEM_TYPE_COLORS.items():
        if item_type == "other":
            continue

        box_rect = fitz.Rect(legend_x, legend_y + y_offset, legend_x + 15, legend_y + y_offset + 10)
        color, alpha = rgb_to_fitz(rgba)
        page.draw_rect(box_rect, fill=color, fill_opacity=alpha, width=0.5, color=(0, 0, 0))

        page.insert_text(
            (legend_x + 20, legend_y + y_offset + 8),
            item_type,
            fontsize=8,
            fontname="helv",
            fontfile=None,
        )

        y_offset += 18

    # Add stats note
    page.insert_text(
        (legend_x, legend_y + y_offset + 10),
        "Transparency shows",
        fontsize=7,
        fontname="helv",
        fontfile=None,
    )
    page.insert_text(
        (legend_x, legend_y + y_offset + 20),
        "overlapping boxes",
        fontsize=7,
        fontname="helv",
        fontfile=None,
    )


def main():
    """Generate overlays for middling performers."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate OCR classification overlays")
    parser.add_argument("--pdf", type=str, required=True, help="PDF basename without extension")
    parser.add_argument(
        "--engine", type=str, default="ocrmac", choices=["ocrmac", "tesseract"], help="OCR engine"
    )
    args = parser.parse_args()

    generate_ocr_overlay(args.pdf, args.engine)


if __name__ == "__main__":
    main()

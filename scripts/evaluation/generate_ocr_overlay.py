#!/usr/bin/env python3
"""
Generate color-coded overlays showing Docling's OCR text classifications.

Creates a PDF with transparent colored boxes overlaid on each text region,
colored by Docling's classification (TextItem=blue, Footnote=red, etc.).
"""

from pathlib import Path

import fitz  # PyMuPDF

from docling_testing import create_image_only_pdf, create_ocr_converter


def get_pdf_rect(bbox, page_height: float) -> fitz.Rect:
    """
    Convert Docling bbox to PyMuPDF rectangle.

    Docling uses bottom-left origin (y increases upward).
    PyMuPDF uses top-left origin (y increases downward).

    Args:
        bbox: Docling BoundingBox with l, t, r, b coordinates
        page_height: Height of page in PDF points (72 DPI)

    Returns:
        PyMuPDF Rect with top-left origin coordinates
    """
    # Docling: bottom-left origin, need to flip y-axis
    # PyMuPDF: top-left origin
    # Formula: pdf_y = page_height - docling_y
    pdf_l = bbox.l
    pdf_r = bbox.r
    pdf_t = page_height - bbox.b  # bbox.b is bottom in Docling (higher y)
    pdf_b = page_height - bbox.t  # bbox.t is top in Docling (lower y)

    rect = fitz.Rect(pdf_l, pdf_t, pdf_r, pdf_b)
    rect.normalize()  # Ensure x0 <= x1 and y0 <= y1
    return rect


def draw_colored_boxes(pdf_doc: fitz.Document, items: list, color_map: dict):
    """
    Draw colored transparent boxes over text regions.

    Args:
        pdf_doc: PyMuPDF document to draw on
        items: List of Docling text items with .prov (provenance) attribute
        color_map: Dict mapping item type name to (r, g, b, alpha) tuple (0-255)
    """
    for item in items:
        if not hasattr(item, "prov") or not item.prov:
            continue

        # Get item type for color
        item_type = type(item).__name__
        color_rgba = color_map.get(item_type, color_map["other"])
        color = (color_rgba[0] / 255, color_rgba[1] / 255, color_rgba[2] / 255)
        alpha = color_rgba[3] / 255

        # Draw box for each provenance entry (one per page where text appears)
        for prov in item.prov:
            page_idx = prov.page_no - 1  # Convert to 0-indexed

            if page_idx < 0 or page_idx >= len(pdf_doc):
                continue

            page = pdf_doc[page_idx]
            page_height = page.rect.height  # Get actual page height for y-flip

            # Convert Docling bbox to PyMuPDF rect
            rect = get_pdf_rect(prov.bbox, page_height)

            # Draw filled rectangle with transparency
            page.draw_rect(rect, fill=color, fill_opacity=alpha)


def add_legend(page: fitz.Page, engine: str, color_map: dict):
    """
    Add color legend showing what each color means.

    Args:
        page: PyMuPDF page to draw legend on (usually first page)
        engine: OCR engine name (e.g., "ocrmac")
        color_map: Dict mapping item type to (r, g, b, alpha) tuple
    """
    page_rect = page.rect
    legend_x = page_rect.width - 220
    legend_y = 50

    # White background box
    bg_rect = fitz.Rect(legend_x - 10, legend_y - 10, page_rect.width - 10, legend_y + 200)
    page.draw_rect(bg_rect, color=(1, 1, 1), fill=(1, 1, 1), width=1)
    page.draw_rect(bg_rect, color=(0, 0, 0), width=1)

    # Title
    page.insert_text(
        (legend_x, legend_y + 5), f"Docling ({engine})", fontsize=10, fontname="helv", fontfile=None
    )

    # Color boxes with labels
    y_offset = 20
    for item_type, rgba in color_map.items():
        if item_type == "other":
            continue

        # Draw color box
        box_rect = fitz.Rect(legend_x, legend_y + y_offset, legend_x + 15, legend_y + y_offset + 10)
        color = (rgba[0] / 255, rgba[1] / 255, rgba[2] / 255)
        alpha = rgba[3] / 255
        page.draw_rect(box_rect, fill=color, fill_opacity=alpha, width=0.5, color=(0, 0, 0))

        # Draw label
        page.insert_text(
            (legend_x + 20, legend_y + y_offset + 8),
            item_type,
            fontsize=8,
            fontname="helv",
            fontfile=None,
        )

        y_offset += 18


def generate_overlay(pdf_name: str, engine: str = "ocrmac"):
    """
    Generate color-coded overlay PDF showing Docling classifications.

    Args:
        pdf_name: PDF basename without extension (e.g., "bu_law_review_nil_compliance")
        engine: OCR engine to use ("ocrmac" or "tesseract")
    """
    # Color scheme: item type -> (r, g, b, alpha) all 0-255
    COLOR_MAP = {
        "TextItem": (0, 0, 255, 80),  # Blue
        "SectionHeaderItem": (0, 255, 0, 80),  # Green
        "ListItem": (255, 165, 0, 80),  # Orange
        "Title": (160, 32, 240, 80),  # Purple
        "Caption": (255, 255, 0, 80),  # Yellow
        "Footnote": (255, 0, 0, 80),  # Red
        "PageHeader": (128, 128, 128, 60),  # Gray
        "PageFooter": (128, 128, 128, 60),  # Gray
        "other": (200, 200, 200, 60),  # Light gray
    }

    print(f"\n{'=' * 80}")
    print(f"Generating {engine} overlay: {pdf_name}")
    print(f"{'=' * 80}")

    # Paths
    pdf_path = Path(f"data/v3_data/raw_pdf/{pdf_name}.pdf")
    img_pdf_path = Path(f"results/ocr_engine_comparison/{pdf_name}_image_only.pdf")
    output_path = Path(f"results/ocr_engine_comparison/overlays/{pdf_name}_{engine}_overlay.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return 1

    # Create image-only PDF if needed
    if not img_pdf_path.exists():
        print("\n[1/3] Creating image-only PDF...")
        create_image_only_pdf(pdf_path, img_pdf_path, dpi=300, grayscale=True)
    else:
        print("\n[1/3] Using cached image-only PDF")

    # Run OCR
    print(f"\n[2/3] Running Docling OCR with {engine}...")
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

    # Create overlay
    print("\n[3/3] Creating overlay PDF...")
    pdf_doc = fitz.open(img_pdf_path)

    draw_colored_boxes(pdf_doc, doc.document.texts, COLOR_MAP)
    add_legend(pdf_doc[0], engine, COLOR_MAP)

    pdf_doc.save(output_path)
    pdf_doc.close()

    print(f"\n✅ Overlay saved: {output_path}")
    return 0


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate OCR classification overlays")
    parser.add_argument("--pdf", type=str, required=True, help="PDF basename without extension")
    parser.add_argument(
        "--engine", type=str, default="ocrmac", choices=["ocrmac", "tesseract"], help="OCR engine"
    )
    args = parser.parse_args()

    return generate_overlay(args.pdf, args.engine)


if __name__ == "__main__":
    exit(main())

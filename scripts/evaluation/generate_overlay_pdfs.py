#!/usr/bin/env python3
"""
Generate overlay PDFs showing extraction classifications.

Creates two PDFs:
1. Uncorrected: Shows Docling's original labels
2. Corrected: Shows fuzzy-matched corrected labels
"""

from pathlib import Path

import fitz  # PyMuPDF
from fuzzy_matcher import match_all_items
from parse_extraction import ExtractedItem, load_extraction
from prepare_matching_data import load_html_ground_truth

# Color scheme (RGB 0-255)
LABEL_COLORS = {
    "body-text": (0, 0, 255),  # Blue
    "footnote-text": (255, 0, 0),  # Red
    "section-header": (0, 255, 0),  # Green
    "title": (255, 255, 0),  # Yellow
    "page-header": (128, 128, 128),  # Gray
    "page-footer": (128, 128, 128),  # Gray
    "other": (200, 200, 200),  # Light gray
}

# Map Docling labels to our color scheme
DOCLING_TO_COLOR_LABEL = {
    "TEXT": "other",
    "FOOTNOTE": "other",
    "SECTION_HEADER": "section-header",
    "PAGE_HEADER": "page-header",
    "PAGE_FOOTER": "page-footer",
    "LIST_ITEM": "other",
}

ALPHA = 0.3  # Transparency


def rgb_to_fitz(rgb):
    """Convert RGB (0-255) to PyMuPDF format (0-1)."""
    return (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


def create_overlay_pdf(
    pdf_path: Path,
    items: list[ExtractedItem],
    label_map: dict[int, str],
    output_path: Path,
    title: str,
):
    """
    Create PDF with colored overlays.

    Args:
        pdf_path: Original PDF
        items: List of extraction items
        label_map: Dict mapping item index to label (for corrected version)
        output_path: Output PDF path
        title: "Uncorrected" or "Corrected"
    """
    doc = fitz.open(pdf_path)

    for item_idx, item in enumerate(items):
        if item.bbox is None:
            continue

        # Get label
        if label_map:
            # Corrected version
            label = label_map.get(item_idx, "other")
        else:
            # Uncorrected version - map Docling label
            label = DOCLING_TO_COLOR_LABEL.get(item.label, "other")

        # Get color
        color_label = label if label in LABEL_COLORS else "other"
        color = LABEL_COLORS[color_label]
        fitz_color = rgb_to_fitz(color)

        # Find page (0-indexed in PyMuPDF)
        page_idx = item.page_num - 1
        if page_idx < 0 or page_idx >= len(doc):
            continue

        page = doc[page_idx]

        # Draw rectangle
        # Docling bbox is (left, top, right, bottom) in PDF coordinates
        l, t, r, b = item.bbox
        rect = fitz.Rect(l, t, r, b)

        page.draw_rect(rect, color=fitz_color, fill=fitz_color, width=0.5, fill_opacity=ALPHA)

    # Add legend
    add_legend(doc[0], title)

    # Save
    doc.save(output_path)
    doc.close()

    print(f"✓ Created {title}: {output_path}")


def add_legend(page, title):
    """Add color legend to page."""
    page_rect = page.rect
    legend_x = page_rect.width - 200
    legend_y = 50

    # White background
    bg_rect = fitz.Rect(legend_x - 10, legend_y - 10, page_rect.width - 10, legend_y + 150)
    page.draw_rect(bg_rect, color=(1, 1, 1), fill=(1, 1, 1), width=1)
    page.draw_rect(bg_rect, color=(0, 0, 0), width=1)

    # Title
    page.insert_text((legend_x, legend_y + 5), f"{title} Labels", fontsize=10, fontname="helv")

    # Labels
    y_offset = 20
    for label, color in LABEL_COLORS.items():
        if label == "other":
            continue

        box_rect = fitz.Rect(legend_x, legend_y + y_offset, legend_x + 15, legend_y + y_offset + 10)
        fitz_color = rgb_to_fitz(color)
        page.draw_rect(box_rect, fill=fitz_color, fill_opacity=ALPHA, width=0.5, color=(0, 0, 0))

        page.insert_text(
            (legend_x + 20, legend_y + y_offset + 8), label, fontsize=8, fontname="helv"
        )

        y_offset += 15


def generate_overlay_pdfs(pdf_name: str, output_dir: Path):
    """
    Generate uncorrected and corrected overlay PDFs.

    Args:
        pdf_name: PDF name without extension (e.g., "harvard_law_review_unwarranted_warrants")
        output_dir: Output directory for PDFs
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find PDF
    pdf_path = None
    for pdf_dir in [Path("data/v3_data/raw_pdf"), Path("data/raw_pdf")]:
        candidate = pdf_dir / f"{pdf_name}.pdf"
        if candidate.exists():
            pdf_path = candidate
            break

    if not pdf_path:
        print(f"Error: PDF not found for {pdf_name}")
        return 1

    # Load extraction
    ext_file = Path(
        f"results/ocr_pipeline_evaluation/extractions/{pdf_name}_baseline_extraction.json"
    )
    if not ext_file.exists():
        print(f"Error: Extraction not found: {ext_file}")
        return 1

    items = load_extraction(ext_file)
    print(f"Loaded {len(items)} extraction items from {pdf_name}")

    # Load HTML ground truth
    body_html, footnote_html = load_html_ground_truth(pdf_name)
    print(f"Loaded HTML ground truth: {len(body_html)} body + {len(footnote_html)} footnotes")

    # Perform fuzzy matching
    print("Performing fuzzy matching...")
    matches = match_all_items(items, body_html, footnote_html, threshold=0.75)

    # Create label map for corrected version
    label_map = {}
    matched_count = 0
    for idx, match in enumerate(matches):
        if match.corrected_label:
            label_map[idx] = match.corrected_label
            matched_count += 1

    print(f"Matched {matched_count}/{len(items)} items ({matched_count / len(items) * 100:.1f}%)")

    # Generate uncorrected PDF
    uncorrected_path = output_dir / f"{pdf_name}_baseline_uncorrected.pdf"
    create_overlay_pdf(pdf_path, items, None, uncorrected_path, "Uncorrected")

    # Generate corrected PDF
    corrected_path = output_dir / f"{pdf_name}_baseline_corrected.pdf"
    create_overlay_pdf(pdf_path, items, label_map, corrected_path, "Corrected")

    print("\n✅ Generated overlay PDFs:")
    print(f"   Uncorrected: {uncorrected_path}")
    print(f"   Corrected: {corrected_path}")

    return 0


def main():
    """Generate overlay PDFs for harvard_law_review."""
    output_dir = Path("results/overlay_pdfs")

    result = generate_overlay_pdfs("harvard_law_review_unwarranted_warrants", output_dir)

    return result


if __name__ == "__main__":
    exit(main())

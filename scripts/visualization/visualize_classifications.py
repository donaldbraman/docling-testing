#!/usr/bin/env python3
"""
Visualize semantic classification results by overlaying PDFs with colored semi-transparent boxes.

Generates two PDFs:
1. *_predictions.pdf - Shows Docling's predictions
2. *_groundtruth.pdf - Shows ground truth from HTML

Color scheme:
- body_text: Blue (rgba: 0, 0, 255, 0.3)
- footnote: Red (rgba: 255, 0, 0, 0.3)
- section_header: Green (rgba: 0, 255, 0, 0.3)
- title: Yellow (rgba: 255, 255, 0, 0.3)
- author: Orange (rgba: 255, 165, 0, 0.3)
- abstract: Purple (rgba: 128, 0, 128, 0.3)
- other: Gray (rgba: 128, 128, 128, 0.3)
"""

import argparse
import json
from pathlib import Path

import fitz  # PyMuPDF

# Color scheme (RGB values, 0-255)
CLASS_COLORS = {
    "body_text": (0, 0, 255),  # Blue
    "footnote": (255, 0, 0),  # Red
    "section_header": (0, 255, 0),  # Green
    "title": (255, 255, 0),  # Yellow
    "author": (255, 165, 0),  # Orange
    "abstract": (128, 0, 128),  # Purple
    "other": (128, 128, 128),  # Gray
}

ALPHA = 0.3  # Transparency level (0=transparent, 1=opaque)


def rgb_to_fitz(rgb: tuple[int, int, int], alpha: float = ALPHA) -> tuple[float, float, float]:
    """Convert RGB (0-255) to PyMuPDF format (0-1)."""
    return (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


def load_extraction_results(json_path: Path) -> list[dict]:
    """Load extraction results from JSON."""
    with open(json_path) as f:
        data = json.load(f)
    return data.get("extracted_items", [])


def load_ground_truth(pdf_name: str, journal: str) -> list[dict]:
    """Load ground truth labels from processed_html or extraction JSON."""
    # First try to load from extraction JSON if it exists
    gt_json = Path(
        f"results/ocr_pipeline_evaluation/extractions/{journal}_{pdf_name}_baseline_extraction.json"
    )

    if gt_json.exists():
        with open(gt_json) as f:
            data = json.load(f)
        return data.get("ground_truth", [])

    # Fallback: could load from processed_html, but for now return empty
    print(f"Warning: No ground truth found for {pdf_name}")
    return []


def create_overlay_pdf(
    input_pdf: Path, items: list[dict], output_pdf: Path, title: str = "Classification Overlay"
):
    """
    Create a PDF with colored overlays for each classification.

    Args:
        input_pdf: Original PDF file
        items: List of items with 'label' and 'bbox' keys
        output_pdf: Output PDF path
        title: Title for the overlay (e.g., "Predictions" or "Ground Truth")
    """
    doc = fitz.open(input_pdf)

    # Process each page
    for page_num in range(len(doc)):
        page = doc[page_num]

        # Filter items for this page
        page_items = [item for item in items if item.get("page_num", 0) == page_num]

        # Draw overlays for each item
        for item in page_items:
            label = item.get("label", "other")
            bbox = item.get("bbox")

            if not bbox or len(bbox) != 4:
                continue

            # Get color for this class
            color = CLASS_COLORS.get(label, CLASS_COLORS["other"])
            fitz_color = rgb_to_fitz(color)

            # Create rectangle (PyMuPDF uses (x0, y0, x1, y1))
            rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])

            # Draw semi-transparent rectangle
            page.draw_rect(rect, color=fitz_color, fill=fitz_color, width=0.5, fill_opacity=ALPHA)

    # Add legend on first page
    add_legend(doc[0])

    # Save output
    doc.save(output_pdf)
    doc.close()

    print(f"✓ Created {title} overlay: {output_pdf}")


def add_legend(page: fitz.Page):
    """Add a color legend to the page."""
    # Position legend in bottom-right corner
    page_rect = page.rect
    legend_x = page_rect.width - 200
    legend_y = page_rect.height - 250

    # Draw white background
    bg_rect = fitz.Rect(legend_x - 10, legend_y - 10, page_rect.width - 10, page_rect.height - 10)
    page.draw_rect(bg_rect, color=(1, 1, 1), fill=(1, 1, 1), width=1)
    page.draw_rect(bg_rect, color=(0, 0, 0), width=1)  # Border

    # Add title
    page.insert_text(
        (legend_x, legend_y + 5), "Classification Legend:", fontsize=10, fontname="helv"
    )

    # Add each class with its color
    y_offset = 20
    for label, color in CLASS_COLORS.items():
        # Draw color box
        box_rect = fitz.Rect(legend_x, legend_y + y_offset, legend_x + 15, legend_y + y_offset + 10)
        fitz_color = rgb_to_fitz(color)
        page.draw_rect(box_rect, fill=fitz_color, fill_opacity=ALPHA, width=0.5, color=(0, 0, 0))

        # Add label text
        page.insert_text(
            (legend_x + 20, legend_y + y_offset + 8), label, fontsize=8, fontname="helv"
        )

        y_offset += 15


def visualize_document(
    pdf_path: Path,
    predictions_json: Path,
    output_dir: Path,
    journal: str = None,
    pdf_name: str = None,
):
    """
    Create both prediction and ground truth overlay PDFs.

    Args:
        pdf_path: Original PDF
        predictions_json: JSON file with Docling predictions
        output_dir: Directory for output PDFs
        journal: Journal name (for loading ground truth)
        pdf_name: PDF name without extension (for loading ground truth)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load predictions
    predictions = load_extraction_results(predictions_json)

    # Create predictions overlay
    pred_output = output_dir / f"{pdf_path.stem}_predictions.pdf"
    create_overlay_pdf(pdf_path, predictions, pred_output, "Docling Predictions")

    # Load and create ground truth overlay if available
    if journal and pdf_name:
        ground_truth = load_ground_truth(pdf_name, journal)
        if ground_truth:
            gt_output = output_dir / f"{pdf_path.stem}_groundtruth.pdf"
            create_overlay_pdf(pdf_path, ground_truth, gt_output, "Ground Truth")


def main():
    parser = argparse.ArgumentParser(description="Visualize PDF classification results")
    parser.add_argument("pdf", type=Path, help="Original PDF file")
    parser.add_argument("predictions", type=Path, help="JSON file with predictions")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/visualizations"),
        help="Output directory for overlay PDFs",
    )
    parser.add_argument("--journal", help="Journal name (for ground truth)")
    parser.add_argument("--pdf-name", help="PDF name without extension (for ground truth)")

    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"Error: PDF not found: {args.pdf}")
        return 1

    if not args.predictions.exists():
        print(f"Error: Predictions JSON not found: {args.predictions}")
        return 1

    visualize_document(args.pdf, args.predictions, args.output_dir, args.journal, args.pdf_name)

    print("\n✅ Visualization complete!")
    print(f"   Predictions: {args.output_dir / f'{args.pdf.stem}_predictions.pdf'}")
    if args.journal and args.pdf_name:
        print(f"   Ground Truth: {args.output_dir / f'{args.pdf.stem}_groundtruth.pdf'}")

    return 0


if __name__ == "__main__":
    exit(main())

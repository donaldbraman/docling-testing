#!/usr/bin/env python3
"""Generate Docling classification overlays for OCR comparison PDFs."""

from pathlib import Path

import fitz

from docling_testing import create_ocr_converter

# Color mapping for classifications
CLASS_COLORS = {
    "TextItem": (0, 0, 1),  # Blue
    "SectionHeaderItem": (0, 1, 0),  # Green
    "ListItem": (1, 0.5, 0),  # Orange
    "Title": (0.5, 0, 0.5),  # Purple
    "Caption": (1, 1, 0),  # Yellow
    "Footnote": (1, 0, 0),  # Red
    "default": (0.5, 0.5, 0.5),  # Gray
}


def create_overlay(image_pdf: Path, original_pdf: Path, output_path: Path, engine: str):
    """Create classification overlay for a PDF."""

    print(f"\n  Creating {engine} overlay...")

    # Run Docling with specified OCR engine
    converter = create_ocr_converter(engine)
    doc = converter.convert(str(image_pdf))

    # Count classifications
    class_counts = {}
    for item in doc.document.texts:
        item_type = type(item).__name__
        class_counts[item_type] = class_counts.get(item_type, 0) + 1

    print(f"    Classifications: {dict(class_counts)}")

    # Open original PDF for overlay
    pdf_doc = fitz.open(str(original_pdf))

    # Add colored overlays for each text item
    highlighted = 0
    for item in doc.document.texts:
        if not item.text or len(item.text.strip()) < 5:
            continue

        item_type = type(item).__name__
        color = CLASS_COLORS.get(item_type, CLASS_COLORS["default"])

        # Search all pages for this text
        for page in pdf_doc:
            # Try exact match first
            areas = page.search_for(item.text[:100])

            if not areas and len(item.text) > 20:
                # Try first few words
                words = item.text.split()[:5]
                search_text = " ".join(words)
                areas = page.search_for(search_text)

            for rect in areas:
                page.draw_rect(rect, color=color, width=1, fill=color, fill_opacity=0.2)
                highlighted += 1

    # Add legend
    first_page = pdf_doc[0]
    add_legend(first_page, engine)

    # Save
    pdf_doc.save(str(output_path))
    pdf_doc.close()

    print(f"    Highlighted {highlighted} regions")
    print(f"    Saved: {output_path.name}")


def add_legend(page, engine_name):
    """Add color legend to page."""
    page_rect = page.rect
    x = 10
    y = 10

    # Background
    legend_height = 180
    bg_rect = fitz.Rect(x, y, x + 180, y + legend_height)
    page.draw_rect(bg_rect, color=(1, 1, 1), fill=(1, 1, 1), width=1)
    page.draw_rect(bg_rect, color=(0, 0, 0), width=1)

    # Title
    page.insert_text((x + 5, y + 15), f"Docling + {engine_name}", fontsize=10, fontname="helv")

    # Colors
    y_offset = 25
    for label, color in CLASS_COLORS.items():
        box_rect = fitz.Rect(x + 5, y + y_offset, x + 20, y + y_offset + 10)
        page.draw_rect(box_rect, fill=color, fill_opacity=0.2, width=0.5, color=(0, 0, 0))
        page.insert_text((x + 25, y + y_offset + 8), label, fontsize=8, fontname="helv")
        y_offset += 15


def main():
    """Generate overlays for one high and one low performer."""

    # Directories
    ocr_dir = Path("results/ocr_engine_comparison")
    pdf_dir = Path("data/v3_data/raw_pdf")
    output_dir = Path("results/ocr_engine_comparison/overlays")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Select representative PDFs
    pdfs_to_visualize = {
        "high_performer": "antitrusts_interdependence_paradox",  # 95% recall
        "low_performer": "usc_law_review_listening_on_campus_academic_freedom_and_its_audiences",  # 29% recall
    }

    print("=" * 80)
    print("GENERATING DOCLING CLASSIFICATION OVERLAYS")
    print("=" * 80)
    print("\nColor Legend:")
    print("  🔵 Blue:   TextItem (body text)")
    print("  🟢 Green:  SectionHeaderItem")
    print("  🟠 Orange: ListItem")
    print("  🟣 Purple: Title")
    print("  🟡 Yellow: Caption")
    print("  🔴 Red:    Footnote")
    print("  ⚪ Gray:   Other/Unclassified")
    print("=" * 80)

    for group, pdf_name in pdfs_to_visualize.items():
        print(f"\n[{group.upper()}] {pdf_name}")
        print("-" * 80)

        original_pdf = pdf_dir / f"{pdf_name}.pdf"
        image_pdf = ocr_dir / f"{pdf_name}_image_only.pdf"

        if not original_pdf.exists():
            print(f"  ⚠️  Original PDF not found: {original_pdf}")
            continue

        if not image_pdf.exists():
            print(f"  ⚠️  Image-only PDF not found: {image_pdf}")
            continue

        # Generate overlays for both engines
        for engine in ["ocrmac", "tesseract"]:
            output_path = output_dir / f"{pdf_name}_{engine}_overlay.pdf"

            try:
                create_overlay(image_pdf, original_pdf, output_path, engine)
            except Exception as e:
                print(f"  ✗ Failed {engine}: {e}")

    print("\n" + "=" * 80)
    print("OVERLAY GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nOverlays saved to: {output_dir}")
    print("\nGenerated files:")
    print("  High performer (95% recall):")
    print("    - antitrusts_interdependence_paradox_ocrmac_overlay.pdf")
    print("    - antitrusts_interdependence_paradox_tesseract_overlay.pdf")
    print("  Low performer (29% recall):")
    print("    - usc_law_review_listening_..._ocrmac_overlay.pdf")
    print("    - usc_law_review_listening_..._tesseract_overlay.pdf")
    print("\nTo view:")
    print(f"  open {output_dir}")


if __name__ == "__main__":
    main()

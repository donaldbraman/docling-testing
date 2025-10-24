#!/usr/bin/env python3
"""
Visualize Docling's semantic classifications as color overlays.

Shows what class Docling assigned to each text region:
- Blue: body_text
- Red: footnote
- Green: section_header
- Purple: title
- Orange: list_item
- Gray: other
"""

import os
from pathlib import Path

import fitz  # PyMuPDF
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

os.environ["TESSDATA_PREFIX"] = "/opt/homebrew/Cellar/tesseract/5.5.1/share/tessdata"

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


def create_classification_overlay(image_pdf: Path, original_pdf: Path, output_path: Path) -> None:
    """Create overlay showing Docling classifications."""

    print(f"\nProcessing: {image_pdf.name}")
    print("  Running Docling + Tesseract to get classifications...")

    # Run Docling on image-only PDF
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = TesseractOcrOptions()

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    doc = converter.convert(str(image_pdf))

    # Count classifications
    class_counts = {}
    for item in doc.document.texts:
        item_type = type(item).__name__
        class_counts[item_type] = class_counts.get(item_type, 0) + 1

    print("\n  Classifications found:")
    for class_name, count in sorted(class_counts.items()):
        print(f"    {class_name}: {count}")

    # Open original PDF for overlay
    pdf_doc = fitz.open(str(original_pdf))

    # Search for each text item and color by classification
    highlighted = 0
    for item in doc.document.texts:
        if not item.text or len(item.text.strip()) < 5:
            continue

        item_type = type(item).__name__
        color = CLASS_COLORS.get(item_type, CLASS_COLORS["default"])

        # Search all pages for this text
        for page in pdf_doc:
            # Try exact match first
            areas = page.search_for(item.text[:100])  # First 100 chars

            if not areas and len(item.text) > 20:
                # Try first few words if exact fails
                words = item.text.split()[:5]
                search_text = " ".join(words)
                areas = page.search_for(search_text)

            for rect in areas:
                page.draw_rect(rect, color=color, width=1, fill=color, fill_opacity=0.2)
                highlighted += 1

    # Save overlay PDF
    pdf_doc.save(str(output_path))
    pdf_doc.close()

    print(f"\n  ✓ Created overlay with {highlighted} highlighted regions")
    print(f"  Saved: {output_path.name}")


def main():
    """Generate classification overlays for worst-performing PDFs."""

    # Directories
    pdf_dir = Path("data/v3_data/raw_pdf")
    image_dir = Path("results/tesseract_corpus_pipeline/grayscale_image_pdfs")
    overlay_dir = Path("results/tesseract_corpus_pipeline/classification_overlays")

    overlay_dir.mkdir(parents=True, exist_ok=True)

    # Process worst performers
    worst_pdfs = [
        "usc_law_review_listening_on_campus_academic_freedom_and_its_audiences",
        "texas_law_review_working-with-statutes",
        "california_law_review_amazon-trademark",
        "antitrusts_interdependence_paradox",
        "ucla_law_review_insurgent_knowledge_battling_cdcr_from_inside_the_system_the_story_of_the_essential_collaboration_be",
    ]

    print("=" * 80)
    print("GENERATING DOCLING CLASSIFICATION OVERLAYS")
    print("=" * 80)
    print("\nColor Legend:")
    print("  🔵 Blue:   TextItem (body_text)")
    print("  🟢 Green:  SectionHeaderItem")
    print("  🟠 Orange: ListItem")
    print("  🟣 Purple: Title")
    print("  🟡 Yellow: Caption")
    print("  🔴 Red:    Footnote")
    print("  ⚪ Gray:   Other/Unclassified")
    print("=" * 80)

    for i, pdf_name in enumerate(worst_pdfs, 1):
        print(f"\n[{i}/{len(worst_pdfs)}] {pdf_name}")
        print("-" * 80)

        original_pdf = pdf_dir / f"{pdf_name}.pdf"
        image_pdf = image_dir / f"{pdf_name}_grayscale_image_only.pdf"
        output_path = overlay_dir / f"{pdf_name}_classification_overlay.pdf"

        if not original_pdf.exists():
            print("  ⚠️  Original PDF not found")
            continue

        if not image_pdf.exists():
            print("  ⚠️  Image-only PDF not found")
            continue

        try:
            create_classification_overlay(image_pdf, original_pdf, output_path)
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    print("\n" + "=" * 80)
    print("CLASSIFICATION OVERLAY GENERATION COMPLETE")
    print("=" * 80)
    print(f"Overlays saved to: {overlay_dir}")
    print("\nThese show Docling's semantic classification of each text region.")
    print("Use this to see what Docling thinks each part of the document is.")
    print("\nTo view:")
    print(f"  open {overlay_dir}")


if __name__ == "__main__":
    main()

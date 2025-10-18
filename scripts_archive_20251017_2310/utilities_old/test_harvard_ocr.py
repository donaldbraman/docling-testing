#!/usr/bin/env python3
"""Test Harvard PDF extraction with OCR enabled."""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    OcrMacOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def test_harvard_with_ocr():
    """Test Harvard PDF with OCR enabled."""
    pdf_path = Path.home() / "Downloads" / "harvard_law_review_unwarranted_warrants.pdf"

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return

    print("🔍 Testing Harvard PDF with OCR enabled...\n")
    print(f"PDF: {pdf_path.name}\n")

    # Configure OCR options
    ocr_options = OcrMacOptions(force_full_page_ocr=True)

    # Configure pipeline with OCR
    pipeline = PdfPipelineOptions(
        do_ocr=True,
        ocr_options=ocr_options,
        generate_page_images=True,
        images_scale=1.0,
    )

    # Create converter with OCR pipeline
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    print("Converting with OCR...")
    result = converter.convert(str(pdf_path))

    print("\n✅ Conversion complete")
    print(f"Document has {len(result.document.pages)} pages\n")

    # Extract paragraphs using iterate_items
    print("Extracting paragraphs...")
    paragraphs = []
    items_count = 0
    text_items = 0

    for item, level in result.document.iterate_items():
        items_count += 1
        if hasattr(item, "text") and item.text:
            text_items += 1
            text = item.text.strip()
            if len(text) > 20:
                paragraphs.append(text.lower())
                if len(paragraphs) <= 5:
                    print(f"\nParagraph {len(paragraphs)}:")
                    print(f"  {text[:200]}...")

    print("\n📊 Results:")
    print(f"  Total items: {items_count}")
    print(f"  Items with text: {text_items}")
    print(f"  Paragraphs (>20 chars): {len(paragraphs)}")

    if len(paragraphs) > 0:
        print(f"\n✅ SUCCESS: OCR extracted {len(paragraphs)} paragraphs")
        return True
    else:
        print("\n❌ FAILED: OCR extracted 0 paragraphs")
        return False


if __name__ == "__main__":
    test_harvard_with_ocr()

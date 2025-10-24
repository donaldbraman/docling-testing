#!/usr/bin/env python3
"""
Test Docling with Tesseract OCR engine instead of ocrmac.
"""

import json
import re
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text).strip().lower()


def main():
    """Test Docling with Tesseract OCR."""
    pdf_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only.pdf"
    )
    output_dir = Path("results/ocr_parameter_tests")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("TESTING DOCLING WITH TESSERACT OCR")
    print("=" * 80)
    print(f"\nPDF: {pdf_path.name}")

    # Configure pipeline to use Tesseract
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = TesseractOcrOptions()

    print("\nOCR Configuration:")
    print("  Engine: Tesseract (via TesseractOcrOptions)")
    print(f"  do_ocr: {pipeline_options.do_ocr}")

    # Run conversion
    print("\nRunning Docling with Tesseract...")
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    doc = converter.convert(str(pdf_path))

    # Collect all text
    all_texts = []
    if doc.document.texts:
        all_texts.extend([item.text for item in doc.document.texts])
    if doc.document.tables:
        for table in doc.document.tables:
            table_md = table.export_to_markdown(doc.document)
            if table_md:
                all_texts.append(table_md)

    print("✓ Extraction complete")
    print(f"  Text blocks: {len(all_texts)}")
    print(f"  Pages: {len(doc.pages) if doc.pages else 0}")

    # Search for test paragraph
    search_text = "Given the growing importance of UE theory"
    search_normalized = normalize_text(search_text)
    found = False
    found_in_block = None

    for i, text in enumerate(all_texts):
        if search_normalized in normalize_text(text):
            found = True
            found_in_block = i
            break

    print("\nTest paragraph search:")
    print(f"  Searching for: '{search_text}'...")
    print(f"  Result: {'✓ FOUND' if found else '✗ NOT FOUND'}")
    if found:
        print(f"  Found in block: {found_in_block}")
        print("\nBlock preview:")
        print(f"  {all_texts[found_in_block][:300]}...")

    # Save extraction
    extraction_path = output_dir / "docling_tesseract_extraction.json"
    with open(extraction_path, "w") as f:
        json.dump(
            {
                "texts": all_texts,
                "metadata": {
                    "ocr_engine": "tesseract",
                    "text_blocks": len(all_texts),
                    "test_paragraph_found": found,
                    "found_in_block": found_in_block,
                },
            },
            f,
            indent=2,
            default=str,
        )

    print(f"\n✓ Saved extraction to: {extraction_path}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("OCR Engine: Tesseract (via Docling)")
    print(f"Text blocks extracted: {len(all_texts)}")
    print(f"Test paragraph: {'✓ FOUND' if found else '✗ NOT FOUND'}")

    if found:
        print("\n✓ SUCCESS: Docling + Tesseract found the missing paragraph!")
        print("   This confirms Tesseract is more accurate than ocrmac.")
    else:
        print("\n✗ NOT FOUND: Tesseract also failed to extract this text.")


if __name__ == "__main__":
    main()

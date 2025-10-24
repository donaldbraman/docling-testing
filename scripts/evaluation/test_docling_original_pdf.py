#!/usr/bin/env python3
"""
Test Docling extraction on the ORIGINAL PDF (not image-only).
"""

import json
from pathlib import Path

from docling.document_converter import DocumentConverter


def main():
    """Test Docling on original PDF."""
    pdf_path = Path("data/v3_data/raw_pdf/usc_law_review_in_the_name_of_accountability.pdf")
    output_path = Path("results/ocr_pipeline_test/original_pdf_extraction.json")

    print(f"Running Docling on original PDF: {pdf_path.name}\n")

    converter = DocumentConverter()
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

    # Save extraction
    extraction_data = {
        "texts": all_texts,
        "page_count": len(doc.pages) if doc.pages else 0,
        "metadata": {
            "source": "original_pdf",
            "text_blocks": len([item.text for item in doc.document.texts])
            if doc.document.texts
            else 0,
            "tables": len(list(doc.document.tables)) if doc.document.tables else 0,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(extraction_data, f, indent=2, default=str)

    print(f"✓ Extraction saved to: {output_path}")
    print(f"  Text blocks: {extraction_data['metadata']['text_blocks']}")
    print(f"  Tables: {extraction_data['metadata']['tables']}")
    print(f"  Total items: {len(all_texts)}")

    # Search for the missing paragraph
    search_text = "Given the growing importance of UE theory"
    found = any(search_text in text for text in all_texts)

    print(f"\nSearching for: '{search_text}'...")
    print(f"Result: {'✓ FOUND' if found else '✗ NOT FOUND'}")

    if found:
        # Find which block contains it
        for i, text in enumerate(all_texts):
            if search_text in text:
                print(f"\nFound in block {i}:")
                print(f"  {text[:200]}...")
                break


if __name__ == "__main__":
    main()

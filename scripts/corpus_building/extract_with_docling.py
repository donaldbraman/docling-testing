#!/usr/bin/env python3
"""
Extract PDF structure using Docling with default settings (V3 Pipeline).

Processes all PDFs in data/v3_data/raw_pdf/ and saves structured output
to data/v3_data/docling_extraction/.

Author: Claude Code
Date: 2025-01-18
"""

import json
from pathlib import Path

from docling.document_converter import DocumentConverter


def extract_single_pdf(pdf_path: Path, output_dir: Path):
    """
    Extract a single PDF using Docling with default settings.

    Args:
        pdf_path: Path to input PDF
        output_dir: Directory to save extraction JSON
    """
    print(f"\n{'=' * 80}")
    print(f"Processing: {pdf_path.name}")
    print(f"{'=' * 80}")

    # Initialize converter with defaults
    converter = DocumentConverter()

    # Convert the document
    result = converter.convert(pdf_path)

    # Explore the result structure
    print(f"\nResult type: {type(result)}")
    print(f"Result attributes: {dir(result)}")

    # Save the full result to JSON for inspection
    output_file = output_dir / f"{pdf_path.stem}.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Try to export as dict/JSON
    if hasattr(result, "document"):
        doc = result.document
        print(f"\nDocument type: {type(doc)}")
        print(f"Document attributes: {dir(doc)}")

        # Export to dict if available
        if hasattr(doc, "export_to_dict"):
            doc_dict = doc.export_to_dict()
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(doc_dict, f, ensure_ascii=False, indent=2)
            print(f"\n✅ Saved extraction to: {output_file}")

            # Print summary
            print("\nExtraction summary:")
            print(f"  Keys in dict: {list(doc_dict.keys())}")
            if "main_text" in doc_dict:
                print(f"  Main text length: {len(doc_dict.get('main_text', ''))}")
            if "elements" in doc_dict:
                print(f"  Number of elements: {len(doc_dict.get('elements', []))}")
        else:
            print("\n⚠️  No export_to_dict method available")
    else:
        print("\n⚠️  No document attribute in result")


def main():
    """Run Docling extraction on a single test PDF."""
    raw_pdf_dir = Path("data/v3_data/raw_pdf")
    output_dir = Path("data/v3_data/docling_extraction")

    # Get first PDF as test
    pdf_files = sorted(raw_pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print("❌ No PDF files found in data/v3_data/raw_pdf/")
        return

    print(f"Found {len(pdf_files)} PDF files")
    print(f"Testing with first file: {pdf_files[0].name}")

    # Extract first PDF
    extract_single_pdf(pdf_files[0], output_dir)


if __name__ == "__main__":
    main()

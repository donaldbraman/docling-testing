#!/usr/bin/env python3
"""
Extract all newly collected PDFs with Docling.
"""

import sys
from datetime import datetime
from pathlib import Path

from docling.document_converter import DocumentConverter


def extract_pdf(pdf_path: Path, output_dir: Path):
    """Extract single PDF with Docling."""
    output_file = output_dir / f"{pdf_path.stem}.docling.json"

    # Skip if already extracted
    if output_file.exists():
        return "skipped"

    try:
        converter = DocumentConverter()
        result = converter.convert(pdf_path)

        # Extract document structure as JSON
        doc_data = {
            "file": pdf_path.name,
            "markdown": result.document.export_to_markdown(),
            "texts": [],
        }

        # Extract all text elements with their labels
        for element, level in result.document.iterate_items():
            if hasattr(element, "text") and hasattr(element, "label"):
                doc_data["texts"].append(
                    {"text": element.text, "label": element.label, "level": level}
                )

        # Save as JSON
        import json

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(doc_data, f, ensure_ascii=False, indent=2)

        return "success"
    except Exception as e:
        return f"error: {e}"


def main():
    pdf_dir = Path("data/raw_pdf")
    output_dir = pdf_dir  # Save in same directory

    # Get all PDFs
    pdfs = sorted(pdf_dir.glob("*.pdf"))

    print("=" * 100)
    print(f"EXTRACTING {len(pdfs)} PDFs WITH DOCLING")
    print("=" * 100)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    extracted = 0
    skipped = 0
    errors = 0

    for i, pdf_path in enumerate(pdfs, 1):
        status = extract_pdf(pdf_path, output_dir)

        if status == "success":
            extracted += 1
            print(f"[{i:3d}/{len(pdfs)}] ✓ Extracted: {pdf_path.name}")
        elif status == "skipped":
            skipped += 1
            print(f"[{i:3d}/{len(pdfs)}] ⊙ Skipped (exists): {pdf_path.name}")
        else:
            errors += 1
            print(f"[{i:3d}/{len(pdfs)}] ✗ Error: {pdf_path.name} - {status}")

        sys.stdout.flush()

    print("\n" + "=" * 100)
    print("EXTRACTION COMPLETE")
    print("=" * 100)
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total PDFs: {len(pdfs)}")
    print(f"Extracted: {extracted}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()

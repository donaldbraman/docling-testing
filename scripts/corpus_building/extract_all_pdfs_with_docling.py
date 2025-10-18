#!/usr/bin/env python3
"""
Extract all PDFs with Docling (Step 1 only).

Author: Claude Code
Date: 2025-01-18
"""

import json
from pathlib import Path

from docling.document_converter import DocumentConverter


def main():
    """Extract all PDFs that have corresponding HTML ground truth."""
    raw_pdf_dir = Path("data/v3_data/raw_pdf")
    processed_html_dir = Path("data/v3_data/processed_html")
    output_dir = Path("data/v3_data/docling_extraction")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of basenames from HTML files
    html_files = sorted(processed_html_dir.glob("*.json"))
    basenames = [f.stem for f in html_files]

    print(f"{'=' * 80}")
    print(f"Extracting {len(basenames)} PDFs with Docling")
    print(f"{'=' * 80}\n")

    # Initialize converter once
    converter = DocumentConverter()

    success_count = 0
    skip_count = 0
    error_count = 0

    for idx, basename in enumerate(basenames, 1):
        pdf_path = raw_pdf_dir / f"{basename}.pdf"
        output_file = output_dir / f"{basename}.json"

        # Check if PDF exists
        if not pdf_path.exists():
            print(f"[{idx}/{len(basenames)}] ⚠️  PDF not found: {basename}.pdf")
            error_count += 1
            continue

        # Skip if already extracted
        if output_file.exists():
            print(f"[{idx}/{len(basenames)}] ⏭️  Already extracted: {basename}")
            skip_count += 1
            continue

        print(f"[{idx}/{len(basenames)}] 📄 Extracting {basename}...", end=" ", flush=True)

        try:
            # Convert the document
            result = converter.convert(pdf_path)

            # Export to JSON
            if hasattr(result, "document") and hasattr(result.document, "export_to_dict"):
                doc_dict = result.document.export_to_dict()
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(doc_dict, f, ensure_ascii=False, indent=2)

                # Count body texts (excluding furniture)
                text_count = sum(
                    1
                    for item in doc_dict.get("texts", [])
                    if item.get("content_layer") != "furniture"
                )
                print(f"✅ ({text_count} text items)")
                success_count += 1
            else:
                print("❌ Failed to export")
                error_count += 1
        except Exception as e:
            print(f"❌ Error: {e}")
            error_count += 1

    print(f"\n{'=' * 80}")
    print("Extraction Summary")
    print(f"{'=' * 80}")
    print(f"Total PDFs: {len(basenames)}")
    print(f"  Newly extracted: {success_count}")
    print(f"  Already extracted: {skip_count}")
    print(f"  Errors: {error_count}")
    print("\n✅ Docling extraction complete!")


if __name__ == "__main__":
    main()

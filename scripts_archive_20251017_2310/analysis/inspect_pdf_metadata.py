#!/usr/bin/env python3
"""
Inspect PDF metadata and structure to check for semantic tags.

Checks if PDFs contain:
1. Basic metadata (title, author, etc.)
2. Structure tags (PDF/UA, tagged PDF)
3. Page-level information (headers/footers marked)
"""

import sys
from pathlib import Path

from pypdf import PdfReader


def inspect_pdf(pdf_path: Path):
    """Inspect PDF metadata and structure."""
    print("=" * 80)
    print(f"INSPECTING: {pdf_path.name}")
    print("=" * 80)

    try:
        reader = PdfReader(pdf_path)

        # Basic metadata
        print("\n1. DOCUMENT METADATA:")
        print("-" * 80)
        metadata = reader.metadata
        if metadata:
            for key, value in metadata.items():
                print(f"  {key}: {value}")
        else:
            print("  No metadata found")

        # Document info
        print("\n2. DOCUMENT INFO:")
        print("-" * 80)
        print(f"  Pages: {len(reader.pages)}")
        print(f"  Encrypted: {reader.is_encrypted}")

        # Check for structure tree (tagged PDF)
        print("\n3. STRUCTURE TREE (Tagged PDF):")
        print("-" * 80)
        catalog = reader.trailer["/Root"]

        if "/StructTreeRoot" in catalog:
            print("  ✓ PDF has structure tree (Tagged PDF)")
            struct_root = catalog["/StructTreeRoot"]
            print(f"  Structure elements: {struct_root}")

            # Try to extract structure types
            if "/K" in struct_root:
                print(f"  Children: {struct_root['/K']}")
        else:
            print("  ✗ No structure tree found (not tagged)")

        # Check first page for content structure
        print("\n4. FIRST PAGE CONTENT ANALYSIS:")
        print("-" * 80)
        page = reader.pages[0]

        # Get page dimensions
        if "/MediaBox" in page:
            mediabox = page["/MediaBox"]
            print(f"  MediaBox: {mediabox}")
            height = float(mediabox[3]) - float(mediabox[1])
            width = float(mediabox[2]) - float(mediabox[0])
            print(f"  Dimensions: {width} x {height} points")

        # Check for annotations
        if "/Annots" in page:
            annots = page["/Annots"]
            print(f"  Annotations: {len(annots)} found")
        else:
            print("  Annotations: None")

        # Extract text to see positioning
        text = page.extract_text()
        lines = text.split("\n")
        print(f"\n  Text lines: {len(lines)}")
        print("  First 3 lines:")
        for i, line in enumerate(lines[:3], 1):
            print(f"    {i}. {line[:80]}")
        print("  Last 3 lines:")
        for i, line in enumerate(lines[-3:], len(lines) - 2):
            print(f"    {i}. {line[:80]}")

        # Check if page has marked content
        print("\n5. MARKED CONTENT:")
        print("-" * 80)
        if "/Contents" in page:
            print("  ✓ Page has content stream")
            # Content streams contain the actual drawing commands
            # Headers/footers might be marked with tags like /Artifact
        else:
            print("  ✗ No content stream found")

        print("\n" + "=" * 80)
        print("CONCLUSION:")
        print("=" * 80)

        if "/StructTreeRoot" in catalog:
            print("✓ This is a TAGGED PDF - might have semantic structure for headers/footers!")
        else:
            print("✗ This is NOT a tagged PDF - headers/footers must be inferred from layout")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        # Default to first PDF found
        pdf_path = Path(
            "/Users/donaldbraman/Documents/GitHub/12-factor-agents/test_corpus/pdfs/VT36J57X_Mitchell_Petersen_Progressive_Prosecutors.pdf"
        )

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)

    inspect_pdf(pdf_path)

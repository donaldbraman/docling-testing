#!/usr/bin/env python3
"""
Search for text in PDF to see if it's actually present.
"""

import sys
from pathlib import Path

import fitz  # PyMuPDF


def search_in_pdf(pdf_path: Path, search_text: str):
    """Search for text across all pages of a PDF."""
    doc = fitz.open(str(pdf_path))

    print(f"Searching for: {search_text[:50]}...")
    print(f"Total pages: {len(doc)}\n")

    found_pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Search for the text
        text_instances = page.search_for(search_text)

        if text_instances:
            found_pages.append(page_num + 1)
            print(f"✓ Found on page {page_num + 1}")
            print(f"  Number of instances: {len(text_instances)}")

            # Show surrounding text
            page_text = page.get_text()
            # Find the search text in page text
            idx = page_text.lower().find(search_text.lower())
            if idx != -1:
                # Show 200 chars before and after
                start = max(0, idx - 200)
                end = min(len(page_text), idx + len(search_text) + 200)
                context = page_text[start:end]
                print(f"  Context:\n    ...{context}...")
            print()

    doc.close()

    if not found_pages:
        print("✗ Text not found in any page of the PDF")
        print("\nThis could mean:")
        print("  1. The text doesn't exist in the PDF at all")
        print("  2. The text exists but is an image (no text layer)")
        print("  3. The text uses different encoding/characters")
    else:
        print(f"\nSummary: Found on {len(found_pages)} page(s): {found_pages}")

    return found_pages


if __name__ == "__main__":
    import sys

    # Test with the first missing paragraph
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        pdf_path = Path("data/v3_data/raw_pdf/usc_law_review_in_the_name_of_accountability.pdf")

    search_text = "Given the growing importance of UE theory"

    print(f"Searching in: {pdf_path}\n")
    search_in_pdf(pdf_path, search_text)

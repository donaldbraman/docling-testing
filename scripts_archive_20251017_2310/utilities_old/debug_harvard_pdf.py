#!/usr/bin/env python3
"""Debug why docling returns 0 paragraphs for Harvard PDFs."""

from pathlib import Path

from docling.document_converter import DocumentConverter

pdf_path = Path.home() / "Downloads" / "harvard_law_review_unwarranted_warrants.pdf"

print(f"Checking docling processing: {pdf_path.name}\n")

converter = DocumentConverter()
result = converter.convert(str(pdf_path))

print("Document converted successfully")
print(f"Document object: {type(result.document)}")
print(f"Document has {len(result.document.pages)} pages")

# Try different ways to access content
print("\n=== Method 1: iterate_items() ===")
items_count = 0
text_items = 0
for item, level in result.document.iterate_items():
    items_count += 1
    if hasattr(item, "text") and item.text:
        text_items += 1
        if text_items <= 5:
            print(f"Item {items_count}: {type(item)}")
            if hasattr(item, "label"):
                print(f"  Label: {item.label}")
            print(f"  Text: {item.text[:100]}")

print(f"\nTotal items from iterate_items(): {items_count}")
print(f"Items with text: {text_items}")

# Try accessing page text directly
print("\n=== Method 2: Direct page access ===")
if result.document.pages:
    print(f"Pages available: {len(result.document.pages)}")
    first_page = result.document.pages[0]
    print(f"First page type: {type(first_page)}")

    # Check page attributes
    attrs = [a for a in dir(first_page) if not a.startswith("_")]
    print(f"Page attributes: {attrs[:10]}")

# Check export to markdown
print("\n=== Method 3: Export to markdown ===")
try:
    md = result.document.export_to_markdown()
    print(f"Markdown export length: {len(md)} chars")
    print(f"First 500 chars:\n{md[:500]}")
except Exception as e:
    print(f"Export failed: {e}")

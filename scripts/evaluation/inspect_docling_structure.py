#!/usr/bin/env python3
"""
Inspect Docling document structure to see what content we're missing.
"""

from pathlib import Path

from docling.document_converter import DocumentConverter


def main():
    """Inspect Docling structure."""
    # Use the image-only PDF that we already created
    pdf_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only.pdf"
    )

    print("Converting PDF with Docling...")
    converter = DocumentConverter()
    doc = converter.convert(str(pdf_path))

    print("\n" + "=" * 80)
    print("DOCLING DOCUMENT STRUCTURE")
    print("=" * 80)

    # Check what attributes the document has
    print("\nDocument attributes:")
    doc_attrs = [attr for attr in dir(doc.document) if not attr.startswith("_")]
    for attr in sorted(doc_attrs):
        print(f"  - {attr}")

    # Count different item types
    print("\n" + "-" * 80)
    print("CONTENT COUNTS")
    print("-" * 80)

    if hasattr(doc.document, "texts"):
        texts = list(doc.document.texts) if doc.document.texts else []
        print(f"texts: {len(texts)}")

    if hasattr(doc.document, "tables"):
        tables = list(doc.document.tables) if doc.document.tables else []
        print(f"tables: {len(tables)}")

    if hasattr(doc.document, "pictures"):
        pictures = list(doc.document.pictures) if doc.document.pictures else []
        print(f"pictures: {len(pictures)}")

    if hasattr(doc.document, "key_value_items"):
        kvs = list(doc.document.key_value_items) if doc.document.key_value_items else []
        print(f"key_value_items: {len(kvs)}")

    # Check for main_text vs other text
    if hasattr(doc.document, "body"):
        print(f"body: {doc.document.body is not None}")

    # Inspect text items in detail
    if hasattr(doc.document, "texts") and doc.document.texts:
        print("\n" + "-" * 80)
        print("TEXT ITEMS SAMPLE (first 10)")
        print("-" * 80)

        for i, item in enumerate(list(doc.document.texts)[:10]):
            # Check what attributes each text item has
            if i == 0:
                print(f"\nText item attributes: {[a for a in dir(item) if not a.startswith('_')]}")

            # Print sample
            text_preview = item.text[:100] if len(item.text) > 100 else item.text

            # Check for label/type
            label = getattr(item, "label", None) or getattr(item, "type", None) or "unknown"

            print(f"\n[{i + 1}] {label}")
            print(f"    Text: {text_preview}...")

            # Check for other useful attributes
            if hasattr(item, "prov"):
                print(f"    Prov: {item.prov}")

    # Check if there's a way to get ALL content
    print("\n" + "-" * 80)
    print("CHECKING FOR ALL CONTENT")
    print("-" * 80)

    # Try to get all items
    if hasattr(doc.document, "iterate_items"):
        all_items = list(doc.document.iterate_items())
        print(f"iterate_items(): {len(all_items)} items")

    if hasattr(doc.document, "main_text"):
        main_text = doc.document.main_text
        print(f"main_text: {len(main_text) if main_text else 0} chars")

    # Export to markdown and check length
    markdown = doc.document.export_to_markdown()
    print(f"\nMarkdown export: {len(markdown)} chars, {len(markdown.split())} words")

    # Check pages
    if doc.pages:
        print(f"Pages: {len(doc.pages)}")

    # Analyze label distribution
    print("\n" + "-" * 80)
    print("LABEL DISTRIBUTION")
    print("-" * 80)

    from collections import Counter

    # Get labels from all texts
    all_text_labels = Counter(item.label for item in doc.document.texts)
    print(f"\nLabels in doc.document.texts ({len(list(doc.document.texts))} items):")
    for label, count in sorted(all_text_labels.items()):
        print(f"  {label}: {count}")

    # Get labels from iterate_items
    if hasattr(doc.document, "iterate_items"):
        iterate_items_list = list(doc.document.iterate_items())

        # Check types of items
        item_types = Counter(type(item).__name__ for item in iterate_items_list)
        print(f"\nTypes in iterate_items() ({len(iterate_items_list)} items):")
        for item_type, count in sorted(item_types.items()):
            print(f"  {item_type}: {count}")

        # Get labels only from items that have the label attribute
        iterate_labels = Counter(
            str(item.label) if hasattr(item, "label") else type(item).__name__
            for item in iterate_items_list
        )
        print("\nLabels in iterate_items():")
        for label, count in sorted(iterate_labels.items()):
            print(f"  {label}: {count}")

        # Find which labels are excluded
        print("\n" + "-" * 80)
        print("LABELS EXCLUDED BY iterate_items()")
        print("-" * 80)

        # Convert both to string sets for comparison
        iterate_set = {str(label) for label in iterate_labels}
        text_set = {str(label) for label in all_text_labels}
        excluded_labels = text_set - iterate_set

        if excluded_labels:
            print(f"\nExcluded labels: {sorted(excluded_labels)}")
            for label_str in sorted(excluded_labels):
                # Find the original label object
                for orig_label in all_text_labels:
                    if str(orig_label) == label_str:
                        print(f"  {label_str}: {all_text_labels[orig_label]} items excluded")
                        break
        else:
            print("\nNo labels excluded - iterate_items() includes all text items")

        # Count total items excluded
        texts_count = len(list(doc.document.texts))
        iterate_count = len(iterate_items_list)
        total_excluded = texts_count - iterate_count
        print(
            f"\nTotal items excluded: {total_excluded} ({total_excluded / texts_count * 100:.1f}%)"
        )
        print(
            f"  {texts_count} text items - {iterate_count} iterate_items = {total_excluded} excluded"
        )


if __name__ == "__main__":
    main()

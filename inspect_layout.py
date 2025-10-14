#!/usr/bin/env python3
"""Inspect Docling's layout detection capabilities."""

import json
from collections import Counter
from pathlib import Path

from docling.document_converter import DocumentConverter


def inspect_layout(pdf_path: Path) -> dict:
    """
    Analyze Docling's layout detection for a single PDF.

    Shows what document elements are detected and where.
    """
    print(f"\n{'='*80}")
    print(f"LAYOUT INSPECTION: {pdf_path.name}")
    print(f"{'='*80}\n")

    # Convert document
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document

    # Get all document items with their types
    items_by_type = Counter()
    all_items = []

    for item in doc.body:
        item_type = type(item).__name__
        items_by_type[item_type] += 1

        # Extract text preview
        text_preview = ""
        if hasattr(item, 'text'):
            text_preview = item.text[:100] if item.text else ""

        all_items.append({
            "type": item_type,
            "text_preview": text_preview,
            "has_text": hasattr(item, 'text'),
            "has_label": hasattr(item, 'label'),
            "label": getattr(item, 'label', None)
        })

    # Print summary
    print("DETECTED ELEMENTS:")
    print("-" * 80)
    for item_type, count in items_by_type.most_common():
        print(f"  {item_type:30} : {count:>4}")

    # Show first few items of each type
    print(f"\n{'='*80}")
    print("SAMPLE ELEMENTS (first occurrence of each type):")
    print('='*80)

    seen_types = set()
    for item in all_items[:50]:  # Check first 50 items
        if item['type'] not in seen_types:
            seen_types.add(item['type'])
            print(f"\n{item['type']}:")
            if item['label']:
                print(f"  Label: {item['label']}")
            if item['text_preview']:
                print(f"  Text: {item['text_preview'][:150]}...")

    # Check for footnotes specifically
    print(f"\n{'='*80}")
    print("FOOTNOTE DETECTION:")
    print('='*80)

    footnote_items = [item for item in all_items if 'footnote' in item['type'].lower() or
                      (item['label'] and 'footnote' in str(item['label']).lower())]

    if footnote_items:
        print(f"✅ Found {len(footnote_items)} footnote elements")
        for i, item in enumerate(footnote_items[:5], 1):
            print(f"\n  Footnote {i}:")
            print(f"    Type: {item['type']}")
            print(f"    Label: {item['label']}")
            print(f"    Text: {item['text_preview'][:100]}...")
    else:
        print("❌ No footnote elements detected")

    # Export structured data
    return {
        "filename": pdf_path.name,
        "element_counts": dict(items_by_type),
        "total_elements": len(all_items),
        "footnote_count": len(footnote_items),
        "sample_items": all_items[:20]
    }


def main():
    """Inspect layout for all test PDFs."""

    base_dir = Path(__file__).parent
    test_corpus = base_dir / "test_corpus" / "law_reviews"
    output_dir = base_dir / "results" / "layout_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(test_corpus.glob("*.pdf"))

    if not pdfs:
        print("❌ No PDFs found")
        return

    print(f"🔬 DOCLING LAYOUT DETECTION TEST")
    print(f"Found {len(pdfs)} test PDFs\n")

    all_results = []
    for pdf_path in pdfs:
        try:
            result = inspect_layout(pdf_path)
            all_results.append(result)

            # Save detailed JSON
            json_path = output_dir / f"{pdf_path.stem}_layout.json"
            json_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(f"\n📁 Layout data saved to: {json_path}")

        except Exception as e:
            print(f"❌ Error: {e}")

    # Summary across all documents
    if all_results:
        print(f"\n{'='*80}")
        print("SUMMARY ACROSS ALL DOCUMENTS")
        print(f"{'='*80}\n")

        total_footnotes = sum(r['footnote_count'] for r in all_results)
        docs_with_footnotes = sum(1 for r in all_results if r['footnote_count'] > 0)

        print(f"Total documents: {len(all_results)}")
        print(f"Documents with detected footnotes: {docs_with_footnotes}/{len(all_results)}")
        print(f"Total footnotes detected: {total_footnotes}")

        # Element type summary
        all_element_types = Counter()
        for result in all_results:
            all_element_types.update(result['element_counts'])

        print(f"\nMost common element types across all docs:")
        for elem_type, count in all_element_types.most_common(10):
            print(f"  {elem_type:30} : {count:>4}")


if __name__ == "__main__":
    main()

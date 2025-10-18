#!/usr/bin/env python3
"""Inspect Docling's layout detection - Version 2 with correct API usage."""

import json
from collections import Counter
from pathlib import Path

from docling.document_converter import DocumentConverter


def inspect_layout(pdf_path: Path) -> dict:
    """
    Analyze Docling's layout detection for a single PDF.

    Shows what document elements are detected and where.
    """
    print(f"\n{'=' * 80}")
    print(f"LAYOUT INSPECTION: {pdf_path.name}")
    print(f"{'=' * 80}\n")

    # Convert document
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document

    # Get all document items with their labels using iterate_items()
    items_by_label = Counter()
    all_items = []

    for item, level in doc.iterate_items():
        label = item.label if hasattr(item, "label") else None
        label_str = str(label) if label else "NO_LABEL"

        items_by_label[label_str] += 1

        # Extract text preview
        text_preview = ""
        if hasattr(item, "text") and item.text:
            text_preview = item.text[:150]

        all_items.append(
            {
                "label": label_str,
                "text_preview": text_preview,
                "level": level,
                "has_text": hasattr(item, "text"),
            }
        )

    # Print summary
    print("DETECTED ELEMENT LABELS:")
    print("-" * 80)
    for label, count in items_by_label.most_common():
        print(f"  {label:30} : {count:>4}")

    # Show first few items of each label type
    print(f"\n{'=' * 80}")
    print("SAMPLE ELEMENTS (first occurrence of each label):")
    print("=" * 80)

    seen_labels = set()
    for item in all_items[:100]:  # Check first 100 items
        if item["label"] not in seen_labels:
            seen_labels.add(item["label"])
            print(f"\n{item['label']} (level {item['level']}):")
            if item["text_preview"]:
                print(f"  Text: {item['text_preview']}...")

    # Check for footnotes specifically
    print(f"\n{'=' * 80}")
    print("FOOTNOTE DETECTION:")
    print("=" * 80)

    footnote_items = [item for item in all_items if "footnote" in item["label"].lower()]

    if footnote_items:
        print(f"✅ Found {len(footnote_items)} footnote elements")
        for i, item in enumerate(footnote_items[:10], 1):
            print(f"\n  Footnote {i} (level {item['level']}):")
            print(f"    Label: {item['label']}")
            print(f"    Text: {item['text_preview'][:100]}...")
    else:
        print("❌ No footnote elements detected")

    # Check for headers/footers
    header_items = [item for item in all_items if "header" in item["label"].lower()]
    footer_items = [item for item in all_items if "footer" in item["label"].lower()]

    print(f"\n  Headers detected: {len(header_items)}")
    print(f"  Footers detected: {len(footer_items)}")

    # Export structured data
    return {
        "filename": pdf_path.name,
        "element_counts": dict(items_by_label),
        "total_elements": len(all_items),
        "footnote_count": len(footnote_items),
        "header_count": len(header_items),
        "footer_count": len(footer_items),
        "sample_items": all_items[:50],  # First 50 for JSON export
    }


def main():
    """Inspect layout for all test PDFs."""

    base_dir = Path(__file__).parent
    test_corpus = base_dir / "test_corpus" / "law_reviews"
    output_dir = base_dir / "results" / "layout_analysis_v2"
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(test_corpus.glob("*.pdf"))

    if not pdfs:
        print("❌ No PDFs found")
        return

    print("🔬 DOCLING LAYOUT DETECTION TEST (V2)")
    print(f"Found {len(pdfs)} test PDFs\n")

    all_results = []
    for pdf_path in pdfs:
        try:
            result = inspect_layout(pdf_path)
            all_results.append(result)

            # Save detailed JSON
            json_path = output_dir / f"{pdf_path.stem}_layout.json"
            json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(f"\n📁 Layout data saved to: {json_path}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()

    # Summary across all documents
    if all_results:
        print(f"\n{'=' * 80}")
        print("SUMMARY ACROSS ALL DOCUMENTS")
        print(f"{'=' * 80}\n")

        total_footnotes = sum(r["footnote_count"] for r in all_results)
        total_headers = sum(r["header_count"] for r in all_results)
        total_footers = sum(r["footer_count"] for r in all_results)
        docs_with_footnotes = sum(1 for r in all_results if r["footnote_count"] > 0)

        print(f"Total documents: {len(all_results)}")
        print(f"Documents with detected footnotes: {docs_with_footnotes}/{len(all_results)}")
        print(f"Total footnotes detected: {total_footnotes}")
        print(f"Total headers detected: {total_headers}")
        print(f"Total footers detected: {total_footers}")

        # Element label summary
        all_element_labels = Counter()
        for result in all_results:
            all_element_labels.update(result["element_counts"])

        print("\nMost common element labels across all docs:")
        for label, count in all_element_labels.most_common(15):
            print(f"  {label:30} : {count:>4}")


if __name__ == "__main__":
    main()

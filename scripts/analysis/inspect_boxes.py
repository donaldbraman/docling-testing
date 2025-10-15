#!/usr/bin/env python3
"""Inspect bounding boxes and layout labels from Docling parsed pages."""

import json
from collections import Counter
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    LayoutOptions,
    PdfPipelineOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def inspect_bounding_boxes(pdf_path: Path, scale: float = 1.0):
    """
    Extract and analyze bounding boxes from Docling.

    Args:
        pdf_path: Path to PDF
        scale: Image scaling factor
    """
    print(f"\n{'=' * 80}")
    print(f"BOUNDING BOX INSPECTION: {pdf_path.name} ({scale}x)")
    print(f"{'=' * 80}\n")

    # Configure with parsed pages enabled
    pipeline = PdfPipelineOptions(
        layout_options=LayoutOptions(),
        generate_parsed_pages=True,  # CRITICAL
        generate_page_images=True,
        images_scale=scale,
        do_table_structure=True,
        table_structure_options=dict(
            mode=TableFormerMode.ACCURATE,
            do_cell_matching=False,
        ),
        do_ocr=True,
    )

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    # Convert
    result = converter.convert(str(pdf_path))

    print("Checking DoclingDocument structure...")
    print(f"  Type: {type(result.document)}")
    print(f"  Has 'pages' attr: {hasattr(result.document, 'pages')}")
    print(f"  Has 'body' attr: {hasattr(result.document, 'body')}")

    # Try to access parsed pages from ConversionResult
    if hasattr(result, "pages"):
        print("\n✅ result.pages exists!")
        print(f"  Number of pages: {len(result.pages) if result.pages else 0}")

        if result.pages:
            # Analyze first page
            first_page = result.pages[0]
            print(f"\n  First page type: {type(first_page)}")
            print(f"  First page attributes: {dir(first_page)}")

            # Look for layout/predictions
            for attr in ["predictions", "layout", "elements", "boxes", "annotations"]:
                if hasattr(first_page, attr):
                    val = getattr(first_page, attr)
                    print(f"    ✅ Has {attr}: {type(val)}")

                    # Explore the object structure
                    if val:
                        print(
                            f"      Object attributes: {[a for a in dir(val) if not a.startswith('_')][:15]}"
                        )

                        # Try to iterate or access common properties
                        try:
                            # Check if it's iterable
                            items = (
                                list(val)
                                if hasattr(val, "__iter__") and not isinstance(val, str)
                                else None
                            )
                            if items:
                                print(f"      ✅ Iterable! Found {len(items)} items")
                                if items:
                                    first_elem = items[0]
                                    print(f"        First element type: {type(first_elem)}")
                                    print(
                                        f"        First element attributes: {[a for a in dir(first_elem) if not a.startswith('_')][:15]}"
                                    )

                                    # Look for label
                                    for label_attr in [
                                        "label",
                                        "class_name",
                                        "type",
                                        "category",
                                        "class_id",
                                    ]:
                                        if hasattr(first_elem, label_attr):
                                            print(
                                                f"          ✅ Label: {label_attr} = {getattr(first_elem, label_attr)}"
                                            )

                                    # Look for bbox
                                    for bbox_attr in [
                                        "bbox",
                                        "box",
                                        "coordinates",
                                        "geometry",
                                        "bounding_box",
                                    ]:
                                        if hasattr(first_elem, bbox_attr):
                                            print(
                                                f"          ✅ Bbox: {bbox_attr} = {getattr(first_elem, bbox_attr)}"
                                            )
                        except Exception as e:
                            print(f"      ❌ Error exploring: {e}")

                            # Try accessing as object properties
                            for prop in ["layout", "boxes", "regions", "elements"]:
                                if hasattr(val, prop):
                                    prop_val = getattr(val, prop)
                                    print(f"      Has property '{prop}': {type(prop_val)}")
                                    if prop_val and hasattr(prop_val, "__len__"):
                                        print(f"        Length: {len(prop_val)}")
    else:
        print("\n❌ result.pages does NOT exist")

    # Try alternative: look in document.body
    print(f"\n{'=' * 80}")
    print("Checking document.body structure...")
    print(f"{'=' * 80}")

    doc = result.document
    item_count = 0
    label_counts = Counter()

    for item, level in doc.iterate_items():
        item_count += 1
        if hasattr(item, "label"):
            label_counts[str(item.label)] += 1

    print(f"\nTotal items in document.body: {item_count}")
    print("\nLabel distribution:")
    for label, count in label_counts.most_common():
        print(f"  {label:30} : {count:>4}")

    # Save structured data
    return {
        "has_pages": hasattr(result, "pages"),
        "num_pages": len(result.pages) if hasattr(result, "pages") and result.pages else 0,
        "item_count": item_count,
        "label_counts": dict(label_counts),
    }


def main():
    """Inspect bounding boxes from 1x scaling test."""

    base_dir = Path(__file__).parent
    test_pdf = base_dir / "test_corpus" / "law_reviews" / "Jackson_2014.pdf"

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return

    # Just test 1x for now
    result = inspect_bounding_boxes(test_pdf, scale=1.0)

    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

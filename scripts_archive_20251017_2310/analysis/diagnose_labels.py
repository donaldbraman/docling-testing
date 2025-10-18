#!/usr/bin/env python3
"""Diagnose what labels are assigned to different types of content."""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    LayoutOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def diagnose_labels(pdf_path: Path):
    """Extract and display items with their labels to diagnose footnote detection."""

    print(f"\n{'=' * 80}")
    print(f"LABEL DIAGNOSIS: {pdf_path.name}")
    print(f"{'=' * 80}\n")

    # Use default config
    pipeline = PdfPipelineOptions(
        layout_options=LayoutOptions(),
        generate_parsed_pages=True,
        generate_page_images=True,
        images_scale=1.0,
        do_table_structure=True,
        do_ocr=True,
    )

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    print("Converting document...")
    result = converter.convert(str(pdf_path))
    doc = result.document

    print("\n" + "=" * 80)
    print("SAMPLE ITEMS BY LABEL")
    print("=" * 80 + "\n")

    # Collect samples by label
    label_samples = {}

    for item, level in doc.iterate_items():
        label = str(item.label) if hasattr(item, "label") else "NO_LABEL"
        text = item.text if hasattr(item, "text") else ""

        if text and label not in label_samples:
            label_samples[label] = []

        if text and len(label_samples[label]) < 3:  # Keep first 3 samples
            label_samples[label].append(text[:200])  # First 200 chars

    # Print samples
    for label in sorted(label_samples.keys()):
        print(f"\n{'=' * 80}")
        print(f"LABEL: {label}")
        print(f"{'=' * 80}")
        for i, sample in enumerate(label_samples[label], 1):
            print(f"\n  Sample {i}:")
            print(f"  {sample}")
            if len(sample) == 200:
                print("  ...")

    # Now let's look specifically for citation-like patterns
    print("\n\n" + "=" * 80)
    print("ITEMS WITH CITATION PATTERNS")
    print("=" * 80 + "\n")

    citation_patterns = []
    for item, level in doc.iterate_items():
        label = str(item.label) if hasattr(item, "label") else "NO_LABEL"
        text = (item.text if hasattr(item, "text") else "").strip()

        # Look for short items that start with "See" or case citations
        if text and (
            text.startswith("See ")
            or text.startswith("Id.")
            or text.startswith("Ibid.")
            or (len(text) < 100 and " U.S. " in text and "(" in text)
        ):
            citation_patterns.append({"label": label, "text": text[:150]})

            if len(citation_patterns) >= 20:  # Just show first 20
                break

    for item in citation_patterns:
        print(f"\nLabel: {item['label']:20} | Text: {item['text']}")


def main():
    base_dir = Path(__file__).parent
    test_pdf = base_dir / "test_corpus" / "law_reviews" / "Jackson_2014.pdf"

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return

    diagnose_labels(test_pdf)


if __name__ == "__main__":
    main()

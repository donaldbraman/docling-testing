#!/usr/bin/env python3
"""Validate Docling's label assignments by examining actual content."""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def validate_labels(pdf_path: Path):
    """Examine Docling's labels and show content for manual validation."""

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=PdfPipelineOptions())}
    )
    result = converter.convert(str(pdf_path))

    print(f"\nVALIDATING: {pdf_path.name}")
    print("=" * 80)

    # Group items by label
    by_label = {}
    for item, _level in result.document.iterate_items():
        if hasattr(item, "text") and item.text:
            label = str(item.label) if hasattr(item, "label") else "unknown"
            if label not in by_label:
                by_label[label] = []
            by_label[label].append(item.text)

    # Show all items grouped by label
    for label in sorted(by_label.keys()):
        items = by_label[label]
        print(f"\n{'=' * 80}")
        print(f"{label.upper()} ({len(items)} instances)")
        print("=" * 80)

        for i, text in enumerate(items, 1):
            # Clean text for display
            display_text = text.replace("\n", " ").strip()
            if len(display_text) > 200:
                display_text = display_text[:200] + "..."

            print(f"\n[{i}] {display_text}")

    # Check for missing elements
    print(f"\n\n{'=' * 80}")
    print("POTENTIAL ISSUES")
    print("=" * 80)

    issues = []

    if "title" not in by_label:
        issues.append("⚠️  NO TITLE detected - Every article should have a title")

    if "page_header" not in by_label:
        issues.append("⚠️  NO PAGE_HEADER detected - Most journals have running headers")

    if "page_footer" not in by_label:
        issues.append("⚠️  NO PAGE_FOOTER detected - Most journals have page numbers")

    if "reference" not in by_label:
        issues.append("ℹ️  NO REFERENCE section - May be a short article without bibliography")

    # Check for suspiciously low text count
    text_count = len(by_label.get("text", []))
    if text_count < 10:
        issues.append(f"⚠️  Very few TEXT blocks ({text_count}) - May be under-segmenting")

    if issues:
        for issue in issues:
            print(issue)
    else:
        print("✓ No obvious issues detected")


def main():
    """Validate labels on sample PDFs."""

    # Test on a few representative PDFs
    test_pdfs = [
        Path("data/raw_pdf/bu_law_review_online_fourth_amendment_secure.pdf"),
        # Add more when available
    ]

    for pdf_path in test_pdfs:
        if pdf_path.exists():
            validate_labels(pdf_path)
        else:
            print(f"⚠️  File not found: {pdf_path}")


if __name__ == "__main__":
    main()

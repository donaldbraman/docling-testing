#!/usr/bin/env python3
"""Diagnose how Docling labels specific footnote citations."""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def diagnose_labels(pdf_path: Path):
    """Show labels for specific citation patterns."""

    # Use default configuration
    pipeline = PdfPipelineOptions(
        layout_options=LayoutOptions(),
        generate_parsed_pages=True,
        generate_page_images=True,
        images_scale=1.0,
    )

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    # Convert
    result = converter.convert(str(pdf_path))
    doc = result.document

    # Look for the specific patterns we found
    target_patterns = [
        "Cf. Fallon, supra note",
        "Cf. SULLIVAN & FRASE",
        "Compare Plyler v. Doe",
        "E.g., United States v. Alvarez",
        "395 U.S.  444",
        "561 U.S.  1",
    ]

    print(f"\n{'=' * 80}")
    print(f"DIAGNOSING LABELS: {pdf_path.name}")
    print(f"{'=' * 80}\n")

    found = []

    for item, level in doc.iterate_items():
        text = item.text if hasattr(item, "text") else ""
        label = str(item.label) if hasattr(item, "label") else "NO_LABEL"

        # Check if this item contains any of our target patterns
        for pattern in target_patterns:
            if pattern in text:
                found.append(
                    {
                        "pattern": pattern,
                        "label": label,
                        "text_preview": text[:150],
                        "length": len(text),
                    }
                )

    # Report findings
    print(f"Found {len(found)} items matching target patterns:\n")

    for i, item in enumerate(found, 1):
        print(f"\n{i}. Pattern: {item['pattern']}")
        print(f"   Label: {item['label']}")
        print(f"   Length: {item['length']} chars")
        print(f"   Preview: {item['text_preview'][:100]}...")
        print()

    # Summary of labels used
    label_summary = {}
    for item in found:
        label = item["label"]
        label_summary[label] = label_summary.get(label, 0) + 1

    print(f"\n{'=' * 80}")
    print("LABEL SUMMARY FOR MISSED FOOTNOTES:")
    print(f"{'=' * 80}\n")

    for label, count in sorted(label_summary.items(), key=lambda x: -x[1]):
        print(f"  {label:30} : {count} items")

    print("\n💡 Key insight:")
    print(
        f"   Docling labeled these citations as '{list(label_summary.keys())[0] if label_summary else 'unknown'}'"
    )
    print("   instead of 'footnote', so they passed through our initial filter.")
    print("   Our heuristic should catch them based on citation patterns.")


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    test_pdf = base_dir / "test_corpus" / "law_reviews" / "Jackson_2014.pdf"

    if test_pdf.exists():
        diagnose_labels(test_pdf)
    else:
        print(f"❌ PDF not found: {test_pdf}")

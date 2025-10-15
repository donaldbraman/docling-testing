#!/usr/bin/env python3
"""Extract body text only, excluding footnotes, headers, and footers."""

import re
import time
from collections import Counter
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    LayoutOptions,
    PdfPipelineOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def calculate_citation_density(text: str) -> float:
    """Calculate what percentage of text consists of citation markers."""

    # Patterns that indicate citation content
    citation_patterns = [
        r"\d+\s+U\.S\.\s+\d+",  # Case citations
        r"\d+\s+S\.\s+Ct\.\s+\d+",
        r"\d+\s+[A-Z][a-z]*\.\s+L\.\s+R[Ee][Vv]\.",  # Law review citations
        r"\(\d{4}\)",  # Years in parens
        r"\bsupra note\s+\d+",  # Cross-references
        r"\binfra note\s+\d+",
        r"\[hereinafter\s+",  # Hereinafter clauses
    ]

    total_chars = len(text)
    if total_chars == 0:
        return 0.0

    citation_chars = 0
    for pattern in citation_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            citation_chars += len(match.group())

    return citation_chars / total_chars


def is_likely_citation(text: str) -> bool:
    """
    Detect if an item is actually a footnote citation.

    Legal citations are typically short and match specific patterns:
    - Case citations: "132 S. Ct. 2537 (2012)"
    - Reference markers: "See", "Id.", "Ibid."
    - Cross-references: "See supra note 116"
    - High citation density (for longer items)
    """
    text = text.strip()

    # Very short standalone case citations (just reporter + year)
    # Example: "554 U.S. 570 (2008)."
    if len(text) < 60 and re.match(r"^\d+\s+[A-Z]", text) and re.search(r"\(\d{4}\)", text):
        return True

    # Short items with case citations: numbers, reporter abbreviations, year in parens
    # Pattern: digits ... reporter abbrev ... digits ... (year)
    if len(text) < 100 and re.search(
        r"\d+.*?(U\.S\.|S\. ?Ct\.|F\.\d?d|P\.\d?d).*?\d+.*?\(\d{4}\)", text[:80]
    ):
        return True

    # Items that start with common citation signals (short items only)
    if len(text) < 200 and re.match(
        r"^(See|Id\.|Ibid\.|Compare|But see|Cf\.)", text, re.IGNORECASE
    ):
        return True

    # Very short items that are mostly case citations
    # Example: "471 U.S. 1 (1985)."
    if len(text) < 50 and re.search(r"\d+.*?(U\.S\.|S\. ?Ct\.|F\.\d?d).*?\d+", text):
        return True

    # Items with "supra note" or "infra note" (cross-references to footnotes)
    if len(text) < 150 and re.search(r"(supra|infra) note", text):
        return True

    # Items with "hereinafter" clauses (ONLY used in footnotes)
    if re.search(r"\[hereinafter\s+", text):
        return True

    # NEW: Check citation density for longer items
    # Items with >20% citation density are likely footnotes
    if len(text) >= 200 and calculate_citation_density(text) > 0.20:
        return True

    # Medium-length items with high citation density and citation signals
    if 200 <= len(text) < 400 and calculate_citation_density(text) > 0.08:
        if re.search(r"\bsee\b", text, re.IGNORECASE) or re.search(r"\bId\.\s+at", text):
            return True

    return False


def extract_body_text(pdf_path: Path, output_dir: Path, config: str = "default") -> dict:
    """
    Extract body text only, filtering out footnotes.

    Args:
        pdf_path: Path to PDF
        output_dir: Where to save results
        config: "default" or "optimized"
    """
    print(f"\n{'=' * 80}")
    print(f"BODY TEXT EXTRACTION: {pdf_path.name} ({config} config)")
    print(f"{'=' * 80}\n")

    start_time = time.time()

    # Configure pipeline
    if config == "optimized":
        layout_opts = LayoutOptions()
        layout_opts.model_spec = "heron-101"
        layout_opts.single_column_fallback = True

        pipeline = PdfPipelineOptions(
            layout_options=layout_opts,
            generate_parsed_pages=True,
            generate_page_images=True,
            images_scale=2.0,
            do_table_structure=True,
            table_structure_options=dict(
                mode=TableFormerMode.ACCURATE,
                do_cell_matching=False,
            ),
            do_ocr=True,
        )
    else:
        # Default configuration (what we've been using)
        pipeline = PdfPipelineOptions(
            layout_options=LayoutOptions(),
            generate_parsed_pages=True,
            generate_page_images=True,
            images_scale=1.0,
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

    # Convert document
    result = converter.convert(str(pdf_path))
    doc = result.document

    elapsed = time.time() - start_time

    # Analyze all items and their labels
    label_counts = Counter()
    body_text_parts = []
    footnote_parts = []
    all_text_parts = []
    citations_caught = []  # Track citations detected by heuristic

    for item, level in doc.iterate_items():
        label = str(item.label) if hasattr(item, "label") else "NO_LABEL"
        label_counts[label] += 1

        # Get text content
        text = item.text if hasattr(item, "text") else ""

        if text:
            all_text_parts.append(text)

            # Filter based on label AND citation detection
            if "footnote" in label.lower():
                # Explicitly labeled as footnote
                footnote_parts.append(text)
            elif is_likely_citation(text):
                # Detected as citation by heuristic (any label)
                footnote_parts.append(text)
                citations_caught.append(text[:80])  # Store preview for reporting
            elif label.lower() in ["text", "section_header", "list_item", "paragraph"]:
                # Body content (after filtering out citations)
                body_text_parts.append(text)

    # Create outputs
    all_text = "\n\n".join(all_text_parts)
    body_only = "\n\n".join(body_text_parts)
    footnotes_only = "\n\n".join(footnote_parts)

    # Save outputs
    all_path = output_dir / f"{pdf_path.stem}_{config}_all.txt"
    body_path = output_dir / f"{pdf_path.stem}_{config}_body_only.txt"
    footnotes_path = output_dir / f"{pdf_path.stem}_{config}_footnotes_only.txt"

    all_path.write_text(all_text, encoding="utf-8")
    body_path.write_text(body_only, encoding="utf-8")
    footnotes_path.write_text(footnotes_only, encoding="utf-8")

    # Metrics
    metrics = {
        "config": config,
        "elapsed_seconds": round(elapsed, 2),
        "total_items": sum(label_counts.values()),
        "label_counts": dict(label_counts),
        "all_text_length": len(all_text),
        "all_text_words": len(all_text.split()),
        "body_text_length": len(body_only),
        "body_text_words": len(body_only.split()),
        "footnote_text_length": len(footnotes_only),
        "footnote_text_words": len(footnotes_only.split()),
        "hyphen_all": all_text.count("-\n"),
        "hyphen_body": body_only.count("-\n"),
        "citations_caught": len(citations_caught),
        "citations_preview": citations_caught[:5],  # First 5 examples
    }

    # Print results
    print("✅ Extraction complete!")
    print(f"   Time: {metrics['elapsed_seconds']}s ({metrics['elapsed_seconds'] / 60:.1f} min)")
    print("\n   Label distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"     {label:30} : {count:>4}")

    print("\n   Text statistics:")
    print(f"     All text: {metrics['all_text_words']:,} words")
    print(f"     Body only: {metrics['body_text_words']:,} words")
    print(f"     Footnotes: {metrics['footnote_text_words']:,} words")
    print(
        f"     Removed: {metrics['all_text_words'] - metrics['body_text_words']:,} words ({100 * (1 - metrics['body_text_words'] / metrics['all_text_words']):.1f}%)"
    )

    print("\n   Hyphenation artifacts:")
    print(f"     All text: {metrics['hyphen_all']}")
    print(f"     Body only: {metrics['hyphen_body']}")

    print("\n   Citation detection:")
    print(f"     List_items caught as citations: {metrics['citations_caught']}")
    if metrics["citations_preview"]:
        print("     Examples:")
        for citation in metrics["citations_preview"]:
            print(f"       - {citation}")

    print("\n   Outputs saved:")
    print(f"     All text: {all_path}")
    print(f"     Body only: {body_path}")
    print(f"     Footnotes: {footnotes_path}")

    return metrics


def main():
    """Test body text extraction with default and optimized configs."""

    base_dir = Path(__file__).parent
    test_corpus = base_dir / "test_corpus" / "law_reviews"
    output_dir = base_dir / "results" / "body_extraction"
    output_dir.mkdir(parents=True, exist_ok=True)

    test_pdf = test_corpus / "Jackson_2014.pdf"

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return

    print("\n🔬 BODY TEXT EXTRACTION TEST")
    print(f"Test document: {test_pdf.name}")
    print("Hardware: M1 Pro with 32GB RAM")
    print()

    # Test with default config
    print("\n" + "=" * 80)
    print("TEST 1: DEFAULT CONFIGURATION")
    print("=" * 80)

    try:
        default_metrics = extract_body_text(test_pdf, output_dir, config="default")
    except Exception as e:
        print(f"❌ Error with default config: {e}")
        import traceback

        traceback.print_exc()
        default_metrics = None

    # Test with optimized config
    print("\n" + "=" * 80)
    print("TEST 2: OPTIMIZED CONFIGURATION")
    print("=" * 80)

    try:
        optimized_metrics = extract_body_text(test_pdf, output_dir, config="optimized")
    except Exception as e:
        print(f"❌ Error with optimized config: {e}")
        import traceback

        traceback.print_exc()
        optimized_metrics = None

    # Comparison
    if default_metrics and optimized_metrics:
        print(f"\n{'=' * 80}")
        print("COMPARISON: DEFAULT vs OPTIMIZED")
        print(f"{'=' * 80}\n")

        print(f"{'Metric':<30} {'Default':<20} {'Optimized':<20}")
        print("-" * 80)
        print(
            f"{'Processing time (s)':<30} {default_metrics['elapsed_seconds']:<20} {optimized_metrics['elapsed_seconds']:<20}"
        )
        print(
            f"{'Footnotes detected':<30} {default_metrics['label_counts'].get('footnote', 0):<20} {optimized_metrics['label_counts'].get('footnote', 0):<20}"
        )
        print(
            f"{'Body text words':<30} {default_metrics['body_text_words']:<20,} {optimized_metrics['body_text_words']:<20,}"
        )
        print(
            f"{'Footnote words removed':<30} {default_metrics['footnote_text_words']:<20,} {optimized_metrics['footnote_text_words']:<20,}"
        )
        print(
            f"{'Hyphenation (body)':<30} {default_metrics['hyphen_body']:<20} {optimized_metrics['hyphen_body']:<20}"
        )

        print(f"\n📁 Results saved to: {output_dir}")


if __name__ == "__main__":
    main()

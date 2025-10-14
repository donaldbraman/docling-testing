#!/usr/bin/env python3
"""Parse an existing Docling result without re-extracting."""

import pickle
from pathlib import Path
from collections import Counter


def parse_saved_docling_result(doc_pickle_path: Path, output_dir: Path) -> dict:
    """
    Load a saved DoclingDocument and extract body text.

    Args:
        doc_pickle_path: Path to pickled DoclingDocument
        output_dir: Where to save parsed results
    """
    print(f"\n{'='*80}")
    print(f"PARSING SAVED RESULT: {doc_pickle_path.name}")
    print(f"{'='*80}\n")

    # Load pickled document
    with open(doc_pickle_path, 'rb') as f:
        doc = pickle.load(f)

    print(f"✅ Loaded DoclingDocument from {doc_pickle_path}")

    # Analyze all items and their labels
    label_counts = Counter()
    body_text_parts = []
    footnote_parts = []
    all_text_parts = []

    for item, level in doc.iterate_items():
        label = str(item.label) if hasattr(item, 'label') else "NO_LABEL"
        label_counts[label] += 1

        # Get text content
        text = item.text if hasattr(item, 'text') else ""

        if text:
            all_text_parts.append(text)

            # Filter based on label
            if 'footnote' in label.lower():
                footnote_parts.append(text)
            elif label.lower() in ['text', 'section_header', 'list_item', 'paragraph']:
                body_text_parts.append(text)

    # Create outputs
    all_text = '\n\n'.join(all_text_parts)
    body_only = '\n\n'.join(body_text_parts)
    footnotes_only = '\n\n'.join(footnote_parts)

    # Save outputs
    base_name = doc_pickle_path.stem.replace('_doc', '')
    all_path = output_dir / f"{base_name}_parsed_all.txt"
    body_path = output_dir / f"{base_name}_parsed_body_only.txt"
    footnotes_path = output_dir / f"{base_name}_parsed_footnotes_only.txt"

    all_path.write_text(all_text, encoding='utf-8')
    body_path.write_text(body_only, encoding='utf-8')
    footnotes_path.write_text(footnotes_only, encoding='utf-8')

    # Metrics
    metrics = {
        "source": "parsed_saved",
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
    }

    # Print results
    print(f"✅ Parsing complete!")
    print(f"\n   Label distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"     {label:30} : {count:>4}")

    print(f"\n   Text statistics:")
    print(f"     All text: {metrics['all_text_words']:,} words")
    print(f"     Body only: {metrics['body_text_words']:,} words")
    print(f"     Footnotes: {metrics['footnote_text_words']:,} words")
    print(f"     Removed: {metrics['all_text_words'] - metrics['body_text_words']:,} words ({100 * (1 - metrics['body_text_words'] / metrics['all_text_words']):.1f}%)")

    print(f"\n   Hyphenation artifacts:")
    print(f"     All text: {metrics['hyphen_all']}")
    print(f"     Body only: {metrics['hyphen_body']}")

    print(f"\n   Outputs saved:")
    print(f"     All text: {all_path}")
    print(f"     Body only: {body_path}")
    print(f"     Footnotes: {footnotes_path}")

    return metrics


def save_docling_document(pdf_path: Path, config: str, output_dir: Path):
    """Extract and save a DoclingDocument for later parsing."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TableFormerMode,
        LayoutOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption
    import time

    print(f"\n{'='*80}")
    print(f"EXTRACTING AND SAVING: {pdf_path.name} ({config} config)")
    print(f"{'='*80}\n")

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
        # Default configuration
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
    print("Converting document...")
    result = converter.convert(str(pdf_path))
    doc = result.document

    elapsed = time.time() - start_time
    print(f"✅ Conversion complete in {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # Save the DoclingDocument
    doc_pickle_path = output_dir / f"{pdf_path.stem}_{config}_doc.pkl"
    with open(doc_pickle_path, 'wb') as f:
        pickle.dump(doc, f)

    print(f"✅ Saved DoclingDocument to {doc_pickle_path}")

    return doc_pickle_path, elapsed


def main():
    """Test parsing saved vs fresh extraction."""
    base_dir = Path(__file__).parent
    test_corpus = base_dir / "test_corpus" / "law_reviews"
    output_dir = base_dir / "results" / "saved_vs_fresh"
    output_dir.mkdir(parents=True, exist_ok=True)

    test_pdf = test_corpus / "Jackson_2014.pdf"

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return

    print(f"\n🔬 SAVED vs FRESH COMPARISON TEST")
    print(f"Test document: {test_pdf.name}")
    print()

    # Step 1: Extract and save DoclingDocument with default config
    print("\n" + "="*80)
    print("STEP 1: EXTRACT AND SAVE (default config)")
    print("="*80)

    doc_pickle_path, extraction_time = save_docling_document(
        test_pdf, "default", output_dir
    )

    # Step 2: Parse the saved document
    print("\n" + "="*80)
    print("STEP 2: PARSE SAVED DOCUMENT")
    print("="*80)

    parsed_metrics = parse_saved_docling_result(doc_pickle_path, output_dir)

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")
    print(f"Extraction time: {extraction_time:.1f}s ({extraction_time/60:.1f} min)")
    print(f"Parsing time: Instant (no re-extraction)")
    print(f"\nFootnotes detected: {parsed_metrics['label_counts'].get('footnote', 0)}")
    print(f"Body text words: {parsed_metrics['body_text_words']:,}")
    print(f"Footnote words removed: {parsed_metrics['footnote_text_words']:,}")
    print(f"Removal rate: {100 * (1 - parsed_metrics['body_text_words'] / parsed_metrics['all_text_words']):.1f}%")

    print(f"\n📁 Results saved to: {output_dir}")


if __name__ == "__main__":
    main()

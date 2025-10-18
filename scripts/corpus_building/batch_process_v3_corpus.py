#!/usr/bin/env python3
"""
Batch process entire V3 corpus through Docling extraction and fuzzy matching.

This script runs the complete V3 pipeline:
1. Extract all PDFs with Docling (default settings)
2. Relabel extractions using sequential fuzzy matching with HTML ground truth
3. Generate summary statistics

Author: Claude Code
Date: 2025-01-18
"""

import json
from pathlib import Path

from docling.document_converter import DocumentConverter


def extract_all_pdfs():
    """Extract all PDFs in v3_data/raw_pdf/ using Docling."""
    raw_pdf_dir = Path("data/v3_data/raw_pdf")
    output_dir = Path("data/v3_data/docling_extraction")
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(raw_pdf_dir.glob("*.pdf"))
    print(f"{'=' * 80}")
    print(f"Step 1: Extracting {len(pdf_files)} PDFs with Docling")
    print(f"{'=' * 80}\n")

    # Initialize converter once for all PDFs
    converter = DocumentConverter()

    for idx, pdf_path in enumerate(pdf_files, 1):
        output_file = output_dir / f"{pdf_path.stem}.json"

        # Skip if already extracted
        if output_file.exists():
            print(f"[{idx}/{len(pdf_files)}] ⏭️  Skipping {pdf_path.name} (already extracted)")
            continue

        print(f"[{idx}/{len(pdf_files)}] 📄 Processing {pdf_path.name}...", end=" ", flush=True)

        try:
            # Convert the document
            result = converter.convert(pdf_path)

            # Export to JSON
            if hasattr(result, "document") and hasattr(result.document, "export_to_dict"):
                doc_dict = result.document.export_to_dict()
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(doc_dict, f, ensure_ascii=False, indent=2)
                print(f"✅ ({len(doc_dict.get('texts', []))} text items)")
            else:
                print("❌ Failed to export")
        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\n✅ Docling extraction complete: {len(list(output_dir.glob('*.json')))} files\n")


def relabel_all_extractions():
    """Relabel all Docling extractions using fuzzy matching with HTML ground truth."""
    import sys

    processed_html_dir = Path("data/v3_data/processed_html")
    relabeled_dir = Path("data/v3_data/relabeled_extraction")
    html_files = sorted(processed_html_dir.glob("*.json"))

    print(f"{'=' * 80}")
    print(f"Step 2: Relabeling {len(html_files)} extractions with fuzzy matching")
    print(f"{'=' * 80}\n")

    # Import the relabeling function dynamically
    sys.path.insert(0, str(Path(__file__).parent))
    from relabel_with_sequential_fuzzy_matching import process_single_article

    success_count = 0
    skip_count = 0

    for idx, html_file in enumerate(html_files, 1):
        basename = html_file.stem
        output_file = relabeled_dir / f"{basename}.json"

        # Skip if already processed
        if output_file.exists():
            print(f"[{idx}/{len(html_files)}] ⏭️  Skipping {basename} (already relabeled)")
            skip_count += 1
            continue

        print(f"[{idx}/{len(html_files)}] 🔄 Relabeling {basename}...", end=" ", flush=True)

        try:
            process_single_article(basename, quiet=True)
            print("✅")
            success_count += 1
        except Exception as e:
            print(f"❌ Error: {e}")

    print(
        f"\n✅ Relabeling complete: {success_count} new, {skip_count} skipped, {len(html_files)} total\n"
    )


def generate_summary_stats():
    """Generate summary statistics for the complete V3 corpus."""
    relabeled_dir = Path("data/v3_data/relabeled_extraction")
    json_files = sorted(relabeled_dir.glob("*.json"))

    print(f"{'=' * 80}")
    print("V3 Corpus Summary Statistics")
    print(f"{'=' * 80}\n")

    total_blocks = 0
    total_body_text = 0
    total_footnotes = 0
    total_section_headers = 0
    total_other = 0
    total_matched = 0
    total_unmatched = 0

    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)

        for block in data["text_blocks"]:
            total_blocks += 1
            if block["matched"]:
                total_matched += 1
            else:
                total_unmatched += 1

            label = block["corrected_label"]
            if label == "body_text":
                total_body_text += 1
            elif label == "footnote":
                total_footnotes += 1
            elif label == "section_header":
                total_section_headers += 1
            else:
                total_other += 1

    print(f"Total articles: {len(json_files)}")
    print(f"Total text blocks: {total_blocks:,}")
    print("\nLabel distribution:")
    print(f"  Body text:       {total_body_text:5,} ({total_body_text / total_blocks * 100:.1f}%)")
    print(f"  Footnotes:       {total_footnotes:5,} ({total_footnotes / total_blocks * 100:.1f}%)")
    print(
        f"  Section headers: {total_section_headers:5,} ({total_section_headers / total_blocks * 100:.1f}%)"
    )
    print(f"  Other:           {total_other:5,} ({total_other / total_blocks * 100:.1f}%)")
    print("\nMatching statistics:")
    print(f"  Matched to HTML:   {total_matched:5,} ({total_matched / total_blocks * 100:.1f}%)")
    print(
        f"  Unmatched:         {total_unmatched:5,} ({total_unmatched / total_blocks * 100:.1f}%)"
    )
    print(f"\nTrainable samples (body_text + footnotes): {total_body_text + total_footnotes:,}")


def main():
    """Run complete V3 pipeline batch processing."""
    print("\n" + "=" * 80)
    print("V3 CORPUS BATCH PROCESSING")
    print("=" * 80 + "\n")

    # Step 1: Extract all PDFs with Docling
    extract_all_pdfs()

    # Step 2: Relabel all extractions with fuzzy matching
    relabel_all_extractions()

    # Step 3: Generate summary statistics
    generate_summary_stats()

    print("\n" + "=" * 80)
    print("✅ V3 CORPUS PROCESSING COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Review summary statistics above")
    print("  2. Inspect sample relabeled extractions in data/v3_data/relabeled_extraction/")
    print("  3. Prepare training data from relabeled extractions")
    print()


if __name__ == "__main__":
    main()

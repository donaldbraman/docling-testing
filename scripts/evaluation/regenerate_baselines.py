#!/usr/bin/env python3
"""
Regenerate baseline ocrmac extractions with proper text extraction.

Fixes the bug where Docling objects were serialized instead of extracting .text
"""

import json
import logging
from pathlib import Path

from docling.document_converter import DocumentConverter

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def regenerate_baseline(pdf_path: Path, output_path: Path) -> None:
    """Regenerate baseline extraction with proper text extraction.

    Args:
        pdf_path: Path to PDF
        output_path: Path to save corrected extraction
    """
    logger.info(f"Processing: {pdf_path.name}")

    converter = DocumentConverter()
    doc = converter.convert(str(pdf_path))

    # Extract text PROPERLY - get .text from each item
    all_text_blocks = []

    if doc.document.texts:
        all_text_blocks.extend([item.text for item in doc.document.texts])

    if doc.document.tables:
        for table in doc.document.tables:
            table_md = table.export_to_markdown(doc.document)
            if table_md:
                all_text_blocks.append(table_md)

    # Save with proper structure
    extraction_data = {
        "texts": all_text_blocks,  # Clean text strings, not objects!
        "markdown_full_text": doc.document.export_to_markdown(),
        "page_count": len(doc.pages) if doc.pages else 0,
        "metadata": {
            "pipeline": "baseline",
            "ocr_engine": "ocrmac",
            "text_blocks": len([item.text for item in doc.document.texts])
            if doc.document.texts
            else 0,
            "tables": len(list(doc.document.tables)) if doc.document.tables else 0,
        },
    }

    with open(output_path, "w") as f:
        json.dump(extraction_data, f, indent=2)  # No default=str needed!

    logger.info(
        f"  ✓ Saved: {len(all_text_blocks)} text blocks, {extraction_data['page_count']} pages"
    )


def main():
    """Regenerate all baseline extractions."""
    pdf_dir = Path("data/v3_data/raw_pdf")
    output_dir = Path("results/ocr_pipeline_evaluation/extractions")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get PDFs that have baseline extractions
    existing_baselines = list(output_dir.glob("*_baseline_extraction.json"))

    logger.info("=" * 80)
    logger.info("REGENERATING BASELINE EXTRACTIONS")
    logger.info("=" * 80)
    logger.info(f"Found {len(existing_baselines)} existing baseline files")
    logger.info("Regenerating with proper .text extraction...")
    logger.info("=" * 80)

    for i, baseline_path in enumerate(existing_baselines, 1):
        # Extract PDF name from baseline filename
        pdf_name = baseline_path.stem.replace("_baseline_extraction", "")
        pdf_path = pdf_dir / f"{pdf_name}.pdf"

        if not pdf_path.exists():
            logger.warning(f"[{i}/{len(existing_baselines)}] ⚠️  PDF not found: {pdf_name}")
            continue

        logger.info(f"\n[{i}/{len(existing_baselines)}] {pdf_name}")

        try:
            regenerate_baseline(pdf_path, baseline_path)
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("REGENERATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Regenerated {len(existing_baselines)} baseline files")
    logger.info("These now contain clean text strings instead of Docling objects")


if __name__ == "__main__":
    main()

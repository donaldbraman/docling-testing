#!/usr/bin/env python3
"""
Visualize missing paragraphs by overlaying colored rectangles on PDF.

Green = Found in Docling OCR
Red = Missing from Docling OCR
"""

import json
import re
from pathlib import Path

import fitz  # PyMuPDF


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text).lower()


def is_para_in_docling(para_text: str, docling_text_normalized: str) -> bool:
    """Check if paragraph exists in Docling OCR."""
    normalized = normalize_text(para_text)

    # Check if first 50 chars appear in Docling
    sample = normalized[:50] if len(normalized) > 50 else normalized

    return sample in docling_text_normalized


def main():
    """Create PDF overlay showing missing vs found paragraphs."""
    # Paths
    pdf_path = Path("data/v3_data/raw_pdf/usc_law_review_in_the_name_of_accountability.pdf")
    gt_path = Path("data/v3_data/processed_html/usc_law_review_in_the_name_of_accountability.json")
    docling_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only_baseline_extraction.json"
    )
    output_path = Path("results/missing_paragraphs_overlay.pdf")

    print("Loading data...")

    # Load ground truth
    with open(gt_path) as f:
        gt_data = json.load(f)

    # Load Docling OCR
    with open(docling_path) as f:
        docling_data = json.load(f)

    # Normalize Docling text
    docling_text = " ".join(docling_data["texts"])
    docling_normalized = normalize_text(docling_text)

    # Classify paragraphs
    found_paras = []
    missing_paras = []

    for para in gt_data["paragraphs"]:
        if is_para_in_docling(para["text"], docling_normalized):
            found_paras.append(para)
        else:
            missing_paras.append(para)

    print(f"Found in Docling: {len(found_paras)} paragraphs")
    print(f"Missing from Docling: {len(missing_paras)} paragraphs")

    # Open PDF
    doc = fitz.open(str(pdf_path))

    print("\\nSearching for paragraphs in PDF and highlighting...")

    # Track stats
    highlighted_count = 0
    not_found_in_pdf = 0

    # Create overlay by searching for each paragraph
    for para in gt_data["paragraphs"]:
        text = para["text"]

        # Check if found or missing in Docling
        is_found = is_para_in_docling(text, docling_normalized)

        # Color: green if found, red if missing
        color = (0, 1, 0) if is_found else (1, 0, 0)  # RGB

        # Search for multiple chunks of the paragraph to get better coverage
        # Split into chunks of 50 words each
        words = text.split()
        chunks = []
        for i in range(0, min(len(words), 150), 50):  # First 150 words, in 50-word chunks
            chunk = " ".join(words[i : i + 50])
            if chunk:
                chunks.append(chunk)

        # Search across all pages
        found_in_pdf = False
        for page_num, page in enumerate(doc):
            page_found = False

            # Try to find any chunk on this page
            for chunk in chunks:
                text_instances = page.search_for(chunk)

                if text_instances:
                    page_found = True
                    found_in_pdf = True
                    # Highlight all instances of this chunk
                    for inst in text_instances:
                        # Add highlight annotation
                        highlight = page.add_highlight_annot(inst)
                        highlight.set_colors(stroke=color)
                        highlight.set_opacity(0.5)
                        highlight.update()
                        highlighted_count += 1

            if page_found:
                break  # Found on this page, move to next paragraph

        if not found_in_pdf:
            not_found_in_pdf += 1

    print(f"  Highlighted {highlighted_count} text instances in PDF")
    print(f"  Could not find {not_found_in_pdf} paragraphs in PDF text layer")

    # Save
    doc.save(str(output_path))
    doc.close()

    print(f"\\n✓ Overlay PDF saved to: {output_path}")
    print(f"  Green = Found in Docling OCR ({len(found_paras)} paragraphs)")
    print(f"  Red = Missing from Docling OCR ({len(missing_paras)} paragraphs)")


if __name__ == "__main__":
    main()

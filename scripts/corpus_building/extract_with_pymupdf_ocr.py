#!/usr/bin/env python3
"""
Extract text blocks from PDF using PyMuPDF's OCR (Tesseract backend).

This is an alternative to extract_with_ocr.py that uses PyMuPDF's built-in OCR
instead of ocrmac. PyMuPDF uses Tesseract as its OCR engine.

Usage:
    uv run python scripts/corpus_building/extract_with_pymupdf_ocr.py --pdf political_mootness
    uv run python scripts/corpus_building/extract_with_pymupdf_ocr.py --pdf political_mootness --dpi 300
"""

import argparse
import re
import time
import unicodedata
from pathlib import Path

import fitz
import pandas as pd
from pymupdf4llm.helpers.get_text_lines import get_text_lines


def normalize_text_for_rag(text: str) -> str:
    """Normalize text for RAG: keep only letters, numbers, basic punctuation.

    Keeps:
    - English letters (a-z, A-Z)
    - Numbers (0-9)
    - Basic punctuation: . , ! ? : ; ' " - ( ) / &
    - Legal symbols: § ¶
    - Brackets: [ ] (heading indicators)
    - Accented Latin characters (proper names)
    - Whitespace

    Normalizes:
    - Smart quotes (' ' " ") → straight quotes (' ")
    - Em/en dashes (— –) → hyphen (-)

    Removes:
    - Emoji
    - Control characters
    - Other unicode symbols
    """
    # Normalize smart quotes and dashes
    text = text.replace(""", "'").replace(""", "'")  # U+2018, U+2019 → '
    text = text.replace('"', '"').replace('"', '"')  # U+201C, U+201D → "
    text = text.replace("—", "-").replace("–", "-")  # U+2014, U+2013 → -

    # Remove control characters (keep normal whitespace)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

    # Keep only allowed characters
    allowed_chars = []
    for char in text:
        # Keep ASCII letters, numbers, basic punctuation, whitespace
        if (
            char.isascii()
            and (char.isalnum() or char in " .,!?:;'\"-()[]/&\n\t")
            or char in "§¶"
            or char in "[]"
        ):
            allowed_chars.append(char)
        # Keep accented Latin characters (for proper names)
        elif unicodedata.category(char).startswith("L"):
            try:
                decomposed = unicodedata.normalize("NFD", char)
                if decomposed[0].isascii():
                    allowed_chars.append(char)
            except:
                pass

    text = "".join(allowed_chars)
    # Normalize whitespace (collapse multiple spaces, tabs, newlines)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def create_image_only_pdf(pdf_path: Path, output_dir: Path, dpi: int = 600) -> Path:
    """Create greyscale image-only PDF at specified DPI."""
    output_path = output_dir / f"{pdf_path.stem}_image_only_{dpi}dpi_pymupdf.pdf"

    if output_path.exists():
        print(f"  Using cached image-only PDF: {output_path.name}")
        return output_path

    print(f"  Creating greyscale image-only PDF at {dpi} DPI...")

    src_doc = fitz.open(str(pdf_path))
    total_pages = len(src_doc)

    img_doc = fitz.open()

    for i in range(total_pages):
        if (i + 1) % 10 == 0:
            print(f"    Page {i + 1}/{total_pages}...")

        page = src_doc[i]

        # Render to greyscale image at specified DPI
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)

        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)
        img_page.insert_image(img_page.rect, pixmap=pix)

    img_doc.save(str(output_path))
    img_doc.close()
    src_doc.close()

    print(f"  ✓ Created: {output_path.name} ({total_pages} pages)")
    return output_path


def extract_text_blocks_with_pymupdf_ocr(image_pdf: Path, dpi: int = 600) -> list[dict]:
    """Extract text blocks with bounding boxes using PyMuPDF's OCR (Tesseract).

    Returns list of dicts with:
        - page_number: 1-indexed page number
        - text: normalized text content
        - x0, y0, x1, y1: bounding box coordinates (normalized 0-1)
        - confidence: OCR confidence score (if available)
    """
    print(f"  Running OCR with PyMuPDF+Tesseract ({dpi} DPI)...")

    doc = fitz.open(str(image_pdf))
    total_pages = len(doc)

    all_blocks = []

    for page_idx in range(total_pages):
        page_num = page_idx + 1

        if page_num % 10 == 0:
            print(f"    Page {page_num}/{total_pages}...")

        page = doc[page_idx]
        page_width = page.rect.width
        page_height = page.rect.height

        # Run OCR on the page
        tp = page.get_textpage_ocr(language="eng", dpi=dpi, full=True)

        # Use pymupdf4llm's get_text_lines for line-level extraction
        # This reconstructs text lines intelligently from OCR spans
        lines = get_text_lines(page, textpage=tp)

        # Convert lines to blocks with bounding boxes
        all_lines = []
        for line_dict in lines:
            text = line_dict.get("text", "")
            bbox = line_dict.get("bbox")

            if text.strip() and bbox:
                all_lines.append((fitz.Rect(bbox), text))

        # Process each line
        for bbox, text in all_lines:
            normalized_text = normalize_text_for_rag(text)

            if normalized_text:  # Skip empty blocks after normalization
                # Normalize coordinates to 0-1
                # PyMuPDF uses top-origin (y=0 at top)
                x0_norm = bbox.x0 / page_width
                y0_norm = bbox.y0 / page_height
                x1_norm = bbox.x1 / page_width
                y1_norm = bbox.y1 / page_height

                all_blocks.append(
                    {
                        "page_number": page_num,
                        "text": normalized_text,
                        "x0": x0_norm,
                        "y0": y0_norm,
                        "x1": x1_norm,
                        "y1": y1_norm,
                        "confidence": 1.0,  # PyMuPDF doesn't provide confidence
                    }
                )

    doc.close()

    print(f"  ✓ Extracted {len(all_blocks)} text blocks from {total_pages} pages")
    return all_blocks


def calculate_features(blocks: list[dict]) -> pd.DataFrame:
    """Calculate features for classification.

    Features:
        - page_number: absolute page number (1-indexed)
        - y_position_normalized: vertical position [0.0, 1.0] where 0=top, 1=bottom
        - normalized_font_size: estimated from bbox height, normalized to page median
        - text: normalized text content
    """
    df = pd.DataFrame(blocks)

    # y_position_normalized is already provided (y0)
    df["y_position_normalized"] = df["y0"]

    # Estimate font size from bounding box height
    df["font_size"] = df["y1"] - df["y0"]

    # Calculate median font size per page for normalization
    page_medians = df.groupby("page_number")["font_size"].median().to_dict()
    df["normalized_font_size"] = df.apply(
        lambda row: row["font_size"] / page_medians[row["page_number"]]
        if page_medians[row["page_number"]] > 0
        else 1.0,
        axis=1,
    )

    # Select final columns (keep bounding boxes for visualization)
    feature_df = df[
        [
            "page_number",
            "y_position_normalized",
            "normalized_font_size",
            "text",
            "confidence",
            "x0",
            "y0",
            "x1",
            "y1",
        ]
    ]

    return feature_df


def main():
    parser = argparse.ArgumentParser(description="Extract text blocks from PDF using PyMuPDF OCR")
    parser.add_argument("--pdf", required=True, help="PDF name (without .pdf extension)")
    parser.add_argument(
        "--dpi", type=int, default=600, help="DPI for image rendering (default: 600)"
    )
    args = parser.parse_args()

    # Paths
    pdf_path = Path(f"data/v3_data/raw_pdf/{args.pdf}.pdf")
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return

    output_dir = Path("results/text_block_extraction")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("OCR Text Block Extraction (PyMuPDF+Tesseract)")
    print(f"{'=' * 60}")
    print(f"PDF: {args.pdf}")
    print(f"DPI: {args.dpi}")
    print("Engine: PyMuPDF+Tesseract")
    print()

    start_time = time.time()

    # Stage 1: Create image-only PDF
    print("[Stage 1] Creating image-only PDF...")
    image_pdf = create_image_only_pdf(pdf_path, output_dir, args.dpi)

    # Stage 2: Extract text blocks with OCR
    print("\n[Stage 2] Extracting text blocks with PyMuPDF OCR...")
    blocks = extract_text_blocks_with_pymupdf_ocr(image_pdf, args.dpi)

    # Stage 3: Calculate features
    print("\n[Stage 3] Calculating features...")
    df = calculate_features(blocks)

    # Save to CSV
    output_file = output_dir / f"{args.pdf}_{args.dpi}dpi_blocks_v1_pymupdf.csv"
    df.to_csv(output_file, index=False)

    elapsed = time.time() - start_time

    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    print(f"Blocks extracted: {len(df):,}")
    print(f"Total time: {elapsed:.1f}s")
    print(f"Speed: {len(df) / elapsed:.1f} blocks/sec")
    print()
    print(f"Output saved to: {output_file}")
    print()
    print("Next step: Auto-labeling (Stage 3)")
    print(
        f"  Run: uv run python scripts/corpus_building/auto_label_ocr_blocks.py --pdf {args.pdf} --dpi {args.dpi} --suffix _pymupdf"
    )


if __name__ == "__main__":
    main()

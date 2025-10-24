#!/usr/bin/env python3
"""
Extract text blocks from PDF using OCR for active learning pipeline.

This is Stage 2 of the active learning pipeline:
1. Converts PDF to greyscale image-only at 600 DPI
2. Runs ocrmac OCR with en-US language preference
3. Extracts text blocks with bounding boxes
4. Calculates features: page_number, y_position_normalized, normalized_font_size, text
5. Normalizes text for RAG
6. Outputs CSV: {pdf_name}_600dpi_blocks_v1.csv

Usage:
    uv run python scripts/corpus_building/extract_with_ocr.py --pdf political_mootness
    uv run python scripts/corpus_building/extract_with_ocr.py --pdf political_mootness --dpi 300
"""

import argparse
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd


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
    import fitz

    output_path = output_dir / f"{pdf_path.stem}_image_only_{dpi}dpi.pdf"

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


def extract_text_blocks_with_ocr(image_pdf: Path, dpi: int = 600) -> list[dict]:
    """Extract text blocks with bounding boxes using ocrmac.

    Returns list of dicts with:
        - page_number: 1-indexed page number
        - text: normalized text content
        - x0, y0, x1, y1: bounding box coordinates (normalized 0-1)
        - confidence: OCR confidence score
    """
    try:
        import fitz
        from ocrmac import ocrmac
        from pdf2image import convert_from_path
    except ImportError as e:
        raise ImportError(
            f"Missing dependency: {e}. Install: uv add ocrmac pdf2image pymupdf"
        ) from e

    print(f"  Running OCR with Apple Neural Engine (en-US, {dpi} DPI)...")

    # Get page dimensions from original PDF
    src_doc = fitz.open(str(image_pdf))
    page_dimensions = [(page.rect.width, page.rect.height) for page in src_doc]
    src_doc.close()

    # Convert PDF to images at matching DPI
    images = convert_from_path(str(image_pdf), dpi=dpi, grayscale=True)

    if len(images) != len(page_dimensions):
        raise ValueError(
            f"Page count mismatch: {len(images)} images vs {len(page_dimensions)} pages"
        )

    all_blocks = []
    total_pages = len(images)

    for page_idx, img in enumerate(images):
        page_num = page_idx + 1

        if page_num % 10 == 0:
            print(f"    Page {page_num}/{total_pages}...")

        # Save temporary image for ocrmac
        temp_img = f"/tmp/ocr_page_{page_idx}.png"
        img.save(temp_img)

        # Run OCR with English language preference
        annotations = ocrmac.OCR(
            temp_img, recognition_level="accurate", language_preference=["en-US"]
        ).recognize()

        # Get page dimensions
        page_width, page_height = page_dimensions[page_idx]

        # Extract blocks with bounding boxes
        for text, confidence, bbox in annotations:
            # bbox format from ocrmac: (x, y, width, height) normalized 0-1
            x, y, width, height = bbox

            # Convert to (x0, y0, x1, y1) format
            x0 = x
            y0 = y
            x1 = x + width
            y1 = y + height

            # Normalize text for RAG
            normalized_text = normalize_text_for_rag(text)

            if normalized_text:  # Skip empty blocks after normalization
                all_blocks.append(
                    {
                        "page_number": page_num,
                        "text": normalized_text,
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                        "confidence": confidence,
                    }
                )

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

    # y_position_normalized is already provided by ocrmac (y0)
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
    parser = argparse.ArgumentParser(description="Extract text blocks from PDF using OCR")
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
    print("OCR Text Block Extraction")
    print(f"{'=' * 60}")
    print(f"PDF: {args.pdf}")
    print(f"DPI: {args.dpi}")
    print("Engine: ocrmac (Neural Engine)")
    print("Language: en-US")
    print()

    start_time = time.time()

    # Stage 1: Create image-only PDF
    print("[Stage 1] Creating image-only PDF...")
    image_pdf = create_image_only_pdf(pdf_path, output_dir, args.dpi)

    # Stage 2: Extract text blocks with OCR
    print("\n[Stage 2] Extracting text blocks with OCR...")
    blocks = extract_text_blocks_with_ocr(image_pdf, args.dpi)

    # Stage 3: Calculate features
    print("\n[Stage 3] Calculating features...")
    df = calculate_features(blocks)

    # Save to CSV
    output_file = output_dir / f"{args.pdf}_{args.dpi}dpi_blocks_v1.csv"
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
    print("  Run: scripts/corpus_building/extract_text_blocks_simple.py")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate overlay PDFs showing extraction classifications.

Creates two PDFs:
1. Uncorrected: Shows Docling's original labels
2. Corrected: Shows fuzzy-matched corrected labels
"""

from pathlib import Path

import fitz  # PyMuPDF
from fuzzy_matcher import match_all_items
from parse_extraction import ExtractedItem, load_extraction
from prepare_matching_data import load_html_ground_truth

# Color scheme (RGB 0-255)
LABEL_COLORS = {
    "body-text": (0, 0, 255),  # Blue
    "footnote-text": (255, 0, 0),  # Red
    "section-header": (0, 255, 0),  # Green
    "title": (255, 255, 0),  # Yellow
    "page-header": (128, 128, 128),  # Gray
    "page-footer": (128, 128, 128),  # Gray
    "other": (200, 200, 200),  # Light gray
}

# Map Docling labels to our color scheme (for uncorrected version)
# Show Docling's original classifications with visible colors
DOCLING_TO_COLOR_LABEL = {
    "TEXT": "body-text",  # Docling's TEXT class (blue)
    "FOOTNOTE": "footnote-text",  # Docling's FOOTNOTE class (red)
    "SECTION_HEADER": "section-header",
    "PAGE_HEADER": "page-header",
    "PAGE_FOOTER": "page-footer",
    "LIST_ITEM": "other",
}

ALPHA = 0.4  # Transparency (increased for better visibility)


def rgb_to_fitz(rgb):
    """Convert RGB (0-255) to PyMuPDF format (0-1)."""
    return (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


def extract_line_level_text(pdf_path: Path) -> dict[int, list[dict]]:
    """
    Extract line-level text and bboxes from PDF.

    Returns:
        Dict mapping page_num (1-indexed) to list of lines, where each line is:
        {'text': str, 'bbox': (x0, y0, x1, y1)}
    """
    doc = fitz.open(pdf_path)
    lines_by_page = {}

    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        lines = []

        # Get text blocks from PyMuPDF
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                # Extract text from all spans in this line
                text = " ".join([span["text"] for span in line["spans"]])
                bbox = line["bbox"]  # (x0, y0, x1, y1) in PDF coordinates

                if text.strip():
                    lines.append({"text": text.strip(), "bbox": bbox})

        lines_by_page[page_num] = lines

    doc.close()
    return lines_by_page


def create_overlay_pdf(
    pdf_path: Path,
    items: list[ExtractedItem],
    label_map: dict[int, str],
    output_path: Path,
    title: str,
):
    """
    Create PDF with colored overlays.

    Args:
        pdf_path: Original PDF
        items: List of extraction items (used for uncorrected only)
        label_map: Dict mapping item index to label (for corrected version)
        output_path: Output PDF path
        title: "Uncorrected" or "Corrected"
    """
    doc = fitz.open(pdf_path)

    for item_idx, item in enumerate(items):
        if item.bbox is None:
            continue

        # Get label
        if label_map:
            # Corrected version
            label = label_map.get(item_idx, "other")
        else:
            # Uncorrected version - map Docling label
            label = DOCLING_TO_COLOR_LABEL.get(item.label, "other")

        # Get color
        color_label = label if label in LABEL_COLORS else "other"
        color = LABEL_COLORS[color_label]
        fitz_color = rgb_to_fitz(color)

        # Find page (0-indexed in PyMuPDF)
        page_idx = item.page_num - 1
        if page_idx < 0 or page_idx >= len(doc):
            continue

        page = doc[page_idx]

        # Docling uses BOTTOMLEFT origin with custom DPI scaling
        # Transform to PyMuPDF TOPLEFT origin at 72 DPI
        # Calculated from control points across page 5:
        # - "2025]" header: Docling (427.8, 2198.0) → PDF (137.5, 86.7)
        # - "See Keith L." footnote: Docling (456.6, 1144.2) → PDF (157.7, 426.3)
        # - "1963" header: Docling (1409.3, 2205.2) → PDF (452.5, 84.7)

        l, t, r, b = item.bbox

        # Constants derived from control points (page 5 headers)
        DOCLING_MAX_Y = 2205.68  # Maximum Y coordinate in Docling space
        X_SCALE = 0.320937
        X_OFFSET = 0.203006
        Y_SCALE = 0.322262
        Y_OFFSET = 84.225026

        # Apply transformation
        # X: simple scale + offset
        pdf_l = l * X_SCALE + X_OFFSET
        pdf_r = r * X_SCALE + X_OFFSET

        # Y: flip from BOTTOMLEFT to TOPLEFT, then scale + offset
        pdf_t = (DOCLING_MAX_Y - t) * Y_SCALE + Y_OFFSET
        pdf_b = (DOCLING_MAX_Y - b) * Y_SCALE + Y_OFFSET

        # Create rectangle (PyMuPDF expects TOPLEFT coords)
        rect = fitz.Rect(pdf_l, pdf_t, pdf_r, pdf_b)
        rect.normalize()  # Ensures x0 <= x1 and y0 <= y1

        # Draw filled rectangle with transparency (no stroke/outline)
        page.draw_rect(rect, fill=fitz_color, fill_opacity=ALPHA)

    # Add legend
    add_legend(doc[0], title)

    # Save
    doc.save(output_path)
    doc.close()

    print(f"✓ Created {title}: {output_path}")


def add_legend(page, title):
    """Add color legend to page."""
    page_rect = page.rect
    legend_x = page_rect.width - 200
    legend_y = 50

    # White background
    bg_rect = fitz.Rect(legend_x - 10, legend_y - 10, page_rect.width - 10, legend_y + 150)
    page.draw_rect(bg_rect, color=(1, 1, 1), fill=(1, 1, 1), width=1)
    page.draw_rect(bg_rect, color=(0, 0, 0), width=1)

    # Title
    page.insert_text((legend_x, legend_y + 5), f"{title} Labels", fontsize=10, fontname="helv")

    # Labels
    y_offset = 20
    for label, color in LABEL_COLORS.items():
        if label == "other":
            continue

        box_rect = fitz.Rect(legend_x, legend_y + y_offset, legend_x + 15, legend_y + y_offset + 10)
        fitz_color = rgb_to_fitz(color)
        page.draw_rect(box_rect, fill=fitz_color, fill_opacity=ALPHA, width=0.5, color=(0, 0, 0))

        page.insert_text(
            (legend_x + 20, legend_y + y_offset + 8), label, fontsize=8, fontname="helv"
        )

        y_offset += 15


def create_corrected_overlay_pdf(
    pdf_path: Path,
    body_html: list,
    footnote_html: list,
    output_path: Path,
    threshold: float = 0.75,
    algorithm: str = "baseline",
):
    """
    Create corrected PDF using line-level fuzzy matching or sequence alignment.

    Extracts lines from PDF, matches each to HTML, groups adjacent same-labeled lines,
    and draws merged bounding boxes.

    Args:
        pdf_path: Path to PDF file
        body_html: Body HTML ground truth
        footnote_html: Footnote HTML ground truth
        output_path: Output PDF path
        threshold: Similarity threshold
        algorithm: Algorithm to use ("baseline", "dp", "two_pass", "hmm")
    """
    from fuzzy_matcher import match_all_lines_with_locality
    from parse_extraction import ExtractedItem

    # Import alignment algorithms if needed
    if algorithm != "baseline":
        from sequence_alignment.dp_alignment import dp_two_sequence_alignment
        from sequence_alignment.hmm_alignment import hmm_viterbi_alignment
        from sequence_alignment.two_pass_alignment import two_pass_alignment

    # Extract lines from PDF
    print("Extracting line-level text from PDF...")
    lines_by_page = extract_line_level_text(pdf_path)

    total_lines = sum(len(lines) for lines in lines_by_page.values())
    print(f"Extracted {total_lines} lines across {len(lines_by_page)} pages")

    # Match each line to HTML using specified algorithm
    print(f"Matching lines to HTML ground truth using {algorithm} algorithm...")

    # First, we need to get Docling's original classifications for fallback
    # Load the extraction items to get original labels
    print("Loading Docling extraction for fallback labels...")
    from pathlib import Path

    from parse_extraction import load_extraction

    pdf_name = pdf_path.stem
    ext_file = Path(
        f"results/ocr_pipeline_evaluation/extractions/{pdf_name}_baseline_extraction.json"
    )
    docling_items = load_extraction(ext_file) if ext_file.exists() else []

    # Create a mapping from (page, text_snippet) to Docling label for fallback
    docling_label_map = {}
    for item in docling_items:
        # Use first 50 chars as key for matching
        key = (item.page_num, item.text[:50].strip())
        docling_label_map[key] = item.label

    # Convert all lines to ExtractedItem objects (in reading order)
    all_line_items = []
    line_to_page = {}  # Track which page each line belongs to

    for page_num in sorted(lines_by_page.keys()):
        for line in lines_by_page[page_num]:
            # Try to find Docling's original label for this line
            key = (page_num, line["text"][:50].strip())
            docling_label = docling_label_map.get(key, "TEXT")  # Default to TEXT

            item = ExtractedItem(
                text=line["text"],
                label=docling_label,
                page_num=page_num,
                bbox=line["bbox"],
                original_docling_label=docling_label,
            )
            line_idx = len(all_line_items)
            all_line_items.append(item)
            line_to_page[line_idx] = {"page_num": page_num, "bbox": line["bbox"]}

    # Match all lines using specified algorithm
    if algorithm == "baseline":
        all_matches = match_all_lines_with_locality(
            all_line_items, body_html, footnote_html, threshold
        )
    elif algorithm == "dp":
        all_matches = dp_two_sequence_alignment(all_line_items, body_html, footnote_html, threshold)
    elif algorithm == "two_pass":
        all_matches = two_pass_alignment(all_line_items, body_html, footnote_html, threshold)
    elif algorithm == "hmm":
        all_matches = hmm_viterbi_alignment(all_line_items, body_html, footnote_html, threshold)
    else:
        raise ValueError(
            f"Unknown algorithm: {algorithm}. Must be one of: baseline, dp, two_pass, hmm"
        )

    # Organize matches back by page
    matched_lines_by_page = {}
    for line_idx, match in enumerate(all_matches):
        page_info = line_to_page[line_idx]
        page_num = page_info["page_num"]

        if page_num not in matched_lines_by_page:
            matched_lines_by_page[page_num] = []

        # Use HTML-corrected label if available, otherwise fall back to Docling's original
        if match.corrected_label:
            # HTML match found - use corrected label (body-text or footnote-text)
            label = match.corrected_label
        else:
            # No HTML match - fall back to Docling's classification
            original_label = match.extraction_item.label
            label = DOCLING_TO_COLOR_LABEL.get(original_label, "other")

        matched_lines_by_page[page_num].append(
            {"text": match.extraction_item.text, "bbox": page_info["bbox"], "label": label}
        )

    # Group adjacent lines with same label
    print("Grouping adjacent lines...")
    grouped_regions_by_page = {}

    for page_num, lines in matched_lines_by_page.items():
        # First, sort lines by Y position (top to bottom)
        sorted_lines = sorted(lines, key=lambda l: l["bbox"][1])  # Sort by top Y

        regions = []
        current_group = []

        for line in sorted_lines:
            # All lines should have labels now (either HTML-corrected or Docling fallback)
            # Check if this line should join current group
            if current_group:
                last_line = current_group[-1]
                same_label = line["label"] == last_line["label"]
                # Check if vertically adjacent (within 5 pixels)
                gap = line["bbox"][1] - last_line["bbox"][3]
                adjacent = gap < 5

                if same_label and adjacent:
                    # Add to current group
                    current_group.append(line)
                else:
                    # Finalize current group
                    min_x = min(l["bbox"][0] for l in current_group)
                    min_y = min(l["bbox"][1] for l in current_group)
                    max_x = max(l["bbox"][2] for l in current_group)
                    max_y = max(l["bbox"][3] for l in current_group)

                    regions.append(
                        {"label": current_group[0]["label"], "bbox": (min_x, min_y, max_x, max_y)}
                    )

                    # Start new group
                    current_group = [line]
            else:
                # Start first group
                current_group = [line]

        # Don't forget last group
        if current_group:
            min_x = min(l["bbox"][0] for l in current_group)
            min_y = min(l["bbox"][1] for l in current_group)
            max_x = max(l["bbox"][2] for l in current_group)
            max_y = max(l["bbox"][3] for l in current_group)

            regions.append(
                {"label": current_group[0]["label"], "bbox": (min_x, min_y, max_x, max_y)}
            )

        grouped_regions_by_page[page_num] = regions

    # Draw overlays
    print("Drawing overlays...")
    doc = fitz.open(pdf_path)

    for page_num, regions in grouped_regions_by_page.items():
        page_idx = page_num - 1
        if page_idx >= len(doc):
            continue

        page = doc[page_idx]

        for region in regions:
            label = region["label"]
            bbox = region["bbox"]

            # Get color
            color = LABEL_COLORS.get(label, LABEL_COLORS["other"])
            fitz_color = rgb_to_fitz(color)

            # Draw rectangle
            rect = fitz.Rect(*bbox)
            page.draw_rect(rect, fill=fitz_color, fill_opacity=ALPHA)

    # Add legend
    add_legend(doc[0], "Corrected")

    # Save
    doc.save(output_path)
    doc.close()

    print(f"✓ Created Corrected: {output_path}")


def generate_overlay_pdfs(pdf_name: str, output_dir: Path, algorithm: str = "baseline"):
    """
    Generate uncorrected and corrected overlay PDFs.

    Args:
        pdf_name: PDF name without extension (e.g., "harvard_law_review_unwarranted_warrants")
        output_dir: Output directory for PDFs
        algorithm: Algorithm to use ("baseline", "dp", "two_pass", "hmm")
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find PDF
    pdf_path = None
    for pdf_dir in [Path("data/v3_data/raw_pdf"), Path("data/raw_pdf")]:
        candidate = pdf_dir / f"{pdf_name}.pdf"
        if candidate.exists():
            pdf_path = candidate
            break

    if not pdf_path:
        print(f"Error: PDF not found for {pdf_name}")
        return 1

    # Load extraction
    ext_file = Path(
        f"results/ocr_pipeline_evaluation/extractions/{pdf_name}_baseline_extraction.json"
    )
    if not ext_file.exists():
        print(f"Error: Extraction not found: {ext_file}")
        return 1

    items = load_extraction(ext_file)
    print(f"Loaded {len(items)} extraction items from {pdf_name}")

    # Load HTML ground truth
    body_html, footnote_html = load_html_ground_truth(pdf_name)
    print(f"Loaded HTML ground truth: {len(body_html)} body + {len(footnote_html)} footnotes")

    # Generate uncorrected PDF (uses Docling paragraph-level boxes)
    uncorrected_path = output_dir / f"{pdf_name}_{algorithm}_uncorrected.pdf"
    matches = match_all_items(items, body_html, footnote_html, threshold=0.75)
    label_map = {}
    for idx, match in enumerate(matches):
        if match.corrected_label:
            label_map[idx] = match.corrected_label
    create_overlay_pdf(pdf_path, items, None, uncorrected_path, "Uncorrected")

    # Generate corrected PDF (uses line-level matching and grouping)
    corrected_path = output_dir / f"{pdf_name}_{algorithm}_corrected.pdf"
    create_corrected_overlay_pdf(
        pdf_path, body_html, footnote_html, corrected_path, threshold=0.75, algorithm=algorithm
    )

    print(f"\n✅ Generated overlay PDFs using {algorithm} algorithm:")
    print(f"   Uncorrected: {uncorrected_path}")
    print(f"   Corrected: {corrected_path}")

    return 0


def main():
    """Generate overlay PDFs for harvard_law_review."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate overlay PDFs with classification corrections"
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        choices=["baseline", "dp", "two_pass", "hmm"],
        default="baseline",
        help="Alignment algorithm to use (default: baseline)",
    )
    parser.add_argument(
        "--pdf",
        type=str,
        default="harvard_law_review_unwarranted_warrants",
        help="PDF name without extension (default: harvard_law_review_unwarranted_warrants)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/sequence_alignment/overlay_pdfs"),
        help="Output directory (default: results/sequence_alignment/overlay_pdfs)",
    )

    args = parser.parse_args()

    result = generate_overlay_pdfs(args.pdf, args.output, args.algorithm)

    return result


if __name__ == "__main__":
    exit(main())

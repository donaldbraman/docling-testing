#!/usr/bin/env python3
"""
Generate CSV files showing PDF-to-HTML alignment for visual inspection (V2 - IMPROVED).

This version includes fixes to reduce false positives from short text matching:
1. Minimum text length filter (15 chars)
2. Section header detection and exclusion
3. Dynamic confidence thresholds based on text length
4. Semantic validation for footnote patterns

Creates one CSV per article with columns:
- page_no: PDF page number
- pdf_text: Text from PDF (Docling extraction)
- pdf_original_label: Docling's automatic label
- pdf_corrected_label: Label after fuzzy matching
- matched_html_body: The actual HTML body text that matched (if any)
- matched_html_footnote: The actual HTML footnote text that matched (if any)
- match_confidence: Fuzzy match score (0-100)
- match_status: "matched" or "unmatched"

Also includes:
- PDF lines that didn't match any HTML
- HTML body paragraphs never matched by PDF
- HTML footnotes never matched by PDF

Author: Claude Code
Date: 2025-01-19 (v2 with false positive fixes)
"""

import csv
import json
import re
from pathlib import Path

try:
    from rapidfuzz import fuzz, utils
except ImportError:
    print("ERROR: RapidFuzz not installed. Install with: uv pip install rapidfuzz")
    exit(1)


def is_section_header(text: str) -> bool:
    """
    Check if text is a section header that should not be matched to footnotes.

    Examples: "I.", "II.", "III.", "IV.", "A.", "B.", "C."
    """
    text = text.strip()

    # Roman numerals followed by period
    if re.match(r"^[IVX]+\.$", text):
        return True

    # Single uppercase letter followed by period
    if re.match(r"^[A-Z]\.$", text):
        return True

    # Common section header patterns (Roman numeral + text)
    if re.match(r"^[IVX]+\.\s+[A-Z]", text):
        return True

    return False


def looks_like_footnote(text: str) -> bool:
    """
    Check if text has footnote patterns (for semantic validation).

    This helps validate that a match makes sense before accepting it.
    """
    text_lower = text.lower()

    # Starts with footnote number pattern
    if re.match(r"^\d+\.\s+", text):
        return True

    # Contains citation keywords
    citation_keywords = [
        "see",
        "supra",
        "infra",
        "id.",
        "cf.",
        "e.g.",
        "i.e.",
        "ibid",
    ]
    if any(keyword in text_lower for keyword in citation_keywords):
        return True

    # Contains legal citation patterns
    if re.search(r"\d+\s+[A-Z][a-z]+\.?\s+L\.?\s+Rev\.?", text):  # Law review
        return True
    if re.search(r"\d+\s+U\.S\.", text):  # US Reports
        return True
    if re.search(r"F\.\d+d\s+\d+", text):  # Federal Reporter
        return True

    return False


def get_confidence_threshold(text_length: int, base_threshold: int = 70) -> int:
    """
    Get dynamic confidence threshold based on text length.

    Short text needs higher confidence to avoid false positives.
    Long text can use lower threshold as matches are more meaningful.
    """
    if text_length < 30:
        return 95  # Very high threshold for short text
    elif text_length < 100:
        return 85  # High threshold for medium text
    else:
        return base_threshold  # Original threshold for long text


def find_best_match(
    pdf_text: str, html_paragraphs: list[str], base_threshold: int = 70
) -> tuple[int, float, str]:
    """
    Find best matching HTML paragraph for PDF text with validation (V2 - IMPROVED).

    Improvements over v1:
    - Filters out very short text (< 15 chars) to avoid table cell false positives
    - Excludes section headers from matching to footnotes
    - Uses dynamic confidence thresholds based on text length
    - Validates matches semantically for medium-confidence cases

    Returns:
        (index, score, matched_text) or (-1, 0, "") if no match
    """
    # 1. Filter very short text (likely table cells, abbreviations, page numbers)
    pdf_text_stripped = pdf_text.strip()
    if len(pdf_text_stripped) < 15:
        return -1, 0, ""

    # 2. Don't match section headers to footnotes
    if is_section_header(pdf_text_stripped):
        return -1, 0, ""

    # 3. Get dynamic threshold based on text length
    threshold = get_confidence_threshold(len(pdf_text_stripped), base_threshold)

    # 4. Find best match using existing logic
    best_score = 0
    best_idx = -1
    best_text = ""

    for idx, html_text in enumerate(html_paragraphs):
        # Use default_process to normalize both texts before matching
        score = fuzz.partial_ratio(pdf_text, html_text, processor=utils.default_process)

        if score > best_score:
            best_score = score
            best_idx = idx
            best_text = html_text

    # 5. Check if score meets dynamic threshold
    if best_score < threshold:
        return -1, best_score, ""

    # 6. Additional validation for medium-confidence matches (85-94%)
    if 85 <= best_score < 95:
        # For medium confidence, validate it makes semantic sense
        # If matching to what looks like a footnote, check PDF text looks like one too
        if not looks_like_footnote(pdf_text):
            # Be more strict - only accept if very high confidence
            if best_score < 90:
                return -1, best_score, ""

    return best_idx, best_score, best_text


def load_docling_texts(docling_file: Path) -> list[dict]:
    """Load Docling extraction texts (excluding furniture)."""
    with open(docling_file) as f:
        data = json.load(f)

    texts = []
    for item in data.get("texts", []):
        if item.get("content_layer") == "furniture":
            continue

        prov = item.get("prov", [])
        page_no = prov[0].get("page_no", 0) if prov else 0

        texts.append(
            {
                "text": item.get("text", ""),
                "original_label": item.get("label", "unknown"),
                "page_no": page_no,
            }
        )

    return texts


def load_html_paragraphs(html_file: Path) -> tuple[list[str], list[str]]:
    """Load HTML ground truth paragraphs."""
    with open(html_file) as f:
        data = json.load(f)

    body_paras = []
    footnote_paras = []

    for para in data.get("paragraphs", []):
        if para["label"] == "body-text":
            body_paras.append(para["text"])
        elif para["label"] == "footnote-text":
            footnote_paras.append(para["text"])

    return body_paras, footnote_paras


def generate_alignment_csv(basename: str, output_dir: Path):
    """
    Generate alignment CSV for a single article.

    Args:
        basename: Article basename
        output_dir: Directory to save CSV
    """
    # Load data
    docling_file = Path(f"data/v3_data/docling_extraction/{basename}.json")
    html_file = Path(f"data/v3_data/processed_html/{basename}.json")

    if not docling_file.exists() or not html_file.exists():
        print(f"⚠️  Skipping {basename}: missing files")
        return None

    pdf_texts = load_docling_texts(docling_file)
    body_paras, footnote_paras = load_html_paragraphs(html_file)

    # Track which HTML paragraphs were matched
    matched_body_indices = set()
    matched_footnote_indices = set()

    # Track filtering stats
    filtered_short = 0
    filtered_section_header = 0

    # Generate CSV rows for PDF lines
    csv_rows = []

    for pdf_item in pdf_texts:
        pdf_text = pdf_item["text"]
        original_label = pdf_item["original_label"]
        page_no = pdf_item["page_no"]

        # Check if this item will be filtered
        if len(pdf_text.strip()) < 15:
            filtered_short += 1
        if is_section_header(pdf_text.strip()):
            filtered_section_header += 1

        # Try matching to body
        body_idx, body_score, body_matched = find_best_match(pdf_text, body_paras)

        # Try matching to footnotes
        fn_idx, fn_score, fn_matched = find_best_match(pdf_text, footnote_paras)

        # Determine best match
        if body_idx >= 0 and fn_idx >= 0:
            # Both matched - pick higher score
            if body_score > fn_score:
                corrected_label = "body_text"
                match_confidence = body_score
                matched_body_indices.add(body_idx)
                csv_rows.append(
                    {
                        "page_no": page_no,
                        "pdf_text": pdf_text,
                        "pdf_original_label": original_label,
                        "pdf_corrected_label": corrected_label,
                        "matched_html_body": body_matched,
                        "matched_html_footnote": "",
                        "match_confidence": match_confidence,
                        "match_status": "matched",
                    }
                )
            else:
                corrected_label = "footnote"
                match_confidence = fn_score
                matched_footnote_indices.add(fn_idx)
                csv_rows.append(
                    {
                        "page_no": page_no,
                        "pdf_text": pdf_text,
                        "pdf_original_label": original_label,
                        "pdf_corrected_label": corrected_label,
                        "matched_html_body": "",
                        "matched_html_footnote": fn_matched,
                        "match_confidence": match_confidence,
                        "match_status": "matched",
                    }
                )
        elif body_idx >= 0:
            # Only body matched
            corrected_label = "body_text"
            match_confidence = body_score
            matched_body_indices.add(body_idx)
            csv_rows.append(
                {
                    "page_no": page_no,
                    "pdf_text": pdf_text,
                    "pdf_original_label": original_label,
                    "pdf_corrected_label": corrected_label,
                    "matched_html_body": body_matched,
                    "matched_html_footnote": "",
                    "match_confidence": match_confidence,
                    "match_status": "matched",
                }
            )
        elif fn_idx >= 0:
            # Only footnote matched
            corrected_label = "footnote"
            match_confidence = fn_score
            matched_footnote_indices.add(fn_idx)
            csv_rows.append(
                {
                    "page_no": page_no,
                    "pdf_text": pdf_text,
                    "pdf_original_label": original_label,
                    "pdf_corrected_label": corrected_label,
                    "matched_html_body": "",
                    "matched_html_footnote": fn_matched,
                    "match_confidence": match_confidence,
                    "match_status": "matched",
                }
            )
        else:
            # No match - keep original label
            corrected_label = original_label
            match_confidence = max(body_score, fn_score)
            csv_rows.append(
                {
                    "page_no": page_no,
                    "pdf_text": pdf_text,
                    "pdf_original_label": original_label,
                    "pdf_corrected_label": corrected_label,
                    "matched_html_body": "",
                    "matched_html_footnote": "",
                    "match_confidence": match_confidence,
                    "match_status": "unmatched",
                }
            )

    # Add unmatched HTML body paragraphs
    for idx, body_text in enumerate(body_paras):
        if idx not in matched_body_indices:
            csv_rows.append(
                {
                    "page_no": "",
                    "pdf_text": "",
                    "pdf_original_label": "",
                    "pdf_corrected_label": "",
                    "matched_html_body": body_text,
                    "matched_html_footnote": "",
                    "match_confidence": 0,
                    "match_status": "html_body_unmatched",
                }
            )

    # Add unmatched HTML footnotes
    for idx, fn_text in enumerate(footnote_paras):
        if idx not in matched_footnote_indices:
            csv_rows.append(
                {
                    "page_no": "",
                    "pdf_text": "",
                    "pdf_original_label": "",
                    "pdf_corrected_label": "",
                    "matched_html_body": "",
                    "matched_html_footnote": fn_text,
                    "match_confidence": 0,
                    "match_status": "html_footnote_unmatched",
                }
            )

    # Write CSV
    output_file = output_dir / f"{basename}.csv"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "page_no",
            "pdf_text",
            "pdf_original_label",
            "pdf_corrected_label",
            "matched_html_body",
            "matched_html_footnote",
            "match_confidence",
            "match_status",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    # Calculate statistics
    matched_count = sum(1 for row in csv_rows if row["match_status"] == "matched")
    unmatched_pdf_count = sum(1 for row in csv_rows if row["match_status"] == "unmatched")
    unmatched_html_body_count = sum(
        1 for row in csv_rows if row["match_status"] == "html_body_unmatched"
    )
    unmatched_html_fn_count = sum(
        1 for row in csv_rows if row["match_status"] == "html_footnote_unmatched"
    )

    return {
        "total_rows": len(csv_rows),
        "matched_pdf": matched_count,
        "unmatched_pdf": unmatched_pdf_count,
        "unmatched_html_body": unmatched_html_body_count,
        "unmatched_html_footnote": unmatched_html_fn_count,
        "filtered_short": filtered_short,
        "filtered_section_header": filtered_section_header,
    }


def main():
    """Generate alignment CSVs for all articles."""
    output_dir = Path("data/v3_data/v3_csv_v2")
    processed_html_dir = Path("data/v3_data/processed_html")

    html_files = sorted(processed_html_dir.glob("*.json"))

    print(f"{'=' * 80}")
    print(f"Generating alignment CSVs (V2 - IMPROVED) for {len(html_files)} articles")
    print(f"{'=' * 80}")
    print()
    print("Improvements:")
    print("  - Minimum text length filter (15 chars)")
    print("  - Section header detection")
    print("  - Dynamic confidence thresholds")
    print("  - Semantic validation")
    print()

    total_stats = {
        "total_rows": 0,
        "matched_pdf": 0,
        "unmatched_pdf": 0,
        "unmatched_html_body": 0,
        "unmatched_html_footnote": 0,
        "filtered_short": 0,
        "filtered_section_header": 0,
    }

    for idx, html_file in enumerate(html_files, 1):
        basename = html_file.stem
        print(f"[{idx}/{len(html_files)}] {basename}...", end=" ", flush=True)

        try:
            stats = generate_alignment_csv(basename, output_dir)
            if stats:
                print(
                    f"✅ ({stats['matched_pdf']} matched, {stats['unmatched_pdf']} unmatched PDF, "
                    f"{stats['filtered_short']} filtered short, {stats['filtered_section_header']} filtered headers)"
                )

                for key in total_stats:
                    total_stats[key] += stats[key]
            else:
                print("⚠️  Skipped")
        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\n{'=' * 80}")
    print("Summary Statistics")
    print(f"{'=' * 80}")
    print(f"Total CSV rows: {total_stats['total_rows']:,}")
    print(f"  Matched PDF lines: {total_stats['matched_pdf']:,}")
    print(f"  Unmatched PDF lines: {total_stats['unmatched_pdf']:,}")
    print(f"  Unmatched HTML body paragraphs: {total_stats['unmatched_html_body']:,}")
    print(f"  Unmatched HTML footnotes: {total_stats['unmatched_html_footnote']:,}")
    print()
    print("Filtering Statistics:")
    print(f"  Filtered short text (< 15 chars): {total_stats['filtered_short']:,}")
    print(f"  Filtered section headers: {total_stats['filtered_section_header']:,}")
    print(f"\n✅ CSV files saved to: {output_dir}/")


if __name__ == "__main__":
    main()

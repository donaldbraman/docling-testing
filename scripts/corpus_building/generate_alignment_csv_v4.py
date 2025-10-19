#!/usr/bin/env python3
"""
Generate CSV files showing PDF-to-HTML alignment for visual inspection (V4 - DIRECTIONAL MATCHING).

This version tests TWO hypotheses:
1. Better normalization: Remove double spaces that default_process creates
2. Length directionality: Reject if HTML is shorter than PDF (can't contain it)

The logic: We're trying to find PDF text INSIDE HTML paragraphs.
If the HTML is shorter than the PDF, it's impossible for it to contain the PDF text.

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

Usage:
    python generate_alignment_csv_v4.py [--margin MARGIN]

Arguments:
    --margin: Minimum score margin between best and 2nd best match to accept (default: 5)
              If margin < this value, match is considered ambiguous and rejected

Author: Claude Code
Date: 2025-01-19 (v4 with better normalization and directional matching)
"""

import argparse
import csv
import json
import re
from pathlib import Path

try:
    from rapidfuzz import fuzz, utils
except ImportError:
    print("ERROR: RapidFuzz not installed. Install with: uv pip install rapidfuzz")
    exit(1)


def normalize_text(text: str) -> str:
    """
    Normalize text for matching.

    Improvements over default_process:
    - Removes double/multiple spaces that punctuation removal creates
    """
    normalized = utils.default_process(text)
    if not normalized:
        return ""
    # Remove multiple spaces
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def find_best_match_directional(
    pdf_text: str,
    html_paragraphs: list[str],
    base_threshold: int = 70,
    ambiguity_margin: int = 5,
) -> tuple[int, float, str, int]:
    """
    Find best matching HTML paragraph for PDF text with directional filtering (V4).

    Two filtering rules:
    1. Length directionality: HTML must be >= PDF length (after normalization)
       Rationale: Can't find long PDF text inside short HTML paragraph
    2. Match ambiguity: Reject if multiple HTML paragraphs score similarly high
       Rationale: Ambiguous matches are likely false positives

    Args:
        pdf_text: Text from PDF
        html_paragraphs: List of HTML paragraphs to match against
        base_threshold: Minimum score to consider a match (default 70)
        ambiguity_margin: Margin between best and 2nd best to accept match (default 5)

    Returns:
        (index, score, matched_text, num_competitors) or (-1, best_score, "", num_competitors)
        where num_competitors is the number of paragraphs scoring >= base_threshold
    """
    # Normalize PDF text once
    pdf_norm = normalize_text(pdf_text)
    pdf_len = len(pdf_norm)

    # Calculate scores only for HTML paragraphs that could contain the PDF text
    scores = []
    for idx, html_text in enumerate(html_paragraphs):
        html_norm = normalize_text(html_text)

        # DIRECTIONAL CHECK: HTML must be at least as long as PDF
        # (Can't find long PDF text inside short HTML paragraph)
        if len(html_norm) < pdf_len:
            continue  # Skip this HTML paragraph

        # Now do fuzzy matching (already normalized, so no processor needed)
        score = fuzz.partial_ratio(pdf_norm, html_norm)
        scores.append((idx, score, html_text))

    # Find all "good enough" matches (>= threshold)
    good_matches = [(idx, s, text) for idx, s, text in scores if s >= base_threshold]

    num_competitors = len(good_matches)

    # No match at all
    if num_competitors == 0:
        best_score = max((s for _, s, _ in scores), default=0)
        return -1, best_score, "", 0

    # UNIQUE match - only one paragraph scored high enough
    if num_competitors == 1:
        idx, score, text = good_matches[0]
        return idx, score, text, 1

    # Multiple matches - check if there's a CLEAR winner
    sorted_matches = sorted(good_matches, key=lambda x: x[1], reverse=True)
    best_idx, best_score, best_text = sorted_matches[0]
    second_best_score = sorted_matches[1][1]

    margin = best_score - second_best_score

    # AMBIGUOUS - top scores too close
    if margin < ambiguity_margin:
        return -1, best_score, "", num_competitors

    # CLEAR winner - margin is large enough
    return best_idx, best_score, best_text, num_competitors


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


def generate_alignment_csv(basename: str, output_dir: Path, ambiguity_margin: int = 5):
    """
    Generate alignment CSV for a single article.

    Args:
        basename: Article basename
        output_dir: Directory to save CSV
        ambiguity_margin: Margin between best and 2nd best score to accept match
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
    filtered_ambiguous = 0
    filtered_directional = 0

    # Generate CSV rows for PDF lines
    csv_rows = []

    for pdf_item in pdf_texts:
        pdf_text = pdf_item["text"]
        original_label = pdf_item["original_label"]
        page_no = pdf_item["page_no"]

        # Try matching to body
        body_idx, body_score, body_matched, body_competitors = find_best_match_directional(
            pdf_text, body_paras, ambiguity_margin=ambiguity_margin
        )

        # Try matching to footnotes
        fn_idx, fn_score, fn_matched, fn_competitors = find_best_match_directional(
            pdf_text, footnote_paras, ambiguity_margin=ambiguity_margin
        )

        # Track filtering reasons
        if body_idx == -1 and body_competitors > 1:
            filtered_ambiguous += 1
        if fn_idx == -1 and fn_competitors > 1:
            filtered_ambiguous += 1

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
        "filtered_ambiguous": filtered_ambiguous,
        "filtered_directional": filtered_directional,
    }


def main():
    """Generate alignment CSVs for all articles."""
    parser = argparse.ArgumentParser(
        description="Generate alignment CSVs with directional matching (V4)"
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=5,
        help="Minimum score margin between best and 2nd best match to accept (default: 5)",
    )
    args = parser.parse_args()

    output_dir = Path("data/v3_data/v3_csv_v4")
    processed_html_dir = Path("data/v3_data/processed_html")

    html_files = sorted(processed_html_dir.glob("*.json"))

    print(f"{'=' * 80}")
    print(f"Generating alignment CSVs (V4 - DIRECTIONAL MATCHING) for {len(html_files)} articles")
    print(f"{'=' * 80}")
    print()
    print("Testing TWO hypotheses:")
    print("  1. Better normalization: Remove double spaces from default_process")
    print("  2. Length directionality: Reject if len(html_norm) < len(pdf_norm)")
    print("     Rationale: Can't find long PDF text inside short HTML paragraph")
    print()
    print("Also includes:")
    print("  3. Match ambiguity filtering: Reject if margin < threshold")
    print()
    print("Parameters:")
    print(f"  - Ambiguity margin: {args.margin}")
    print(f"    (Reject match if best_score - second_best_score < {args.margin})")
    print()

    total_stats = {
        "total_rows": 0,
        "matched_pdf": 0,
        "unmatched_pdf": 0,
        "unmatched_html_body": 0,
        "unmatched_html_footnote": 0,
        "filtered_ambiguous": 0,
        "filtered_directional": 0,
    }

    for idx, html_file in enumerate(html_files, 1):
        basename = html_file.stem
        print(f"[{idx}/{len(html_files)}] {basename}...", end=" ", flush=True)

        try:
            stats = generate_alignment_csv(basename, output_dir, ambiguity_margin=args.margin)
            if stats:
                print(
                    f"✅ ({stats['matched_pdf']} matched, {stats['unmatched_pdf']} unmatched, "
                    f"{stats['filtered_ambiguous']} filtered ambiguous)"
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
    print(f"  Filtered ambiguous matches: {total_stats['filtered_ambiguous']:,}")
    print(f"  Filtered directional mismatches: {total_stats['filtered_directional']:,}")
    print(f"\n✅ CSV files saved to: {output_dir}/")


if __name__ == "__main__":
    main()

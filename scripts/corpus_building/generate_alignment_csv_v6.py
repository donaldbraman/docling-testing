#!/usr/bin/env python3
"""
Generate CSV files showing PDF-to-HTML alignment for visual inspection (V6 - FINAL).

This version combines V5's soft locality bias with minimum length filtering:

1. MINIMUM LENGTH FILTER (NEW):
   - Reject matches if normalized PDF text < 5 characters
   - Prevents short string substring bug (e.g., "IV." matching inside "div")
   - Based on analysis: 9 false positives eliminated, 0 legitimate matches lost

2. SOFT LOCALITY BIAS (from V5):
   - Windowed search around last match position (1000/2000 chars)
   - Distance as tiebreaker when scores are similar
   - Disambiguates similar patterns by document position

Creates one CSV per article with columns:
- page_no: PDF page number
- pdf_text: Text from PDF (Docling extraction)
- pdf_original_label: Docling's automatic label
- pdf_corrected_label: Label after fuzzy matching
- matched_html_body: The actual HTML body text that matched (if any)
- matched_html_footnote: The actual HTML footnote text that matched (if any)
- match_confidence: Fuzzy match score (0-100)
- match_status: "matched" or "unmatched"

Author: Claude Code
Date: 2025-01-19 (v6 - final version with minimum length filter)
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


def find_best_match_sequential(
    pdf_text: str,
    html_paragraphs: list[str],
    last_matched_index: int = -1,
    base_threshold: int = 70,
    distance_tiebreaker_margin: int = 5,
    search_window_chars: int = 2000,
    initial_search_chars: int = 1000,
    min_length: int = 5,
) -> tuple[int, float, str]:
    """
    Find best matching HTML paragraph with SOFT locality bias + windowed search (V6).

    V6 improvements:
    1. Minimum length filter: Reject if normalized PDF text < 5 chars (prevents short string bug)
    2. Locality assumption: Documents roughly follow sequential order
    3. Windowed search: First match searches first N chars, subsequent searches ±M chars
    4. Distance tiebreaker: When scores are similar, prefer closer match

    This handles cases like similar footnote structures ("see, e.g., Thomas supra note __")
    where fuzzy scores tie, but document position disambiguates.

    Args:
        pdf_text: Text from PDF
        html_paragraphs: List of HTML paragraphs to match against
        last_matched_index: Index of last matched HTML paragraph (-1 if none)
        base_threshold: Minimum score to consider a match (default 70)
        distance_tiebreaker_margin: Use distance as tiebreaker if scores within this margin (default 5)
        search_window_chars: Search within this many characters before/after last match (default 2000)
        initial_search_chars: For first match, search only first N chars (default 1000)
        min_length: Minimum normalized length to attempt matching (default 5)

    Returns:
        (index, score, matched_text) or (-1, best_score, "") if no match
    """
    # Normalize PDF text once
    pdf_norm = normalize_text(pdf_text)

    # MINIMUM LENGTH FILTER: Reject short strings to prevent substring false positives
    # Analysis showed 9 false positives (I., II., III., IV.) and 0 legitimate short matches
    if len(pdf_norm) < min_length:
        return -1, 0, ""  # Too short - unreliable for fuzzy matching

    # Determine search window
    if last_matched_index >= 0:
        # Subsequent matches: window around last match
        chars_before_match = sum(len(html_paragraphs[i]) for i in range(last_matched_index))
        window_start_chars = max(0, chars_before_match - search_window_chars)
        window_end_chars = (
            chars_before_match + len(html_paragraphs[last_matched_index]) + search_window_chars
        )
    else:
        # First match: search first initial_search_chars
        window_start_chars = 0
        window_end_chars = initial_search_chars

    # Convert character positions to paragraph indices
    cumulative_chars = 0
    start_idx = 0
    end_idx = len(html_paragraphs)

    for idx, html_text in enumerate(html_paragraphs):
        if cumulative_chars >= window_start_chars and start_idx == 0:
            start_idx = idx
        cumulative_chars += len(html_text)
        if cumulative_chars >= window_end_chars:
            end_idx = idx + 1
            break

    # Search within window
    candidates = []

    for idx in range(start_idx, end_idx):
        html_text = html_paragraphs[idx]
        html_norm = normalize_text(html_text)

        # Fuzzy match (already normalized, so no processor needed)
        score = fuzz.partial_ratio(pdf_norm, html_norm)

        if score >= base_threshold:
            # Calculate distance from last match
            distance = abs(idx - last_matched_index) if last_matched_index >= 0 else 0

            candidates.append((idx, score, html_text, distance))

    # No candidates above threshold
    if not candidates:
        return -1, 0, ""

    # Find best score
    best_score = max(c[1] for c in candidates)

    # Get all candidates with scores within tiebreaker margin of best
    top_candidates = [c for c in candidates if c[1] >= best_score - distance_tiebreaker_margin]

    # If multiple candidates with similar scores, use distance as tiebreaker
    if len(top_candidates) > 1:
        # Pick the one with smallest distance from last match
        best_candidate = min(top_candidates, key=lambda c: c[3])  # c[3] is distance
    else:
        best_candidate = top_candidates[0]

    idx, score, text, distance = best_candidate
    return idx, score, text


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


def generate_alignment_csv(
    basename: str,
    output_dir: Path,
    base_threshold: int = 70,
    initial_window_chars: int = 1000,
    search_window_chars: int = 2000,
):
    """
    Generate alignment CSV for a single article.

    Args:
        basename: Article basename
        output_dir: Directory to save CSV
        base_threshold: Minimum score to consider a match
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

    # Track SEQUENTIAL state - last matched index
    last_body_match_idx = -1  # Start at -1 (before first paragraph)
    last_footnote_match_idx = -1

    # Track filtering stats
    filtered_sequential = 0  # Count how many failed due to no forward match
    filtered_short = 0  # Count how many rejected due to min length filter

    # Generate CSV rows for PDF lines
    csv_rows = []

    for pdf_item in pdf_texts:
        pdf_text = pdf_item["text"]
        original_label = pdf_item["original_label"]
        page_no = pdf_item["page_no"]

        # Check if text is too short (for tracking)
        pdf_norm = normalize_text(pdf_text)
        is_too_short = len(pdf_norm) < 5

        # Try matching to body (search forward from last body match)
        body_idx, body_score, body_matched = find_best_match_sequential(
            pdf_text,
            body_paras,
            last_matched_index=last_body_match_idx,
            base_threshold=base_threshold,
            search_window_chars=search_window_chars,
            initial_search_chars=initial_window_chars,
        )

        # Try matching to footnotes (search forward from last footnote match)
        fn_idx, fn_score, fn_matched = find_best_match_sequential(
            pdf_text,
            footnote_paras,
            last_matched_index=last_footnote_match_idx,
            base_threshold=base_threshold,
            search_window_chars=search_window_chars,
            initial_search_chars=initial_window_chars,
        )

        # Determine best match
        if body_idx >= 0 and fn_idx >= 0:
            # Both matched - pick higher score
            if body_score > fn_score:
                corrected_label = "body_text"
                match_confidence = body_score
                matched_body_indices.add(body_idx)
                last_body_match_idx = body_idx  # Update sequential state
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
                last_footnote_match_idx = fn_idx  # Update sequential state
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
            last_body_match_idx = body_idx  # Update sequential state
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
            last_footnote_match_idx = fn_idx  # Update sequential state
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

            # Track filtering reason
            if is_too_short:
                filtered_short += 1
            else:
                filtered_sequential += 1  # No forward match found

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
        "filtered_sequential": filtered_sequential,
        "filtered_short": filtered_short,
    }


def main():
    """Generate alignment CSVs for test articles."""
    parser = argparse.ArgumentParser(
        description="Generate alignment CSVs with minimum length filter + locality bias (V6)"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=70,
        help="Minimum match score threshold (default: 70)",
    )
    parser.add_argument(
        "--initial-window",
        type=int,
        default=1000,
        help="For first match, search first N characters (default: 1000)",
    )
    parser.add_argument(
        "--search-window",
        type=int,
        default=2000,
        help="For subsequent matches, search ±N characters around last match (default: 2000)",
    )
    parser.add_argument(
        "--output-suffix",
        type=str,
        default="",
        help="Suffix for output directory (e.g., '_1000_2000')",
    )
    parser.add_argument(
        "--articles",
        nargs="+",
        help="Specific article basenames to process (default: test on high-error articles)",
    )
    args = parser.parse_args()

    output_suffix = (
        args.output_suffix if args.output_suffix else f"_{args.initial_window}_{args.search_window}"
    )
    output_dir = Path(f"data/v3_data/v3_csv_v6{output_suffix}")

    # Default: test on high-error articles first
    if args.articles:
        test_articles = args.articles
    else:
        test_articles = [
            "california_law_review_amazon-trademark",  # 56.5% FP rate
            "bu_law_review_online_building_new_constitutional_jerusalem",  # Heavy V4 filtering
            "california_law_review_affirmative-asylum",  # 366 corrections
        ]

    print(f"{'=' * 80}")
    print(f"Generating alignment CSVs (V6 - FINAL) for {len(test_articles)} articles")
    print(f"{'=' * 80}")
    print()
    print("V6 IMPROVEMENTS:")
    print("  1. MINIMUM LENGTH FILTER (NEW):")
    print("     - Skip matching if normalized text < 5 characters")
    print("     - Prevents short string substring bug (e.g., 'IV.' inside 'div')")
    print()
    print("  2. SOFT LOCALITY BIAS + WINDOWED SEARCH:")
    print("     - Documents roughly follow sequential order")
    print(f"     - First match: Search first {args.initial_window} chars")
    print(f"     - Subsequent matches: Search ±{args.search_window} char window around last match")
    print("     - When fuzzy scores are similar (within margin), prefer closer match")
    print("     - Disambiguates similar patterns (e.g., 'see, e.g., Thomas supra note __')")
    print()
    print("Parameters:")
    print(f"  - Base threshold: {args.threshold}")
    print(f"  - Initial search: first {args.initial_window} characters")
    print(f"  - Subsequent search window: ±{args.search_window} characters")
    print(f"  - Output directory: {output_dir}")
    print()
    print("Test articles (high-error cases):")
    for article in test_articles:
        print(f"  - {article}")
    print()

    total_stats = {
        "total_rows": 0,
        "matched_pdf": 0,
        "unmatched_pdf": 0,
        "unmatched_html_body": 0,
        "unmatched_html_footnote": 0,
        "filtered_sequential": 0,
        "filtered_short": 0,
    }

    for idx, basename in enumerate(test_articles, 1):
        print(f"[{idx}/{len(test_articles)}] {basename}...", end=" ", flush=True)

        try:
            stats = generate_alignment_csv(
                basename,
                output_dir,
                base_threshold=args.threshold,
                initial_window_chars=args.initial_window,
                search_window_chars=args.search_window,
            )
            if stats:
                print(
                    f"✅ ({stats['matched_pdf']} matched, {stats['unmatched_pdf']} unmatched, "
                    f"{stats['filtered_short']} too short, {stats['filtered_sequential']} no match in window)"
                )

                for key in total_stats:
                    total_stats[key] += stats[key]
            else:
                print("⚠️  Skipped")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()

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
    print(f"  Filtered (too short, < 5 chars): {total_stats['filtered_short']:,}")
    print(f"  Filtered (no match in search window): {total_stats['filtered_sequential']:,}")
    print(f"\n✅ CSV files saved to: {output_dir}/")


if __name__ == "__main__":
    main()

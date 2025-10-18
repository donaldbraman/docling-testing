#!/usr/bin/env python3
"""
Generate CSV files showing PDF-to-HTML alignment for visual inspection (OPTIMIZED).

This version uses RapidFuzz's process.extractOne for ~1.87x speedup vs manual iteration.

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
Date: 2025-01-18 (optimized version)
"""

import csv
import json
from pathlib import Path

try:
    from rapidfuzz import fuzz, process, utils
except ImportError:
    print("ERROR: RapidFuzz not installed. Install with: uv pip install rapidfuzz")
    exit(1)


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


def find_best_match(
    pdf_text: str, html_paragraphs: list[str], threshold: int = 70
) -> tuple[int, float, str]:
    """
    Find best matching HTML paragraph for PDF text using process.extractOne (OPTIMIZED).

    Uses RapidFuzz's process.extractOne for ~1.87x speedup vs manual iteration.
    Normalizes both texts (lowercase, strip punctuation) before matching.

    Note: Uses exhaustive search for comprehensive matching. This is intentional
    for CSV generation (diagnostic/exploratory tool) vs. relabeling (sequential).

    Returns:
        (index, score, matched_text) or (-1, 0, "") if no match
    """
    # Try to find match above threshold
    result = process.extractOne(
        pdf_text,
        html_paragraphs,
        scorer=fuzz.partial_ratio,
        processor=utils.default_process,
        score_cutoff=threshold,
    )

    if result:
        best_text, best_score, best_idx = result
        return best_idx, best_score, best_text
    else:
        # If no match above threshold, find best score anyway (for reporting)
        result = process.extractOne(
            pdf_text,
            html_paragraphs,
            scorer=fuzz.partial_ratio,
            processor=utils.default_process,
            score_cutoff=0,
        )
        if result:
            _, best_score, _ = result
            return -1, best_score, ""
        else:
            return -1, 0, ""


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
        return

    pdf_texts = load_docling_texts(docling_file)
    body_paras, footnote_paras = load_html_paragraphs(html_file)

    # Track which HTML paragraphs were matched
    matched_body_indices = set()
    matched_footnote_indices = set()

    # Generate CSV rows for PDF lines
    csv_rows = []

    for pdf_item in pdf_texts:
        pdf_text = pdf_item["text"]
        original_label = pdf_item["original_label"]
        page_no = pdf_item["page_no"]

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

    # Print summary
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
    }


def main():
    """Generate alignment CSVs for all articles."""
    output_dir = Path("data/v3_data/v3_csv")
    processed_html_dir = Path("data/v3_data/processed_html")

    html_files = sorted(processed_html_dir.glob("*.json"))

    print(f"{'=' * 80}")
    print(f"Generating alignment CSVs for {len(html_files)} articles")
    print(f"{'=' * 80}\n")

    total_stats = {
        "total_rows": 0,
        "matched_pdf": 0,
        "unmatched_pdf": 0,
        "unmatched_html_body": 0,
        "unmatched_html_footnote": 0,
    }

    for idx, html_file in enumerate(html_files, 1):
        basename = html_file.stem
        print(f"[{idx}/{len(html_files)}] {basename}...", end=" ", flush=True)

        try:
            stats = generate_alignment_csv(basename, output_dir)
            print(
                f"✅ ({stats['matched_pdf']} matched, {stats['unmatched_pdf']} unmatched PDF, "
                f"{stats['unmatched_html_body']} unmatched HTML body, "
                f"{stats['unmatched_html_footnote']} unmatched HTML fn)"
            )

            for key in total_stats:
                total_stats[key] += stats[key]
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
    print(f"\n✅ CSV files saved to: {output_dir}/")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Calculate content coverage for Docling-only predictions (no fuzzy matching correction).

This script calculates how well Docling's raw labels match the HTML ground truth
by concatenating all text by label and using fuzzy string matching to measure coverage.
"""

import json
import re
from pathlib import Path

from rapidfuzz import fuzz


def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def preprocess_docling_label(docling_label: str) -> str:
    """
    Map Docling labels to target labels using preprocessing strategy.

    Rules:
    - PAGE_HEADER, PAGE_FOOTER → "other" (skip matching)
    - SECTION_HEADER, LIST_ITEM → "body-text" (trust Docling)
    - TEXT → "body-text" (default assumption)
    - FOOTNOTE → "footnote-text"
    """
    if docling_label in ["page_header", "page_footer"]:
        return "other"
    elif docling_label in ["section_header", "list_item"]:
        return "body-text"
    elif docling_label == "footnote":
        return "footnote-text"
    elif docling_label == "text":
        return "body-text"  # Default: assume TEXT is body
    else:
        return "other"  # Unknown labels


def extract_label_from_repr(text_repr: str) -> str:
    """Extract the Docling label from the repr string."""
    # Find label=<DocItemLabel.XXXX: 'xxxx'>
    match = re.search(r"label=<DocItemLabel\.\w+: '([^']+)'>", text_repr)
    if match:
        return match.group(1)
    return "unknown"


def extract_text_from_repr(text_repr: str) -> str:
    """Extract the text content from the repr string."""
    # Find text='...'
    match = re.search(r"text='([^']*(?:''[^']*)*)'", text_repr)
    if match:
        # Handle escaped quotes
        return match.group(1).replace("\\'", "'")
    return ""


def calculate_content_coverage(
    pdf_texts: list[tuple[str, str]],  # List of (label, text)
    html_body: list[str],
    html_footnotes: list[str],
) -> dict[str, float]:
    """
    Calculate content coverage by concatenating all text by label and fuzzy matching.

    Args:
        pdf_texts: List of (label, text) tuples from PDF extraction
        html_body: List of body text paragraphs from HTML
        html_footnotes: List of footnote text paragraphs from HTML

    Returns:
        Dictionary with coverage metrics
    """
    # Separate PDF text by label
    pdf_body_texts = [text for label, text in pdf_texts if label == "body-text"]
    pdf_footnote_texts = [text for label, text in pdf_texts if label == "footnote-text"]
    pdf_other_texts = [text for label, text in pdf_texts if label == "other"]

    # Concatenate all text by label
    full_pdf_body = " ".join(pdf_body_texts)
    full_pdf_footnotes = " ".join(pdf_footnote_texts)
    full_html_body = " ".join(html_body)
    full_html_footnotes = " ".join(html_footnotes)

    # Normalize for comparison
    norm_pdf_body = normalize_text(full_pdf_body)
    norm_pdf_footnotes = normalize_text(full_pdf_footnotes)
    norm_html_body = normalize_text(full_html_body)
    norm_html_footnotes = normalize_text(full_html_footnotes)

    # Calculate coverage using fuzzy ratio
    body_coverage = fuzz.ratio(norm_pdf_body, norm_html_body) / 100.0
    footnote_coverage = fuzz.ratio(norm_pdf_footnotes, norm_html_footnotes) / 100.0

    # Overall coverage (weighted by character count)
    html_total_chars = len(norm_html_body) + len(norm_html_footnotes)
    if html_total_chars > 0:
        body_weight = len(norm_html_body) / html_total_chars
        footnote_weight = len(norm_html_footnotes) / html_total_chars
        overall_coverage = (body_coverage * body_weight) + (footnote_coverage * footnote_weight)
    else:
        overall_coverage = 0.0

    return {
        "body_coverage": body_coverage,
        "footnote_coverage": footnote_coverage,
        "overall_coverage": overall_coverage,
        "pdf_body_chars": len(norm_pdf_body),
        "pdf_footnote_chars": len(norm_pdf_footnotes),
        "pdf_other_chars": len(" ".join(pdf_other_texts)),
        "html_body_chars": len(norm_html_body),
        "html_footnote_chars": len(norm_html_footnotes),
        "num_body_lines": len(pdf_body_texts),
        "num_footnote_lines": len(pdf_footnote_texts),
        "num_other_lines": len(pdf_other_texts),
    }


def process_pdf(extraction_path: Path, ground_truth_path: Path) -> dict:
    """Process a single PDF and calculate coverage metrics."""
    # Load extraction
    with open(extraction_path) as f:
        extraction_data = json.load(f)

    # Load ground truth
    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    # Parse extraction texts and assign labels using preprocessing
    pdf_texts = []
    for text_repr in extraction_data["texts"]:
        docling_label = extract_label_from_repr(text_repr)
        text_content = extract_text_from_repr(text_repr)
        target_label = preprocess_docling_label(docling_label)
        pdf_texts.append((target_label, text_content))

    # Get HTML ground truth
    html_body = [p["text"] for p in gt_data["body_text_paragraphs"]]
    html_footnotes = [p["text"] for p in gt_data.get("footnotes", [])]

    # Calculate coverage
    metrics = calculate_content_coverage(pdf_texts, html_body, html_footnotes)

    return {"pdf_name": extraction_path.stem.replace("_baseline_extraction", ""), **metrics}


def create_histogram(values: list[float], title: str, num_bins: int = 10) -> str:
    """Create a simple ASCII histogram."""
    if not values:
        return "No data"

    # Define bins
    min_val = min(values)
    max_val = max(values)
    bin_width = (max_val - min_val) / num_bins if max_val > min_val else 1.0

    # Count values in each bin
    bins = []
    for i in range(num_bins):
        bin_start = min_val + i * bin_width
        bin_end = bin_start + bin_width
        count = sum(
            1 for v in values if bin_start <= v < bin_end or (i == num_bins - 1 and v == max_val)
        )
        bins.append((bin_start, bin_end, count))

    # Find max count for scaling
    max_count = max(b[2] for b in bins)

    # Build histogram
    lines = [f"\n{title}"]
    lines.append("=" * 60)

    for bin_start, bin_end, count in bins:
        bar_length = int(40 * count / max_count) if max_count > 0 else 0
        bar = "█" * bar_length
        lines.append(f"{bin_start:5.1%} - {bin_end:5.1%} | {bar} {count:2d}")

    return "\n".join(lines)


def main():
    # Paths
    extraction_dir = Path("results/ocr_pipeline_evaluation/extractions")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    output_dir = Path("results/ocr_pipeline_evaluation/metrics")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all baseline extractions
    extraction_files = sorted(extraction_dir.glob("*_baseline_extraction.json"))

    print(f"Processing {len(extraction_files)} PDFs...\n")

    # Process all PDFs
    results = []
    for extraction_path in extraction_files:
        pdf_name = extraction_path.stem.replace("_baseline_extraction", "")
        gt_path = gt_dir / f"{pdf_name}_ground_truth.json"

        if not gt_path.exists():
            print(f"⚠️  Skipping {pdf_name}: ground truth not found")
            continue

        print(f"Processing {pdf_name}...")
        result = process_pdf(extraction_path, gt_path)
        results.append(result)

        print(f"  Body: {result['body_coverage']:.1%}")
        print(f"  Footnote: {result['footnote_coverage']:.1%}")
        print(f"  Overall: {result['overall_coverage']:.1%}\n")

    # Calculate summary statistics
    body_coverages = [r["body_coverage"] for r in results]
    footnote_coverages = [r["footnote_coverage"] for r in results]
    overall_coverages = [r["overall_coverage"] for r in results]

    print("\n" + "=" * 60)
    print("DOCLING-ONLY COVERAGE SUMMARY")
    print("=" * 60)
    print(f"Total PDFs: {len(results)}")
    print("\nBody Coverage:")
    print(f"  Mean: {sum(body_coverages) / len(body_coverages):.1%}")
    print(f"  Min:  {min(body_coverages):.1%}")
    print(f"  Max:  {max(body_coverages):.1%}")
    print("\nFootnote Coverage:")
    print(f"  Mean: {sum(footnote_coverages) / len(footnote_coverages):.1%}")
    print(f"  Min:  {min(footnote_coverages):.1%}")
    print(f"  Max:  {max(footnote_coverages):.1%}")
    print("\nOverall Coverage:")
    print(f"  Mean: {sum(overall_coverages) / len(overall_coverages):.1%}")
    print(f"  Min:  {min(overall_coverages):.1%}")
    print(f"  Max:  {max(overall_coverages):.1%}")

    # Create histograms
    print(create_histogram(body_coverages, "BODY TEXT COVERAGE DISTRIBUTION"))
    print(create_histogram(footnote_coverages, "FOOTNOTE COVERAGE DISTRIBUTION"))
    print(create_histogram(overall_coverages, "OVERALL COVERAGE DISTRIBUTION"))

    # Save results to JSON
    output_file = output_dir / "docling_only_coverage.json"
    with open(output_file, "w") as f:
        json.dump(
            {
                "summary": {
                    "total_pdfs": len(results),
                    "mean_body_coverage": sum(body_coverages) / len(body_coverages),
                    "mean_footnote_coverage": sum(footnote_coverages) / len(footnote_coverages),
                    "mean_overall_coverage": sum(overall_coverages) / len(overall_coverages),
                    "min_body_coverage": min(body_coverages),
                    "max_body_coverage": max(body_coverages),
                    "min_footnote_coverage": min(footnote_coverages),
                    "max_footnote_coverage": max(footnote_coverages),
                },
                "per_pdf_results": results,
            },
            f,
            indent=2,
        )

    print(f"\n✅ Results saved to {output_file}")

    # Save CSV
    csv_file = output_dir / "docling_only_coverage.csv"
    with open(csv_file, "w") as f:
        # Header
        f.write("pdf_name,body_coverage,footnote_coverage,overall_coverage,")
        f.write("pdf_body_chars,pdf_footnote_chars,html_body_chars,html_footnote_chars\n")

        # Rows
        for r in results:
            f.write(f"{r['pdf_name']},{r['body_coverage']:.4f},{r['footnote_coverage']:.4f},")
            f.write(f"{r['overall_coverage']:.4f},{r['pdf_body_chars']},{r['pdf_footnote_chars']},")
            f.write(f"{r['html_body_chars']},{r['html_footnote_chars']}\n")

    print(f"✅ CSV saved to {csv_file}")


if __name__ == "__main__":
    main()

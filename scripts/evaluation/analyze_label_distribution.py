#!/usr/bin/env python3
"""
Analyze the distribution of body:footnote:other labels across the corpus.

Shows both PDF extraction labels and HTML ground truth for comparison.
"""

import json
import re
from pathlib import Path


def preprocess_docling_label(docling_label: str) -> str:
    """Map Docling labels to target labels."""
    if docling_label in ["page_header", "page_footer"]:
        return "other"
    elif docling_label in ["section_header", "list_item"]:
        return "body-text"
    elif docling_label == "footnote":
        return "footnote-text"
    elif docling_label == "text":
        return "body-text"
    else:
        return "other"


def extract_label_from_repr(text_repr: str) -> str:
    """Extract the Docling label."""
    match = re.search(r"label=<DocItemLabel\.\w+: '([^']+)'>", text_repr)
    return match.group(1) if match else "unknown"


def extract_text_from_repr(text_repr: str) -> str:
    """Extract text content."""
    match = re.search(r"text='([^']*(?:''[^']*)*)'", text_repr)
    return match.group(1).replace("\\'", "'") if match else ""


def analyze_document(extraction_path: Path, ground_truth_path: Path) -> dict:
    """Analyze label distribution for one document."""

    # Load data
    with open(extraction_path) as f:
        extraction_data = json.load(f)

    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    # Parse PDF extractions
    pdf_body_chars = 0
    pdf_footnote_chars = 0
    pdf_other_chars = 0

    for text_repr in extraction_data["texts"]:
        docling_label = extract_label_from_repr(text_repr)
        text_content = extract_text_from_repr(text_repr)
        target_label = preprocess_docling_label(docling_label)

        char_count = len(text_content)

        if target_label == "body-text":
            pdf_body_chars += char_count
        elif target_label == "footnote-text":
            pdf_footnote_chars += char_count
        else:  # "other"
            pdf_other_chars += char_count

    pdf_total = pdf_body_chars + pdf_footnote_chars + pdf_other_chars

    # Parse HTML ground truth
    html_body_chars = sum(len(p["text"]) for p in gt_data["body_text_paragraphs"])
    html_footnote_chars = sum(len(p["text"]) for p in gt_data.get("footnotes", []))
    html_total = html_body_chars + html_footnote_chars

    return {
        "pdf": {
            "body": pdf_body_chars,
            "footnote": pdf_footnote_chars,
            "other": pdf_other_chars,
            "total": pdf_total,
        },
        "html": {
            "body": html_body_chars,
            "footnote": html_footnote_chars,
            "total": html_total,
        },
    }


def main():
    extraction_dir = Path("results/ocr_pipeline_evaluation/extractions")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    extraction_files = sorted(extraction_dir.glob("*_baseline_extraction.json"))

    print("=" * 100)
    print("LABEL DISTRIBUTION ANALYSIS: body:footnote:other")
    print("=" * 100)

    # Aggregate across corpus
    total_pdf_body = 0
    total_pdf_footnote = 0
    total_pdf_other = 0
    total_html_body = 0
    total_html_footnote = 0

    per_doc_results = []

    for extraction_path in extraction_files:
        pdf_name = extraction_path.stem.replace("_baseline_extraction", "")

        # Skip antitrusts_paradox
        if "antitrust" in pdf_name.lower():
            continue

        gt_path = gt_dir / f"{pdf_name}_ground_truth.json"
        if not gt_path.exists():
            continue

        result = analyze_document(extraction_path, gt_path)
        result["pdf_name"] = pdf_name
        per_doc_results.append(result)

        # Aggregate
        total_pdf_body += result["pdf"]["body"]
        total_pdf_footnote += result["pdf"]["footnote"]
        total_pdf_other += result["pdf"]["other"]
        total_html_body += result["html"]["body"]
        total_html_footnote += result["html"]["footnote"]

    # Corpus-level statistics
    print("\n" + "-" * 100)
    print("CORPUS-LEVEL DISTRIBUTION")
    print("-" * 100)

    total_pdf = total_pdf_body + total_pdf_footnote + total_pdf_other
    total_html = total_html_body + total_html_footnote

    print("\nHTML Ground Truth (characters):")
    print(f"  Body:     {total_html_body:,} chars ({100 * total_html_body / total_html:.1f}%)")
    print(
        f"  Footnote: {total_html_footnote:,} chars ({100 * total_html_footnote / total_html:.1f}%)"
    )
    print(f"  Total:    {total_html:,} chars")

    body_fn_ratio = (
        total_html_body / total_html_footnote if total_html_footnote > 0 else float("inf")
    )
    print(f"\n  Ratio body:footnote = {body_fn_ratio:.2f}:1")

    print("\nPDF Extraction (characters):")
    print(f"  Body:     {total_pdf_body:,} chars ({100 * total_pdf_body / total_pdf:.1f}%)")
    print(f"  Footnote: {total_pdf_footnote:,} chars ({100 * total_pdf_footnote / total_pdf:.1f}%)")
    print(f"  Other:    {total_pdf_other:,} chars ({100 * total_pdf_other / total_pdf:.1f}%)")
    print(f"  Total:    {total_pdf:,} chars")

    if total_pdf_footnote > 0:
        pdf_body_fn_ratio = total_pdf_body / total_pdf_footnote
        print(
            f"\n  Ratio body:footnote:other = {pdf_body_fn_ratio:.2f}:{1}:{total_pdf_other / total_pdf_footnote:.2f}"
        )

    # Per-document breakdown
    print("\n" + "-" * 100)
    print("PER-DOCUMENT DISTRIBUTION")
    print("-" * 100)
    print(f"\n{'Document':<60} {'Body':<8} {'Footnote':<8} {'Other':<8} {'B:F Ratio':<10}")
    print("-" * 100)

    for result in sorted(per_doc_results, key=lambda r: r["pdf_name"]):
        pdf = result["pdf"]

        if pdf["total"] == 0:
            continue

        body_pct = 100 * pdf["body"] / pdf["total"]
        fn_pct = 100 * pdf["footnote"] / pdf["total"]
        other_pct = 100 * pdf["other"] / pdf["total"]

        if pdf["footnote"] > 0:
            ratio = pdf["body"] / pdf["footnote"]
            ratio_str = f"{ratio:.2f}:1"
        else:
            ratio_str = "∞:1"

        print(
            f"{result['pdf_name']:<60} {body_pct:>6.1f}%  {fn_pct:>6.1f}%  {other_pct:>6.1f}%  {ratio_str:<10}"
        )

    # Summary statistics
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    print(f"""
GROUND TRUTH (HTML):
  Total content: {total_html:,} chars
  Body: {100 * total_html_body / total_html:.1f}%
  Footnote: {100 * total_html_footnote / total_html:.1f}%
  Ratio: {body_fn_ratio:.2f}:1

EXTRACTED (PDF):
  Total content: {total_pdf:,} chars ({100 * total_pdf / total_html:.1f}% of ground truth)
  Body: {100 * total_pdf_body / total_pdf:.1f}%
  Footnote: {100 * total_pdf_footnote / total_pdf:.1f}%
  Other (headers/footers): {100 * total_pdf_other / total_pdf:.1f}%

KEY INSIGHTS:
  - PDF extraction captures {100 * total_pdf / total_html:.1f}% of total ground truth
  - "Other" content makes up {100 * total_pdf_other / total_pdf:.1f}% of PDF extraction
  - This "other" content is noise (headers, footers, page numbers)
  - Suggests we should filter "other" labels before evaluation
""")


if __name__ == "__main__":
    main()

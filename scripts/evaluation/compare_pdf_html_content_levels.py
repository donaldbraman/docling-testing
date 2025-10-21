#!/usr/bin/env python3
"""
Compare content levels between PDF extraction and HTML ground truth.

Shows which documents have relatively equal extraction vs missing content.
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
    """Compare PDF vs HTML content levels for one document."""

    # Load data
    with open(extraction_path) as f:
        extraction_data = json.load(f)

    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    # Parse PDF extractions (excluding "other")
    pdf_body_chars = 0
    pdf_footnote_chars = 0

    for text_repr in extraction_data["texts"]:
        docling_label = extract_label_from_repr(text_repr)
        text_content = extract_text_from_repr(text_repr)
        target_label = preprocess_docling_label(docling_label)

        if target_label == "body-text":
            pdf_body_chars += len(text_content)
        elif target_label == "footnote-text":
            pdf_footnote_chars += len(text_content)

    pdf_total = pdf_body_chars + pdf_footnote_chars

    # Parse HTML ground truth
    html_body_chars = sum(len(p["text"]) for p in gt_data["body_text_paragraphs"])
    html_footnote_chars = sum(len(p["text"]) for p in gt_data.get("footnotes", []))
    html_total = html_body_chars + html_footnote_chars

    # Calculate coverage ratios
    body_coverage = pdf_body_chars / html_body_chars if html_body_chars > 0 else 0
    footnote_coverage = pdf_footnote_chars / html_footnote_chars if html_footnote_chars > 0 else 0
    overall_coverage = pdf_total / html_total if html_total > 0 else 0

    return {
        "pdf_body": pdf_body_chars,
        "pdf_footnote": pdf_footnote_chars,
        "pdf_total": pdf_total,
        "html_body": html_body_chars,
        "html_footnote": html_footnote_chars,
        "html_total": html_total,
        "body_coverage": body_coverage,
        "footnote_coverage": footnote_coverage,
        "overall_coverage": overall_coverage,
    }


def main():
    extraction_dir = Path("results/ocr_pipeline_evaluation/extractions")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    extraction_files = sorted(extraction_dir.glob("*_baseline_extraction.json"))

    print("=" * 120)
    print("PDF vs HTML CONTENT LEVEL COMPARISON")
    print("=" * 120)

    results = []

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
        results.append(result)

    # Sort by overall coverage (best to worst)
    results_sorted = sorted(results, key=lambda r: r["overall_coverage"], reverse=True)

    print("\n" + "-" * 120)
    print("DOCUMENTS SORTED BY EXTRACTION COMPLETENESS")
    print("-" * 120)
    print(
        f"\n{'Document':<62} {'Overall':<10} {'Body':<10} {'Footnote':<10} {'PDF Total':<12} {'HTML Total':<12}"
    )
    print("-" * 120)

    for result in results_sorted:
        print(
            f"{result['pdf_name']:<62} "
            f"{result['overall_coverage']:>8.1%}  "
            f"{result['body_coverage']:>8.1%}  "
            f"{result['footnote_coverage']:>8.1%}  "
            f"{result['pdf_total']:>10,}  "
            f"{result['html_total']:>10,}"
        )

    # Categorize documents
    print("\n" + "=" * 120)
    print("CATEGORIZATION BY EXTRACTION QUALITY")
    print("=" * 120)

    excellent = [r for r in results if r["overall_coverage"] >= 0.5]
    good = [r for r in results if 0.3 <= r["overall_coverage"] < 0.5]
    moderate = [r for r in results if 0.1 <= r["overall_coverage"] < 0.3]
    poor = [r for r in results if r["overall_coverage"] < 0.1]

    print(f"\nEXCELLENT (≥50% coverage): {len(excellent)} documents")
    for r in excellent:
        print(f"  • {r['pdf_name'][:60]}: {r['overall_coverage']:.1%}")

    print(f"\nGOOD (30-50% coverage): {len(good)} documents")
    for r in good:
        print(f"  • {r['pdf_name'][:60]}: {r['overall_coverage']:.1%}")

    print(f"\nMODERATE (10-30% coverage): {len(moderate)} documents")
    for r in moderate:
        print(f"  • {r['pdf_name'][:60]}: {r['overall_coverage']:.1%}")

    print(f"\nPOOR (<10% coverage): {len(poor)} documents")
    for r in poor:
        print(f"  • {r['pdf_name'][:60]}: {r['overall_coverage']:.1%}")

    # Detailed analysis of best documents
    print("\n" + "=" * 120)
    print("DETAILED ANALYSIS OF BEST EXTRACTIONS")
    print("=" * 120)

    for result in results_sorted[:3]:
        print(f"\n{result['pdf_name']}")
        print("-" * 120)
        print(f"  Overall coverage: {result['overall_coverage']:.1%}")
        print(
            f"  Body coverage:    {result['body_coverage']:.1%} ({result['pdf_body']:,} / {result['html_body']:,} chars)"
        )
        print(
            f"  Footnote coverage: {result['footnote_coverage']:.1%} ({result['pdf_footnote']:,} / {result['html_footnote']:,} chars)"
        )

    # Detailed analysis of worst documents
    print("\n" + "=" * 120)
    print("DETAILED ANALYSIS OF WORST EXTRACTIONS")
    print("=" * 120)

    for result in results_sorted[-3:]:
        print(f"\n{result['pdf_name']}")
        print("-" * 120)
        print(f"  Overall coverage: {result['overall_coverage']:.1%}")
        print(
            f"  Body coverage:    {result['body_coverage']:.1%} ({result['pdf_body']:,} / {result['html_body']:,} chars)"
        )
        print(
            f"  Footnote coverage: {result['footnote_coverage']:.1%} ({result['pdf_footnote']:,} / {result['html_footnote']:,} chars)"
        )

    # Summary statistics
    print("\n" + "=" * 120)
    print("SUMMARY STATISTICS")
    print("=" * 120)

    avg_overall = sum(r["overall_coverage"] for r in results) / len(results)
    avg_body = sum(r["body_coverage"] for r in results) / len(results)
    avg_footnote = sum(r["footnote_coverage"] for r in results) / len(results)

    print(f"\nAverage coverage across {len(results)} documents:")
    print(f"  Overall:  {avg_overall:.1%}")
    print(f"  Body:     {avg_body:.1%}")
    print(f"  Footnote: {avg_footnote:.1%}")

    print("\nDistribution:")
    print(
        f"  Excellent (≥50%):  {len(excellent)} docs ({100 * len(excellent) / len(results):.1f}%)"
    )
    print(f"  Good (30-50%):     {len(good)} docs ({100 * len(good) / len(results):.1f}%)")
    print(f"  Moderate (10-30%): {len(moderate)} docs ({100 * len(moderate) / len(results):.1f}%)")
    print(f"  Poor (<10%):       {len(poor)} docs ({100 * len(poor) / len(results):.1f}%)")


if __name__ == "__main__":
    main()

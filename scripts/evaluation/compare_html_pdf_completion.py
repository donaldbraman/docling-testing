#!/usr/bin/env python3
"""
Compare HTML vs PDF OCR to detect if OCR is incomplete (e.g., only first few pages).

Checks:
1. Last footnote number in HTML vs PDF
2. Last paragraph in HTML vs PDF (fuzzy match)
3. Overall content completeness
"""

import json
import re
from pathlib import Path

from rapidfuzz import fuzz


def extract_label_from_repr(text_repr: str) -> str:
    """Extract the Docling label."""
    match = re.search(r"label=<DocItemLabel\.\w+: '([^']+)'>", text_repr)
    return match.group(1) if match else "unknown"


def extract_text_from_repr(text_repr: str) -> str:
    """Extract text content."""
    match = re.search(r"text='([^']*(?:''[^']*)*)'", text_repr)
    return match.group(1).replace("\\'", "'") if match else ""


def extract_footnote_numbers(text: str) -> list[int]:
    """Extract all footnote numbers from text."""
    # Look for patterns like: ^1, [1], (1), ¹, etc.
    numbers = []

    # Pattern 1: Superscript numbers in text (most common in PDF OCR)
    numbers.extend([int(n) for n in re.findall(r"\b(\d{1,3})\b", text)])

    return numbers


def analyze_document(extraction_path: Path, ground_truth_path: Path) -> dict:
    """Compare HTML vs PDF completion for one document."""

    # Load data
    with open(extraction_path) as f:
        extraction_data = json.load(f)

    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    # Get PDF extraction info
    pdf_texts = []
    pdf_footnote_labels = []

    for text_repr in extraction_data["texts"]:
        docling_label = extract_label_from_repr(text_repr)
        text_content = extract_text_from_repr(text_repr)

        pdf_texts.append(
            {"label": docling_label, "text": text_content, "length": len(text_content)}
        )

        if docling_label == "footnote":
            pdf_footnote_labels.append(text_content)

    # Get HTML ground truth info
    html_body = gt_data["body_text_paragraphs"]
    html_footnotes = gt_data.get("footnotes", [])

    # Extract footnote numbers from HTML (from body text references)
    html_all_body_text = " ".join([p["text"] for p in html_body])
    html_footnote_numbers = extract_footnote_numbers(html_all_body_text)
    max_html_footnote = max(html_footnote_numbers) if html_footnote_numbers else 0

    # Extract footnote numbers from PDF
    pdf_all_text = " ".join([t["text"] for t in pdf_texts])
    pdf_footnote_numbers = extract_footnote_numbers(pdf_all_text)
    max_pdf_footnote = max(pdf_footnote_numbers) if pdf_footnote_numbers else 0

    # Get last paragraphs
    html_last_para = html_body[-1]["text"][:500] if html_body else ""
    pdf_last_para = pdf_texts[-1]["text"][:500] if pdf_texts else ""

    # Fuzzy match last paragraphs
    last_para_similarity = fuzz.ratio(html_last_para.lower(), pdf_last_para.lower())

    # Get first paragraphs for comparison
    html_first_para = html_body[0]["text"][:500] if html_body else ""
    pdf_first_para = ""
    for t in pdf_texts:
        if len(t["text"]) > 50:  # Skip headers
            pdf_first_para = t["text"][:500]
            break

    first_para_similarity = fuzz.ratio(html_first_para.lower(), pdf_first_para.lower())

    # Total content comparison
    html_total_chars = sum(len(p["text"]) for p in html_body) + sum(
        len(fn["text"]) for fn in html_footnotes
    )
    pdf_total_chars = sum(t["length"] for t in pdf_texts)

    completion_ratio = pdf_total_chars / html_total_chars if html_total_chars > 0 else 0

    return {
        "max_html_footnote": max_html_footnote,
        "max_pdf_footnote": max_pdf_footnote,
        "footnote_gap": max_html_footnote - max_pdf_footnote,
        "html_footnote_count": len(html_footnotes),
        "pdf_footnote_count": len(pdf_footnote_labels),
        "html_body_paragraphs": len(html_body),
        "pdf_text_blocks": len(pdf_texts),
        "html_total_chars": html_total_chars,
        "pdf_total_chars": pdf_total_chars,
        "completion_ratio": completion_ratio,
        "last_para_similarity": last_para_similarity,
        "first_para_similarity": first_para_similarity,
        "html_last_para": html_last_para[:200],
        "pdf_last_para": pdf_last_para[:200],
    }


def main():
    extraction_dir = Path("results/ocr_pipeline_evaluation/extractions")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    extraction_files = sorted(extraction_dir.glob("*_baseline_extraction.json"))

    print("=" * 120)
    print("HTML vs PDF COMPLETION ANALYSIS")
    print("=" * 120)
    print("\nChecking if PDF OCR is incomplete (e.g., only extracting first few pages)\n")

    results = []

    for extraction_path in extraction_files:
        pdf_name = extraction_path.stem.replace("_baseline_extraction", "")

        # Skip antitrusts_paradox
        if "antitrust" in pdf_name.lower():
            continue

        gt_path = gt_dir / f"{pdf_name}_ground_truth.json"
        if not gt_path.exists():
            continue

        try:
            result = analyze_document(extraction_path, gt_path)
            result["pdf_name"] = pdf_name
            results.append(result)
        except Exception as e:
            print(f"Error processing {pdf_name}: {e}")
            continue

    # Sort by completion ratio (worst first)
    results_sorted = sorted(results, key=lambda r: r["completion_ratio"])

    print("-" * 120)
    print("DOCUMENTS SORTED BY COMPLETION (worst first)")
    print("-" * 120)
    print(
        f"\n{'Document':<50} {'Complete':<10} {'Last FN':<12} {'Last Para':<12} {'First Para':<12}"
    )
    print("-" * 120)

    for result in results_sorted:
        last_fn_str = f"{result['max_pdf_footnote']}/{result['max_html_footnote']}"

        # Color coding for severity
        marker = ""
        if result["completion_ratio"] < 0.2:
            marker = "❌"  # Very incomplete
        elif result["completion_ratio"] < 0.5:
            marker = "⚠️"  # Moderately incomplete
        elif result["last_para_similarity"] > 80:
            marker = "✅"  # Complete

        print(
            f"{result['pdf_name']:<50} "
            f"{result['completion_ratio']:>8.1%}  "
            f"{last_fn_str:>10}  "
            f"{result['last_para_similarity']:>10}%  "
            f"{result['first_para_similarity']:>10}%  {marker}"
        )

    # Categorize by completion
    print("\n" + "=" * 120)
    print("CATEGORIZATION BY COMPLETION")
    print("=" * 120)

    very_incomplete = [r for r in results if r["completion_ratio"] < 0.2]
    incomplete = [r for r in results if 0.2 <= r["completion_ratio"] < 0.5]
    partial = [r for r in results if 0.5 <= r["completion_ratio"] < 0.8]
    complete = [r for r in results if r["completion_ratio"] >= 0.8]

    print(f"\nVERY INCOMPLETE (<20% of content): {len(very_incomplete)} documents")
    for r in very_incomplete[:10]:
        fn_info = (
            f"(FN: {r['max_pdf_footnote']}/{r['max_html_footnote']})"
            if r["max_html_footnote"] > 0
            else ""
        )
        print(f"  ❌ {r['pdf_name'][:60]}: {r['completion_ratio']:.1%} {fn_info}")

    print(f"\nINCOMPLETE (20-50% of content): {len(incomplete)} documents")
    for r in incomplete[:10]:
        fn_info = (
            f"(FN: {r['max_pdf_footnote']}/{r['max_html_footnote']})"
            if r["max_html_footnote"] > 0
            else ""
        )
        print(f"  ⚠️  {r['pdf_name'][:60]}: {r['completion_ratio']:.1%} {fn_info}")

    print(f"\nPARTIAL (50-80% of content): {len(partial)} documents")
    for r in partial[:10]:
        fn_info = (
            f"(FN: {r['max_pdf_footnote']}/{r['max_html_footnote']})"
            if r["max_html_footnote"] > 0
            else ""
        )
        print(f"  {r['pdf_name'][:60]}: {r['completion_ratio']:.1%} {fn_info}")

    print(f"\nCOMPLETE (≥80% of content): {len(complete)} documents")
    for r in complete[:10]:
        fn_info = (
            f"(FN: {r['max_pdf_footnote']}/{r['max_html_footnote']})"
            if r["max_html_footnote"] > 0
            else ""
        )
        print(f"  ✅ {r['pdf_name'][:60]}: {r['completion_ratio']:.1%} {fn_info}")

    # Detailed examples
    print("\n" + "=" * 120)
    print("DETAILED EXAMPLES: INCOMPLETE EXTRACTIONS")
    print("=" * 120)

    for result in very_incomplete[:3]:
        print(f"\n{result['pdf_name']}")
        print("-" * 120)
        print(f"  Completion: {result['completion_ratio']:.1%}")
        print(
            f"  Max footnote: PDF={result['max_pdf_footnote']}, HTML={result['max_html_footnote']} (missing {result['footnote_gap']} footnotes)"
        )
        print(f"  Last paragraph similarity: {result['last_para_similarity']}%")
        print(f"\n  HTML last paragraph: '{result['html_last_para']}...'")
        print(f"  PDF last paragraph:  '{result['pdf_last_para']}...'")

    # Summary
    print("\n" + "=" * 120)
    print("SUMMARY")
    print("=" * 120)

    avg_completion = sum(r["completion_ratio"] for r in results) / len(results)
    avg_last_para_sim = sum(r["last_para_similarity"] for r in results) / len(results)

    print(f"""
Total documents analyzed: {len(results)}

Completion distribution:
  Very incomplete (<20%):  {len(very_incomplete)} docs ({100 * len(very_incomplete) / len(results):.1f}%)
  Incomplete (20-50%):     {len(incomplete)} docs ({100 * len(incomplete) / len(results):.1f}%)
  Partial (50-80%):        {len(partial)} docs ({100 * len(partial) / len(results):.1f}%)
  Complete (≥80%):         {len(complete)} docs ({100 * len(complete) / len(results):.1f}%)

Average completion: {avg_completion:.1%}
Average last paragraph similarity: {avg_last_para_sim:.1f}%

INTERPRETATION:
  - Very incomplete/Incomplete: PDF OCR is likely only getting first few pages
  - Partial: PDF OCR is getting most content but missing some pages/sections
  - Complete: PDF OCR is extracting nearly all content

  Low last paragraph similarity suggests OCR stopped early (didn't reach end of document)
""")

    if len(very_incomplete) + len(incomplete) > len(results) / 2:
        print(
            f"⚠️  WARNING: {len(very_incomplete) + len(incomplete)} documents ({100 * (len(very_incomplete) + len(incomplete)) / len(results):.1f}%) have <50% completion"
        )
        print("   This suggests PDF OCR is only extracting first few pages for most documents")
    else:
        print(f"✅ Most documents ({len(partial) + len(complete)}) have >50% completion")


if __name__ == "__main__":
    main()

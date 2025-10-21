#!/usr/bin/env python3
"""
Compare absolute content levels between PDF and HTML documents.

Shows which document pairs have similar total content length,
regardless of extraction quality.
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
    """Get total content sizes for PDF and HTML."""

    # Load data
    with open(extraction_path) as f:
        extraction_data = json.load(f)

    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    # Total PDF content (all labels)
    pdf_total = 0
    for text_repr in extraction_data["texts"]:
        text_content = extract_text_from_repr(text_repr)
        pdf_total += len(text_content)

    # Total HTML ground truth
    html_body_chars = sum(len(p["text"]) for p in gt_data["body_text_paragraphs"])
    html_footnote_chars = sum(len(p["text"]) for p in gt_data.get("footnotes", []))
    html_total = html_body_chars + html_footnote_chars

    # Calculate ratio
    ratio = pdf_total / html_total if html_total > 0 else 0
    difference = abs(pdf_total - html_total)
    similarity = (
        min(pdf_total, html_total) / max(pdf_total, html_total)
        if max(pdf_total, html_total) > 0
        else 0
    )

    return {
        "pdf_total": pdf_total,
        "html_total": html_total,
        "pdf_to_html_ratio": ratio,
        "absolute_difference": difference,
        "similarity": similarity,  # 1.0 = equal size, 0.0 = very different
    }


def main():
    extraction_dir = Path("results/ocr_pipeline_evaluation/extractions")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    extraction_files = sorted(extraction_dir.glob("*_baseline_extraction.json"))

    print("=" * 120)
    print("ABSOLUTE CONTENT LEVEL COMPARISON (PDF vs HTML)")
    print("=" * 120)
    print("\nShowing which document pairs have similar total content length\n")

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

    # Sort by similarity (most similar sizes first)
    results_sorted = sorted(results, key=lambda r: r["similarity"], reverse=True)

    print("-" * 120)
    print("DOCUMENTS SORTED BY SIZE SIMILARITY")
    print("-" * 120)
    print(
        f"\n{'Document':<62} {'PDF Size':<12} {'HTML Size':<12} {'Similarity':<12} {'Difference':<12}"
    )
    print("-" * 120)

    for result in results_sorted:
        print(
            f"{result['pdf_name']:<62} "
            f"{result['pdf_total']:>10,}  "
            f"{result['html_total']:>10,}  "
            f"{result['similarity']:>10.1%}  "
            f"{result['absolute_difference']:>10,}"
        )

    # Categorize by similarity
    print("\n" + "=" * 120)
    print("CATEGORIZATION BY SIZE SIMILARITY")
    print("=" * 120)

    very_similar = [r for r in results if r["similarity"] >= 0.8]  # Within 20% of each other
    similar = [r for r in results if 0.5 <= r["similarity"] < 0.8]  # Within 50%
    different = [r for r in results if 0.2 <= r["similarity"] < 0.5]  # 2-5x difference
    very_different = [r for r in results if r["similarity"] < 0.2]  # >5x difference

    print(f"\nVERY SIMILAR (≥80% size match): {len(very_similar)} documents")
    for r in very_similar:
        print(
            f"  • {r['pdf_name'][:60]}: PDF={r['pdf_total']:,} HTML={r['html_total']:,} ({r['similarity']:.1%})"
        )

    print(f"\nSIMILAR (50-80% size match): {len(similar)} documents")
    for r in similar:
        print(
            f"  • {r['pdf_name'][:60]}: PDF={r['pdf_total']:,} HTML={r['html_total']:,} ({r['similarity']:.1%})"
        )

    print(f"\nDIFFERENT (20-50% size match): {len(different)} documents")
    for r in different:
        print(
            f"  • {r['pdf_name'][:60]}: PDF={r['pdf_total']:,} HTML={r['html_total']:,} ({r['similarity']:.1%})"
        )

    print(f"\nVERY DIFFERENT (<20% size match): {len(very_different)} documents")
    for r in very_different:
        ratio_str = (
            f"{r['pdf_to_html_ratio']:.1%}"
            if r["pdf_to_html_ratio"] < 1
            else f"{1 / r['pdf_to_html_ratio']:.1%} (HTML larger)"
        )
        print(
            f"  • {r['pdf_name'][:60]}: PDF={r['pdf_total']:,} HTML={r['html_total']:,} ({ratio_str})"
        )

    # Summary
    print("\n" + "=" * 120)
    print("SUMMARY")
    print("=" * 120)

    print(f"""
Total documents analyzed: {len(results)}

Size similarity distribution:
  Very similar (≥80%):  {len(very_similar)} docs ({100 * len(very_similar) / len(results):.1f}%)
  Similar (50-80%):     {len(similar)} docs ({100 * len(similar) / len(results):.1f}%)
  Different (20-50%):   {len(different)} docs ({100 * len(different) / len(results):.1f}%)
  Very different (<20%): {len(very_different)} docs ({100 * len(very_different) / len(results):.1f}%)

INTERPRETATION:
  - Very similar: PDF and HTML have nearly equal total content (good for testing)
  - Similar: PDF has 50-80% of HTML content (moderate for testing)
  - Different/Very different: PDF has much less content than HTML (poor for testing)

DOCUMENTS WITH EQUAL CONTENT LEVELS:
""")

    if very_similar:
        print("  Best matches for testing (nearly equal PDF/HTML sizes):")
        for r in very_similar:
            print(f"    • {r['pdf_name'][:60]}")
    else:
        print("  No documents have very similar PDF/HTML sizes (≥80% match)")

    if similar:
        print("\n  Moderate matches for testing (50-80% size match):")
        for r in similar:
            print(f"    • {r['pdf_name'][:60]}")


if __name__ == "__main__":
    main()

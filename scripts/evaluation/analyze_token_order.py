#!/usr/bin/env python3
"""
Analyze why token_set_ratio gives higher scores than order-sensitive methods.

Investigates:
1. How much text is actually in wrong order?
2. What's the longest ordered subsequence we can find?
3. Are there duplicate removal benefits?
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from rapidfuzz import fuzz


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


def get_unique_token_counts(text: str) -> tuple[int, int]:
    """Get unique and total token counts."""
    tokens = text.split()
    return len(set(tokens)), len(tokens)


def longest_common_substring_ratio(s1: str, s2: str) -> float:
    """Find longest common substring as ratio of shorter string."""
    matcher = SequenceMatcher(None, s1, s2)
    match = matcher.find_longest_match(0, len(s1), 0, len(s2))
    lcs_length = match.size
    shorter_length = min(len(s1), len(s2))
    return lcs_length / shorter_length if shorter_length > 0 else 0.0


def analyze_order_sensitivity(pdf_text: str, html_text: str, label: str) -> dict:
    """Analyze why order-insensitive matching scores higher."""
    norm_pdf = normalize_text(pdf_text)
    norm_html = normalize_text(html_text)

    # Different fuzzy strategies
    ratio_score = fuzz.ratio(norm_pdf, norm_html) / 100.0
    partial_score = fuzz.partial_ratio(norm_pdf, norm_html) / 100.0
    token_sort_score = fuzz.token_sort_ratio(norm_pdf, norm_html) / 100.0
    token_set_score = fuzz.token_set_ratio(norm_pdf, norm_html) / 100.0

    # Token analysis
    pdf_unique, pdf_total = get_unique_token_counts(norm_pdf)
    html_unique, html_total = get_unique_token_counts(norm_html)

    # Longest common substring
    lcs_ratio = longest_common_substring_ratio(norm_pdf, norm_html)

    # Calculate order difference impact
    order_penalty = token_set_score - ratio_score
    duplicate_benefit = token_set_score - token_sort_score

    return {
        "label": label,
        "pdf_chars": len(norm_pdf),
        "html_chars": len(norm_html),
        "pdf_unique_tokens": pdf_unique,
        "pdf_total_tokens": pdf_total,
        "html_unique_tokens": html_unique,
        "html_total_tokens": html_total,
        "pdf_duplicate_ratio": (pdf_total - pdf_unique) / pdf_total if pdf_total > 0 else 0,
        "html_duplicate_ratio": (html_total - html_unique) / html_total if html_total > 0 else 0,
        "ratio_score": ratio_score,
        "partial_score": partial_score,
        "token_sort_score": token_sort_score,
        "token_set_score": token_set_score,
        "lcs_ratio": lcs_ratio,
        "order_penalty": order_penalty,
        "duplicate_benefit": duplicate_benefit,
    }


def analyze_pdf(extraction_path: Path, ground_truth_path: Path) -> dict:
    """Analyze one PDF."""
    pdf_name = extraction_path.stem.replace("_baseline_extraction", "")

    # Skip antitrusts_paradox
    if "antitrust" in pdf_name.lower():
        return None

    # Load data
    with open(extraction_path) as f:
        extraction_data = json.load(f)

    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    # Parse extractions
    pdf_texts = []
    for text_repr in extraction_data["texts"]:
        docling_label = extract_label_from_repr(text_repr)
        text_content = extract_text_from_repr(text_repr)
        target_label = preprocess_docling_label(docling_label)
        pdf_texts.append((target_label, text_content))

    # Get ground truth
    html_body = [p["text"] for p in gt_data["body_text_paragraphs"]]
    html_footnotes = [p["text"] for p in gt_data.get("footnotes", [])]

    # Concatenate by label
    pdf_body = " ".join([text for label, text in pdf_texts if label == "body-text"])
    pdf_footnotes = " ".join([text for label, text in pdf_texts if label == "footnote-text"])
    html_body_full = " ".join(html_body)
    html_footnotes_full = " ".join(html_footnotes)

    # Analyze both
    body_analysis = analyze_order_sensitivity(pdf_body, html_body_full, "body-text")
    footnote_analysis = analyze_order_sensitivity(
        pdf_footnotes, html_footnotes_full, "footnote-text"
    )

    return {
        "pdf_name": pdf_name,
        "body": body_analysis,
        "footnote": footnote_analysis,
    }


def main():
    extraction_dir = Path("results/ocr_pipeline_evaluation/extractions")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    extraction_files = sorted(extraction_dir.glob("*_baseline_extraction.json"))

    print("Analyzing token order impact (excluding antitrusts_paradox)...\n")

    all_results = []
    for extraction_path in extraction_files:
        pdf_name = extraction_path.stem.replace("_baseline_extraction", "")

        # Skip antitrusts_paradox
        if "antitrust" in pdf_name.lower():
            print(f"⊗ Skipping {pdf_name} (excluded from corpus)")
            continue

        gt_path = gt_dir / f"{pdf_name}_ground_truth.json"
        if not gt_path.exists():
            continue

        print(f"Analyzing {pdf_name[:50]}...")
        result = analyze_pdf(extraction_path, gt_path)
        if result:
            all_results.append(result)

    # Summary statistics
    print("\n" + "=" * 120)
    print("TOKEN ORDER ANALYSIS SUMMARY")
    print("=" * 120)

    # Aggregate by label
    body_results = [r["body"] for r in all_results]
    footnote_results = [r["footnote"] for r in all_results]

    def print_label_summary(results, label_name):
        print(f"\n### {label_name}")
        print(f"{'Metric':<35} {'Mean':<12} {'Min':<12} {'Max':<12}")
        print("-" * 120)

        metrics = [
            ("Order penalty (token_set - ratio)", "order_penalty"),
            ("Duplicate benefit (token_set - sort)", "duplicate_benefit"),
            ("Longest common substring ratio", "lcs_ratio"),
            ("Token_set score", "token_set_score"),
            ("Ratio score (order-sensitive)", "ratio_score"),
            ("Partial_ratio score", "partial_score"),
            ("PDF duplicate ratio", "pdf_duplicate_ratio"),
            ("HTML duplicate ratio", "html_duplicate_ratio"),
        ]

        for metric_name, key in metrics:
            values = [r[key] for r in results if r[key] is not None]
            if values:
                mean_val = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)
                print(f"{metric_name:<35} {mean_val:>11.1%} {min_val:>11.1%} {max_val:>11.1%}")

    print_label_summary(body_results, "BODY TEXT")
    print_label_summary(footnote_results, "FOOTNOTE TEXT")

    # Per-document table
    print("\n" + "=" * 140)
    print("PER-DOCUMENT ORDER IMPACT")
    print("=" * 140)
    print(
        f"{'Document':<50} {'Label':<10} {'Order Penalty':<15} {'LCS Ratio':<12} {'Token_Set':<12} {'Ratio':<12}"
    )
    print("-" * 140)

    for result in sorted(all_results, key=lambda r: r["body"]["order_penalty"], reverse=True):
        for label_type in ["body", "footnote"]:
            data = result[label_type]
            print(
                f"{result['pdf_name']:<50} {data['label']:<10} "
                f"{data['order_penalty']:>13.1%}  {data['lcs_ratio']:>10.1%}  "
                f"{data['token_set_score']:>10.1%}  {data['ratio_score']:>10.1%}"
            )

    # Interpretation
    print("\n" + "=" * 120)
    print("INTERPRETATION")
    print("=" * 120)
    print("""
Order Penalty = token_set_score - ratio_score
  • High penalty (>40%) = Text is severely out of order
  • Medium penalty (20-40%) = Moderate reordering
  • Low penalty (<20%) = Text is mostly in correct order

Longest Common Substring (LCS) Ratio:
  • High (>60%) = Large contiguous chunks match
  • Medium (30-60%) = Some contiguous sections
  • Low (<30%) = Text is highly fragmented

Recommendations:
  • If order_penalty is high BUT lcs_ratio is high: Use partial_ratio (finds best substring)
  • If order_penalty is high AND lcs_ratio is low: Token-based methods are appropriate
  • If order_penalty is low: Use ratio (order matters)
    """)

    # Save results
    output_dir = Path("results/ocr_pipeline_evaluation/metrics")
    output_file = output_dir / "token_order_analysis.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"✅ Detailed results saved to {output_file}")


if __name__ == "__main__":
    main()

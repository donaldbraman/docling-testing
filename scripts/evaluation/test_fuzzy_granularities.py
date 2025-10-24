#!/usr/bin/env python3
"""
Test different fuzzy matching strategies to find the highest match rate.

Compares:
1. Different fuzzy matching algorithms (ratio, partial_ratio, token_sort_ratio, token_set_ratio)
2. Different granularities (full text, paragraph-level, line-level)
"""

import json
import re
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
    """Extract the Docling label from the repr string."""
    match = re.search(r"label=<DocItemLabel\.\w+: '([^']+)'>", text_repr)
    if match:
        return match.group(1)
    return "unknown"


def extract_text_from_repr(text_repr: str) -> str:
    """Extract the text content from the repr string."""
    match = re.search(r"text='([^']*(?:''[^']*)*)'", text_repr)
    if match:
        return match.group(1).replace("\\'", "'")
    return ""


def calculate_coverage_full_text(
    pdf_texts: list[tuple[str, str]], html_body: list[str], html_footnotes: list[str], fuzzy_fn
) -> dict[str, float]:
    """
    Calculate coverage by concatenating all text and using fuzzy matching.

    Args:
        fuzzy_fn: Function to use for fuzzy matching (e.g., fuzz.ratio, fuzz.partial_ratio)
    """
    pdf_body = " ".join([text for label, text in pdf_texts if label == "body-text"])
    pdf_footnotes = " ".join([text for label, text in pdf_texts if label == "footnote-text"])
    html_body_full = " ".join(html_body)
    html_footnotes_full = " ".join(html_footnotes)

    norm_pdf_body = normalize_text(pdf_body)
    norm_pdf_footnotes = normalize_text(pdf_footnotes)
    norm_html_body = normalize_text(html_body_full)
    norm_html_footnotes = normalize_text(html_footnotes_full)

    body_coverage = fuzzy_fn(norm_pdf_body, norm_html_body) / 100.0
    footnote_coverage = fuzzy_fn(norm_pdf_footnotes, norm_html_footnotes) / 100.0

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
    }


def calculate_coverage_paragraph_level(
    pdf_texts: list[tuple[str, str]], html_body: list[str], html_footnotes: list[str], fuzzy_fn
) -> dict[str, float]:
    """
    Calculate coverage by matching at paragraph level.
    For each HTML paragraph, find best-matching PDF text and average.
    """
    pdf_body_texts = [text for label, text in pdf_texts if label == "body-text"]
    pdf_footnote_texts = [text for label, text in pdf_texts if label == "footnote-text"]

    # Match each HTML paragraph to best PDF line
    body_matches = []
    for html_para in html_body:
        norm_html = normalize_text(html_para)
        if not norm_html:
            continue
        best_score = 0.0
        for pdf_text in pdf_body_texts:
            norm_pdf = normalize_text(pdf_text)
            if norm_pdf:
                score = fuzzy_fn(norm_pdf, norm_html) / 100.0
                best_score = max(best_score, score)
        body_matches.append(best_score)

    footnote_matches = []
    for html_note in html_footnotes:
        norm_html = normalize_text(html_note)
        if not norm_html:
            continue
        best_score = 0.0
        for pdf_text in pdf_footnote_texts:
            norm_pdf = normalize_text(pdf_text)
            if norm_pdf:
                score = fuzzy_fn(norm_pdf, norm_html) / 100.0
                best_score = max(best_score, score)
        footnote_matches.append(best_score)

    body_coverage = sum(body_matches) / len(body_matches) if body_matches else 0.0
    footnote_coverage = sum(footnote_matches) / len(footnote_matches) if footnote_matches else 0.0

    # Weight by character count
    html_body_chars = sum(len(p) for p in html_body)
    html_footnote_chars = sum(len(p) for p in html_footnotes)
    html_total_chars = html_body_chars + html_footnote_chars

    if html_total_chars > 0:
        body_weight = html_body_chars / html_total_chars
        footnote_weight = html_footnote_chars / html_total_chars
        overall_coverage = (body_coverage * body_weight) + (footnote_coverage * footnote_weight)
    else:
        overall_coverage = 0.0

    return {
        "body_coverage": body_coverage,
        "footnote_coverage": footnote_coverage,
        "overall_coverage": overall_coverage,
    }


def calculate_coverage_weighted_paragraph(
    pdf_texts: list[tuple[str, str]], html_body: list[str], html_footnotes: list[str], fuzzy_fn
) -> dict[str, float]:
    """
    Calculate coverage by matching at paragraph level, weighted by paragraph length.
    """
    pdf_body_texts = [text for label, text in pdf_texts if label == "body-text"]
    pdf_footnote_texts = [text for label, text in pdf_texts if label == "footnote-text"]

    # Match each HTML paragraph, weight by length
    body_weighted_scores = []
    for html_para in html_body:
        norm_html = normalize_text(html_para)
        if not norm_html:
            continue
        best_score = 0.0
        for pdf_text in pdf_body_texts:
            norm_pdf = normalize_text(pdf_text)
            if norm_pdf:
                score = fuzzy_fn(norm_pdf, norm_html) / 100.0
                best_score = max(best_score, score)
        body_weighted_scores.append(best_score * len(norm_html))

    footnote_weighted_scores = []
    for html_note in html_footnotes:
        norm_html = normalize_text(html_note)
        if not norm_html:
            continue
        best_score = 0.0
        for pdf_text in pdf_footnote_texts:
            norm_pdf = normalize_text(pdf_text)
            if norm_pdf:
                score = fuzzy_fn(norm_pdf, norm_html) / 100.0
                best_score = max(best_score, score)
        footnote_weighted_scores.append(best_score * len(norm_html))

    total_body_chars = sum(len(normalize_text(p)) for p in html_body)
    total_footnote_chars = sum(len(normalize_text(p)) for p in html_footnotes)

    body_coverage = sum(body_weighted_scores) / total_body_chars if total_body_chars > 0 else 0.0
    footnote_coverage = (
        sum(footnote_weighted_scores) / total_footnote_chars if total_footnote_chars > 0 else 0.0
    )

    total_chars = total_body_chars + total_footnote_chars
    if total_chars > 0:
        body_weight = total_body_chars / total_chars
        footnote_weight = total_footnote_chars / total_chars
        overall_coverage = (body_coverage * body_weight) + (footnote_coverage * footnote_weight)
    else:
        overall_coverage = 0.0

    return {
        "body_coverage": body_coverage,
        "footnote_coverage": footnote_coverage,
        "overall_coverage": overall_coverage,
    }


def test_all_strategies(extraction_path: Path, ground_truth_path: Path) -> dict:
    """Test all fuzzy matching strategies on one document."""
    pdf_name = extraction_path.stem.replace("_baseline_extraction", "")

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

    # Test all strategies
    strategies = {
        "full_text_ratio": (calculate_coverage_full_text, fuzz.ratio),
        "full_text_partial": (calculate_coverage_full_text, fuzz.partial_ratio),
        "full_text_token_sort": (calculate_coverage_full_text, fuzz.token_sort_ratio),
        "full_text_token_set": (calculate_coverage_full_text, fuzz.token_set_ratio),
        "paragraph_ratio": (calculate_coverage_paragraph_level, fuzz.ratio),
        "paragraph_partial": (calculate_coverage_paragraph_level, fuzz.partial_ratio),
        "paragraph_weighted_ratio": (calculate_coverage_weighted_paragraph, fuzz.ratio),
        "paragraph_weighted_partial": (calculate_coverage_weighted_paragraph, fuzz.partial_ratio),
    }

    results = {"pdf_name": pdf_name}
    for strategy_name, (calc_fn, fuzzy_fn) in strategies.items():
        coverage = calc_fn(pdf_texts, html_body, html_footnotes, fuzzy_fn)
        results[strategy_name] = coverage["overall_coverage"]

    return results


def main():
    extraction_dir = Path("results/ocr_pipeline_evaluation/extractions")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    extraction_files = sorted(extraction_dir.glob("*_baseline_extraction.json"))

    print(f"Testing fuzzy matching strategies on {len(extraction_files)} PDFs...\n")

    all_results = []
    for extraction_path in extraction_files:
        pdf_name = extraction_path.stem.replace("_baseline_extraction", "")
        gt_path = gt_dir / f"{pdf_name}_ground_truth.json"

        if not gt_path.exists():
            continue

        print(f"Testing {pdf_name[:50]}...")
        result = test_all_strategies(extraction_path, gt_path)
        all_results.append(result)

    # Calculate averages
    strategy_names = [k for k in all_results[0] if k != "pdf_name"]
    averages = {}
    for strategy in strategy_names:
        averages[strategy] = sum(r[strategy] for r in all_results) / len(all_results)

    # Print results
    print("\n" + "=" * 100)
    print("FUZZY MATCHING STRATEGY COMPARISON")
    print("=" * 100)
    print(f"{'Strategy':<35} {'Avg Coverage':<15} {'Description':<50}")
    print("-" * 100)

    descriptions = {
        "full_text_ratio": "Full concatenation, Levenshtein distance",
        "full_text_partial": "Full concatenation, substring matching",
        "full_text_token_sort": "Full concatenation, word-order invariant",
        "full_text_token_set": "Full concatenation, set-based (ignores duplicates)",
        "paragraph_ratio": "Paragraph-level matching, unweighted average",
        "paragraph_partial": "Paragraph-level matching (partial), unweighted",
        "paragraph_weighted_ratio": "Paragraph-level, weighted by char count",
        "paragraph_weighted_partial": "Paragraph-level (partial), weighted",
    }

    for strategy in sorted(strategy_names, key=lambda s: averages[s], reverse=True):
        print(f"{strategy:<35} {averages[strategy]:>13.1%}  {descriptions.get(strategy, ''):<50}")

    # Best strategy per document
    print("\n" + "=" * 100)
    print("BEST STRATEGY PER DOCUMENT")
    print("=" * 100)

    for result in sorted(all_results, key=lambda r: r["pdf_name"]):
        best_strategy = max(strategy_names, key=lambda s: result[s])
        best_score = result[best_strategy]
        print(f"{result['pdf_name']:<60} {best_strategy:<35} {best_score:>6.1%}")

    # Save detailed results
    output_dir = Path("results/ocr_pipeline_evaluation/metrics")
    output_file = output_dir / "fuzzy_strategy_comparison.json"
    with open(output_file, "w") as f:
        json.dump({"averages": averages, "per_document": all_results}, f, indent=2)

    print(f"\n✅ Detailed results saved to {output_file}")


if __name__ == "__main__":
    main()

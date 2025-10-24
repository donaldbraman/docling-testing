#!/usr/bin/env python3
"""
Show actual text examples to understand what "order penalty" really means.

The text should NOT be out of order if we're extracting in Y-axis order.
Let's see what's actually happening.
"""

import json
import re
from pathlib import Path


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


def show_text_comparison(pdf_name: str, extraction_path: Path, ground_truth_path: Path):
    """Show actual text to understand mismatches."""

    # Load data
    with open(extraction_path) as f:
        extraction_data = json.load(f)

    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    # Parse extractions with original order
    pdf_lines = []
    for i, text_repr in enumerate(extraction_data["texts"]):
        docling_label = extract_label_from_repr(text_repr)
        text_content = extract_text_from_repr(text_repr)
        target_label = preprocess_docling_label(docling_label)
        pdf_lines.append(
            {
                "index": i,
                "docling_label": docling_label,
                "target_label": target_label,
                "text": text_content,
            }
        )

    # Get ground truth
    html_body_paras = gt_data["body_text_paragraphs"]
    html_footnote_paras = gt_data.get("footnotes", [])

    # Show first 10 PDF lines vs first 5 HTML paragraphs
    print(f"\n{'=' * 120}")
    print(f"DOCUMENT: {pdf_name}")
    print(f"{'=' * 120}\n")

    print("PDF EXTRACTION (First 10 lines, in extraction order):")
    print("-" * 120)
    for line in pdf_lines[:10]:
        text_preview = line["text"][:80].replace("\n", " ")
        print(
            f"[{line['index']:3d}] {line['docling_label']:15s} → {line['target_label']:15s} | {text_preview}"
        )

    print(f"\n{'-' * 120}\n")
    print("HTML GROUND TRUTH BODY (First 5 paragraphs):")
    print("-" * 120)
    for i, para in enumerate(html_body_paras[:5], 1):
        text_preview = para["text"][:150].replace("\n", " ")
        print(f"[{i:2d}] {text_preview}")

    print(f"\n{'-' * 120}\n")
    print("HTML GROUND TRUTH FOOTNOTES (First 5):")
    print("-" * 120)
    for i, para in enumerate(html_footnote_paras[:5], 1):
        text_preview = para["text"][:150].replace("\n", " ")
        print(f"[{i:2d}] {text_preview}")

    # Show concatenated comparison
    pdf_body_lines = [line for line in pdf_lines if line["target_label"] == "body-text"]
    pdf_footnote_lines = [line for line in pdf_lines if line["target_label"] == "footnote-text"]

    pdf_body_text = " ".join([line["text"] for line in pdf_body_lines])
    pdf_footnote_text = " ".join([line["text"] for line in pdf_footnote_lines])

    html_body_text = " ".join([p["text"] for p in html_body_paras])
    html_footnote_text = " ".join([p["text"] for p in html_footnote_paras])

    print(f"\n{'-' * 120}\n")
    print("CONCATENATED BODY TEXT COMPARISON:")
    print("-" * 120)
    print("PDF body text (first 500 chars):")
    print(pdf_body_text[:500])
    print("\nHTML body text (first 500 chars):")
    print(html_body_text[:500])

    print(f"\n{'-' * 120}\n")
    print("BODY TEXT STATISTICS:")
    print(f"  PDF extracted:  {len(pdf_body_text):,} chars from {len(pdf_body_lines)} lines")
    print(f"  HTML expected:  {len(html_body_text):,} chars from {len(html_body_paras)} paragraphs")
    print(
        f"  Coverage:       {100 * len(pdf_body_text) / len(html_body_text) if html_body_text else 0:.1f}%"
    )

    print(f"\n{'-' * 120}\n")
    print("FOOTNOTE TEXT STATISTICS:")
    print(
        f"  PDF extracted:  {len(pdf_footnote_text):,} chars from {len(pdf_footnote_lines)} lines"
    )
    print(
        f"  HTML expected:  {len(html_footnote_text):,} chars from {len(html_footnote_paras)} paragraphs"
    )
    if html_footnote_text:
        print(f"  Coverage:       {100 * len(pdf_footnote_text) / len(html_footnote_text):.1f}%")
    else:
        print("  Coverage:       N/A (no footnotes)")

    # Analyze what's in PDF but not in HTML (potential misclassifications)
    pdf_body_words = set(pdf_body_text.lower().split())
    html_body_words = set(html_body_text.lower().split())
    pdf_only_words = pdf_body_words - html_body_words
    html_only_words = html_body_words - pdf_body_words

    print(f"\n{'-' * 120}\n")
    print("WORD SET ANALYSIS (body text):")
    print(f"  Unique words in PDF body:  {len(pdf_body_words):,}")
    print(f"  Unique words in HTML body: {len(html_body_words):,}")
    print(f"  Words only in PDF (potential footnotes mislabeled as body): {len(pdf_only_words):,}")
    print(f"  Words only in HTML (missing from PDF): {len(html_only_words):,}")

    if pdf_only_words:
        sample = list(pdf_only_words)[:20]
        print(f"  Sample PDF-only words: {', '.join(sorted(sample)[:15])}")


def main():
    extraction_dir = Path("results/ocr_pipeline_evaluation/extractions")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")

    # Show examples from different order penalty categories
    examples = [
        ("california_law_review_amazon-trademark", "HIGH order penalty (83%)"),
        ("harvard_law_review_unwarranted_warrants", "LOW order penalty (18%)"),
        ("wisconsin_law_review_marriage_equality_comes_to_wisconsin", "MEDIUM order penalty (41%)"),
    ]

    for pdf_base, description in examples:
        extraction_path = extraction_dir / f"{pdf_base}_baseline_extraction.json"
        gt_path = gt_dir / f"{pdf_base}_ground_truth.json"

        if extraction_path.exists() and gt_path.exists():
            print(f"\n\n{'#' * 120}")
            print(f"# EXAMPLE: {description}")
            print(f"{'#' * 120}")
            show_text_comparison(pdf_base, extraction_path, gt_path)


if __name__ == "__main__":
    main()

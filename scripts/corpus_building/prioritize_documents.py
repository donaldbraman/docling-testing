#!/usr/bin/env python3
"""
Analyze and prioritize documents for labeling based on quality criteria.

Criteria:
1. Page count (ideal: 30-50 pages)
2. Ground truth quality (has body_text and footnotes)
3. Text structure (typical law review with front matter, body, footnotes)
"""

import json
from pathlib import Path

import fitz  # PyMuPDF


def analyze_document(pdf_path: Path, gt_path: Path) -> dict:
    """Analyze a single document and return quality metrics."""

    # Get page count
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()

    # Load ground truth
    with open(gt_path) as f:
        gt = json.load(f)

    body_count = len(gt.get("body_text_paragraphs", []))
    footnote_count = len(gt.get("footnotes", []))

    # Calculate quality score
    # Ideal: 30-50 pages, >50 body paragraphs, >20 footnotes
    page_score = 100 if 30 <= page_count <= 50 else max(0, 100 - abs(page_count - 40) * 5)
    body_score = min(100, body_count * 2)  # 50+ paragraphs = 100 points
    footnote_score = min(100, footnote_count * 5)  # 20+ footnotes = 100 points

    # Weighted average
    quality_score = page_score * 0.3 + body_score * 0.5 + footnote_score * 0.2

    return {
        "name": pdf_path.stem,
        "pages": page_count,
        "body_paragraphs": body_count,
        "footnotes": footnote_count,
        "quality_score": round(quality_score, 1),
    }


def main():
    pdf_dir = Path("data/v3_data/raw_pdf")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")

    documents = []

    print("Analyzing documents...")
    print("=" * 80)

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        gt_path = gt_dir / f"{pdf_path.stem}_ground_truth.json"

        if not gt_path.exists():
            continue

        try:
            doc_info = analyze_document(pdf_path, gt_path)
            documents.append(doc_info)
        except Exception as e:
            print(f"Error analyzing {pdf_path.stem}: {e}")

    # Sort by quality score
    documents.sort(key=lambda x: x["quality_score"], reverse=True)

    print(f"\nAnalyzed {len(documents)} documents with ground truth")
    print("\n" + "=" * 80)
    print("PRIORITIZED DOCUMENT LIST")
    print("=" * 80)
    print(f"{'Rank':<5} {'Name':<60} {'Pages':<7} {'Body':<7} {'Ftnts':<7} {'Score':<7}")
    print("-" * 80)

    for i, doc in enumerate(documents[:30], 1):  # Top 30
        print(
            f"{i:<5} {doc['name']:<60} {doc['pages']:<7} "
            f"{doc['body_paragraphs']:<7} {doc['footnotes']:<7} {doc['quality_score']:<7.1f}"
        )

    # Show bottom 10 for reference
    print("\n" + "=" * 80)
    print("LOWEST PRIORITY (for reference)")
    print("=" * 80)
    for i, doc in enumerate(documents[-10:], len(documents) - 9):
        print(
            f"{i:<5} {doc['name']:<60} {doc['pages']:<7} "
            f"{doc['body_paragraphs']:<7} {doc['footnotes']:<7} {doc['quality_score']:<7.1f}"
        )

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print(f"\nStart with: {documents[0]['name']}")
    print(f"  Pages: {documents[0]['pages']}")
    print(f"  Body paragraphs: {documents[0]['body_paragraphs']}")
    print(f"  Footnotes: {documents[0]['footnotes']}")
    print(f"  Quality score: {documents[0]['quality_score']}")


if __name__ == "__main__":
    main()

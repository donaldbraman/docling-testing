#!/usr/bin/env python3
"""
Quick inspection tool for article analysis.

Provides comprehensive stats about an article's label disagreements,
Docling extraction, and HTML ground truth.

Usage:
    python inspect_article.py <basename>

Author: Claude Code
Date: 2025-01-19
"""

import json
import sys
from pathlib import Path


def inspect_article(basename: str):
    """Display comprehensive stats for an article."""

    # Load disagreement data
    disagree_file = Path("data/v3_data/label_disagreements.json")
    with open(disagree_file) as f:
        disagree_data = json.load(f)

    # Load Docling extraction
    docling_file = Path(f"data/v3_data/docling_extraction/{basename}.json")
    if not docling_file.exists():
        print(f"❌ Docling extraction not found: {docling_file}")
        return

    with open(docling_file) as f:
        docling_data = json.load(f)

    # Load HTML ground truth
    html_file = Path(f"data/v3_data/processed_html/{basename}.json")
    if not html_file.exists():
        print(f"❌ HTML ground truth not found: {html_file}")
        return

    with open(html_file) as f:
        html_data = json.load(f)

    # Find article stats
    article_stats = next(
        (a for a in disagree_data["article_stats"] if a["basename"] == basename), None
    )

    if not article_stats:
        print(f"❌ No disagreement data found for {basename}")
        return

    # Print report
    print("=" * 80)
    print(f"ARTICLE INSPECTION: {basename}")
    print("=" * 80)
    print()

    # Disagreement summary
    print("LABEL DISAGREEMENTS:")
    print(f"  Total corrections: {article_stats['total_corrections']}")
    print(f"  fn → body (gaining): {article_stats['fn_to_body']}")
    print(f"  body → fn (contamination): {article_stats['body_to_fn']}")
    print()

    # Docling stats
    texts = [t for t in docling_data.get("texts", []) if t.get("content_layer") != "furniture"]

    print("DOCLING EXTRACTION:")
    print(f"  Total text items: {len(texts)}")

    # Label distribution
    labels = {}
    for item in texts:
        label = item.get("label", "unknown")
        labels[label] = labels.get(label, 0) + 1

    print("  Label distribution:")
    for label, count in sorted(labels.items(), key=lambda x: -x[1]):
        print(f"    {label}: {count}")

    # Page distribution
    pages = set()
    for item in texts:
        prov = item.get("prov", [])
        if prov:
            pages.add(prov[0].get("page_no", 0))

    print(f"  Pages with content: {len(pages)}")
    print()

    # HTML stats
    paras = html_data.get("paragraphs", [])
    body_paras = [p for p in paras if p["label"] == "body-text"]
    footnote_paras = [p for p in paras if p["label"] == "footnote-text"]

    print("HTML GROUND TRUTH:")
    print(f"  Total paragraphs: {len(paras)}")
    print(f"  Body paragraphs: {len(body_paras)}")
    print(f"  Footnote paragraphs: {len(footnote_paras)}")
    print(f"  Total words: {html_data.get('stats', {}).get('total_words', 0):,}")
    print()

    # Example corrections
    examples = [
        e for e in disagree_data["examples"] if e.get("page_no") or True
    ]  # Filter by basename if available

    # Get examples for this article by matching text patterns
    article_examples = []
    for ex in examples:
        pdf_text = ex.get("pdf_text", "")
        # Check if this example's text appears in this article's Docling extraction
        for item in texts:
            if pdf_text[:100] in item.get("text", "")[:100]:
                article_examples.append(ex)
                break

    if article_examples:
        print("EXAMPLE CORRECTIONS (first 5):")
        for i, ex in enumerate(article_examples[:5], 1):
            print(f"  {i}. Type: {ex['type']}")
            print(f"     Original: {ex['pdf_original_label']}")
            print(f"     Corrected: {ex['pdf_corrected_label']}")
            print(f"     Confidence: {ex['match_confidence']:.1f}%")
            print(f"     Text: {ex['pdf_text'][:100]}...")
            print()

    # Diagnosis
    print("DIAGNOSIS:")
    if article_stats["total_corrections"] == 0:
        print("  ✅ Perfect alignment - no corrections needed")
    elif article_stats["total_corrections"] < 10:
        print("  ✅ Minimal disagreements - likely random variation")
    elif article_stats["total_corrections"] < 50:
        print("  ⚠️  Moderate disagreements - investigate patterns")
    else:
        print("  🔴 High disagreements - systematic issues likely")

    if article_stats["fn_to_body"] > article_stats["body_to_fn"]:
        print("  ⚠️  More fn→body than body→fn - check HTML for inline footnotes")

    if article_stats["body_to_fn"] > 100:
        print("  🔴 Many footnotes mislabeled as body - Docling missing footnote patterns")

    print()


def main():
    if len(sys.argv) != 2:
        print("Usage: python inspect_article.py <basename>")
        sys.exit(1)

    basename = sys.argv[1]
    inspect_article(basename)


if __name__ == "__main__":
    main()

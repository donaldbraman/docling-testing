#!/usr/bin/env python3
"""
Validate Docling's automatic labels against HTML ground truth.

This script compares Docling PDF extraction labels with our curated HTML labels
to evaluate whether we can trust Docling's automatic classification or need
to implement sequential fuzzy matching.

Key questions:
1. How accurate is Docling's footnote detection?
2. How many body_text paragraphs does Docling correctly identify?
3. What false positives/negatives do we see?

Author: Claude Code
Date: 2025-01-18
"""

import json
from pathlib import Path
from typing import Any

try:
    from rapidfuzz import fuzz
except ImportError:
    print("ERROR: RapidFuzz not installed. Install with: uv pip install rapidfuzz")
    exit(1)


def load_docling_extraction(json_file: Path) -> dict[str, list[dict[str, Any]]]:
    """
    Load Docling extraction and organize by label.

    Args:
        json_file: Path to Docling extraction JSON

    Returns:
        Dict mapping label -> list of text items
    """
    with open(json_file) as f:
        data = json.load(f)

    texts = data.get("texts", [])

    # Organize by label, filtering out furniture
    labeled_texts = {}
    for item in texts:
        label = item.get("label", "unknown")
        content_layer = item.get("content_layer", "")

        # Skip furniture (page headers, etc.)
        if content_layer == "furniture":
            continue

        if label not in labeled_texts:
            labeled_texts[label] = []

        labeled_texts[label].append(
            {
                "text": item.get("text", ""),
                "label": label,
                "page_no": item.get("prov", [{}])[0].get("page_no") if item.get("prov") else None,
            }
        )

    return labeled_texts


def load_html_ground_truth(json_file: Path) -> dict[str, list[str]]:
    """
    Load HTML ground truth.

    Args:
        json_file: Path to processed HTML JSON

    Returns:
        Dict with 'body_text' and 'footnote' lists
    """
    with open(json_file) as f:
        data = json.load(f)

    ground_truth = {
        "body_text": [],
        "footnote": [],
    }

    for para in data.get("paragraphs", []):
        label = para["label"]
        text = para["text"]

        if label == "body-text":
            ground_truth["body_text"].append(text)
        elif label == "footnote-text":
            ground_truth["footnote"].append(text)

    return ground_truth


def fuzzy_match_texts(
    docling_texts: list[str], html_texts: list[str], threshold: int = 80
) -> dict[str, Any]:
    """
    Match Docling texts to HTML ground truth using fuzzy matching.

    Args:
        docling_texts: List of texts from Docling
        html_texts: List of ground truth texts from HTML
        threshold: Minimum similarity score (0-100)

    Returns:
        Dict with match statistics
    """
    matches = 0
    unmatched_docling = []
    matched_html_indices = set()

    for docling_text in docling_texts:
        best_score = 0
        best_idx = -1

        # Search for best match in HTML
        for idx, html_text in enumerate(html_texts):
            score = fuzz.partial_ratio(docling_text, html_text)
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_score >= threshold:
            matches += 1
            matched_html_indices.add(best_idx)
        else:
            unmatched_docling.append((docling_text[:100], best_score))

    unmatched_html_count = len(html_texts) - len(matched_html_indices)

    return {
        "matches": matches,
        "docling_total": len(docling_texts),
        "html_total": len(html_texts),
        "unmatched_docling": unmatched_docling,
        "unmatched_html_count": unmatched_html_count,
        "precision": matches / len(docling_texts) if docling_texts else 0,
        "recall": matches / len(html_texts) if html_texts else 0,
    }


def validate_article(basename: str):
    """
    Validate Docling labels for a single article.

    Args:
        basename: Article basename
    """
    print(f"\n{'=' * 80}")
    print(f"Validating: {basename}")
    print(f"{'=' * 80}")

    # Load files
    docling_file = Path(f"data/v3_data/docling_extraction/{basename}.json")
    html_file = Path(f"data/v3_data/processed_html/{basename}.json")

    if not docling_file.exists():
        print(f"❌ Docling extraction not found: {docling_file}")
        return

    if not html_file.exists():
        print(f"❌ HTML ground truth not found: {html_file}")
        return

    # Load data
    docling_texts = load_docling_extraction(docling_file)
    html_ground_truth = load_html_ground_truth(html_file)

    print("\n📊 Docling extraction:")
    for label, items in sorted(docling_texts.items()):
        print(f"  {label:20s}: {len(items):3d} items")

    print("\n📚 HTML ground truth:")
    print(f"  body_text           : {len(html_ground_truth['body_text']):3d} paragraphs")
    print(f"  footnote            : {len(html_ground_truth['footnote']):3d} paragraphs")

    # Validate footnotes
    print("\n🔍 Validating Docling 'footnote' labels...")
    if "footnote" in docling_texts:
        docling_footnotes = [item["text"] for item in docling_texts["footnote"]]
        html_footnotes = html_ground_truth["footnote"]

        fn_stats = fuzzy_match_texts(docling_footnotes, html_footnotes, threshold=80)

        print(f"  Docling footnotes: {fn_stats['docling_total']}")
        print(f"  HTML footnotes: {fn_stats['html_total']}")
        print(f"  Matched: {fn_stats['matches']}")
        print(f"  Precision: {fn_stats['precision']:.1%} (of Docling footnotes that match HTML)")
        print(f"  Recall: {fn_stats['recall']:.1%} (of HTML footnotes found by Docling)")

        if fn_stats["unmatched_docling"]:
            print(f"\n  ⚠️  Unmatched Docling footnotes ({len(fn_stats['unmatched_docling'])}):")
            for text, score in fn_stats["unmatched_docling"][:3]:
                print(f"    - {text}... (best score: {score})")

        if fn_stats["unmatched_html_count"] > 0:
            print(f"\n  ⚠️  HTML footnotes not found by Docling: {fn_stats['unmatched_html_count']}")

    else:
        print("  ❌ No footnotes found by Docling!")

    # Validate body text
    print("\n🔍 Validating Docling 'text' labels...")
    if "text" in docling_texts:
        docling_body = [item["text"] for item in docling_texts["text"]]
        html_body = html_ground_truth["body_text"]

        body_stats = fuzzy_match_texts(docling_body, html_body, threshold=80)

        print(f"  Docling 'text' items: {body_stats['docling_total']}")
        print(f"  HTML body paragraphs: {body_stats['html_total']}")
        print(f"  Matched: {body_stats['matches']}")
        print(
            f"  Precision: {body_stats['precision']:.1%} (of Docling text items that match HTML body)"
        )
        print(f"  Recall: {body_stats['recall']:.1%} (of HTML body paragraphs found by Docling)")

        if body_stats["unmatched_docling"]:
            print(f"\n  ⚠️  Unmatched Docling text items ({len(body_stats['unmatched_docling'])}):")
            for text, score in body_stats["unmatched_docling"][:3]:
                print(f"    - {text}... (best score: {score})")

        if body_stats["unmatched_html_count"] > 0:
            print(
                f"\n  ⚠️  HTML body paragraphs not found by Docling: {body_stats['unmatched_html_count']}"
            )

    else:
        print("  ❌ No 'text' items found by Docling!")

    # Overall assessment
    print("\n📋 Overall assessment:")
    if "footnote" in docling_texts and "text" in docling_texts:
        fn_stats = fuzzy_match_texts(
            [item["text"] for item in docling_texts["footnote"]],
            html_ground_truth["footnote"],
            threshold=80,
        )
        body_stats = fuzzy_match_texts(
            [item["text"] for item in docling_texts["text"]],
            html_ground_truth["body_text"],
            threshold=80,
        )

        avg_precision = (fn_stats["precision"] + body_stats["precision"]) / 2
        avg_recall = (fn_stats["recall"] + body_stats["recall"]) / 2

        print(f"  Average precision: {avg_precision:.1%}")
        print(f"  Average recall: {avg_recall:.1%}")

        if avg_precision >= 0.95 and avg_recall >= 0.95:
            print("  ✅ Docling labels are highly accurate - may not need fuzzy matching!")
        elif avg_precision >= 0.85 and avg_recall >= 0.85:
            print("  ⚠️  Docling labels are good but could benefit from fuzzy matching")
        else:
            print("  ❌ Docling labels need significant correction via fuzzy matching")


def main():
    """Validate Docling labels for the first extracted article."""
    extraction_dir = Path("data/v3_data/docling_extraction")

    # Get first JSON file
    json_files = sorted(extraction_dir.glob("*.json"))
    if not json_files:
        print("❌ No extraction files found")
        return

    # Extract basename from first file
    basename = json_files[0].stem

    # Validate
    validate_article(basename)


if __name__ == "__main__":
    main()

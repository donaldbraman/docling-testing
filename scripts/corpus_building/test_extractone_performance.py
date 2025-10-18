#!/usr/bin/env python3
"""
Benchmark: Manual loop vs RapidFuzz process.extractOne

Tests performance difference between:
1. Manual iteration through all paragraphs (current approach)
2. Using RapidFuzz's process.extractOne (optimized C++ implementation)
"""

import json
import time
from pathlib import Path

from rapidfuzz import fuzz, process, utils


def manual_find_best_match(pdf_text: str, html_paragraphs: list[str], threshold: int = 70):
    """Current approach: Manual iteration."""
    best_score = 0
    best_idx = -1
    best_text = ""

    for idx, html_text in enumerate(html_paragraphs):
        score = fuzz.partial_ratio(pdf_text, html_text, processor=utils.default_process)
        if score > best_score:
            best_score = score
            best_idx = idx
            best_text = html_text

    if best_score >= threshold:
        return best_idx, best_score, best_text
    else:
        return -1, best_score, ""


def extractone_find_best_match(pdf_text: str, html_paragraphs: list[str], threshold: int = 70):
    """Optimized approach: Use process.extractOne."""
    result = process.extractOne(
        pdf_text,
        html_paragraphs,
        scorer=fuzz.partial_ratio,
        processor=utils.default_process,
        score_cutoff=threshold,
    )

    if result:
        best_text, best_score, best_idx = result
        return best_idx, best_score, best_text
    else:
        # If no match above threshold, find best score anyway
        result = process.extractOne(
            pdf_text,
            html_paragraphs,
            scorer=fuzz.partial_ratio,
            processor=utils.default_process,
            score_cutoff=0,  # Get best match even if below threshold
        )
        if result:
            best_text, best_score, best_idx = result
            return -1, best_score, ""
        else:
            return -1, 0, ""


def benchmark_article(basename: str):
    """Benchmark both approaches on a single article."""
    # Load data
    docling_file = Path(f"data/v3_data/docling_extraction/{basename}.json")
    html_file = Path(f"data/v3_data/processed_html/{basename}.json")

    if not docling_file.exists() or not html_file.exists():
        print(f"⚠️  Skipping {basename}: missing files")
        return None

    # Load PDF texts
    with open(docling_file) as f:
        data = json.load(f)
    pdf_texts = [
        item.get("text", "")
        for item in data.get("texts", [])
        if item.get("content_layer") != "furniture"
    ]

    # Load HTML paragraphs
    with open(html_file) as f:
        data = json.load(f)
    body_paras = [p["text"] for p in data.get("paragraphs", []) if p["label"] == "body-text"]

    print(f"\nBenchmarking: {basename}")
    print(f"  PDF items: {len(pdf_texts)}")
    print(f"  HTML paragraphs: {len(body_paras)}")
    print(f"  Total comparisons: {len(pdf_texts) * len(body_paras):,}")

    # Benchmark manual approach
    start_time = time.time()
    for pdf_text in pdf_texts[:100]:  # Test first 100 items
        manual_find_best_match(pdf_text, body_paras)
    manual_time = time.time() - start_time

    # Benchmark extractOne approach
    start_time = time.time()
    for pdf_text in pdf_texts[:100]:  # Test first 100 items
        extractone_find_best_match(pdf_text, body_paras)
    extractone_time = time.time() - start_time

    # Calculate speedup
    speedup = manual_time / extractone_time if extractone_time > 0 else 0

    print(f"  Manual approach:     {manual_time:.2f}s")
    print(f"  extractOne approach: {extractone_time:.2f}s")
    print(f"  Speedup:             {speedup:.2f}x")

    return {
        "basename": basename,
        "pdf_items": len(pdf_texts),
        "html_paras": len(body_paras),
        "manual_time": manual_time,
        "extractone_time": extractone_time,
        "speedup": speedup,
    }


def main():
    """Run benchmarks on sample articles."""
    print("=" * 80)
    print("RapidFuzz process.extractOne Performance Benchmark")
    print("=" * 80)

    # Test on articles of different sizes
    test_articles = [
        "bu_law_review_law_and_culture",  # Small (150 items)
        "bu_law_review_nil_compliance",  # Medium (258 items)
        "california_law_review_affirmative-asylum",  # Large (851 items)
        "california_law_review_amazon-trademark",  # Very large (1261 items)
    ]

    results = []
    for basename in test_articles:
        result = benchmark_article(basename)
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    avg_speedup = sum(r["speedup"] for r in results) / len(results) if results else 0
    print(f"Average speedup: {avg_speedup:.2f}x")
    print(
        f"\nRecommendation: {'Use process.extractOne' if avg_speedup > 1.2 else 'Keep manual approach'}"
    )


if __name__ == "__main__":
    main()

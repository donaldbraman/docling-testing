#!/usr/bin/env python3
"""
Two-Pass Needleman-Wunsch Sequence Alignment

Sequential alignment approach: First align PDF to body, then remaining to footnotes.

Algorithm:
- Pass 1: Needleman-Wunsch alignment between PDF and body_html
- Pass 2: Needleman-Wunsch alignment between remaining PDF and footnote_html
- Pass 3: Assign unmatched lines to original labels
- Complexity: O(n×m) + O(n×k) ≈ 270K operations for typical inputs
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from parse_extraction import ExtractedItem
from prepare_matching_data import HTMLLine, normalize_text


@dataclass
class TwoPassMatch:
    """Result of two-pass alignment for a single PDF line."""

    extraction_item: ExtractedItem
    matched_html: HTMLLine | None
    similarity_score: float  # 0.0 to 1.0
    corrected_label: str | None  # "body-text", "footnote-text", or None
    assignment: str  # "body", "footnote", or "original"


def calculate_similarity(pdf_text: str, html_text: str) -> float:
    """
    Calculate text similarity using rapidfuzz or difflib.

    Args:
        pdf_text: Normalized PDF line text
        html_text: Normalized HTML text

    Returns:
        Similarity score between 0.0 and 1.0
    """
    try:
        from rapidfuzz import fuzz

        return fuzz.partial_ratio(pdf_text, html_text) / 100.0
    except ImportError:
        from difflib import SequenceMatcher

        return SequenceMatcher(None, pdf_text, html_text).ratio()


def needleman_wunsch(
    pdf_items: list[ExtractedItem],
    html_lines: list[HTMLLine],
    threshold: float = 0.75,
    gap_penalty: float = 0.0,
) -> dict[int, tuple[HTMLLine, float]]:
    """
    Standard Needleman-Wunsch sequence alignment.

    Finds optimal global alignment between two sequences.

    Args:
        pdf_items: List of PDF extraction items
        html_lines: List of HTML lines to align to
        threshold: Minimum similarity to consider a match
        gap_penalty: Penalty for gaps in alignment (default 0)

    Returns:
        Dictionary mapping PDF index → (matched HTML line, similarity score)
        Only includes matches above threshold
    """
    n = len(pdf_items)
    m = len(html_lines)

    # Precompute similarity matrix
    sim = [[0.0] * m for _ in range(n)]
    for i, item in enumerate(pdf_items):
        query = normalize_text(item.text)
        if len(query) < 10:
            continue
        for j, html_line in enumerate(html_lines):
            target = normalize_text(html_line.text)
            sim[i][j] = calculate_similarity(query, target)

    # Initialize DP table
    # dp[i][j] = best alignment score for first i PDF items and j HTML items
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]

    # Backpointer for reconstruction
    # backpointer[i][j] = (prev_i, prev_j, action)
    backpointer = [[None] * (m + 1) for _ in range(n + 1)]

    # Initialize first row and column (gaps at start)
    for i in range(1, n + 1):
        dp[i][0] = i * gap_penalty
        backpointer[i][0] = (i - 1, 0, "pdf_gap")

    for j in range(1, m + 1):
        dp[0][j] = j * gap_penalty
        backpointer[0][j] = (0, j - 1, "html_gap")

    # Fill DP table
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            # Option 1: Match/substitute
            match_score = dp[i - 1][j - 1] + sim[i - 1][j - 1]

            # Option 2: Gap in HTML (skip HTML item)
            html_gap_score = dp[i][j - 1] + gap_penalty

            # Option 3: Gap in PDF (skip PDF item)
            pdf_gap_score = dp[i - 1][j] + gap_penalty

            # Choose best option
            best_score = max(match_score, html_gap_score, pdf_gap_score)
            dp[i][j] = best_score

            if best_score == match_score:
                backpointer[i][j] = (i - 1, j - 1, "match")
            elif best_score == html_gap_score:
                backpointer[i][j] = (i, j - 1, "html_gap")
            else:
                backpointer[i][j] = (i - 1, j, "pdf_gap")

    # Reconstruct alignment from backpointers
    matches = {}
    i, j = n, m
    while i > 0 or j > 0:
        if backpointer[i][j] is None:
            break

        prev_i, prev_j, action = backpointer[i][j]

        if action == "match":
            # PDF item i-1 matched to HTML item j-1
            score = sim[i - 1][j - 1]
            if score >= threshold:
                matches[i - 1] = (html_lines[j - 1], score)

        i, j = prev_i, prev_j

    return matches


def two_pass_alignment(
    items: list[ExtractedItem],
    body_html: list[HTMLLine],
    footnote_html: list[HTMLLine],
    threshold: float = 0.75,
) -> list[TwoPassMatch]:
    """
    Two-pass sequence alignment: body first, then footnotes.

    Pass 1: Align all PDF lines to body_html
    Pass 2: Align remaining PDF lines to footnote_html
    Pass 3: Keep original labels for unmatched lines

    Args:
        items: List of extraction items (PDF lines in reading order)
        body_html: HTML body-text paragraphs (in order)
        footnote_html: HTML footnote-text paragraphs (in order)
        threshold: Minimum similarity score to consider a match

    Returns:
        List of TwoPassMatch results
    """
    # Pass 1: Align PDF → body_html
    body_matches = needleman_wunsch(items, body_html, threshold)

    # Track which PDF lines were matched in Pass 1
    matched_indices = set(body_matches.keys())

    # Pass 2: Align remaining PDF → footnote_html
    remaining_items = [item for i, item in enumerate(items) if i not in matched_indices]
    remaining_indices = [i for i in range(len(items)) if i not in matched_indices]

    footnote_matches_raw = needleman_wunsch(remaining_items, footnote_html, threshold)

    # Map back to original indices
    footnote_matches = {}
    for relative_idx, (html_line, score) in footnote_matches_raw.items():
        original_idx = remaining_indices[relative_idx]
        footnote_matches[original_idx] = (html_line, score)

    # Build results for all items
    results = []
    for i, item in enumerate(items):
        if i in body_matches:
            html_line, score = body_matches[i]
            results.append(
                TwoPassMatch(
                    extraction_item=item,
                    matched_html=html_line,
                    similarity_score=score,
                    corrected_label="body-text",
                    assignment="body",
                )
            )
        elif i in footnote_matches:
            html_line, score = footnote_matches[i]
            results.append(
                TwoPassMatch(
                    extraction_item=item,
                    matched_html=html_line,
                    similarity_score=score,
                    corrected_label="footnote-text",
                    assignment="footnote",
                )
            )
        else:
            # Keep original label
            results.append(
                TwoPassMatch(
                    extraction_item=item,
                    matched_html=None,
                    similarity_score=0.0,
                    corrected_label=None,
                    assignment="original",
                )
            )

    return results


def main():
    """Test two-pass alignment on harvard_law_review."""
    from parse_extraction import load_extraction
    from prepare_matching_data import load_html_ground_truth

    # Load data
    ext_file = Path(
        "results/ocr_pipeline_evaluation/extractions/harvard_law_review_unwarranted_warrants_baseline_extraction.json"
    )
    items = load_extraction(ext_file)

    body_html, footnote_html = load_html_ground_truth("harvard_law_review_unwarranted_warrants")

    print(f"Running two-pass alignment on {len(items)} PDF lines...")
    print(f"Body HTML: {len(body_html)} items")
    print(f"Footnote HTML: {len(footnote_html)} items")

    # Run two-pass alignment
    matches = two_pass_alignment(items, body_html, footnote_html, threshold=0.75)

    # Analyze results
    body_matches = [m for m in matches if m.assignment == "body"]
    footnote_matches = [m for m in matches if m.assignment == "footnote"]
    original_matches = [m for m in matches if m.assignment == "original"]

    print("\nResults:")
    print(f"  Body assignments: {len(body_matches)} ({len(body_matches) / len(items) * 100:.1f}%)")
    print(
        f"  Footnote assignments: {len(footnote_matches)} ({len(footnote_matches) / len(items) * 100:.1f}%)"
    )
    print(
        f"  Original labels: {len(original_matches)} ({len(original_matches) / len(items) * 100:.1f}%)"
    )

    # HTML utilization
    body_html_used = len({m.matched_html for m in body_matches if m.matched_html})
    footnote_html_used = len({m.matched_html for m in footnote_matches if m.matched_html})

    print("\nHTML Utilization:")
    print(f"  Body HTML used: {body_html_used}/{len(body_html)}")
    print(f"  Footnote HTML used: {footnote_html_used}/{len(footnote_html)}")

    # Show examples
    print("\nSample body matches:")
    for i, match in enumerate(body_matches[:3], 1):
        print(f"\n[{i}] Similarity: {match.similarity_score:.3f}")
        print(f"    PDF: {match.extraction_item.text[:70]}...")
        if match.matched_html:
            print(f"    HTML: {match.matched_html.text[:70]}...")

    print("\nSample footnote matches:")
    for i, match in enumerate(footnote_matches[:3], 1):
        print(f"\n[{i}] Similarity: {match.similarity_score:.3f}")
        print(f"    PDF: {match.extraction_item.text[:70]}...")
        if match.matched_html:
            print(f"    HTML: {match.matched_html.text[:70]}...")

    return 0


if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
"""
Dynamic Programming Two-Sequence Alignment

Globally optimal partition of PDF lines into body and footnote sequences.

Algorithm:
- State: (pdf_idx, body_idx, footnote_idx)
- Transitions: Assign line to body, footnote, or keep original label
- Objective: Maximize total similarity score
- Complexity: O(n × m × k) where n=pdf lines, m=body items, k=footnote items
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
class DPMatch:
    """Result of DP alignment for a single PDF line."""

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


def dp_two_sequence_alignment(
    items: list[ExtractedItem],
    body_html: list[HTMLLine],
    footnote_html: list[HTMLLine],
    threshold: float = 0.75,
    gap_penalty: float = -0.2,
    weak_match_penalty: float = -0.1,
) -> list[DPMatch]:
    """
    Globally optimal two-sequence alignment using 3D dynamic programming.

    Finds the best partition of PDF lines into body and footnote sequences
    by maximizing total similarity scores.

    Args:
        items: List of extraction items (PDF lines in reading order)
        body_html: HTML body-text paragraphs (in order)
        footnote_html: HTML footnote-text paragraphs (in order)
        threshold: Minimum similarity score to consider a match

    Returns:
        List of DPMatch results with optimal assignments
    """
    n = len(items)
    m = len(body_html)
    k = len(footnote_html)

    # Precompute all similarity scores (optimization)
    # sim_body[i][j] = similarity between items[i] and body_html[j]
    # sim_footnote[i][j] = similarity between items[i] and footnote_html[j]
    sim_body = [[0.0] * m for _ in range(n)]
    sim_footnote = [[0.0] * k for _ in range(n)]

    for i, item in enumerate(items):
        query = normalize_text(item.text)
        # Skip very short queries
        if len(query) < 10:
            continue

        for j, html_line in enumerate(body_html):
            target = normalize_text(html_line.text)
            sim_body[i][j] = calculate_similarity(query, target)

        for j, html_line in enumerate(footnote_html):
            target = normalize_text(html_line.text)
            sim_footnote[i][j] = calculate_similarity(query, target)

    # Initialize DP table
    # dp[i][j][k] = best score for first i PDF lines, j body items, k footnote items
    # Use -inf for impossible states, 0.0 for valid states
    NEG_INF = float("-inf")
    dp = [[[NEG_INF] * (k + 1) for _ in range(m + 1)] for _ in range(n + 1)]
    dp[0][0][0] = 0.0  # Base case: no lines processed

    # Backpointer to reconstruct path
    # backpointer[i][j][k] = (prev_i, prev_j, prev_k, action)
    backpointer = [[[None] * (k + 1) for _ in range(m + 1)] for _ in range(n + 1)]

    # Fill DP table
    for i in range(n + 1):
        for j in range(m + 1):
            for l in range(k + 1):  # noqa: E741
                # Skip if current state is unreachable
                if dp[i][j][l] == NEG_INF:
                    continue

                # We're at state (i, j, l) with score dp[i][j][l]
                # Try all three transitions for next PDF line (if not at end)
                if i < n:
                    current_score = dp[i][j][l]

                    # Transition 1: Assign to body sequence
                    # Only if we haven't exhausted body_html
                    if j < m:
                        match_score = sim_body[i][j]
                        if match_score >= threshold:
                            # Good match: reward with similarity score
                            new_score = current_score + match_score
                            if new_score > dp[i + 1][j + 1][l]:
                                dp[i + 1][j + 1][l] = new_score
                                backpointer[i + 1][j + 1][l] = (i, j, l, "body")
                        elif match_score > 0.1:  # Weak match
                            # Below threshold but not completely dissimilar
                            new_score = current_score + match_score + weak_match_penalty
                            if new_score > dp[i + 1][j + 1][l]:
                                dp[i + 1][j + 1][l] = new_score
                                backpointer[i + 1][j + 1][l] = (i, j, l, "body")

                    # Transition 2: Assign to footnote sequence
                    # Only if we haven't exhausted footnote_html
                    if l < k:
                        match_score = sim_footnote[i][l]
                        if match_score >= threshold:
                            # Good match: reward with similarity score
                            new_score = current_score + match_score
                            if new_score > dp[i + 1][j][l + 1]:
                                dp[i + 1][j][l + 1] = new_score
                                backpointer[i + 1][j][l + 1] = (i, j, l, "footnote")
                        elif match_score > 0.1:  # Weak match
                            # Below threshold but not completely dissimilar
                            new_score = current_score + match_score + weak_match_penalty
                            if new_score > dp[i + 1][j][l + 1]:
                                dp[i + 1][j][l + 1] = new_score
                                backpointer[i + 1][j][l + 1] = (i, j, l, "footnote")

                    # Transition 3: Keep original label (no match = gap)
                    # Apply gap penalty to discourage skipping HTML items
                    new_score = current_score + gap_penalty
                    if new_score > dp[i + 1][j][l]:
                        dp[i + 1][j][l] = new_score
                        backpointer[i + 1][j][l] = (i, j, l, "original")

    # Find best final state (processed all n lines, any j, l)
    best_score = NEG_INF
    best_j = 0
    best_l = 0
    for j in range(m + 1):
        for l in range(k + 1):
            if dp[n][j][l] > best_score:
                best_score = dp[n][j][l]
                best_j = j
                best_l = l

    # Reconstruct path from backpointers
    path = []
    i, j, l = n, best_j, best_l
    while i > 0:
        prev_i, prev_j, prev_l, action = backpointer[i][j][l]
        path.append((prev_i, prev_j, prev_l, action))
        i, j, l = prev_i, prev_j, prev_l

    path.reverse()  # Now path[i] = action for items[i]

    # Build results
    results = []
    for i, item in enumerate(items):
        if i < len(path):
            _, j_used, l_used, action = path[i]

            if action == "body":
                matched_html = body_html[j_used]
                similarity = sim_body[i][j_used]
                corrected_label = "body-text"
            elif action == "footnote":
                matched_html = footnote_html[l_used]
                similarity = sim_footnote[i][l_used]
                corrected_label = "footnote-text"
            else:  # original
                matched_html = None
                similarity = 0.0
                corrected_label = None

            results.append(
                DPMatch(
                    extraction_item=item,
                    matched_html=matched_html,
                    similarity_score=similarity,
                    corrected_label=corrected_label,
                    assignment=action,
                )
            )
        else:
            # Shouldn't happen, but handle gracefully
            results.append(
                DPMatch(
                    extraction_item=item,
                    matched_html=None,
                    similarity_score=0.0,
                    corrected_label=None,
                    assignment="original",
                )
            )

    return results


def main():
    """Test DP alignment on harvard_law_review."""
    from parse_extraction import load_extraction
    from prepare_matching_data import load_html_ground_truth

    # Load data
    ext_file = Path(
        "results/ocr_pipeline_evaluation/extractions/harvard_law_review_unwarranted_warrants_baseline_extraction.json"
    )
    items = load_extraction(ext_file)

    body_html, footnote_html = load_html_ground_truth("harvard_law_review_unwarranted_warrants")

    print(f"Running DP alignment on {len(items)} PDF lines...")
    print(f"Body HTML: {len(body_html)} items")
    print(f"Footnote HTML: {len(footnote_html)} items")

    # Run DP alignment
    matches = dp_two_sequence_alignment(items, body_html, footnote_html, threshold=0.75)

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

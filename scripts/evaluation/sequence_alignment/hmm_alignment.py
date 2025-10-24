#!/usr/bin/env python3
"""
Hidden Markov Model with Viterbi Decoding

Probabilistic sequence labeling with spatial priors.

Algorithm:
- States: {body-text, footnote-text}
- Emissions: P(PDF line | state) from HTML similarity
- Transitions: P(state → state) from spatial position
- Inference: Viterbi algorithm finds most likely state sequence
- Complexity: O(n × 2) = ~9K operations for typical inputs
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from parse_extraction import ExtractedItem
from prepare_matching_data import HTMLLine, normalize_text


@dataclass
class HMMMatch:
    """Result of HMM alignment for a single PDF line."""

    extraction_item: ExtractedItem
    matched_html: HTMLLine | None
    similarity_score: float  # 0.0 to 1.0
    corrected_label: str | None  # "body-text", "footnote-text", or None
    assignment: str  # "body", "footnote", or "original"
    state_probability: float  # Viterbi probability


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


def calculate_emission_probability(
    item: ExtractedItem,
    html_lines: list[HTMLLine],
    threshold: float = 0.75,
) -> tuple[float, HTMLLine | None]:
    """
    Calculate emission probability P(observation | state).

    Uses maximum similarity to any HTML line in the given state.

    Args:
        item: PDF extraction item
        html_lines: HTML lines for this state
        threshold: Minimum similarity for valid match

    Returns:
        Tuple of (probability, best matched HTML line or None)
    """
    query = normalize_text(item.text)

    # Skip very short queries
    if len(query) < 10:
        return (0.01, None)  # Small probability, no match

    best_score = 0.0
    best_html = None

    for html_line in html_lines:
        target = normalize_text(html_line.text)
        score = calculate_similarity(query, target)

        if score > best_score:
            best_score = score
            best_html = html_line

    # Convert similarity to probability
    # High similarity → high probability
    # Below threshold → low probability
    if best_score >= threshold:
        probability = best_score
        return (probability, best_html)
    else:
        # Below threshold: give small probability, no match
        probability = best_score * 0.1  # Penalize weak matches
        return (probability, None)


def calculate_transition_probability(
    from_state: str,
    to_state: str,
    page_position: float,
) -> float:
    """
    Calculate transition probability P(to_state | from_state, position).

    Incorporates spatial prior: bottom of page favors footnotes.

    Args:
        from_state: Previous state ("body" or "footnote")
        to_state: Next state ("body" or "footnote")
        page_position: Normalized position on page (0.0 = top, 1.0 = bottom)

    Returns:
        Transition probability
    """
    # Bottom of page (position > 0.75) favors footnotes
    if page_position > 0.75:
        # At bottom of page
        if to_state == "footnote":
            return 0.8  # Likely to be footnote
        else:
            return 0.2  # Less likely to be body
    else:
        # Not at bottom: favor state persistence
        if from_state == to_state:
            return 0.9  # Stay in same state
        else:
            return 0.1  # Transition to other state


def hmm_viterbi_alignment(
    items: list[ExtractedItem],
    body_html: list[HTMLLine],
    footnote_html: list[HTMLLine],
    threshold: float = 0.75,
) -> list[HMMMatch]:
    """
    HMM sequence labeling with Viterbi decoding.

    Finds most likely state sequence using:
    - Emission probabilities from HTML similarity
    - Transition probabilities from spatial position

    Args:
        items: List of extraction items (PDF lines in reading order)
        body_html: HTML body-text paragraphs (in order)
        footnote_html: HTML footnote-text paragraphs (in order)
        threshold: Minimum similarity score to consider a match

    Returns:
        List of HMMMatch results with Viterbi state assignments
    """
    n = len(items)
    states = ["body", "footnote"]
    num_states = len(states)

    # Precompute emission probabilities
    # emissions[i][state] = (probability, matched_html)
    emissions = []
    for item in items:
        body_prob, body_match = calculate_emission_probability(item, body_html, threshold)
        footnote_prob, footnote_match = calculate_emission_probability(
            item, footnote_html, threshold
        )

        emissions.append(
            {
                "body": (body_prob, body_match),
                "footnote": (footnote_prob, footnote_match),
            }
        )

    # Initialize Viterbi tables (in log space to avoid underflow)
    # viterbi[i][state] = max log probability of state sequence ending in state at position i
    viterbi = [[float("-inf")] * num_states for _ in range(n)]

    # backpointer[i][state] = previous state in best path
    backpointer = [[None] * num_states for _ in range(n)]

    # Initial probabilities (assume equal prior)
    initial_prob = 1.0 / num_states
    for s, state in enumerate(states):
        emission_prob, _ = emissions[0][state]
        viterbi[0][s] = math.log(initial_prob) + math.log(emission_prob + 1e-10)

    # Forward pass: fill Viterbi table
    for i in range(1, n):
        # Calculate page position (simple heuristic)
        # bbox is a tuple: (l, t, r, b)
        if items[i].bbox:
            l, t, r, b = items[i].bbox
            page_position = (t + b) / 2.0  # Middle y-coordinate
            # Normalize to [0, 1] assuming page height ~2200 (Docling coordinates)
            page_position = min(1.0, max(0.0, page_position / 2200.0))
        else:
            page_position = 0.5  # Default to middle if no bbox

        for s, to_state in enumerate(states):
            emission_prob, _ = emissions[i][to_state]

            # Find best previous state
            best_prev_score = float("-inf")
            best_prev_state = None

            for s_prev, from_state in enumerate(states):
                transition_prob = calculate_transition_probability(
                    from_state, to_state, page_position
                )

                score = viterbi[i - 1][s_prev] + math.log(transition_prob + 1e-10)

                if score > best_prev_score:
                    best_prev_score = score
                    best_prev_state = s_prev

            # Update Viterbi table
            viterbi[i][s] = best_prev_score + math.log(emission_prob + 1e-10)
            backpointer[i][s] = best_prev_state

    # Backward pass: reconstruct best path
    best_final_state = 0
    best_final_score = viterbi[n - 1][0]
    for s in range(1, num_states):
        if viterbi[n - 1][s] > best_final_score:
            best_final_score = viterbi[n - 1][s]
            best_final_state = s

    # Trace back
    path = [best_final_state]
    for i in range(n - 1, 0, -1):
        path.append(backpointer[i][path[-1]])

    path.reverse()  # Now path[i] = state index for items[i]

    # Build results
    results = []
    for i, item in enumerate(items):
        state_idx = path[i]
        state = states[state_idx]

        emission_prob, matched_html = emissions[i][state]

        if matched_html is not None:
            # Valid match
            corrected_label = "body-text" if state == "body" else "footnote-text"
            # Get actual similarity score (not probability)
            query = normalize_text(item.text)
            target = normalize_text(matched_html.text)
            similarity = calculate_similarity(query, target)
        else:
            # No match (below threshold)
            corrected_label = None
            similarity = 0.0

        results.append(
            HMMMatch(
                extraction_item=item,
                matched_html=matched_html,
                similarity_score=similarity,
                corrected_label=corrected_label,
                assignment=state if matched_html else "original",
                state_probability=math.exp(viterbi[i][state_idx]),
            )
        )

    return results


def main():
    """Test HMM alignment on harvard_law_review."""
    from parse_extraction import load_extraction
    from prepare_matching_data import load_html_ground_truth

    # Load data
    ext_file = Path(
        "results/ocr_pipeline_evaluation/extractions/harvard_law_review_unwarranted_warrants_baseline_extraction.json"
    )
    items = load_extraction(ext_file)

    body_html, footnote_html = load_html_ground_truth("harvard_law_review_unwarranted_warrants")

    print(f"Running HMM Viterbi alignment on {len(items)} PDF lines...")
    print(f"Body HTML: {len(body_html)} items")
    print(f"Footnote HTML: {len(footnote_html)} items")

    # Run HMM alignment
    matches = hmm_viterbi_alignment(items, body_html, footnote_html, threshold=0.75)

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
        print(
            f"\n[{i}] Similarity: {match.similarity_score:.3f}, P(state): {match.state_probability:.3f}"
        )
        print(f"    PDF: {match.extraction_item.text[:70]}...")
        if match.matched_html:
            print(f"    HTML: {match.matched_html.text[:70]}...")

    print("\nSample footnote matches:")
    for i, match in enumerate(footnote_matches[:3], 1):
        print(
            f"\n[{i}] Similarity: {match.similarity_score:.3f}, P(state): {match.state_probability:.3f}"
        )
        print(f"    PDF: {match.extraction_item.text[:70]}...")
        if match.matched_html:
            print(f"    HTML: {match.matched_html.text[:70]}...")

    return 0


if __name__ == "__main__":
    exit(main())

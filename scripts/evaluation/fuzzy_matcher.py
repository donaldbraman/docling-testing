#!/usr/bin/env python3
"""
Fuzzy matching between extraction items and HTML ground truth.

Matches each extraction item to the most similar HTML paragraph using:
- Text similarity (RapidFuzz or difflib)
- No locality optimization yet (Phase 2)
"""

from __future__ import annotations

from dataclasses import dataclass

from parse_extraction import ExtractedItem
from prepare_matching_data import HTMLLine, normalize_text


@dataclass
class FuzzyMatch:
    """Result of fuzzy matching an extraction item to HTML."""

    extraction_item: ExtractedItem
    matched_html: HTMLLine | None
    similarity_score: float  # 0.0 to 1.0
    corrected_label: str | None  # "body-text" or "footnote-text" from HTML


def fuzzy_match_item(
    item: ExtractedItem,
    body_html: list[HTMLLine],
    footnote_html: list[HTMLLine],
    threshold: float = 0.75,
) -> FuzzyMatch:
    """
    Find the best fuzzy match for an extraction item in HTML ground truth.

    Searches both body and footnote collections, returns best match.

    Args:
        item: Extraction item to match
        body_html: List of HTML body-text paragraphs
        footnote_html: List of HTML footnote-text paragraphs
        threshold: Minimum similarity score (0.0-1.0)

    Returns:
        FuzzyMatch with best match or None if no match above threshold
    """
    # Try rapidfuzz first (faster), fall back to difflib
    try:
        from rapidfuzz import fuzz

        use_rapidfuzz = True
    except ImportError:
        from difflib import SequenceMatcher

        use_rapidfuzz = False

    # Normalize extraction text
    query = normalize_text(item.text)

    # Skip very short queries (likely headers/footers)
    if len(query) < 10:
        return FuzzyMatch(
            extraction_item=item, matched_html=None, similarity_score=0.0, corrected_label=None
        )

    best_match = None
    best_score = 0.0
    best_html = None

    # Search body text
    for html_line in body_html:
        target = normalize_text(html_line.text)

        if use_rapidfuzz:
            # Use partial_ratio for substring matching (extraction may be fragment of HTML)
            score = fuzz.partial_ratio(query, target) / 100.0
        else:
            # SequenceMatcher for similarity
            score = SequenceMatcher(None, query, target).ratio()

        if score > best_score:
            best_score = score
            best_html = html_line
            best_match = "body"

    # Search footnotes
    for html_line in footnote_html:
        target = normalize_text(html_line.text)

        if use_rapidfuzz:
            score = fuzz.partial_ratio(query, target) / 100.0
        else:
            score = SequenceMatcher(None, query, target).ratio()

        if score > best_score:
            best_score = score
            best_html = html_line
            best_match = "footnote"

    # Check threshold
    if best_score < threshold:
        return FuzzyMatch(
            extraction_item=item,
            matched_html=None,
            similarity_score=best_score,
            corrected_label=None,
        )

    return FuzzyMatch(
        extraction_item=item,
        matched_html=best_html,
        similarity_score=best_score,
        corrected_label=best_html.label if best_html else None,
    )


def fuzzy_match_item_with_locality(
    item: ExtractedItem,
    body_html: list[HTMLLine],
    footnote_html: list[HTMLLine],
    current_body_idx: int,
    current_footnote_idx: int,
    threshold: float = 0.75,
    matched_body_indices: set[int] | None = None,
    matched_footnote_indices: set[int] | None = None,
) -> tuple[FuzzyMatch, int, int]:
    """
    Find best fuzzy match with locality preference.

    Implements proximity-weighted matching to prefer matches near recent position.
    This ensures natural forward flow through HTML and prevents same HTML from
    matching multiple non-adjacent PDF lines.

    Args:
        item: Extraction item to match
        body_html: List of HTML body-text paragraphs
        footnote_html: List of HTML footnote-text paragraphs
        current_body_idx: Current position in body_html (0-indexed)
        current_footnote_idx: Current position in footnote_html (0-indexed)
        threshold: Minimum similarity score (0.0-1.0)
        matched_body_indices: Set of already-matched body HTML indices (for one-to-one)
        matched_footnote_indices: Set of already-matched footnote HTML indices (for one-to-one)

    Returns:
        Tuple of (FuzzyMatch, new_body_idx, new_footnote_idx)
    """
    # Try rapidfuzz first (faster), fall back to difflib
    try:
        from rapidfuzz import fuzz

        use_rapidfuzz = True
    except ImportError:
        from difflib import SequenceMatcher

        use_rapidfuzz = False

    # Normalize extraction text
    query = normalize_text(item.text)

    # Skip very short queries (likely headers/footers)
    if len(query) < 10:
        return (
            FuzzyMatch(
                extraction_item=item, matched_html=None, similarity_score=0.0, corrected_label=None
            ),
            current_body_idx,
            current_footnote_idx,
        )

    best_final_score = 0.0
    best_match_type = None
    best_match_idx = -1
    best_html = None
    best_similarity = 0.0

    # Search body text with proximity weighting
    for idx, html_line in enumerate(body_html):
        # Skip if already matched (one-to-one enforcement)
        if matched_body_indices is not None and idx in matched_body_indices:
            continue

        target = normalize_text(html_line.text)

        if use_rapidfuzz:
            similarity = fuzz.partial_ratio(query, target) / 100.0
        else:
            similarity = SequenceMatcher(None, query, target).ratio()

        # Only consider matches above threshold
        if similarity >= threshold:
            # Use pure similarity (no proximity bonus)
            final_score = similarity

            if final_score > best_final_score:
                best_final_score = final_score
                best_match_type = "body"
                best_match_idx = idx
                best_html = html_line
                best_similarity = similarity

    # Search footnotes with proximity weighting
    for idx, html_line in enumerate(footnote_html):
        # Skip if already matched (one-to-one enforcement)
        if matched_footnote_indices is not None and idx in matched_footnote_indices:
            continue

        target = normalize_text(html_line.text)

        if use_rapidfuzz:
            similarity = fuzz.partial_ratio(query, target) / 100.0
        else:
            similarity = SequenceMatcher(None, query, target).ratio()

        # Only consider matches above threshold
        if similarity >= threshold:
            # Use pure similarity (no proximity bonus)
            final_score = similarity

            if final_score > best_final_score:
                best_final_score = final_score
                best_match_type = "footnote"
                best_match_idx = idx
                best_html = html_line
                best_similarity = similarity

    # No match found above threshold
    if best_match_type is None:
        return (
            FuzzyMatch(
                extraction_item=item,
                matched_html=None,
                similarity_score=0.0,
                corrected_label=None,
            ),
            current_body_idx,
            current_footnote_idx,
        )

    # Update position indices - advance to next position after matched item
    new_body_idx = best_match_idx + 1 if best_match_type == "body" else current_body_idx
    new_footnote_idx = best_match_idx + 1 if best_match_type == "footnote" else current_footnote_idx

    return (
        FuzzyMatch(
            extraction_item=item,
            matched_html=best_html,
            similarity_score=best_similarity,
            corrected_label=best_html.label if best_html else None,
        ),
        new_body_idx,
        new_footnote_idx,
    )


def match_all_lines_with_locality(
    items: list[ExtractedItem],
    body_html: list[HTMLLine],
    footnote_html: list[HTMLLine],
    threshold: float = 0.75,
    enforce_one_to_one: bool = True,
) -> list[FuzzyMatch]:
    """
    Match all items with locality-aware preference (Phase 2).

    Tracks current position in HTML lists and prefers matches near recent position.
    This ensures natural forward flow through HTML and eliminates overlapping boxes.

    Args:
        items: List of extraction items (in reading order)
        body_html: HTML body-text paragraphs
        footnote_html: HTML footnote-text paragraphs
        threshold: Minimum similarity score
        enforce_one_to_one: If True, each HTML item can only be matched once

    Returns:
        List of FuzzyMatch results with locality optimization
    """
    matches = []
    current_body_idx = 0
    current_footnote_idx = 0

    # Track which HTML items have been matched (for one-to-one enforcement)
    matched_body_indices = set() if enforce_one_to_one else None
    matched_footnote_indices = set() if enforce_one_to_one else None

    for item in items:
        match, current_body_idx, current_footnote_idx = fuzzy_match_item_with_locality(
            item,
            body_html,
            footnote_html,
            current_body_idx,
            current_footnote_idx,
            threshold,
            matched_body_indices,
            matched_footnote_indices,
        )
        matches.append(match)

        # Mark HTML item as matched
        if enforce_one_to_one and match.matched_html is not None:
            if match.corrected_label == "body-text":
                # Find index of matched body HTML
                for idx, html in enumerate(body_html):
                    if html.text == match.matched_html.text:
                        matched_body_indices.add(idx)
                        break
            elif match.corrected_label == "footnote-text":
                # Find index of matched footnote HTML
                for idx, html in enumerate(footnote_html):
                    if html.text == match.matched_html.text:
                        matched_footnote_indices.add(idx)
                        break

    return matches


def match_all_items(
    items: list[ExtractedItem],
    body_html: list[HTMLLine],
    footnote_html: list[HTMLLine],
    threshold: float = 0.75,
) -> list[FuzzyMatch]:
    """
    Match all extraction items to HTML ground truth.

    NOTE: This is the basic (Phase 1) implementation without locality optimization.
    For line-level matching with locality awareness, use match_all_lines_with_locality().

    Args:
        items: List of extraction items
        body_html: HTML body-text paragraphs
        footnote_html: HTML footnote-text paragraphs
        threshold: Minimum similarity score

    Returns:
        List of FuzzyMatch results
    """
    matches = []

    for item in items:
        match = fuzzy_match_item(item, body_html, footnote_html, threshold)
        matches.append(match)

    return matches


def main():
    """Test fuzzy matching on harvard_law_review."""
    from pathlib import Path

    from parse_extraction import load_extraction
    from prepare_matching_data import load_html_ground_truth

    # Load data
    ext_file = Path(
        "results/ocr_pipeline_evaluation/extractions/harvard_law_review_unwarranted_warrants_baseline_extraction.json"
    )
    items = load_extraction(ext_file)

    body_html, footnote_html = load_html_ground_truth("harvard_law_review_unwarranted_warrants")

    print(f"Matching {len(items)} extraction items...")

    # Match all items
    matches = match_all_items(items, body_html, footnote_html, threshold=0.75)

    # Analyze results
    matched = [m for m in matches if m.matched_html is not None]
    unmatched = [m for m in matches if m.matched_html is None]

    print("\nResults:")
    print(f"  Matched: {len(matched)}/{len(items)} ({len(matched) / len(items) * 100:.1f}%)")
    print(f"  Unmatched: {len(unmatched)}")

    # Show some examples
    print("\nSample matches:")
    for i, match in enumerate(matched[:5], 1):
        item = match.extraction_item
        print(f"\n[{i}] Original label: {item.label}")
        print(f"    Corrected label: {match.corrected_label}")
        print(f"    Similarity: {match.similarity_score:.3f}")
        print(f"    Extraction: {item.text[:70]}...")
        if match.matched_html:
            print(f"    HTML match: {match.matched_html.text[:70]}...")

    # Label change statistics
    label_changes = {}
    for match in matched:
        if match.extraction_item.label == "TEXT":
            original = "TEXT"
        elif match.extraction_item.label == "FOOTNOTE":
            original = "FOOTNOTE"
        else:
            continue

        corrected = match.corrected_label
        key = f"{original} → {corrected}"
        label_changes[key] = label_changes.get(key, 0) + 1

    print("\nLabel changes:")
    for change, count in sorted(label_changes.items()):
        print(f"  {change}: {count}")

    return 0


if __name__ == "__main__":
    exit(main())

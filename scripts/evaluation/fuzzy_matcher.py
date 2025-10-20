#!/usr/bin/env python3
"""
Fuzzy matching between extraction items and HTML ground truth.

Matches each extraction item to the most similar HTML paragraph using:
- Text similarity (RapidFuzz or difflib)
- No locality optimization yet (Phase 2)
"""

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


def match_all_items(
    items: list[ExtractedItem],
    body_html: list[HTMLLine],
    footnote_html: list[HTMLLine],
    threshold: float = 0.75,
) -> list[FuzzyMatch]:
    """
    Match all extraction items to HTML ground truth.

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

#!/usr/bin/env python3
"""
Sequential Fuzzy Matching for PDF-to-HTML Label Transfer (V3 Pipeline).

This script implements the v3 corpus building pipeline:
1. Load Docling extraction from PDF (tokens/lines with auto-labels)
2. Load processed HTML ground truth (body paragraphs + footnote paragraphs)
3. Use sequential fuzzy matching to relabel PDF lines with HTML ground truth
4. Output relabeled extraction with corrected labels

Key Principles:
- SEQUENTIAL MATCHING: PDF lines match HTML in reading order (monotonic)
- FUZZY MATCHING: Use RapidFuzz partial_ratio for short-to-long string matching
- GROUND TRUTH: HTML structure is definitive for body_text and footnote labels

Author: Claude Code (draft)
Date: 2025-01-17
"""

import json
from dataclasses import dataclass
from pathlib import Path

try:
    from rapidfuzz import fuzz, utils
except ImportError:
    print("ERROR: RapidFuzz not installed. Install with: pip install rapidfuzz")
    exit(1)


# Configuration
MATCH_THRESHOLD = 70  # Minimum similarity score (0-100) to accept a match
CONTEXT_WINDOW = 500  # Characters to search forward from current position


@dataclass
class PDFLine:
    """A single line/token from Docling PDF extraction."""

    text: str
    original_label: str  # Docling's automatic label
    page_num: int
    bbox: dict | None = None  # Bounding box if available


@dataclass
class HTMLParagraph:
    """A paragraph from processed HTML ground truth."""

    text: str
    label: str  # "body-text" or "footnote-text"
    word_count: int


@dataclass
class MatchResult:
    """Result of a fuzzy match attempt."""

    matched: bool
    html_paragraph_idx: int
    similarity_score: float
    match_position: int  # Character position in concatenated HTML where match was found


class SequentialFuzzyMatcher:
    """
    Matches PDF lines to HTML paragraphs using sequential fuzzy matching.

    Maintains monotonic constraint: each match must occur after the previous match
    in the HTML reading order.
    """

    def __init__(
        self,
        body_paragraphs: list[HTMLParagraph],
        footnote_paragraphs: list[HTMLParagraph],
        threshold: int = MATCH_THRESHOLD,
    ):
        """
        Initialize matcher with HTML ground truth.

        Args:
            body_paragraphs: List of body text paragraphs from HTML
            footnote_paragraphs: List of footnote paragraphs from HTML
            threshold: Minimum similarity score to accept a match
        """
        self.body_paragraphs = body_paragraphs
        self.footnote_paragraphs = footnote_paragraphs
        self.threshold = threshold

        # Concatenate HTML for sequential searching
        self.body_text = " ".join(p.text for p in body_paragraphs)
        self.footnote_text = " ".join(p.text for p in footnote_paragraphs)

        # Track current position for monotonic matching
        self.body_position = 0
        self.footnote_position = 0

        # Statistics
        self.stats = {
            "total_lines": 0,
            "body_matches": 0,
            "footnote_matches": 0,
            "no_match": 0,
            "backtrack_violations": 0,
        }

    def _find_best_match_in_window(
        self, pdf_line: str, html_text: str, start_pos: int, window_size: int = CONTEXT_WINDOW
    ) -> MatchResult:
        """
        Find best fuzzy match within a window of HTML text.

        Uses RapidFuzz partial_ratio to find short PDF line within longer HTML.

        Args:
            pdf_line: Short text from PDF to match
            html_text: Long HTML text to search within
            start_pos: Character position to start search (for monotonic constraint)
            window_size: How many characters forward to search

        Returns:
            MatchResult with match details
        """
        # Extract search window (enforce forward-only search)
        end_pos = min(start_pos + window_size, len(html_text))
        search_window = html_text[start_pos:end_pos]

        if not search_window:
            return MatchResult(
                matched=False, html_paragraph_idx=-1, similarity_score=0.0, match_position=start_pos
            )

        # Use partial_ratio: finds best substring match
        # Use default_process to normalize (lowercase, strip punctuation)
        similarity = fuzz.partial_ratio(pdf_line, search_window, processor=utils.default_process)

        if similarity >= self.threshold:
            # TODO: Could calculate exact match position using token_set_ratio
            # For now, just advance position by reasonable amount
            match_pos = start_pos + len(pdf_line)
            return MatchResult(
                matched=True,
                html_paragraph_idx=-1,  # TODO: map to paragraph
                similarity_score=similarity,
                match_position=match_pos,
            )
        else:
            return MatchResult(
                matched=False,
                html_paragraph_idx=-1,
                similarity_score=similarity,
                match_position=start_pos,
            )

    def match_line(self, pdf_line: PDFLine) -> tuple[str, MatchResult]:
        """
        Match a single PDF line to HTML ground truth.

        Tries body text first, then footnotes, maintaining sequential constraint.

        Args:
            pdf_line: PDF line to match

        Returns:
            Tuple of (assigned_label, match_result)
        """
        self.stats["total_lines"] += 1

        # Try matching against body text
        body_match = self._find_best_match_in_window(
            pdf_line.text, self.body_text, self.body_position
        )

        # Try matching against footnote text
        footnote_match = self._find_best_match_in_window(
            pdf_line.text, self.footnote_text, self.footnote_position
        )

        # Decide which label to assign
        if body_match.matched and footnote_match.matched:
            # Both matched - pick the one with higher score
            if body_match.similarity_score > footnote_match.similarity_score:
                self.body_position = body_match.match_position
                self.stats["body_matches"] += 1
                return "body_text", body_match
            else:
                self.footnote_position = footnote_match.match_position
                self.stats["footnote_matches"] += 1
                return "footnote", footnote_match

        elif body_match.matched:
            self.body_position = body_match.match_position
            self.stats["body_matches"] += 1
            return "body_text", body_match

        elif footnote_match.matched:
            self.footnote_position = footnote_match.match_position
            self.stats["footnote_matches"] += 1
            return "footnote", footnote_match

        else:
            # No match found - keep original Docling label or mark uncertain
            self.stats["no_match"] += 1
            return pdf_line.original_label, MatchResult(
                matched=False,
                html_paragraph_idx=-1,
                similarity_score=max(body_match.similarity_score, footnote_match.similarity_score),
                match_position=-1,
            )

    def print_stats(self):
        """Print matching statistics."""
        print("\n=== Sequential Fuzzy Matching Statistics ===")
        print(f"Total PDF lines processed: {self.stats['total_lines']}")
        print(
            f"  Matched to body_text:    {self.stats['body_matches']} ({self.stats['body_matches'] / self.stats['total_lines'] * 100:.1f}%)"
        )
        print(
            f"  Matched to footnote:     {self.stats['footnote_matches']} ({self.stats['footnote_matches'] / self.stats['total_lines'] * 100:.1f}%)"
        )
        print(
            f"  No match found:          {self.stats['no_match']} ({self.stats['no_match'] / self.stats['total_lines'] * 100:.1f}%)"
        )
        print(f"  Match threshold used:    {self.threshold}%")


def load_docling_extraction(pdf_extraction_file: Path) -> list[PDFLine]:
    """
    Load Docling PDF extraction.

    Actual Docling format has 'texts' array with items containing:
    - text: The text content
    - label: Docling's automatic label (footnote, text, section_header, etc.)
    - content_layer: 'body' or 'furniture' (we skip furniture)
    - prov: List of provenance dicts with page_no and bbox

    Args:
        pdf_extraction_file: Path to Docling extraction JSON

    Returns:
        List of PDFLine objects
    """
    with open(pdf_extraction_file) as f:
        data = json.load(f)

    pdf_lines = []
    for item in data.get("texts", []):
        # Skip furniture (page headers, page numbers, etc.)
        if item.get("content_layer") == "furniture":
            continue

        # Extract page number and bbox from provenance
        prov = item.get("prov", [])
        page_num = prov[0].get("page_no", 0) if prov else 0
        bbox = prov[0].get("bbox") if prov else None

        pdf_lines.append(
            PDFLine(
                text=item.get("text", ""),
                original_label=item.get("label", "unknown"),
                page_num=page_num,
                bbox=bbox,
            )
        )

    return pdf_lines


def load_processed_html(
    processed_html_file: Path,
) -> tuple[list[HTMLParagraph], list[HTMLParagraph]]:
    """
    Load processed HTML ground truth.

    Expected format: JSON with "paragraphs" list, each with:
    - text, label ("body-text" or "footnote-text"), word_count

    Args:
        processed_html_file: Path to processed HTML JSON

    Returns:
        Tuple of (body_paragraphs, footnote_paragraphs)
    """
    with open(processed_html_file) as f:
        data = json.load(f)

    body_paragraphs = []
    footnote_paragraphs = []

    for para in data["paragraphs"]:
        html_para = HTMLParagraph(
            text=para["text"], label=para["label"], word_count=para["word_count"]
        )

        if para["label"] == "body-text":
            body_paragraphs.append(html_para)
        elif para["label"] == "footnote-text":
            footnote_paragraphs.append(html_para)

    return body_paragraphs, footnote_paragraphs


def save_relabeled_extraction(
    pdf_lines: list[PDFLine],
    labels: list[str],
    match_results: list[MatchResult],
    output_file: Path,
    quiet: bool = False,
):
    """
    Save relabeled PDF extraction with corrected labels.

    Args:
        pdf_lines: Original PDF lines
        labels: Corrected labels from fuzzy matching
        match_results: Match details for each line
        output_file: Path to save relabeled extraction
        quiet: If True, suppress output message
    """
    relabeled_data = {
        "basename": output_file.stem,
        "method": "sequential_fuzzy_matching",
        "match_threshold": MATCH_THRESHOLD,
        "text_blocks": [],
    }

    for pdf_line, label, match_result in zip(pdf_lines, labels, match_results, strict=False):
        relabeled_data["text_blocks"].append(
            {
                "text": pdf_line.text,
                "original_label": pdf_line.original_label,
                "corrected_label": label,
                "page_num": pdf_line.page_num,
                "bbox": pdf_line.bbox,
                "match_confidence": match_result.similarity_score,
                "matched": match_result.matched,
            }
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(relabeled_data, f, ensure_ascii=False, indent=2)

    if not quiet:
        print(f"\n✅ Saved relabeled extraction to: {output_file}")


def process_single_article(basename: str, quiet: bool = False):
    """
    Process a single article through the v3 pipeline.

    Args:
        basename: Article basename (e.g., "harvard_law_review_excited_delirium")
        quiet: If True, suppress detailed output (for batch processing)
    """
    if not quiet:
        print(f"\n{'=' * 80}")
        print(f"Processing: {basename}")
        print(f"{'=' * 80}")

    # Define paths
    docling_file = Path(f"data/v3_data/docling_extraction/{basename}.json")
    html_file = Path(f"data/v3_data/processed_html/{basename}.json")
    output_file = Path(f"data/v3_data/relabeled_extraction/{basename}.json")

    # Check inputs exist
    if not docling_file.exists():
        if not quiet:
            print(f"⚠️  Docling extraction not found: {docling_file}")
        return
    if not html_file.exists():
        if not quiet:
            print(f"⚠️  Processed HTML not found: {html_file}")
        return

    # Load data
    if not quiet:
        print(f"Loading Docling extraction: {docling_file}")
    pdf_lines = load_docling_extraction(docling_file)
    if not quiet:
        print(f"  Loaded {len(pdf_lines)} PDF lines")

    if not quiet:
        print(f"Loading HTML ground truth: {html_file}")
    body_paragraphs, footnote_paragraphs = load_processed_html(html_file)
    if not quiet:
        print(f"  Loaded {len(body_paragraphs)} body paragraphs")
        print(f"  Loaded {len(footnote_paragraphs)} footnote paragraphs")

    # Initialize matcher
    matcher = SequentialFuzzyMatcher(body_paragraphs, footnote_paragraphs)

    # Match each PDF line
    if not quiet:
        print(f"\nMatching {len(pdf_lines)} PDF lines to HTML ground truth...")
    labels = []
    match_results = []

    for pdf_line in pdf_lines:
        label, match_result = matcher.match_line(pdf_line)
        labels.append(label)
        match_results.append(match_result)

    # Print statistics
    if not quiet:
        matcher.print_stats()

    # Save relabeled extraction
    save_relabeled_extraction(pdf_lines, labels, match_results, output_file, quiet=quiet)


def main():
    """
    Main entry point for v3 pipeline relabeling.

    TODO: Implement batch processing for all articles in v3_data
    """
    print("V3 Pipeline: Sequential Fuzzy Matching for Label Transfer")
    print("=" * 80)

    # Example: Process a single article
    # TODO: Get list of all basenames from v3_data/processed_html
    example_basename = "academic_limbo__reforming_campus_speech_governance_for_students"
    process_single_article(example_basename)

    # TODO: Batch processing
    # processed_html_dir = Path("data/v3_data/processed_html")
    # for html_file in sorted(processed_html_dir.glob("*.json")):
    #     basename = html_file.stem
    #     process_single_article(basename)


if __name__ == "__main__":
    main()

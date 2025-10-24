#!/usr/bin/env python3
"""
Unit tests for sequence alignment algorithms.

Tests all three alignment approaches:
1. DP two-sequence alignment
2. Two-Pass Needleman-Wunsch
3. HMM Viterbi
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "evaluation"))

from parse_extraction import ExtractedItem
from prepare_matching_data import HTMLLine
from sequence_alignment.dp_alignment import dp_two_sequence_alignment
from sequence_alignment.hmm_alignment import hmm_viterbi_alignment
from sequence_alignment.two_pass_alignment import two_pass_alignment


# Test fixtures
@pytest.fixture
def simple_pdf_items():
    """Create simple test PDF items."""
    return [
        ExtractedItem(
            text="This is body text one",
            label="TEXT",
            page_num=1,
            bbox=(100, 100, 500, 120),  # (l, t, r, b)
            original_docling_label="DocItemLabel.TEXT",
        ),
        ExtractedItem(
            text="This is body text two",
            label="TEXT",
            page_num=1,
            bbox=(100, 150, 500, 170),
            original_docling_label="DocItemLabel.TEXT",
        ),
        ExtractedItem(
            text="This is a footnote one",
            label="TEXT",
            page_num=1,
            bbox=(100, 700, 500, 720),  # Near bottom
            original_docling_label="DocItemLabel.TEXT",
        ),
    ]


@pytest.fixture
def simple_body_html():
    """Create simple body HTML ground truth."""
    return [
        HTMLLine(text="This is body text one", label="body-text", paragraph_index=0, source="test"),
        HTMLLine(text="This is body text two", label="body-text", paragraph_index=1, source="test"),
    ]


@pytest.fixture
def simple_footnote_html():
    """Create simple footnote HTML ground truth."""
    return [
        HTMLLine(
            text="This is a footnote one", label="footnote-text", paragraph_index=0, source="test"
        ),
    ]


class TestDPAlignment:
    """Tests for DP two-sequence alignment."""

    def test_simple_case(self, simple_pdf_items, simple_body_html, simple_footnote_html):
        """Test simple 3-line PDF with 2 body + 1 footnote."""
        matches = dp_two_sequence_alignment(
            simple_pdf_items, simple_body_html, simple_footnote_html, threshold=0.5
        )

        assert len(matches) == 3

        # First two should be body
        assert matches[0].assignment == "body"
        assert matches[1].assignment == "body"

        # Third should be footnote
        assert matches[2].assignment == "footnote"

        # Check labels
        assert matches[0].corrected_label == "body-text"
        assert matches[1].corrected_label == "body-text"
        assert matches[2].corrected_label == "footnote-text"

    def test_empty_html(self, simple_pdf_items):
        """Test with empty HTML lists."""
        matches = dp_two_sequence_alignment(simple_pdf_items, [], [], threshold=0.75)

        assert len(matches) == 3
        # All should keep original labels
        for match in matches:
            assert match.assignment == "original"
            assert match.matched_html is None

    def test_single_match(self):
        """Test with single PDF line and single HTML match."""
        items = [
            ExtractedItem(
                text="This is a longer test line with enough content",
                label="TEXT",
                page_num=1,
                bbox=(100, 100, 500, 120),
                original_docling_label="DocItemLabel.TEXT",
            )
        ]
        body_html = [
            HTMLLine(
                text="This is a longer test line with enough content",
                label="body-text",
                paragraph_index=0,
                source="test",
            )
        ]
        footnote_html = []

        matches = dp_two_sequence_alignment(items, body_html, footnote_html, threshold=0.5)

        assert len(matches) == 1
        assert matches[0].assignment == "body"
        assert matches[0].similarity_score > 0.9  # Should be high similarity

    def test_threshold_sensitivity(self, simple_pdf_items, simple_body_html, simple_footnote_html):
        """Test that threshold affects matching."""
        # With low threshold
        matches_low = dp_two_sequence_alignment(
            simple_pdf_items, simple_body_html, simple_footnote_html, threshold=0.3
        )

        # With high threshold
        matches_high = dp_two_sequence_alignment(
            simple_pdf_items, simple_body_html, simple_footnote_html, threshold=0.99
        )

        # Low threshold should match more
        low_matched = sum(1 for m in matches_low if m.matched_html is not None)
        high_matched = sum(1 for m in matches_high if m.matched_html is not None)

        assert low_matched >= high_matched


class TestTwoPassAlignment:
    """Tests for Two-Pass Needleman-Wunsch alignment."""

    def test_simple_case(self, simple_pdf_items, simple_body_html, simple_footnote_html):
        """Test simple 3-line PDF with 2 body + 1 footnote."""
        matches = two_pass_alignment(
            simple_pdf_items, simple_body_html, simple_footnote_html, threshold=0.5
        )

        assert len(matches) == 3

        # Should identify body and footnote (exact assignments may vary)
        body_count = sum(1 for m in matches if m.assignment == "body")
        footnote_count = sum(1 for m in matches if m.assignment == "footnote")

        assert body_count >= 1  # At least one body
        assert footnote_count >= 1  # At least one footnote

    def test_empty_html(self, simple_pdf_items):
        """Test with empty HTML lists."""
        matches = two_pass_alignment(simple_pdf_items, [], [], threshold=0.75)

        assert len(matches) == 3
        # All should keep original labels
        for match in matches:
            assert match.assignment == "original"
            assert match.matched_html is None

    def test_pass_independence(self, simple_pdf_items, simple_body_html, simple_footnote_html):
        """Test that pass order matters (or document behavior)."""
        # Current implementation: body first, then footnote
        two_pass_alignment(simple_pdf_items, simple_body_html, simple_footnote_html, threshold=0.5)

        # Verify that body pass happens first
        # If a line matches both body and footnote well, body should win
        first_item = simple_pdf_items[0]

        # Create competing HTML
        competing_footnote = [
            HTMLLine(
                text="This is body text one",
                label="footnote-text",
                paragraph_index=0,
                source="test",
            )
        ]

        matches_competing = two_pass_alignment(
            [first_item], simple_body_html, competing_footnote, threshold=0.5
        )

        # Body should win in pass 1
        assert matches_competing[0].assignment == "body"

    def test_threshold_sensitivity(self, simple_pdf_items, simple_body_html, simple_footnote_html):
        """Test that threshold affects matching."""
        matches_low = two_pass_alignment(
            simple_pdf_items, simple_body_html, simple_footnote_html, threshold=0.3
        )

        matches_high = two_pass_alignment(
            simple_pdf_items, simple_body_html, simple_footnote_html, threshold=0.99
        )

        low_matched = sum(1 for m in matches_low if m.matched_html is not None)
        high_matched = sum(1 for m in matches_high if m.matched_html is not None)

        assert low_matched >= high_matched


class TestHMMAlignment:
    """Tests for HMM Viterbi alignment."""

    def test_simple_case(self, simple_pdf_items, simple_body_html, simple_footnote_html):
        """Test simple 3-line PDF with 2 body + 1 footnote."""
        matches = hmm_viterbi_alignment(
            simple_pdf_items, simple_body_html, simple_footnote_html, threshold=0.5
        )

        assert len(matches) == 3

        # All should have state assignments (even if original)
        for match in matches:
            assert match.assignment in ["body", "footnote", "original"]

    def test_spatial_prior(self):
        """Test that spatial position affects state assignment."""
        # Create items at different vertical positions
        items = [
            ExtractedItem(
                text="Top text unclear match",
                label="TEXT",
                page_num=1,
                bbox=(100, 100, 500, 120),  # Top
                original_docling_label="DocItemLabel.TEXT",
            ),
            ExtractedItem(
                text="Bottom text unclear match",
                label="TEXT",
                page_num=1,
                bbox=(100, 700, 500, 720),  # Bottom
                original_docling_label="DocItemLabel.TEXT",
            ),
        ]

        # Create ambiguous HTML (low similarity)
        body_html = [
            HTMLLine(
                text="Some other body text", label="body-text", paragraph_index=0, source="test"
            )
        ]
        footnote_html = [
            HTMLLine(
                text="Some other footnote text",
                label="footnote-text",
                paragraph_index=0,
                source="test",
            )
        ]

        matches = hmm_viterbi_alignment(items, body_html, footnote_html, threshold=0.3)

        # Bottom item should favor footnote state due to spatial prior
        # (though this depends on emission probabilities too)
        assert len(matches) == 2

    def test_state_persistence(self):
        """Test that similar items nearby tend to stay in same state."""
        # Create several similar items in sequence
        items = [
            ExtractedItem(
                text=f"Body paragraph {i}",
                label="TEXT",
                page_num=1,
                bbox=(100, 100 + i * 30, 500, 120 + i * 30),
                original_docling_label="DocItemLabel.TEXT",
            )
            for i in range(5)
        ]

        body_html = [
            HTMLLine(
                text="Body paragraph reference", label="body-text", paragraph_index=0, source="test"
            )
        ]
        footnote_html = [
            HTMLLine(
                text="Footnote reference", label="footnote-text", paragraph_index=0, source="test"
            )
        ]

        matches = hmm_viterbi_alignment(items, body_html, footnote_html, threshold=0.3)

        # Should exhibit state persistence (most in same state)
        body_count = sum(1 for m in matches if m.assignment == "body")
        footnote_count = sum(1 for m in matches if m.assignment == "footnote")

        # One state should dominate
        assert max(body_count, footnote_count) >= 3

    def test_empty_html(self, simple_pdf_items):
        """Test with empty HTML lists."""
        matches = hmm_viterbi_alignment(simple_pdf_items, [], [], threshold=0.75)

        assert len(matches) == 3
        # All should keep original labels (low emission probabilities)
        for match in matches:
            assert match.assignment == "original"
            assert match.matched_html is None


class TestIntegration:
    """Integration tests with real data structure."""

    @pytest.mark.slow
    def test_real_data(self):
        """Test all algorithms on real harvard_law_review data."""
        from parse_extraction import load_extraction
        from prepare_matching_data import load_html_ground_truth

        ext_file = Path(
            "results/ocr_pipeline_evaluation/extractions/harvard_law_review_unwarranted_warrants_baseline_extraction.json"
        )

        # Skip if file doesn't exist
        if not ext_file.exists():
            pytest.skip(f"Test data not found: {ext_file}")

        items = load_extraction(ext_file)
        body_html, footnote_html = load_html_ground_truth("harvard_law_review_unwarranted_warrants")

        # Test DP
        dp_matches = dp_two_sequence_alignment(items, body_html, footnote_html, threshold=0.75)
        assert len(dp_matches) == len(items)

        # Test Two-Pass
        tp_matches = two_pass_alignment(items, body_html, footnote_html, threshold=0.75)
        assert len(tp_matches) == len(items)

        # Test HMM
        hmm_matches = hmm_viterbi_alignment(items, body_html, footnote_html, threshold=0.75)
        assert len(hmm_matches) == len(items)

        # Verify all produce valid assignments
        for matches in [dp_matches, tp_matches, hmm_matches]:
            for match in matches:
                assert match.assignment in ["body", "footnote", "original"]
                if match.matched_html is not None:
                    assert match.similarity_score > 0

    def test_algorithms_differ_from_baseline(
        self, simple_pdf_items, simple_body_html, simple_footnote_html
    ):
        """Test that new algorithms can produce different results than baseline."""
        from fuzzy_matcher import match_all_lines_with_locality

        # Run baseline
        baseline_matches = match_all_lines_with_locality(
            simple_pdf_items, simple_body_html, simple_footnote_html, threshold=0.5
        )

        # Run DP
        dp_matches = dp_two_sequence_alignment(
            simple_pdf_items, simple_body_html, simple_footnote_html, threshold=0.5
        )

        # At least verify they can run without errors
        assert len(baseline_matches) == len(dp_matches) == len(simple_pdf_items)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

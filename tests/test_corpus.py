"""Test corpus data files."""

import pandas as pd
import pytest


def test_corpus_file_exists(corpus_file):
    """Test that the main corpus file exists."""
    assert corpus_file.exists(), f"Corpus file not found: {corpus_file}"


def test_corpus_is_csv(corpus_file):
    """Test that corpus file can be loaded as CSV."""
    try:
        df = pd.read_csv(corpus_file)
        assert df is not None
        assert len(df) > 0, "Corpus is empty"
    except Exception as e:
        pytest.fail(f"Failed to load corpus as CSV: {e}")


def test_corpus_has_required_columns(corpus_file):
    """Test that corpus has required columns."""
    df = pd.read_csv(corpus_file)

    required_columns = {"text", "label"}
    actual_columns = set(df.columns)

    assert required_columns.issubset(actual_columns), (
        f"Missing required columns. Expected {required_columns}, got {actual_columns}"
    )


def test_corpus_labels_are_valid(corpus_file):
    """Test that all labels in corpus are valid."""
    df = pd.read_csv(corpus_file)

    valid_labels = {
        "body_text",
        "heading",
        "footnote",
        "caption",
        "page_header",
        "page_footer",
        "cover",
    }

    unique_labels = set(df["label"].unique())

    assert unique_labels.issubset(valid_labels), (
        f"Invalid labels found. Expected subset of {valid_labels}, got {unique_labels}"
    )


def test_corpus_has_core_classes(corpus_file):
    """Test that corpus contains core classes (body_text, footnote)."""
    df = pd.read_csv(corpus_file)

    # Core classes that should always be present
    core_classes = {"body_text", "footnote"}

    actual_classes = set(df["label"].unique())

    assert core_classes.issubset(actual_classes), (
        f"Missing core classes. Expected at least {core_classes}, got {actual_classes}"
    )


def test_corpus_no_empty_text(corpus_file):
    """Test that corpus has no empty text entries."""
    df = pd.read_csv(corpus_file)

    empty_count = df["text"].isna().sum() + (df["text"].str.strip() == "").sum()

    assert empty_count == 0, f"Found {empty_count} empty text entries in corpus"


def test_corpus_minimum_samples_per_class(corpus_file):
    """Test that each class has minimum number of samples."""
    df = pd.read_csv(corpus_file)

    MIN_SAMPLES = 50

    class_counts = df["label"].value_counts()

    for label, count in class_counts.items():
        assert count >= MIN_SAMPLES, (
            f"Class '{label}' has only {count} samples (minimum {MIN_SAMPLES})"
        )


def test_corpus_size_reasonable(corpus_file):
    """Test that corpus has a reasonable total size."""
    df = pd.read_csv(corpus_file)

    MIN_TOTAL = 1000  # At least 1000 samples total
    MAX_TOTAL = 1000000  # At most 1M samples total

    total_samples = len(df)

    assert MIN_TOTAL <= total_samples <= MAX_TOTAL, (
        f"Corpus size {total_samples} outside reasonable range [{MIN_TOTAL}, {MAX_TOTAL}]"
    )

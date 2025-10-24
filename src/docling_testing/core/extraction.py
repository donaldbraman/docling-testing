"""Text extraction utilities for Docling results.

Centralizes common extraction patterns from Docling ConversionResult objects.
"""

from typing import Any


def extract_text_blocks(doc: Any) -> list[str]:
    """Extract all text blocks from Docling document.

    Args:
        doc: Docling ConversionResult object

    Returns:
        List of text strings from document.texts
    """
    return [item.text for item in doc.document.texts if item.text]


def extract_body_text(doc: Any) -> list[str]:
    """Extract only body text (TextItem) blocks.

    Args:
        doc: Docling ConversionResult object

    Returns:
        List of text strings classified as TextItem
    """
    return [
        item.text for item in doc.document.texts if type(item).__name__ == "TextItem" and item.text
    ]


def extract_by_classification(doc: Any) -> dict[str, list[str]]:
    """Extract text blocks grouped by classification.

    Args:
        doc: Docling ConversionResult object

    Returns:
        Dictionary mapping classification names to lists of text blocks
    """
    classifications = {}

    for item in doc.document.texts:
        item_type = type(item).__name__
        if item_type not in classifications:
            classifications[item_type] = []
        if item.text:
            classifications[item_type].append(item.text)

    return classifications


def get_classification_counts(doc: Any) -> dict[str, int]:
    """Count text blocks by classification.

    Args:
        doc: Docling ConversionResult object

    Returns:
        Dictionary mapping classification names to counts
    """
    counts = {}

    for item in doc.document.texts:
        item_type = type(item).__name__
        counts[item_type] = counts.get(item_type, 0) + 1

    return counts


def extract_metadata(doc: Any) -> dict[str, Any]:
    """Extract common metadata from Docling result.

    Args:
        doc: Docling ConversionResult object

    Returns:
        Dictionary with metadata including text_blocks, tables, etc.
    """
    return {
        "text_blocks": len(doc.document.texts) if hasattr(doc.document, "texts") else 0,
        "tables": len(doc.document.tables) if hasattr(doc.document, "tables") else 0,
        "pages": doc.document.pages if hasattr(doc.document, "pages") else None,
    }


def export_to_json(doc: Any, include_metadata: bool = True) -> dict[str, Any]:
    """Export Docling result to JSON-serializable dictionary.

    Args:
        doc: Docling ConversionResult object
        include_metadata: Include metadata in output

    Returns:
        Dictionary with texts, classifications, and optionally metadata
    """
    result = {
        "texts": extract_text_blocks(doc),
        "classifications": extract_by_classification(doc),
    }

    if include_metadata:
        result["metadata"] = extract_metadata(doc)

    return result

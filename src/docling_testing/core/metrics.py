"""Evaluation metrics for OCR and text extraction.

Centralizes metric calculations used across evaluation scripts.
"""

from typing import Any


def calculate_character_coverage(extracted: str, reference: str) -> float:
    """Calculate character coverage as percentage.

    Args:
        extracted: Text extracted by system under test
        reference: Reference text (ground truth or baseline)

    Returns:
        Coverage percentage (0-100)
    """
    if not reference:
        return 0.0
    return 100 * len(extracted) / len(reference)


def calculate_block_ratio(extracted_blocks: list[str], reference_blocks: list[str]) -> float:
    """Calculate ratio of extracted blocks to reference blocks.

    Args:
        extracted_blocks: Text blocks from system under test
        reference_blocks: Reference blocks

    Returns:
        Ratio as percentage (0-100+)
    """
    if not reference_blocks:
        return 0.0
    return 100 * len(extracted_blocks) / len(reference_blocks)


def calculate_consolidation_factor(
    extracted_blocks: list[str], reference_blocks: list[str]
) -> float:
    """Calculate average block size ratio (measures consolidation).

    Args:
        extracted_blocks: Text blocks from system under test
        reference_blocks: Reference blocks

    Returns:
        Ratio of average chars/block (>1 means more consolidated)
    """
    if not reference_blocks or not extracted_blocks:
        return 0.0

    avg_extracted = sum(len(b) for b in extracted_blocks) / len(extracted_blocks)
    avg_reference = sum(len(b) for b in reference_blocks) / len(reference_blocks)

    if avg_reference == 0:
        return 0.0

    return avg_extracted / avg_reference


def compare_ocr_results(ocrmac_blocks: list[str], tesseract_blocks: list[str]) -> dict[str, Any]:
    """Compare two OCR results with multiple metrics.

    Args:
        ocrmac_blocks: Text blocks from ocrmac
        tesseract_blocks: Text blocks from Tesseract

    Returns:
        Dictionary with comparison metrics
    """
    ocrmac_chars = sum(len(b) for b in ocrmac_blocks)
    tesseract_chars = sum(len(b) for b in tesseract_blocks)

    return {
        "ocrmac": {
            "blocks": len(ocrmac_blocks),
            "chars": ocrmac_chars,
            "avg_chars_per_block": ocrmac_chars / len(ocrmac_blocks) if ocrmac_blocks else 0,
        },
        "tesseract": {
            "blocks": len(tesseract_blocks),
            "chars": tesseract_chars,
            "avg_chars_per_block": (
                tesseract_chars / len(tesseract_blocks) if tesseract_blocks else 0
            ),
        },
        "comparison": {
            "char_coverage_pct": calculate_character_coverage(
                "".join(tesseract_blocks), "".join(ocrmac_blocks)
            ),
            "block_ratio_pct": calculate_block_ratio(tesseract_blocks, ocrmac_blocks),
            "consolidation_factor": calculate_consolidation_factor(tesseract_blocks, ocrmac_blocks),
        },
    }


def format_metrics_summary(metrics: dict[str, Any]) -> str:
    """Format metrics dictionary as readable summary.

    Args:
        metrics: Metrics dictionary from compare_ocr_results()

    Returns:
        Formatted string summary
    """
    lines = []
    lines.append("\nMetrics Summary:")
    lines.append(
        f"  ocrmac:    {metrics['ocrmac']['blocks']:4d} blocks, {metrics['ocrmac']['chars']:7,d} chars"
    )
    lines.append(
        f"  Tesseract: {metrics['tesseract']['blocks']:4d} blocks, {metrics['tesseract']['chars']:7,d} chars"
    )
    lines.append("\nComparison:")
    lines.append(f"  Character coverage:   {metrics['comparison']['char_coverage_pct']:5.1f}%")
    lines.append(f"  Block ratio:          {metrics['comparison']['block_ratio_pct']:5.1f}%")
    lines.append(f"  Consolidation factor: {metrics['comparison']['consolidation_factor']:5.2f}x")

    return "\n".join(lines)

"""Docling Testing: ML model training repository for document structure classification.

This package provides shared utilities for OCR evaluation, text extraction,
and metrics calculation.
"""

__version__ = "3.0.0"

from .core import (
    OcrEngine,
    calculate_block_ratio,
    calculate_character_coverage,
    calculate_consolidation_factor,
    check_pdf_colorspace,
    compare_ocr_results,
    create_color_overlay,
    create_image_only_pdf,
    create_ocr_converter,
    create_pipeline_options,
    export_to_json,
    extract_body_text,
    extract_by_classification,
    extract_metadata,
    extract_text_blocks,
    extract_text_pymupdf,
    format_metrics_summary,
    get_classification_counts,
    get_ocr_options,
    get_pdf_page_count,
)

__all__ = [
    "__version__",
    # OCR
    "OcrEngine",
    "create_ocr_converter",
    "create_pipeline_options",
    "get_ocr_options",
    # PDF utilities
    "create_image_only_pdf",
    "check_pdf_colorspace",
    "create_color_overlay",
    "extract_text_pymupdf",
    "get_pdf_page_count",
    # Extraction
    "extract_text_blocks",
    "extract_body_text",
    "extract_by_classification",
    "get_classification_counts",
    "extract_metadata",
    "export_to_json",
    # Metrics
    "calculate_character_coverage",
    "calculate_block_ratio",
    "calculate_consolidation_factor",
    "compare_ocr_results",
    "format_metrics_summary",
]

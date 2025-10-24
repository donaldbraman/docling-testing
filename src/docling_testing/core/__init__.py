"""Core utilities for Docling OCR testing and evaluation."""

from .extraction import (
    export_to_json,
    extract_body_text,
    extract_by_classification,
    extract_metadata,
    extract_text_blocks,
    get_classification_counts,
)
from .metrics import (
    calculate_block_ratio,
    calculate_character_coverage,
    calculate_consolidation_factor,
    compare_ocr_results,
    format_metrics_summary,
)
from .ocr import OcrEngine, create_ocr_converter, create_pipeline_options, get_ocr_options
from .pdf_utils import (
    check_pdf_colorspace,
    create_color_overlay,
    create_image_only_pdf,
    extract_text_pymupdf,
    get_pdf_page_count,
)

__all__ = [
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

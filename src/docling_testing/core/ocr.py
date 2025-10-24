"""OCR engine configuration and utilities.

Centralizes OCR engine setup to avoid duplication across scripts.
"""

import os
from typing import Literal

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    OcrAutoOptions,
    OcrMacOptions,
    PdfPipelineOptions,
    RapidOcrOptions,
    TesseractCliOcrOptions,
    TesseractOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

# Set Tesseract data directory
os.environ.setdefault("TESSDATA_PREFIX", "/opt/homebrew/Cellar/tesseract/5.5.1/share/tessdata")

OcrEngine = Literal["ocrmac", "tesseract", "tesseract_cli", "easyocr", "rapidocr", "auto"]


def get_ocr_options(engine: OcrEngine):
    """Get OCR options for specified engine.

    Args:
        engine: OCR engine name

    Returns:
        OCR options object for the specified engine
    """
    match engine:
        case "ocrmac":
            return OcrMacOptions()
        case "tesseract":
            return TesseractOcrOptions()
        case "tesseract_cli":
            return TesseractCliOcrOptions()
        case "easyocr":
            return EasyOcrOptions()
        case "rapidocr":
            return RapidOcrOptions()
        case "auto":
            return OcrAutoOptions()
        case _:
            raise ValueError(f"Unknown OCR engine: {engine}")


def create_ocr_converter(engine: OcrEngine) -> DocumentConverter:
    """Create DocumentConverter with specified OCR engine.

    Args:
        engine: OCR engine name

    Returns:
        Configured DocumentConverter instance
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = get_ocr_options(engine)

    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )


def create_pipeline_options(engine: OcrEngine) -> PdfPipelineOptions:
    """Create PdfPipelineOptions with specified OCR engine.

    Useful when you need the options but not the full converter.

    Args:
        engine: OCR engine name

    Returns:
        Configured PdfPipelineOptions instance
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = get_ocr_options(engine)
    return pipeline_options

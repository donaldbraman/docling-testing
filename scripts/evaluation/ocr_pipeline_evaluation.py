"""
Comprehensive OCR Pipeline Evaluation Framework.

Evaluates three extraction methods on representative corpus:
1. Baseline (Docling text layer only)
2. OCRmyPDF (Tesseract-based OCR)
3. PaddleOCR (GPU-accelerated OCR)

Generates confusion matrices comparing Docling output vs HTML ground truth
for body_text classification, with variation analysis across journals.

Usage:
  uv run scripts/evaluation/ocr_pipeline_evaluation.py --corpus-config corpus_12pdfs.json
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class EvaluationConfig:
    """Configuration for evaluation run."""

    test_pdfs: dict[str, dict[str, str]]  # {journal: {pdf_name, html_name}}
    output_dir: Path
    run_baseline: bool = True
    run_ocrmypdf: bool = True
    run_paddleocr: bool = True
    timing_samples: int = 3  # samples per PDF for timing
    skip_extraction: bool = False  # for testing only


@dataclass
class ExtractionResult:
    """Result from a single extraction."""

    pipeline: str  # "baseline", "ocrmypdf", "paddleocr"
    pdf_name: str
    journal: str
    success: bool
    extraction_time_ms: float
    classification_time_ms: float
    total_time_ms: float
    page_count: int
    item_count: int
    items_per_page: float
    error: str | None = None


@dataclass
class ConfusionMatrixResult:
    """Confusion matrix for body_text classification."""

    pipeline: str
    pdf_name: str
    journal: str
    tp: int  # True positives (correctly identified body_text)
    fp: int  # False positives (body_text that aren't)
    fn: int  # False negatives (body_text that weren't identified)
    tn: int  # True negatives (correctly identified non-body_text)
    precision: float
    recall: float
    f1: float
    accuracy: float
    error_rate: float


class OCRPipelineEvaluator:
    """Main evaluation orchestrator."""

    def __init__(self, config: EvaluationConfig):
        """Initialize evaluator.

        Args:
            config: Evaluation configuration
        """
        self.config = config
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Output subdirectories
        self.extractions_dir = self.config.output_dir / "extractions"
        self.ground_truth_dir = self.config.output_dir / "ground_truth"
        self.matrices_dir = self.config.output_dir / "confusion_matrices"
        self.metrics_dir = self.config.output_dir / "metrics"

        for d in [
            self.extractions_dir,
            self.ground_truth_dir,
            self.matrices_dir,
            self.metrics_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

        self.extraction_results = []
        self.confusion_matrices = []

    def run_evaluation(self) -> None:
        """Execute full evaluation pipeline."""
        logger.info("Starting OCR Pipeline Evaluation")
        logger.info(f"Test PDFs: {len(self.config.test_pdfs)}")
        logger.info(f"Output directory: {self.config.output_dir}")

        try:
            # Phase 1: Extract ground truth from HTML
            logger.info("\n=== PHASE 1: Ground Truth Extraction ===")
            self._extract_ground_truth()

            # Phase 2: Run extractions
            logger.info("\n=== PHASE 2: PDF Extractions ===")
            self._run_extractions()

            # Phase 3: Generate confusion matrices
            logger.info("\n=== PHASE 3: Confusion Matrix Generation ===")
            self._generate_confusion_matrices()

            # Phase 4: Analysis and reporting
            logger.info("\n=== PHASE 4: Analysis & Reporting ===")
            self._generate_reports()

            logger.info("\n=== EVALUATION COMPLETE ===")
            logger.info(f"Results saved to: {self.config.output_dir}")

        except Exception as e:
            logger.error(f"Evaluation failed: {e}", exc_info=True)
            raise

    def _extract_ground_truth(self) -> None:
        """Load/extract ground truth labels (from processed_html if available)."""
        logger.info("Loading ground truth from processed_html...")

        processed_html_dir = Path("data/v3_data/processed_html")

        for journal, files in self.config.test_pdfs.items():
            pdf_name = files["pdf"]

            # Try to use pre-processed ground truth first
            processed_file = processed_html_dir / f"{pdf_name}.json"
            if processed_file.exists():
                # Convert processed_html format to our format
                gt_data = self._convert_processed_html_to_gt(processed_file, journal)

                output_path = self.ground_truth_dir / f"{pdf_name}_ground_truth.json"
                with open(output_path, "w") as f:
                    json.dump(gt_data, f, indent=2)

                logger.info(
                    f"  {journal}: {pdf_name} (from processed_html: "
                    f"{len(gt_data['body_text_paragraphs'])} body paragraphs)"
                )
            else:
                # Fall back to HTML extraction if processed version not available
                logger.warning(f"  {journal}: {pdf_name} not in processed_html, using raw HTML")
                self._extract_from_raw_html(pdf_name, journal)

        logger.info("Ground truth loading complete")

    def _convert_processed_html_to_gt(self, processed_file: Path, journal: str) -> dict[str, Any]:
        """Convert processed_html format to ground truth format.

        Args:
            processed_file: Path to processed HTML JSON
            journal: Journal name

        Returns:
            Ground truth dict in expected format
        """
        with open(processed_file) as f:
            data = json.load(f)

        # Extract body_text and footnote paragraphs (labels use hyphens in processed_html)
        body_text = [
            {
                "text": para["text"],
                "source": "processed_html",
                "length": len(para["text"]),
            }
            for para in data.get("paragraphs", [])
            if para.get("label") == "body-text"
        ]

        footnotes = [
            {
                "text": para["text"],
                "source": "processed_html",
                "length": len(para["text"]),
            }
            for para in data.get("paragraphs", [])
            if para.get("label") == "footnote-text"
        ]

        return {
            "file": data.get("basename", "unknown"),
            "journal": journal,
            "body_text_paragraphs": body_text,
            "footnotes": footnotes,
            "headers": [],
            "other_elements": [],
            "metadata": {
                "source": "processed_html",
                "total_body_paragraphs": len(body_text),
                "total_footnotes": len(footnotes),
                "total_headers": 0,
                "total_other": 0,
                "extraction_method": data.get("extraction_method", "unknown"),
                "stats": data.get("stats", {}),
            },
        }

    def _extract_from_raw_html(self, pdf_name: str, journal: str) -> None:
        """Fall back to raw HTML extraction if processed version not available.

        Args:
            pdf_name: PDF file name stem
            journal: Journal name
        """
        from html_ground_truth_extractor import (
            HTMLGroundTruthExtractor,
        )

        html_path = Path("data/v3_data/raw_html") / (pdf_name + ".html")

        if not html_path.exists():
            logger.warning(f"Neither processed nor raw HTML found for {pdf_name}")
            return

        extractor = HTMLGroundTruthExtractor(output_dir=self.ground_truth_dir)
        extractor.extract(html_path, journal=journal)

    def _run_extractions(self) -> None:
        """Run all enabled extraction pipelines."""
        pipelines = []

        if self.config.run_baseline:
            pipelines.append(("baseline", self._extract_baseline))
        if self.config.run_ocrmypdf:
            pipelines.append(("ocrmypdf", self._extract_ocrmypdf))
        if self.config.run_paddleocr:
            pipelines.append(("paddleocr", self._extract_paddleocr))

        total_pdfs = len(self.config.test_pdfs)
        total_extractions = len(pipelines) * total_pdfs

        current = 0
        for pipeline_name, extract_fn in pipelines:
            logger.info(f"\n--- Pipeline: {pipeline_name} ---")

            for journal, files in self.config.test_pdfs.items():
                current += 1
                pdf_path = Path("data/v3_data/raw_pdf") / (files["pdf"] + ".pdf")

                if not pdf_path.exists():
                    logger.warning(f"PDF not found: {pdf_path}")
                    continue

                logger.info(f"[{current}/{total_extractions}] {pipeline_name} - {journal}")

                try:
                    result = extract_fn(pdf_path, journal, files["pdf"])
                    self.extraction_results.append(result)

                    if result.success:
                        logger.info(
                            f"  ✓ Success: {result.page_count} pages, "
                            f"{result.items_per_page:.1f} items/page, "
                            f"{result.total_time_ms:.0f}ms"
                        )
                    else:
                        logger.error(f"  ✗ Failed: {result.error}")

                except Exception as e:
                    logger.error(f"  ✗ Exception: {e}")
                    self.extraction_results.append(
                        ExtractionResult(
                            pipeline=pipeline_name,
                            pdf_name=files["pdf"],
                            journal=journal,
                            success=False,
                            extraction_time_ms=0,
                            classification_time_ms=0,
                            total_time_ms=0,
                            page_count=0,
                            item_count=0,
                            items_per_page=0.0,
                            error=str(e),
                        )
                    )

        # Save extraction results
        self._save_extraction_results()

    def _extract_baseline(self, pdf_path: Path, journal: str, pdf_name: str) -> ExtractionResult:
        """Extract using baseline Docling (text layer only).

        Args:
            pdf_path: Path to PDF
            journal: Journal name
            pdf_name: PDF filename stem

        Returns:
            ExtractionResult with timing and metrics
        """
        start = time.time()

        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            doc = converter.convert(str(pdf_path))
            total_time = time.time() - start

            # Metrics
            item_count = len(doc.document.texts) if doc.document.texts else 0
            page_count = len(doc.pages) if doc.pages else 1

            # Save extraction
            output_path = self.extractions_dir / f"{pdf_name}_baseline_extraction.json"
            self._save_docling_output(doc, output_path)

            return ExtractionResult(
                pipeline="baseline",
                pdf_name=pdf_name,
                journal=journal,
                success=True,
                extraction_time_ms=0,  # No OCR in baseline
                classification_time_ms=total_time * 1000,
                total_time_ms=total_time * 1000,
                page_count=page_count,
                item_count=item_count,
                items_per_page=item_count / page_count if page_count > 0 else 0,
            )
        except Exception as e:
            return ExtractionResult(
                pipeline="baseline",
                pdf_name=pdf_name,
                journal=journal,
                success=False,
                extraction_time_ms=0,
                classification_time_ms=0,
                total_time_ms=time.time() - start,
                page_count=0,
                item_count=0,
                items_per_page=0.0,
                error=str(e),
            )

    def _extract_ocrmypdf(self, pdf_path: Path, journal: str, pdf_name: str) -> ExtractionResult:
        """Extract using OCRmyPDF (Tesseract).

        Args:
            pdf_path: Path to PDF
            journal: Journal name
            pdf_name: PDF filename stem

        Returns:
            ExtractionResult with timing and metrics
        """
        start = time.time()

        try:
            import tempfile

            import ocrmypdf
            from docling.document_converter import DocumentConverter

            ocr_start = time.time()

            # OCR the PDF (first 10 pages for speed)
            with tempfile.TemporaryDirectory() as tmpdir:
                ocr_output = Path(tmpdir) / "ocr.pdf"
                ocrmypdf.ocr(
                    str(pdf_path),
                    str(ocr_output),
                    language="eng",
                    pages="1-10",
                    progress_bar=False,
                )
                ocr_time = time.time() - ocr_start

                # Extract with Docling
                classification_start = time.time()
                converter = DocumentConverter()
                doc = converter.convert(str(ocr_output))
                classification_time = time.time() - classification_start

                # Metrics
                item_count = len(doc.document.texts) if doc.document.texts else 0
                page_count = len(doc.pages) if doc.pages else 1

                # Save extraction
                output_path = self.extractions_dir / f"{pdf_name}_ocrmypdf_extraction.json"
                self._save_docling_output(doc, output_path)

                total_time = time.time() - start

                return ExtractionResult(
                    pipeline="ocrmypdf",
                    pdf_name=pdf_name,
                    journal=journal,
                    success=True,
                    extraction_time_ms=ocr_time * 1000,
                    classification_time_ms=classification_time * 1000,
                    total_time_ms=total_time * 1000,
                    page_count=page_count,
                    item_count=item_count,
                    items_per_page=item_count / page_count if page_count > 0 else 0,
                )
        except Exception as e:
            return ExtractionResult(
                pipeline="ocrmypdf",
                pdf_name=pdf_name,
                journal=journal,
                success=False,
                extraction_time_ms=0,
                classification_time_ms=0,
                total_time_ms=time.time() - start,
                page_count=0,
                item_count=0,
                items_per_page=0.0,
                error=str(e),
            )

    def _extract_paddleocr(self, pdf_path: Path, journal: str, pdf_name: str) -> ExtractionResult:
        """Extract using PaddleOCR (GPU-accelerated).

        Args:
            pdf_path: Path to PDF
            journal: Journal name
            pdf_name: PDF filename stem

        Returns:
            ExtractionResult with timing and metrics
        """
        start = time.time()

        try:
            import pdf2image
            from paddleocr import PaddleOCR

            ocr_start = time.time()

            # Initialize PaddleOCR with GPU
            ocr = PaddleOCR(use_gpu=True, lang="en")

            # Convert first 10 pages to images
            images = pdf2image.convert_from_path(str(pdf_path), first_page=1, last_page=10)

            # Run OCR
            item_count = 0
            for image in images:
                result = ocr.ocr(image, cls=True)
                if result and result[0]:
                    item_count += len(result[0])

            ocr_time = time.time() - ocr_start

            # Note: For full integration, would pass OCR results to Docling for classification
            # For now, estimate based on page count
            page_count = len(images)
            items_per_page = item_count / page_count if page_count > 0 else 0

            classification_time = 0  # Placeholder

            total_time = time.time() - start

            return ExtractionResult(
                pipeline="paddleocr",
                pdf_name=pdf_name,
                journal=journal,
                success=True,
                extraction_time_ms=ocr_time * 1000,
                classification_time_ms=classification_time * 1000,
                total_time_ms=total_time * 1000,
                page_count=page_count,
                item_count=item_count,
                items_per_page=items_per_page,
            )
        except Exception as e:
            return ExtractionResult(
                pipeline="paddleocr",
                pdf_name=pdf_name,
                journal=journal,
                success=False,
                extraction_time_ms=0,
                classification_time_ms=0,
                total_time_ms=time.time() - start,
                page_count=0,
                item_count=0,
                items_per_page=0.0,
                error=str(e),
            )

    def _save_docling_output(self, doc: Any, output_path: Path) -> None:
        """Save Docling document output as JSON.

        Args:
            doc: Docling document
            output_path: Output file path
        """
        # Extract structured data
        output_data = {
            "texts": list(doc.document.texts) if doc.document.texts else [],
            "page_count": len(doc.pages) if doc.pages else 0,
            "metadata": {
                "model": doc.model_name if hasattr(doc, "model_name") else "unknown",
            },
        }

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)

    def _generate_confusion_matrices(self) -> None:
        """Generate confusion matrices comparing extractions to ground truth."""
        logger.info("Generating confusion matrices...")
        # Placeholder for Phase 3 implementation
        logger.info("  (Confusion matrix generation to follow)")

    def _generate_reports(self) -> None:
        """Generate comprehensive evaluation reports."""
        logger.info("Generating reports...")

        # Save extraction results summary
        if self.extraction_results:
            df = pd.DataFrame([asdict(r) for r in self.extraction_results])
            results_path = self.metrics_dir / "extraction_results.csv"
            df.to_csv(results_path, index=False)
            logger.info(f"  Saved extraction results: {results_path}")

            # Summary statistics
            summary = {
                "total_extractions": len(self.extraction_results),
                "successful": sum(1 for r in self.extraction_results if r.success),
                "failed": sum(1 for r in self.extraction_results if not r.success),
                "by_pipeline": {
                    pipeline: {
                        "count": sum(1 for r in self.extraction_results if r.pipeline == pipeline),
                        "avg_time_ms": pd.Series(
                            [
                                r.total_time_ms
                                for r in self.extraction_results
                                if r.pipeline == pipeline and r.success
                            ]
                        ).mean(),
                        "avg_items_per_page": pd.Series(
                            [
                                r.items_per_page
                                for r in self.extraction_results
                                if r.pipeline == pipeline and r.success
                            ]
                        ).mean(),
                    }
                    for pipeline in {"baseline", "ocrmypdf", "paddleocr"}
                },
            }

            summary_path = self.metrics_dir / "summary.json"
            with open(summary_path, "w") as f:
                json.dump(summary, f, indent=2)
            logger.info(f"  Saved summary: {summary_path}")

            # Print summary
            logger.info("\nExtraction Summary:")
            for pipeline, stats in summary["by_pipeline"].items():
                if stats["count"] > 0:
                    logger.info(
                        f"  {pipeline:12} - "
                        f"{stats['count']:2} tests, "
                        f"avg time: {stats['avg_time_ms']:7.0f}ms, "
                        f"items/page: {stats['avg_items_per_page']:5.1f}"
                    )

    def _save_extraction_results(self) -> None:
        """Save extraction results to CSV."""
        if not self.extraction_results:
            return

        df = pd.DataFrame([asdict(r) for r in self.extraction_results])
        output_path = self.extractions_dir / "extraction_results.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"Saved extraction results: {output_path}")


def load_corpus_config(config_path: Path) -> dict:
    """Load test corpus configuration from JSON.

    Args:
        config_path: Path to config file

    Returns:
        Test PDFs mapping
    """
    with open(config_path) as f:
        return json.load(f)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Comprehensive OCR Pipeline Evaluation")
    parser.add_argument(
        "--corpus-config",
        type=Path,
        default=Path("scripts/evaluation/test_corpus_config.json"),
        help="Path to test corpus configuration JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/ocr_pipeline_evaluation"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="Run baseline extraction only",
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip extraction phase (for testing)",
    )

    args = parser.parse_args()

    # Load corpus configuration
    if not args.corpus_config.exists():
        logger.error(f"Config not found: {args.corpus_config}")
        return 1

    test_pdfs = load_corpus_config(args.corpus_config)

    # Create config
    config = EvaluationConfig(
        test_pdfs=test_pdfs,
        output_dir=args.output_dir,
        run_baseline=True,
        run_ocrmypdf=not args.baseline_only,
        run_paddleocr=not args.baseline_only,
        skip_extraction=args.skip_extraction,
    )

    # Run evaluation
    evaluator = OCRPipelineEvaluator(config)
    evaluator.run_evaluation()

    return 0


if __name__ == "__main__":
    exit(main())

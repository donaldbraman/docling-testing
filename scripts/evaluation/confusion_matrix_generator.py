"""
Generate confusion matrices comparing Docling extractions to HTML ground truth.

For each extracted document, compares the Docling-labeled text items against
ground truth body_text labels from HTML, computing precision/recall/F1 metrics.

Uses fuzzy matching (from V6 pipeline) to match extracted text to ground truth,
then classifies matches as:
- TP (True Positive): Correctly identified as body_text
- FP (False Positive): Identified as body_text but isn't
- FN (False Negative): Actual body_text but not identified
- TN (True Negative): Correctly identified as non-body_text
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


@dataclass
class ConfusionMatrixMetrics:
    """Confusion matrix and derived metrics."""

    tp: int  # True positives
    fp: int  # False positives
    fn: int  # False negatives
    tn: int  # True negatives

    @property
    def precision(self) -> float:
        """Precision: TP / (TP + FP)."""
        if self.tp + self.fp == 0:
            return 0.0
        return self.tp / (self.tp + self.fp)

    @property
    def recall(self) -> float:
        """Recall: TP / (TP + FN)."""
        if self.tp + self.fn == 0:
            return 0.0
        return self.tp / (self.tp + self.fn)

    @property
    def f1(self) -> float:
        """F1 Score: 2 * (precision * recall) / (precision + recall)."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    @property
    def accuracy(self) -> float:
        """Accuracy: (TP + TN) / total."""
        total = self.tp + self.fp + self.fn + self.tn
        if total == 0:
            return 0.0
        return (self.tp + self.tn) / total

    @property
    def error_rate(self) -> float:
        """Error rate: (FP + FN) / total."""
        return 1.0 - self.accuracy

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "accuracy": self.accuracy,
            "error_rate": self.error_rate,
        }


class ConfusionMatrixGenerator:
    """Generate confusion matrices from extractions and ground truth."""

    def __init__(
        self,
        extractions_dir: Path = Path("results/ocr_pipeline_evaluation/extractions"),
        ground_truth_dir: Path = Path("results/ocr_pipeline_evaluation/ground_truth"),
        output_dir: Path = Path("results/ocr_pipeline_evaluation/confusion_matrices"),
        match_threshold: float = 80.0,
    ):
        """Initialize generator.

        Args:
            extractions_dir: Directory containing extracted PDFs
            ground_truth_dir: Directory containing ground truth JSONs
            output_dir: Directory for confusion matrices
            match_threshold: Fuzzy match threshold (0-100)
        """
        self.extractions_dir = Path(extractions_dir)
        self.ground_truth_dir = Path(ground_truth_dir)
        self.output_dir = Path(output_dir)
        self.match_threshold = match_threshold

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self) -> list[dict[str, Any]]:
        """Generate confusion matrices for all extraction/ground truth pairs.

        Returns:
            List of confusion matrix results
        """
        results = []

        # Find all extraction files
        extraction_files = list(self.extractions_dir.glob("*_extraction.json"))

        logger.info(f"Generating matrices for {len(extraction_files)} extractions")

        for i, extraction_file in enumerate(extraction_files, 1):
            logger.info(f"[{i}/{len(extraction_files)}] {extraction_file.name}")

            try:
                result = self._generate_matrix_for_file(extraction_file)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"  Error: {e}")

        return results

    def _generate_matrix_for_file(self, extraction_file: Path) -> dict[str, Any] | None:
        """Generate confusion matrix for a single extraction.

        Args:
            extraction_file: Path to extraction JSON

        Returns:
            Confusion matrix result dict, or None if error
        """
        # Parse filename: {pdf_name}_{pipeline}_extraction.json
        parts = extraction_file.stem.split("_extraction")[0]
        parts_split = parts.rsplit("_", 1)
        if len(parts_split) != 2:
            logger.warning(f"Unexpected filename format: {extraction_file.name}")
            return None

        pdf_name, pipeline = parts_split

        # Find matching ground truth file
        ground_truth_file = self.ground_truth_dir / f"{pdf_name}_ground_truth.json"
        if not ground_truth_file.exists():
            logger.warning(f"Ground truth not found: {ground_truth_file.name}")
            return None

        # Load data
        try:
            with open(extraction_file) as f:
                extraction_data = json.load(f)
            with open(ground_truth_file) as f:
                ground_truth_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON error: {e}")
            return None

        # Generate confusion matrix
        matrix = self._compute_confusion_matrix(extraction_data, ground_truth_data)

        # Create result
        result = {
            "pdf_name": pdf_name,
            "pipeline": pipeline,
            "journal": ground_truth_data.get("journal", "unknown"),
            "confusion_matrix": matrix.to_dict(),
            "extracted_count": len(extraction_data.get("texts", [])),
            "ground_truth_count": len(ground_truth_data.get("body_text_paragraphs", [])),
        }

        # Save to file
        output_file = self.output_dir / f"{pdf_name}_{pipeline}_confusion_matrix.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        logger.info(f"  ✓ P: {matrix.precision:.1%} | R: {matrix.recall:.1%} | F1: {matrix.f1:.1%}")

        return result

    def _compute_confusion_matrix(
        self, extraction_data: dict[str, Any], ground_truth_data: dict[str, Any]
    ) -> ConfusionMatrixMetrics:
        """Compute confusion matrix by fuzzy matching extracted vs ground truth.

        Args:
            extraction_data: Docling extracted data
            ground_truth_data: HTML ground truth

        Returns:
            ConfusionMatrixMetrics
        """
        extracted_texts = extraction_data.get("texts", [])
        ground_truth_texts = ground_truth_data.get("body_text_paragraphs", [])

        tp = 0  # Extracted as body, actually body
        fp = 0  # Extracted as body, actually not body
        fn = 0  # Not extracted as body, but is body
        tn = 0  # Not extracted as body, actually not body

        # Track which ground truth items were matched
        matched_ground_truth = set()

        # For each extracted text, try to match to ground truth
        for extracted in extracted_texts:
            best_match_score = 0
            best_match_idx = None

            # Find best match in ground truth
            for idx, gt in enumerate(ground_truth_texts):
                if idx in matched_ground_truth:
                    continue  # Already matched

                score = self._fuzzy_match_score(extracted, gt["text"])
                if score > best_match_score:
                    best_match_score = score
                    best_match_idx = idx

            # Classify based on match
            if best_match_score >= self.match_threshold:
                # Matched to ground truth body_text
                tp += 1
                matched_ground_truth.add(best_match_idx)
            else:
                # Extracted text doesn't match ground truth (FP)
                fp += 1

        # Unmatched ground truth items are false negatives
        fn = len(ground_truth_texts) - len(matched_ground_truth)

        # True negatives: harder to estimate without full corpus
        # For now, estimate as proportion of unmatched items
        tn = max(0, (len(extracted_texts) - tp - fp) // 2)

        return ConfusionMatrixMetrics(tp=tp, fp=fp, fn=fn, tn=tn)

    def _fuzzy_match_score(self, text1: str, text2: str) -> float:
        """Compute fuzzy match score between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Match score (0-100)
        """
        # Normalize both texts
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)

        # Use partial ratio for matching (allows substring matches)
        score = fuzz.partial_ratio(norm1, norm2)

        return score

    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        import re

        # Convert to lowercase
        text = text.lower()

        # Remove punctuation (except internal structure)
        text = re.sub(r"[^\w\s]", "", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def generate_summary(self, results: list[dict[str, Any]]) -> pd.DataFrame:
        """Generate summary DataFrame from confusion matrices.

        Args:
            results: List of confusion matrix results

        Returns:
            Summary DataFrame
        """
        summary_data = []

        for result in results:
            cm = result["confusion_matrix"]
            summary_data.append(
                {
                    "pdf": result["pdf_name"],
                    "pipeline": result["pipeline"],
                    "journal": result["journal"],
                    "precision": cm["precision"],
                    "recall": cm["recall"],
                    "f1": cm["f1"],
                    "accuracy": cm["accuracy"],
                    "error_rate": cm["error_rate"],
                    "extracted_count": result["extracted_count"],
                    "ground_truth_count": result["ground_truth_count"],
                }
            )

        df = pd.DataFrame(summary_data)
        return df

    def save_summary_csv(self, results: list[dict[str, Any]]) -> None:
        """Save summary as CSV.

        Args:
            results: List of confusion matrix results
        """
        df = self.generate_summary(results)
        output_file = self.output_dir / "confusion_matrices_summary.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"Saved summary: {output_file}")


def main():
    """Generate all confusion matrices."""
    generator = ConfusionMatrixGenerator()
    results = generator.generate_all()

    if results:
        generator.save_summary_csv(results)

        # Print summary statistics
        df = generator.generate_summary(results)
        logger.info("\n=== Summary Statistics ===")
        logger.info(df.groupby("pipeline")[["precision", "recall", "f1"]].mean())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    main()

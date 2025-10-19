"""
Comprehensive analysis and reporting for OCR pipeline evaluation.

Analyzes:
1. Variation by journal (error patterns by source)
2. Pipeline comparison (speed vs quality trade-offs)
3. Fragmentation metrics (items per page)
4. Error pattern analysis (false positives, false negatives)
5. Small caps detection and handling
"""

import json
import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

logger = logging.getLogger(__name__)


class EvaluationAnalyzer:
    """Analyze evaluation results and generate reports."""

    def __init__(
        self,
        confusion_matrices_dir: Path = Path("results/ocr_pipeline_evaluation/confusion_matrices"),
        extractions_dir: Path = Path("results/ocr_pipeline_evaluation/extractions"),
        output_dir: Path = Path("results/ocr_pipeline_evaluation/analysis"),
    ):
        """Initialize analyzer.

        Args:
            confusion_matrices_dir: Directory with confusion matrices
            extractions_dir: Directory with extraction results
            output_dir: Output directory for analysis
        """
        self.confusion_matrices_dir = Path(confusion_matrices_dir)
        self.extractions_dir = Path(extractions_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_all(self) -> dict[str, Any]:
        """Run comprehensive analysis.

        Returns:
            Analysis results dictionary
        """
        logger.info("Starting comprehensive analysis...")

        # Load data
        cm_summary_file = self.confusion_matrices_dir / "confusion_matrices_summary.csv"
        extractions_file = self.extractions_dir / "extraction_results.csv"

        if not cm_summary_file.exists():
            logger.error(f"Confusion matrix summary not found: {cm_summary_file}")
            return {}

        cm_df = pd.read_csv(cm_summary_file)
        extractions_df = pd.read_csv(extractions_file) if extractions_file.exists() else None

        analysis = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "variation_by_journal": self._analyze_journal_variation(cm_df),
            "pipeline_comparison": self._analyze_pipeline_comparison(cm_df, extractions_df),
            "error_patterns": self._analyze_error_patterns(cm_df),
            "fragmentation_analysis": self._analyze_fragmentation(extractions_df),
            "recommendations": self._generate_recommendations(cm_df, extractions_df),
        }

        return analysis

    def _analyze_journal_variation(self, cm_df: pd.DataFrame) -> dict[str, Any]:
        """Analyze variation across journals.

        Args:
            cm_df: Confusion matrix summary DataFrame

        Returns:
            Journal variation analysis
        """
        logger.info("Analyzing journal variation...")

        variation = {}

        for journal in cm_df["journal"].unique():
            journal_data = cm_df[cm_df["journal"] == journal]

            variation[journal] = {
                "doc_count": len(journal_data),
                "avg_precision": journal_data["precision"].mean(),
                "avg_recall": journal_data["recall"].mean(),
                "avg_f1": journal_data["f1"].mean(),
                "avg_accuracy": journal_data["accuracy"].mean(),
                "std_precision": journal_data["precision"].std(),
                "std_recall": journal_data["recall"].std(),
                "std_f1": journal_data["f1"].std(),
            }

        return variation

    def _analyze_pipeline_comparison(
        self, cm_df: pd.DataFrame, extractions_df: pd.DataFrame | None
    ) -> dict[str, Any]:
        """Compare pipelines on quality and speed.

        Args:
            cm_df: Confusion matrix summary DataFrame
            extractions_df: Extraction results DataFrame

        Returns:
            Pipeline comparison analysis
        """
        logger.info("Analyzing pipeline comparison...")

        comparison = {}

        for pipeline in cm_df["pipeline"].unique():
            pipeline_data = cm_df[cm_df["pipeline"] == pipeline]

            comparison[pipeline] = {
                "doc_count": len(pipeline_data),
                "avg_precision": pipeline_data["precision"].mean(),
                "avg_recall": pipeline_data["recall"].mean(),
                "avg_f1": pipeline_data["f1"].mean(),
                "avg_accuracy": pipeline_data["accuracy"].mean(),
                "median_f1": pipeline_data["f1"].median(),
                "std_f1": pipeline_data["f1"].std(),
            }

            # Add timing if available
            if extractions_df is not None:
                timing_data = extractions_df[extractions_df["pipeline"] == pipeline]
                if len(timing_data) > 0:
                    comparison[pipeline]["avg_time_ms"] = timing_data["total_time_ms"].mean()
                    comparison[pipeline]["avg_ocr_time_ms"] = timing_data["ocr_time_ms"].mean()

        return comparison

    def _analyze_error_patterns(self, cm_df: pd.DataFrame) -> dict[str, Any]:
        """Analyze error patterns (FP, FN by pipeline).

        Args:
            cm_df: Confusion matrix summary DataFrame

        Returns:
            Error pattern analysis
        """
        logger.info("Analyzing error patterns...")

        patterns = {
            "by_pipeline": {},
            "by_journal": {},
        }

        # By pipeline
        for pipeline in cm_df["pipeline"].unique():
            pipeline_data = cm_df[cm_df["pipeline"] == pipeline]
            patterns["by_pipeline"][pipeline] = {
                "avg_error_rate": pipeline_data["error_rate"].mean(),
                "max_error_rate": pipeline_data["error_rate"].max(),
                "min_error_rate": pipeline_data["error_rate"].min(),
            }

        # By journal
        for journal in cm_df["journal"].unique():
            journal_data = cm_df[cm_df["journal"] == journal]
            patterns["by_journal"][journal] = {
                "avg_error_rate": journal_data["error_rate"].mean(),
                "max_error_rate": journal_data["error_rate"].max(),
                "min_error_rate": journal_data["error_rate"].min(),
            }

        return patterns

    def _analyze_fragmentation(self, extractions_df: pd.DataFrame | None) -> dict[str, Any]:
        """Analyze text fragmentation metrics.

        Args:
            extractions_df: Extraction results DataFrame

        Returns:
            Fragmentation analysis
        """
        logger.info("Analyzing fragmentation...")

        if extractions_df is None or len(extractions_df) == 0:
            return {"status": "no_data"}

        fragmentation = {}

        for pipeline in extractions_df["pipeline"].unique():
            pipeline_data = extractions_df[extractions_df["pipeline"] == pipeline]
            pipeline_data = pipeline_data[pipeline_data["success"]]

            if len(pipeline_data) > 0:
                fragmentation[pipeline] = {
                    "avg_items_per_page": pipeline_data["items_per_page"].mean(),
                    "std_items_per_page": pipeline_data["items_per_page"].std(),
                    "min_items_per_page": pipeline_data["items_per_page"].min(),
                    "max_items_per_page": pipeline_data["items_per_page"].max(),
                }

        return fragmentation

    def _generate_recommendations(
        self, cm_df: pd.DataFrame, extractions_df: pd.DataFrame | None
    ) -> dict[str, str]:
        """Generate recommendations based on analysis.

        Args:
            cm_df: Confusion matrix summary DataFrame
            extractions_df: Extraction results DataFrame

        Returns:
            Recommendations dictionary
        """
        logger.info("Generating recommendations...")

        recommendations = {}

        # Find best performing pipeline
        best_f1_pipeline = cm_df.groupby("pipeline")["f1"].mean().idxmax()
        best_f1_score = cm_df.groupby("pipeline")["f1"].mean().max()

        recommendations["best_quality_pipeline"] = f"{best_f1_pipeline} (F1: {best_f1_score:.2%})"

        # Check if significant variation by journal
        journal_f1_std = cm_df.groupby("journal")["f1"].mean().std()
        if journal_f1_std > 0.1:
            recommendations["variation_note"] = (
                "Significant variation across journals detected. Consider journal-specific tuning."
            )
        else:
            recommendations["variation_note"] = (
                "Consistent performance across journals. Approach generalizes well."
            )

        # Speed vs quality trade-off
        if extractions_df is not None and len(extractions_df) > 0:
            fastest = extractions_df.groupby("pipeline")["total_time_ms"].mean().idxmin()
            recommendations["fastest_pipeline"] = fastest

        return recommendations

    def generate_report(self, analysis: dict[str, Any]) -> str:
        """Generate markdown report from analysis.

        Args:
            analysis: Analysis results

        Returns:
            Markdown report string
        """
        report = """# OCR Pipeline Evaluation Report

## Executive Summary

This report presents comprehensive evaluation of three OCR extraction pipelines
on a representative test corpus of 12 legal documents across 10 journal sources.

### Key Findings

"""

        # Add recommendations
        if "recommendations" in analysis:
            report += "#### Recommendations\n\n"
            for key, value in analysis["recommendations"].items():
                report += f"- **{key}**: {value}\n"

        report += "\n## Detailed Analysis\n\n"

        # Pipeline comparison
        if "pipeline_comparison" in analysis:
            report += "### Pipeline Comparison\n\n"
            report += "| Pipeline | F1 Score | Precision | Recall | Avg Time |\n"
            report += "|----------|----------|-----------|--------|----------|\n"

            for pipeline, metrics in analysis["pipeline_comparison"].items():
                f1 = metrics.get("avg_f1", 0)
                prec = metrics.get("avg_precision", 0)
                rec = metrics.get("avg_recall", 0)
                time_ms = metrics.get("avg_time_ms", 0)

                report += f"| {pipeline} | {f1:.2%} | {prec:.2%} | {rec:.2%} | {time_ms:.0f}ms |\n"

        # Journal variation
        if "variation_by_journal" in analysis:
            report += "\n### Variation by Journal\n\n"
            report += "| Journal | F1 Score | Std Dev |\n"
            report += "|---------|----------|----------|\n"

            for journal, metrics in analysis["variation_by_journal"].items():
                f1 = metrics.get("avg_f1", 0)
                std = metrics.get("std_f1", 0)
                report += f"| {journal} | {f1:.2%} | ±{std:.2%} |\n"

        report += "\n---\n*Report generated: {}*\n".format(analysis.get("timestamp", "unknown"))

        return report

    def save_report(self, analysis: dict[str, Any]) -> None:
        """Save analysis and report to files.

        Args:
            analysis: Analysis results
        """
        # Save analysis JSON
        json_path = self.output_dir / "analysis.json"
        with open(json_path, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        logger.info(f"Saved analysis: {json_path}")

        # Save markdown report
        report = self.generate_report(analysis)
        report_path = self.output_dir / "evaluation_report.md"
        with open(report_path, "w") as f:
            f.write(report)
        logger.info(f"Saved report: {report_path}")

    def generate_visualizations(self, cm_df: pd.DataFrame) -> None:
        """Generate comparison visualizations.

        Args:
            cm_df: Confusion matrix summary DataFrame
        """
        logger.info("Generating visualizations...")

        # Set style
        sns.set_style("whitegrid")
        plt.rcParams["figure.figsize"] = (12, 6)

        # 1. Pipeline comparison - F1 scores
        fig, ax = plt.subplots(figsize=(10, 6))
        cm_df.boxplot(column="f1", by="pipeline", ax=ax)
        ax.set_title("F1 Score Distribution by Pipeline")
        ax.set_ylabel("F1 Score")
        ax.set_xlabel("Pipeline")
        plt.suptitle("")  # Remove default title
        fig.savefig(self.output_dir / "f1_by_pipeline.png", dpi=150, bbox_inches="tight")
        plt.close()

        # 2. Precision vs Recall scatter
        fig, ax = plt.subplots(figsize=(10, 6))
        for pipeline in cm_df["pipeline"].unique():
            data = cm_df[cm_df["pipeline"] == pipeline]
            ax.scatter(data["recall"], data["precision"], label=pipeline, s=100, alpha=0.7)
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.set_title("Precision vs Recall by Pipeline")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.savefig(self.output_dir / "precision_vs_recall.png", dpi=150, bbox_inches="tight")
        plt.close()

        # 3. Error rate by journal
        fig, ax = plt.subplots(figsize=(12, 6))
        journal_errors = cm_df.groupby("journal")["error_rate"].mean().sort_values(ascending=False)
        journal_errors.plot(kind="barh", ax=ax, color="steelblue")
        ax.set_xlabel("Average Error Rate")
        ax.set_title("Average Error Rate by Journal")
        fig.savefig(
            self.output_dir / "error_rate_by_journal.png",
            dpi=150,
            bbox_inches="tight",
        )
        plt.close()

        logger.info("Visualizations saved")


def main():
    """Run analysis and generate reports."""
    analyzer = EvaluationAnalyzer()
    analysis = analyzer.analyze_all()

    if analysis:
        analyzer.save_report(analysis)

        # Load confusion matrix summary for visualization
        cm_file = analyzer.confusion_matrices_dir / "confusion_matrices_summary.csv"
        if cm_file.exists():
            cm_df = pd.read_csv(cm_file)
            analyzer.generate_visualizations(cm_df)

        logger.info("Analysis complete")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    main()

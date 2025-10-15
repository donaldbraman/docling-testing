#!/usr/bin/env python3
"""
Benchmark extraction framework with standardized metrics and reporting.

Runs multiple configurations on each document and produces comparable reports.
"""

import json
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    LayoutOptions,
    PdfPipelineOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

from extract_body_only import calculate_citation_density, is_likely_citation


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""

    name: str
    images_scale: float
    model_spec: str = "default"
    single_column_fallback: bool = False
    do_ocr: bool = True
    do_table_structure: bool = True


@dataclass
class BenchmarkMetrics:
    """Standardized metrics for comparison."""

    # Document metadata
    document_name: str
    file_size_mb: float

    # Configuration
    config_name: str
    images_scale: float
    model_spec: str
    single_column_fallback: bool

    # Processing metrics
    processing_time_seconds: float
    processing_time_minutes: float

    # Page metadata (from PDF if available)
    page_count: int

    # Label distribution
    label_counts: dict[str, int]
    total_items: int

    # Text metrics
    total_words: int
    body_words: int
    footnote_words: int
    removed_words: int
    removal_percentage: float

    # Citation detection
    citations_caught_by_heuristic: int
    high_density_paragraphs: int  # Paragraphs with >15% citation density

    # Quality metrics
    hyphenation_artifacts_total: int
    hyphenation_artifacts_body: int

    # Output sizes
    all_text_chars: int
    body_text_chars: int
    footnote_text_chars: int


def create_pipeline(config: BenchmarkConfig) -> PdfPipelineOptions:
    """Create pipeline from configuration."""

    if config.model_spec == "default":
        layout_opts = LayoutOptions()
    else:
        layout_opts = LayoutOptions()
        layout_opts.model_spec = config.model_spec
        layout_opts.single_column_fallback = config.single_column_fallback

    return PdfPipelineOptions(
        layout_options=layout_opts,
        generate_parsed_pages=True,
        generate_page_images=True,
        images_scale=config.images_scale,
        do_table_structure=config.do_table_structure,
        table_structure_options=dict(
            mode=TableFormerMode.ACCURATE,
            do_cell_matching=False,
        ),
        do_ocr=config.do_ocr,
    )


def extract_and_measure(pdf_path: Path, config: BenchmarkConfig) -> BenchmarkMetrics:
    """Extract document and collect comprehensive metrics."""

    print(f"\n{'=' * 80}")
    print(f"EXTRACTING: {pdf_path.name}")
    print(f"CONFIG: {config.name}")
    print(f"{'=' * 80}\n")

    start_time = time.time()

    # Create converter
    pipeline = create_pipeline(config)
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    # Convert document
    print("Converting document...")
    result = converter.convert(str(pdf_path))
    doc = result.document

    elapsed = time.time() - start_time

    # Extract and filter content
    label_counts = Counter()
    body_text_parts = []
    footnote_parts = []
    all_text_parts = []
    citations_caught = 0

    for item, level in doc.iterate_items():
        label = str(item.label) if hasattr(item, "label") else "NO_LABEL"
        label_counts[label] += 1

        text = item.text if hasattr(item, "text") else ""

        if text:
            all_text_parts.append(text)

            if "footnote" in label.lower():
                footnote_parts.append(text)
            elif is_likely_citation(text):
                footnote_parts.append(text)
                citations_caught += 1
            elif label.lower() in ["text", "section_header", "list_item", "paragraph"]:
                body_text_parts.append(text)

    # Create outputs
    all_text = "\n\n".join(all_text_parts)
    body_only = "\n\n".join(body_text_parts)
    footnotes_only = "\n\n".join(footnote_parts)

    # Calculate high-density paragraphs in body text
    body_paragraphs = [p.strip() for p in body_only.split("\n\n") if p.strip()]
    high_density = sum(
        1 for p in body_paragraphs if len(p) > 200 and calculate_citation_density(p) > 0.15
    )

    # Get page count (estimate from items if not available)
    page_count = len(result.pages) if hasattr(result, "pages") else 0

    # Build metrics
    metrics = BenchmarkMetrics(
        document_name=pdf_path.name,
        file_size_mb=round(pdf_path.stat().st_size / (1024 * 1024), 2),
        config_name=config.name,
        images_scale=config.images_scale,
        model_spec=config.model_spec,
        single_column_fallback=config.single_column_fallback,
        processing_time_seconds=round(elapsed, 2),
        processing_time_minutes=round(elapsed / 60, 2),
        page_count=page_count,
        label_counts=dict(label_counts),
        total_items=sum(label_counts.values()),
        total_words=len(all_text.split()),
        body_words=len(body_only.split()),
        footnote_words=len(footnotes_only.split()),
        removed_words=len(all_text.split()) - len(body_only.split()),
        removal_percentage=round(100 * (1 - len(body_only.split()) / len(all_text.split())), 2)
        if len(all_text.split()) > 0
        else 0,
        citations_caught_by_heuristic=citations_caught,
        high_density_paragraphs=high_density,
        hyphenation_artifacts_total=all_text.count("-\n"),
        hyphenation_artifacts_body=body_only.count("-\n"),
        all_text_chars=len(all_text),
        body_text_chars=len(body_only),
        footnote_text_chars=len(footnotes_only),
    )

    print(f"\n✅ Completed in {metrics.processing_time_minutes:.1f} min")
    print(f"   Body: {metrics.body_words:,} words")
    print(f"   Removed: {metrics.removed_words:,} words ({metrics.removal_percentage}%)")
    print(f"   Citations caught: {metrics.citations_caught_by_heuristic}")

    return metrics, body_only, footnotes_only


def generate_report(metrics: BenchmarkMetrics, output_path: Path):
    """Generate standardized markdown report."""

    report = f"""# Extraction Benchmark Report

## Document Information
- **File**: {metrics.document_name}
- **Size**: {metrics.file_size_mb} MB
- **Pages**: {metrics.page_count}

## Configuration
- **Name**: {metrics.config_name}
- **Image Scale**: {metrics.images_scale}x
- **Model**: {metrics.model_spec}
- **Single Column Fallback**: {metrics.single_column_fallback}

## Processing Performance
- **Time**: {metrics.processing_time_seconds}s ({metrics.processing_time_minutes:.2f} min)
- **Speed**: {metrics.page_count / metrics.processing_time_minutes if metrics.processing_time_minutes > 0 else 0:.1f} pages/min

## Label Distribution
| Label | Count |
|-------|-------|
"""

    # Sort labels by count
    for label, count in sorted(metrics.label_counts.items(), key=lambda x: -x[1])[:10]:
        report += f"| {label} | {count:,} |\n"

    report += f"""
**Total Items**: {metrics.total_items:,}

## Text Extraction Results
| Metric | Value |
|--------|-------|
| **Total Words** | {metrics.total_words:,} |
| **Body Words** | {metrics.body_words:,} |
| **Footnote Words** | {metrics.footnote_words:,} |
| **Words Removed** | {metrics.removed_words:,} ({metrics.removal_percentage}%) |

## Footnote Detection
| Metric | Value |
|--------|-------|
| **Labeled as Footnote** | {metrics.label_counts.get("footnote", 0):,} |
| **Caught by Heuristic** | {metrics.citations_caught_by_heuristic:,} |
| **Total Removed** | {metrics.footnote_words:,} words |

## Quality Metrics
| Metric | Value |
|--------|-------|
| **Hyphenation Artifacts (All)** | {metrics.hyphenation_artifacts_total} |
| **Hyphenation Artifacts (Body)** | {metrics.hyphenation_artifacts_body} |
| **High-Density Paragraphs (Body)** | {metrics.high_density_paragraphs} |

## Output Sizes
| Output | Characters |
|--------|-----------|
| **All Text** | {metrics.all_text_chars:,} |
| **Body Only** | {metrics.body_text_chars:,} |
| **Footnotes Only** | {metrics.footnote_text_chars:,} |

---
*Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}*
"""

    output_path.write_text(report, encoding="utf-8")
    print(f"\n📊 Report saved: {output_path}")


def main():
    """Run benchmark on all test documents with multiple configurations."""

    # Define configurations to test
    configs = [
        BenchmarkConfig(
            name="default",
            images_scale=1.0,
        ),
        BenchmarkConfig(
            name="2x_scale",
            images_scale=2.0,
        ),
        BenchmarkConfig(
            name="optimized",
            images_scale=2.0,
            model_spec="heron-101",
            single_column_fallback=True,
        ),
    ]

    # Get test documents
    base_dir = Path(__file__).parent
    test_corpus = base_dir / "test_corpus" / "law_reviews"
    pdfs = sorted(test_corpus.glob("*.pdf"))

    if not pdfs:
        print(f"❌ No PDFs found in {test_corpus}")
        return

    print(f"\n{'=' * 80}")
    print(f"BENCHMARK: {len(pdfs)} documents × {len(configs)} configurations")
    print(f"{'=' * 80}\n")

    print("Documents:")
    for pdf in pdfs:
        size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"  - {pdf.name} ({size_mb:.1f} MB)")

    print("\nConfigurations:")
    for config in configs:
        print(f"  - {config.name}: {config.images_scale}x scale, {config.model_spec}")

    # Create output directories
    results_dir = base_dir / "results" / "benchmarks"
    results_dir.mkdir(parents=True, exist_ok=True)

    reports_dir = base_dir / "results" / "benchmark_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Run benchmarks
    all_metrics = []

    for pdf in pdfs:
        for config in configs:
            try:
                metrics, body_text, footnotes = extract_and_measure(pdf, config)
                all_metrics.append(metrics)

                # Save outputs
                output_name = f"{pdf.stem}_{config.name}"
                (results_dir / f"{output_name}_body.txt").write_text(body_text, encoding="utf-8")
                (results_dir / f"{output_name}_footnotes.txt").write_text(
                    footnotes, encoding="utf-8"
                )

                # Generate report
                report_path = reports_dir / f"{output_name}_report.md"
                generate_report(metrics, report_path)

                # Save metrics as JSON
                metrics_path = results_dir / f"{output_name}_metrics.json"
                metrics_path.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")

            except Exception as e:
                print(f"\n❌ Error processing {pdf.name} with {config.name}: {e}")
                import traceback

                traceback.print_exc()

    # Generate comparison report
    generate_comparison_report(all_metrics, reports_dir / "comparison_report.md")

    print(f"\n{'=' * 80}")
    print("BENCHMARK COMPLETE")
    print(f"{'=' * 80}\n")
    print(f"Total runs: {len(all_metrics)}")
    print(f"Reports: {reports_dir}")
    print(f"Outputs: {results_dir}")


def generate_comparison_report(all_metrics: list[BenchmarkMetrics], output_path: Path):
    """Generate comparison report across all runs."""

    report = f"""# Extraction Benchmark Comparison

**Total Runs**: {len(all_metrics)}

## Summary by Document

"""

    # Group by document
    by_doc = {}
    for m in all_metrics:
        if m.document_name not in by_doc:
            by_doc[m.document_name] = []
        by_doc[m.document_name].append(m)

    for doc_name, metrics_list in sorted(by_doc.items()):
        report += f"### {doc_name}\n\n"
        report += "| Config | Time (min) | Body Words | Removed | % Removed | Citations Caught | High Density |\n"
        report += "|--------|-----------|------------|---------|-----------|-----------------|-------------|\n"

        for m in metrics_list:
            report += f"| {m.config_name} | {m.processing_time_minutes:.2f} | {m.body_words:,} | {m.removed_words:,} | {m.removal_percentage}% | {m.citations_caught_by_heuristic} | {m.high_density_paragraphs} |\n"

        report += "\n"

    report += """## Processing Speed Comparison

| Document | Config | Pages/Min | Total Time |
|----------|--------|-----------|------------|
"""

    for m in sorted(all_metrics, key=lambda x: (x.document_name, x.config_name)):
        pages_per_min = (
            m.page_count / m.processing_time_minutes if m.processing_time_minutes > 0 else 0
        )
        report += f"| {m.document_name} | {m.config_name} | {pages_per_min:.1f} | {m.processing_time_minutes:.2f} min |\n"

    report += "\n## Key Findings\n\n"

    # Calculate averages by config
    by_config = {}
    for m in all_metrics:
        if m.config_name not in by_config:
            by_config[m.config_name] = []
        by_config[m.config_name].append(m)

    for config_name, metrics_list in sorted(by_config.items()):
        avg_removal = sum(m.removal_percentage for m in metrics_list) / len(metrics_list)
        avg_citations = sum(m.citations_caught_by_heuristic for m in metrics_list) / len(
            metrics_list
        )
        avg_time = sum(m.processing_time_minutes for m in metrics_list) / len(metrics_list)

        report += f"**{config_name}**:\n"
        report += f"- Avg removal: {avg_removal:.1f}%\n"
        report += f"- Avg citations caught: {avg_citations:.0f}\n"
        report += f"- Avg processing time: {avg_time:.2f} min\n\n"

    report += f"""
---
*Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}*
"""

    output_path.write_text(report, encoding="utf-8")
    print(f"\n📊 Comparison report saved: {output_path}")


if __name__ == "__main__":
    main()

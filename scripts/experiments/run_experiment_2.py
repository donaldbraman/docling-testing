#!/usr/bin/env python3
"""
Experiment 2: Test 2x image scaling impact on footnote detection
Issue: https://github.com/donaldbraman/docling-testing/issues/2
"""

import json
from dataclasses import asdict
from pathlib import Path

from benchmark_extraction import (
    BenchmarkConfig,
    extract_and_measure,
    generate_comparison_report,
    generate_report,
)


def main():
    """Run Experiment 2: 2x image scaling configuration on all documents."""

    print(f"\n{'=' * 80}")
    print("EXPERIMENT 2: 2X IMAGE SCALING")
    print("Issue: https://github.com/donaldbraman/docling-testing/issues/2")
    print(f"{'=' * 80}\n")

    # Configuration for this experiment
    config = BenchmarkConfig(
        name="2x_scale",
        images_scale=2.0,  # ← Key change from Experiment 1
        model_spec="default",
        single_column_fallback=False,
    )

    print("Configuration:")
    print(f"  images_scale: {config.images_scale}x ← 2x baseline")
    print(f"  model_spec: {config.model_spec}")
    print(f"  single_column_fallback: {config.single_column_fallback}")
    print()
    print("Hypothesis: Higher DPI should improve footnote detection")
    print("Trade-off: Likely 2-3x slower processing")
    print()

    # Get test documents
    base_dir = Path(__file__).parent
    test_corpus = base_dir / "test_corpus" / "law_reviews"
    pdfs = sorted(test_corpus.glob("*.pdf"))

    print(f"Test corpus ({len(pdfs)} documents):")
    for pdf in pdfs:
        size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"  - {pdf.name} ({size_mb:.1f} MB)")
    print()

    # Create output directories
    results_dir = base_dir / "results" / "experiment_2"
    results_dir.mkdir(parents=True, exist_ok=True)

    reports_dir = base_dir / "results" / "experiment_2_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Run extraction on all documents
    all_metrics = []

    for i, pdf in enumerate(pdfs, 1):
        print(f"\n{'=' * 80}")
        print(f"DOCUMENT {i}/{len(pdfs)}: {pdf.name}")
        print(f"{'=' * 80}")

        try:
            metrics, body_text, footnotes = extract_and_measure(pdf, config)
            all_metrics.append(metrics)

            # Save outputs
            output_name = f"{pdf.stem}_2x_scale"
            (results_dir / f"{output_name}_body.txt").write_text(body_text, encoding="utf-8")
            (results_dir / f"{output_name}_footnotes.txt").write_text(footnotes, encoding="utf-8")

            # Generate report
            report_path = reports_dir / f"{output_name}_report.md"
            generate_report(metrics, report_path)

            # Save metrics as JSON
            metrics_path = results_dir / f"{output_name}_metrics.json"
            metrics_path.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")

        except Exception as e:
            print(f"\n❌ Error processing {pdf.name}: {e}")
            import traceback

            traceback.print_exc()

    # Generate comparison report
    if all_metrics:
        comparison_path = reports_dir / "experiment_2_summary.md"
        generate_comparison_report(all_metrics, comparison_path)

        print(f"\n{'=' * 80}")
        print("EXPERIMENT 2 COMPLETE")
        print(f"{'=' * 80}\n")
        print(f"✅ Processed {len(all_metrics)}/{len(pdfs)} documents successfully")
        print(f"\n📊 Reports: {reports_dir}")
        print(f"📁 Results: {results_dir}")
        print(f"\n🔗 View results: {reports_dir / 'experiment_2_summary.md'}")
        print("\n💡 Next: Compare with Experiment 1 baseline using compare_body_text.py")


if __name__ == "__main__":
    main()

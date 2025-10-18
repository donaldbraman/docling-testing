#!/usr/bin/env python3
"""Quick test of benchmark framework on smallest document."""

from pathlib import Path

from benchmark_extraction import (
    BenchmarkConfig,
    extract_and_measure,
    generate_report,
)


def main():
    """Test on Nedrud (smallest document) with default config."""

    base_dir = Path(__file__).parent
    test_pdf = base_dir / "test_corpus" / "law_reviews" / "Nedrud_1964.pdf"

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return

    config = BenchmarkConfig(
        name="default",
        images_scale=1.0,
    )

    print("\n🧪 TESTING BENCHMARK FRAMEWORK")
    print(f"   Document: {test_pdf.name} (smallest)")
    print(f"   Config: {config.name}\n")

    try:
        metrics, body_text, footnotes = extract_and_measure(test_pdf, config)

        # Save outputs
        results_dir = base_dir / "results" / "benchmark_test"
        results_dir.mkdir(parents=True, exist_ok=True)

        (results_dir / "body.txt").write_text(body_text, encoding="utf-8")
        (results_dir / "footnotes.txt").write_text(footnotes, encoding="utf-8")

        # Generate report
        report_path = results_dir / "report.md"
        generate_report(metrics, report_path)

        print(f"\n{'=' * 80}")
        print("TEST RESULTS")
        print(f"{'=' * 80}\n")
        print("✅ Framework validated successfully!")
        print(f"   Processing time: {metrics.processing_time_minutes:.2f} min")
        print(f"   Body words: {metrics.body_words:,}")
        print(f"   Removed: {metrics.removal_percentage}%")
        print(f"\n📁 Test outputs: {results_dir}")
        print("\n💡 Ready to run full benchmark on all 3 documents × 3 configs")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

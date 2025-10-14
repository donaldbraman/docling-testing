#!/usr/bin/env python3
"""Test the improved citation detection on Jackson_2014.pdf with default config only."""

from pathlib import Path
from extract_body_only import extract_body_text


def main():
    """Run extraction with improved citation detection."""

    base_dir = Path(__file__).parent
    test_corpus = base_dir / "test_corpus" / "law_reviews"
    output_dir = base_dir / "results" / "body_extraction"
    output_dir.mkdir(parents=True, exist_ok=True)

    test_pdf = test_corpus / "Jackson_2014.pdf"

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return

    print(f"\n🔬 TESTING IMPROVED CITATION DETECTION")
    print(f"Test document: {test_pdf.name}")
    print(f"Configuration: default (with improved citation detection)")
    print()

    try:
        metrics = extract_body_text(test_pdf, output_dir, config="default")

        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}\n")
        print(f"✅ Extraction completed successfully!")
        print(f"   Citations caught by heuristic: {metrics['citations_caught']}")
        print(f"   Body text: {metrics['body_text_words']:,} words")
        print(f"   Footnotes removed: {metrics['footnote_text_words']:,} words")
        print(f"\n📁 Output: {output_dir / f'{test_pdf.stem}_default_body_only.txt'}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

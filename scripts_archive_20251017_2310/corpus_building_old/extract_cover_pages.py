#!/usr/bin/env python3
"""
Extract cover pages from Zotero PDFs and add to training corpus.

Uses existing cover detection patterns to identify HeinOnline, JSTOR, etc.
Extracts first page text and labels paragraphs as cover_page type.
"""

import re
from pathlib import Path

import pandas as pd
from docling.document_converter import DocumentConverter


def detect_cover_type(text: str) -> str | None:
    """Detect cover page type using pattern matching.

    Returns cover type or None if not a cover page.
    """
    # HeinOnline cover
    heinonline_patterns = [
        r"Downloaded from HeinOnline",
        r"SOURCE: Content Downloaded",
        r"Citations:",
        r"Bluebook.*ed\.",
        r"ALWD.*ed\.",
        r"https://heinonline\.org",
    ]
    if sum(1 for p in heinonline_patterns if re.search(p, text, re.I)) >= 2:
        return "heinonline"

    # JSTOR cover
    jstor_patterns = [
        r"JSTOR",
        r"www\.jstor\.org",
        r"accessed.*jstor",
        r"Your use of.*JSTOR",
        r"Terms and Conditions of Use",
        r"JSTOR is a not-for-profit",
    ]
    if sum(1 for p in jstor_patterns if re.search(p, text, re.I)) >= 2:
        return "jstor"

    # Westlaw cover
    westlaw_patterns = [
        r"Westlaw",
        r"Thomson Reuters",
        r"West Reporter",
        r"For the convenience of the user",
        r"Reproduced with permission",
    ]
    if sum(1 for p in westlaw_patterns if re.search(p, text, re.I)) >= 2:
        return "westlaw"

    # LexisNexis cover
    lexisnexis_patterns = [
        r"LexisNexis",
        r"Lexis Advance",
        r"Matthew Bender",
        r"Copyright.*LexisNexis",
    ]
    if sum(1 for p in lexisnexis_patterns if re.search(p, text, re.I)) >= 2:
        return "lexisnexis"

    return None


def extract_cover_pages(pdf_dir: Path) -> list[dict]:
    """Extract cover pages from PDFs and label paragraphs.

    Args:
        pdf_dir: Directory containing PDFs

    Returns:
        List of dicts with 'text', 'label', 'source' keys
    """
    converter = DocumentConverter()
    cover_samples = []

    stats = {
        "total_pdfs": 0,
        "heinonline": 0,
        "jstor": 0,
        "westlaw": 0,
        "lexisnexis": 0,
        "no_cover": 0,
        "total_paragraphs": 0,
    }

    print("Extracting cover pages from PDFs...")
    print("=" * 60)

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        stats["total_pdfs"] += 1

        try:
            # Extract first page with docling
            result = converter.convert(pdf_path)
            doc_md = result.document.export_to_markdown()

            # Get first page worth of text (approximate)
            lines = doc_md.split("\n")
            first_page_lines = lines[:100]  # Rough first page estimate
            first_page_text = "\n".join(first_page_lines)

            # Detect cover type
            cover_type = detect_cover_type(first_page_text)

            if cover_type:
                stats[cover_type] = stats.get(cover_type, 0) + 1

                # Split into paragraphs
                paragraphs = [p.strip() for p in first_page_text.split("\n\n") if p.strip()]

                # Filter out very short paragraphs (< 20 chars)
                paragraphs = [p for p in paragraphs if len(p) >= 20]

                for para in paragraphs:
                    cover_samples.append(
                        {
                            "text": para,
                            "label": f"cover_{cover_type}",
                            "source": pdf_path.name,
                            "extraction_method": "pdf_first_page",
                        }
                    )
                    stats["total_paragraphs"] += 1

                print(f"✓ {cover_type:15s} {pdf_path.name[:50]}")
            else:
                stats["no_cover"] += 1
                print(f"  (no cover)       {pdf_path.name[:50]}")

        except Exception as e:
            print(f"✗ Error with {pdf_path.name}: {e}")

    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Total PDFs scanned:        {stats['total_pdfs']}")
    print(f"  HeinOnline covers:       {stats['heinonline']}")
    print(f"  JSTOR covers:            {stats['jstor']}")
    print(f"  Westlaw covers:          {stats['westlaw']}")
    print(f"  LexisNexis covers:       {stats['lexisnexis']}")
    print(f"  No cover:                {stats['no_cover']}")
    print(f"\nTotal cover paragraphs:    {stats['total_paragraphs']}")
    print(
        f"Average paragraphs/cover:  {stats['total_paragraphs'] / (stats['total_pdfs'] - stats['no_cover']):.1f}"
    )

    return cover_samples


def main():
    """Extract cover pages and add to corpus."""
    # Paths
    base_dir = Path(__file__).parent
    pdf_dir = Path("/Users/donaldbraman/Documents/GitHub/12-factor-agents/test_corpus/pdfs")
    corpus_path = base_dir / "data" / "labeled_pdf_corpus.csv"
    output_path = base_dir / "data" / "cover_pages_corpus.csv"

    if not pdf_dir.exists():
        print(f"Error: PDF directory not found: {pdf_dir}")
        return

    # Extract cover pages
    cover_samples = extract_cover_pages(pdf_dir)

    if not cover_samples:
        print("\nNo cover pages found!")
        return

    # Save as CSV
    df_covers = pd.DataFrame(cover_samples)
    df_covers.to_csv(output_path, index=False)

    print(f"\n✓ Cover page corpus saved to: {output_path}")
    print(f"  {len(df_covers)} paragraphs")

    # Show label distribution
    print("\nLabel Distribution:")
    print(df_covers["label"].value_counts())

    # Check if we should merge with existing corpus
    if corpus_path.exists():
        df_existing = pd.read_csv(corpus_path)
        print(f"\n📊 Existing corpus: {len(df_existing)} paragraphs")
        print(f"   Footnotes:       {len(df_existing[df_existing['html_label'] == 'footnote'])}")
        print(f"   Body text:       {len(df_existing[df_existing['html_label'] == 'body_text'])}")

        # Ask about merging
        print(f"\n📦 New covers:      {len(df_covers)} paragraphs")
        print("\nTo create multi-class corpus, run:")
        print("  python merge_corpus.py")


if __name__ == "__main__":
    main()

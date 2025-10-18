#!/usr/bin/env python3
"""
Contextual inspection: Check if tables/captions from PDFs exist in HTML.

Strategy:
1. Load full_docling_corpus.csv (once extraction completes)
2. Find paragraphs labeled as 'caption' or 'table'
3. For each, search for surrounding text in corresponding HTML file
4. Report findings: Do HTML sources contain this information?
"""

import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-\s+", "", text)
    return text.strip().lower()


def find_in_html(target_text: str, html_file: Path, context_chars=100) -> bool:
    """
    Search for target text (or its context) in HTML file.

    Returns True if found, False otherwise.
    """
    if not html_file.exists():
        return None  # HTML file doesn't exist

    try:
        with open(html_file, encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        html_text = normalize_text(soup.get_text())
        target_normalized = normalize_text(target_text)

        # Try exact match first
        if target_normalized in html_text:
            return True

        # Try partial match (first 50 chars)
        if len(target_normalized) > 50:
            partial = target_normalized[:50]
            if partial in html_text:
                return True

        return False

    except Exception as e:
        print(f"Error reading {html_file.name}: {e}")
        return None


def main():
    """Inspect captions and tables from Docling extraction."""
    base_dir = Path(__file__).parent

    # Load full Docling corpus
    corpus_path = base_dir / "data" / "full_docling_corpus.csv"

    if not corpus_path.exists():
        print(f"❌ Corpus not found: {corpus_path}")
        print("Run extract_all_docling_labels.py first")
        return

    print("=" * 80)
    print("CONTEXTUAL INSPECTION: Tables & Captions in HTML")
    print("=" * 80)

    df = pd.read_csv(corpus_path)
    print(f"\nLoaded {len(df):,} paragraphs from Docling extraction")

    # Filter for captions and tables
    captions = df[df["docling_label"].str.contains("caption", case=False, na=False)]
    tables = df[df["docling_label"].str.contains("table", case=False, na=False)]

    print("\nFound:")
    print(f"  {len(captions):3d} captions")
    print(f"  {len(tables):3d} tables")

    if len(captions) == 0 and len(tables) == 0:
        print("\n⚠️  No captions or tables found in Docling extraction!")
        return

    # Check captions
    if len(captions) > 0:
        print("\n" + "=" * 80)
        print("CHECKING CAPTIONS IN HTML")
        print("=" * 80)

        html_dir = base_dir / "data" / "raw_html"
        found_count = 0
        not_found_count = 0
        no_html_count = 0

        for idx, row in captions.head(20).iterrows():  # Check first 20
            source_pdf = row["source"]
            caption_text = row["text"]

            # Derive HTML filename
            html_file = html_dir / source_pdf.replace(".pdf", ".html")

            result = find_in_html(caption_text, html_file)

            if result is None:
                no_html_count += 1
                status = "NO_HTML"
            elif result:
                found_count += 1
                status = "✓ FOUND"
            else:
                not_found_count += 1
                status = "✗ NOT_FOUND"

            print(f"\n{status}: {source_pdf}")
            print(f"  Caption: {caption_text[:100]}...")

        print("\n" + "=" * 80)
        print("Caption Results (first 20):")
        print(f"  ✓ Found in HTML:     {found_count}")
        print(f"  ✗ Not found in HTML: {not_found_count}")
        print(f"  ⚠️  No HTML file:     {no_html_count}")

    # Check tables
    if len(tables) > 0:
        print("\n" + "=" * 80)
        print("CHECKING TABLES IN HTML")
        print("=" * 80)

        html_dir = base_dir / "data" / "raw_html"
        found_count = 0
        not_found_count = 0
        no_html_count = 0

        for idx, row in tables.head(20).iterrows():  # Check first 20
            source_pdf = row["source"]
            table_text = row["text"]

            # Derive HTML filename
            html_file = html_dir / source_pdf.replace(".pdf", ".html")

            result = find_in_html(table_text, html_file)

            if result is None:
                no_html_count += 1
                status = "NO_HTML"
            elif result:
                found_count += 1
                status = "✓ FOUND"
            else:
                not_found_count += 1
                status = "✗ NOT_FOUND"

            print(f"\n{status}: {source_pdf}")
            print(f"  Table: {table_text[:100]}...")

        print("\n" + "=" * 80)
        print("Table Results (first 20):")
        print(f"  ✓ Found in HTML:     {found_count}")
        print(f"  ✗ Not found in HTML: {not_found_count}")
        print(f"  ⚠️  No HTML file:     {no_html_count}")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("\nIf captions/tables are FOUND in HTML:")
    print("  → We can extract them for high-quality ground truth!")
    print("\nIf captions/tables are NOT FOUND in HTML:")
    print("  → Must trust Docling's layout analysis for these classes")


if __name__ == "__main__":
    main()

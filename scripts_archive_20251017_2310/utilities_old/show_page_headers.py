#!/usr/bin/env python3
"""Show first and last lines from each PDF page to identify headers/footers."""

import json
import re
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

CACHE_DIR = Path("data/extraction_cache")


def normalize_text(text: str) -> str:
    """Normalize text."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-\s+", "", text)
    text = re.sub(r'["' '"]', '"', text)
    text = re.sub(r"[–—]", "-", text)
    return text.strip()


def get_cache_path(pdf_path: Path) -> Path:
    """Get cache path for page structure."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{pdf_path.stem}_pages.json"


def is_cache_valid(cache_path: Path, source_path: Path) -> bool:
    """Check if cache is newer than source."""
    if not cache_path.exists():
        return False
    return cache_path.stat().st_mtime > source_path.stat().st_mtime


def extract_page_structure(pdf_path: Path):
    """Extract first and last lines from each page (with caching)."""
    cache_path = get_cache_path(pdf_path)

    # Try cache first
    if is_cache_valid(cache_path, pdf_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                print("  (loaded from cache)")
                return json.load(f)
        except Exception:
            pass
    pipeline = PdfPipelineOptions(
        layout_options=LayoutOptions(),
        generate_parsed_pages=True,
        generate_page_images=True,
        images_scale=1.0,
    )

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    try:
        result = converter.convert(str(pdf_path))
    except Exception as e:
        print(f"Error converting PDF: {e}")
        return []

    # Extract text by page - iterate through all items and group by page
    pages = {}

    for item, _level in result.document.iterate_items():
        if hasattr(item, "text") and item.text and hasattr(item, "prov"):
            text = normalize_text(item.text)
            if len(text) > 10:  # Min length
                # Get page number from provenance
                for prov in item.prov:
                    if hasattr(prov, "page_no"):
                        page_num = prov.page_no
                        if page_num not in pages:
                            pages[page_num] = []
                        pages[page_num].append(text)
                        break

    # Convert to list format with first/last lines
    page_list = []
    for page_num in sorted(pages.keys()):
        page_items = pages[page_num]
        if page_items:
            page_list.append(
                {
                    "page_num": page_num,
                    "first_line": page_items[0],
                    "last_line": page_items[-1],
                    "total_items": len(page_items),
                }
            )

    # Save to cache
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(page_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  ⚠️  Failed to save cache: {e}")

    return page_list


def analyze_pdf(pdf_path: Path, basename: str, max_pages: int = 10):
    """Analyze headers/footers in a PDF."""
    print(f"\n{'=' * 80}")
    print(f"PDF: {basename}")
    print(f"{'=' * 80}\n")

    pages = extract_page_structure(pdf_path)

    if not pages:
        print("No pages extracted")
        return

    print(f"Total pages: {len(pages)}\n")
    print(f"Showing first {min(max_pages, len(pages))} pages:\n")

    for page_info in pages[:max_pages]:
        print(f"Page {page_info['page_num']} ({page_info['total_items']} items):")
        print(f"  FIRST: {page_info['first_line'][:150]}")
        if len(page_info["first_line"]) > 150:
            print(f"         {...}")
        print(f"  LAST:  {page_info['last_line'][:150]}")
        if len(page_info["last_line"]) > 150:
            print(f"         {...}")
        print()

    # Look for repeated first lines (headers)
    first_lines = [p["first_line"] for p in pages]
    from collections import Counter

    first_line_counts = Counter(first_lines)

    repeated_headers = [(line, count) for line, count in first_line_counts.items() if count > 1]

    if repeated_headers:
        print("\n🔍 REPEATED FIRST LINES (likely headers):")
        print("=" * 80)
        for line, count in sorted(repeated_headers, key=lambda x: -x[1]):
            print(f"  [{count}x] {line[:100]}")
            if len(line) > 100:
                print(f"        {...}")
    else:
        print("\n✅ No repeated first lines found")

    # Look for repeated last lines (footers)
    last_lines = [p["last_line"] for p in pages]
    last_line_counts = Counter(last_lines)

    repeated_footers = [(line, count) for line, count in last_line_counts.items() if count > 1]

    if repeated_footers:
        print("\n🔍 REPEATED LAST LINES (likely footers):")
        print("=" * 80)
        for line, count in sorted(repeated_footers, key=lambda x: -x[1]):
            print(f"  [{count}x] {line[:100]}")
            if len(line) > 100:
                print(f"        {...}")
    else:
        print("\n✅ No repeated last lines found")


def analyze_corpus():
    """Analyze headers/footers in corpus PDFs."""
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    if not html_dir.exists() or not pdf_dir.exists():
        print("❌ Directories not found")
        return

    # Only analyze PDFs that have matching HTML files
    html_files = sorted(html_dir.glob("*.html"))
    corpus_pairs = []

    for html_file in html_files:
        pdf_file = pdf_dir / html_file.with_suffix(".pdf").name
        if pdf_file.exists():
            corpus_pairs.append((html_file, pdf_file))

    print("🔍 ANALYZING PDF PAGE HEADERS/FOOTERS (CORPUS ONLY)")
    print(f"Found {len(corpus_pairs)} corpus pairs\n")
    print(f"Cache: {CACHE_DIR}\n")

    # Analyze all corpus PDFs
    for _html_file, pdf_file in corpus_pairs:
        analyze_pdf(pdf_file, pdf_file.stem, max_pages=15)


if __name__ == "__main__":
    analyze_corpus()

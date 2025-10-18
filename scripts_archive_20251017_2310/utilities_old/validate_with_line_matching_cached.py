#!/usr/bin/env python3
"""Validate corpus using line-level fuzzy matching with RapidFuzz (with caching)."""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from rapidfuzz import fuzz

CACHE_DIR = Path("data/extraction_cache")


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)  # Collapse whitespace
    text = re.sub(r"-\s+", "", text)  # Remove line-break hyphens
    text = re.sub(r'[""' "]", '"', text)  # Normalize quotes
    text = re.sub(r"[–—]", "-", text)  # Normalize dashes
    return text.strip()


def get_cache_path(file_path: Path, cache_type: str) -> Path:
    """Get cache file path for a given file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_name = f"{file_path.stem}_{cache_type}.json"
    return CACHE_DIR / cache_name


def is_cache_valid(cache_path: Path, source_path: Path) -> bool:
    """Check if cache is newer than source file."""
    if not cache_path.exists():
        return False
    return cache_path.stat().st_mtime > source_path.stat().st_mtime


def extract_lines_from_pdf(pdf_path: Path) -> list[str]:
    """Extract lines from PDF using training pipeline settings (with caching)."""
    cache_path = get_cache_path(pdf_path, "pdf_lines")

    # Try to load from cache
    if is_cache_valid(cache_path, pdf_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass  # Cache corrupted, re-extract

    # Extract from PDF
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
        print(f"  ⚠️  Error converting PDF: {e}")
        return []

    # Extract paragraphs first
    paragraphs = []
    for item, _level in result.document.iterate_items():
        if hasattr(item, "text") and item.text:
            text = normalize_text(item.text)
            if len(text) > 20:
                paragraphs.append(text)

    # Break paragraphs into lines (sentences)
    lines = []
    for para in paragraphs:
        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", para)
        for sent in sentences:
            sent = sent.strip()
            # Filter: min 20 words, not mostly numbers
            words = sent.split()
            if len(words) >= 20:
                # Check if not mostly numbers/citations (>30% digits)
                text_only = re.sub(r"[^a-zA-Z]", "", sent)
                if len(text_only) > len(sent) * 0.7:
                    lines.append(sent)

    # Save to cache
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(lines, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  ⚠️  Failed to save cache: {e}")

    return lines


def extract_text_from_html(html_path: Path) -> str:
    """Extract all text from HTML (with caching)."""
    cache_path = get_cache_path(html_path, "html_text")

    # Try to load from cache
    if is_cache_valid(cache_path, html_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
                return data["text"]
        except Exception:
            pass  # Cache corrupted, re-extract

    # Extract from HTML
    try:
        with open(html_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except Exception as e:
        print(f"  ⚠️  Error reading HTML: {e}")
        return ""

    # Remove script and style
    for script in soup(["script", "style"]):
        script.decompose()

    # Get all text
    text = soup.get_text(separator=" ", strip=True)
    text = normalize_text(text)

    # Save to cache
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"text": text, "length": len(text)}, f, ensure_ascii=False)
    except Exception as e:
        print(f"  ⚠️  Failed to save cache: {e}")

    return text


def match_line_in_html(pdf_line: str, html_text: str, threshold: float = 0.85):
    """
    Match PDF line in HTML using fuzzy matching.

    Returns:
        matched: bool
        score: float (0-1)
        position: int (position in HTML text, or -1)
        method: str ("exact" or "fuzzy")
    """
    norm_pdf = normalize_text(pdf_line)
    norm_html = html_text  # Already normalized

    # Stage 1: Exact match
    if norm_pdf in norm_html:
        pos = norm_html.find(norm_pdf)
        return True, 1.0, pos, "exact"

    # Stage 2: Fuzzy match with sliding window
    best_score = 0.0
    best_pos = -1
    window_size = int(len(norm_pdf) * 1.2)
    stride = 100  # Check every 100 chars for speed

    for i in range(0, len(norm_html) - window_size, stride):
        window = norm_html[i : i + window_size]
        score = fuzz.ratio(norm_pdf, window) / 100.0

        if score > best_score:
            best_score = score
            best_pos = i

        # Early termination
        if score >= 0.95:
            break

    if best_score >= threshold:
        return True, best_score, best_pos, "fuzzy"

    return False, best_score, -1, "no_match"


def validate_pair(html_path: Path, pdf_path: Path, basename: str):
    """Validate a single HTML-PDF pair using line matching."""
    print(f"\n{basename}")
    print("-" * 70)

    # Extract lines from PDF (cached)
    print("  Extracting lines from PDF...")
    pdf_lines = extract_lines_from_pdf(pdf_path)
    if not pdf_lines:
        print("    ⚠️  No PDF lines extracted")
        return None
    print(f"    {len(pdf_lines)} lines")

    # Extract text from HTML (cached)
    print("  Extracting text from HTML...")
    html_text = extract_text_from_html(html_path)
    if not html_text:
        print("    ⚠️  No HTML text extracted")
        return None
    html_words = len(html_text.split())
    print(f"    {html_words:,} words")

    # Match lines
    print("  Matching lines...")
    matches = []
    unmatched_lines = []

    for idx, line in enumerate(pdf_lines):
        matched, score, pos, method = match_line_in_html(line, html_text)

        if matched:
            matches.append({"line": line, "score": score, "pos": pos, "method": method})
        else:
            unmatched_lines.append({"line": line, "score": score})

    # Calculate metrics
    match_count = len(matches)
    total_lines = len(pdf_lines)
    match_rate = (match_count / total_lines * 100) if total_lines > 0 else 0

    exact_matches = [m for m in matches if m["method"] == "exact"]
    fuzzy_matches = [m for m in matches if m["method"] == "fuzzy"]

    avg_score = sum(m["score"] for m in matches) / len(matches) if matches else 0

    # Check sequential pattern (positions should be mostly increasing)
    positions = [m["pos"] for m in matches]
    sequential_count = sum(1 for i in range(len(positions) - 1) if positions[i + 1] > positions[i])
    sequential_rate = (sequential_count / (len(positions) - 1) * 100) if len(positions) > 1 else 0

    # Report
    print("\n  Results:")
    print(f"    Total PDF lines:       {total_lines}")
    print(f"    Matched lines:         {match_count} ({match_rate:.1f}%)")
    print(
        f"      - Exact matches:     {len(exact_matches)} ({len(exact_matches) / total_lines * 100:.1f}%)"
    )
    print(
        f"      - Fuzzy matches:     {len(fuzzy_matches)} ({len(fuzzy_matches) / total_lines * 100:.1f}%)"
    )
    print(f"    Average match score:   {avg_score:.1%}")
    print(f"    Sequential pattern:    {sequential_rate:.1f}% sequential")

    # Show sample unmatched lines
    if unmatched_lines:
        print("\n  Sample unmatched lines (first 5):")
        for i, item in enumerate(unmatched_lines[:5], 1):
            line_preview = item["line"][:80] + "..." if len(item["line"]) > 80 else item["line"]
            print(f"    {i}. (score: {item['score']:.2f}) {line_preview}")

    # Status
    status = "✅ PASS" if match_rate >= 75 else "❌ FAIL"
    print(f"\n  Status: {status}")

    return {
        "basename": basename,
        "total_lines": total_lines,
        "matched": match_count,
        "match_rate": match_rate,
        "exact_matches": len(exact_matches),
        "fuzzy_matches": len(fuzzy_matches),
        "avg_score": avg_score,
        "sequential_rate": sequential_rate,
        "unmatched_samples": unmatched_lines[:10],
        "status": "PASS" if match_rate >= 75 else "FAIL",
    }


def validate_corpus():
    """Validate all pairs in data/raw_html and data/raw_pdf."""
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    if not html_dir.exists() or not pdf_dir.exists():
        print("❌ Corpus directories not found: data/raw_html/ or data/raw_pdf/")
        return

    # Find all HTML files
    html_files = sorted(html_dir.glob("*.html"))

    print("🔍 Validating corpus with line-level fuzzy matching (RapidFuzz + Caching)")
    print(f"Found {len(html_files)} HTML files in corpus")
    print(f"Cache directory: {CACHE_DIR}\n")
    print("=" * 70)

    results = []
    errors = []

    for html_file in html_files:
        # Find corresponding PDF
        pdf_file = pdf_dir / html_file.with_suffix(".pdf").name

        if not pdf_file.exists():
            errors.append(f"Missing PDF for: {html_file.name}")
            continue

        basename = html_file.stem
        result = validate_pair(html_file, pdf_file, basename)

        if result:
            results.append(result)
        else:
            errors.append(f"Extraction failed: {basename}")

    # Summary
    print(f"\n\n{'=' * 70}")
    print("CORPUS VALIDATION SUMMARY (LINE-LEVEL MATCHING)")
    print(f"{'=' * 70}\n")

    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]

    print(f"✅ PASSED (≥75% line match rate): {len(passed)}")
    for r in sorted(passed, key=lambda x: x["match_rate"], reverse=True):
        print(
            f"   {r['match_rate']:5.1f}% ({r['matched']:3d}/{r['total_lines']:3d}) "
            f"[E:{r['exact_matches']:3d} F:{r['fuzzy_matches']:3d}] "
            f"seq:{r['sequential_rate']:4.0f}% - {r['basename']}"
        )

    if failed:
        print(f"\n❌ FAILED (<75% line match rate): {len(failed)}")
        for r in sorted(failed, key=lambda x: x["match_rate"]):
            print(
                f"   {r['match_rate']:5.1f}% ({r['matched']:3d}/{r['total_lines']:3d}) "
                f"[E:{r['exact_matches']:3d} F:{r['fuzzy_matches']:3d}] "
                f"seq:{r['sequential_rate']:4.0f}% - {r['basename']}"
            )

    if errors:
        print(f"\n⚠️  ERRORS: {len(errors)}")
        for error in errors:
            print(f"   {error}")

    if passed:
        avg_match_rate = sum(r["match_rate"] for r in passed) / len(passed)
        avg_score = sum(r["avg_score"] for r in passed) / len(passed)
        avg_sequential = sum(r["sequential_rate"] for r in passed) / len(passed)
        print("\n📊 Passed pairs average:")
        print(f"   Match rate:    {avg_match_rate:.1f}%")
        print(f"   Match score:   {avg_score:.1%}")
        print(f"   Sequential:    {avg_sequential:.1f}%")

    print(f"\n{'=' * 70}")
    print(f"OVERALL: {len(passed)}/{len(results)} pairs passed validation")

    if failed:
        print(f"\n⚠️  RECOMMENDATION: Review {len(failed)} failed pairs")
        print("   Failed pairs may have abstract-only HTML or extraction issues")

    print(f"\n💾 Extraction cache saved to: {CACHE_DIR}")
    print("   Subsequent runs will be much faster!")

    return results


if __name__ == "__main__":
    validate_corpus()

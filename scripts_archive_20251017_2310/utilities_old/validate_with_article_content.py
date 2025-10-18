#!/usr/bin/env python3
"""Validate corpus using article-only HTML content with token-level fuzzy matching."""

import json
import re
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from rapidfuzz import fuzz

CACHE_DIR = Path("data/extraction_cache")
LABELED_HTML_DIR = Path("data/labeled_html")
REVIEW_DIR = Path("data/validation_review_article_only")


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)  # Collapse whitespace
    text = re.sub(r"-\s+", "", text)  # Remove line-break hyphens
    text = re.sub(r'["' '"]', '"', text)  # Normalize quotes
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
                cached = json.load(f)
                print("    (loaded from cache)")
                return cached
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


def load_labeled_html(basename: str) -> str:
    """Load labeled HTML paragraphs and join into normalized text."""
    labeled_file = LABELED_HTML_DIR / f"{basename}.json"

    if not labeled_file.exists():
        print(f"    ⚠️  Labeled HTML not found: {labeled_file}")
        return ""

    try:
        with open(labeled_file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"    ⚠️  Error loading labeled HTML: {e}")
        return ""

    # Join all paragraph text (already normalized during extraction)
    paragraphs = data.get("paragraphs", [])
    text = " ".join(p["text"] for p in paragraphs)

    print(f"    (loaded {len(paragraphs)} paragraphs from labeled HTML)")
    return text


def match_line_with_token_fuzzy(
    pdf_line: str,
    html_text: str,
    token_threshold: float = 0.80,
    line_threshold: float = 0.80,
):
    """
    Match PDF line in HTML using token-level fuzzy matching.

    Returns:
        matched: bool
        score: float (0-1)
        position: int (position in HTML text, or -1)
        method: str ("exact", "token_fuzzy", or "no_match")
        details: dict with token-level stats
    """
    norm_pdf = normalize_text(pdf_line)
    norm_html = html_text  # Already normalized

    # Stage 1: Exact match (fast optimization)
    if norm_pdf in norm_html:
        pos = norm_html.find(norm_pdf)
        return True, 1.0, pos, "exact", {}

    # Stage 2: Token-level fuzzy matching with sliding window
    pdf_tokens = norm_pdf.split()
    best_score = 0.0
    best_pos = -1
    best_details = {}

    # Window size: 1.5x PDF line length to allow for OCR errors
    window_size = int(len(norm_pdf) * 1.5)
    stride = 100  # Check every 100 chars for speed

    for i in range(0, len(norm_html) - window_size, stride):
        window = norm_html[i : i + window_size]
        html_tokens = window.split()

        # Token-level fuzzy matching
        matched_tokens = 0
        total_similarity = 0.0

        for pdf_token in pdf_tokens:
            # Auto-match very short tokens (punctuation, etc.)
            if len(pdf_token) < 3:
                matched_tokens += 1
                total_similarity += 1.0
                continue

            # Find best fuzzy match for this token in HTML window
            best_token_score = 0.0
            for html_token in html_tokens:
                score = fuzz.ratio(pdf_token, html_token) / 100.0
                if score > best_token_score:
                    best_token_score = score

            total_similarity += best_token_score

            # Token matches if >= token_threshold
            if best_token_score >= token_threshold:
                matched_tokens += 1

        # Line score = fraction of tokens that matched
        line_score = matched_tokens / len(pdf_tokens) if pdf_tokens else 0
        avg_similarity = total_similarity / len(pdf_tokens) if pdf_tokens else 0

        if line_score > best_score:
            best_score = line_score
            best_pos = i
            best_details = {
                "tokens_matched": matched_tokens,
                "total_tokens": len(pdf_tokens),
                "avg_token_similarity": avg_similarity,
            }

        # Early termination if we found a very good match
        if line_score >= 0.95:
            break

    # Line matches if >= line_threshold of tokens matched
    if best_score >= line_threshold:
        return True, best_score, best_pos, "token_fuzzy", best_details

    return False, best_score, -1, "no_match", best_details


def save_unmatched_lines(basename: str, unmatched_lines: list[dict]):
    """Save unmatched lines to review file."""
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    review_file = REVIEW_DIR / f"{basename}_unmatched.txt"

    with open(review_file, "w", encoding="utf-8") as f:
        f.write(f"UNMATCHED LINES FOR: {basename}\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total unmatched: {len(unmatched_lines)}\n\n")

        for i, item in enumerate(unmatched_lines, 1):
            details = item.get("details", {})
            f.write(f"\n{'─' * 80}\n")
            f.write(f"Line {i}/{len(unmatched_lines)}\n")
            f.write(f"Best match score: {item['score']:.2%}\n")
            f.write(f"Method: {item['method']}\n")

            if details:
                f.write(
                    f"Tokens matched: {details.get('tokens_matched', 0)}/"
                    f"{details.get('total_tokens', 0)}\n"
                )
                f.write(f"Avg token similarity: {details.get('avg_token_similarity', 0):.1%}\n")

            f.write(f"Word count: {len(item['line'].split())} words\n")
            f.write(f"{'─' * 80}\n")
            f.write(f"{item['line']}\n")


def validate_pair(html_path: Path, pdf_path: Path, basename: str):
    """Validate a single HTML-PDF pair using article-only content."""
    print(f"\n{basename}")
    print("-" * 70)

    # Extract lines from PDF (cached)
    print("  Extracting lines from PDF...")
    pdf_lines = extract_lines_from_pdf(pdf_path)
    if not pdf_lines:
        print("    ⚠️  No PDF lines extracted")
        return None
    print(f"    {len(pdf_lines)} lines")

    # Load labeled HTML paragraphs
    print("  Loading article-only HTML...")
    html_text = load_labeled_html(basename)
    if not html_text:
        print("    ⚠️  No HTML text loaded")
        return None
    html_words = len(html_text.split())
    print(f"    {html_words:,} words")

    # Match lines
    print("  Matching lines...")
    matches = []
    unmatched_lines = []

    for idx, line in enumerate(pdf_lines):
        matched, score, pos, method, details = match_line_with_token_fuzzy(line, html_text)

        if matched:
            matches.append({"line": line, "score": score, "pos": pos, "method": method})
        else:
            unmatched_lines.append(
                {
                    "line": line,
                    "score": score,
                    "line_num": idx + 1,
                    "method": method,
                    "details": details,
                }
            )

    # Calculate metrics
    match_count = len(matches)
    total_lines = len(pdf_lines)
    match_rate = (match_count / total_lines * 100) if total_lines > 0 else 0

    exact_matches = [m for m in matches if m["method"] == "exact"]
    fuzzy_matches = [m for m in matches if m["method"] == "token_fuzzy"]

    avg_score = sum(m["score"] for m in matches) / len(matches) if matches else 0

    # Check sequential pattern (positions should be mostly increasing)
    positions = [m["pos"] for m in matches]
    sequential_count = sum(1 for i in range(len(positions) - 1) if positions[i + 1] > positions[i])
    sequential_rate = (sequential_count / (len(positions) - 1) * 100) if len(positions) > 1 else 0

    # Save unmatched lines to review file
    if unmatched_lines:
        save_unmatched_lines(basename, unmatched_lines)
        print(
            f"  💾 Saved {len(unmatched_lines)} unmatched lines to "
            f"{REVIEW_DIR}/{basename}_unmatched.txt"
        )

    # Report
    print("\n  Results:")
    print(f"    Total PDF lines:       {total_lines}")
    print(f"    Matched lines:         {match_count} ({match_rate:.1f}%)")
    print(
        f"      - Exact matches:     {len(exact_matches)} "
        f"({len(exact_matches) / total_lines * 100:.1f}%)"
    )
    print(
        f"      - Fuzzy matches:     {len(fuzzy_matches)} "
        f"({len(fuzzy_matches) / total_lines * 100:.1f}%)"
    )
    print(
        f"    Unmatched lines:       {len(unmatched_lines)} "
        f"({len(unmatched_lines) / total_lines * 100:.1f}%)"
    )
    print(f"    Average match score:   {avg_score:.1%}")
    print(f"    Sequential pattern:    {sequential_rate:.1f}% sequential")

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
        "unmatched_count": len(unmatched_lines),
        "avg_score": avg_score,
        "sequential_rate": sequential_rate,
        "status": "PASS" if match_rate >= 75 else "FAIL",
    }


def validate_corpus():
    """Validate all pairs using article-only HTML content."""
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    if not html_dir.exists() or not pdf_dir.exists():
        print("❌ Corpus directories not found: data/raw_html/ or data/raw_pdf/")
        return

    if not LABELED_HTML_DIR.exists():
        print(f"❌ Labeled HTML directory not found: {LABELED_HTML_DIR}/")
        print("   Run extract_labeled_html.py first to extract article content")
        return

    # Find all HTML files
    html_files = sorted(html_dir.glob("*.html"))

    print("🔍 Validating corpus with article-only HTML + token-level fuzzy matching")
    print(f"Found {len(html_files)} HTML files in corpus")
    print(f"📁 Cache: {CACHE_DIR}")
    print(f"📁 Labeled HTML: {LABELED_HTML_DIR}")
    print(f"📁 Review files: {REVIEW_DIR}\n")
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
            errors.append(f"Validation failed: {basename}")

    # Summary
    print(f"\n\n{'=' * 70}")
    print("CORPUS VALIDATION SUMMARY (ARTICLE-ONLY HTML)")
    print(f"{'=' * 70}\n")

    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]

    print(f"✅ PASSED (≥75% line match rate): {len(passed)}")
    for r in sorted(passed, key=lambda x: x["match_rate"], reverse=True):
        print(
            f"   {r['match_rate']:5.1f}% ({r['matched']:3d}/{r['total_lines']:3d}) "
            f"[E:{r['exact_matches']:3d} F:{r['fuzzy_matches']:3d} U:{r['unmatched_count']:3d}] "
            f"seq:{r['sequential_rate']:4.0f}% - {r['basename']}"
        )

    if failed:
        print(f"\n❌ FAILED (<75% line match rate): {len(failed)}")
        for r in sorted(failed, key=lambda x: x["match_rate"]):
            print(
                f"   {r['match_rate']:5.1f}% ({r['matched']:3d}/{r['total_lines']:3d}) "
                f"[E:{r['exact_matches']:3d} F:{r['fuzzy_matches']:3d} U:{r['unmatched_count']:3d}] "
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
        avg_unmatched = sum(r["unmatched_count"] for r in passed) / len(passed)
        print("\n📊 Passed pairs average:")
        print(f"   Match rate:    {avg_match_rate:.1f}%")
        print(f"   Match score:   {avg_score:.1%}")
        print(f"   Sequential:    {avg_sequential:.1f}%")
        print(f"   Unmatched/doc: {avg_unmatched:.1f} lines")

    print(f"\n{'=' * 70}")
    print(f"OVERALL: {len(passed)}/{len(results)} pairs passed validation")

    if failed:
        print(f"\n⚠️  RECOMMENDATION: Review {len(failed)} failed pairs")
        print(f"   Unmatched lines saved to: {REVIEW_DIR}/")
        print("   Check if unmatched lines are:")
        print("     - Headers/footers/metadata (expected) → can keep pair")
        print("     - Substantive content (unexpected) → remove pair")

    print(f"\n💾 Extraction cache: {CACHE_DIR}")
    print(f"📋 Review files: {REVIEW_DIR}")
    print("   Using article-only HTML (no navigation/headers/footers)")

    return results


if __name__ == "__main__":
    validate_corpus()

#!/usr/bin/env python3
"""Diagnose what PDF headers/footers are matching in article HTML."""

import json
import re
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from rapidfuzz import fuzz

CACHE_DIR = Path("data/extraction_cache")
LABELED_HTML_DIR = Path("data/labeled_html")


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-\s+", "", text)
    text = re.sub(r'["' '"]', '"', text)
    text = re.sub(r"[–—]", "-", text)
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
    """Extract lines from PDF (with caching)."""
    cache_path = get_cache_path(pdf_path, "pdf_lines")

    if is_cache_valid(cache_path, pdf_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
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
        print(f"  ⚠️  Error converting PDF: {e}")
        return []

    paragraphs = []
    for item, _level in result.document.iterate_items():
        if hasattr(item, "text") and item.text:
            text = normalize_text(item.text)
            if len(text) > 20:
                paragraphs.append(text)

    lines = []
    for para in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", para)
        for sent in sentences:
            sent = sent.strip()
            words = sent.split()
            if len(words) >= 20:
                text_only = re.sub(r"[^a-zA-Z]", "", sent)
                if len(text_only) > len(sent) * 0.7:
                    lines.append(sent)

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
        return ""

    try:
        with open(labeled_file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"    ⚠️  Error loading labeled HTML: {e}")
        return ""

    paragraphs = data.get("paragraphs", [])
    text = " ".join(p["text"] for p in paragraphs)
    return text


def match_line_with_token_fuzzy(
    pdf_line: str,
    html_text: str,
    token_threshold: float = 0.80,
    line_threshold: float = 0.80,
):
    """Match PDF line in HTML using token-level fuzzy matching."""
    norm_pdf = normalize_text(pdf_line)
    norm_html = html_text

    # Stage 1: Exact match
    if norm_pdf in norm_html:
        pos = norm_html.find(norm_pdf)
        matched_text = norm_html[pos : pos + len(norm_pdf)]
        return True, 1.0, pos, "exact", matched_text, {}

    # Stage 2: Token-level fuzzy matching
    pdf_tokens = norm_pdf.split()
    best_score = 0.0
    best_pos = -1
    best_matched_text = ""
    best_details = {}

    window_size = int(len(norm_pdf) * 1.5)
    stride = 100

    for i in range(0, len(norm_html) - window_size, stride):
        window = norm_html[i : i + window_size]
        html_tokens = window.split()

        matched_tokens = 0
        total_similarity = 0.0

        for pdf_token in pdf_tokens:
            if len(pdf_token) < 3:
                matched_tokens += 1
                total_similarity += 1.0
                continue

            best_token_score = 0.0
            for html_token in html_tokens:
                score = fuzz.ratio(pdf_token, html_token) / 100.0
                if score > best_token_score:
                    best_token_score = score

            total_similarity += best_token_score

            if best_token_score >= token_threshold:
                matched_tokens += 1

        line_score = matched_tokens / len(pdf_tokens) if pdf_tokens else 0
        avg_similarity = total_similarity / len(pdf_tokens) if pdf_tokens else 0

        if line_score > best_score:
            best_score = line_score
            best_pos = i
            best_matched_text = window
            best_details = {
                "tokens_matched": matched_tokens,
                "total_tokens": len(pdf_tokens),
                "avg_token_similarity": avg_similarity,
            }

        if line_score >= 0.95:
            break

    if best_score >= line_threshold:
        return (
            True,
            best_score,
            best_pos,
            "token_fuzzy",
            best_matched_text,
            best_details,
        )

    return False, best_score, -1, "no_match", "", best_details


def is_likely_header_footer(line: str) -> tuple[bool, str]:
    """Check if a line is likely a header or footer."""
    words = line.split()
    word_count = len(words)

    # Very short lines (20-25 words) might be headers
    if 20 <= word_count <= 25:
        return True, "short_line"

    # Contains page numbers or volume references
    if re.search(r"\b\d{1,4}\b", line) and word_count < 30:
        return True, "page_number"

    # Contains journal names
    journal_indicators = [
        "law review",
        "journal",
        "quarterly",
        "supreme court review",
        "michigan",
        "boston university",
    ]
    if any(indicator in line for indicator in journal_indicators) and word_count < 35:
        return True, "journal_name"

    # Repeated words (like headers)
    unique_words = set(words)
    if len(unique_words) < len(words) * 0.6:  # Less than 60% unique
        return True, "repeated_words"

    return False, "content"


def diagnose_pair(html_path: Path, pdf_path: Path, basename: str, max_lines: int = 50):
    """Diagnose header/footer matching for a single pair."""
    print(f"\n{'=' * 80}")
    print(f"DIAGNOSING: {basename}")
    print(f"{'=' * 80}\n")

    # Extract PDF lines
    pdf_lines = extract_lines_from_pdf(pdf_path)
    if not pdf_lines:
        print("⚠️  No PDF lines extracted")
        return

    # Load HTML
    html_text = load_labeled_html(basename)
    if not html_text:
        print("⚠️  No HTML text loaded")
        return

    print(f"PDF lines: {len(pdf_lines)}")
    print(f"HTML words: {len(html_text.split()):,}\n")

    # Match lines and identify potential headers
    matched_headers = []
    matched_content = []

    for idx, line in enumerate(pdf_lines[:max_lines]):  # Limit to first N lines
        matched, score, pos, method, matched_text, details = match_line_with_token_fuzzy(
            line, html_text
        )

        if matched:
            is_header, header_type = is_likely_header_footer(line)
            match_info = {
                "line_num": idx + 1,
                "pdf_line": line,
                "score": score,
                "method": method,
                "position": pos,
                "matched_text": matched_text[:200] + "..."
                if len(matched_text) > 200
                else matched_text,
                "header_type": header_type,
            }

            if is_header:
                matched_headers.append(match_info)
            else:
                matched_content.append(match_info)

    # Report matched headers
    if matched_headers:
        print(f"🔍 MATCHED HEADERS/FOOTERS: {len(matched_headers)}")
        print("=" * 80)

        for info in matched_headers:
            print(f"\nLine {info['line_num']} ({info['header_type']}):")
            print(f"  Score: {info['score']:.1%} | Method: {info['method']}")
            print(f"  PDF: {info['pdf_line']}")
            print(f"  HTML Match: {info['matched_text']}")
            print()
    else:
        print("✅ No likely headers/footers matched (good!)\n")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total lines analyzed: {min(max_lines, len(pdf_lines))}")
    print(f"Matched headers/footers: {len(matched_headers)}")
    print(f"Matched content: {len(matched_content)}")

    if matched_headers:
        print(f"\n⚠️  {len(matched_headers)} likely headers/footers matched in HTML!")
        print("    This suggests false positives - headers matching article content.")
    else:
        print("\n✅ No headers/footers matched - validation looks good!")


def diagnose_corpus():
    """Diagnose header matching across corpus."""
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    if not html_dir.exists() or not pdf_dir.exists():
        print("❌ Corpus directories not found")
        return

    html_files = sorted(html_dir.glob("*.html"))

    print("🔍 DIAGNOSING HEADER/FOOTER MATCHING")
    print(f"Found {len(html_files)} HTML files\n")

    # Diagnose first 3 files in detail
    for html_file in html_files[:3]:
        pdf_file = pdf_dir / html_file.with_suffix(".pdf").name

        if not pdf_file.exists():
            continue

        basename = html_file.stem
        diagnose_pair(html_file, pdf_file, basename, max_lines=100)


if __name__ == "__main__":
    diagnose_corpus()

#!/usr/bin/env python3
"""
Generate side-by-side HTML comparison of OCR outputs.

Usage:
  python3 scripts/evaluation/generate_ocr_comparison_html.py
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path


def load_extraction(path: Path) -> dict:
    """Load extraction JSON."""
    with open(path) as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Strip markdown
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"-{2,}", "", text)
    # Normalize whitespace but preserve paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def split_into_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs."""
    # First try splitting on double newlines
    paragraphs = re.split(r"\n\n+", text)

    # If we only get one paragraph, try splitting on single newlines
    # (This handles PyPDF2's page-level extraction)
    if len(paragraphs) <= 1:
        paragraphs = text.split("\n")

    # Clean up and filter empty paragraphs
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]
    return paragraphs


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, text1, text2).ratio()


def highlight_differences(text1: str, text2: str) -> tuple[str, str]:
    """Highlight word-level differences between two texts."""
    words1 = text1.split()
    words2 = text2.split()

    matcher = SequenceMatcher(None, words1, words2)

    html1_parts = []
    html2_parts = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            html1_parts.append(" ".join(words1[i1:i2]))
            html2_parts.append(" ".join(words2[j1:j2]))
        elif tag == "replace":
            html1_parts.append(f'<mark class="diff-replace">{" ".join(words1[i1:i2])}</mark>')
            html2_parts.append(f'<mark class="diff-replace">{" ".join(words2[j1:j2])}</mark>')
        elif tag == "delete":
            html1_parts.append(f'<mark class="diff-delete">{" ".join(words1[i1:i2])}</mark>')
        elif tag == "insert":
            html2_parts.append(f'<mark class="diff-insert">{" ".join(words2[j1:j2])}</mark>')

    return " ".join(html1_parts), " ".join(html2_parts)


def align_paragraphs(paras1: list[str], paras2: list[str]) -> list[tuple[str, str, float]]:
    """Align paragraphs using greedy best-match approach with order preservation."""
    # Try to use rapidfuzz for faster similarity calculation
    try:
        from rapidfuzz import fuzz

        def similarity(a: str, b: str) -> float:
            return fuzz.ratio(a, b) / 100.0

    except ImportError:
        similarity = calculate_similarity

    aligned = []
    used_j = set()  # Track which paras2 indices have been matched

    # For each para1, find best matching para2 within reasonable distance
    i = 0
    last_matched_j = -1  # Track last matched position to preserve order

    while i < len(paras1):
        best_j = None
        best_score = 0.0

        # Look ahead up to 50 paragraphs in paras2 (or remaining)
        search_start = max(0, last_matched_j + 1)
        search_end = min(len(paras2), last_matched_j + 51)

        for j in range(search_start, search_end):
            if j in used_j:
                continue

            score = similarity(paras1[i], paras2[j])

            if score > best_score:
                best_score = score
                best_j = j

        # Accept match if similarity > 0.3 (low threshold for OCR differences)
        if best_j is not None and best_score > 0.3:
            # Add any skipped para2 items before this match
            for j in range(last_matched_j + 1, best_j):
                if j not in used_j:
                    aligned.append(("", paras2[j], 0.0))
                    used_j.add(j)

            # Add the match
            aligned.append((paras1[i], paras2[best_j], best_score))
            used_j.add(best_j)
            last_matched_j = best_j
        else:
            # No good match found - para1 is unique
            aligned.append((paras1[i], "", 0.0))

        i += 1

    # Add remaining unmatched para2 items
    for j in range(len(paras2)):
        if j not in used_j:
            aligned.append(("", paras2[j], 0.0))

    return aligned


def generate_html(aligned_paras: list[tuple[str, str, float]], output_path: Path, metadata: dict):
    """Generate HTML comparison file."""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR Comparison: Docling vs Tesseract</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .metadata {{
            color: #666;
            font-size: 14px;
            line-height: 1.6;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            border-left: 3px solid #007bff;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .stat-value {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }}
        .legend {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .legend h3 {{
            margin: 0 0 10px 0;
            font-size: 16px;
            color: #333;
        }}
        .legend-items {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }}
        .comparison-table {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #007bff;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{
            padding: 15px;
            vertical-align: top;
            border-bottom: 1px solid #e0e0e0;
            line-height: 1.6;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .para-num {{
            width: 50px;
            text-align: center;
            color: #999;
            font-weight: bold;
            background: #f8f9fa;
        }}
        .similarity {{
            width: 80px;
            text-align: center;
            font-size: 12px;
            font-weight: bold;
        }}
        .sim-high {{ color: #28a745; }}
        .sim-medium {{ color: #ffc107; }}
        .sim-low {{ color: #dc3545; }}
        .text-cell {{
            font-family: 'Georgia', serif;
            font-size: 15px;
            max-width: 45%;
        }}
        .empty-cell {{
            background: #fff3cd;
            font-style: italic;
            color: #856404;
        }}
        mark {{
            padding: 2px 4px;
            border-radius: 3px;
        }}
        .diff-replace {{
            background: #fff3cd;
            color: #856404;
        }}
        .diff-delete {{
            background: #f8d7da;
            color: #721c24;
            text-decoration: line-through;
        }}
        .diff-insert {{
            background: #d4edda;
            color: #155724;
        }}
        .filter-controls {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .filter-controls label {{
            margin-right: 15px;
            cursor: pointer;
        }}
        .filter-controls input {{
            margin-right: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>OCR Comparison: Docling vs Tesseract</h1>
        <div class="metadata">
            <div><strong>Document:</strong> {metadata["document"]}</div>
            <div><strong>Pages:</strong> {metadata["pages"]}</div>
            <div><strong>Source:</strong> {metadata["source"]}</div>
        </div>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-label">Docling</div>
                <div class="stat-value">{metadata["docling_words"]:,} words</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Tesseract</div>
                <div class="stat-value">{metadata["tesseract_words"]:,} words</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Difference</div>
                <div class="stat-value">{metadata["diff_words"]:,} words</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Paragraphs Compared</div>
                <div class="stat-value">{len(aligned_paras)}</div>
            </div>
        </div>
    </div>

    <div class="legend">
        <h3>Legend</h3>
        <div class="legend-items">
            <div class="legend-item">
                <mark class="diff-replace">Yellow</mark>
                <span>Different text in both versions</span>
            </div>
            <div class="legend-item">
                <mark class="diff-delete">Red strikethrough</mark>
                <span>Only in Docling</span>
            </div>
            <div class="legend-item">
                <mark class="diff-insert">Green</mark>
                <span>Only in Tesseract</span>
            </div>
            <div class="legend-item">
                <span class="empty-cell" style="padding: 2px 8px; border-radius: 3px;">Tan background</span>
                <span>Missing paragraph</span>
            </div>
        </div>
    </div>

    <div class="filter-controls">
        <label><input type="checkbox" id="show-identical" checked> Show identical paragraphs</label>
        <label><input type="checkbox" id="show-similar" checked> Show similar paragraphs (&gt;50%)</label>
        <label><input type="checkbox" id="show-different" checked> Show different paragraphs (&lt;50%)</label>
    </div>

    <div class="comparison-table">
        <table>
            <thead>
                <tr>
                    <th class="para-num">#</th>
                    <th>Docling (ocrmac)</th>
                    <th>Tesseract (OCRmyPDF)</th>
                    <th class="similarity">Match</th>
                </tr>
            </thead>
            <tbody>
"""

    for idx, (para1, para2, similarity) in enumerate(aligned_paras, 1):
        # Determine similarity class
        if similarity >= 0.95:
            sim_class = "sim-high"
            sim_text = f"{similarity:.0%}"
            row_class = "row-identical"
        elif similarity >= 0.5:
            sim_class = "sim-medium"
            sim_text = f"{similarity:.0%}"
            row_class = "row-similar"
        else:
            sim_class = "sim-low"
            sim_text = f"{similarity:.0%}"
            row_class = "row-different"

        # Highlight differences if both paragraphs exist
        if para1 and para2:
            para1_html, para2_html = highlight_differences(para1, para2)
            cell1_class = "text-cell"
            cell2_class = "text-cell"
        else:
            para1_html = para1 if para1 else "<em>(Missing in Docling)</em>"
            para2_html = para2 if para2 else "<em>(Missing in Tesseract)</em>"
            cell1_class = "text-cell empty-cell" if not para1 else "text-cell"
            cell2_class = "text-cell empty-cell" if not para2 else "text-cell"

        html += f"""                <tr class="{row_class}">
                    <td class="para-num">{idx}</td>
                    <td class="{cell1_class}">{para1_html}</td>
                    <td class="{cell2_class}">{para2_html}</td>
                    <td class="similarity {sim_class}">{sim_text}</td>
                </tr>
"""

    html += """            </tbody>
        </table>
    </div>

    <script>
        // Filter controls
        const showIdentical = document.getElementById('show-identical');
        const showSimilar = document.getElementById('show-similar');
        const showDifferent = document.getElementById('show-different');

        function updateDisplay() {
            const rows = document.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const simText = row.querySelector('.similarity').textContent;
                const sim = parseFloat(simText) / 100;

                let show = false;
                if (sim >= 0.95 && showIdentical.checked) show = true;
                if (sim >= 0.5 && sim < 0.95 && showSimilar.checked) show = true;
                if (sim < 0.5 && showDifferent.checked) show = true;

                row.style.display = show ? '' : 'none';
            });
        }

        showIdentical.addEventListener('change', updateDisplay);
        showSimilar.addEventListener('change', updateDisplay);
        showDifferent.addEventListener('change', updateDisplay);
    </script>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html)


def main():
    """Generate HTML comparison."""
    # Paths
    docling_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only_baseline_extraction.json"
    )
    tesseract_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only_ocr_ocrmypdf_extraction.json"
    )
    output_path = Path("results/ocr_comparison.html")

    print("Loading extractions...")
    docling_data = load_extraction(docling_path)
    tesseract_data = load_extraction(tesseract_path)

    # Get markdown export for Docling (has line breaks)
    # Get page-level text for Tesseract
    docling_markdown = docling_data.get("markdown_full_text", "")
    tesseract_texts = tesseract_data.get("texts", [])

    # Split both into lines for fair comparison
    print("Splitting into lines...")

    # Docling markdown - split into lines
    docling_lines = [line.strip() for line in docling_markdown.split("\n") if line.strip()]

    # Tesseract (via PyPDF2) extracts page-level blocks - split into lines
    tesseract_lines = []
    for page_text in tesseract_texts:
        # Split on newlines to get line-level granularity
        lines = [line.strip() for line in page_text.split("\n") if line.strip()]
        tesseract_lines.extend(lines)

    print("Cleaning text lines...")
    # Normalize each line
    docling_paras = [normalize_text(t) for t in docling_lines if t.strip()]
    tesseract_paras = [normalize_text(t) for t in tesseract_lines if t.strip()]

    # Filter out very short lines (likely artifacts)
    docling_paras = [p for p in docling_paras if len(p) > 10]
    tesseract_paras = [p for p in tesseract_paras if len(p) > 10]

    print(f"  Docling: {len(docling_paras)} paragraphs")
    print(f"  Tesseract: {len(tesseract_paras)} paragraphs")

    print("Aligning paragraphs...")
    aligned = align_paragraphs(docling_paras, tesseract_paras)

    # Calculate metadata from aligned text blocks
    docling_words = sum(len(p.split()) for p in docling_paras)
    tesseract_words = sum(len(p.split()) for p in tesseract_paras)

    metadata = {
        "document": "usc_law_review_in_the_name_of_accountability.pdf",
        "pages": 30,
        "source": "Same image-only PDF (300 DPI)",
        "docling_words": docling_words,
        "tesseract_words": tesseract_words,
        "diff_words": abs(tesseract_words - docling_words),
    }

    print("Generating HTML...")
    generate_html(aligned, output_path, metadata)

    print(f"\n✓ HTML comparison saved to: {output_path}")
    print(f"  Compared {len(aligned)} paragraph pairs")
    print(f"  Docling: {docling_words:,} words")
    print(f"  Tesseract: {tesseract_words:,} words")
    print(
        f"  Difference: {metadata['diff_words']:,} words ({abs(tesseract_words - docling_words) / docling_words * 100:.1f}%)"
    )


if __name__ == "__main__":
    main()

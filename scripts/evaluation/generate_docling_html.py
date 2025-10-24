#!/usr/bin/env python3
"""
Generate clean HTML view of Docling output.

Usage:
  python3 scripts/evaluation/generate_docling_html.py
"""

import json
from pathlib import Path


def load_extraction(path: Path) -> dict:
    """Load extraction JSON."""
    with open(path) as f:
        return json.load(f)


def generate_html(texts: list[str], output_path: Path, metadata: dict):
    """Generate HTML view of Docling paragraphs."""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Docling OCR Output</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f5;
            line-height: 1.6;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 15px 0;
            color: #333;
            font-size: 28px;
        }}
        .metadata {{
            color: #666;
            font-size: 14px;
            line-height: 1.8;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 4px;
            border-left: 3px solid #007bff;
        }}
        .stat-label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }}
        .content {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .paragraph {{
            margin-bottom: 25px;
            padding-bottom: 25px;
            border-bottom: 1px solid #eee;
        }}
        .paragraph:last-child {{
            border-bottom: none;
        }}
        .para-number {{
            display: inline-block;
            background: #007bff;
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .para-text {{
            font-family: 'Georgia', serif;
            font-size: 16px;
            color: #333;
            line-height: 1.8;
        }}
        .controls {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .controls input {{
            padding: 8px 12px;
            font-size: 14px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 100%;
            max-width: 300px;
        }}
        .highlight {{
            background: #fff3cd;
            padding: 2px 4px;
            border-radius: 2px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Docling OCR Output</h1>
        <div class="metadata">
            <div><strong>Document:</strong> {metadata["document"]}</div>
            <div><strong>Pages:</strong> {metadata["pages"]}</div>
            <div><strong>OCR Engine:</strong> {metadata["ocr_engine"]}</div>
            <div><strong>Processing Time:</strong> {metadata["time"]}</div>
        </div>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-label">Text Blocks</div>
                <div class="stat-value">{len(texts)}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Total Words</div>
                <div class="stat-value">{metadata["words"]:,}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Characters</div>
                <div class="stat-value">{metadata["chars"]:,}</div>
            </div>
        </div>
    </div>

    <div class="controls">
        <input type="text" id="search" placeholder="Search text...">
    </div>

    <div class="content">
"""

    for idx, text in enumerate(texts, 1):
        # Escape HTML
        text_html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        html += f"""        <div class="paragraph" data-text="{text.lower()}">
            <div class="para-number">Block {idx}</div>
            <div class="para-text">{text_html}</div>
        </div>
"""

    html += """    </div>

    <script>
        // Search functionality
        const searchInput = document.getElementById('search');
        const paragraphs = document.querySelectorAll('.paragraph');

        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();

            paragraphs.forEach(para => {
                const text = para.getAttribute('data-text');
                const textDiv = para.querySelector('.para-text');

                if (!query) {
                    para.style.display = '';
                    textDiv.innerHTML = textDiv.textContent; // Remove highlights
                } else if (text.includes(query)) {
                    para.style.display = '';

                    // Highlight matching text
                    const originalText = textDiv.textContent;
                    const regex = new RegExp(`(${query})`, 'gi');
                    const highlighted = originalText.replace(regex, '<span class="highlight">$1</span>');
                    textDiv.innerHTML = highlighted;
                } else {
                    para.style.display = 'none';
                }
            });
        });
    </script>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html)


def main():
    """Generate Docling HTML view."""
    # Path
    docling_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only_baseline_extraction.json"
    )
    output_path = Path("results/docling_output.html")

    print("Loading Docling extraction...")
    data = load_extraction(docling_path)

    texts = data.get("texts", [])
    page_count = data.get("page_count", 0)
    extraction_time = data.get("metadata", {}).get("extraction_time_s", 0)

    # Calculate stats
    total_chars = sum(len(t) for t in texts)
    total_words = sum(len(t.split()) for t in texts)

    metadata = {
        "document": "usc_law_review_in_the_name_of_accountability.pdf",
        "pages": page_count,
        "ocr_engine": "ocrmac (Docling auto-selected)",
        "time": f"{extraction_time:.1f}s",
        "chars": total_chars,
        "words": total_words,
    }

    print("Generating HTML...")
    generate_html(texts, output_path, metadata)

    print(f"\n✓ HTML saved to: {output_path}")
    print(f"  {len(texts)} text blocks")
    print(f"  {total_words:,} words")
    print(f"  {total_chars:,} characters")


if __name__ == "__main__":
    main()

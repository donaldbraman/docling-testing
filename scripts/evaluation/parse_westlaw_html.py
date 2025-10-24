#!/usr/bin/env python3
"""
Parse Westlaw HTML files to extract body text and footnotes.

Westlaw HTML has a specific structure with:
- Body paragraphs: <div class="co_paragraph"><div class="co_paragraphText">...</div></div>
- Footnote references: <a class="co_footnoteReference" ... href="#co_footnote_F...">...</a>
- Footnote content: <div id="co_footnote_F..." class="co_footnoteText">...</div>
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


def parse_westlaw_html(html_path: Path) -> dict:
    """
    Parse Westlaw HTML file and extract body text + footnotes.

    Args:
        html_path: Path to HTML file

    Returns:
        Dict with 'paragraphs' list containing {text, label} items
    """
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    paragraphs = []

    # Extract body paragraphs
    for para_div in soup.find_all("div", class_="co_paragraph"):
        text_div = para_div.find("div", class_="co_paragraphText")
        if not text_div:
            continue

        # Get text, removing footnote markers but keeping the text
        text = text_div.get_text(separator=" ", strip=True)

        # Clean up excessive whitespace
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > 20:  # Minimum length filter
            paragraphs.append({"text": text, "label": "body-text"})

    # Extract footnotes
    for footnote_div in soup.find_all("div", class_="co_footnoteText"):
        text = footnote_div.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > 20:  # Minimum length filter
            paragraphs.append({"text": text, "label": "footnote-text"})

    return {"paragraphs": paragraphs, "source": "westlaw_html", "pdf_name": html_path.stem}


def main():
    """Process the 5 Westlaw HTML files."""
    westlaw_pdfs = [
        "antitrusts_interdependence_paradox",
        "deterring_unenforceable_terms",
        "free_speech_breathing_space_and_liability_insurance",
        "political_mootness",
        "the_association_game__applying_noscitur_a_sociis_and_ejusdem_generis",
    ]

    html_dir = Path("data/v3_data/raw_html")
    output_dir = Path("data/v3_data/processed_html")
    output_dir.mkdir(parents=True, exist_ok=True)

    for pdf_name in westlaw_pdfs:
        html_path = html_dir / f"{pdf_name}.html"
        if not html_path.exists():
            print(f"❌ Not found: {pdf_name}")
            continue

        print(f"Processing: {pdf_name}")

        try:
            result = parse_westlaw_html(html_path)

            output_path = output_dir / f"{pdf_name}.json"
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)

            body_count = sum(1 for p in result["paragraphs"] if p["label"] == "body-text")
            footnote_count = sum(1 for p in result["paragraphs"] if p["label"] == "footnote-text")

            print(f"  ✅ Extracted: {body_count} body, {footnote_count} footnotes")
            print(f"  💾 Saved: {output_path}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()

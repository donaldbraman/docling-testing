#!/usr/bin/env python3
"""Debug BU Law Review HTML extraction to see what's being classified as body vs footnote."""

import re
from pathlib import Path

from bs4 import BeautifulSoup


def normalize_text(text: str) -> str:
    """Normalize text for consistency."""
    text = re.sub(r"\s+", " ", text)  # Collapse whitespace
    text = re.sub(r"-\s+", "", text)  # Remove line-break hyphens
    return text.strip()


def debug_extraction(html_path: Path):
    """Debug the extraction process step by step."""
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Remove script and style tags
    for script in soup(["script", "style"]):
        script.decompose()

    print(f"DEBUGGING: {html_path.name}")
    print("=" * 80)

    all_paragraphs = soup.find_all("p")
    print(f"\nTotal <p> tags found: {len(all_paragraphs)}\n")

    for i, p in enumerate(all_paragraphs):
        text = p.get_text(separator=" ", strip=True)

        # Show decision process
        print(f"\n[{i + 1}] Length: {len(text)} chars")

        if len(text) < 20:
            print("    SKIPPED (too short)")
            continue

        normalized = normalize_text(text)

        # Check if starts with [N] pattern (footnote)
        if re.match(r"^\[\d+\]", text):
            print("    CLASSIFIED AS: footnote-text")
            print(f"    First 100 chars: {text[:100]}")
        else:
            # Check if navigation/header
            lower_text = text.lower()
            skip_patterns = ["skip to content", "menu", "search", "home"]
            matched_pattern = None
            for pattern in skip_patterns:
                if pattern in lower_text:
                    matched_pattern = pattern
                    break

            if matched_pattern:
                print(f"    SKIPPED (navigation) - matched: '{matched_pattern}'")
                print(f"    First 100 chars: {text[:100]}")
                continue
            print("    CLASSIFIED AS: body-text")
            print(f"    First 100 chars: {text[:100]}")


if __name__ == "__main__":
    html_path = Path("data/raw_html/bu_law_review_online_fourth_amendment_secure.html")
    debug_extraction(html_path)

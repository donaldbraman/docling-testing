#!/usr/bin/env python3
"""Generate histogram of law review pair quality scores."""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\d+", "", text)
    return text.strip()


def get_word_set(text: str, min_length: int = 4) -> set:
    """Get set of significant words from text."""
    words = text.split()
    return {w for w in words if len(w) >= min_length}


def extract_text_from_html(html_path: Path) -> str:
    """Extract clean text from HTML file."""
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    for script in soup(["script", "style"]):
        script.decompose()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = " ".join(chunk for chunk in chunks if chunk)
    return text.lower()


def calculate_jaccard(html_text: str, pdf_text: str) -> float:
    """Calculate Jaccard similarity between HTML and PDF."""
    html_norm = normalize_text(html_text)
    pdf_norm = normalize_text(pdf_text)

    html_words = get_word_set(html_norm)
    pdf_words = get_word_set(pdf_norm)

    if not html_words or not pdf_words:
        return 0.0

    intersection = html_words & pdf_words
    union = html_words | pdf_words
    return (len(intersection) / len(union)) * 100 if union else 0.0


def generate_histogram():
    """Generate and display histogram of Jaccard scores."""
    import pypdf

    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    # Get all law review HTML files
    html_files = sorted(html_dir.glob("*.html"))
    law_review_files = [f for f in html_files if not f.stem.startswith("arxiv_")]

    print(f"📊 Analyzing {len(law_review_files)} law review pairs...\n")

    scores = []

    for i, html_path in enumerate(law_review_files, 1):
        pdf_path = pdf_dir / html_path.name.replace(".html", ".pdf")

        if not pdf_path.exists():
            continue

        try:
            html_text = extract_text_from_html(html_path)

            pdf_reader = pypdf.PdfReader(pdf_path)
            pdf_text = ""
            for page in pdf_reader.pages:
                pdf_text += page.extract_text()
            pdf_text = pdf_text.lower()

            jaccard = calculate_jaccard(html_text, pdf_text)
            scores.append({"basename": html_path.stem, "jaccard": jaccard})

            if i % 20 == 0:
                print(f"  Processed {i}/{len(law_review_files)} pairs...")

        except Exception as e:
            print(f"⚠️  Error processing {html_path.name}: {e}")
            continue

    print(f"\n✅ Analyzed {len(scores)} law review pairs\n")

    # Create bins
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    bin_counts = {f"{bins[i]}-{bins[i + 1]}%": 0 for i in range(len(bins) - 1)}

    for score in scores:
        jaccard = score["jaccard"]
        for i in range(len(bins) - 1):
            if bins[i] <= jaccard < bins[i + 1]:
                bin_counts[f"{bins[i]}-{bins[i + 1]}%"] += 1
                break
        else:
            if jaccard >= bins[-1]:
                bin_counts[f"{bins[-2]}-{bins[-1]}%"] += 1

    # Display histogram
    print("=" * 60)
    print("LAW REVIEW PAIR QUALITY DISTRIBUTION")
    print("=" * 60)
    print("\nJaccard Similarity Score Histogram:\n")

    max_count = max(bin_counts.values())
    max_bar_width = 50

    for bin_label, count in bin_counts.items():
        bar_width = int((count / max_count) * max_bar_width) if max_count > 0 else 0
        bar = "#" * bar_width
        print(f"{bin_label:10s} | {bar} {count}")

    # Statistics
    jaccard_values = [s["jaccard"] for s in scores]
    avg_jaccard = sum(jaccard_values) / len(jaccard_values)
    median_jaccard = sorted(jaccard_values)[len(jaccard_values) // 2]

    print(f"\n{'-' * 60}")
    print(f"Total pairs:      {len(scores)}")
    print(f"Average Jaccard:  {avg_jaccard:.1f}%")
    print(f"Median Jaccard:   {median_jaccard:.1f}%")
    print("\nPairs by quality:")
    print(f"  Excellent (≥80%): {sum(1 for s in scores if s['jaccard'] >= 80)}")
    print(f"  Good (60-80%):    {sum(1 for s in scores if 60 <= s['jaccard'] < 80)}")
    print(f"  Marginal (40-60%): {sum(1 for s in scores if 40 <= s['jaccard'] < 60)}")
    print(f"  Poor (<40%):      {sum(1 for s in scores if s['jaccard'] < 40)}")

    # Save detailed results
    results_file = Path("data/law_review_quality_scores.json")
    with open(results_file, "w") as f:
        json.dump(
            {
                "total_pairs": len(scores),
                "average_jaccard": avg_jaccard,
                "median_jaccard": median_jaccard,
                "histogram": bin_counts,
                "scores": sorted(scores, key=lambda x: x["jaccard"]),
            },
            f,
            indent=2,
        )

    print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    generate_histogram()

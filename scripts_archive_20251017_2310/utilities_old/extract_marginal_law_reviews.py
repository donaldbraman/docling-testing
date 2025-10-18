#!/usr/bin/env python3
"""Extract law review pairs with marginal quality scores for manual review."""

import json
import re
import shutil
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
    significant_words = {w for w in words if len(w) >= min_length}
    return significant_words


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


def calculate_overlap(html_text: str, pdf_text: str) -> dict:
    """Calculate text overlap between HTML and PDF."""
    html_norm = normalize_text(html_text)
    pdf_norm = normalize_text(pdf_text)

    html_words = get_word_set(html_norm)
    pdf_words = get_word_set(pdf_norm)

    if not html_words or not pdf_words:
        return {
            "jaccard_similarity": 0.0,
            "overlap_ratio": 0.0,
            "common_words": 0,
            "html_words": len(html_words),
            "pdf_words": len(pdf_words),
        }

    intersection = html_words & pdf_words
    union = html_words | pdf_words
    jaccard = len(intersection) / len(union) if union else 0

    smaller_set = min(len(html_words), len(pdf_words))
    overlap_ratio = len(intersection) / smaller_set if smaller_set > 0 else 0

    return {
        "jaccard_similarity": jaccard,
        "overlap_ratio": overlap_ratio,
        "common_words": len(intersection),
        "html_words": len(html_words),
        "pdf_words": len(pdf_words),
    }


def extract_marginal_law_reviews(min_jaccard=60.0, max_jaccard=80.0):
    """Extract law review pairs with marginal quality scores."""
    import pypdf

    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")
    review_dir = Path("data/pairs_for_review")

    # Get all HTML files
    html_files = sorted(html_dir.glob("*.html"))

    # Filter to law reviews only (exclude arxiv)
    law_review_files = [f for f in html_files if not f.stem.startswith("arxiv_")]

    print(f"📊 Analyzing {len(law_review_files)} law review pairs...")
    print(f"Looking for Jaccard scores between {min_jaccard}% and {max_jaccard}%\n")

    marginal_pairs = []

    for html_path in law_review_files:
        pdf_path = pdf_dir / html_path.name.replace(".html", ".pdf")

        if not pdf_path.exists():
            continue

        # Extract texts
        try:
            html_text = extract_text_from_html(html_path)

            pdf_reader = pypdf.PdfReader(pdf_path)
            pdf_text = ""
            for page in pdf_reader.pages:
                pdf_text += page.extract_text()
            pdf_text = pdf_text.lower()

            # Calculate overlap
            metrics = calculate_overlap(html_text, pdf_text)
            jaccard_pct = metrics["jaccard_similarity"] * 100

            # Check if in marginal range
            if min_jaccard <= jaccard_pct <= max_jaccard:
                marginal_pairs.append(
                    {
                        "basename": html_path.stem,
                        "html_file": html_path.name,
                        "pdf_file": pdf_path.name,
                        "jaccard": jaccard_pct,
                        "overlap": metrics["overlap_ratio"] * 100,
                        "common_words": metrics["common_words"],
                    }
                )

        except Exception as e:
            print(f"⚠️  Error processing {html_path.name}: {e}")
            continue

    # Sort by Jaccard score
    marginal_pairs.sort(key=lambda x: x["jaccard"])

    if not marginal_pairs:
        print(f"✅ No law review pairs found in {min_jaccard}-{max_jaccard}% range")
        return

    # Copy to review folder
    review_html = review_dir / "html"
    review_pdf = review_dir / "pdf"

    for pair in marginal_pairs:
        html_path = html_dir / pair["html_file"]
        pdf_path = pdf_dir / pair["pdf_file"]

        shutil.copy(html_path, review_html / pair["html_file"])
        shutil.copy(pdf_path, review_pdf / pair["pdf_file"])

    # Update summary
    summary_file = review_dir / "REVIEW_SUMMARY.json"
    if summary_file.exists():
        with open(summary_file) as f:
            existing = json.load(f)
    else:
        existing = []

    # Add new pairs (avoid duplicates)
    existing_basenames = {item["basename"] for item in existing}
    for pair in marginal_pairs:
        if pair["basename"] not in existing_basenames:
            existing.append(
                {
                    "basename": pair["basename"],
                    "jaccard": pair["jaccard"],
                    "overlap": pair["overlap"],
                    "status": "MARGINAL",
                    "html_copied": True,
                    "pdf_copied": True,
                }
            )

    with open(summary_file, "w") as f:
        json.dump(existing, f, indent=2)

    # Update README
    readme = review_dir / "README.md"
    with open(readme, "w") as f:
        f.write("# HTML-PDF Pairs for Manual Review\n\n")
        f.write("These pairs need manual verification due to quality concerns.\n\n")
        f.write("## Review Criteria\n\n")
        f.write("For each pair, verify:\n")
        f.write("1. Are the HTML and PDF about the same article/paper?\n")
        f.write("2. Is the content substantially the same?\n")
        f.write("3. Should we keep this pair for training?\n\n")
        f.write("## Status Legend\n\n")
        f.write("- **MISMATCH**: <40% Jaccard - likely wrong pairing\n")
        f.write("- **PARTIAL**: 40-60% Jaccard - needs verification\n")
        f.write(
            f"- **MARGINAL**: {min_jaccard}-{max_jaccard}% Jaccard - above threshold but worth checking\n\n"
        )
        f.write("## Pairs to Review\n\n")
        f.write("| Basename | Jaccard | Overlap | Status |\n")
        f.write("|----------|---------|---------|--------|\n")

        for item in sorted(existing, key=lambda x: x["jaccard"]):
            basename_short = (
                item["basename"][:60] + "..." if len(item["basename"]) > 60 else item["basename"]
            )
            f.write(
                f"| {basename_short} | {item['jaccard']:.1f}% | {item['overlap']:.1f}% | {item['status']} |\n"
            )

        f.write(f"\n\n**Total pairs to review:** {len(existing)}\n")

    print(f"\n✅ Added {len(marginal_pairs)} marginal law review pairs")
    print(f"📁 Review folder: {review_dir}")
    print("\n📊 Marginal pairs added:")
    for pair in marginal_pairs:
        print(f"   {pair['jaccard']:.1f}% - {pair['basename'][:60]}")


if __name__ == "__main__":
    # Extract law reviews with 60-80% Jaccard
    extract_marginal_law_reviews(min_jaccard=60.0, max_jaccard=80.0)

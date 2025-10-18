#!/usr/bin/env python3
"""
HTML-PDF Pair Validation Script

Validates that HTML and PDF pairs are actually the same document by comparing text overlap.
"""

import re
import sys
from pathlib import Path

try:
    import pypdf
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Required packages not installed")
    print("Run: pip install pypdf beautifulsoup4")
    sys.exit(1)

# Paths
REPO_ROOT = Path("/Users/donaldbraman/Documents/GitHub/docling-testing")
HTML_DIR = REPO_ROOT / "data/raw_html"
PDF_DIR = REPO_ROOT / "data/raw_pdf"


def extract_text_from_html(html_path: Path) -> str:
    """Extract clean text from HTML file."""
    try:
        with open(html_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)

        return text.lower()

    except Exception as e:
        print(f"  Error extracting HTML: {e}")
        return ""


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF file."""
    try:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + " "

        return text.lower()

    except Exception as e:
        print(f"  Error extracting PDF: {e}")
        return ""


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    # Remove numbers (page numbers, years can differ)
    text = re.sub(r"\d+", "", text)
    return text.strip()


def get_word_set(text: str, min_length: int = 4) -> set:
    """Get set of significant words from text."""
    words = text.split()
    # Filter out very short words (articles, prepositions)
    significant_words = {w for w in words if len(w) >= min_length}
    return significant_words


def calculate_overlap(html_text: str, pdf_text: str) -> dict:
    """Calculate text overlap between HTML and PDF."""
    # Normalize texts
    html_norm = normalize_text(html_text)
    pdf_norm = normalize_text(pdf_text)

    # Get word sets
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

    # Calculate Jaccard similarity
    intersection = html_words & pdf_words
    union = html_words | pdf_words
    jaccard = len(intersection) / len(union) if union else 0

    # Calculate overlap ratio (how much of smaller set is in larger)
    smaller_set = min(len(html_words), len(pdf_words))
    overlap_ratio = len(intersection) / smaller_set if smaller_set > 0 else 0

    return {
        "jaccard_similarity": jaccard,
        "overlap_ratio": overlap_ratio,
        "common_words": len(intersection),
        "html_words": len(html_words),
        "pdf_words": len(pdf_words),
    }


def extract_title_from_html(html_text: str) -> str:
    """Extract potential title from HTML (first significant line)."""
    lines = [line.strip() for line in html_text.split("\n") if line.strip()]
    # Look for first substantial line (likely title)
    for line in lines[:10]:
        if 10 < len(line) < 200 and not line.startswith("http"):
            return line[:100]
    return "No title found"


def extract_title_from_pdf(pdf_text: str) -> str:
    """Extract potential title from PDF (first significant line)."""
    lines = [line.strip() for line in pdf_text.split("\n") if line.strip()]
    # Look for first substantial line (likely title)
    for line in lines[:10]:
        if 10 < len(line) < 200:
            return line[:100]
    return "No title found"


def find_pairs() -> list[tuple[Path, Path]]:
    """Find all HTML-PDF pairs by matching filenames."""
    pairs = []

    for html_file in sorted(HTML_DIR.glob("*.html")):
        # Try to find matching PDF
        base_name = html_file.stem
        pdf_file = PDF_DIR / f"{base_name}.pdf"

        if pdf_file.exists():
            pairs.append((html_file, pdf_file))

    return pairs


def validate_pair(html_path: Path, pdf_path: Path, verbose: bool = False) -> dict:
    """Validate a single HTML-PDF pair."""
    print(f"\nValidating: {html_path.name}")

    # Extract texts
    html_text = extract_text_from_html(html_path)
    pdf_text = extract_text_from_pdf(pdf_path)

    if not html_text or not pdf_text:
        print("  ❌ Failed to extract text from one or both files")
        return {
            "html_file": html_path.name,
            "pdf_file": pdf_path.name,
            "status": "extraction_failed",
            "overlap": None,
        }

    # Calculate overlap
    overlap = calculate_overlap(html_text, pdf_text)

    # Determine status
    jaccard = overlap["jaccard_similarity"]
    overlap_ratio = overlap["overlap_ratio"]

    if jaccard >= 0.6 or overlap_ratio >= 0.7:
        status = "✅ MATCH"
    elif jaccard >= 0.4 or overlap_ratio >= 0.5:
        status = "⚠️  PARTIAL MATCH"
    else:
        status = "❌ MISMATCH"

    print(f"  {status}")
    print(f"  Jaccard similarity: {jaccard:.2%}")
    print(f"  Overlap ratio: {overlap_ratio:.2%}")
    print(f"  Common words: {overlap['common_words']:,}")
    print(f"  HTML words: {overlap['html_words']:,} | PDF words: {overlap['pdf_words']:,}")

    if verbose or status == "❌ MISMATCH":
        # Show potential titles for comparison
        html_title = extract_title_from_html(html_text)
        pdf_title = extract_title_from_pdf(pdf_text)
        print(f"\n  HTML title: {html_title}")
        print(f"  PDF title:  {pdf_title}")

    return {
        "html_file": html_path.name,
        "pdf_file": pdf_path.name,
        "status": status,
        "jaccard": jaccard,
        "overlap_ratio": overlap_ratio,
        "overlap": overlap,
    }


def main():
    print("=" * 80)
    print("HTML-PDF PAIR VALIDATION")
    print("=" * 80)

    # Find all pairs
    pairs = find_pairs()

    if not pairs:
        print("No HTML-PDF pairs found!")
        return 1

    print(f"\nFound {len(pairs)} HTML-PDF pairs to validate")
    print("=" * 80)

    # Validate each pair
    results = []
    for html_path, pdf_path in pairs:
        result = validate_pair(html_path, pdf_path, verbose=False)
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    matches = [r for r in results if "✅" in r["status"]]
    partial = [r for r in results if "⚠️" in r["status"]]
    mismatches = [r for r in results if "❌" in r["status"]]

    print(f"\nTotal pairs: {len(results)}")
    print(f"  ✅ Matches: {len(matches)} ({100 * len(matches) / len(results):.1f}%)")
    print(f"  ⚠️  Partial matches: {len(partial)} ({100 * len(partial) / len(results):.1f}%)")
    print(f"  ❌ Mismatches: {len(mismatches)} ({100 * len(mismatches) / len(results):.1f}%)")

    if mismatches:
        print("\n" + "=" * 80)
        print("MISMATCHED PAIRS (Review Required)")
        print("=" * 80)
        for r in mismatches:
            if r["overlap"]:
                print(f"\n{r['html_file']}")
                print(f"  Jaccard: {r['jaccard']:.2%} | Overlap: {r['overlap_ratio']:.2%}")
                print(f"  Common words: {r['overlap']['common_words']:,}")

    if partial:
        print("\n" + "=" * 80)
        print("PARTIAL MATCHES (May Need Review)")
        print("=" * 80)
        for r in partial:
            if r["overlap"]:
                print(f"\n{r['html_file']}")
                print(f"  Jaccard: {r['jaccard']:.2%} | Overlap: {r['overlap_ratio']:.2%}")

    # Quality metrics
    if results:
        avg_jaccard = sum(r["jaccard"] for r in results if r["overlap"]) / len(
            [r for r in results if r["overlap"]]
        )
        avg_overlap = sum(r["overlap_ratio"] for r in results if r["overlap"]) / len(
            [r for r in results if r["overlap"]]
        )

        print("\n" + "=" * 80)
        print("QUALITY METRICS")
        print("=" * 80)
        print(f"Average Jaccard similarity: {avg_jaccard:.2%}")
        print(f"Average overlap ratio: {avg_overlap:.2%}")

    print("\n" + "=" * 80)

    # Return exit code based on mismatches
    if mismatches:
        print("\n⚠️  WARNING: Found mismatched pairs that should be reviewed")
        return 1
    else:
        print("\n✅ All pairs validated successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

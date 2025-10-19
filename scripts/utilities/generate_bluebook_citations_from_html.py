#!/usr/bin/env python3
"""
Generate Bluebook citations for PDF articles using HTML metadata.

Cross-references HTML files to extract accurate metadata.
"""

import csv
import re
from pathlib import Path

from bs4 import BeautifulSoup


def extract_metadata_from_html(html_path: str) -> dict[str, str | None]:
    """Extract metadata from HTML file."""
    metadata = {
        "author": None,
        "title": None,
        "journal": None,
        "volume": None,
        "page": None,
        "year": None,
    }

    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Extract title from multiple sources
    title = None

    # Try 1: og:title meta tag (most reliable)
    title_tag = soup.find("meta", {"property": "og:title"})
    if title_tag:
        title = title_tag.get("content", "")

    # Try 2: <title> tag
    if not title:
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.text.strip()

    # Try 3: H1 tags (usually the main heading)
    if not title:
        h1_tags = soup.find_all("h1")
        for h1 in h1_tags:
            h1_text = h1.text.strip()
            # Look for substantive H1 (not empty, reasonable length)
            if h1_text and 10 < len(h1_text) < 300:
                title = h1_text
                break

    # Try 4: itemprop headline
    if not title:
        headline_tag = soup.find("meta", {"itemprop": "headline"})
        if headline_tag:
            title = headline_tag.get("content", "")

    # Clean up the title
    if title:
        # Remove common suffixes like "— Journal Name" or "| Westlaw"
        title = re.split(r"\s+[—–|-]\s+", title)[0].strip()
        # Remove "| Secondary Sources | National | Westlaw" type patterns
        title = re.sub(r"\s*\|\s*Secondary Sources.*$", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\s*\|\s*Westlaw.*$", "", title, flags=re.IGNORECASE)
        # Clean up any trailing punctuation from splits
        title = title.rstrip("|—–-").strip()
        metadata["title"] = title

    # Extract year from date published (multiple patterns)
    date_tag = soup.find("meta", {"itemprop": "datePublished"}) or soup.find(
        "meta", {"property": "article:published_time"}
    )
    if date_tag:
        date_str = date_tag.get("content", "")
        year_match = re.search(r"\b(20\d{2}|19\d{2})\b", date_str)
        if year_match:
            metadata["year"] = year_match.group(1)

    # Get body text to search for additional metadata
    body_text = soup.get_text()

    # Extract author - look for pattern "Name*" or "By Name" or "Note - by Name"
    # Common pattern: author name followed by asterisk on early lines
    lines = body_text.split("\n")
    for i, line in enumerate(lines[:200]):  # Check first 200 lines
        line = line.strip()

        # Skip short lines and common non-author text
        if len(line) < 5 or len(line) > 200:
            continue

        # Pattern 1: Name with asterisk (e.g., "Andrew Albright*")
        author_match = re.search(
            r"\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[*†]",
            line,
        )
        if author_match:
            metadata["author"] = author_match.group(1).strip()
            break

        # Pattern 2: "By FirstName LastName" or "by FirstName LastName"
        author_match = re.search(
            r"(?:^By |^by |- by )\s*([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            line,
        )
        if author_match:
            metadata["author"] = author_match.group(1).strip()
            break

    # Extract volume - look for patterns like "Vol. 113" or "113 LAW REVIEW"
    volume_match = re.search(r"(?:Vol\.|Volume)\s*(\d+)", body_text, re.IGNORECASE)
    if volume_match:
        metadata["volume"] = volume_match.group(1)
    else:
        # Try pattern like "[Vol. 113:801"
        volume_match = re.search(r"\[Vol\.\s*(\d+):", body_text)
        if volume_match:
            metadata["volume"] = volume_match.group(1)

    # Extract page number - multiple patterns
    # Pattern 1: [Vol. 113:801] format
    page_match = re.search(r"\[Vol\.\s*\d+:(\d+)", body_text)
    if page_match:
        metadata["page"] = page_match.group(1)
    else:
        # Pattern 2: Citation format like "101 Tex. L. Rev. 358"
        # Look for volume + journal + page
        if metadata.get("volume") and metadata.get("journal"):
            journal_abbrev = metadata["journal"].replace(".", r"\.")  # Escape dots
            pattern = rf"{metadata['volume']}\s+{journal_abbrev}\s+(\d{{1,4}})"
            page_match = re.search(pattern, body_text[:5000])
            if page_match:
                metadata["page"] = page_match.group(1)

    # Pattern 3: Page range format (fallback)
    if not metadata.get("page"):
        page_match = re.search(r"\b(\d{1,4})\s*[-–]\s*\d{1,4}\b", body_text[:5000])
        if page_match:
            metadata["page"] = page_match.group(1)

    # Extract journal name from meta or body
    text_upper = body_text[:3000].upper()

    journal_patterns = [
        (r"HARVARD LAW REVIEW", "Harv. L. Rev."),
        (r"YALE LAW JOURNAL", "Yale L.J."),
        (r"STANFORD LAW REVIEW", "Stan. L. Rev."),
        (r"CALIFORNIA LAW REVIEW", "Cal. L. Rev."),
        (r"TEXAS LAW REVIEW", "Tex. L. Rev."),
        (r"MICHIGAN LAW REVIEW", "Mich. L. Rev."),
        (r"VIRGINIA LAW REVIEW", "Va. L. Rev."),
        (r"WISCONSIN LAW REVIEW", "Wis. L. Rev."),
        (r"BOSTON UNIVERSITY LAW REVIEW", "B.U. L. Rev."),
        (r"SOUTHERN CALIFORNIA LAW REVIEW", "S. Cal. L. Rev."),
        (r"UCLA LAW REVIEW", "UCLA L. Rev."),
        (r"SUPREME COURT REVIEW", "Sup. Ct. Rev."),
        (r"COLUMBIA LAW REVIEW", "Colum. L. Rev."),
        (r"NEW YORK UNIVERSITY LAW REVIEW", "N.Y.U. L. Rev."),
        (r"NORTHWESTERN UNIVERSITY LAW REVIEW", "Nw. U. L. Rev."),
    ]

    for pattern, abbrev in journal_patterns:
        if re.search(pattern, text_upper):
            metadata["journal"] = abbrev
            break

    # If no journal found, try from filename
    if not metadata["journal"]:
        filename = Path(html_path).stem
        journal_filename_patterns = {
            "harvard_law_review": "Harv. L. Rev.",
            "california_law_review": "Cal. L. Rev.",
            "texas_law_review": "Tex. L. Rev.",
            "michigan_law_review": "Mich. L. Rev.",
            "bu_law_review": "B.U. L. Rev.",
            "usc_law_review": "S. Cal. L. Rev.",
            "ucla_law_review": "UCLA L. Rev.",
            "virginia_law_review": "Va. L. Rev.",
            "wisconsin_law_review": "Wis. L. Rev.",
            "supreme_court_review": "Sup. Ct. Rev.",
        }
        for pattern, abbrev in journal_filename_patterns.items():
            if pattern in filename.lower():
                metadata["journal"] = abbrev
                break

    return metadata


def format_bluebook_citation(metadata: dict[str, str | None]) -> str:
    """Format metadata as a Bluebook citation."""
    parts = []

    # Author (if available)
    if metadata.get("author"):
        parts.append(metadata["author"])

    # Title
    if metadata.get("title"):
        parts.append(metadata["title"])

    # Volume Journal Page
    citation_parts = []
    if metadata.get("volume"):
        citation_parts.append(metadata["volume"])
    if metadata.get("journal"):
        citation_parts.append(metadata["journal"])
    if metadata.get("page"):
        citation_parts.append(metadata["page"])

    if citation_parts:
        parts.append(" ".join(citation_parts))

    # Year
    if metadata.get("year"):
        parts.append(f"({metadata['year']})")

    if len(parts) >= 2:
        return ", ".join(parts[:-1]) + " " + parts[-1] + "."
    else:
        return "[Incomplete metadata]"


def process_directories(pdf_dir: str, html_dir: str, output_csv: str):
    """Process PDFs and cross-reference with HTML files."""
    pdf_files = sorted(Path(pdf_dir).glob("*.pdf"))
    html_dir_path = Path(html_dir)

    results = []

    print(f"Processing {len(pdf_files)} PDF files with HTML cross-reference...")

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")

        # Find corresponding HTML file
        html_filename = pdf_path.stem + ".html"
        html_path = html_dir_path / html_filename

        if html_path.exists():
            # Extract metadata from HTML
            metadata = extract_metadata_from_html(str(html_path))
            metadata["filename"] = pdf_path.name
        else:
            print(f"  ⚠️  No HTML file found for {pdf_path.name}")
            metadata = {
                "filename": pdf_path.name,
                "author": None,
                "title": None,
                "journal": None,
                "volume": None,
                "page": None,
                "year": None,
            }

        # Format citation
        citation = format_bluebook_citation(metadata)

        results.append(
            {
                "filename": pdf_path.name,
                "citation": citation,
                "author": metadata.get("author", ""),
                "title": metadata.get("title", ""),
                "journal": metadata.get("journal", ""),
                "volume": metadata.get("volume", ""),
                "page": metadata.get("page", ""),
                "year": metadata.get("year", ""),
            }
        )

    # Write to CSV
    print(f"\nWriting results to {output_csv}")
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "filename",
            "citation",
            "author",
            "title",
            "journal",
            "volume",
            "page",
            "year",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"✓ Done! Generated {len(results)} citations")

    # Print statistics
    print("\n=== STATISTICS ===")
    print(f"Total: {len(results)}")
    print(f"With author: {sum(1 for r in results if r['author'])}")
    print(f"With title: {sum(1 for r in results if r['title'])}")
    print(f"With journal: {sum(1 for r in results if r['journal'])}")
    print(f"With volume: {sum(1 for r in results if r['volume'])}")
    print(f"With page: {sum(1 for r in results if r['page'])}")
    print(f"With year: {sum(1 for r in results if r['year'])}")


def main():
    pdf_dir = "/Users/donaldbraman/Documents/GitHub/docling-testing/data/v3_data/raw_pdf"
    html_dir = "/Users/donaldbraman/Documents/GitHub/docling-testing/data/v3_data/raw_html"
    output_csv = "/Users/donaldbraman/Downloads/bluebook_citations.csv"

    process_directories(pdf_dir, html_dir, output_csv)


if __name__ == "__main__":
    main()

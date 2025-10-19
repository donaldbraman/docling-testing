#!/usr/bin/env python3
"""
Generate Bluebook citations for PDF articles.

Extracts metadata from PDFs and formats them as Bluebook citations.
"""

import csv
import re
from pathlib import Path

import PyPDF2


def extract_text_from_first_pages(pdf_path: str, num_pages: int = 5) -> str:
    """Extract text from the first few pages of a PDF."""
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for i in range(min(num_pages, len(reader.pages))):
                text += reader.pages[i].extract_text() + "\n"
            return text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""


def parse_metadata(text: str, filename: str) -> dict[str, str | None]:
    """
    Parse metadata from PDF text to extract citation components.

    Returns dict with: author, title, journal, volume, page, year
    """
    metadata = {
        "author": None,
        "title": None,
        "journal": None,
        "volume": None,
        "page": None,
        "year": None,
        "filename": filename,
    }

    # Extract year (4-digit number, typically in parentheses or at end)
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if year_match:
        metadata["year"] = year_match.group(1)

    # Extract volume and page pattern like "123 HARV. L. REV. 456"
    # Common patterns: "Vol. 123, No. 4" or just "123"
    volume_match = re.search(r"(?:Vol\.|Volume)\s*(\d+)", text, re.IGNORECASE)
    if volume_match:
        metadata["volume"] = volume_match.group(1)
    else:
        # Try to find standalone number before journal name
        vol_match = re.search(
            r"\b(\d{1,3})\s+(?:HARV\.|YALE|STAN\.|CAL\.|TEX\.|MICH\.|VA\.|WIS\.|B\.U\.|USC|UCLA)",
            text,
        )
        if vol_match:
            metadata["volume"] = vol_match.group(1)

    # Extract starting page
    page_match = re.search(r"\b(\d{1,4})\s*[-–]\s*\d{1,4}\b", text)
    if page_match:
        metadata["page"] = page_match.group(1)

    # Extract journal name - comprehensive search
    text_upper = text.upper()

    # First try filename patterns
    journal_patterns_filename = {
        "harvard_law_review": "Harv. L. Rev.",
        "yale_law_journal": "Yale L.J.",
        "stanford_law_review": "Stan. L. Rev.",
        "california_law_review": "Cal. L. Rev.",
        "texas_law_review": "Tex. L. Rev.",
        "michigan_law_review": "Mich. L. Rev.",
        "virginia_law_review": "Va. L. Rev.",
        "wisconsin_law_review": "Wis. L. Rev.",
        "bu_law_review": "B.U. L. Rev.",
        "usc_law_review": "S. Cal. L. Rev.",
        "ucla_law_review": "UCLA L. Rev.",
        "supreme_court_review": "Sup. Ct. Rev.",
    }

    filename_lower = filename.lower()
    for pattern, abbrev in journal_patterns_filename.items():
        if pattern in filename_lower:
            metadata["journal"] = abbrev
            break

    # Then try text patterns (both full names and abbreviations)
    if not metadata["journal"]:
        journal_patterns_text = [
            # (pattern_to_search, abbreviation_or_full_name)
            (r"HARVARD LAW REVIEW", "Harv. L. Rev."),
            (r"YALE LAW JOURNAL", "Yale L.J."),
            (r"STANFORD LAW REVIEW", "Stan. L. Rev."),
            (r"CALIFORNIA LAW REVIEW", "Cal. L. Rev."),
            (r"TEXAS LAW REVIEW", "Tex. L. Rev."),
            (r"MICHIGAN LAW REVIEW", "Mich. L. Rev."),
            (r"VIRGINIA LAW REVIEW", "Va. L. Rev."),
            (r"WISCONSIN LAW REVIEW", "Wis. L. Rev."),
            (r"BOSTON UNIVERSITY LAW REVIEW", "B.U. L. Rev."),
            (r"B\.U\. LAW REVIEW", "B.U. L. Rev."),
            (r"SOUTHERN CALIFORNIA LAW REVIEW", "S. Cal. L. Rev."),
            (r"USC LAW REVIEW", "S. Cal. L. Rev."),
            (r"UCLA LAW REVIEW", "UCLA L. Rev."),
            (r"SUPREME COURT REVIEW", "Sup. Ct. Rev."),
            (r"COLUMBIA LAW REVIEW", "Colum. L. Rev."),
            (r"NYU LAW REVIEW", "N.Y.U. L. Rev."),
            (r"NEW YORK UNIVERSITY LAW REVIEW", "N.Y.U. L. Rev."),
            (r"UNIVERSITY OF PENNSYLVANIA LAW REVIEW", "U. Pa. L. Rev."),
            (r"PENN LAW REVIEW", "U. Pa. L. Rev."),
            (r"NORTHWESTERN UNIVERSITY LAW REVIEW", "Nw. U. L. Rev."),
            (r"DUKE LAW JOURNAL", "Duke L.J."),
            (r"GEORGETOWN LAW JOURNAL", "Geo. L.J."),
            (r"CORNELL LAW REVIEW", "Cornell L. Rev."),
            (r"VANDERBILT LAW REVIEW", "Vand. L. Rev."),
            (r"MINNESOTA LAW REVIEW", "Minn. L. Rev."),
            (r"IOWA LAW REVIEW", "Iowa L. Rev."),
            (r"ARIZONA STATE LAW JOURNAL", "Ariz. St. L.J."),
            (r"FLORIDA LAW REVIEW", "Fla. L. Rev."),
            (r"WASHINGTON LAW REVIEW", "Wash. L. Rev."),
            (r"EMORY LAW JOURNAL", "Emory L.J."),
        ]

        for pattern, abbrev in journal_patterns_text:
            if re.search(pattern, text_upper):
                metadata["journal"] = abbrev
                break

    # If still not found, try to find ANY "X LAW REVIEW" or "X LAW JOURNAL" pattern
    if not metadata["journal"]:
        # Look for patterns like "THE UNIVERSITY OF X LAW REVIEW"
        journal_match = re.search(
            r"(?:THE\s+)?(?:UNIVERSITY\s+OF\s+)?([A-Z][A-Z\s&]+?)\s+LAW\s+(?:REVIEW|JOURNAL)",
            text_upper,
        )
        if journal_match:
            # Extract the journal name and use it without abbreviation
            journal_name = journal_match.group(0).title()
            metadata["journal"] = journal_name
        else:
            # Try simpler pattern: "X LAW REVIEW"
            journal_match = re.search(
                r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+Law\s+(?:Review|Journal)", text
            )
            if journal_match:
                metadata["journal"] = journal_match.group(0)

    # Extract title - more comprehensive approach
    lines = text.split("\n")

    # Try multiple strategies to find the title
    title_candidates = []

    # Strategy 1: Look for all-caps multi-word lines (traditional article titles)
    for i, line in enumerate(lines[:50]):  # Check first 50 lines
        line = line.strip()
        # Skip very short lines, single words, and common section headers
        if len(line) < 15:
            continue
        if line.upper() in ["ARTICLE", "NOTE", "ESSAY", "COMMENT", "BOOK REVIEW", "INTRODUCTION"]:
            continue

        # Check if it's mostly uppercase and substantive
        if line.isupper() and len(line.split()) >= 3 and len(line) < 300:
            # Skip if it's a journal name or author affiliation
            line_lower = line.lower()
            skip_patterns = [
                "law review",
                "court review",
                "university",
                "professor",
                "law school",
                "volume",
                "number",
                "copyright",
                "reserved",
                "foundation",
            ]
            if not any(pattern in line_lower for pattern in skip_patterns):
                # Clean up the title
                title = line.title()
                # Remove common artifacts
                title = re.sub(r"^\d+\s*", "", title)  # Remove leading numbers
                title = re.sub(r"\s+", " ", title).strip()  # Normalize whitespace
                if len(title) > 10:
                    title_candidates.append((i, title, "caps"))

    # Strategy 2: Look for lines after ARTICLE/NOTE/ESSAY markers
    for i, line in enumerate(lines[:50]):
        line_upper = line.strip().upper()
        if line_upper in ["ARTICLE", "NOTE", "ESSAY", "COMMENT"]:
            # Next substantive line might be the title
            for j in range(i + 1, min(i + 10, len(lines))):
                next_line = lines[j].strip()
                if len(next_line) >= 15 and next_line.isupper():
                    title = next_line.title()
                    title = re.sub(r"^\d+\s*", "", title)
                    title = re.sub(r"\s+", " ", title).strip()
                    if len(title) > 10:
                        title_candidates.append((j, title, "after_marker"))
                        break

    # Strategy 3: Look for title case lines (less common but possible)
    for i, line in enumerate(lines[5:40]):  # Skip first few header lines
        line = line.strip()
        # Look for substantial title-case text
        if len(line) >= 20 and len(line.split()) >= 4:
            # Check if it's title case (most words start with capital)
            words = line.split()
            capital_words = sum(1 for w in words if w and w[0].isupper())
            if capital_words >= len(words) * 0.6:  # At least 60% capitalized
                line_lower = line.lower()
                skip_patterns = [
                    "law review",
                    "court review",
                    "university",
                    "professor",
                    "volume",
                    "number",
                    "copyright",
                ]
                if not any(pattern in line_lower for pattern in skip_patterns):
                    title = re.sub(r"^\d+\s*", "", line)
                    title = re.sub(r"\s+", " ", title).strip()
                    if len(title) > 10:
                        title_candidates.append((i + 5, title, "title_case"))

    # Pick the best title candidate (prefer earlier in document, prefer caps method)
    if title_candidates:
        # Sort by: method priority (caps > after_marker > title_case), then by position
        method_priority = {"caps": 0, "after_marker": 1, "title_case": 2}
        title_candidates.sort(key=lambda x: (method_priority[x[2]], x[0]))
        metadata["title"] = title_candidates[0][1]

    # Strategy 4: If no title found, try to extract from filename
    if not metadata["title"]:
        # Remove journal prefix and clean up filename
        title_from_filename = filename
        # Remove common prefixes
        for prefix in [
            "harvard_law_review_",
            "california_law_review_",
            "texas_law_review_",
            "michigan_law_review_",
            "bu_law_review_",
            "usc_law_review_",
            "ucla_law_review_",
            "virginia_law_review_",
            "wisconsin_law_review_",
            "supreme_court_review_",
        ]:
            if title_from_filename.lower().startswith(prefix):
                title_from_filename = title_from_filename[len(prefix) :]
                break

        # Remove .pdf and convert underscores/hyphens to spaces
        title_from_filename = title_from_filename.replace(".pdf", "")
        title_from_filename = title_from_filename.replace("_", " ").replace("-", " ")
        # Title case it
        title_from_filename = title_from_filename.title()
        # Remove "The Supreme Court Review Vol 2024" style suffixes
        title_from_filename = re.sub(
            r"\s+The Supreme Court Review.*$", "", title_from_filename, flags=re.IGNORECASE
        )
        title_from_filename = re.sub(
            r"\s+Vol\s+\d+.*$", "", title_from_filename, flags=re.IGNORECASE
        )
        title_from_filename = title_from_filename.strip()

        if len(title_from_filename) >= 10:
            metadata["title"] = title_from_filename

    # Extract author - typically appears before or after title
    # Look for patterns like "By FirstName LastName" or "FirstName LastName*"
    author_match = re.search(r"(?:By|by)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)", text)
    if author_match:
        metadata["author"] = author_match.group(1)
    else:
        # Look for name with asterisk or dagger (common in law reviews)
        author_match = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)[*†]", text)
        if author_match:
            metadata["author"] = author_match.group(1)

    return metadata


def format_bluebook_citation(metadata: dict[str, str | None]) -> str:
    """
    Format metadata as a Bluebook citation.

    Standard format: Author, Title, Volume Journal Page (Year).
    """
    parts = []

    # Author (if available)
    if metadata["author"]:
        parts.append(metadata["author"])

    # Title
    if metadata["title"]:
        parts.append(metadata["title"])

    # Volume Journal Page
    citation_parts = []
    if metadata["volume"]:
        citation_parts.append(metadata["volume"])
    if metadata["journal"]:
        citation_parts.append(metadata["journal"])
    if metadata["page"]:
        citation_parts.append(metadata["page"])

    if citation_parts:
        parts.append(" ".join(citation_parts))

    # Year
    if metadata["year"]:
        parts.append(f"({metadata['year']})")

    if len(parts) >= 2:  # At least title and one other element
        return ", ".join(parts[:-1]) + " " + parts[-1] + "."
    else:
        # Fallback: just use filename if we couldn't parse enough
        return f"[Unable to parse: {metadata['filename']}]"


def process_directory(pdf_dir: str, output_csv: str):
    """
    Process all PDFs in directory and generate CSV with citations.
    """
    pdf_files = sorted(Path(pdf_dir).glob("*.pdf"))

    results = []

    print(f"Processing {len(pdf_files)} PDF files...")

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")

        # Extract text from first pages
        text = extract_text_from_first_pages(str(pdf_path))

        # Parse metadata
        metadata = parse_metadata(text, pdf_path.name)

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


def main():
    pdf_dir = "/Users/donaldbraman/Documents/GitHub/docling-testing/data/v3_data/raw_pdf"
    output_csv = "/Users/donaldbraman/Downloads/bluebook_citations.csv"

    process_directory(pdf_dir, output_csv)


if __name__ == "__main__":
    main()

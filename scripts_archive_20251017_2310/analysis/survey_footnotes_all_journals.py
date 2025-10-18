#!/usr/bin/env python3
"""Survey footnote patterns from one representative file per journal."""

from pathlib import Path

from bs4 import BeautifulSoup


def identify_journal(filename: str) -> str:
    """Extract journal name from filename."""
    # Get first part before underscore
    parts = filename.split("_")
    if not parts:
        return "unknown"

    # Handle multi-word journal names
    if parts[0] in ["bu", "boston"]:
        return "BU Law Review"
    elif parts[0] == "california":
        return "California Law Review"
    elif parts[0] == "michigan":
        return "Michigan Law Review"
    elif parts[0] == "supreme":
        return "Supreme Court Review"
    elif parts[0] == "harvard":
        return "Harvard Law Review"
    elif parts[0] == "yale":
        return "Yale Law Journal"
    elif parts[0] == "stanford":
        return "Stanford Law Review"
    elif parts[0] == "texas":
        return "Texas Law Review"
    elif parts[0] == "duke":
        return "Duke Law Journal"
    elif parts[0] == "georgetown":
        return "Georgetown Law Journal"
    elif parts[0] == "nyu":
        return "NYU Law Review"
    elif parts[0] == "columbia":
        return "Columbia Law Review"
    elif parts[0] == "chicago":
        return "University of Chicago Law Review"
    elif parts[0] == "northwestern":
        return "Northwestern Law Review"
    elif parts[0] == "virginia":
        return "Virginia Law Review"
    elif parts[0] == "penn" or parts[0] == "upenn":
        return "Penn Law Review"
    elif parts[0] == "ucla":
        return "UCLA Law Review"
    elif parts[0] == "cornell":
        return "Cornell Law Review"
    elif parts[0] == "vanderbilt":
        return "Vanderbilt Law Review"
    elif parts[0] == "minnesota":
        return "Minnesota Law Review"
    elif parts[0] == "washington" or parts[0] == "washu":
        return "Washington University Law Review"
    elif parts[0] == "florida":
        return "Florida Law Review"
    elif parts[0] == "indiana":
        return "Indiana Law Journal"
    elif parts[0] == "iowa":
        return "Iowa Law Review"
    elif parts[0] == "wisconsin":
        return "Wisconsin Law Review"
    elif parts[0] == "usc":
        return "USC Law Review"
    elif parts[0] == "gwu":
        return "GWU Law Review"
    elif parts[0] == "fordham":
        return "Fordham Law Review"
    else:
        return parts[0].title()


def survey_footnotes(html_path: Path) -> dict:
    """Survey footnote patterns in HTML file."""
    try:
        with open(html_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except (UnicodeDecodeError, Exception) as e:
        return {
            "journal": identify_journal(html_path.name),
            "file": html_path.name,
            "patterns": [f"Error reading file: {e}"],
        }

    result = {"journal": identify_journal(html_path.name), "file": html_path.name, "patterns": []}

    # 1. Check for [N] pattern paragraphs
    bracket_count = 0
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and text[0] == "[" and len(text) > 2 and text[1].isdigit():
            bracket_count += 1

    if bracket_count > 0:
        result["patterns"].append(f"{bracket_count} <p> tags starting with [N]")

    # 2. Check for Michigan modern-footnotes
    modern_fn = soup.find_all("span", class_="modern-footnotes-footnote__note")
    if modern_fn:
        result["patterns"].append(
            f"{len(modern_fn)} <span class='modern-footnotes-footnote__note'>"
        )

    # 3. Check for Supreme Court NLM_fn
    nlm_fn = soup.find_all("span", class_="NLM_fn")
    if nlm_fn:
        result["patterns"].append(f"{len(nlm_fn)} <span class='NLM_fn'>")

    # 4. Check for other footnote classes
    fn_elements = soup.find_all(class_=lambda x: x and "footnote" in " ".join(x).lower())
    # Exclude modern-footnotes already counted
    fn_elements = [
        e for e in fn_elements if "modern-footnotes" not in " ".join(e.get("class", [])).lower()
    ]
    if fn_elements:
        classes = set()
        for elem in fn_elements[:5]:  # Sample first 5
            classes.add(" ".join(elem.get("class", [])))
        result["patterns"].append(
            f"{len(fn_elements)} elements with 'footnote' class: {list(classes)[:2]}"
        )

    # 5. Check for <sup> tags (common for footnote references)
    sup_tags = soup.find_all("sup")
    if sup_tags and len(sup_tags) > 5:  # More than 5 suggests footnote references
        result["patterns"].append(f"{len(sup_tags)} <sup> tags")

    if not result["patterns"]:
        result["patterns"].append("No clear footnote pattern detected")

    return result


def main():
    """Survey one file per journal."""
    print("FOOTNOTE PATTERNS ACROSS ALL JOURNALS")
    print("=" * 80)
    print("(examining one representative file per journal)\n")

    # Find all HTML files
    html_files = []
    for path in Path("data").rglob("*.html"):
        # Skip certain directories
        if "archived_abstract_only" in str(path):
            continue
        if "cover_pages" in str(path):
            continue
        if "pdf_content_visualizations" in str(path):
            continue
        html_files.append(path)

    # Group by journal
    by_journal = {}
    for html_path in html_files:
        journal = identify_journal(html_path.name)
        if journal not in by_journal:
            by_journal[journal] = []
        by_journal[journal].append(html_path)

    # Survey one file per journal
    results = []
    for journal in sorted(by_journal.keys()):
        files = by_journal[journal]
        # Pick first file
        sample_file = files[0]
        result = survey_footnotes(sample_file)
        results.append(result)

    # Report
    for result in sorted(results, key=lambda x: x["journal"]):
        print(f"{result['journal']}")
        print(f"  File: {result['file']}")
        print(f"  Total files: {len(by_journal[result['journal']])}")
        for pattern in result["patterns"]:
            print(f"    • {pattern}")
        print()

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total journals surveyed: {len(results)}")
    print(f"Total HTML files examined: {len(html_files)}")


if __name__ == "__main__":
    main()

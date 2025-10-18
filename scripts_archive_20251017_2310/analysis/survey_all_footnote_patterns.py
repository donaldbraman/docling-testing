#!/usr/bin/env python3
"""Survey footnote patterns across ALL HTML files in corpus."""

from pathlib import Path

from bs4 import BeautifulSoup


def survey_footnote_patterns(html_path: Path) -> dict:
    """Extract footnote pattern information from HTML."""
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Count different footnote indicators
    results = {
        "file": html_path.stem,
        "total_paragraphs": len(soup.find_all("p")),
        "bracket_pattern_paras": 0,  # [1], [2], etc.
        "modern_footnotes_spans": 0,  # Michigan plugin
        "nlm_fn_spans": 0,  # Supreme Court Review
        "other_footnote_classes": 0,
        "footnote_details": [],
    }

    # Check for [N] pattern paragraphs
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and text[0] == "[" and len(text) > 2 and text[1].isdigit():
            results["bracket_pattern_paras"] += 1

    # Check for Michigan modern-footnotes
    modern_fn = soup.find_all("span", class_="modern-footnotes-footnote__note")
    results["modern_footnotes_spans"] = len(modern_fn)

    # Check for Supreme Court NLM_fn
    nlm_fn = soup.find_all("span", class_="NLM_fn")
    results["nlm_fn_spans"] = len(nlm_fn)

    # Check for any other footnote-related classes
    other_fn = soup.find_all(
        class_=lambda x: x
        and "footnote" in " ".join(x).lower()
        and "modern-footnotes" not in " ".join(x).lower()
    )
    results["other_footnote_classes"] = len(other_fn)

    # Determine pattern type
    if results["bracket_pattern_paras"] > 0:
        results["pattern"] = "bracket_paragraphs"
        results["footnote_details"].append(
            f"{results['bracket_pattern_paras']} paragraphs start with [N]"
        )
    elif results["modern_footnotes_spans"] > 0:
        results["pattern"] = "modern_footnotes"
        results["footnote_details"].append(
            f"{results['modern_footnotes_spans']} <span class='modern-footnotes-footnote__note'>"
        )
    elif results["nlm_fn_spans"] > 0:
        results["pattern"] = "nlm_fn"
        results["footnote_details"].append(f"{results['nlm_fn_spans']} <span class='NLM_fn'>")
    else:
        results["pattern"] = "unknown"
        results["footnote_details"].append("No clear footnote pattern detected")

    return results


def main():
    """Survey all HTML files."""
    html_dir = Path("data/raw_html")
    html_files = sorted(html_dir.glob("*.html"))

    print("FOOTNOTE PATTERN SURVEY - ALL CORPUS FILES")
    print("=" * 80)
    print(f"Total HTML files: {len(html_files)}\n")

    # Group by journal
    journals = {
        "BU Law Review Online": [],
        "Michigan Law Review": [],
        "Supreme Court Review": [],
    }

    for html_file in html_files:
        result = survey_footnote_patterns(html_file)

        if "bu_law_review" in html_file.stem:
            journals["BU Law Review Online"].append(result)
        elif "michigan_law_review" in html_file.stem:
            journals["Michigan Law Review"].append(result)
        elif "supreme_court_review" in html_file.stem:
            journals["Supreme Court Review"].append(result)

    # Report by journal
    for journal_name, articles in journals.items():
        if not articles:
            continue

        print(f"\n{'=' * 80}")
        print(f"{journal_name}")
        print(f"{'=' * 80}")
        print(f"Articles: {len(articles)}\n")

        # Check pattern consistency
        patterns = {a["pattern"] for a in articles}
        if len(patterns) == 1:
            print(f"✓ CONSISTENT PATTERN: {list(patterns)[0]}")
        else:
            print(f"⚠ INCONSISTENT PATTERNS: {patterns}")

        print()

        # Show each article
        for article in articles:
            print(f"  {article['file']}")
            print(f"    Pattern: {article['pattern']}")
            print(f"    Total paragraphs: {article['total_paragraphs']}")
            for detail in article["footnote_details"]:
                print(f"    {detail}")
            print()

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}\n")

    for journal_name, articles in journals.items():
        if not articles:
            continue
        pattern = articles[0]["pattern"]
        print(f"{journal_name} ({len(articles)} articles): {pattern}")

    print("\nPATTERN DETAILS:")
    print("-" * 80)
    print("  bracket_paragraphs: Footnotes in plain <p> tags starting with [1], [2], etc.")
    print("  modern_footnotes:   Footnotes in <span class='modern-footnotes-footnote__note'>")
    print("  nlm_fn:             Footnotes in <span class='NLM_fn'>")


if __name__ == "__main__":
    main()

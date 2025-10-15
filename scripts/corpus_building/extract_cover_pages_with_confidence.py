#!/usr/bin/env python3
"""
Extract cover pages with confidence scores for manual review.
"""

import re
from pathlib import Path

import pandas as pd
from docling.document_converter import DocumentConverter


def detect_cover_type_with_confidence(text: str) -> tuple[str | None, int, list[str]]:
    """Detect cover page type with confidence score.

    Returns:
        (cover_type, pattern_count, matched_patterns)
    """
    # HeinOnline cover
    heinonline_patterns = {
        "Downloaded from HeinOnline": r"Downloaded from HeinOnline",
        "SOURCE: Content Downloaded": r"SOURCE: Content Downloaded",
        "Citations:": r"Citations:",
        "Bluebook": r"Bluebook.*ed\.",
        "ALWD": r"ALWD.*ed\.",
        "heinonline.org": r"https://heinonline\.org",
    }
    hein_matches = [
        name for name, pattern in heinonline_patterns.items() if re.search(pattern, text, re.I)
    ]
    if len(hein_matches) >= 2:
        return "heinonline", len(hein_matches), hein_matches

    # JSTOR cover
    jstor_patterns = {
        "JSTOR keyword": r"JSTOR",
        "jstor.org": r"www\.jstor\.org",
        "accessed via jstor": r"accessed.*jstor",
        "Your use of JSTOR": r"Your use of.*JSTOR",
        "Terms and Conditions": r"Terms and Conditions of Use",
        "not-for-profit": r"JSTOR is a not-for-profit",
    }
    jstor_matches = [
        name for name, pattern in jstor_patterns.items() if re.search(pattern, text, re.I)
    ]
    if len(jstor_matches) >= 2:
        return "jstor", len(jstor_matches), jstor_matches

    # Westlaw cover
    westlaw_patterns = {
        "Westlaw": r"Westlaw",
        "Thomson Reuters": r"Thomson Reuters",
        "West Reporter": r"West Reporter",
        "convenience": r"For the convenience of the user",
        "permission": r"Reproduced with permission",
    }
    westlaw_matches = [
        name for name, pattern in westlaw_patterns.items() if re.search(pattern, text, re.I)
    ]
    if len(westlaw_matches) >= 2:
        return "westlaw", len(westlaw_matches), westlaw_matches

    # LexisNexis cover
    lexis_patterns = {
        "LexisNexis": r"LexisNexis",
        "Lexis Advance": r"Lexis Advance",
        "Matthew Bender": r"Matthew Bender",
        "Copyright LexisNexis": r"Copyright.*LexisNexis",
    }
    lexis_matches = [
        name for name, pattern in lexis_patterns.items() if re.search(pattern, text, re.I)
    ]
    if len(lexis_matches) >= 2:
        return "lexisnexis", len(lexis_matches), lexis_matches

    return None, 0, []


def main():
    """Extract cover pages with confidence tracking."""
    pdf_dir = Path("/Users/donaldbraman/Documents/GitHub/12-factor-agents/test_corpus/pdfs")
    converter = DocumentConverter()

    results = []

    print("Scanning PDFs for cover pages...")
    print("=" * 80)

    for i, pdf_path in enumerate(sorted(pdf_dir.glob("*.pdf")), 1):
        try:
            # Extract first page
            result = converter.convert(pdf_path)
            doc_md = result.document.export_to_markdown()
            first_page_text = "\n".join(doc_md.split("\n")[:100])

            # Detect with confidence
            cover_type, pattern_count, matches = detect_cover_type_with_confidence(first_page_text)

            results.append(
                {
                    "filename": pdf_path.name,
                    "cover_type": cover_type or "no_cover",
                    "confidence": pattern_count,
                    "matched_patterns": ", ".join(matches) if matches else "",
                    "first_100_chars": first_page_text[:100].replace("\n", " "),
                }
            )

            # Flag uncertain cases
            if cover_type and pattern_count == 2:
                flag = "⚠️  LOW CONF"
            elif cover_type and pattern_count >= 4:
                flag = "✓ HIGH CONF"
            elif cover_type:
                flag = "✓"
            else:
                flag = "  (no cover)"

            print(f"{i:2d}. {flag} {cover_type or 'none':15s} {pdf_path.name[:50]}")

        except Exception as e:
            print(f"{i:2d}. ✗ ERROR: {pdf_path.name[:50]}")
            results.append(
                {
                    "filename": pdf_path.name,
                    "cover_type": "error",
                    "confidence": 0,
                    "matched_patterns": str(e),
                    "first_100_chars": "",
                }
            )

    # Save results
    df = pd.DataFrame(results)
    output_path = Path(__file__).parent / "data" / "cover_page_analysis.csv"
    df.to_csv(output_path, index=False)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(df["cover_type"].value_counts().to_string())

    # Show uncertain cases
    uncertain = df[(df["cover_type"] != "no_cover") & (df["confidence"] == 2)]
    if len(uncertain) > 0:
        print("\n" + "=" * 80)
        print("⚠️  UNCERTAIN DETECTIONS (only 2 patterns matched)")
        print("=" * 80)
        for _, row in uncertain.iterrows():
            print(f"\n{row['filename']}")
            print(f"  Type: {row['cover_type']}")
            print(f"  Patterns: {row['matched_patterns']}")
            print(f"  Preview: {row['first_100_chars']}")

    # Show no-cover cases
    no_covers = df[df["cover_type"] == "no_cover"]
    if len(no_covers) > 0:
        print("\n" + "=" * 80)
        print(f"📄 NO COVER DETECTED ({len(no_covers)} PDFs)")
        print("=" * 80)
        for _, row in no_covers.iterrows():
            print(f"\n{row['filename']}")
            print(f"  Preview: {row['first_100_chars']}")

    print(f"\n✓ Analysis saved to: {output_path}")


if __name__ == "__main__":
    main()

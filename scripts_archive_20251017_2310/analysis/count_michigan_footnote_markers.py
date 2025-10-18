#!/usr/bin/env python3
"""Count footnote reference markers in Michigan Law Review body text."""

from pathlib import Path

from bs4 import BeautifulSoup


def count_footnote_markers(html_path: Path):
    """Count footnote markers in body text vs footnote content spans."""

    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    print(f"ANALYZING: {html_path.name}")
    print("=" * 80)

    # Find footnote content spans
    modern_fn = soup.find_all("span", class_="modern-footnotes-footnote__note")
    print(f"\n✓ Footnote content spans: {len(modern_fn)}")

    # Find body text container
    wrap = soup.find("div", class_="wrap-wysiwyg")
    if not wrap:
        print("❌ No wrap-wysiwyg div found")
        return

    # Count body paragraphs
    body_paragraphs = wrap.find_all("p", recursive=True)
    print(f"✓ Body paragraphs: {len(body_paragraphs)}")

    # Count footnote reference markers in body
    # Modern-footnotes plugin typically uses <sup> tags or data attributes

    # Method 1: Count <sup> tags in body
    footnote_sups = wrap.find_all("sup")
    print(f"\n<sup> tags in body: {len(footnote_sups)}")
    if footnote_sups:
        print(f"  First 5 examples: {[sup.get_text(strip=True) for sup in footnote_sups[:5]]}")

    # Method 2: Count modern-footnotes reference links
    footnote_links = wrap.find_all(
        "a", class_=lambda x: x and "modern-footnotes" in " ".join(x).lower()
    )
    print(f"\nModern-footnotes reference links in body: {len(footnote_links)}")
    if footnote_links:
        print(f"  First 5 examples: {[link.get('class') for link in footnote_links[:5]]}")

    # Method 3: Count by data-mfn attribute (common in modern-footnotes)
    mfn_elements = wrap.find_all(attrs={"data-mfn": True})
    print(f"\nElements with data-mfn attribute: {len(mfn_elements)}")
    if mfn_elements:
        print(f"  First 5 data-mfn values: {[elem.get('data-mfn') for elem in mfn_elements[:5]]}")

    # Method 4: Show examples of footnote markers
    print("\n" + "=" * 80)
    print("FOOTNOTE MARKER EXAMPLES IN BODY TEXT:")
    print("=" * 80)

    for i, p in enumerate(body_paragraphs[:10]):
        text = p.get_text(separator=" ", strip=True)
        if len(text) < 50:
            continue

        # Check if this paragraph has footnote markers
        markers_in_p = p.find_all("sup")
        links_in_p = p.find_all(
            "a", class_=lambda x: x and "modern-footnotes" in " ".join(x).lower()
        )

        if markers_in_p or links_in_p:
            print(f"\n[Paragraph {i + 1}]")
            print(f"  <sup> tags: {len(markers_in_p)}")
            print(f"  Modern-footnotes links: {len(links_in_p)}")
            print(f"  Text preview: {text[:100]}...")
            if markers_in_p:
                print(f"  Marker text: {[sup.get_text(strip=True) for sup in markers_in_p]}")


if __name__ == "__main__":
    html_path = Path("data/raw_html/michigan_law_review_law_enforcement_privilege.html")
    count_footnote_markers(html_path)

#!/usr/bin/env python3
"""Count footnote reference markers in Supreme Court Review body text."""

from pathlib import Path

from bs4 import BeautifulSoup


def count_footnote_markers(html_path: Path):
    """Count footnote markers in body text vs footnote content spans."""

    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    print(f"ANALYZING: {html_path.name}")
    print("=" * 80)

    # Find footnote content spans
    nlm_fn = soup.find_all("span", class_="NLM_fn")
    print(f"\n✓ NLM_fn footnote content spans: {len(nlm_fn)}")

    # Find article container
    article = soup.find("article")
    if not article:
        print("❌ No <article> tag found")
        return

    # Count body paragraphs (excluding those inside NLM_fn)
    all_paragraphs = article.find_all("p")
    body_paragraphs = [p for p in all_paragraphs if not p.find_parent(class_="NLM_fn")]
    print(f"✓ Body paragraphs: {len(body_paragraphs)}")

    # Count <sup> tags in body (footnote reference markers)
    footnote_sups = []
    for p in body_paragraphs:
        footnote_sups.extend(p.find_all("sup"))

    print(f"\n<sup> tags in body: {len(footnote_sups)}")
    if footnote_sups:
        print(f"  First 10 examples: {[sup.get_text(strip=True) for sup in footnote_sups[:10]]}")

    # Count <a> tags that link to footnotes
    footnote_links = []
    for p in body_paragraphs:
        links = p.find_all("a", href=lambda x: x and "#" in str(x))
        footnote_links.extend(links)

    print(f"\nFootnote reference links in body: {len(footnote_links)}")
    if footnote_links:
        print(f"  First 5 href values: {[link.get('href') for link in footnote_links[:5]]}")

    # Show examples
    print("\n" + "=" * 80)
    print("FOOTNOTE MARKER EXAMPLES IN BODY TEXT:")
    print("=" * 80)

    for i, p in enumerate(body_paragraphs[:10]):
        text = p.get_text(separator=" ", strip=True)
        if len(text) < 50:
            continue

        markers_in_p = p.find_all("sup")
        links_in_p = p.find_all("a", href=lambda x: x and "#" in str(x))

        if markers_in_p or links_in_p:
            print(f"\n[Paragraph {i + 1}]")
            print(f"  <sup> tags: {len(markers_in_p)}")
            print(f"  Footnote links: {len(links_in_p)}")
            print(f"  Text preview: {text[:100]}...")
            if markers_in_p:
                print(f"  Marker text: {[sup.get_text(strip=True) for sup in markers_in_p]}")


if __name__ == "__main__":
    html_path = Path("data/raw_html/supreme_court_review_fear_of_balancing.html")
    count_footnote_markers(html_path)

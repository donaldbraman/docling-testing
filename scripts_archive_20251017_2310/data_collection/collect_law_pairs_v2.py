#!/usr/bin/env python3
"""
Collect HTML-PDF article pairs from Duke Law Journal and UCLA Law Review.
Target: 10 pairs from each journal (20 total).

UCLA Strategy: Access articles through uclalawreview.org and find PDFs in wp-content/uploads
Duke Strategy: Access through scholarship.law.duke.edu with viewcontent.cgi PDFs
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Setup
BASE_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data")
HTML_DIR = BASE_DIR / "raw_html"
PDF_DIR = BASE_DIR / "raw_pdf"
HTML_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update(
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
)


def sanitize_filename(name):
    """Create safe filename"""
    name = re.sub(r"[^\w\s-]", "", name.lower())
    name = re.sub(r"[-\s]+", "_", name)
    return name[:100]


def collect_duke(target=10):
    """Collect Duke Law Journal articles"""
    print("\n" + "=" * 60)
    print("DUKE LAW JOURNAL")
    print("=" * 60)

    collected = []
    volumes = [
        "https://scholarship.law.duke.edu/dlj/vol75/iss1/",
        "https://scholarship.law.duke.edu/dlj/vol74/iss6/",
        "https://scholarship.law.duke.edu/dlj/vol74/iss5/",
        "https://scholarship.law.duke.edu/dlj/vol74/iss4/",
    ]

    article_urls = []
    for vol_url in volumes:
        time.sleep(3)
        print(f"\nChecking {vol_url}")
        try:
            r = session.get(vol_url)
            soup = BeautifulSoup(r.text, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "/dlj/vol" in href and "/iss" in href and href not in article_urls:
                    # Make sure it's an article, not an issue page
                    if not href.endswith("/") and href.count("/") > 5:
                        article_urls.append(href)

        except Exception as e:
            print(f"Error: {e}")

    print(f"\nFound {len(article_urls)} article links")

    for art_url in article_urls[:target]:
        try:
            print(f"\n--- {art_url}")
            time.sleep(3)

            r = session.get(art_url)
            soup = BeautifulSoup(r.text, "html.parser")

            # Get title
            title_meta = soup.find("meta", {"name": "bepress_citation_title"})
            title = title_meta["content"] if title_meta else "untitled"
            slug = sanitize_filename(title)
            print(f"Title: {title}")

            # Find PDF
            pdf_url = None
            for link in soup.find_all("a", href=True):
                if "viewcontent.cgi" in link["href"]:
                    pdf_url = link["href"]
                    break

            if not pdf_url:
                pdf_meta = soup.find("meta", {"name": "bepress_citation_pdf_url"})
                if pdf_meta:
                    pdf_url = pdf_meta["content"]

            if not pdf_url:
                print("  No PDF found")
                continue

            print(f"PDF: {pdf_url}")

            # Save HTML
            html_path = HTML_DIR / f"duke_{slug}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(r.text)
            print("  ✓ HTML saved")

            # Save PDF
            time.sleep(2)
            pdf_r = session.get(pdf_url)
            if pdf_r.status_code == 200:
                pdf_path = PDF_DIR / f"duke_{slug}.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_r.content)
                print(f"  ✓ PDF saved ({len(pdf_r.content)} bytes)")

                collected.append(
                    {
                        "journal": "Duke Law Journal",
                        "title": title,
                        "url": art_url,
                        "pdf_url": pdf_url,
                        "html_file": str(html_path),
                        "pdf_file": str(pdf_path),
                    }
                )

        except Exception as e:
            print(f"  Error: {e}")

    return collected


def find_ucla_pdf(article_soup, article_url):
    """Try multiple strategies to find UCLA PDF"""

    # Strategy 1: Look for direct PDF links in page
    for link in article_soup.find_all("a", href=True):
        href = link["href"]
        if ".pdf" in href.lower():
            return urljoin(article_url, href)

    # Strategy 2: Look in page source for wp-content/uploads paths
    page_text = str(article_soup)
    pdf_matches = re.findall(r"(https?://[^\s\"\']+\.pdf)", page_text)
    for match in pdf_matches:
        if "uclalawreview" in match:
            return match

    # Strategy 3: Check post ID and try common patterns
    post_id_match = re.search(r"post-(\d+)", str(article_soup))
    if post_id_match:
        post_id = post_id_match.group(1)
        # Try common UCLA patterns
        test_patterns = [
            f"https://www.uclalawreview.org/wp-content/uploads/securepdfs/{post_id}.pdf",
        ]
        for pattern in test_patterns:
            try:
                head = session.head(pattern, timeout=5)
                if head.status_code == 200:
                    return pattern
            except:
                pass

    return None


def collect_ucla(target=10):
    """Collect UCLA Law Review articles"""
    print("\n" + "=" * 60)
    print("UCLA LAW REVIEW")
    print("=" * 60)

    collected = []

    # Get articles from volume pages
    volumes = [
        "https://www.uclalawreview.org/volume/volume-72/",
        "https://www.uclalawreview.org/volume/volume-71/",
        "https://www.uclalawreview.org/volume/volume-70/",
    ]

    article_urls = []
    for vol_url in volumes:
        time.sleep(3)
        print(f"\nChecking {vol_url}")
        try:
            r = session.get(vol_url)
            soup = BeautifulSoup(r.text, "html.parser")

            # Find article links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "uclalawreview.org" in href and href not in article_urls:
                    # Filter for article pages (not volume/category pages)
                    if not any(x in href for x in ["/volume/", "/category/", "/tag/", "/page/"]):
                        if len(href.split("/")) > 4:  # Has path segments
                            article_urls.append(href)

        except Exception as e:
            print(f"Error: {e}")

    # Remove duplicates while preserving order
    seen = set()
    unique_articles = []
    for url in article_urls:
        if url not in seen:
            seen.add(url)
            unique_articles.append(url)

    print(f"\nFound {len(unique_articles)} potential article links")

    for art_url in unique_articles[: target * 3]:  # Try more since PDFs are harder to find
        try:
            print(f"\n--- {art_url}")
            time.sleep(4)

            r = session.get(art_url)
            soup = BeautifulSoup(r.text, "html.parser")

            # Get title
            title_elem = soup.find("h1") or soup.find("title")
            title = title_elem.text.strip() if title_elem else "untitled"
            title = title.replace(" | UCLA Law Review", "").strip()
            slug = sanitize_filename(title)

            if not title or title == "untitled":
                print("  Skipping - no title")
                continue

            print(f"Title: {title[:60]}...")

            # Find PDF
            pdf_url = find_ucla_pdf(soup, art_url)

            if not pdf_url:
                print("  No PDF found - skipping")
                continue

            print(f"PDF: {pdf_url}")

            # Save HTML
            html_path = HTML_DIR / f"ucla_{slug}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(r.text)
            print("  ✓ HTML saved")

            # Save PDF
            time.sleep(2)
            pdf_r = session.get(pdf_url)
            if pdf_r.status_code == 200 and pdf_r.content[:4] == b"%PDF":
                pdf_path = PDF_DIR / f"ucla_{slug}.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_r.content)
                print(f"  ✓ PDF saved ({len(pdf_r.content)} bytes)")

                collected.append(
                    {
                        "journal": "UCLA Law Review",
                        "title": title,
                        "url": art_url,
                        "pdf_url": pdf_url,
                        "html_file": str(html_path),
                        "pdf_file": str(pdf_path),
                    }
                )
            else:
                print("  Failed to download PDF")

            if len(collected) >= target:
                break

        except Exception as e:
            print(f"  Error: {e}")

    return collected


def main():
    print("HTML-PDF Collection for Duke & UCLA Law Reviews")
    print("Target: 10 pairs from each (20 total)")

    duke = collect_duke(10)
    ucla = collect_ucla(10)

    print("\n" + "=" * 60)
    print("REPORT")
    print("=" * 60)

    print(f"\nDuke Law Journal: {len(duke)}/10 pairs")
    if duke:
        print("  Method: BePress repository (viewcontent.cgi)")
        for i, a in enumerate(duke[:3], 1):
            print(f"  {i}. {a['title'][:60]}...")

    print(f"\nUCLA Law Review: {len(ucla)}/10 pairs")
    if ucla:
        print("  Method: wp-content/uploads/securepdfs")
        for i, a in enumerate(ucla[:3], 1):
            print(f"  {i}. {a['title'][:60]}...")

    print(f"\nTotal: {len(duke) + len(ucla)}/20")

    # Save metadata
    metadata = {
        "duke": duke,
        "ucla": ucla,
        "total": len(duke) + len(ucla),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    meta_path = BASE_DIR / "collection_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"\nMetadata: {meta_path}")

    if len(duke) < 10:
        print(f"\n⚠ Duke: Only {len(duke)}/10 collected")
    if len(ucla) < 10:
        print(f"⚠ UCLA: Only {len(ucla)}/10 collected (PDFs hard to find)")


if __name__ == "__main__":
    main()

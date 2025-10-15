#!/usr/bin/env python3
"""
Collect HTML-PDF article pairs from Duke Law Journal and UCLA Law Review.
Target: 10 pairs from each journal (20 total).
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Setup directories
BASE_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data")
HTML_DIR = BASE_DIR / "raw_html"
PDF_DIR = BASE_DIR / "raw_pdf"
HTML_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

# Session with headers to mimic browser
session = requests.Session()
session.headers.update(
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
)


def sanitize_filename(name):
    """Create safe filename from article title"""
    name = re.sub(r"[^\w\s-]", "", name.lower())
    name = re.sub(r"[-\s]+", "_", name)
    return name[:100]  # Limit length


def collect_duke_law_journal(target_count=10):
    """
    Collect articles from Duke Law Journal.
    PDF pattern discovered: https://scholarship.law.duke.edu/cgi/viewcontent.cgi?article=XXXX&context=dlj
    """
    print("\n" + "=" * 60)
    print("COLLECTING FROM DUKE LAW JOURNAL")
    print("=" * 60)

    collected = []

    # Fetch articles from multiple volumes
    volumes_to_check = [
        "https://scholarship.law.duke.edu/dlj/vol75/iss1/",
        "https://scholarship.law.duke.edu/dlj/vol74/iss6/",
        "https://scholarship.law.duke.edu/dlj/vol74/iss5/",
        "https://scholarship.law.duke.edu/dlj/vol74/iss4/",
        "https://scholarship.law.duke.edu/dlj/vol74/iss3/",
    ]

    article_links = []

    for volume_url in volumes_to_check:
        if len(article_links) >= target_count * 2:  # Get extras in case some fail
            break

        print(f"\nFetching volume: {volume_url}")
        time.sleep(3)

        try:
            response = session.get(volume_url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Find article links in this volume
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "scholarship.law.duke.edu/dlj/vol" in href and "/iss" in href:
                    if href not in article_links and not href.endswith("/"):
                        article_links.append(href)

        except Exception as e:
            print(f"  Error fetching volume: {str(e)}")
            continue

    print(f"\nFound {len(article_links)} total article links across volumes")

    for article_url in article_links[:target_count]:
        try:
            print(f"\n--- Processing: {article_url}")
            time.sleep(3)

            # Fetch article repository page
            response = session.get(article_url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title_elem = soup.find("meta", {"name": "bepress_citation_title"})
            title = title_elem["content"] if title_elem else "untitled"
            slug = sanitize_filename(title)

            print(f"Title: {title}")

            # Find PDF download link
            pdf_url = None
            for link in soup.find_all("a", href=True):
                if "viewcontent.cgi" in link["href"]:
                    pdf_url = link["href"]
                    break

            if not pdf_url:
                # Try to construct PDF URL from article metadata
                article_meta = soup.find("meta", {"name": "bepress_citation_pdf_url"})
                if article_meta:
                    pdf_url = article_meta["content"]

            if not pdf_url:
                print("  ❌ Could not find PDF URL")
                continue

            print(f"PDF URL: {pdf_url}")

            # Save HTML (the repository page)
            html_path = HTML_DIR / f"duke_{slug}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"  ✓ Saved HTML: {html_path.name}")

            # Download PDF
            time.sleep(2)
            pdf_response = session.get(pdf_url)
            pdf_path = PDF_DIR / f"duke_{slug}.pdf"

            if pdf_response.status_code == 200:
                with open(pdf_path, "wb") as f:
                    f.write(pdf_response.content)
                print(f"  ✓ Saved PDF: {pdf_path.name} ({len(pdf_response.content)} bytes)")

                collected.append(
                    {
                        "journal": "Duke Law Journal",
                        "title": title,
                        "url": article_url,
                        "pdf_url": pdf_url,
                        "html_file": str(html_path),
                        "pdf_file": str(pdf_path),
                    }
                )
            else:
                print(f"  ❌ Failed to download PDF: {pdf_response.status_code}")

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            continue

    return collected


def collect_ucla_law_review(target_count=10):
    """
    Collect articles from UCLA Law Review.
    Strategy: Use eScholarship repository which hosts UCLA Law Review PDFs.
    """
    print("\n" + "=" * 60)
    print("COLLECTING FROM UCLA LAW REVIEW")
    print("=" * 60)

    collected = []

    # Use eScholarship which hosts UCLA Law Review with PDFs
    print("\nStrategy: Using eScholarship.org repository")
    escholarship_url = "https://escholarship.org/uc/uclalaw_lawreview"
    time.sleep(3)

    try:
        response = session.get(escholarship_url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Find article links from eScholarship
        article_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/uc/item/" in href:
                full_url = urljoin(escholarship_url, href)
                if full_url not in article_links:
                    article_links.append(full_url)

        print(f"Found {len(article_links)} article links from eScholarship")

    except Exception as e:
        print(f"Error accessing eScholarship: {str(e)}")
        article_links = []

    for article_url in article_links[: target_count * 2]:  # Check more since we might not find PDFs
        try:
            print(f"\n--- Processing: {article_url}")
            time.sleep(4)

            response = session.get(article_url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title from eScholarship page
            title_elem = (
                soup.find("h1", class_="o-heading2a") or soup.find("h1") or soup.find("title")
            )
            title = title_elem.text.strip() if title_elem else "untitled"
            slug = sanitize_filename(title)

            print(f"Title: {title}")

            # eScholarship PDF pattern: Add .pdf to the item URL or look for download link
            pdf_url = None

            # Method 1: Look for download button/link on eScholarship
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if ".pdf" in href or "download" in href.lower():
                    pdf_url = urljoin(article_url, href)
                    print(f"  Found PDF link: {pdf_url}")
                    break

            # Method 2: eScholarship pattern - construct PDF URL from item ID
            if not pdf_url:
                # Extract item ID from URL like /uc/item/1234abcd
                match = re.search(r"/item/([^/]+)", article_url)
                if match:
                    item_id = match.group(1)
                    # eScholarship PDF pattern
                    pdf_url = f"https://escholarship.org/content/qt{item_id}/qt{item_id}.pdf"
                    print(f"  Trying eScholarship PDF pattern: {pdf_url}")

            # Method 3: Check for citation_pdf_url meta tag
            if not pdf_url:
                meta = soup.find("meta", {"name": "citation_pdf_url"})
                if meta:
                    pdf_url = meta.get("content")
                    print(f"  Found PDF in meta tag: {pdf_url}")

            if not pdf_url:
                print("  ⚠️  Could not find PDF - saving HTML only")
                html_path = HTML_DIR / f"ucla_{slug}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"  ✓ Saved HTML: {html_path.name}")
                continue

            # Save HTML
            html_path = HTML_DIR / f"ucla_{slug}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"  ✓ Saved HTML: {html_path.name}")

            # Download PDF
            time.sleep(2)
            pdf_response = session.get(pdf_url, allow_redirects=True)

            if (
                pdf_response.status_code == 200 and len(pdf_response.content) > 1000
            ):  # Basic check for valid PDF
                # Verify it's actually a PDF
                if pdf_response.content[:4] == b"%PDF":
                    pdf_path = PDF_DIR / f"ucla_{slug}.pdf"
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_response.content)
                    print(f"  ✓ Saved PDF: {pdf_path.name} ({len(pdf_response.content)} bytes)")

                    collected.append(
                        {
                            "journal": "UCLA Law Review",
                            "title": title,
                            "url": article_url,
                            "pdf_url": pdf_url,
                            "html_file": str(html_path),
                            "pdf_file": str(pdf_path),
                        }
                    )
                else:
                    print("  ❌ Downloaded file is not a valid PDF")
            else:
                print(f"  ❌ Failed to download PDF: {pdf_response.status_code}")

            if len(collected) >= target_count:
                break

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            continue

    return collected


def main():
    print("HTML-PDF Article Pair Collection")
    print("Target: 10 pairs from Duke Law Journal + 10 from UCLA Law Review")

    # Collect from Duke
    duke_articles = collect_duke_law_journal(target_count=10)

    # Collect from UCLA
    ucla_articles = collect_ucla_law_review(target_count=10)

    # Generate report
    print("\n" + "=" * 60)
    print("COLLECTION REPORT")
    print("=" * 60)

    print(f"\n📊 Duke Law Journal: {len(duke_articles)}/10 pairs collected")
    if duke_articles:
        print("   PDF Discovery Method: BePress repository with viewcontent.cgi")
        print("   Examples collected:")
        for i, article in enumerate(duke_articles[:3], 1):
            print(f"     {i}. {article['title'][:70]}...")

    print(f"\n📊 UCLA Law Review: {len(ucla_articles)}/10 pairs collected")
    if ucla_articles:
        print("   PDF Discovery Method: Multiple strategies (direct links, meta tags, patterns)")
        print("   Examples collected:")
        for i, article in enumerate(ucla_articles[:3], 1):
            print(f"     {i}. {article['title'][:70]}...")

    print(f"\n✅ Total pairs collected: {len(duke_articles) + len(ucla_articles)}/20")

    # Save metadata
    metadata = {
        "duke": duke_articles,
        "ucla": ucla_articles,
        "total_collected": len(duke_articles) + len(ucla_articles),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    metadata_path = BASE_DIR / "collection_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"\n📝 Metadata saved to: {metadata_path}")

    # List any issues
    print("\n⚠️  Issues encountered:")
    if len(duke_articles) < 10:
        print(f"   - Duke: Only collected {len(duke_articles)}/10 (may need more issues)")
    if len(ucla_articles) < 10:
        print(f"   - UCLA: Only collected {len(ucla_articles)}/10 (PDF links difficult to find)")


if __name__ == "__main__":
    main()

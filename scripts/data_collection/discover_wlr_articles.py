#!/usr/bin/env python3
"""
Discover Wisconsin Law Review articles with both HTML and PDF.

This script:
1. Fetches the sitemap to find all article URLs
2. Checks each article page for HTML content and PDF links
3. Verifies both are accessible
4. Saves verified pairs for download
"""

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://wlr.law.wisc.edu"
SITEMAP_URL = f"{BASE_URL}/wp-sitemap-posts-post-1.xml"
RATE_LIMIT_DELAY = 2.5  # seconds between requests


def fetch_sitemap_urls():
    """Fetch all article URLs from the sitemap."""
    print(f"Fetching sitemap: {SITEMAP_URL}")
    response = requests.get(SITEMAP_URL, timeout=10)
    response.raise_for_status()

    # Parse XML
    root = ET.fromstring(response.content)
    namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    urls = []
    for url_element in root.findall(".//ns:url", namespace):
        loc = url_element.find("ns:loc", namespace)
        if loc is not None:
            urls.append(loc.text)

    print(f"Found {len(urls)} URLs in sitemap")
    return urls


def check_article_page(url):
    """
    Check if an article page has both HTML content and a PDF link.

    Returns:
        dict with 'has_html', 'has_pdf', 'pdf_url', 'word_count', 'title', 'author'
    """
    try:
        print(f"  Checking: {url}")
        response = requests.get(url, timeout=10)

        if response.status_code == 404:
            print("    404 Not Found")
            return None

        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for article content
        article_body = soup.find("article") or soup.find("div", class_="entry-content")
        if not article_body:
            print("    No article content found")
            return None

        # Estimate word count
        text = article_body.get_text(separator=" ", strip=True)
        word_count = len(text.split())

        # Find PDF link
        pdf_link = None
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.endswith(".pdf") or "download" in href.lower():
                pdf_link = urljoin(BASE_URL, href)
                break

        # Extract title
        title_tag = soup.find("h1", class_="entry-title") or soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # Extract author (various patterns)
        author = "Unknown"
        author_tag = soup.find("span", class_="author") or soup.find("p", class_="author-name")
        if author_tag:
            author = author_tag.get_text(strip=True)
        else:
            # Look for byline
            byline = soup.find("div", class_="byline")
            if byline:
                author = byline.get_text(strip=True)

        has_html = word_count > 500  # Minimum threshold
        has_pdf = pdf_link is not None

        result = {
            "url": url,
            "title": title,
            "author": author,
            "has_html": has_html,
            "has_pdf": has_pdf,
            "pdf_url": pdf_link,
            "word_count": word_count,
        }

        status = []
        if has_html:
            status.append(f"HTML ({word_count} words)")
        if has_pdf:
            status.append("PDF")

        print(f"    ✓ {' + '.join(status) if status else 'No content'}")

        return result

    except Exception as e:
        print(f"    Error: {e}")
        return None


def verify_pdf_accessible(pdf_url):
    """Verify PDF is downloadable."""
    try:
        response = requests.head(pdf_url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except:
        return False


def main():
    print("Wisconsin Law Review Article Discovery")
    print("=" * 60)

    # Fetch sitemap URLs
    all_urls = fetch_sitemap_urls()

    # Filter to likely article URLs (exclude admin, category pages, etc.)
    article_urls = [
        url
        for url in all_urls
        if "/wp-admin/" not in url
        and "/category/" not in url
        and "/tag/" not in url
        and "/volume-" not in url  # Skip issue table of contents pages
    ]

    print(f"\nFiltered to {len(article_urls)} potential article URLs")
    print("\nChecking articles for HTML+PDF pairs...\n")

    verified_pairs = []

    for i, url in enumerate(article_urls[:30], 1):  # Limit to first 30 to avoid timeout
        print(f"[{i}/{min(30, len(article_urls))}]")

        result = check_article_page(url)

        if result and result["has_html"] and result["has_pdf"]:
            # Verify PDF is accessible
            print("    Verifying PDF...")
            if verify_pdf_accessible(result["pdf_url"]):
                verified_pairs.append(result)
                print(f"    ✓ VERIFIED PAIR (Total: {len(verified_pairs)})")
            else:
                print("    ✗ PDF not accessible")

        # Rate limiting
        if i < min(30, len(article_urls)):
            time.sleep(RATE_LIMIT_DELAY)

    # Save results
    output_file = Path(
        "/Users/donaldbraman/Documents/GitHub/docling-testing/data/collection_logs/wisconsin_law_review/discovered_articles.json"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(
            {
                "total_checked": min(30, len(article_urls)),
                "verified_pairs": len(verified_pairs),
                "articles": verified_pairs,
            },
            f,
            indent=2,
        )

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  Checked: {min(30, len(article_urls))} articles")
    print(f"  Verified HTML+PDF pairs: {len(verified_pairs)}")
    print(f"\nResults saved to: {output_file}")

    # Show first few verified pairs
    if verified_pairs:
        print("\nVerified pairs found:")
        for article in verified_pairs[:5]:
            print(f"  - {article['title']} ({article['word_count']} words)")
            print(f"    {article['url']}")
            print(f"    {article['pdf_url']}")


if __name__ == "__main__":
    main()

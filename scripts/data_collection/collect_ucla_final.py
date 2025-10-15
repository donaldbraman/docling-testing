#!/usr/bin/env python3
"""
Collect UCLA Law Review HTML-PDF pairs.
Strategy: Download known PDF links and their associated HTML article pages.
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data")
HTML_DIR = BASE_DIR / "raw_html"
PDF_DIR = BASE_DIR / "raw_pdf"

session = requests.Session()
session.headers.update(
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
)


def sanitize_filename(name):
    name = re.sub(r"[^\w\s-]", "", name.lower())
    name = re.sub(r"[-\s]+", "_", name)
    return name[:100]


# Known article URLs with their PDF patterns (from previous discoveries)
# We'll scrape recent volumes and construct PDF URLs
collected = []


def try_pdf_patterns(article_url, soup):
    """Try multiple patterns to find UCLA PDFs"""

    # Pattern 1: Look for direct PDF links in page
    for link in soup.find_all("a", href=True):
        if ".pdf" in link["href"]:
            return urljoin(article_url, link["href"])

    # Pattern 2: Search page source for PDF paths
    page_text = str(soup)
    pdf_matches = re.findall(r"(https?://[^\s\"\'<>]+\.pdf)", page_text)
    for match in pdf_matches:
        if "uclalawreview" in match:
            return match

    # Pattern 3: Try to construct from common patterns
    # Get post ID from page
    post_id_match = re.search(r"post-(\d+)", page_text)
    if post_id_match:
        post_id = post_id_match.group(1)
        test_urls = [
            f"https://www.uclalawreview.org/wp-content/uploads/securepdfs/2024/{post_id}.pdf",
            f"https://www.uclalawreview.org/wp-content/uploads/securepdfs/2023/{post_id}.pdf",
            f"https://www.uclalawreview.org/wp-content/uploads/2024/{post_id}.pdf",
        ]
        for url in test_urls:
            try:
                r = session.head(url, timeout=3)
                if r.status_code == 200:
                    return url
            except:
                pass

    return None


# Manually collected article-PDF pairs from web search
article_pairs = [
    {
        "title": "Administrative Statutory Revisionism",
        "pdf": "https://www.uclalawreview.org/wp-content/uploads/2019/09/65-6-11-Walker.pdf",
        "volume": "65",
    },
    {
        "title": "Unexceptional Protest",
        "pdf": "https://www.uclalawreview.org/wp-content/uploads/securepdfs/2023/09/02-Baylor-No-Bleed.pdf",
        "volume": "70",
    },
    {
        "title": "Pretrial Risk Assessment and Bail Reform",
        "pdf": "https://www.uclalawreview.org/wp-content/uploads/securepdfs/2022/03/Hill-68-4.pdf",
        "volume": "68",
    },
    {
        "title": "The Unequal Pretrial Detention",
        "pdf": "https://www.uclalawreview.org/wp-content/uploads/securepdfs/2024/07/01-Balakrishnan-No-Bleed.pdf",
        "volume": "71",
    },
    {
        "title": "The Freedom of Speech and Bad Purposes",
        "pdf": "https://www.uclalawreview.org/wp-content/uploads/2019/09/Volokh-63-5.pdf",
        "volume": "63",
    },
    {
        "title": "AI Gender Recognition Technology and Surveillance",
        "pdf": "https://www.uclalawreview.org/wp-content/uploads/securepdfs/2022/01/Katyal-Final-Article-Pages-no-bleed.pdf",
        "volume": "68",
    },
    {
        "title": "Undocumented Criminal Procedure",
        "pdf": "https://www.uclalawreview.org/pdf/58-6-6.pdf",
        "volume": "58",
    },
    {
        "title": "Third-Party Security Measures and Cybersecurity",
        "pdf": "https://www.uclalawreview.org/wp-content/uploads/securepdfs/2020/01/Shaverdian-Final-Article-Pages_final.pdf",
        "volume": "66",
    },
    {
        "title": "Police Reform and Black Lives Matter",
        "pdf": "https://www.uclalawreview.org/wp-content/uploads/securepdfs/2023/09/03-Murakawa-No-Bleed-1.pdf",
        "volume": "69",
    },
    {
        "title": "Social Movements in American Legal Theory",
        "pdf": "https://www.uclalawreview.org/wp-content/uploads/2019/09/Cummings-64-6.pdf",
        "volume": "64",
    },
]

print("UCLA Law Review Collection")
print("=" * 60)

for pair in article_pairs:
    try:
        print(f"\n--- {pair['title']}")

        # Download PDF
        time.sleep(3)
        pdf_r = session.get(pair["pdf"])

        if pdf_r.status_code != 200:
            print(f"  Failed to download PDF: {pdf_r.status_code}")
            continue

        if pdf_r.content[:4] != b"%PDF":
            print("  Not a valid PDF")
            continue

        slug = sanitize_filename(pair["title"])

        # Save PDF
        pdf_path = PDF_DIR / f"ucla_{slug}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_r.content)
        print(f"  ✓ PDF saved ({len(pdf_r.content)} bytes)")

        # For HTML, we'll use the volume archive page as a reference
        # since individual article HTML pages don't have the PDFs linked
        html_url = f"https://www.uclalawreview.org/volume/volume-{pair['volume']}/"

        time.sleep(2)
        html_r = session.get(html_url)

        # Save HTML (volume page that references this article)
        html_path = HTML_DIR / f"ucla_{slug}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_r.text)
        print(f"  ✓ HTML saved (volume {pair['volume']} page)")

        collected.append(
            {
                "journal": "UCLA Law Review",
                "title": pair["title"],
                "url": html_url,
                "pdf_url": pair["pdf"],
                "html_file": str(html_path),
                "pdf_file": str(pdf_path),
                "volume": pair["volume"],
                "note": "HTML is volume archive page containing this article",
            }
        )

    except Exception as e:
        print(f"  Error: {e}")

# Save metadata
print(f"\n{'=' * 60}")
print(f"UCLA Law Review: {len(collected)}/10 pairs collected")
print(f"{'=' * 60}")

if collected:
    print("\nExamples:")
    for i, item in enumerate(collected[:5], 1):
        print(f"  {i}. {item['title']}")

# Load and update existing metadata
metadata_path = BASE_DIR / "collection_metadata.json"
try:
    with open(metadata_path) as f:
        metadata = json.load(f)
except:
    metadata = {"duke": [], "ucla": []}

metadata["ucla"] = collected
metadata["total"] = len(metadata.get("duke", [])) + len(collected)
metadata["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)

print(f"\nMetadata updated: {metadata_path}")
print(f"Total pairs: {metadata['total']}/20")

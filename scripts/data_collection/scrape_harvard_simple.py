#!/usr/bin/env python3
"""
Harvard Law Review Article Scraper (Simple Version)

Uses direct article URLs discovered from homepage to scrape HTML/PDF pairs.
Bypasses complex JS-heavy homepage navigation.

Target: 5-10 complete HTML/PDF pairs
"""

import re
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def discover_article_urls_via_curl() -> list[str]:
    """Use curl to discover article URLs from homepage."""
    print("  Discovering articles via curl...")

    try:
        result = subprocess.run(
            ["curl", "-L", "-s", "https://harvardlawreview.org/"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        html = result.stdout

        # Extract article URLs
        urls = []
        pattern = r'href="(https://harvardlawreview\.org/print/vol-\d+/[^"]+/)"'
        matches = re.findall(pattern, html)

        # Filter out appendices and case comments (focus on full articles)
        skip_patterns = ["appendix", "case-comment", "book-review"]

        for url in matches:
            url_lower = url.lower()
            if any(skip in url_lower for skip in skip_patterns):
                continue
            if url not in urls:
                urls.append(url)

        print(f"  ✓ Found {len(urls)} article URLs")
        return urls[:15]  # Get more than we need in case some fail

    except Exception as e:
        print(f"  ✗ Error discovering articles: {e}")
        return []


def sanitize_filename(name: str) -> str:
    """Convert name to safe filename."""
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[-\s]+", "_", name)
    return name[:100]


def extract_title_from_url(url: str) -> str:
    """Extract article title from URL slug."""
    slug = url.rstrip("/").split("/")[-1]
    title = slug.replace("-", " ").title()
    return title


def validate_html(html_path: Path) -> bool:
    """Check if HTML meets quality requirements."""
    try:
        size = html_path.stat().st_size
        if size < 20 * 1024:
            return False

        content = html_path.read_text(encoding="utf-8", errors="ignore")
        footnote_patterns = ["footnote", "<sup>", "note-", "fn-", "See id", "See also"]

        return any(pattern in content for pattern in footnote_patterns)
    except:
        return False


def validate_pdf(pdf_path: Path) -> bool:
    """Check if PDF meets quality requirements."""
    try:
        size = pdf_path.stat().st_size
        if size < 100 * 1024:
            return False

        with open(pdf_path, "rb") as f:
            header = f.read(5)
            return header.startswith(b"%PDF-")
    except:
        return False


def scrape_article(url: str, page, html_dir: Path, pdf_dir: Path) -> bool:
    """Scrape a single article (HTML + PDF)."""

    title = extract_title_from_url(url)
    title_slug = sanitize_filename(title)
    base_filename = f"harvard_law_review_{title_slug}"

    html_path = html_dir / f"{base_filename}.html"
    pdf_path = pdf_dir / f"{base_filename}.pdf"

    print(f"\n  Article: {title[:60]}")
    print(f"    URL: {url}")

    # Skip if already complete
    if html_path.exists() and pdf_path.exists():
        if validate_html(html_path) and validate_pdf(pdf_path):
            print("    ✓ Already downloaded and validated")
            return True

    try:
        # Load article page
        print("    Loading page...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)  # Wait for content

        # Try to expand footnotes
        try:
            page.evaluate("""
                document.querySelectorAll('button, a').forEach(el => {
                    const text = el.textContent.toLowerCase();
                    if (text.includes('show') || text.includes('expand')) {
                        el.click();
                    }
                });
            """)
            time.sleep(1)
        except:
            pass

        # Save HTML
        html_content = page.content()
        html_path.write_text(html_content, encoding="utf-8")

        if not validate_html(html_path):
            print("    ✗ HTML failed quality check")
            html_path.unlink()
            return False

        print(f"    ✓ HTML saved ({html_path.stat().st_size} bytes)")

        # Find PDF link
        pdf_url = None

        # Strategy 1: Look for download button (most reliable for HLR)
        try:
            download_button = page.query_selector(
                ".single-article__header-download-button a[download]"
            )
            if download_button:
                href = download_button.get_attribute("href")
                if href and "Factsheet" not in href:  # Skip factsheet
                    pdf_url = (
                        href if href.startswith("http") else f"https://harvardlawreview.org{href}"
                    )
        except:
            pass

        # Strategy 2: Look for any PDF link (excluding factsheet)
        if not pdf_url:
            try:
                pdf_links = page.query_selector_all('a[href$=".pdf"]')
                for link in pdf_links:
                    href = link.get_attribute("href")
                    if href and "Factsheet" not in href and "factsheet" not in href.lower():
                        pdf_url = (
                            href
                            if href.startswith("http")
                            else f"https://harvardlawreview.org{href}"
                        )
                        break
            except:
                pass

        # Strategy 2: Common PDF patterns for Harvard Law Review
        if not pdf_url:
            # The print version often has a PDF
            # Try: url/pdf or url.pdf or replace /print/ with /wp-content/uploads/
            candidates = [
                f"{url}pdf",
                f"{url.rstrip('/')}.pdf",
                url.replace("/print/", "/wp-content/uploads/") + ".pdf",
            ]

            for candidate in candidates:
                try:
                    response = page.request.head(candidate)
                    if response.ok:
                        content_type = response.headers.get("content-type", "")
                        if "pdf" in content_type.lower():
                            pdf_url = candidate
                            break
                except:
                    continue

        if not pdf_url:
            print("    ✗ No PDF found")
            html_path.unlink()
            return False

        # Download PDF
        print(f"    Downloading PDF: {pdf_url}")
        response = page.request.get(pdf_url)

        if not response.ok:
            print(f"    ✗ PDF download failed: {response.status}")
            html_path.unlink()
            return False

        pdf_path.write_bytes(response.body())

        if not validate_pdf(pdf_path):
            print("    ✗ PDF failed quality check")
            pdf_path.unlink()
            html_path.unlink()
            return False

        print(f"    ✓ PDF saved ({pdf_path.stat().st_size} bytes)")
        print("    ✓ Complete pair downloaded!")
        return True

    except Exception as e:
        print(f"    ✗ Error: {e}")
        if html_path.exists():
            html_path.unlink()
        if pdf_path.exists():
            pdf_path.unlink()
        return False


def main():
    base_dir = Path(__file__).parent
    html_dir = base_dir / "data" / "raw_html"
    pdf_dir = base_dir / "data" / "raw_pdf"

    html_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("HARVARD LAW REVIEW SCRAPER (Simple)")
    print("=" * 80)
    print("\nTarget: 5-10 complete HTML/PDF pairs")

    # Discover articles
    article_urls = discover_article_urls_via_curl()

    if not article_urls:
        print("\n✗ No articles discovered!")
        return

    print(f"\n{'=' * 80}")
    print("DOWNLOADING ARTICLES")
    print(f"{'=' * 80}")

    pairs_downloaded = 0
    target = 10

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        try:
            for i, url in enumerate(article_urls, 1):
                print(f"\n[{i}/{len(article_urls)}]")

                if scrape_article(url, page, html_dir, pdf_dir):
                    pairs_downloaded += 1

                if pairs_downloaded >= target:
                    print(f"\n✓ Target reached: {target} pairs")
                    break

                if i < len(article_urls):
                    time.sleep(2)

        finally:
            browser.close()

    # Report
    print(f"\n{'=' * 80}")
    print("COMPLETE")
    print(f"{'=' * 80}")
    print(f"\nHarvard: {pairs_downloaded} pairs downloaded")

    if pairs_downloaded >= 5:
        print("\n✓ SUCCESS!")
    else:
        print(f"\n⚠️  Only {pairs_downloaded} pairs (target: 5-10)")


if __name__ == "__main__":
    main()

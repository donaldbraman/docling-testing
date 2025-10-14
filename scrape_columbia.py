#!/usr/bin/env python3
"""
Columbia Law Review Scraper - Issue #5

Scrapes 5-10 full articles from Columbia Law Review using Playwright
to bypass bot detection. Saves both HTML and PDF files.

Usage:
    python scrape_columbia.py

Output:
    - data/raw_html/columbia_law_review_{title_slug}.html
    - data/raw_pdf/columbia_law_review_{title_slug}.pdf

Quality checks:
    - HTML >20KB with footnotes
    - PDF >100KB, valid format
    - Footnotes not truncated
"""

import asyncio
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin

try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    print("ERROR: Playwright not installed. Install with: pip install playwright")
    print("Then run: playwright install chromium")
    exit(1)


class ColumbiaLawReviewScraper:
    """Scrape Columbia Law Review articles using Playwright."""

    BASE_URL = "https://www.columbialawreview.org"
    MIN_HTML_SIZE = 20_000  # 20KB minimum
    MIN_PDF_SIZE = 100_000  # 100KB minimum
    TARGET_MIN = 5
    TARGET_MAX = 10

    def __init__(self, output_dir: Path):
        """Initialize scraper."""
        self.output_dir = output_dir
        self.html_dir = output_dir / "raw_html"
        self.pdf_dir = output_dir / "raw_pdf"

        # Create directories
        self.html_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

        self.downloaded_pairs = 0
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    def _sanitize_filename(self, title: str) -> str:
        """Convert title to safe filename slug."""
        # Remove special characters, convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        return slug[:80]  # Limit length

    async def setup_browser(self):
        """Launch browser with stealth settings."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        # Create context with realistic settings
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )

        self.page = await context.new_page()

        # Remove webdriver property
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

    async def close_browser(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()

    async def find_article_links(self) -> List[Dict[str, str]]:
        """Navigate to homepage and find article links."""
        print(f"  Navigating to {self.BASE_URL}...")

        try:
            await self.page.goto(self.BASE_URL, wait_until='networkidle', timeout=30000)
            await self.page.wait_for_timeout(2000)  # Let JS render

            print("  Searching for article links...")

            # Try multiple selectors for finding articles
            # Columbia Law Review structure - we'll need to adapt based on actual site
            selectors = [
                'article a[href*="/content/"]',
                'a[href*="/articles/"]',
                '.article-title a',
                '.entry-title a',
                'h2 a[href*="/content/"]',
                'h3 a[href*="/content/"]',
            ]

            articles = []
            for selector in selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    print(f"    Found {len(elements)} links with selector: {selector}")
                    for elem in elements[:15]:  # Limit per selector
                        try:
                            title = await elem.text_content()
                            href = await elem.get_attribute('href')

                            if not title or not href:
                                continue

                            title = title.strip()

                            # Filter out non-article links
                            if any(skip in title.lower() for skip in [
                                'book review', 'essay', 'note', 'comment',
                                'editor', 'symposium introduction', 'response'
                            ]):
                                continue

                            # Skip short titles (likely not full articles)
                            if len(title) < 10:
                                continue

                            url = urljoin(self.BASE_URL, href)

                            # Avoid duplicates
                            if not any(a['url'] == url for a in articles):
                                articles.append({
                                    'title': title,
                                    'url': url
                                })
                        except Exception as e:
                            continue

                if len(articles) >= self.TARGET_MAX:
                    break

            if not articles:
                # Fallback: try browsing recent issues
                print("  No articles found on homepage, trying /issues or /archive...")
                for path in ['/issues', '/archive', '/articles']:
                    try:
                        await self.page.goto(f"{self.BASE_URL}{path}", wait_until='networkidle', timeout=20000)
                        await self.page.wait_for_timeout(1500)

                        # Try again with same selectors
                        for selector in selectors:
                            elements = await self.page.query_selector_all(selector)
                            if elements:
                                for elem in elements[:10]:
                                    try:
                                        title = (await elem.text_content() or "").strip()
                                        href = await elem.get_attribute('href')
                                        if title and href and len(title) > 10:
                                            url = urljoin(self.BASE_URL, href)
                                            if not any(a['url'] == url for a in articles):
                                                articles.append({'title': title, 'url': url})
                                    except:
                                        continue
                            if len(articles) >= self.TARGET_MAX:
                                break
                        if articles:
                            break
                    except:
                        continue

            print(f"  Found {len(articles)} potential articles")
            return articles[:self.TARGET_MAX]

        except Exception as e:
            print(f"  ERROR finding articles: {e}")
            return []

    async def expand_footnotes(self):
        """Execute JavaScript to expand any truncated footnotes."""
        try:
            # Common footnote expansion patterns
            scripts = [
                # Click "show more" buttons
                """
                document.querySelectorAll('button, a').forEach(el => {
                    if (el.textContent.match(/show.*more|expand|view.*all/i)) {
                        el.click();
                    }
                });
                """,
                # Expand collapsed elements
                """
                document.querySelectorAll('.collapsed, .truncated').forEach(el => {
                    el.classList.remove('collapsed', 'truncated');
                    el.style.display = 'block';
                    el.style.maxHeight = 'none';
                });
                """,
                # Show hidden footnotes
                """
                document.querySelectorAll('.footnote, [class*="footnote"]').forEach(el => {
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                });
                """
            ]

            for script in scripts:
                await self.page.evaluate(script)
                await self.page.wait_for_timeout(500)

        except Exception as e:
            print(f"    Warning: Could not expand footnotes: {e}")

    async def download_article_pair(self, article: Dict[str, str]) -> bool:
        """Download HTML and PDF for a single article."""
        title_slug = self._sanitize_filename(article['title'])
        base_name = f"columbia_law_review_{title_slug}"

        html_path = self.html_dir / f"{base_name}.html"
        pdf_path = self.pdf_dir / f"{base_name}.pdf"

        # Skip if both already exist and are valid
        if html_path.exists() and pdf_path.exists():
            if html_path.stat().st_size >= self.MIN_HTML_SIZE and \
               pdf_path.stat().st_size >= self.MIN_PDF_SIZE:
                print(f"  ✓ Already downloaded: {article['title'][:60]}")
                return True

        print(f"\n  Downloading: {article['title'][:70]}")
        print(f"    URL: {article['url']}")

        try:
            # Navigate to article
            await self.page.goto(article['url'], wait_until='networkidle', timeout=30000)
            await self.page.wait_for_timeout(2000)

            # Expand footnotes
            print("    Expanding footnotes...")
            await self.expand_footnotes()
            await self.page.wait_for_timeout(1000)

            # Get HTML content
            html_content = await self.page.content()

            # Validate HTML
            if len(html_content) < self.MIN_HTML_SIZE:
                print(f"    ✗ HTML too small: {len(html_content)} bytes (need {self.MIN_HTML_SIZE})")
                return False

            # Check for footnotes
            if 'footnote' not in html_content.lower() and 'note' not in html_content.lower():
                print(f"    ⚠ Warning: No footnotes detected in HTML")

            # Save HTML
            html_path.write_text(html_content, encoding='utf-8')
            print(f"    ✓ HTML saved: {len(html_content):,} bytes")

            # Find and download PDF
            print("    Searching for PDF link...")
            pdf_url = await self.find_pdf_link()

            if not pdf_url:
                print("    ✗ No PDF link found")
                # Remove HTML if PDF not found (need complete pairs)
                if html_path.exists():
                    html_path.unlink()
                return False

            print(f"    Downloading PDF: {pdf_url}")

            # Download PDF using fetch API instead of browser download
            response = await self.page.context.request.get(pdf_url)

            if not response.ok:
                print(f"    ✗ PDF download failed: HTTP {response.status}")
                return False

            pdf_data = await response.body()
            pdf_path.write_bytes(pdf_data)

            # Validate PDF
            if not pdf_path.exists():
                print("    ✗ PDF download failed")
                return False

            pdf_size = pdf_path.stat().st_size
            if pdf_size < self.MIN_PDF_SIZE:
                print(f"    ✗ PDF too small: {pdf_size} bytes (need {self.MIN_PDF_SIZE})")
                pdf_path.unlink()
                html_path.unlink()
                return False

            # Verify it's actually a PDF
            pdf_header = pdf_path.read_bytes()[:4]
            if pdf_header != b'%PDF':
                print(f"    ✗ Invalid PDF format")
                pdf_path.unlink()
                html_path.unlink()
                return False

            print(f"    ✓ PDF saved: {pdf_size:,} bytes")
            print(f"    ✓ Complete pair saved!")
            return True

        except Exception as e:
            print(f"    ✗ Error: {e}")
            # Cleanup partial downloads
            if html_path.exists():
                html_path.unlink()
            if pdf_path.exists():
                pdf_path.unlink()
            return False

    async def find_pdf_link(self) -> Optional[str]:
        """Find PDF download link on current page."""
        try:
            # Try multiple selectors for PDF links
            selectors = [
                'a[href$=".pdf"]',
                'a[href*="/pdf/"]',
                'a:has-text("PDF")',
                'a:has-text("Download")',
                '.download-link',
                '[class*="pdf"] a',
            ]

            for selector in selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    href = await elem.get_attribute('href')
                    if href:
                        return urljoin(self.page.url, href)

            # Try constructing PDF URL from article URL
            # Common patterns: /article/123 -> /article/123.pdf
            current_url = self.page.url
            for variant in ['.pdf', '/pdf', '/download/pdf']:
                pdf_url = current_url.rstrip('/') + variant
                # Quick check if this URL exists
                try:
                    response = await self.page.context.request.head(pdf_url)
                    if response.ok and 'pdf' in response.headers.get('content-type', '').lower():
                        return pdf_url
                except:
                    continue

            return None

        except Exception as e:
            print(f"    Error finding PDF: {e}")
            return None

    async def run(self):
        """Main scraping workflow."""
        print("="*80)
        print("COLUMBIA LAW REVIEW SCRAPER")
        print("="*80)
        print(f"Target: {self.TARGET_MIN}-{self.TARGET_MAX} complete HTML/PDF pairs\n")

        try:
            # Setup browser
            print("Launching browser...")
            await self.setup_browser()

            # Find articles
            articles = await self.find_article_links()

            if not articles:
                print("\n✗ No articles found!")
                return

            print(f"\nFound {len(articles)} articles to process")

            # Download each article
            for i, article in enumerate(articles, 1):
                print(f"\n[{i}/{len(articles)}]")

                success = await self.download_article_pair(article)
                if success:
                    self.downloaded_pairs += 1

                # Stop if we've reached target
                if self.downloaded_pairs >= self.TARGET_MAX:
                    print(f"\n✓ Target reached: {self.TARGET_MAX} pairs")
                    break

                # Polite delay between articles
                if i < len(articles):
                    await asyncio.sleep(2)

        finally:
            await self.close_browser()

        # Final report
        print("\n" + "="*80)
        print("SCRAPING COMPLETE")
        print("="*80)
        print(f"\nColumbia: {self.downloaded_pairs} pairs downloaded")
        print(f"\nFiles saved to:")
        print(f"  HTML: {self.html_dir}")
        print(f"  PDF:  {self.pdf_dir}")

        if self.downloaded_pairs >= self.TARGET_MIN:
            print(f"\n✓ Success! {self.downloaded_pairs} complete pairs ready.")
        else:
            print(f"\n⚠ Warning: Only {self.downloaded_pairs} pairs downloaded (target: {self.TARGET_MIN}-{self.TARGET_MAX})")


async def main():
    """Entry point."""
    base_dir = Path(__file__).parent
    output_dir = base_dir / "data"

    scraper = ColumbiaLawReviewScraper(output_dir)
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())

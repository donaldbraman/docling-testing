#!/usr/bin/env python3
"""
Harvard Law Review Article Scraper

Scrapes 5-10 full articles from Harvard Law Review using Playwright to bypass 403 errors.
Saves both HTML (with expanded footnotes) and PDF for each article.

Target: 5-10 complete HTML/PDF pairs
Quality checks:
- HTML >20KB with footnotes
- PDF >100KB, valid format
- Footnotes NOT truncated

Issue #5: Expand Training Corpus - Harvard Law Review
"""

import json
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from playwright.sync_api import sync_playwright, Page, Browser


class HarvardLawReviewScraper:
    """Scrapes articles from Harvard Law Review using Playwright."""

    def __init__(self, output_dir: Path):
        """Initialize scraper."""
        self.output_dir = output_dir
        self.html_dir = output_dir / "raw_html"
        self.pdf_dir = output_dir / "raw_pdf"

        # Create output directories
        self.html_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

        self.base_url = "https://harvardlawreview.org"
        self.target_count = 10  # Target 10 articles
        self.min_target = 5     # Minimum acceptable

        # Statistics
        self.stats = {
            'articles_found': 0,
            'html_downloaded': 0,
            'pdf_downloaded': 0,
            'pairs_complete': 0,
            'quality_passed': 0,
        }

    def _sanitize_filename(self, name: str) -> str:
        """Convert name to safe filename."""
        # Replace special characters with underscores
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '_', name)
        return name[:100]  # Limit length

    def _expand_footnotes(self, page: Page) -> None:
        """Execute JavaScript to expand truncated footnotes."""
        try:
            # Common patterns for expanding footnotes in law review sites:
            # 1. Click "Show more" buttons
            # 2. Expand collapsed sections
            # 3. Remove truncation CSS classes

            expand_js = """
            // Find and click all "Show more", "Expand", "Read more" buttons
            const expandButtons = Array.from(document.querySelectorAll('button, a, span'))
                .filter(el => {
                    const text = el.textContent.toLowerCase();
                    return text.includes('show more') ||
                           text.includes('expand') ||
                           text.includes('read more') ||
                           text.includes('view all');
                });
            expandButtons.forEach(btn => btn.click());

            // Remove truncation classes
            const truncated = document.querySelectorAll('.truncated, .collapsed, .hidden-content');
            truncated.forEach(el => {
                el.classList.remove('truncated', 'collapsed', 'hidden-content');
                el.style.display = 'block';
                el.style.maxHeight = 'none';
            });

            // Expand any footnotes specifically
            const footnotes = document.querySelectorAll('.footnote, [class*="footnote"]');
            footnotes.forEach(fn => {
                fn.style.display = 'block';
                fn.style.maxHeight = 'none';
            });
            """

            page.evaluate(expand_js)
            time.sleep(1)  # Wait for any animations

        except Exception as e:
            print(f"        Warning: Could not expand footnotes: {e}")

    def _validate_html_quality(self, html_path: Path) -> bool:
        """Validate HTML meets quality requirements."""
        try:
            size = html_path.stat().st_size
            if size < 20 * 1024:  # Less than 20KB
                print(f"        ✗ HTML too small: {size} bytes")
                return False

            # Check for footnotes
            content = html_path.read_text(encoding='utf-8', errors='ignore')
            footnote_indicators = [
                'footnote',
                'endnote',
                'note-',
                'fn-',
                '<sup>',
                '[1]',
                'See id.',
                'See also',
            ]

            has_footnotes = any(indicator in content for indicator in footnote_indicators)
            if not has_footnotes:
                print(f"        ✗ No footnotes detected")
                return False

            print(f"        ✓ HTML quality OK: {size} bytes, footnotes present")
            return True

        except Exception as e:
            print(f"        ✗ HTML validation error: {e}")
            return False

    def _validate_pdf_quality(self, pdf_path: Path) -> bool:
        """Validate PDF meets quality requirements."""
        try:
            size = pdf_path.stat().st_size
            if size < 100 * 1024:  # Less than 100KB
                print(f"        ✗ PDF too small: {size} bytes")
                return False

            # Check PDF header
            with open(pdf_path, 'rb') as f:
                header = f.read(5)
                if not header.startswith(b'%PDF-'):
                    print(f"        ✗ Invalid PDF format")
                    return False

            print(f"        ✓ PDF quality OK: {size} bytes")
            return True

        except Exception as e:
            print(f"        ✗ PDF validation error: {e}")
            return False

    def discover_articles(self, page: Page) -> List[Dict]:
        """Discover recent full articles (not book reviews or short essays)."""
        print(f"\n  Navigating to {self.base_url}...")

        try:
            # Navigate to homepage with longer timeout and less strict wait condition
            page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
            print(f"  ✓ Page loaded")
            time.sleep(3)  # Give extra time for JavaScript to load

            # Wait for content to load
            page.wait_for_selector('article, .article, [class*="article"]', timeout=10000)

            # Extract article links
            # Look for full articles, avoiding book reviews and short pieces
            articles = []

            # Try multiple selectors to find articles
            selectors = [
                'article a[href*="/vol-"]',  # Volume-based URLs
                'a[href*="/articles/"]',
                '.article-title a',
                'article h2 a',
                'article h3 a',
            ]

            for selector in selectors:
                try:
                    links = page.query_selector_all(selector)
                    for link in links:
                        try:
                            href = link.get_attribute('href')
                            title = link.inner_text().strip()

                            if not href or not title:
                                continue

                            # Skip book reviews, commentaries, essays (look for full articles)
                            skip_keywords = [
                                'book review',
                                'commentary',
                                'essay',
                                'response',
                                'reply',
                                'foreword',
                                'symposium',
                            ]

                            if any(keyword in title.lower() for keyword in skip_keywords):
                                continue

                            # Make absolute URL
                            if href.startswith('http'):
                                article_url = href
                            else:
                                article_url = f"{self.base_url}{href}" if href.startswith('/') else f"{self.base_url}/{href}"

                            # Avoid duplicates
                            if any(a['url'] == article_url for a in articles):
                                continue

                            articles.append({
                                'title': title,
                                'url': article_url,
                            })

                        except Exception as e:
                            continue

                    if articles:
                        break  # Found articles with this selector

                except Exception as e:
                    continue

            print(f"  ✓ Found {len(articles)} potential articles")
            return articles[:self.target_count]  # Limit to target count

        except Exception as e:
            print(f"  ✗ Error discovering articles: {e}")
            return []

    def download_article_pair(self, page: Page, article: Dict) -> bool:
        """Download both HTML and PDF for an article."""
        title = article['title']
        url = article['url']

        print(f"\n  Article: {title[:60]}...")
        print(f"    URL: {url}")

        # Generate filenames
        title_slug = self._sanitize_filename(title)
        base_filename = f"harvard_law_review_{title_slug}"
        html_path = self.html_dir / f"{base_filename}.html"
        pdf_path = self.pdf_dir / f"{base_filename}.pdf"

        # Skip if both exist and pass quality checks
        if html_path.exists() and pdf_path.exists():
            if self._validate_html_quality(html_path) and self._validate_pdf_quality(pdf_path):
                print(f"    ✓ Already downloaded and validated")
                self.stats['pairs_complete'] += 1
                self.stats['quality_passed'] += 1
                return True

        try:
            # Navigate to article page
            print(f"    Loading article page...")
            page.goto(url, wait_until='domcontentloaded', timeout=60000)

            # Wait for main content
            page.wait_for_selector('article, .article-content, [class*="article"]', timeout=10000)
            time.sleep(2)  # Extra time for lazy-loaded content

            # Expand footnotes
            print(f"    Expanding footnotes...")
            self._expand_footnotes(page)

            # Save HTML
            print(f"    Saving HTML...")
            html_content = page.content()
            html_path.write_text(html_content, encoding='utf-8')

            if not self._validate_html_quality(html_path):
                html_path.unlink()  # Remove invalid HTML
                print(f"    ✗ HTML failed quality check")
                return False

            self.stats['html_downloaded'] += 1

            # Find and download PDF
            print(f"    Searching for PDF...")
            pdf_url = None

            # Strategy 1: Look for PDF link on page
            try:
                pdf_links = page.query_selector_all('a[href*=".pdf"], a[href*="/pdf"]')
                for link in pdf_links:
                    href = link.get_attribute('href')
                    if href:
                        if href.startswith('http'):
                            pdf_url = href
                        else:
                            pdf_url = f"{self.base_url}{href}" if href.startswith('/') else f"{self.base_url}/{href}"
                        break
            except:
                pass

            # Strategy 2: Try common PDF URL patterns
            if not pdf_url:
                # Extract slug from URL
                url_parts = url.rstrip('/').split('/')
                if len(url_parts) >= 2:
                    # Try: /print/{slug}/ or /pdf/{slug}.pdf
                    slug = url_parts[-1]
                    pdf_candidates = [
                        f"{self.base_url}/print/{slug}/pdf",
                        f"{self.base_url}/wp-content/uploads/{slug}.pdf",
                        f"{url}/pdf",
                        f"{url}.pdf",
                    ]

                    for candidate in pdf_candidates:
                        try:
                            response = page.request.get(candidate)
                            if response.ok and 'pdf' in response.headers.get('content-type', '').lower():
                                pdf_url = candidate
                                break
                        except:
                            continue

            if not pdf_url:
                print(f"    ✗ No PDF found")
                html_path.unlink()  # Remove HTML if no PDF (need pairs)
                self.stats['html_downloaded'] -= 1
                return False

            # Download PDF
            print(f"    Downloading PDF: {pdf_url}")
            try:
                response = page.request.get(pdf_url)
                if response.ok:
                    pdf_path.write_bytes(response.body())

                    if not self._validate_pdf_quality(pdf_path):
                        pdf_path.unlink()
                        html_path.unlink()  # Remove both if PDF fails
                        self.stats['html_downloaded'] -= 1
                        print(f"    ✗ PDF failed quality check")
                        return False

                    self.stats['pdf_downloaded'] += 1
                    self.stats['pairs_complete'] += 1
                    self.stats['quality_passed'] += 1
                    print(f"    ✓ Complete pair downloaded and validated!")
                    return True
                else:
                    print(f"    ✗ PDF download failed: {response.status}")
                    html_path.unlink()
                    self.stats['html_downloaded'] -= 1
                    return False

            except Exception as e:
                print(f"    ✗ Error downloading PDF: {e}")
                html_path.unlink()
                self.stats['html_downloaded'] -= 1
                return False

        except Exception as e:
            print(f"    ✗ Error: {e}")
            # Clean up partial downloads
            if html_path.exists():
                html_path.unlink()
            if pdf_path.exists():
                pdf_path.unlink()
            return False

    def scrape(self):
        """Main scraping function."""
        print(f"{'='*80}")
        print(f"HARVARD LAW REVIEW SCRAPER")
        print(f"{'='*80}")
        print(f"\nTarget: {self.min_target}-{self.target_count} complete HTML/PDF pairs")
        print(f"Output:")
        print(f"  HTML: {self.html_dir}")
        print(f"  PDF:  {self.pdf_dir}")

        with sync_playwright() as p:
            # Launch browser (headless for speed, but can set to False for debugging)
            print(f"\nLaunching browser...")
            browser = p.chromium.launch(headless=True)

            # Create context with realistic headers to avoid detection
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
            )

            page = context.new_page()

            try:
                # Discover articles
                articles = self.discover_articles(page)

                if not articles:
                    print(f"\n✗ No articles found!")
                    return

                self.stats['articles_found'] = len(articles)

                # Download pairs
                print(f"\n{'='*80}")
                print(f"DOWNLOADING ARTICLES")
                print(f"{'='*80}")

                for i, article in enumerate(articles, 1):
                    print(f"\n[{i}/{len(articles)}]")
                    success = self.download_article_pair(page, article)

                    # Stop if we've reached target
                    if self.stats['pairs_complete'] >= self.target_count:
                        print(f"\n✓ Target reached: {self.target_count} pairs")
                        break

                    # Brief delay between articles
                    if i < len(articles):
                        time.sleep(2)

            finally:
                browser.close()

        # Final report
        print(f"\n{'='*80}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*80}")
        print(f"\nStatistics:")
        print(f"  Articles found:     {self.stats['articles_found']}")
        print(f"  HTML downloaded:    {self.stats['html_downloaded']}")
        print(f"  PDF downloaded:     {self.stats['pdf_downloaded']}")
        print(f"  Complete pairs:     {self.stats['pairs_complete']}")
        print(f"  Quality passed:     {self.stats['quality_passed']}")

        # Success criteria
        if self.stats['pairs_complete'] >= self.min_target:
            print(f"\n✓ SUCCESS: Harvard: {self.stats['pairs_complete']} pairs downloaded")
        else:
            print(f"\n⚠️  INCOMPLETE: Only {self.stats['pairs_complete']} pairs (target: {self.min_target}-{self.target_count})")


def main():
    """Run Harvard Law Review scraper."""
    base_dir = Path(__file__).parent
    output_dir = base_dir / "data"

    scraper = HarvardLawReviewScraper(output_dir)
    scraper.scrape()

    print(f"\n{'='*80}")
    print(f"Next steps:")
    print(f"  1. Review files in {scraper.html_dir}")
    print(f"  2. Review files in {scraper.pdf_dir}")
    print(f"  3. Run label transfer: python match_html_pdf.py")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

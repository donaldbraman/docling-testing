# Law Review HTML-PDF Pair Collection Strategy
## Multi-Agent Parallel Collection Guide

**Objective:** Each agent collects 10 HTML-PDF pairs from assigned law review(s)
**Target:** Polite, persistent, diverse strategy approach to maximize success across varied website structures
**Context:** Building DoclingBERT v3 training corpus - we need document layout diversity

---

## 🎯 Success Criteria

Per Agent/Journal:
- ✅ Collect **minimum 10 complete HTML-PDF pairs** (stretch goal: 15+)
- ✅ All pairs are **full articles** (not comments, book reviews, short essays <5k words)
- ✅ Files are **complete and readable**
- ✅ Both HTML and PDF exist for each article
- ✅ **No blocking/blacklisting** occurred
- ✅ **Documentation** of strategies tried and success rates

---

## 🛠️ Agent Setup & Tools

**Agent Type:** `general-purpose` (has access to all tools)

### ✅ Tools & Dependencies Status

All required tools are installed and ready:

```
System Tools:
✓ curl          /usr/bin/curl        (HTTP requests, file downloads)
✓ wget          /opt/homebrew/bin/wget (Alternative downloads)

Python Packages (via uv):
✓ requests      2.31.0+  (HTTP with sessions, automatic retries)
✓ beautifulsoup4 4.12.0+ (HTML parsing, CSS selectors)
✓ feedparser    6.0.12+  (RSS/Atom feed parsing)
✓ lxml          5.4.0+   (XML/HTML processing)
✓ pandas        2.1.0+   (Data handling, CSV output)
✓ pypdf         6.1.1+   (PDF validation)

Built-in Tools:
✓ WebFetch      (HTML retrieval with JavaScript rendering)
✓ Bash          (Shell commands, curl, wget)
✓ Python        (Script execution)
✓ File Ops      (Read, Write, Glob, Grep)
```

### How to Run Commands in Agent Context

```python
# When agent runs collection script:
# Use: uv run python scripts/collection_agent.py

# This ensures:
# - Correct Python environment
# - All dependencies available
# - Consistent across runs
```

### Tool Selection by Discovery Strategy

| Strategy | Primary Tool | Backup Tool | Best For |
|----------|--|--|--|
| Browse Recent Issues | WebFetch | Bash (curl) | Human-readable navigation |
| Search + Crawl | WebFetch + Python | Bash (curl + grep) | Dynamic search parsing |
| Archive/Browse | WebFetch | Bash (curl) | Static archive structures |
| RSS Feed | Bash (curl) | Python (feedparser) | Structured data extraction |
| URL Pattern Construction | Bash (curl with retry logic) | Python | Batch verification |
| PDF Discovery | Bash (curl with size check) | Python (PDF validation) | File verification |

### Detailed Tool Usage

**WebFetch Tool:**
- ✅ Best for: Initial HTML page retrieval, JavaScript rendering
- ✅ Handles: 403 errors better than raw curl
- ✅ Usage: Fetch article page to extract PDF link
- ⚠️ Limitation: Returns rendered HTML but may not capture dynamic PDFs

**Bash (curl/wget):**
- ✅ Best for: PDF downloads, direct file transfers
- ✅ Handles: Large binary files, timeout control
- ✅ Usage: `curl -o article.pdf --max-time 30 "{pdf_url}"`
- ⚠️ Limitation: May hit 403 on first attempts (use WebFetch for HTML first)

**Python:**
- ✅ Best for: Parsing HTML, extracting URLs, validating files
- ✅ Tools: BeautifulSoup (HTML parsing), requests (HTTP with sessions)
- ✅ Usage: Parse article pages to find PDF links, validate file integrity
- ⚠️ Limitation: Slower than bash for simple downloads

**File Operations:**
- ✅ Read: Check downloaded file validity
- ✅ Glob: Find already-downloaded files, avoid duplicates
- ✅ Grep: Extract URLs from HTML

---

## 🔄 Multi-Stage Discovery Pipeline

### Stage 1: Reconnaissance (5-10 min per journal)
*Learn the journal's website structure before attempting collection*

**Phase 1A: Information Gathering**
```
1. Check robots.txt for allowed paths
   - Visit: https://{base_url}/robots.txt
   - Look for: Disallowed paths, crawl delays, user-agent rules
   - Decision: If crawling explicitly forbidden, skip to Polite Contact strategy

2. Find site map or archive
   - Look for: /sitemap.xml, /sitemap_index.xml, /archives, /browse
   - Alternative: /issues, /volumes, /years, /browse-by-date
   - Note: Some journals use multiple naming conventions

3. Locate search functionality
   - Search bar usually at top of site
   - Try simple search like: keyword "law" or "court"
   - Note: Query parameters for future use

4. Check for recent articles page
   - Look for: /latest, /recent, /news, /current, /newest
   - Many journals have homepage curated list

5. Scan for available access levels
   - Open access vs. paywall
   - Preview/abstract only vs. full text
   - Print-friendly versions (often more stable)
```

**Phase 1B: URL Pattern Discovery (Using WebFetch)**
```python
# Tool: WebFetch
# 1. Fetch homepage
html = WebFetch("{base_url}", "Extract article URLs and links")

# Tool: Grep (or Python parsing)
# 2. Find article links
article_urls = extract_urls_from_html(html, pattern="article|vol|issue")

# Tool: Python
# 3. Parse and document patterns
for url in article_urls[:3]:
    pattern = categorize_url_pattern(url)
    # Output: {base_url}/articles/{slug}, {base_url}/vol-{v}/{slug}, etc.

# Document: Save patterns to journal_config.json
```

Discovered patterns should include:
   - Pattern: /articles/{slug}, /vol-{v}/{slug}, /issues/{v}/{i}/{slug}
   - Some use: /print/article/{slug}, /articles/view/{id}
   - Volume/issue/article numbering scheme
   - Consistent slug formatting (underscores, hyphens, etc.)
   - PDF URL patterns (e.g., /download, /pdf, /file)

---

### Stage 2: Discovery Strategies (Parallel Attempt)
*Try multiple approaches simultaneously; first success wins*

#### Strategy A: Browse Recent Issues (EASIEST - Try First)
```python
# Approach: Human-readable browsing of current/recent content
1. Navigate to: {base_url} (homepage)
2. Look for: "Latest Articles", "Current Issue", "Browse"
3. Click on recent articles to get URLs
4. Pattern matching: Extract URL structure
5. Repeat for 10-15 different article URLs

Success Rate: 70-85% (most journals maintain recent articles page)
Time: 3-5 minutes per journal
Blocking Risk: Very Low
```

**Tactical Implementation:**
```
- Look for visual cards/list with article titles and dates
- Sort by: Most Recent, Latest, Newest
- Click first article and note HTML URL
- Find PDF link on article page (button or sidebar)
- Save both URLs
- Repeat 10 times with different articles
```

#### Strategy B: Search + Crawl (BALANCED)
```python
# Approach: Use search to discover articles, then navigate
1. Use site-specific search with broad terms:
   - "law" OR "court" OR "legal" (just to get results)
   - Keywords related to section: "employment", "constitutional", "contract"

2. For each search result:
   - Click article link (gets article page URL)
   - Extract PDF URL from page (usually obvious button/link)
   - Verify both files exist before saving

3. Continue with different search terms until 10 pairs

Success Rate: 65-80%
Time: 5-8 minutes per journal
Blocking Risk: Low-Medium (search is generally allowed)
```

**Tactical Implementation:**
```
- Search 1: "law" (get random articles)
- Search 2: "court" (get different results)
- Search 3: "{specific-field}" based on journal focus
- Search 4-5: Variations to find more articles
- For each result: Click article, extract HTML + PDF URLs
```

#### Strategy C: Archive/Browse by Volume (MOST COMPLETE)
```python
# Approach: Navigate journal's archive structure
1. Find: {base_url}/archives or {base_url}/browse or similar
2. Select latest volume (if listing available)
3. Select latest issue within volume
4. Browse articles in that issue:
   - Click article title
   - Note article URL
   - Find PDF download link
   - Save pair

5. Go back, select previous volume/issue, repeat

Success Rate: 80-90% (very reliable if archive exists)
Time: 8-12 minutes per journal
Blocking Risk: Very Low (archives are meant to be browsed)
```

**Implementation Checklist:**
```
☐ Navigate to /archives or /browse
☐ Select latest volume
☐ Select latest issue (often "Issue 1" or "Issue 6")
☐ For each article on page:
  ☐ Click article title → get HTML URL
  ☐ Find PDF link (Download, PDF, View PDF button)
  ☐ Note both URLs
  ☐ Check file exists (200 OK response)
☐ Repeat for previous volume/issue
```

#### Strategy D: RSS/Feed Discovery (MODERATE)
```python
# Approach: Journal RSS feeds often list recent content
1. Look for: /feed, /rss.xml, /atom.xml at {base_url}
2. Fetch feed and parse article URLs
3. Each feed entry may contain:
   - Article URL
   - Direct PDF link
   - Publication date

4. For each entry: Extract article URL, navigate to get PDF URL

Success Rate: 40-60% (not all journals have feeds)
Time: 3-5 minutes if feed exists
Blocking Risk: Very Low
```

**Implementation:**
```bash
# Try common feed URLs:
- {base_url}/feed
- {base_url}/rss.xml
- {base_url}/feed/rss
- {base_url}/atom.xml
- {base_url}/feed/atom

# If found: Parse XML for article links
# Extract from: <link>, <id>, <content>, <enclosure>
```

#### Strategy E: Direct Pattern URL Construction (ADVANCED)
```python
# Approach: Use discovered patterns to construct URLs directly
1. From Stage 1, you identified URL pattern (e.g., /articles/{slug})
2. Try constructing URLs with common article slugs:
   - "2024-volume-recent"
   - "latest-articles"
   - "featured-2024"

3. For each constructed URL: Test if article exists (200 OK)
4. If exists: Extract PDF link from HTML

Success Rate: 20-40% (hit-or-miss)
Time: 3-5 minutes
Blocking Risk: Low-Medium (might trigger rate limiting if too many 404s)
```

---

### Stage 3: PDF Discovery (Article Page Parsing)

Once you have article HTML page, extract PDF link:

**Standard PDF Link Locations:**
```
1. Download button/link (most common)
   - Selector: a[href*=".pdf"], button[class*=download]
   - Text: "PDF", "Download", "Download PDF", "View PDF"

2. Sidebar buttons
   - Right sidebar often has: PDF, EPUB, Share, Cite buttons

3. Toolbar buttons
   - Top of article: Download, Print, etc.

4. Footer links
   - Bottom of page: Often has format options

5. Direct URL patterns
   - /articles/{slug}.pdf
   - /articles/{slug}/download
   - /pdf/{article_id}
   - /files/{article_id}.pdf
   - CDN: /wp-content/uploads/... (WordPress pattern)
   - Publisher CDN: /content/dam/...
```

**Fallback PDF Discovery:**
```
If no obvious PDF link found:

1. Check page HTML for <iframe> with PDF viewer
   - Extract src attribute for PDF URL

2. Check for data-pdf or data-file attributes
   - JavaScript might lazy-load PDF URL

3. Try common filename patterns:
   - Article title + author + year
   - Volume + issue + page numbers
   - Example: "smith_contract_law_v77_p1.pdf"

4. Check breadcrumbs or metadata for clues
   - Citation info often points to PDF location

5. Try direct CDN URLs:
   - Replace /articles/{slug} with /wp-content/uploads/...
   - Replace domain with publisher CDN
```

---

## 🛡️ Politeness & Rate Limiting Strategy

### HTTP Headers (Identify Yourself Respectfully)
```
User-Agent: "DoclingBERT-MLResearch/1.0 (+https://github.com/your-org/docling-testing; research@example.com)"
Accept: "text/html,application/pdf,application/xhtml+xml"
Accept-Language: "en-US,en;q=0.9"
Referer: "{base_url}"
```

### Rate Limiting Protocol
```
☐ 2-3 second delay between requests to SAME domain
☐ Respect 429 (Too Many Requests) - back off for 1 hour
☐ Respect 503 (Service Unavailable) - wait 5 minutes, retry once
☐ Respect 403 (Forbidden) - switch to alternative strategy/journal
☐ If blocked: Log time/URL, wait 24 hours before retrying
☐ Max 10 articles per hour from single journal
```

### Blocking Detection & Response
```
If you get consecutive blocks (429, 403, 410):
1. First attempt: Wait 15 minutes, use different strategy
2. Second attempt: Wait 1 hour, try alternative journal temporarily
3. Third attempt: Skip this journal for 24 hours
4. Document: What triggered blocking, recovery time needed

If page load is very slow (>10s):
1. Server is under load - increase delays to 5 seconds
2. Consider switching to alternative journal
3. Come back in 1 hour
```

---

## 📋 Practical Workflow (Per Agent)

### Agent Pseudocode (High-Level Workflow)

```python
# ============================================================================
# LAW REVIEW COLLECTION AGENT - Main Loop
# ============================================================================

import sys
sys.path.insert(0, "/path/to/tools")  # WebFetch, Bash, Python, File ops

JOURNAL = "michigan_law_review"
BASE_URL = "https://michiganlawreview.org"
TARGET = 10
PAIRS_COLLECTED = []

# PHASE 1: RECONNAISSANCE
print(f"[PHASE 1] Reconnaissance: Learning {JOURNAL} structure...")

# Check robots.txt (Bash)
robots = fetch_robots(BASE_URL)  # → curl {base_url}/robots.txt
if is_crawling_forbidden(robots):
    print("ERROR: Crawling forbidden by robots.txt")
    sys.exit(1)

# Find article structure (WebFetch)
homepage_html = WebFetch(BASE_URL, "Find article links and structure")
discovered_patterns = extract_url_patterns(homepage_html)
print(f"Discovered patterns: {discovered_patterns}")

# PHASE 2: DISCOVERY (Try strategies in order)
print(f"[PHASE 2] Discovery: Finding articles...")

strategies = [
    ("browse_recent", 10, 0.7),    # strategy, articles, success_rate
    ("search_crawl", 10, 0.65),
    ("archive_browse", 10, 0.8),
    ("rss_feed", 5, 0.4),
]

for strategy_name, target_articles, expected_rate in strategies:
    if len(PAIRS_COLLECTED) >= TARGET:
        break

    needed = TARGET - len(PAIRS_COLLECTED)
    print(f"\n[STRATEGY] {strategy_name}: Attempting to find {needed} more articles...")

    if strategy_name == "browse_recent":
        # Strategy A: Browse Recent Issues
        articles = strategy_browse_recent(BASE_URL, discovered_patterns)
        # Returns list of (html_url, pdf_url) tuples

    elif strategy_name == "search_crawl":
        # Strategy B: Search + Crawl
        articles = strategy_search_crawl(BASE_URL)

    elif strategy_name == "archive_browse":
        # Strategy C: Archive/Browse by Volume
        articles = strategy_archive_browse(BASE_URL, discovered_patterns)

    elif strategy_name == "rss_feed":
        # Strategy D: RSS Feed
        articles = strategy_rss_feed(BASE_URL)

    # PHASE 3: VERIFICATION & COLLECTION
    for html_url, pdf_url in articles:
        if len(PAIRS_COLLECTED) >= TARGET:
            break

        print(f"  Verifying pair: {html_url}")

        # Check HTML (Bash: curl -I)
        if not verify_url(html_url):
            print(f"    ✗ HTML not accessible")
            continue

        # Check PDF (Bash: curl -I)
        if not verify_url(pdf_url):
            print(f"    ✗ PDF not accessible")
            # Try PDF fallback patterns
            pdf_url = find_pdf_fallback(html_url)
            if not verify_url(pdf_url):
                continue

        # Download HTML (WebFetch)
        html_content = WebFetch(html_url, "Download full article HTML")

        # Download PDF (Bash: curl)
        pdf_path = bash_download_pdf(pdf_url, timeout=30)

        # Validate files (Python + File operations)
        if validate_html(html_content) and validate_pdf(pdf_path):
            # Save files (Write)
            save_pair(JOURNAL, html_url, pdf_url, html_content, pdf_path)
            PAIRS_COLLECTED.append((html_url, pdf_url))
            print(f"    ✓ Saved ({len(PAIRS_COLLECTED)}/{TARGET})")
        else:
            print(f"    ✗ Validation failed")

# PHASE 4: REPORTING
print(f"\n[PHASE 4] Completion Report")
print(f"Collected: {len(PAIRS_COLLECTED)}/{TARGET}")
print(f"Success Rate: {100 * len(PAIRS_COLLECTED) / TARGET:.1f}%")
print(f"Files Location: data/raw_html/{JOURNAL}_*.html, data/raw_pdf/{JOURNAL}_*.pdf")

# ============================================================================
```

### Setup Phase (5 min)
```bash
# 1. Create working directory (using Bash)
mkdir -p data/collection_logs/{journal_name}

# 2. Create tracking file
cat > data/collection_logs/{journal_name}/progress.txt << EOF
Journal: {journal_name}
Base URL: {base_url}
Target: 10 complete pairs
Start Time: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

Status: IN_PROGRESS

Discovery Strategy: [To be filled]
Success Count: 0/10
EOF

# 3. Create URLs file
touch data/collection_logs/{journal_name}/urls.txt
```

### Collection Phase (20-30 min per 10 articles)
```bash
# For each article discovered:

1. Verify HTML is accessible
   curl -I --max-time 10 "{html_url}"  # Check HTTP headers

2. Verify PDF is accessible
   curl -I --max-time 10 "{pdf_url}"

3. If both 200 OK:
   - Log URLs to tracking file
   - Download article HTML (using WebFetch or curl)
   - Download PDF (using curl with large timeout)
   - Name files: {journal_slug}_{article_slug}.{ext}

4. If either failed:
   - Try alternative PDF link patterns
   - Try alternative discovery strategy
   - Document failure reason

5. Verification check:
   - HTML file size > 15KB
   - PDF file size > 50KB (most law review PDFs are large)
   - Both files are readable (spot check)
```

### Completion Phase
```bash
# When 10 articles collected:

1. Create collection report
   - Journal name, base URL
   - Discovery strategies used
   - Success rate (X/10 pairs)
   - Time taken
   - Any blockers encountered
   - File list with sizes

2. Copy files to standard locations:
   - HTML → data/raw_html/{journal_slug}_{article_slug}.html
   - PDF → data/raw_pdf/{journal_slug}_{article_slug}.pdf

3. Verify files are readable:
   - HTML: Contains article text (grep for 20+ unique words)
   - PDF: Not corrupted (file command shows "PDF")

4. Commit files with descriptive message
```

---

## 🚨 Troubleshooting & Fallback Strategies

### Problem: No Recent Articles Page Found
**Fallback Approach:**
```
1. Try these alternative locations:
   - /latest
   - /news
   - /newest
   - /current-issue
   - /vol-{latest-vol}

2. If still not found:
   - Go to homepage and look for article cards/blocks
   - Manually click 3-5 visible articles
   - Use search strategy instead
```

### Problem: Articles Behind Paywall
**Fallback Approach:**
```
1. Check if free preview/abstract available
   - Some journals show PDF preview (read-only)
   - Extract what you can

2. Try alternative access:
   - Google Scholar: scholar.google.com
     Search: "article title" + journal name
     Often links to free versions

   - ResearchGate: researchgate.net
     Authors often post their own PDFs

   - SSRN: ssrn.com
     Legal papers repository

   - Academia.edu: academia.edu
     Author community repository

   - Author's institution repository
     e.g., MIT faculty often host on faculty pages

3. Last resort - respectful contact:
   - Email: submissions@{journal_url}
   - Subject: "Research data collection request - DoclingBERT v3"
   - Request: "Could you provide PDF access for training research?"
   - Many journals grant access for legitimate research
```

### Problem: 403 Forbidden (Bot Detection)
**Fallback Approach:**
```
1. First attempt - change headers:
   - Different User-Agent from known browser
   - Add: Referer, Accept-Language, Accept-Encoding

2. Second attempt - change timing:
   - Increase delays to 5-10 seconds
   - Wait 30 minutes before retry

3. Third attempt - use alternative tool:
   - Try WebFetch instead of curl
   - Try different discovery strategy (RSS vs. search)

4. If persistent:
   - Skip to other journals
   - Come back to this one in 24 hours
   - Try different IP if available
```

### Problem: PDF URL Not Found on Article Page
**Fallback Approach:**
```
1. Check page source for hidden/lazy-loaded URLs:
   - data-pdf="..." attributes
   - JavaScript variables: pdf_url, file_url
   - <script> tags with URL data

2. Try URL pattern variations:
   If article URL is: /articles/my-article-slug
   Try:
   - /articles/my-article-slug.pdf
   - /articles/my-article-slug/pdf
   - /download/my-article-slug
   - /files/my-article-slug.pdf

3. Check for alternative formats:
   - EPUB available but not PDF? → Skip
   - Print view available? → Use that
   - Abstract only? → Try alternative article

4. Search for article in Google Scholar:
   - Often has links to PDF copies
   - May be author's personal copy
```

### Problem: Rate Limited (429 Too Many Requests)
**Immediate Response:**
```
1. STOP immediately
2. Wait 1 hour minimum
3. When resuming:
   - Increase delays to 10 seconds between requests
   - Collect fewer articles per hour (max 5/hour)
   - Switch to different journal temporarily
4. Document: Time blocked, recovery action
```

### Problem: Journal Website Significantly Restructured
**Adaptation Strategy:**
```
1. Follow Stage 1 reconnaissance again
2. Identify new URL patterns
3. Try discovery strategies in different order:
   - Archive/browse (most reliable)
   - Search (fallback)
   - RSS feed (if available)
4. Adjust for changes
5. Document structural changes for future reference
```

### Problem: Journal Only Provides Abstracts in HTML (NOT Full Text)
**CRITICAL BLOCKER - Cannot Collect HTML-PDF Pairs**

**Detection:**
```
1. Navigate to article page
2. Check visible text length:
   - Abstract-only: ~200-500 words
   - Full article: >5,000 words
3. Look for "Download PDF" or "Read Full Text" buttons
   - If PDF is ONLY access method → BLOCKER
4. Check HTML source for article body content
   - Look for: <article>, <div class="content">, <section class="body">
   - If only abstract/metadata visible → BLOCKER
```

**Known Journals with This Architecture:**
- NYU Law Review (https://nyulawreview.org) - Abstract + PDF only
  - Tested: 2024-10-16
  - Pattern: WordPress CMS with abstract-only HTML
  - PDFs available but no HTML full text
  - Volume 99-100 (2024-2025) confirmed

**Recommendation:**
```
SKIP these journals for HTML-PDF pair collection.
These journals are suitable for:
- PDF-only corpus building
- Abstract/metadata extraction
- Citation network analysis

NOT suitable for:
- HTML-PDF structure comparison
- HTML parsing training data
- Multi-format layout learning
```

**Alternative Action:**
```
1. Mark journal as "PDF-only" in journal compatibility matrix
2. Move to next assigned journal
3. Document finding in collection_logs/{journal}/progress.txt
4. Focus effort on journals with full HTML text
```

**How to Identify HTML Full-Text Journals:**
```
Positive indicators:
- Article page shows >2,000 words of visible content
- Multiple sections/headings visible in HTML
- Footnotes/endnotes rendered in HTML
- Tables/figures embedded in page (not just images)
- "Print view" or "HTML view" option available

Negative indicators:
- Only abstract + metadata visible
- Prominent "Download PDF" as primary access
- Text cuts off with "...read more in PDF"
- Article content in <iframe> from PDF viewer
```

---

## 🎯 Discovery Strategy Priority Order (By Journal Type)

### Type 1: Modern Website (20+ articles/year published recently)
**Recommended Strategy Order:**
1. Browse Recent Issues → 70% success rate
2. Search Functionality → 20% success rate
3. Archive Navigation → 8% success rate
4. RSS Feed → 2% success rate

### Type 2: Institutional Repository (hosted on scholarship.law.*)
**Recommended Strategy Order:**
1. Archive/Browse by Volume → 90% success rate
2. Search Functionality → 8% success rate
3. Recent Articles → 2% success rate

### Type 3: Older/Legacy Website (unclear structure)
**Recommended Strategy Order:**
1. Search Functionality → 60% success rate
2. RSS Feed → 20% success rate
3. Direct URL Patterns → 15% success rate
4. Contact Webmaster → 5% success rate

---

## 📊 Multi-Agent Coordination

### Journal Assignment Template
```
Agent 1:  Harvard Law Review        (10 pairs target)
Agent 2:  Stanford Law Review       (10 pairs target)
Agent 3:  Yale Law Journal          (10 pairs target)
Agent 4:  Columbia Law Review       (10 pairs target)
Agent 5:  University of Chicago LR  (10 pairs target)
Agent 6:  NYU Law Review            (10 pairs target)
Agent 7:  Virginia Law Review       (10 pairs target)
Agent 8:  Duke Law Journal          (10 pairs target)
Agent 9:  Michigan Law Review       (10 pairs target)
Agent 10: UCLA Law Review           (10 pairs target)

... (continue for 20-30+ agents for comprehensive coverage)
```

### Parallel Execution Rules
```
✓ Agents work independently and in parallel
✓ No shared rate-limit concerns (different domains)
✓ Report successes/blockers in real-time
✓ If agent reaches target early, help another agent
✓ If agent gets blocked, switch to backup journal
```

### Progress Tracking
```
Each agent maintains: {journal}/progress.txt

Format:
START_TIME: 2025-10-16T14:30:00Z
JOURNAL: Michigan Law Review
BASE_URL: https://michiganlawreview.org

STRATEGY_ATTEMPT_1: Browse Recent → SUCCESS (4/10)
STRATEGY_ATTEMPT_2: Search Law → SUCCESS (3/10)
STRATEGY_ATTEMPT_3: Archive Volume 123 → SUCCESS (3/10)

FINAL_COUNT: 10/10 ✓
BLOCKERS_ENCOUNTERED: None
TIME_ELAPSED: 28 minutes
SUCCESS_RATE: 100%

FILES_SAVED: data/raw_html/michigan_law_review_*.html (10 files)
FILES_SAVED: data/raw_pdf/michigan_law_review_*.pdf (10 files)
```

---

## 🔐 Quality Assurance Checklist

Before reporting success:

```
☐ 10+ complete HTML-PDF pairs collected
☐ All files are readable (spot check 3-5 files)
☐ HTML files > 15KB and contain article text
☐ PDF files > 50KB and valid PDF format
☐ Naming convention followed: {journal_slug}_{article_slug}.{ext}
☐ No paywall-locked articles included
☐ All articles are full articles (not comments/short pieces)
☐ Articles are recent (preferably 2020+ publications)
☐ No duplicate articles across pairs
☐ Filename contains clear journal/article identifiers
☐ Permissions/blocking: No 403/429 errors encountered
☐ Rate limiting respected throughout (no >5 failures due to rate limit)
☐ Collection report generated with metadata
☐ No copyright/legal concerns (all from open-access law reviews)
```

---

## 📞 Emergency Contact Escalation

**If agent is unable to reach target:**

1. **First 5 articles (50% progress):**
   - Continue with different strategies
   - Try alternative discovery method
   - Persist for 45 minutes total

2. **5-8 articles collected (50-80% progress):**
   - Switch to backup journal
   - Document blocker encountered
   - Note: We'll revisit primary journal later

3. **Unable to get even 1 article:**
   - Try 2-3 backup journals immediately
   - Document technical issues
   - Note: This journal may need research team review

---

## 📝 Reporting Template

When collection complete (or time-boxed), provide:

```markdown
## Collection Report: {Journal Name}

**Statistics:**
- Target: 10 HTML-PDF pairs
- Collected: X/10 ✅ or ⏳
- Success Rate: X%
- Time Elapsed: X minutes

**Strategies Used:**
1. {Strategy A} → X articles found
2. {Strategy B} → X articles found
3. {Strategy C} → Attempted but {result}

**Blockers Encountered:**
- {Blocker 1}: {Resolution}
- {Blocker 2}: {Resolution}

**Files Location:**
- HTML: data/raw_html/[journal_slug]_*.html (X files)
- PDF: data/raw_pdf/[journal_slug]_*.pdf (X files)

**Key Discoveries:**
- PDF pattern: {pattern discovered}
- Best strategy: {most effective}
- Access level: Open / Partially Paywalled / Unknown

**Recommendations for Next Round:**
- {Any learnings or optimizations for future}
```

---

## 🌐 Useful Resources

### External Access Routes
- **Google Scholar:** scholar.google.com (free PDF versions often available)
- **SSRN:** ssrn.com (legal papers repository)
- **ResearchGate:** researchgate.net (authors share their work)
- **Academia.edu:** academia.edu (author community platform)
- **Internet Archive:** archive.org (Wayback Machine for historical captures)
- **WorldCat:** worldcat.org (library resource finder)

### Command-Line Tools
```bash
# Check article page accessibility
curl -I --max-time 10 "{article_url}"

# Download HTML with proper headers
curl -H "User-Agent: DoclingBERT-Research/1.0" \
     -H "Referer: https://example.com" \
     -o article.html \
     "{article_url}"

# Download PDF with timeout
curl --max-time 30 \
     -o article.pdf \
     "{pdf_url}"

# Check PDF validity
file article.pdf  # Should show "PDF document"
```

### Law Review Database
```
See: data/law_review_patterns.json
Contains: 100+ law reviews with URL patterns, search endpoints, known structures
Update this file as you discover new patterns/access methods
```

---

## ✅ Final Success Metrics

**Per Agent Success:**
- 10+ complete pairs ✅
- 0 accidental blocks/permanent bans ✅
- Respectful rate limiting maintained ✅
- Comprehensive progress documented ✅

**Aggregate Target (30 agents × 10 pairs):**
- 300+ HTML-PDF pairs collected
- 15+ different law reviews covered
- Multiple geographic/topical diversity
- Enables training of robust, generalizable DoclingBERT v3

---

## 📋 Journal Compatibility Matrix

**Purpose:** Track which journals provide HTML full text vs. abstract-only

| Journal | Base URL | HTML Full Text? | Status | Tested Date | Notes |
|---------|----------|----------------|--------|-------------|-------|
| NYU Law Review | https://nyulawreview.org | ❌ NO | Abstract-only | 2025-10-16 | WordPress, PDF-only access |
| Rutgers University Law Review | https://rutgerslawreview.com | ❌ NO | PDF-only | 2025-10-16 | WordPress, volume pages link directly to PDFs, no HTML article pages |
| UCLA Law Review | https://www.uclalawreview.org | ⚠️ PARTIAL | Mixed | 2025-10-16 | Print archive: abstract-only. Law Meets World/Discourse/Dialectic: full HTML text. Collected 15 articles. |
| Iowa Law Review | https://ilr.law.uiowa.edu | ❌ NO | Abstract-only | 2025-10-16 | Drupal CMS, abstract + PDF download only, ~200 word abstracts, 4 paragraph tags |
| Indiana Law Journal | https://www.repository.law.indiana.edu/ilj/ | ❌ NO | Abstract-only | 2025-10-16 | BePress Digital Commons, ~200-500 word abstracts, collected 10 pairs but NOT suitable for HTML-PDF training |
| *Add more as discovered* | | | | | |

**Legend:**
- ✅ YES = Full article text available in HTML (suitable for collection)
- ❌ NO = Abstract-only or PDF-only (NOT suitable for HTML-PDF pairs)
- ⚠️ PARTIAL = Some articles have HTML, others don't (case-by-case)
- ❓ UNKNOWN = Not yet tested

**Usage:**
1. Before starting collection on a new journal, check this matrix
2. If marked ❌ NO, skip and choose alternative journal
3. If marked ❓ UNKNOWN, perform Stage 1 reconnaissance first
4. Update matrix with findings after testing

---

**Remember:** Be polite, be persistent, be documented. Law reviews WANT their research discovered—finding the right approach is just engineering.

Generated: 2025-10-16
Updated: 2025-10-16 (Added NYU Law Review, Rutgers University Law Review, UCLA Law Review, and Iowa Law Review findings)
For: Issue #21 - Expand Training Corpus for DoclingBERT v3

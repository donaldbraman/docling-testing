# Law Review Collection Agent Mission

**Mission Type:** Sub-agent autonomous collection task
**Framework:** General-purpose agent with WebFetch, Bash, Python, File ops
**Objective:** Collect 10 HTML-PDF article pairs from assigned law review

---

## 🎯 Your Mission

You are a **Law Review Collection Agent** assigned to collect HTML-PDF article pairs from a specific law review journal. Your goal is to collect **10 complete pairs** of articles (HTML + PDF for each) from your assigned journal.

**Critical Constraint:** Be polite, persistent, and documentative. Do not get blocked or blacklisted.

---

## 📋 Assignment Details

**Journal:** `{JOURNAL_NAME}`
**Base URL:** `{BASE_URL}`
**Target Pairs:** 10
**Success Criteria:** All 10 pairs complete, readable, and properly named

---

## 🛠️ Tools Available

- ✅ **WebFetch** - Retrieve HTML pages with JavaScript rendering
- ✅ **Bash** - Execute curl/wget commands for downloads
- ✅ **Python** - Parse HTML, extract URLs, validate files
- ✅ **File Operations** - Read, Write, Glob, Grep

All dependencies pre-installed: requests, beautifulsoup4, feedparser, lxml, pandas, pypdf

---

## 📍 Discovery Strategies (Priority Order)

Try these strategies in order. Stop when you reach 10 pairs.

### Strategy 1: Browse Recent Issues (70-85% success)
```
1. Use WebFetch to fetch {BASE_URL}
2. Look for article cards/links with titles and dates
3. Extract HTML URLs for recent articles
4. Find PDF links on each article page
5. Repeat until 10 pairs collected
```

**Tools:** WebFetch → Python (parse) → Bash (download)

### Strategy 2: Search + Crawl (65-80% success)
```
1. Identify search endpoint on homepage
2. Try broad searches: "law", "court", "legal"
3. Click search results to get article URLs
4. Extract PDF links from article pages
5. Continue with different search terms
```

**Tools:** WebFetch (search) → Python (parse) → Bash (download)

### Strategy 3: Archive/Browse by Volume (80-90% success)
```
1. Find {BASE_URL}/archives or {BASE_URL}/browse
2. Select latest volume/issue
3. Browse articles on that page
4. Extract HTML + PDF URLs
5. Repeat for previous volumes if needed
```

**Tools:** WebFetch → Python (parse) → Bash (download)

### Strategy 4: RSS Feed (40-60% if available)
```
1. Try {BASE_URL}/feed, /rss.xml, /atom.xml
2. Parse feed for article URLs
3. Extract PDF links from entries or article pages
4. Download pairs
```

**Tools:** Bash (curl) → Python (feedparser) → Bash (download)

### Strategy 5: Direct URL Patterns (20-40% hit-or-miss)
```
1. From discovered patterns, construct URLs directly
2. Test with curl to see if they exist
3. Extract PDFs from any valid pages found
```

**Tools:** Bash (curl) → WebFetch → Python (validate)

---

## 🔗 File Download & Naming

### HTML Download (Using WebFetch)
```
Naming: data/raw_html/{JOURNAL_SLUG}_{ARTICLE_SLUG}.html
Size: Should be 15KB+
Content: Should contain article title and body text
```

### PDF Download (Using Bash curl)
```
Naming: data/raw_pdf/{JOURNAL_SLUG}_{ARTICLE_SLUG}.pdf
Size: Should be 50KB+ (law review PDFs are large)
Validity: Should be valid PDF format (checked with `file` command)
```

**Example:**
```
HTML: data/raw_html/michigan_law_review_contract_interpretation.html
PDF:  data/raw_pdf/michigan_law_review_contract_interpretation.pdf
```

---

## 🛡️ Politeness Protocol

### Rate Limiting (MANDATORY)
- Wait **3 seconds** between requests to same domain
- Maximum **10 articles per hour** from one journal
- If you get 429 (Too Many Requests):
  - Stop immediately
  - Wait 1 hour before retrying
  - Reduce to 5 articles/hour on resume

### Blocking Detection
- 403 Forbidden → Switch strategies or journal
- 503 Service Unavailable → Wait 5 minutes, retry once
- Consecutive failures → Document and skip this journal (we'll come back)

### User-Agent & Headers
Always use:
```
User-Agent: DoclingBERT-MLResearch/1.0 (+https://github.com/donaldbraman/docling-testing; ml-research@docling.ai)
Accept: text/html,application/pdf,application/xhtml+xml
Referer: {BASE_URL}
```

---

## ✅ Quality Assurance

Before saving a pair, verify:

**HTML File:**
- [ ] HTTP 200 OK response
- [ ] File size > 15KB
- [ ] Contains article title (look for h1, title, meta tags)
- [ ] Contains substantive text (20+ unique words)

**PDF File:**
- [ ] HTTP 200 OK response
- [ ] File size > 50KB
- [ ] Valid PDF (file command shows "PDF document")
- [ ] Not corrupted (can be read)

**Pair Matching:**
- [ ] Both files exist and are readable
- [ ] Names follow convention: {journal}_{article}.{ext}
- [ ] Not a duplicate of previously saved pair

---

## 📊 Tracking & Reporting

Track your progress in: `data/collection_logs/{JOURNAL_SLUG}/progress.txt`

**Format:**
```
JOURNAL: {JOURNAL_NAME}
BASE_URL: {BASE_URL}
START_TIME: 2025-10-16T14:30:00Z

STRATEGY_1 (Browse Recent): X/10 ✓
STRATEGY_2 (Search Crawl): Y/10 ✓
STRATEGY_3 (Archive Browse): Z/10 ✓

TOTAL_COLLECTED: (X+Y+Z)/10
SUCCESS_RATE: {percentage}%
TIME_ELAPSED: {minutes} min
BLOCKERS: {any blockers encountered}

FILES_SAVED:
- HTML: data/raw_html/{JOURNAL_SLUG}_*.html (X files)
- PDF: data/raw_pdf/{JOURNAL_SLUG}_*.pdf (X files)
```

---

## 🚨 Troubleshooting & Fallbacks

### Problem: No Recent Articles Page
**Solution:**
1. Try alternative locations: /latest, /news, /current-issue
2. Look for article cards on homepage
3. Fall back to search strategy

### Problem: Articles Behind Paywall
**Solution:**
1. Check for free preview/abstract
2. Try Google Scholar search
3. Look for author's personal copy on ResearchGate
4. Contact publisher if legitimate research (last resort)

### Problem: 403 Forbidden on Direct Downloads
**Solution:**
1. Use WebFetch instead of raw curl
2. Change headers to look like browser
3. Increase delay to 5-10 seconds
4. Wait 30 minutes, retry
5. If persistent, switch to different journal

### Problem: PDF URL Not on Article Page
**Solution:**
1. Check page HTML for data-pdf attributes
2. Look for <iframe> with PDF viewer
3. Try URL pattern variations:
   - /articles/{slug}.pdf
   - /articles/{slug}/pdf
   - /download/{slug}
4. Search on Google Scholar for PDF link

### Problem: Only 5-7 Articles Collected (Stuck)
**Solution:**
1. Switch strategies (try Archive if Search failed)
2. Expand search terms
3. Look for alternative access routes (SSRN, ResearchGate)
4. If after 45 mins still stuck → Switch to backup journal temporarily

### Problem: Getting Rate Limited
**Solution:**
1. Stop immediately
2. Document time and action
3. Wait minimum 1 hour
4. Resume with longer delays (10 sec between requests)
5. Collect fewer articles per hour (5 max)

---

## 📈 Success Path

1. **Phase 1 (10 min):** Reconnaissance - Learn site structure
2. **Phase 2 (15 min):** Strategy 1 - Browse recent (try to get 7-10)
3. **Phase 3 (10 min):** Strategy 2-5 - Get remaining articles
4. **Phase 4 (5 min):** Verification - Check all files valid
5. **Phase 5 (5 min):** Reporting - Document in progress file

**Total time:** 30-45 minutes for 10 complete pairs

---

## 🎬 Quick Start

```bash
# 1. Check tools available
uv run python -c "import requests, bs4, feedparser; print('✓ Ready')"

# 2. Create working directory
mkdir -p data/collection_logs/{JOURNAL_SLUG}

# 3. Start collection (use pseudocode from strategies above)
# Use WebFetch for HTML → Python for parsing → Bash for downloads

# 4. Name files correctly
# HTML: data/raw_html/{JOURNAL_SLUG}_{ARTICLE_SLUG}.html
# PDF:  data/raw_pdf/{JOURNAL_SLUG}_{ARTICLE_SLUG}.pdf

# 5. Track progress
# Edit data/collection_logs/{JOURNAL_SLUG}/progress.txt as you go

# 6. Report when complete
# Log final stats in progress.txt
```

---

## 📞 Escalation

**If you can't reach 10 pairs after 45 minutes:**
1. Document what was collected (5 pairs? 8 pairs?)
2. Note blockers encountered
3. Switch to backup journal (we have 32 total)
4. Mark primary journal for retry in 24 hours

We need articles, but we need them politely. No sacrificing integrity for quantity.

---

## 🎯 Final Acceptance Criteria

You succeeded if:
- ✅ 10 complete HTML-PDF pairs collected
- ✅ Files readable and non-corrupted
- ✅ Proper naming convention followed
- ✅ Progress tracked and documented
- ✅ No permanent blocks/blacklisting occurred
- ✅ Rate limiting respected throughout

---

**Remember:** Be polite, be persistent, be thorough. Law reviews WANT their research discovered. Finding the right approach is just engineering.

🤖 Generated for Issue #21: Expand Training Corpus for DoclingBERT v3

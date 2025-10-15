# HTML-PDF Pairs Collection Report - Georgetown & Texas Law Reviews

**Collection Date:** October 14, 2025
**Target:** 10 HTML-PDF pairs from each journal (20 total)
**Status:** COMPLETED - 20 pairs collected successfully

---

## Executive Summary

Successfully collected 20 HTML-PDF article pairs from Georgetown Law Journal and Texas Law Review, meeting the target of 10 pairs from each journal. All articles are recent publications from 2024-2025.

### Collection Statistics

| Journal | Target | Collected | Success Rate |
|---------|--------|-----------|--------------|
| Georgetown Law Journal | 10 | 10 | 100% |
| Texas Law Review | 10 | 10 | 100% |
| **TOTAL** | **20** | **20** | **100%** |

---

## Georgetown Law Journal (10 pairs)

**Working Homepage:** https://www.law.georgetown.edu/georgetown-law-journal/
**Article Archive:** https://www.law.georgetown.edu/georgetown-law-journal/in-print/

### Method Used
Georgetown Law Journal provides FREE direct access to both HTML article pages and PDF downloads through their official website. PDFs are hosted at `law.georgetown.edu/georgetown-law-journal/wp-content/uploads/`.

### Articles Collected

1. **The New Sexual Deviancy** - Jordan Blair Woods (Vol. 113, Issue 5, May 2025)
2. **A Faster Way to Yes: Re-Balancing American Asylum Procedures** - Michael Kagan (Vol. 113, Issue 5, May 2025)
3. **The Sheriff's Constitution** - Farhang Heydari (Vol. 113, Issue 5, May 2025)
4. **Renters' Tax Credits** - Michelle D. Layser (Vol. 113, Issue 5, May 2025)
5. **Selective Enforcement** - Kristelia García (Vol. 113, Issue 5, May 2025)
6. **Afrofuturism and the Law: A Manifesto** - I. Bennett Capers (Vol. 112, Issue 6, June 2024)
7. **Taxing the Metaverse** - Young Ran (Christine) Kim (Vol. 112, Issue 4, April 2024)
8. **An Information Commission** - Margaret B. Kwoka (Vol. 112, Issue 4, April 2024)
9. **The Bias Presumption** - Dave Hall & Brad Areheart (Vol. 112, Issue 4, April 2024)
10. **Data as Likeness** - Zahra Takhshid (Vol. 112, Issue 5, May 2024)

---

## Texas Law Review (10 pairs)

**Working Homepage:** https://texaslawreview.org/
**Article Archive:** https://texaslawreview.org/publication_type/article/

### Method Used
Texas Law Review provides FREE access to both HTML article pages and PDF downloads. Article HTML pages are at `texaslawreview.org/[article-slug]/` and PDFs are hosted at `texaslawreview.org/wp-content/uploads/` with `.Printer.pdf` or `.printer.pdf` naming convention.

### Articles Collected

1. **The Beleaguered Sovereign: Judicial Restraints on Public Enforcement** - Helen Hershkoff & Luke P. Norris (Vol. 103, 2025)
2. **A Law and Political Economy of Intellectual Property** - Oren Bracha & Talha Syed (Vol. 103, 2025)
3. **Corporate Democracy and the Intermediary Voting Dilemma** - Jill Fisch & Jeff Schwartz (Vol. 103, 2024)
4. **Big Data Searches and the Future of Criminal Procedure** - Mary D. Fan (Vol. 103, 2024)
5. **The Constitutional Case Against Exclusionary Zoning** - Joshua Braver & Ilya Somin (Vol. 103, 2024)
6. **Selective Originalism and Judicial Role Morality** - Richard H. Fallon, Jr. (Vol. 103, 2024)
7. **Judicial Review of Unconventional Enforcement Regimes** - James E. Pfander (Vol. 103, 2024)
8. **Second Amendment Exceptionalism: Public Expression and Public Carry** - Timothy Zick (Vol. 103, 2024)
9. **Workarounds in American Public Law** - Daniel A. Farber, Jonathan S. Gould & Matthew C. Stephenson (Vol. 103, 2025)
10. **Video Analytics and Fourth Amendment Vision** - Andrew Guthrie Ferguson (Vol. 103, 2025)

---

## Files Location

All files have been saved to:
- **HTML files:** `/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_html/`
- **PDF files:** `/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_pdf/`

### Naming Convention
- Georgetown: `georgetown_[author_lastname]_[topic_keywords].[html/pdf]`
- Texas: `texas_[author_lastname]_[topic_keywords].[html/pdf]`

---

## Key Findings & Methods

### What Worked

#### Georgetown Law Journal
- Direct free access to both HTML and PDF versions
- Consistent URL structure: `/in-print/volume-XXX/volume-XXX-issue-X-month-year/article-title/`
- PDF URLs follow pattern: `/wp-content/uploads/sites/26/YYYY/MM/Author_Title.pdf`
- No authentication required
- Volumes 106+ (2017-present) available online

#### Texas Law Review
- Direct free access to both HTML and PDF versions
- HTML article URL pattern: `texaslawreview.org/article-slug/`
- PDF URL pattern: `texaslawreview.org/wp-content/uploads/YYYY/MM/Author.Printer.pdf`
- No authentication required
- PDFs use ".Printer.pdf" or ".printer.pdf" suffix

### Challenges Encountered

1. **PDF URL Discovery**
   - Georgetown: Some PDF URLs required exact filename matching (case-sensitive, hyphenation variations)
   - Texas: PDF URLs not directly linked from article pages, required searching wp-content directory
   - Solution: Used WebFetch on HTML pages and web search for PDF URLs

2. **404 Errors**
   - 3 Georgetown PDFs initially had incorrect filenames (resolved by finding correct URLs)
   - 2 Texas PDFs had incorrect URLs (substituted with alternative articles)
   - Solution: Verified PDF URLs through web search before downloading

### Best Practices Used

1. **Respectful scraping:** 4-second delays between requests
2. **User agent:** Standard browser user agent to avoid blocks
3. **Error handling:** Retry logic and alternative article selection
4. **Documentation:** Detailed JSON metadata for each collection
5. **Verification:** Confirmed file downloads before marking as complete

---

## Access Methods Summary

### Georgetown Law Journal
- **Homepage:** https://www.law.georgetown.edu/georgetown-law-journal/
- **Access:** Open access, no subscription required
- **Archive coverage:** Volumes 106+ (2017-present)
- **Format:** HTML pages + downloadable PDFs
- **Alternative access:** HeinOnline (subscription required for older volumes)

### Texas Law Review
- **Homepage:** https://texaslawreview.org/
- **Access:** Open access, no subscription required
- **Archive coverage:** Recent volumes freely available
- **Format:** HTML pages + downloadable PDFs
- **Alternative access:** HeinOnline (subscription required for comprehensive archive)

---

## Scripts Created

1. **collect_georgetown_articles.py** - Automated Georgetown collection
2. **collect_texas_articles.py** - Automated Texas collection

Both scripts include:
- Automatic downloading with delays
- Error handling and retry logic
- JSON metadata output
- Progress reporting
- Success/failure tracking

---

**Collection completed successfully on October 14, 2025**

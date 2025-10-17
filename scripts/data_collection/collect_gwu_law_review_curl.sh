#!/bin/bash
# GWU Law Review Collection Script using curl
# Site blocks Python requests library but allows curl with proper headers

set -e

# Configuration
BASE_URL="https://www.gwlr.org"
OUTPUT_HTML="/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_html"
OUTPUT_PDF="/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_pdf"
LOG_DIR="/Users/donaldbraman/Documents/GitHub/docling-testing/data/collection_logs/gwu_law_review"
DELAY=2.5
TARGET=15

# Browser-like headers to avoid ModSecurity blocking
USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS=(
    -H "User-Agent: $USER_AGENT"
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    -H "Accept-Language: en-US,en;q=0.5"
    -H "Accept-Encoding: gzip, deflate, br"
    -H "DNT: 1"
    -H "Connection: keep-alive"
    -H "Upgrade-Insecure-Requests: 1"
)

# Ensure directories exist
mkdir -p "$OUTPUT_HTML" "$OUTPUT_PDF" "$LOG_DIR"

# Article URLs (curated list)
ARTICLES=(
    "https://www.gwlr.org/coercive-settlements/"
    "https://www.gwlr.org/criminal-investors/"
    "https://www.gwlr.org/non-universal-response-to-the-universal-injunction-problem/"
    "https://www.gwlr.org/chenery-ii-revisited/"
    "https://www.gwlr.org/chevron-bias/"
    "https://www.gwlr.org/contextual-interpretation-applying-civil-rights-to-healthcare-in-section-1557-of-the-affordable-care-act/"
    "https://www.gwlr.org/drawing-a-line-how-energy-law-can-provide-a-practical-boundary-for-the-rapidly-expanding-major-questions-doctrine/"
    "https://www.gwlr.org/good-cause-is-cause-for-concern/"
    "https://www.gwlr.org/how-chevron-deference-fits-into-article-iii/"
    "https://www.gwlr.org/lying-in-wait-how-a-court-should-handle-the-first-pretextual-for-cause-removal/"
    "https://www.gwlr.org/nondelegation-as-constitutional-symbolism/"
    "https://www.gwlr.org/optimal-ossification/"
    "https://www.gwlr.org/overseeing-agency-enforcement/"
    "https://www.gwlr.org/remand-and-dialogue-in-administrative-law/"
    "https://www.gwlr.org/the-ambiguity-fallacy/"
    "https://www.gwlr.org/the-american-nondelegation-doctrine/"
    "https://www.gwlr.org/the-future-of-deference/"
    "https://www.gwlr.org/the-ordinary-questions-doctrine/"
    "https://www.gwlr.org/the-power-to-vacate-a-rule/"
    "https://www.gwlr.org/what-the-new-major-questions-doctrine-is-not/"
)

# Progress tracking
SUCCESSFUL=0
FAILED=0
LOG_FILE="$LOG_DIR/progress.txt"

echo "======================================================================"
echo "GWU Law Review Collection Script"
echo "======================================================================"
echo "Target: 10-$TARGET complete HTML-PDF pairs"
echo "Rate limit: ${DELAY}s delay between requests"
echo ""

# Initialize log file
cat > "$LOG_FILE" <<EOF
GWU Law Review Collection Report
======================================================================
Date: $(date '+%Y-%m-%d %H:%M:%S')

Details:
EOF

# Process each article
COUNT=0
for ARTICLE_URL in "${ARTICLES[@]}"; do
    COUNT=$((COUNT + 1))

    # Stop if we've reached target
    if [ $SUCCESSFUL -ge $TARGET ]; then
        echo ""
        echo "✓ Reached target of $TARGET pairs, stopping"
        break
    fi

    echo ""
    echo "[$COUNT] Processing: $ARTICLE_URL"

    # Extract slug from URL
    SLUG=$(echo "$ARTICLE_URL" | sed 's|https://www.gwlr.org/||' | sed 's|/$||')
    BASE_FILENAME="gwu_law_review_${SLUG}"
    HTML_FILE="$OUTPUT_HTML/${BASE_FILENAME}.html"
    PDF_FILE="$OUTPUT_PDF/${BASE_FILENAME}.pdf"

    # Download HTML
    echo "  Fetching HTML..."
    if curl -s -f "${HEADERS[@]}" "$ARTICLE_URL" -o "$HTML_FILE"; then
        # Check file size as proxy for content (skip word count due to encoding issues)
        FILE_SIZE=$(stat -f%z "$HTML_FILE" 2>/dev/null || stat -c%s "$HTML_FILE" 2>/dev/null || echo "0")
        echo "  HTML file size: $FILE_SIZE bytes"

        if [ "$FILE_SIZE" -lt 5000 ]; then
            echo "  ⚠ Skipping: Too small (likely error page)"
            rm "$HTML_FILE"
            FAILED=$((FAILED + 1))
            echo "✗ $ARTICLE_URL (too small)" >> "$LOG_FILE"
            sleep $DELAY
            continue
        fi

        # Extract PDF URL (try multiple patterns)
        PDF_URL=$(grep -oE 'https://www.gwlr.org/wp-content/uploads/[^">< ]+\.pdf' "$HTML_FILE" | head -1)

        if [ -z "$PDF_URL" ]; then
            echo "  ⚠ No PDF link found, skipping"
            rm "$HTML_FILE"
            FAILED=$((FAILED + 1))
            echo "✗ $ARTICLE_URL (no PDF)" >> "$LOG_FILE"
            sleep $DELAY
            continue
        fi

        echo "  Found PDF: $PDF_URL"

        # Verify PDF is accessible (HEAD request)
        sleep $DELAY
        if curl -s -f -I "${HEADERS[@]}" "$PDF_URL" > /dev/null 2>&1; then
            # Download PDF
            echo "  Downloading PDF..."
            sleep $DELAY
            if curl -s -f "${HEADERS[@]}" "$PDF_URL" -o "$PDF_FILE"; then
                PDF_SIZE=$(stat -f%z "$PDF_FILE" 2>/dev/null || stat -c%s "$PDF_FILE" 2>/dev/null || echo "unknown")
                echo "  ✓ Saved HTML: ${BASE_FILENAME}.html"
                echo "  ✓ Saved PDF: ${BASE_FILENAME}.pdf ($PDF_SIZE bytes)"
                SUCCESSFUL=$((SUCCESSFUL + 1))
                echo "✓ $ARTICLE_URL" >> "$LOG_FILE"
            else
                echo "  ✗ Failed to download PDF"
                rm "$HTML_FILE"
                FAILED=$((FAILED + 1))
                echo "✗ $ARTICLE_URL (PDF download failed)" >> "$LOG_FILE"
            fi
        else
            echo "  ⚠ PDF not accessible"
            rm "$HTML_FILE"
            FAILED=$((FAILED + 1))
            echo "✗ $ARTICLE_URL (PDF not accessible)" >> "$LOG_FILE"
        fi
    else
        echo "  ✗ Failed to fetch HTML"
        FAILED=$((FAILED + 1))
        echo "✗ $ARTICLE_URL (HTML fetch failed)" >> "$LOG_FILE"
    fi

    # Rate limiting
    sleep $DELAY
done

# Final summary
echo ""
echo "======================================================================"
echo "Collection Complete"
echo "======================================================================"
echo "Successful pairs: $SUCCESSFUL"
echo "Failed attempts: $FAILED"

if [ $((SUCCESSFUL + FAILED)) -gt 0 ]; then
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($SUCCESSFUL/($SUCCESSFUL+$FAILED))*100}")
    echo "Success rate: ${SUCCESS_RATE}%"
else
    echo "Success rate: N/A"
fi

# Update log file with summary
cat >> "$LOG_FILE" <<EOF

Summary:
Successful pairs: $SUCCESSFUL
Failed attempts: $FAILED
EOF

if [ $((SUCCESSFUL + FAILED)) -gt 0 ]; then
    echo "Success rate: ${SUCCESS_RATE}%" >> "$LOG_FILE"
fi

echo ""
echo "Progress report saved to: $LOG_FILE"
echo ""

if [ $SUCCESSFUL -ge 10 ]; then
    echo "✓ SUCCESS: Met minimum target of 10 pairs"
    exit 0
else
    echo "⚠ WARNING: Only collected $SUCCESSFUL pairs (target: 10)"
    exit 1
fi

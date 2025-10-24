# Classification Correction Experiments

**Goal:** Find the best strategy for correcting Docling text classifications using limited HTML ground truth (61 items for 4484 lines).

**Problem:** Current locality-aware matching produces ~80% body-text, ~20% footnotes, but paper should be ~40% body / ~60% footnotes.

---

## Experimental Framework

### Overall Evaluation Criterion (OEC)

**Primary Metric: Balanced Classification Rate**
- Target: ≥20% body-text AND ≥20% footnote-text (minimum viable balance)
- Ideal: ~40% body-text, ~60% footnote-text (matches paper structure)

### Guardrail Metrics

Track these for debugging and validation:

1. **HTML Match Utilization**
   - How many of 24 body_html items matched?
   - How many of 37 footnote_html items matched?
   - Are we using the HTML ground truth effectively?

2. **Classification Flip Rate**
   - How many lines changed from Docling classification?
   - Which direction: TEXT→footnote or FOOTNOTE→body?

3. **Spatial Distribution**
   - Where on pages are footnotes/body-text classified?
   - Do footnotes cluster at page bottoms as expected?

4. **Match Confidence Distribution**
   - What's the similarity score distribution for HTML matches?
   - Are we matching confidently or guessing?

5. **Per-Page Balance**
   - Do pages with many footnotes show correct distribution?
   - Or are all pages uniformly ~80/20?

### Testing Methodology

**Simple Controlled Experiments:**
1. Test one hypothesis at a time (single variable)
2. Compare against baseline (current locality-aware algorithm)
3. Use McNemar's test for statistical significance (good for limited data)
4. Track all guardrail metrics for each experiment

**Data Split:**
- Use harvard_law_review_unwarranted_warrants (89 pages, 4484 lines)
- No train/test split needed - we're evaluating correction strategies, not training
- Ground truth: 24 body_html + 37 footnote_html items

---

## Baseline (Control)

**Current Algorithm:**
- Locality-aware fuzzy matching
- Proximity bonus: `0.1 / (1.0 + distance * 0.1)` (max 0.1)
- Fallback to Docling classification when no HTML match
- Threshold: 0.75 similarity

**Baseline Metrics to Measure:**
```python
{
    'body_text_pct': ?,
    'footnote_text_pct': ?,
    'html_body_utilization': ?/24,
    'html_footnote_utilization': ?/37,
    'docling_override_count': ?,
    'avg_match_confidence': ?,
}
```

---

## Hypothesis 1: High-Confidence HTML Override

**Rationale:**
- We have limited HTML ground truth (61 items vs 4484 lines)
- HTML should **correct errors**, not classify everything
- Docling already classified all text - trust it unless we're very confident

**Strategy:**
- Only use HTML match if similarity ≥ 0.90 (very high confidence)
- Otherwise, keep Docling's original classification
- No locality tracking needed (not matching sequentially)

**Implementation:**
```python
def match_with_high_confidence_override(line, body_html, footnote_html, docling_label):
    # Find best match in both lists (no locality tracking)
    best_match = find_best_match_anywhere(line, body_html, footnote_html)

    if best_match.similarity >= 0.90:
        return best_match.corrected_label  # Override with HTML
    else:
        return docling_label  # Trust Docling
```

**Prediction:**
- Will use fewer HTML matches (only high-confidence)
- Should preserve Docling's footnote classifications better
- May increase footnote percentage

**Metrics to Track:**
- Classification distribution (target: ≥20% each)
- HTML utilization (expect lower than baseline)
- Where do overrides happen? (page locations)

---

## Hypothesis 2: Spatial Position Prior

**Rationale:**
- Footnotes have strong spatial structure (bottom of pages)
- Page position is independent signal (orthogonal to text similarity)
- Can break ties when similarity scores are close

**Strategy:**
- Calculate line's Y position on page (normalized 0-1)
- If line is in bottom 25% of page, boost footnote scores
- Combine with current locality-aware matching

**Implementation:**
```python
def match_with_spatial_prior(line, body_html, footnote_html, page_height):
    # Get position on page
    line_position = line.bbox[1] / page_height  # 0 = top, 1 = bottom

    # Find matches as usual
    best_body_match = find_best_body_match(...)
    best_footnote_match = find_best_footnote_match(...)

    # Apply spatial boost
    if line_position > 0.75:  # Bottom 25% of page
        best_footnote_match.score += 0.05  # Small boost

    return best_match(best_body_match, best_footnote_match)
```

**Prediction:**
- Footnotes at page bottoms more likely to be classified correctly
- Should see spatial clustering in metrics
- May increase footnote percentage moderately

**Metrics to Track:**
- Classification distribution by page region (top/middle/bottom)
- Do bottom-page footnotes get classified correctly?
- Does spatial boost override high-similarity body matches incorrectly?

---

## Hypothesis 3: Sequential Consistency Check

**Rationale:**
- Footnotes tend to cluster (multiple consecutive footnote lines)
- Body text tends to cluster (paragraphs)
- If neighbors agree on label, current line probably same label
- Addresses cascading bias problem (missed footnote hurts future footnotes)

**Strategy:**
- After initial classification, do second pass
- For each line, check 2 neighbors before and after
- If 3+ neighbors have same label AND current line's similarity is < 0.85, flip to neighbor label

**Implementation:**
```python
def match_with_consistency_check(lines):
    # First pass: classify as usual
    initial_labels = [classify_line(line) for line in lines]

    # Second pass: check consistency
    final_labels = []
    for i, line in enumerate(lines):
        neighbors = initial_labels[max(0, i-2):i+3]  # 2 before + self + 2 after

        # Count neighbor labels
        neighbor_votes = Counter(neighbors)
        majority_label, count = neighbor_votes.most_common(1)[0]

        # If strong consensus and we're not confident, flip
        if count >= 3 and line.match_confidence < 0.85:
            final_labels.append(majority_label)
        else:
            final_labels.append(initial_labels[i])

    return final_labels
```

**Prediction:**
- Should create more coherent regions of footnotes/body
- May help recover from cascading bias
- Could incorrectly flip isolated footnotes in body text

**Metrics to Track:**
- How many lines flipped in consistency pass?
- Do footnote regions become more coherent?
- Are isolated correct classifications getting incorrectly flipped?

---

## Hypothesis 4: Bayesian Sequential Lookahead

**Rationale:**
- After matching line N to HTML[i], look at what comes NEXT in HTML
- If next PDF line (N+1) matches HTML[i+1], this is evidence we're in the right category
- Uses HTML sequence as template for PDF sequence alignment
- Bayesian prior: P(category | previous match) × P(next line matches next HTML)

**Strategy:**
- Track previous HTML match for each category (last_body_idx, last_footnote_idx)
- For current line, calculate:
  - Standard similarity to all HTML items
  - **Lookahead bonus:** Does next PDF line match HTML[previous_idx+1]?
- Combine: `score = current_similarity + lookahead_match_score * 0.15`

**Implementation:**
```python
def match_with_sequential_lookahead(lines, body_html, footnote_html):
    results = []
    last_body_match_idx = None
    last_footnote_match_idx = None

    for i, current_line in enumerate(lines):
        # Standard similarity matching
        body_scores = [similarity(current_line, h) for h in body_html]
        footnote_scores = [similarity(current_line, h) for h in footnote_html]

        # Lookahead bonus: check if NEXT pdf line matches NEXT html
        if i < len(lines) - 1:
            next_line = lines[i + 1]

            # If we previously matched body_html[j], check body_html[j+1]
            if last_body_match_idx is not None and last_body_match_idx + 1 < len(body_html):
                next_body_sim = similarity(next_line, body_html[last_body_match_idx + 1])
                if next_body_sim > 0.75:  # High confidence lookahead
                    body_scores[last_body_match_idx + 1] += 0.15  # Boost

            # Same for footnotes
            if last_footnote_match_idx is not None and last_footnote_match_idx + 1 < len(footnote_html):
                next_footnote_sim = similarity(next_line, footnote_html[last_footnote_match_idx + 1])
                if next_footnote_sim > 0.75:
                    footnote_scores[last_footnote_match_idx + 1] += 0.15

        # Select best match (with lookahead boost applied)
        best_body_idx = argmax(body_scores)
        best_footnote_idx = argmax(footnote_scores)

        if body_scores[best_body_idx] > footnote_scores[best_footnote_idx]:
            results.append('body-text')
            last_body_match_idx = best_body_idx
        else:
            results.append('footnote-text')
            last_footnote_match_idx = best_footnote_idx

    return results
```

**Why This Works:**
1. **Captures sequential structure** - HTML sequence is template for PDF sequence
2. **Self-correcting** - Wrong match at line N corrected when N+1 doesn't match expected next
3. **Breaks cascading bias** - Looks forward (what's next?) not backward (where were we?)
4. **Chain of evidence** - Each match informs next classification
5. **Orthogonal signal** - Lookahead evidence independent of current-line similarity

**Why This Might Fail:**
1. **HTML/PDF ordering mismatch** - If HTML not in document reading order, lookahead predicts wrong
2. **Sparse coverage** - Only 61 HTML items for 4484 lines, most lines have no previous match
3. **Document structure** - Page breaks, columns, figures disrupt sequential flow
4. **Boundary errors** - At transitions (body→footnote), lookahead predicts wrong category
5. **Error propagation** - Wrong match reinforced by lookahead ("stay in this category")
6. **Computational cost** - Must match both current AND next line for all candidates

**Critical Assumption to Validate:**
- Are HTML body_html and footnote_html in document reading order?
- Or are they grouped differently (e.g., all footnotes at end)?
- This determines if sequential lookahead is viable

**Prediction:**
- If HTML is in document order: Significant improvement, high coherence
- If HTML is reordered: Catastrophic failure, random predictions
- Need to inspect HTML ground truth ordering before implementing

**Metrics to Track:**
- Classification distribution (target ≥20% each)
- Chain length (how many consecutive matches using lookahead?)
- Lookahead hit rate (when we predict next, are we right?)
- Boundary error rate (failures at category transitions)

---

## Experimental Procedure

### Step 1: Measure Baseline
```bash
python scripts/evaluation/measure_classification_metrics.py --algorithm baseline
```

Output:
```json
{
    "algorithm": "baseline",
    "body_text_pct": 78.2,
    "footnote_text_pct": 21.8,
    "html_body_utilization": 18/24,
    "html_footnote_utilization": 12/37,
    "docling_overrides": 342,
    "avg_match_confidence": 0.81,
    "spatial_distribution": {...},
    "per_page_balance": {...}
}
```

### Step 2: Validate H4 Assumption (Critical!)
```bash
# Check if HTML is in document reading order
python scripts/evaluation/inspect_html_ordering.py

# Output: Are body_html items sequential? Are footnote_html items sequential?
# If not, H4 will fail - document before implementing
```

### Step 3: Test Each Hypothesis
```bash
# Hypothesis 1
python scripts/evaluation/measure_classification_metrics.py --algorithm h1_high_confidence

# Hypothesis 2
python scripts/evaluation/measure_classification_metrics.py --algorithm h2_spatial_prior

# Hypothesis 3
python scripts/evaluation/measure_classification_metrics.py --algorithm h3_consistency_check

# Hypothesis 4 (only if HTML ordering validated)
python scripts/evaluation/measure_classification_metrics.py --algorithm h4_sequential_lookahead
```

### Step 4: Compare Results

**Simple Comparison Table:**
| Algorithm | Body % | Footnote % | Meets Target? | HTML Used | Overrides |
|-----------|--------|------------|---------------|-----------|-----------|
| Baseline  | ?      | ?          | ?             | ?         | ?         |
| H1: High-Conf | ?   | ?          | ?             | ?         | ?         |
| H2: Spatial | ?     | ?          | ?             | ?         | ?         |
| H3: Consistency | ? | ?          | ?             | ?         | ?         |
| H4: Lookahead | ?   | ?          | ?             | ?         | ?         |

**Statistical Test:**
- Use McNemar's test to compare each hypothesis vs baseline
- Null hypothesis: No significant difference in classification
- p-value < 0.05 → statistically significant improvement

### Step 5: Visual Validation

Generate overlay PDFs for each algorithm:
```bash
python scripts/evaluation/generate_overlay_pdfs.py --algorithm h1_high_confidence
```

Manually inspect pages 3, 5, 10 to verify:
- Are footnote regions properly classified?
- Do classifications look coherent?
- Any obvious errors?

---

## Implementation Plan

### New Files to Create

1. **`scripts/evaluation/classification_metrics.py`**
   - Functions to calculate all metrics
   - Classification distribution
   - HTML utilization
   - Spatial analysis

2. **`scripts/evaluation/correction_strategies.py`**
   - Implement all 3 hypotheses as separate functions
   - Baseline function (current algorithm)
   - Each strategy is self-contained and testable

3. **`scripts/evaluation/run_experiment.py`**
   - Main experimental harness
   - Run all algorithms on same data
   - Generate comparison table
   - Save detailed metrics JSON

4. **`scripts/evaluation/visualize_results.py`**
   - Plot classification distribution by algorithm
   - Plot spatial distribution
   - Generate comparison charts

### Modifications to Existing Files

- **`generate_overlay_pdfs.py`**: Add `--algorithm` parameter to switch strategies
- **`fuzzy_matcher.py`**: Extract strategies into separate functions

---

## Success Criteria

**Minimum Viable:**
- ≥20% body-text AND ≥20% footnote-text
- Statistically significant improvement over baseline (p < 0.05)

**Ideal:**
- ~40% body-text, ~60% footnote-text
- High HTML utilization (>80% of ground truth matched)
- Spatial distribution matches expected patterns
- Visual validation shows clean, coherent regions

**If No Hypothesis Succeeds:**
- Document learnings from metrics
- Propose new hypotheses based on guardrail metric insights
- Consider hybrid approaches (combine successful elements)

---

## Next Steps

1. ✅ Design experimental framework (this document)
2. ⏭️ **CRITICAL:** Validate H4 assumption - check if HTML is in document order
3. ⏭️ Implement metrics measurement (`classification_metrics.py`)
4. ⏭️ Measure baseline performance
5. ⏭️ Implement 4 hypothesis strategies
6. ⏭️ Run experiments
7. ⏭️ Analyze results and select best strategy
8. ⏭️ Update PRD with findings

---

**Last Updated:** 2025-10-20
**Status:** Design Complete, Ready for Implementation

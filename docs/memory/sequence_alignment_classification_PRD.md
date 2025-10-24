# PRD: Sequence Alignment for Classification Correction

**Problem:** Current line-by-line fuzzy matching produces incorrect classification distribution (80% body-text, 20% footnotes) due to cascading bias in greedy sequential matching.

**Solution:** Reframe as global optimization problem - partition PDF lines into two sequences that best align with HTML body and footnote templates.

---

## Problem Statement

### Current Approach Issues

**Greedy Line-by-Line Matching:**
- Line 1: Find best match → assign label
- Line 2: Find best match → assign label
- Result: Cascading bias when we miss a footnote

**Why Cascading Bias Occurs:**
1. Miss footnote at line N (classify as body text)
2. Position tracker advances: `current_body_idx = 24`, `current_footnote_idx = 0`
3. Next footnote at line N+1 gets huge distance penalty from footnote tracker
4. Body text tracker is "close" so wins again
5. Snowball effect: Each missed footnote makes future footnotes harder to match

**Observed Results:**
- 80% body-text, 20% footnotes
- Expected: 40% body-text, 60% footnotes
- HTML utilization: Low (only ~30 of 61 items matched)

---

## Solution: Global Sequence Alignment

### Key Insight

Instead of asking "what label for this line?", ask:

> **"How should we partition 4484 PDF lines into two sequences that maximize alignment quality with body_html (24 items) and footnote_html (37 items)?"**

This is a **global optimization** problem:
- Finds best overall partition
- No cascading bias (considers all possibilities)
- Sequence-aware (HTML order matters)
- Self-correcting (sacrifice local match for global optimum)

---

## Three Approaches to Test

### Hypothesis 1: Dynamic Programming - Two-Sequence Alignment

**Algorithm:** 3D DP finding globally optimal partition

**State:** `(pdf_idx, body_idx, footnote_idx)`
- How many PDF lines processed
- How many body_html items consumed
- How many footnote_html items consumed

**Transitions at each PDF line:**
1. Assign to body sequence → match body_html[body_idx], advance body_idx
2. Assign to footnote sequence → match footnote_html[footnote_idx], advance footnote_idx
3. No match → use Docling label, don't advance HTML indices

**Scoring:** Sum of similarity scores for all matched pairs

**Complexity:** O(n × m × k) = O(4484 × 24 × 37) = 4M operations ✅ Tractable

**Expected Outcome:**
- ✅ Globally optimal partition (no local minima)
- ✅ Enforces HTML sequence order
- ✅ No cascading bias
- ✅ Handles sparse HTML coverage
- Target: 40-60% balance, high HTML utilization

---

### Hypothesis 2: Two-Pass Sequence Alignment (Needleman-Wunsch)

**Algorithm:** Standard sequence alignment applied twice

**Pass 1:** Align PDF → body_html
- Use Needleman-Wunsch algorithm
- Extract PDF lines with alignment score > threshold
- Mark as body sequence

**Pass 2:** Align remaining PDF → footnote_html
- Take unmatched PDF lines
- Align to footnote_html
- Extract lines with score > threshold
- Mark as footnote sequence

**Pass 3:** Assign unmatched lines
- Use Docling labels for lines not matched in either pass

**Complexity:** O(n × m) + O(n × k) = O(4484 × 24) + O(4484 × 37) = 270K operations ✅ Fast

**Expected Outcome:**
- ✅ Standard, well-tested algorithms
- ✅ Simpler implementation
- ✅ Natural sequence extraction
- ❓ Not globally optimal (greedy two-pass)
- ❓ Pass order may matter (body first vs footnote first)
- Target: Better than baseline, may not reach 40-60%

---

### Hypothesis 3: Hidden Markov Model (Viterbi)

**Algorithm:** Probabilistic sequence labeling

**Model:**
- **States:** {body-text, footnote-text}
- **Observations:** PDF line text
- **Emissions:** P(PDF line | state) from HTML similarity
- **Transitions:** P(state1 → state2) from spatial position

**Emission Probabilities:**
```python
P(obs | body) = max(similarity(line, h) for h in body_html)
P(obs | footnote) = max(similarity(line, h) for h in footnote_html)
```

**Transition Probabilities:**
```python
# Bottom of page → likely footnote
if page_position > 0.75:
    P(any → footnote) = 0.8
else:
    P(same → same) = 0.9  # State persistence
```

**Inference:** Viterbi algorithm finds most likely state sequence

**Complexity:** O(n × 2) = O(8968) ✅ Very fast

**Expected Outcome:**
- ✅ Probabilistic framework (principled)
- ✅ Incorporates spatial priors
- ✅ Smooth state transitions
- ❓ Requires parameter tuning
- ❓ May overfit to spatial patterns
- Target: Good spatial coherence, unknown balance

---

## Evaluation Framework

### Primary Metric (OEC)

**Balanced Classification Rate:**
- Minimum: ≥20% body-text AND ≥20% footnote-text
- Target: ~40% body-text, ~60% footnote-text

### Guardrail Metrics

1. **HTML Match Utilization**
   - How many body_html items matched? (Target: >20/24)
   - How many footnote_html items matched? (Target: >30/37)

2. **Alignment Quality**
   - Average similarity for matched pairs
   - Distribution of match confidences

3. **Spatial Coherence**
   - Do footnotes cluster at page bottoms?
   - Are body/footnote regions contiguous?

4. **Sequence Preservation**
   - Do matched PDF lines follow HTML order?
   - Number of order violations

### Statistical Significance

- Use McNemar's test comparing each approach to baseline
- p < 0.05 for statistical significance
- Baseline: Current locality-aware fuzzy matching

---

## Implementation Plan

### New Files

1. **`scripts/evaluation/sequence_alignment/`** (new directory)
   - `dp_alignment.py` - Hypothesis 1 implementation
   - `two_pass_alignment.py` - Hypothesis 2 implementation
   - `hmm_alignment.py` - Hypothesis 3 implementation
   - `alignment_metrics.py` - Evaluation metrics
   - `__init__.py` - Package init

2. **`scripts/evaluation/run_alignment_experiment.py`**
   - Main experimental harness
   - Runs all 3 approaches + baseline
   - Generates comparison table
   - Saves detailed metrics JSON

3. **`tests/test_sequence_alignment.py`**
   - Unit tests for each algorithm
   - Validation tests (sequence order preserved, etc.)
   - Integration test with real PDF data

### Modified Files

1. **`scripts/evaluation/generate_overlay_pdfs.py`**
   - Add `--algorithm` parameter
   - Support: baseline, dp, two_pass, hmm
   - Use selected algorithm for classification

2. **`scripts/evaluation/fuzzy_matcher.py`**
   - Keep existing functions for baseline
   - Add imports for new alignment modules

### Data Files

**Input:**
- PDF: `data/v3_data/raw_pdf/harvard_law_review_unwarranted_warrants.pdf`
- Extraction: `results/ocr_pipeline_evaluation/extractions/harvard_law_review_unwarranted_warrants_baseline_extraction.json`
- Ground truth: HTML body/footnote lists

**Output:**
- `results/sequence_alignment/metrics/`
  - `baseline_metrics.json`
  - `dp_metrics.json`
  - `two_pass_metrics.json`
  - `hmm_metrics.json`
  - `comparison_table.csv`
- `results/sequence_alignment/overlay_pdfs/`
  - `*_dp_corrected.pdf`
  - `*_two_pass_corrected.pdf`
  - `*_hmm_corrected.pdf`

---

## Testing Strategy

### Unit Tests

1. **DP Algorithm:**
   - Simple 3-line PDF, 2-item HTML → verify optimal partition
   - Test boundary conditions (empty HTML, single match)
   - Verify DP table correctness

2. **Two-Pass Algorithm:**
   - Test Needleman-Wunsch correctness
   - Verify pass order independence (or document dependence)
   - Test threshold sensitivity

3. **HMM Algorithm:**
   - Test Viterbi correctness
   - Verify emission probability calculation
   - Test transition probability logic

### Integration Tests

1. **Real Data Test:**
   - Run on harvard_law_review (89 pages, 4484 lines)
   - Verify all lines classified
   - Check no crashes with sparse HTML

2. **Metrics Validation:**
   - Verify percentages sum to 100%
   - Check HTML utilization counts correct
   - Validate spatial distribution calculation

3. **Visual Validation:**
   - Generate overlay PDFs
   - Spot-check pages 3, 5, 10
   - Verify coherent regions

---

## Success Criteria

### Minimum Viable

- ✅ At least one algorithm achieves ≥20% body AND ≥20% footnotes
- ✅ Statistically significant improvement over baseline (p < 0.05)
- ✅ All tests pass
- ✅ Visual validation shows coherent regions

### Ideal

- ✅ Best algorithm achieves ~40% body, ~60% footnotes
- ✅ High HTML utilization (>80% of items matched)
- ✅ Spatial coherence (footnotes at page bottoms)
- ✅ Sequence preservation (HTML order maintained)
- ✅ No overlapping boxes in overlay PDFs

### Decision Criteria

**Select best algorithm based on:**
1. Primary metric (classification balance)
2. Statistical significance
3. HTML utilization
4. Implementation simplicity
5. Computational performance

**If multiple succeed:** Choose simplest (likely Two-Pass)

**If none succeed:** Analyze guardrail metrics to understand why, propose hybrid approach

---

## Risks and Mitigations

### Risk 1: HTML Not in Document Order

**Impact:** Sequence alignment assumes HTML order matches PDF reading order

**Mitigation:**
- Before implementing, validate HTML ordering
- If out of order, algorithms may fail
- Fallback: Sort HTML by first match position in PDF

### Risk 2: Sparse HTML Coverage

**Impact:** 61 HTML items for 4484 lines = 1.4% coverage

**Mitigation:**
- All algorithms have "no match" fallback (use Docling)
- DP explicitly models this as transition
- Most lines will still use Docling, we're just fixing errors

### Risk 3: Computational Complexity

**Impact:** DP is O(n×m×k), could be slow

**Mitigation:**
- Pre-calculated: 4M operations = fast on modern CPU
- Can add memoization if needed
- Can prune DP state space (skip unlikely states)

### Risk 4: Parameter Tuning

**Impact:** HMM requires transition probabilities, thresholds, etc.

**Mitigation:**
- Start with reasonable defaults from literature
- Document sensitivity in metrics
- If brittle, mark as less practical despite performance

---

## Timeline

**Estimated:** 1 autonomous dev cycle

1. **Analysis & Setup** (covered by this PRD)
2. **Implementation:** ~2-3 hours
   - DP algorithm: 1 hour
   - Two-pass algorithm: 30 min
   - HMM algorithm: 1 hour
   - Metrics/harness: 30 min
3. **Testing:** ~1 hour
   - Unit tests
   - Integration tests
   - Visual validation
4. **PR & Merge:** 15 min

**Total:** 4-5 hours

---

## Deliverables

1. ✅ Three working alignment algorithms
2. ✅ Comprehensive test suite (all passing)
3. ✅ Experimental results with metrics
4. ✅ Comparison table showing best approach
5. ✅ Overlay PDFs demonstrating improvement
6. ✅ Documentation in code and README
7. ✅ Updated PRD with findings

---

## Follow-Up Work (Out of Scope)

- Apply best algorithm to full evaluation corpus
- Combine successful elements into hybrid approach
- Optimize computational performance if needed
- Extend to multi-document evaluation

---

**Created:** 2025-10-20
**Status:** Ready for Implementation
**Issue:** #[TBD]
**Branch:** feature/issue-[TBD]-sequence-alignment

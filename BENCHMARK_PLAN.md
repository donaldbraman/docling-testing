# Docling Extraction Benchmark Plan

## Objective

Systematically test Docling configurations across multiple law review PDFs to identify optimal settings for footnote detection and body text extraction.

## Test Corpus

**3 Documents** (spanning 60 years of legal publishing):

| Document | Size | Year | Characteristics |
|----------|------|------|-----------------|
| **Nedrud_1964.pdf** | 1.9 MB | 1964 | Oldest, smallest, simpler layout |
| **Green_Roiphe_2020.pdf** | 3.0 MB | 2020 | Newest, modern formatting |
| **Jackson_2014.pdf** | 6.6 MB | 2014 | Largest, complex two-column layout |

## Configurations to Test

**3 Configurations** (9 total runs):

1. **default**
   - `images_scale: 1.0`
   - `model_spec: default`
   - Baseline performance

2. **2x_scale**
   - `images_scale: 2.0`
   - `model_spec: default`
   - Test if higher DPI improves detection

3. **optimized**
   - `images_scale: 2.0`
   - `model_spec: heron-101`
   - `single_column_fallback: True`
   - Full recommended optimizations

## Standardized Metrics

Each run collects:

### Performance
- Processing time (seconds & minutes)
- Pages per minute
- File size

### Label Distribution
- Count per label type (footnote, text, list_item, etc.)
- Total items detected

### Extraction Quality
- Total words extracted
- Body text words (after filtering)
- Footnote words removed
- Removal percentage

### Footnote Detection
- Items labeled as "footnote" by Docling
- Items caught by citation heuristic
- Total removed

### Quality Indicators
- Hyphenation artifacts (total & in body)
- High-density citation paragraphs (>15% citations in body)

## Testing Strategy

### Phase 1: Validate Framework
- Run on **Nedrud_1964.pdf** (smallest) with default config
- Verify metrics collection works
- Check report generation
- **Time**: ~2 minutes

### Phase 2: Full Benchmark
- Run all 3 documents × 3 configs = **9 extraction runs**
- Generate individual reports for each run
- Create comparison report
- **Estimated time**: 20-35 minutes total

### Phase 3: Analysis
- Compare configurations across documents
- Identify patterns:
  - Does 2x scaling improve footnote detection?
  - Does Heron-101 outperform default?
  - Are older documents handled differently than newer ones?
- Calculate cost/benefit of each configuration

## Learning Objectives

**Questions to Answer**:

1. **Does higher resolution help?**
   - Compare default (1.0x) vs 2x_scale
   - Look at: footnotes detected, high-density paragraphs, processing time

2. **Is Heron-101 better than default?**
   - Compare 2x_scale vs optimized (both use 2x, but different models)
   - Look at: label distribution, footnote detection accuracy

3. **Are results consistent across documents?**
   - Compare same config across different documents
   - Look for patterns by document age or complexity

4. **What's the optimal cost/benefit?**
   - Processing time vs quality improvement
   - Is 2x-3x slower processing worth better detection?

## Reports Generated

### Individual Reports (`benchmark_reports/`)
- One per run (9 total)
- Full metrics for that document + config
- Standardized format for comparison

### Comparison Report
- Side-by-side comparison across all runs
- Grouped by document and by configuration
- Summary statistics and key findings
- Recommendations for optimal settings

### JSON Metrics (`results/benchmarks/`)
- Machine-readable metrics for each run
- Enable programmatic analysis
- Can be used for visualization

## Next Steps After Benchmarking

Based on results:
1. **If optimized config is clearly better**: Use it as default
2. **If results vary by document**: Create document-specific strategies
3. **If contamination remains**: Add Gemini Flash post-processing
4. **If quality is good**: Test on larger corpus (20-30 documents)

## Running the Benchmark

```bash
# Test framework first (2 min)
uv run python test_benchmark_framework.py

# Run full benchmark (20-35 min)
uv run python benchmark_extraction.py

# View comparison report
cat results/benchmark_reports/comparison_report.md
```

## Success Criteria

A successful benchmark will:
- ✅ Complete all 9 runs without errors
- ✅ Generate comparable metrics
- ✅ Identify clear winners/losers
- ✅ Provide actionable recommendations
- ✅ Reveal patterns across documents

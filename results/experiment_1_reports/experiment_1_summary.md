# Extraction Benchmark Comparison

**Total Runs**: 3

## Summary by Document

### Green_Roiphe_2020.pdf

| Config | Time (min) | Body Words | Removed | % Removed | Citations Caught | High Density |
|--------|-----------|------------|---------|-----------|-----------------|-------------|
| baseline_default | 1.06 | 13,807 | 7,264 | 34.47% | 0 | 0 |

### Jackson_2014.pdf

| Config | Time (min) | Body Words | Removed | % Removed | Citations Caught | High Density |
|--------|-----------|------------|---------|-----------|-----------------|-------------|
| baseline_default | 2.32 | 43,008 | 11,011 | 20.38% | 88 | 1 |

### Nedrud_1964.pdf

| Config | Time (min) | Body Words | Removed | % Removed | Citations Caught | High Density |
|--------|-----------|------------|---------|-----------|-----------------|-------------|
| baseline_default | 0.68 | 10,196 | 6,032 | 37.17% | 2 | 0 |

## Processing Speed Comparison

| Document | Config | Pages/Min | Total Time |
|----------|--------|-----------|------------|
| Green_Roiphe_2020.pdf | baseline_default | 48.1 | 1.06 min |
| Jackson_2014.pdf | baseline_default | 45.3 | 2.32 min |
| Nedrud_1964.pdf | baseline_default | 50.0 | 0.68 min |

## Key Findings

**baseline_default**:
- Avg removal: 30.7%
- Avg citations caught: 30
- Avg processing time: 1.35 min


---
*Generated: 2025-10-13 21:37:50*

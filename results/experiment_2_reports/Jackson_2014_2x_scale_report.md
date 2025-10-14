# Extraction Benchmark Report

## Document Information
- **File**: Jackson_2014.pdf
- **Size**: 6.55 MB
- **Pages**: 105

## Configuration
- **Name**: 2x_scale
- **Image Scale**: 2.0x
- **Model**: default
- **Single Column Fallback**: False

## Processing Performance
- **Time**: 137.84s (2.30 min)
- **Speed**: 45.7 pages/min

## Label Distribution
| Label | Count |
|-------|-------|
| list_item | 272 |
| text | 261 |
| footnote | 205 |
| section_header | 32 |
| picture | 5 |
| document_index | 1 |

**Total Items**: 776

## Text Extraction Results
| Metric | Value |
|--------|-------|
| **Total Words** | 54,019 |
| **Body Words** | 43,008 |
| **Footnote Words** | 11,011 |
| **Words Removed** | 11,011 (20.38%) |

## Footnote Detection
| Metric | Value |
|--------|-------|
| **Labeled as Footnote** | 205 |
| **Caught by Heuristic** | 88 |
| **Total Removed** | 11,011 words |

## Quality Metrics
| Metric | Value |
|--------|-------|
| **Hyphenation Artifacts (All)** | 34 |
| **Hyphenation Artifacts (Body)** | 26 |
| **High-Density Paragraphs (Body)** | 1 |

## Output Sizes
| Output | Characters |
|--------|-----------|
| **All Text** | 379,957 |
| **Body Only** | 305,044 |
| **Footnotes Only** | 74,911 |

---
*Generated: 2025-10-13 21:50:16*

# cite-assist Integration Guide

**Code Version:** 0.1.0
**Last Updated:** 2025-10-15

## Purpose

Guide to deploying DoclingBERT models to cite-assist for production use.

## Current Integration Status

**Issue:** [cite-assist#461](https://github.com/donaldbraman/cite-assist/issues/461)

**Model Ready:** DoclingBERT v2-rebalanced
- Location: `models/doclingbert-v2-rebalanced/final_model/`
- Performance: 83.3% recall, 84.08% F1
- Format: HuggingFace transformers (ModernBERT-base)

## Integration Questions (Awaiting cite-assist Response)

1. **Model Delivery Format**
   - Copy entire `final_model/` directory to cite-assist repo?
   - Keep in docling-testing and update volume mount?
   - Upload to model registry (HuggingFace)?

2. **Service Adaptation**
   - Update existing `footnote-classifier` service?
   - Create new `body-text-classifier` service?
   - Provide code patch?

3. **API Changes**
   - Keep `is_citation: bool` or rename to `is_body_text: bool`?
   - Expose all 7 classes for richer processing?

## Model Files

**Required files in final_model/:**
```
final_model/
├── config.json                 # Model configuration
├── model.safetensors          # Model weights (~600MB)
├── tokenizer.json             # Tokenizer config
├── tokenizer_config.json      # Tokenizer settings
├── special_tokens_map.json    # Special tokens
└── label_map.json             # Class mapping + metadata
```

## Binary Classification Mapping

DoclingBERT outputs 7 classes but can be used for binary body_text detection:

```python
# In classifier service
predicted_class_id = torch.argmax(probabilities, dim=-1).item()

# Binary mapping
is_body_text = (predicted_class_id == 0)  # Class 0 = body_text

# All other classes treated as non-body_text:
# 1: heading, 2: footnote, 3: caption,
# 4: page_header, 5: page_footer, 6: cover
```

## Expected Performance in Production

**Metrics:**
- 83.3% of body_text paragraphs correctly identified
- 17% miss rate (148/885 false negatives)
- 126/885 false positives (acceptable trade-off)

**Practical impact:**
- Before: Missing 35% of content (baseline)
- After: Missing 17% of content (v2-rebalanced)
- **53% reduction in missed content**

## Next Steps

Waiting for cite-assist team response on:
1. Preferred model delivery format
2. Service integration approach
3. API design preferences

See: https://github.com/donaldbraman/cite-assist/issues/461

---

**Last Updated:** 2025-10-15

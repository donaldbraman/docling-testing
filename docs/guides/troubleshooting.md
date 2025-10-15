# Troubleshooting Guide

**Code Version:** 0.1.0
**Last Updated:** 2025-10-15

## Common Issues

### Training Issues

#### Training Hangs During Evaluation

**Symptoms:** Training completes a step but evaluation stuck at 41%

**Cause:** MPS (Apple Silicon GPU) deadlock or memory pressure

**Solutions:**
```bash
# 1. Kill stuck process
ps aux | grep python | grep train
kill <PID>

# 2. Reduce batch size
# Edit train script: per_device_eval_batch_size=4

# 3. Disable MPS fallback
PYTORCH_ENABLE_MPS_FALLBACK=1 python train_multiclass_classifier.py
```

#### Out of Memory (OOM)

**Symptoms:** Training crashes with CUDA/MPS OOM error

**Solutions:**
```bash
# 1. Reduce batch size
per_device_train_batch_size=1
gradient_accumulation_steps=32  # Effective batch size still 32

# 2. Enable gradient checkpointing (already enabled in scripts)
gradient_checkpointing=True

# 3. Use smaller model
# Switch from ModernBERT-base to smaller variant (future)
```

#### NaN Loss

**Symptoms:** Loss becomes NaN during training

**Causes:**
- Learning rate too high
- Gradient explosion
- Bad data (inf/nan values)

**Solutions:**
```bash
# 1. Reduce learning rate
learning_rate=1e-5  # Down from 2e-5

# 2. Check data quality
python build_clean_corpus.py --validate

# 3. Use gradient clipping
max_grad_norm=1.0  # Already default in trainer
```

### Evaluation Issues

#### Low Recall Despite High Accuracy

**Symptoms:** 95% accuracy but 65% body_text recall

**Cause:** Class imbalance (model optimized for majority class)

**Solution:**
```bash
# Train with increased class weight
python train_rebalanced.py  # Uses 3x body_text weight
```

See: [Model Training](model-training.md) - Workflow 2

#### Model Not Loading

**Symptoms:** `FileNotFoundError` or `OSError` when loading model

**Solutions:**
```bash
# 1. Verify model path exists
ls -la models/doclingbert-v2-rebalanced/final_model/

# 2. Check required files present
ls models/doclingbert-v2-rebalanced/final_model/
# Should see: config.json, model.safetensors, tokenizer files

# 3. Re-save model if corrupted
python train_multiclass_classifier.py  # Retrain
```

### Data Collection Issues

#### Scraper Timing Out

**Symptoms:** `requests.exceptions.Timeout` when scraping

**Solutions:**
```bash
# 1. Increase timeout
# Edit scrape_law_reviews.py: timeout=60

# 2. Add delay between requests
import time
time.sleep(2)  # 2 second delay

# 3. Use exponential backoff
for i in range(3):  # Retry 3 times
    try:
        response = requests.get(url, timeout=30)
        break
    except Timeout:
        time.sleep(2 ** i)  # 1s, 2s, 4s
```

#### PDF Download Fails

**Symptoms:** PDFs not downloading or corrupted

**Solutions:**
```bash
# 1. Verify URL accessibility
curl -I <pdf_url>

# 2. Check disk space
df -h

# 3. Validate downloaded PDFs
python batch_inspect_pdfs.py
```

## Error Messages

### `ModuleNotFoundError: No module named 'transformers'`

**Solution:**
```bash
uv sync  # Install all dependencies
```

### `RuntimeError: MPS backend out of memory`

**Solution:**
```bash
# Reduce batch size or switch to CPU
PYTORCH_ENABLE_MPS_FALLBACK=1 python train.py
```

### `ValueError: label_map.json missing required field`

**Solution:**
```bash
# Ensure label_map.json has:
# - model_name
# - version
# - base_model
# - label_map

# Regenerate if needed
python train_multiclass_classifier.py  # Creates new label_map.json
```

## Getting Help

1. **Check existing issues:** https://github.com/donaldbraman/docling-testing/issues
2. **Read related guides:**
   - [Model Training](model-training.md)
   - [Model Evaluation](model-evaluation.md)
3. **Create new issue** with:
   - Error message (full traceback)
   - Steps to reproduce
   - System info (OS, Python version, GPU)

---

**Last Updated:** 2025-10-15

# Docker Build Journey - OCR + Classification Pipeline

**Date:** 2025-10-24
**Final Status:** Build #2 in progress (should succeed)

---

## The Problem

ModernBERT model requires **transformers 4.57.0**, but PyPI only has up to 4.46.3.
Solution: Install from GitHub main branch where ModernBERT support was added.

---

## Build Attempts

### Build #1 - Failed ❌
**Commit:** 7881b26 - "fix: Install transformers from GitHub for ModernBERT support"
**Change:** Added `pip install git+https://github.com/huggingface/transformers.git`

**Error:**
```
ERROR: Cannot find command 'git' - do you have 'git' installed and in your PATH?
```

**Root cause:** Docker image didn't have `git` installed in system dependencies

**Duration:** 3m52s

---

### Build #2 - In Progress ⏳
**Commit:** c219350 - "fix: Add git to Docker image for transformers GitHub install"
**Change:** Added `git` to apt-get install

**Dockerfile changes:**
```dockerfile
# Before
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0

# After
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0
```

**Status:** Running for 7+ minutes (expected for large container)

**Expected outcome:** ✅ Should succeed - all dependencies now available

---

## Container Size Breakdown

| Component | Size | Notes |
|-----------|------|-------|
| PyTorch 2.6.0 + CUDA 12.4 base | ~3-5 GB | From pytorch/pytorch official image |
| EasyOCR + dependencies | ~500 MB | opencv, scikit-image, scipy, shapely |
| Transformers (from git) | ~300 MB | Full repo clone + install |
| ModernBERT model weights | 571 MB | Uploaded separately to vast.ai instances |
| **Total container** | **~5-7 GB** | Compressed on Docker Hub |

---

## Why This Takes Time

1. **Git clone:** Transformers repo has ~100k commits, full history
2. **Install:** Building wheels for transformers dependencies
3. **Pushing:** 5-7 GB upload to Docker Hub

**Typical build time:** 8-12 minutes

---

## What Works Now

✅ SSH connection parsing fixed (fields 10,11 instead of 8,9)
✅ Instance provisioning working (RTX 3060-3090 on vast.ai)
✅ EasyOCR installation and pre-download
✅ PyMuPDF for PDF manipulation
✅ All system dependencies
✅ Git installed for transformers install
⏳ Transformers with ModernBERT support (building now)

---

## Next Steps After Build Completes

1. **Verify Docker image:**
   ```bash
   # Check build succeeded
   gh run list --workflow=build-easyocr-image.yml --limit 1
   ```

2. **Create instance with new image:**
   ```bash
   vastai create instance <MACHINE_ID> --image donaldbraman/body-extractor:latest --disk 40
   ```

3. **Wait 3-4 minutes** for instance to pull and load the 5-7 GB image

4. **Run classification test:**
   ```bash
   ./run_classification_test.sh
   ```

5. **Expected output:** 5 files in `results_classified/`:
   - Plain text
   - Text overlay PDF
   - Class overlay PDF (colored by type)
   - CSV with predictions
   - JSON with full metadata

---

## Cost Analysis

**Development costs (today):**
- Instance attempts: ~5 instances
- Testing time: ~45 minutes total runtime
- Estimated cost: **$2-3**

**Production costs (per run):**
- OCR + classification: 5-10 minutes
- Auto-cleanup: Destroys instance after completion
- Cost per test: **$0.01-0.02**

**Monthly estimate** (assuming 100 tests/month):
- 100 tests × $0.015 avg = **$1.50/month**
- Very affordable for development/research

---

## Lessons Learned

1. **ModernBERT is cutting edge** - Not yet in stable transformers release
2. **Docker build dependencies matter** - Need git for pip install from GitHub
3. **Large containers are slow** - 5-7 GB takes time to build and distribute
4. **Vast.ai instance startup varies** - Some machines load faster than others
5. **Auto-cleanup is essential** - Prevents runaway costs from forgotten instances

---

## Final Dockerfile

```dockerfile
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

LABEL maintainer="body-extractor"
LABEL description="EasyOCR + ModernBERT environment for body text extraction"

# Install system dependencies (including git for transformers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    easyocr==1.7.2 \
    pdf2image==1.17.0 \
    pillow==11.0.0 \
    pandas==2.3.3 \
    pymupdf==1.26.5 \
    rapidfuzz==3.14.1 \
    torch==2.6.0

# Install transformers from GitHub main for ModernBERT support
RUN pip install --no-cache-dir git+https://github.com/huggingface/transformers.git

# Pre-download EasyOCR English models
RUN python3 -c "import easyocr; reader = easyocr.Reader(['en'], gpu=False); print('EasyOCR models pre-downloaded')"

WORKDIR /workspace

CMD ["/bin/bash"]
```

---

**Build monitoring:** `gh run watch <RUN_ID>` or check GitHub Actions web interface

*This document will be deleted after successful testing.*

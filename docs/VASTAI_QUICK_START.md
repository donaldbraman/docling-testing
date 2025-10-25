# vast.ai Quick Start Guide

**Fast, cost-effective GPU testing for body-extractor**

## TL;DR

```bash
# Run OCR + classification test on vast.ai (takes ~2-3 minutes, costs ~$0.10)
./scripts/vastai/run_classification_test_v2.sh

# Or with custom PDF:
./scripts/vastai/run_classification_test_v2.sh path/to/test.pdf
```

## Why This Approach Works

### ❌ What Doesn't Work
- **Large CUDA images** (12GB+): Stuck in "loading" for 10+ minutes
- **Direct model compilation**: Requires extensive build tools

### ✅ What Works
- **Lightweight Ubuntu base** (ubuntu:22.04): Starts in ~30 seconds
- **Runtime dependency install with uv**: 25 seconds (10-100x faster than pip)
- **Total setup time**: ~1 minute vs 10+ minutes with CUDA images

## Performance Comparison

| Approach | Instance Start | Dependency Install | Total Setup | Cost |
|----------|---------------|-------------------|-------------|------|
| **CUDA Image** (old) | 10+ min (often stuck) | Included | 10+ min | $0.08/hr |
| **Ubuntu + uv** (new) | 30 sec | 25 sec | ~1 min | $0.08/hr |
| **RunPod** | 1-2 min | 2-3 min | 3-5 min | $0.34/hr |

**Winner:** Ubuntu + uv (5-10x faster, same cost)

## Quick Start

### 1. Install vast.ai CLI

```bash
pip install vastai
vastai set api-key YOUR_API_KEY
```

Get API key at: https://cloud.vast.ai/api/

### 2. Run Classification Test

```bash
# Default test (Jackson 2014 law review)
./scripts/vastai/run_classification_test_v2.sh

# Custom PDF
./scripts/vastai/run_classification_test_v2.sh path/to/test.pdf

# Custom model and output directory
./scripts/vastai/run_classification_test_v2.sh \
  test.pdf \
  models/my-model \
  results/test
```

### 3. Results

The script will:
1. ✅ Create Ubuntu instance (~30 sec)
2. ✅ Install dependencies with uv (~25 sec)
3. ✅ Upload script, model, and PDF (~60 sec)
4. ✅ Run OCR + classification
5. ✅ Download results
6. ✅ Clean up (destroy instance)

Total time: ~2-3 minutes (first run: ~35 min with EasyOCR download)
Total cost: ~$0.10-0.15

### Validation Results (2025-10-25)

**End-to-end test validated:**
- Instance: 27283423 (offer 20171200, reliability > 0.99)
- Setup: 20s instance start + 25s uv install = **45s total setup**
- Uploads: 556MB model in 71s (7.8 MB/s), 6.5MB PDF in 1.4s (4.7 MB/s)
- Processing: Jackson_2014.pdf (104 pages) → 5 output files
- Results: 353KB plain text, 944KB CSV, 4.4MB JSON, 13MB+14MB overlay PDFs
- Cleanup: Instance auto-destroyed, zero orphaned costs

**Performance validated:**
```
| Phase              | Time    | Notes                           |
|--------------------|---------|----------------------------------|
| Search offer       | 2s      | Filters reliability > 0.99      |
| Instance startup   | 20s     | Ubuntu 22.04 (not stuck!)       |
| uv install         | 25s     | 10-100x faster than pip         |
| Model upload       | 71s     | 7.8 MB/s transfer               |
| OCR+classification | Varies  | First run: +30min EasyOCR DL    |
| Results download   | <10s    | Automatic with rsync            |
| **Subsequent runs**| **~5min**| **Models cached**              |
```

## How It Works

### Lightweight Base + Runtime Install

```bash
# 1. Search for reliable offer (>99.9% uptime, good network)
OFFER_ID=$(vastai search offers "reliability > 0.99 gpu_name=RTX_4090 disk_space > 20 inet_down > 100" --raw | \
    jq -r 'sort_by(-(.reliability * 100) + .dph_total) | .[0].id')

# 2. Create instance from offer with Ubuntu (fast startup)
vastai create instance $OFFER_ID --image ubuntu:22.04 --disk 20

# 3. Install uv (10-100x faster than pip)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 4. Install dependencies (25 seconds)
uv pip install torch transformers easyocr ...

# 5. Run classification
python3 run_ocr_with_classification.py ...
```

**Critical:** Must search offers first, then create from offer ID. Using `--search` flag with `create instance` fails.

### Robust File Transfer

The script uses 3-layer fallback for maximum reliability:

1. **rsync** (fastest, resumable)
2. **Legacy SCP with -O flag** (bypasses ASCII art issues)
3. **SSH pipe** (always works)

See `VASTAI_BEST_PRACTICES.md` for details.

## GPU Selection

### Recommended GPUs (Best Value)

```bash
# RTX 4090 (best performance, $0.44/hr)
./scripts/vastai/run_classification_test_v2.sh test.pdf . . . RTX_4090

# RTX 3090 (good performance, $0.30/hr)
./scripts/vastai/run_classification_test_v2.sh test.pdf . . . RTX_3090

# RTX 3080 (budget option, $0.20/hr)
./scripts/vastai/run_classification_test_v2.sh test.pdf . . . RTX_3080
```

### Provider Selection

**Best providers (100% reliability):**
- Iceland (host 1647): 100% reliability, $0.44/hr RTX 4090
- Japan (host 53856): 99.9% reliability, $0.47/hr RTX 4090
- Norway (host 85684): 99.9% reliability, $0.93/hr RTX 4080S

**Avoid:**
- China providers: Frequently stuck in "loading"
- New providers (<50 reliability score)

## Troubleshooting

### Instance Stuck in "loading"

**Root cause:** Low-reliability providers (even with Ubuntu images)

**Fix:** Script now filters for `reliability > 0.99` + `inet_down > 100`. Iceland (host 1647) is 100% reliable.

If stuck:
1. Destroy: `vastai destroy instance <ID>`
2. Script auto-retries with different offer
3. Manually select Iceland: Search for `host_id=1647` in offers

### SSH Connection Refused

- Wait 10-15 seconds for SSH key to propagate
- Script auto-retries 10 times with 5s delay
- If still fails, check: `vastai show instance <ID>`

### File Transfer Fails

The script tries 3 methods automatically:
1. rsync (fastest)
2. Legacy SCP with -O (vast.ai compatible)
3. SSH pipe (always works)

If all fail, check network connectivity.

### EasyOCR Model Download Slow

**First run:** Downloads ~250-300MB of models (detection + recognition)
- This is one-time only
- Cached on instance for subsequent runs
- Takes 3-5 minutes depending on provider bandwidth

**Subsequent runs:** Models are cached, no download needed

## Cost Management

### Typical Costs

```bash
# Single test run: ~2-3 minutes
Cost: $0.10-0.15 (RTX 4090)

# 10 test runs (reusing instance): ~15 minutes
Cost: $0.60-0.75

# Full day of testing: 8 hours
Cost: $3.50 (RTX 4090)
```

### Cost Optimization

1. **Reuse instances** for multiple tests (models cached)
2. **Use cheaper GPUs** (RTX 3080 is 50% cheaper)
3. **Destroy when done** (script auto-destroys)
4. **Set max runtime** in vast.ai dashboard

## Advanced Usage

### Reuse Instance (Skip Setup)

```bash
# Create instance once
INSTANCE_ID=$(vastai create instance --image ubuntu:22.04 ...)

# Run multiple tests
for pdf in *.pdf; do
    ./scripts/vastai/run_classification_test_v2.sh "$pdf" . results/"${pdf%.pdf}"
done

# Clean up
vastai destroy instance $INSTANCE_ID
```

### Custom Dependencies

Edit `run_classification_test_v2.sh` and add to the `uv pip install` section:

```bash
uv pip install --quiet \
    torch==2.1.0 \
    transformers==4.50.0 \
    your-custom-package==1.0.0
```

### Different Base Images

The script uses `ubuntu:22.04` for fast startup. Other options:

```bash
# Python pre-installed (slightly larger)
--image python:3.10-slim

# PyTorch pre-installed (much larger, slower startup)
--image pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime
```

**Recommendation:** Stick with Ubuntu 22.04 + runtime install

## Comparison with Alternatives

### vs RunPod

| Feature | vast.ai (new) | RunPod |
|---------|---------------|---------|
| Setup time | ~1 min | 3-5 min |
| Cost (RTX 4090) | $0.08-0.44/hr | $0.69/hr |
| Reliability | 95-100% (provider-dependent) | ~99% |
| Ease of use | CLI | Web + CLI |
| SSH setup | Simple | More complex |

**Verdict:** vast.ai is 5-10x cheaper with good providers

### vs Local GPU

| Feature | vast.ai | Local RTX 4090 |
|---------|---------|----------------|
| Initial cost | $0 | $1,600+ |
| Running cost | $0.44/hr | Electricity (~$0.10/hr) |
| Setup | 1 minute | Hours (drivers, CUDA, etc.) |
| Scalability | Infinite | 1 GPU |

**Verdict:** vast.ai for occasional testing, local for heavy use

## Links

- **vast.ai Dashboard**: https://cloud.vast.ai/
- **CLI Docs**: https://vast.ai/docs/cli/commands
- **API Docs**: https://vast.ai/docs/api/introduction
- **Pricing**: Search at https://cloud.vast.ai/

## Related Docs

- **VASTAI_BEST_PRACTICES.md** - Comprehensive troubleshooting guide
- **RUNPOD_SETUP_GUIDE.md** - Alternative provider guide
- **TRAINING_QUICK_START.md** - Full training workflow

---

*Last updated: 2025-10-25*

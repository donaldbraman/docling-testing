# vast.ai GPU Rental Analysis for OCR and ModernBERT Training

**Date:** 2025-01-24
**Purpose:** Evaluate vast.ai GPU rental options for running OCR workloads (EasyOCR, PaddleOCR, Surya) and ModernBERT training

---

## Executive Summary

**Recommended Configuration:**
- **OCR Processing:** RTX 3090 (24GB) at $0.09-$0.20/hour
- **ModernBERT Training:** RTX 4090 (24GB) at $0.15-$0.40/hour (Flash Attention 2 compatible)
- **Combined Workflow:** RTX 4090 (handles both tasks efficiently)

**Total Estimated Costs:**
- **50 PDFs OCR Processing:** $0.50-$2.00 (1-4 hours @ $0.50/hour avg)
- **ModernBERT Training:** $0.30-$0.80 (1-2 hours @ $0.40/hour avg)
- **Total Project Cost:** $0.80-$2.80

**vs Local Mac M1:**
- **NVIDIA GPU advantage:** 10-15x faster for OCR, 15-30x faster for training
- **Cost effective:** Even at $3 total, vastly cheaper than time investment on M1
- **Compatibility:** Better library support (CUDA) vs M1 MPS issues

---

## 1. Current vast.ai GPU Pricing (January 2025)

### Consumer GPUs (Flash Attention 2 Compatible)

| GPU Model | VRAM | Compute Cap | Flash Attn 2 | Price Range ($/hr) | Best For |
|-----------|------|-------------|--------------|-------------------|----------|
| **RTX 3090** | 24GB | 8.6 (Ampere) | Yes | $0.09 - $0.20 | OCR workloads |
| **RTX 4090** | 24GB | 8.9 (Ada) | Yes | $0.15 - $0.40 | Training + OCR |

### Enterprise GPUs (Flash Attention 2 Compatible)

| GPU Model | VRAM | Compute Cap | Flash Attn 2 | Price Range ($/hr) | Best For |
|-----------|------|-------------|--------------|-------------------|----------|
| **A100 SXM4** | 40GB/80GB | 8.0 (Ampere) | Yes | $0.73 - $1.61 | Large-scale training |
| **H100** | 80GB | 9.0 (Hopper) | Yes | $0.90 - $2.00+ | Maximum performance |
| **L4** | 24GB | 8.9 (Ada) | Yes | ~$0.50 - $1.00 | Inference + training |

### Key Pricing Notes:
- **Per-second billing:** Only pay when instance is running
- **Storage costs:** Additional charges for disk space (applies when stopped)
- **Bandwidth:** Data transfer costs apply
- **Minimum deposit:** $5 to start
- **Price variability:** Marketplace pricing fluctuates based on availability
- **Savings:** 40-80% cheaper than AWS/GCP/Azure

---

## 2. Flash Attention 2 Compatibility

### Requirements:
- **Minimum Compute Capability:** 8.0
- **Supported Architectures:**
  - Ampere (8.0, 8.6): A100, RTX 3090, A10, A30
  - Ada Lovelace (8.9): RTX 4090, L4, L40
  - Hopper (9.0): H100, H800

### Benefits:
- **2-4x faster training** for ModernBERT
- **Lower memory footprint** (enables larger batch sizes)
- **Required for optimal ModernBERT performance**

### Not Supported:
- Turing GPUs (7.5): RTX 2080 Ti, T4 (use FlashAttention 1.x)
- Older architectures (Pascal, Volta)

---

## 3. VRAM Requirements

### OCR Models

| Model | Base VRAM | Batch Processing | Recommended GPU |
|-------|-----------|------------------|-----------------|
| **EasyOCR** | 2-4GB | 4-6GB | RTX 3090 (24GB) |
| **PaddleOCR** | 1-2GB | 3-4GB | RTX 3090 (24GB) |
| **Surya OCR** | 24GB+ | 24GB+ | A100 (40GB) recommended |

**Notes:**
- EasyOCR: PyTorch-based, excellent GPU acceleration
- PaddleOCR: Lightweight (<10MB), very fast with GPU
- Surya: High VRAM requirements, can be reduced with batch size tuning
- **Recommendation:** RTX 3090 24GB handles all three comfortably

### ModernBERT Training (149M parameters)

| Configuration | VRAM Required | Batch Size | GPU Recommendation |
|---------------|---------------|------------|-------------------|
| **Minimal** | 12GB | 4-8 | RTX 3060 (12GB) |
| **Standard** | 16GB | 8-16 | RTX 4080 (16GB) |
| **Optimal** | 24GB | 16-32 | RTX 3090/4090 (24GB) |
| **Large-scale** | 40GB+ | 32+ | A100 (40GB/80GB) |

**Training Time Benchmark:**
- **15,000 samples, 5 epochs:** 321 seconds (5.4 minutes) on L4 GPU
- **ModernBERT vs BERT:** 3x faster training time
- **Your corpus:** ~38,000 samples = ~12-20 minutes on RTX 4090

**Flash Attention 2 Impact:**
- Enables 2-4x faster training
- Reduces memory usage by ~30%
- **Critical for optimal performance**

---

## 4. Cost Estimation for Your Use Case

### OCR Processing: 50 PDFs (40 pages each = 2,000 pages)

#### RTX 3090 Scenario ($0.15/hour avg):

**EasyOCR:**
- Speed: ~3-5 seconds/page with GPU
- Total time: 2,000 pages × 4 sec = 8,000 sec = 2.2 hours
- Cost: 2.2 hours × $0.15 = **$0.33**

**PaddleOCR:**
- Speed: ~1-2 seconds/page with GPU (faster than EasyOCR)
- Total time: 2,000 pages × 1.5 sec = 3,000 sec = 0.83 hours
- Cost: 0.83 hours × $0.15 = **$0.12**

**Combined approach (Surya for difficult pages):**
- Primary: PaddleOCR (80% of pages) = 0.66 hours
- Fallback: Surya OCR (20% of pages) = 0.5 hours
- Total time: ~1.2 hours
- Cost: 1.2 hours × $0.20 = **$0.24**

**Recommended:** PaddleOCR as primary engine = **$0.12-$0.25 total**

### ModernBERT Training: 38,000 samples, 100 steps

#### RTX 4090 Scenario ($0.30/hour avg):

**Training Configuration:**
- Model: ModernBERT-base (149M parameters)
- Dataset: 38,000 labeled paragraphs
- Epochs: 3-5 (based on your v2-rebalanced model)
- Batch size: 16-24 (with Flash Attention 2)

**Time Estimate:**
- Reference: 15,000 samples = 5.4 minutes on L4
- Scaling: 38,000 samples ≈ 13.7 minutes
- With Flash Attn 2 on RTX 4090: ~10-15 minutes
- Conservative estimate: **20-30 minutes (0.33-0.5 hours)**

**Cost:**
- Training: 0.5 hours × $0.30 = **$0.15**
- Checkpoint evaluation: 0.1 hours × $0.30 = **$0.03**
- Total: **$0.18-$0.30**

### Combined Workflow Total

| Task | GPU | Time | Cost |
|------|-----|------|------|
| OCR (50 PDFs) | RTX 3090 | 1 hour | $0.15 |
| Training | RTX 4090 | 0.5 hours | $0.15 |
| Evaluation | RTX 4090 | 0.1 hours | $0.03 |
| **TOTAL** | - | **1.6 hours** | **$0.33** |

**Buffer for experimentation:** 2x cost = **$0.66 total**

---

## 5. vast.ai vs Mac M1 GPU Comparison

### Performance Differential

| Workload | Mac M1 (MPS) | RTX 3090/4090 (CUDA) | Speedup |
|----------|--------------|----------------------|---------|
| **EasyOCR inference** | ~10-15 sec/page | ~3-5 sec/page | 2-3x faster |
| **PaddleOCR inference** | ~5-8 sec/page | ~1-2 sec/page | 3-5x faster |
| **BERT training (inference)** | 36.00 sec | 0.82 sec (A10G) | **44x faster** |
| **ModernBERT training** | No benchmarks | 5.4 min (15k samples) | Est. 15-30x faster |

### Mac M1 Challenges

**OCR Processing:**
- PaddleOCR has known freezing issues on M1 Macs
- EasyOCR works but 2-3x slower than NVIDIA GPUs
- Limited CUDA library support (PyTorch MPS backend incomplete)

**Training:**
- MPS backend 13-44x slower than NVIDIA GPUs
- No Flash Attention 2 support (requires CUDA 8.0+)
- Limited to FP32 (no FP16 Tensor Core acceleration)
- Batch size constraints due to unified memory architecture

**Compatibility:**
- Many ML libraries optimized for CUDA, not Metal
- Frequent compatibility issues with newer models
- Less community support for M1 troubleshooting

### Cost-Benefit Analysis

**50 PDF OCR + ModernBERT Training:**

**Mac M1 Local:**
- Time: 5-10 hours (OCR) + 5-10 hours (training) = **10-20 hours**
- Cost: $0 (hardware already owned)
- Developer time: 10-20 hours @ $50-150/hour = **$500-$3,000 value**
- Compatibility issues: High risk of failures

**vast.ai RTX 4090:**
- Time: 1 hour (OCR) + 0.5 hours (training) = **1.5 hours**
- Cost: **$0.50-$0.75**
- Developer time: 1.5 hours @ $50-150/hour = **$75-$225 value**
- Compatibility issues: Minimal (standard CUDA)

**Savings:** $499-$2,999 in developer time
**ROI:** Immediate for any non-trivial workload

---

## 6. Recommended GPU Strategy

### For OCR-Only Workloads

**GPU:** RTX 3090 (24GB)
- **Compute Capability:** 8.6 (Ampere)
- **Flash Attention 2:** Yes
- **Price:** $0.09-$0.20/hour
- **VRAM:** 24GB (handles all OCR models comfortably)
- **Why:** Best price-performance for inference workloads

**Alternative:** RTX 4080 (16GB) at $0.15-$0.30/hour if RTX 3090 unavailable

### For Training-Only Workloads

**GPU:** RTX 4090 (24GB)
- **Compute Capability:** 8.9 (Ada Lovelace)
- **Flash Attention 2:** Yes
- **Price:** $0.15-$0.40/hour
- **VRAM:** 24GB (optimal batch sizes)
- **Why:** Latest architecture, excellent Flash Attention 2 performance

**Alternative:** A100 (40GB/80GB) at $0.73-$1.61/hour for larger models/datasets

### For Combined Workflows (Recommended)

**GPU:** RTX 4090 (24GB)
- Handles both OCR and training efficiently
- Single instance = no data transfer costs
- Flash Attention 2 support for training
- Price: $0.15-$0.40/hour

**Workflow:**
1. Rent RTX 4090 instance
2. Process all OCR tasks (1-2 hours)
3. Train ModernBERT (0.5-1 hour)
4. Evaluate checkpoints (0.1-0.2 hours)
5. Download results and terminate
6. **Total cost:** $0.50-$1.20

---

## 7. Practical Recommendations

### Getting Started with vast.ai

1. **Sign up:** Create account, deposit $5 minimum
2. **Search filters:**
   - GPU Model: RTX 4090 or RTX 3090
   - VRAM: 24GB minimum
   - Compute Capability: 8.0+
   - Sort by: Price (lowest first)
3. **Instance setup:**
   - Choose PyTorch template (includes CUDA)
   - Mount storage: 50-100GB for PDFs + models
   - Enable SSH access for monitoring
4. **Cost management:**
   - Stop instance when not processing (saves GPU cost)
   - Delete storage after project completion
   - Use interruptible instances for 50% savings (if acceptable)

### Optimization Tips

**OCR Processing:**
- Batch PDFs into groups of 10-20
- Use PaddleOCR as primary (fastest)
- EasyOCR as fallback for difficult pages
- Monitor GPU utilization (should be >70%)

**Training:**
- Enable Flash Attention 2 (requires CUDA 8.0+)
- Use mixed precision (FP16) for 2x speedup
- Batch size: Start at 24, reduce if OOM
- Gradient accumulation if batch size limited
- Save checkpoints every 25 steps
- Use early stopping to avoid overfitting

**Cost Saving:**
- Use spot/interruptible instances (50% cheaper)
- Process multiple tasks in single session
- Preload data before starting instance
- Download results immediately after completion
- Terminate instance promptly (per-second billing)

### Monitoring Performance

**OCR:**
```bash
# Monitor GPU utilization
watch -n 1 nvidia-smi

# Track pages/second
time python scripts/ocr_pipeline.py --batch-size 10
```

**Training:**
```bash
# Training with progress monitoring
uv run python scripts/training/train_rebalanced.py \
  --logging_steps 10 \
  --eval_steps 25 \
  --save_steps 25
```

### Troubleshooting

**Common Issues:**

1. **OOM (Out of Memory):**
   - Reduce batch size
   - Enable gradient checkpointing
   - Use FP16 mixed precision

2. **Slow training:**
   - Verify Flash Attention 2 is enabled
   - Check GPU utilization (should be >80%)
   - Increase batch size if utilization low

3. **Data transfer:**
   - Use vast.ai storage (no transfer costs)
   - Compress PDFs before upload
   - Stream results directly to S3/Cloud Storage

---

## 8. Cost Comparison Summary

| Approach | Time | GPU Cost | Dev Time Value | Total Cost |
|----------|------|----------|----------------|------------|
| **Mac M1 Local** | 10-20 hrs | $0 | $500-$3,000 | $500-$3,000 |
| **vast.ai RTX 3090** | 2-3 hrs | $0.30-$0.60 | $100-$450 | $100-$450 |
| **vast.ai RTX 4090** | 1.5-2 hrs | $0.45-$0.80 | $75-$300 | $75-$300 |
| **vast.ai A100** | 1-1.5 hrs | $1.10-$2.40 | $50-$225 | $51-$227 |

**Winner:** RTX 4090 for best balance of speed and cost

---

## 9. Pros and Cons

### vast.ai Advantages

**Performance:**
- 10-30x faster than Mac M1 for ML workloads
- Flash Attention 2 support (2-4x training speedup)
- Full CUDA ecosystem compatibility
- Tensor Core acceleration (FP16/BF16)

**Cost:**
- Pay-per-second billing (no waste)
- 40-80% cheaper than major cloud providers
- No long-term commitments
- Spot instances for 50% additional savings

**Flexibility:**
- Wide GPU selection (RTX 3090 to H100)
- Scale up/down instantly
- Multiple concurrent instances
- Global availability

### vast.ai Disadvantages

**Setup:**
- Initial learning curve (marketplace navigation)
- Instance availability varies
- Need to manage data transfer
- Docker/containerization knowledge helpful

**Reliability:**
- Marketplace = variable host quality
- Possible interruptions on spot instances
- No enterprise SLA guarantees
- Network speeds vary by host

**Costs:**
- Storage costs (even when stopped)
- Bandwidth charges for large datasets
- $5 minimum deposit

### Mac M1 Local Advantages

**Convenience:**
- No setup/configuration needed
- No data transfer required
- Works offline
- No recurring costs

**Integration:**
- Familiar development environment
- Direct file system access
- No container overhead

### Mac M1 Local Disadvantages

**Performance:**
- 10-30x slower than NVIDIA GPUs
- No Flash Attention 2 support
- MPS backend limitations
- Limited FP16 acceleration

**Compatibility:**
- PaddleOCR freezing issues
- Many CUDA-only libraries
- Incomplete PyTorch MPS support
- Less community documentation

**Efficiency:**
- Ties up local machine for hours
- Battery drain on MacBook
- Thermal throttling on long tasks
- Developer time costs far exceed GPU rental

---

## 10. Final Recommendations

### For Your Use Case (50 PDFs + Training)

**Recommended Approach:**

1. **Rent RTX 4090 instance** ($0.30-$0.40/hour)
2. **Process OCR first** (1-2 hours):
   - Use PaddleOCR for speed
   - Batch process 10 PDFs at a time
   - Estimated cost: $0.30-$0.80
3. **Train ModernBERT** (0.5-1 hour):
   - Enable Flash Attention 2
   - Batch size 24 with mixed precision
   - Evaluate checkpoints at steps 25, 50, 75, 100
   - Estimated cost: $0.15-$0.40
4. **Total project cost:** $0.45-$1.20
5. **Time savings:** 8-18 hours vs Mac M1

### Long-Term Strategy

**For recurring workloads:**
- Develop on Mac M1 (fast iteration)
- Validate on vast.ai RTX 4090 (production runs)
- Use spot instances for cost optimization
- Maintain scripts for easy vast.ai deployment

**For one-off experiments:**
- Small tests: Mac M1 (free)
- Production runs: vast.ai (faster)
- Critical deadline: Pay for A100 (maximum speed)

### Decision Matrix

| Scenario | Recommended GPU | Reasoning |
|----------|-----------------|-----------|
| **First-time training** | RTX 4090 | Flash Attn 2, mid-tier price |
| **Budget-constrained** | RTX 3090 | Best price/performance |
| **Time-critical** | A100/H100 | Maximum performance |
| **OCR-only** | RTX 3090 | Cheapest with 24GB VRAM |
| **Experimentation** | Mac M1 | Free, good for debugging |
| **Production pipeline** | RTX 4090 | Balanced speed/cost |

---

## Conclusion

For your use case (50 PDFs + ModernBERT training), **vast.ai is highly recommended** over local Mac M1 processing:

**Bottom Line:**
- **Total cost:** $0.45-$1.20
- **Time savings:** 8-18 hours
- **Performance:** 10-30x faster
- **Reliability:** Better compatibility, fewer issues
- **ROI:** Immediate (saves developer time worth $400-$3,000)

**Recommended configuration:**
- GPU: RTX 4090 (24GB)
- Price: $0.30-$0.40/hour
- Total time: 1.5-2 hours
- Total cost: $0.45-$0.80

The modest GPU rental cost is vastly outweighed by time savings and reduced frustration dealing with M1 compatibility issues.

---

## Additional Resources

**vast.ai Documentation:**
- Pricing page: https://vast.ai/pricing
- Console: https://cloud.vast.ai
- Documentation: https://docs.vast.ai

**Flash Attention 2:**
- GitHub: https://github.com/Dao-AILab/flash-attention
- PyPI: https://pypi.org/project/flash-attn/

**ModernBERT:**
- Hugging Face: https://huggingface.co/answerdotai/ModernBERT-base
- Training guide: https://www.philschmid.de/fine-tune-modern-bert-in-2025

**OCR Libraries:**
- EasyOCR: https://github.com/JaidedAI/EasyOCR
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- Surya: https://github.com/VikParuchuri/surya

---

*Last updated: 2025-01-24*

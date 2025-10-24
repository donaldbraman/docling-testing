# Vast.ai Research Summary: Key Findings and Recommendations

**Date:** 2025-10-24
**Purpose:** Executive summary of best practices research for deploying ML workloads to vast.ai

---

## Overview

This document summarizes research findings from official vast.ai documentation, community guides, and 2024-2025 production deployments. The full best practices guide is available in [VAST_AI_BEST_PRACTICES_2025.md](VAST_AI_BEST_PRACTICES_2025.md).

---

## Key Findings

### 1. Initial Setup

**API Key Management:**
- Stored in `~/.vast_api_key` by default
- Can use `VAST_API_KEY` environment variable
- Command: `vastai set api-key xxxxxxxx`
- Security: Never commit to version control, rotate periodically

**Account Verification:**
- Increases spending limits
- Unlocks access to premium datacenter hosts
- Recommended for production workloads

**SSH Keys:**
- Add public key at https://cloud.vast.ai/manage-keys/
- Password authentication disabled (keys only)
- Use ed25519 keys (more secure than RSA)

### 2. Instance Selection Strategy

**Reliability Score:**
- 0.0-1.0 scale based on historical disconnects/outages
- **Recommendation:** Use reliability > 0.95 for production
- Directly impacts job interruption risk

**Host Types:**
| Type | Reliability | Cost | Best For |
|------|-------------|------|----------|
| Verified Datacenters | High | Higher | Production, sensitive data |
| Unverified Hosts | Variable | Lower | Experimentation, testing |

**Secure Cloud Filter:**
- ISO 27001 certified datacenters
- Tier 3/4 compliance standards
- Data Processing Agreements (DPAs) signed
- **Use for:** Sensitive data, production workloads

**Rental Types:**
| Type | Cost | Reliability | Best For |
|------|------|-------------|----------|
| On-Demand | 2-3x higher | Guaranteed | Training >4 hours, production |
| Interruptible | 50-70% cheaper | Can be paused | Experimentation, <2 hours |

**Critical Finding:** Interruptible instances can save 50-70% but require aggressive checkpointing strategy.

### 3. Docker and Container Best Practices

**Recommended Base Images (2025):**

1. **Official PyTorch:** `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel`
   - Pros: Official support, all dependencies included
   - Cons: Large size (~10GB)
   - Best for: Most use cases

2. **NVIDIA CUDA Base:** `nvidia/cuda:12.4.0-cudnn9-runtime-ubuntu22.04`
   - Pros: Minimal, customizable
   - Cons: Must install Python/packages
   - Best for: Custom builds, specific Python versions

3. **AI-Dock Images:** `ai-dock/pytorch:latest-cuda-12.4-python-3.11`
   - Pros: Vast.ai optimized, includes common tools
   - Cons: Less official support
   - Best for: Quick starts, Jupyter workflows

**Environment Variables (Auto-Set):**
- `CONTAINER_ID` - Instance identifier
- `CONTAINER_API_KEY` - Per-instance API key
- `DATA_DIRECTORY` - Default data location
- `PYTORCH_VERSION` - PyTorch version (if applicable)

**Provisioning Scripts:**
- Alternative to custom Docker images
- Host script on GitHub/Gist, set URL in `PROVISIONING_SCRIPT` env var
- Good for: Quick customizations without rebuilding images

### 4. Code Deployment Patterns

**Comparison of Methods:**
| Method | Speed | Incremental | Best For |
|--------|-------|-------------|----------|
| rsync | Fast | Yes | Iterative development |
| scp | Medium | No | One-time transfers |
| git clone | Medium | N/A | Version-controlled deployments |
| Cloud storage | Very fast | N/A | Large datasets (>10GB) |
| Docker image | Slow | N/A | Pre-configured environments |

**Recommended Workflow:**
1. Code via rsync (fast, incremental)
2. Small data (<10GB) via rsync
3. Large data (>10GB) via cloud storage (S3/GCS)
4. Results back via rsync (periodic backup)

**rsync Best Practices:**
```bash
# Basic command
rsync -avz -e "ssh -p <PORT>" --exclude='.venv' --exclude='models/' \
  /local/project/ root@<IP>:/workspace/project/

# Flags:
# -a (archive mode), -v (verbose), -z (compress)
# --partial (resume support), --progress (show progress)
```

### 5. Environment Setup

**Python Package Managers:**

| Tool | Speed | Best For | Notes |
|------|-------|----------|-------|
| **uv** | 10-100x faster | Modern projects | Recommended for docling-testing |
| pip + venv | Baseline | Simple projects | Traditional approach |
| conda | Slower | Complex C/C++ deps | Only when necessary |

**uv Advantages:**
- Automatic virtual environment management
- Deterministic dependency resolution
- Built-in Python version management
- Zero config for Docker containers

**Flash Attention 2 Installation:**
- **Critical:** Requires Ampere/Ada/Hopper GPUs (8.0+ compute capability)
- **NOT supported:** Turing GPUs (T4, RTX 2080 Ti)
- **Speedup:** Install ninja first: `apt-get install -y ninja-build`
- Compilation time: 3-5 minutes with ninja, 60-120 minutes without

### 6. Data Transfer Optimization

**Vast.ai Network Architecture:**

1. **Proxy SSH (Default):**
   - Latency: High (300-500ms)
   - Bandwidth: Moderate (10-50 MB/s)
   - Cost: FREE (no bandwidth charges)
   - Use for: Small files (<1GB), interactive sessions

2. **Direct SSH:**
   - Latency: Low (10-50ms)
   - Bandwidth: High (50-200 MB/s)
   - Cost: Bandwidth charges apply
   - Use for: Large transfers (1-10GB)

3. **Cloud Storage:**
   - Latency: Very low (<10ms)
   - Bandwidth: Very high (200-1000 MB/s)
   - Cost: Cloud egress charges ($0.09-$0.12/GB)
   - Use for: Very large datasets (>10GB)

**Critical Finding:** Instance-to-instance transfers within same host are FREE.

**Bandwidth Cost Optimization:**
- Use proxy SSH for small transfers (free)
- Compress before transfer: `tar -czf project.tar.gz project/`
- Use cloud storage for large datasets (much faster, predictable cost)
- Copy between instances on same host (free)

### 7. Job Execution and Monitoring

**Persistent Sessions (Critical):**
- **Always use:** screen, tmux, or nohup
- SSH disconnects don't kill your job
- Enables remote monitoring

**Screen vs tmux:**
| Feature | screen | tmux |
|---------|--------|------|
| Simplicity | Simpler | More complex |
| Features | Basic | Advanced (split panes, scripting) |
| Best for | Quick jobs | Interactive development |

**GPU Monitoring Tools:**

| Tool | Type | Best For |
|------|------|----------|
| nvidia-smi | CLI | Basic monitoring, scripting |
| nvtop | Interactive | User-friendly, real-time graphs |
| nvitop | Interactive | Modern, ML framework integration |
| gpustat | CLI | Minimal, scriptable |

**Checkpointing Strategy:**
- **Frequency:** Every 50-100 steps (critical for interruptible instances)
- **Cloud backup:** Essential - sync checkpoints to S3/GCS every 10 minutes
- **Disk management:** Keep only 3 best checkpoints (save disk space)

**Recovery Script Pattern:**
```bash
# 1. Download latest checkpoint from cloud
aws s3 sync s3://bucket/models/ /workspace/models/

# 2. Find latest checkpoint
LATEST=$(ls -td /workspace/models/checkpoint-* | head -1)

# 3. Resume training
python train.py --resume-from-checkpoint "$LATEST"
```

### 8. Cost Optimization Strategies

**Storage Costs (Critical Finding):**
- **Stopped instances are still charged storage costs**
- **Solution:** DESTROY instances immediately after downloading results
- Don't just STOP - you're still being billed!

**Minimize Billable Time:**
1. Test code locally first (catch bugs before deploying)
2. Use pre-built Docker images (faster startup)
3. Use cloud storage for large datasets (much faster than rsync)
4. Auto-stop on completion (add to training script)

**Instance Selection:**
| Workload | GPU | Cost/hr | Notes |
|----------|-----|---------|-------|
| OCR | RTX 3090 | $0.09-$0.20 | Best price/performance |
| Training | RTX 4090 | $0.15-$0.40 | Flash Attention 2 support |
| Large-scale | A100 40GB | $0.73-$1.61 | Maximum performance |

**Multi-Instance Strategies:**
- Parallel OCR processing: 4 instances = 4x faster (same cost, faster results)
- Hyperparameter search: Test 5 configs in parallel (5x faster)
- Cost is same, but results arrive much faster

**Estimated Costs (docling-testing):**
| Task | GPU | Duration | Cost |
|------|-----|----------|------|
| OCR 50 PDFs | RTX 3090 | 2 hours | $0.18-$0.30 |
| Train ModernBERT | RTX 4090 | 0.5 hours | $0.08-$0.20 |
| **TOTAL** | - | 2.5 hours | **$0.26-$0.50** |

**ROI Analysis:**
- Local Mac M1: 10-20 hours @ $50-150/hr value = $500-$3,000
- Vast.ai: 2.5 hours actual, $0.50 GPU cost
- **Savings: $499.50-$2,999.50 in developer time**

### 9. Common Pitfalls and Solutions

**Top 5 Issues:**

1. **Flash Attention 2 Install Fails**
   - Cause: Incompatible GPU (Turing), missing CUDA toolkit
   - Solution: Use Ampere+ GPUs, install CUDA toolkit, use ninja

2. **CUDA Out of Memory**
   - Cause: Batch size too large
   - Solution: Reduce batch size, enable gradient checkpointing, use FP16

3. **Instance Disk Full**
   - Cause: Too many checkpoints
   - Solution: Set `save_total_limit=3`, delete old checkpoints

4. **SSH Disconnects Kill Job**
   - Cause: Running job directly in SSH session
   - Solution: Always use screen/tmux/nohup

5. **Slow Data Transfer**
   - Cause: Using proxy for large files, many small files
   - Solution: Use cloud storage for large datasets, compress small files

### 10. Security Best Practices

**SSH Keys:**
- Use ed25519 keys (more secure than RSA)
- Protect private key: `chmod 600 ~/.ssh/id_ed25519`
- Rotate keys periodically
- Never share private keys

**Data Privacy:**
- Instances isolated in Docker containers
- No logging by vast.ai (self-hosted)
- Host providers range from datacenters to hobbyists
- **Recommendation:** Use verified datacenters for sensitive data

**Credential Management:**
- Use environment variables (not .env files)
- Use temporary credentials (AWS session tokens)
- Clean up credentials before destroying instance
- Never commit secrets to git

**Encryption:**
- SSH already encrypts (default)
- For extra security: GPG encrypt data before transfer
- Encrypt sensitive data at rest

---

## Recommendations for docling-testing Project

### Development Workflow

**1. Local Development:**
- Write code on Mac M1
- Test with small datasets
- Use pytest for unit tests
- Git commit frequently

**2. Vast.ai Production Runs:**
- Deploy to RTX 4090 (balanced cost/performance)
- Use interruptible for experimentation (<2 hours)
- Use on-demand for production training (>4 hours)
- Enable aggressive checkpointing (every 50 steps)
- Backup checkpoints to S3 every 10 minutes

**3. Instance Selection:**
- **OCR only:** RTX 3090 interruptible @ $0.09-$0.15/hr
- **Training only:** RTX 4090 interruptible @ $0.15-$0.30/hr
- **Combined:** RTX 4090 on-demand @ $0.25-$0.35/hr (reliability)

**4. Data Transfer:**
- Code via rsync (fast, incremental)
- PDFs via rsync (small corpus, <5GB)
- Models via S3 (large pre-trained weights)
- Results back via rsync (periodic backup)

**5. Environment:**
- Use uv package manager (10-100x faster than pip)
- Use PyTorch official Docker image
- Install Flash Attention 2 with ninja (3-5 min compile)
- Verify CUDA before starting job

**6. Monitoring:**
- Use screen for persistence
- TensorBoard for training metrics
- nvidia-smi for GPU utilization
- Periodic checkpoint downloads (every 30 minutes)

**7. Cost Management:**
- Estimated $0.50-$1.50 per complete workflow
- DESTROY instances immediately after downloading results
- Use interruptible for cost savings (when appropriate)
- Track spending: `vastai show instances`

### Deployment Automation

**Use Provided Script:**
```bash
# Search for instances
uv run python scripts/utilities/deploy_to_vastai.py --search training

# Deploy
uv run python scripts/utilities/deploy_to_vastai.py --mode training --instance-id 12345

# Script handles:
# - SSH connection setup
# - Code deployment (rsync)
# - Environment setup (uv, dependencies)
# - Flash Attention 2 installation
# - Helper script generation
```

**Helper Scripts Generated:**
- `vastai_ocr_helper.sh` - OCR workflow commands
- `vastai_training_helper.sh` - Training workflow commands

---

## Production Deployment Checklist

**Pre-Deployment:**
- [ ] Code tested locally
- [ ] Dependencies listed (pyproject.toml)
- [ ] Checkpointing implemented (every 50-100 steps)
- [ ] Logging implemented
- [ ] Data validated (checksums)

**Instance Selection:**
- [ ] Search: `vastai search offers 'reliability > 0.95 cuda_vers >= 12.4' -o 'dph+'`
- [ ] Verify GPU model (Ampere+ for Flash Attention 2)
- [ ] Choose rental type (on-demand or interruptible)
- [ ] Create instance

**Deployment:**
- [ ] Transfer code (rsync)
- [ ] Setup environment (uv sync)
- [ ] Verify CUDA (torch.cuda.is_available())
- [ ] Install Flash Attention 2 (if needed)
- [ ] Transfer data

**Execution:**
- [ ] Start screen/tmux session
- [ ] Setup GPU monitoring
- [ ] Start TensorBoard (optional)
- [ ] Start training
- [ ] Detach from session
- [ ] Setup checkpoint backup to S3

**Monitoring:**
- [ ] Check GPU utilization
- [ ] Check logs
- [ ] Check TensorBoard
- [ ] Check disk space
- [ ] Periodic checkpoint downloads

**Post-Job:**
- [ ] Download final model
- [ ] Download logs
- [ ] Download results
- [ ] Verify downloads
- [ ] DESTROY instance (stops billing)

---

## Additional Documentation

**Comprehensive Guides:**
- [VAST_AI_BEST_PRACTICES_2025.md](VAST_AI_BEST_PRACTICES_2025.md) - Full best practices guide (all 11 sections)
- [VAST_AI_DEPLOYMENT_GUIDE.md](VAST_AI_DEPLOYMENT_GUIDE.md) - Step-by-step deployment guide
- [VAST_AI_QUICK_REFERENCE.md](VAST_AI_QUICK_REFERENCE.md) - Quick reference cheat sheet
- [VASTAI_GPU_RENTAL_ANALYSIS.md](VASTAI_GPU_RENTAL_ANALYSIS.md) - Cost-benefit analysis

**Official Resources:**
- Vast.ai Docs: https://docs.vast.ai/
- Vast.ai Console: https://cloud.vast.ai/
- Vast.ai CLI: https://github.com/vast-ai/vast-cli

**Community Resources:**
- GitHub Guide: https://github.com/joystiller/vast-ai-guide
- Vast.ai Discord: https://discord.gg/vast

---

## Key Takeaways

1. **Setup is straightforward:** Install CLI, set API key, add SSH key, start instance
2. **Reliability matters:** Use reliability >0.95, verified datacenters for production
3. **Interruptible instances save 50-70%** but require aggressive checkpointing
4. **Stopped instances still cost money** - DESTROY when done
5. **Always use screen/tmux** - SSH disconnects are common
6. **Cloud storage is fastest** for large datasets (200-1000 MB/s)
7. **uv is 10-100x faster** than pip for dependency installation
8. **Flash Attention 2 requires Ampere+** GPUs (not Turing)
9. **Cost for docling-testing: $0.50-$1.50** per complete workflow
10. **ROI is immediate:** Saves $500-$3,000 in developer time vs Mac M1

---

**Last Updated:** 2025-10-24
**Author:** Claude Code (via web research and official documentation analysis)
**Project:** docling-testing

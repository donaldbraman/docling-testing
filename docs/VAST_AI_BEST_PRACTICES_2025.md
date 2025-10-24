# Vast.ai Best Practices for ML Workloads (2025)

**Last Updated:** 2025-10-24
**Purpose:** Consolidated best practices for deploying ML workloads to vast.ai GPU instances, based on official documentation, community guides, and 2024-2025 production deployments.

**Related Docs:**
- [VAST_AI_DEPLOYMENT_GUIDE.md](VAST_AI_DEPLOYMENT_GUIDE.md) - Complete step-by-step deployment guide
- [VAST_AI_QUICK_REFERENCE.md](VAST_AI_QUICK_REFERENCE.md) - Quick reference cheat sheet
- [VASTAI_GPU_RENTAL_ANALYSIS.md](VASTAI_GPU_RENTAL_ANALYSIS.md) - Cost-benefit analysis

---

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Instance Selection Strategy](#instance-selection-strategy)
3. [Docker and Container Best Practices](#docker-and-container-best-practices)
4. [Code Deployment Patterns](#code-deployment-patterns)
5. [Environment Setup](#environment-setup)
6. [Data Transfer Optimization](#data-transfer-optimization)
7. [Job Execution and Monitoring](#job-execution-and-monitoring)
8. [Cost Optimization Strategies](#cost-optimization-strategies)
9. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)
10. [Security Best Practices](#security-best-practices)
11. [Production Deployment Checklist](#production-deployment-checklist)

---

## 1. Initial Setup

### Account Creation and Configuration

**Step 1: Create Account**
- Sign up at https://cloud.vast.ai
- Minimum deposit: $5
- Payment methods: Credit card, cryptocurrency
- Account verification: Increases spending limits and access to premium hosts

**Step 2: Install CLI**
```bash
# Install via pip
pip install vastai

# Verify installation
vastai --version
```

**Step 3: Configure API Key**
```bash
# Get API key from https://cloud.vast.ai/console/cli/
# Copy the provided command, typically:
vastai set api-key xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Verify connection
vastai show instances
```

**API Key Security:**
- Stored in: `~/.vast_api_key` (keep secure)
- Alternative: Set `VAST_API_KEY` environment variable
- Never commit API keys to version control
- Rotate keys periodically for security

**Initial Configuration Checklist:**
- [ ] Account created and verified
- [ ] SSH key added at https://cloud.vast.ai/manage-keys/
- [ ] CLI installed and API key configured
- [ ] Test connection: `vastai show instances`
- [ ] Understand billing model (per-second, storage, bandwidth)

---

## 2. Instance Selection Strategy

### Understanding the Marketplace

**Host Types:**
- **Verified Datacenters:** ISO 27001 certified, Tier 3/4 compliance, DPAs signed
- **Unverified Hosts:** Individual hobbyists to small datacenters, variable reliability
- **Recommendation:** Use verified datacenters for production workloads

**Reliability Metrics:**
- **Reliability Score:** 0.0-1.0 (aim for >0.95)
- Based on: Historical disconnects, outages, errors
- Used in: Default 'auto' ranking
- Critical: Low reliability = high risk of interruption

### Search Strategy

**Basic Search (OCR Workloads):**
```bash
vastai search offers 'reliability > 0.95 cuda_vers >= 12.0 gpu_ram >= 16' -o 'dph+'
```

**Advanced Search (Training with Flash Attention 2):**
```bash
vastai search offers 'reliability > 0.95 cuda_vers >= 12.4 gpu_name ~ A100|RTX_4090|RTX_3090|H100 num_gpus=1' -o 'dph+'
```

**Multi-GPU Search:**
```bash
vastai search offers 'reliability > 0.95 cuda_vers >= 12.4 gpu_name ~ A100 num_gpus >= 2' -o 'dph+'
```

**Search Filters:**
- `reliability > 0.95` - Only reliable hosts
- `cuda_vers >= 12.4` - CUDA version minimum
- `gpu_ram >= 24` - Minimum VRAM
- `num_gpus = 1` - Exact GPU count
- `gpu_name ~ A100|RTX_4090` - Regex match GPU model
- `-o 'dph+'` - Sort by price (dollars per hour, ascending)

**Understanding DLPerf Score:**
- **DLPerf:** Deep Learning Performance score
- Approximate estimate for typical DL tasks
- Higher = better performance
- Use as relative comparison, not absolute metric

### Rental Types

**On-Demand (High Priority):**
- Fixed pricing set by host
- Guaranteed availability (no interruptions)
- 2-3x more expensive than interruptible
- Best for: Training jobs >4 hours, production workloads, critical deadlines

**Interruptible (Low Priority):**
- Bidding system (set your max bid price)
- Can be paused if outbid or on-demand rental created
- 50-70% cheaper than on-demand
- Best for: Experimentation, short jobs (<2 hours), fault-tolerant workloads

**Decision Matrix:**
| Workload Type | Duration | Recommended | Reason |
|--------------|----------|-------------|--------|
| Experimentation | Any | Interruptible | Cost savings, easy restart |
| Training (small model) | <2 hours | Interruptible | Low interruption risk |
| Training (large model) | >4 hours | On-Demand | Avoid losing progress |
| Production pipeline | Any | On-Demand | Reliability required |
| Checkpoint-heavy workflow | Any | Interruptible | Easy recovery from interruption |

### Cost-Performance Selection Guide

**For Your Use Case (DoclingBERT Training + OCR):**

| GPU Model | VRAM | Price/hr | Best For | Notes |
|-----------|------|----------|----------|-------|
| RTX 3090 | 24GB | $0.09-$0.20 | OCR only | Best price/performance for inference |
| RTX 4090 | 24GB | $0.15-$0.40 | OCR + Training | Flash Attn 2, handles both tasks |
| A100 40GB | 40GB | $0.73-$1.61 | Large-scale training | Maximum performance, higher cost |
| H100 | 80GB | $0.90-$2.00+ | Ultra-large models | Overkill for most use cases |

**Recommendation for docling-testing project:**
- **Development/Testing:** RTX 3090 interruptible @ $0.09-$0.15/hr
- **Production Runs:** RTX 4090 on-demand @ $0.25-$0.35/hr
- **Cost Estimate:** $0.50-$1.50 for complete OCR + training workflow

---

## 3. Docker and Container Best Practices

### Recommended Base Images (2025)

**1. Official PyTorch Images (Best for most use cases)**
```bash
# Latest: Python 3.12 + PyTorch 2.6 + CUDA 12.4 + cuDNN 9
pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel

# Stable: Python 3.11 + PyTorch 2.4 + CUDA 12.4
pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel
```

**Pros:**
- Official support from PyTorch team
- All dependencies included (CUDA, cuDNN, Python)
- Well-tested and regularly updated
- Comprehensive ML libraries pre-installed

**Cons:**
- Large image size (~10GB)
- May include unnecessary packages

**2. NVIDIA CUDA Base (For custom builds)**
```bash
# Runtime (smaller, production)
nvidia/cuda:12.4.0-cudnn9-runtime-ubuntu22.04

# Devel (includes compilation tools)
nvidia/cuda:12.4.0-cudnn9-devel-ubuntu22.04
```

**Use when:**
- Need specific Python version (e.g., 3.13)
- Want minimal image size
- Custom ML stack required

**3. AI-Dock Images (Optimized for vast.ai/runpod)**
```bash
# Check latest at: https://github.com/ai-dock/pytorch
ai-dock/pytorch:latest-cuda-12.4-python-3.11
```

**Pros:**
- Built-in vast.ai integration (TLS, auth, proxy)
- Includes common ML tools and Jupyter
- Optimized for cloud GPU platforms

**Cons:**
- Less official support
- Larger image size
- May have compatibility issues with some workflows

### Docker Configuration Best Practices

**Template Configuration (Web UI):**
```yaml
Docker Image: pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel
Disk Space: 50-100GB (depends on dataset size)
Launch Type: SSH (recommended) or Jupyter
On-start Script: /workspace/setup.sh (optional)
```

**Environment Variables:**
Vast.ai automatically sets:
- `CONTAINER_ID` - Unique instance identifier
- `CONTAINER_API_KEY` - Per-instance API key
- `DATA_DIRECTORY` - Default data location
- `VAST_CONTAINERLABEL` - Container label for identification
- `PYTORCH_VERSION` - PyTorch version (if applicable)

**Port Mapping:**
- SSH: Automatically configured
- Jupyter: Port 8080 (if using Jupyter template)
- TensorBoard: Forward port 6006 via SSH tunnel
- Custom services: Use SSH tunneling

### Custom Docker Images

**When to build custom images:**
- Specific Python version requirements (e.g., 3.13)
- Need reproducible environment across runs
- Complex dependency stack
- Frequently used configuration

**Building from Vast.ai Base Images:**
```dockerfile
# Use vast.ai base for built-in features
FROM vastai/base:latest

# Install custom dependencies
RUN apt-get update && apt-get install -y \
    ninja-build \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    flash-attn \
    easyocr \
    docling

# Set working directory
WORKDIR /workspace

# Copy application code (or use volume mount)
# COPY . /workspace/

# Entry point
CMD ["/bin/bash"]
```

**Using Custom Registry:**
- Vast.ai supports private Docker registries
- Configure credentials in instance settings
- Faster startup than building on instance

**Provisioning Scripts (Alternative to Custom Images):**
```bash
# Host script on GitHub/Gist
# Set PROVISIONING_SCRIPT env var to raw URL
# Example: https://gist.githubusercontent.com/user/hash/raw/setup.sh

#!/bin/bash
# setup.sh - Quick customization without rebuilding image

apt-get update && apt-get install -y ninja-build poppler-utils
pip install flash-attn easyocr --no-cache-dir
echo "Setup complete!"
```

**Best Practices:**
- Use `--no-cache-dir` with pip to save space
- Clean up apt cache: `rm -rf /var/lib/apt/lists/*`
- Multi-stage builds for smaller images
- Pin versions for reproducibility
- Test locally before deploying

---

## 4. Code Deployment Patterns

### Deployment Methods Comparison

| Method | Speed | Best For | Pros | Cons |
|--------|-------|----------|------|------|
| **rsync** | Fast (incremental) | Iterative development | Only transfers changes, resume support | Requires SSH access |
| **scp** | Medium (full copy) | One-time transfers | Simple, widely available | No incremental sync |
| **git clone** | Medium | Clean deployments | Version control, reproducible | Transfers .git history |
| **Cloud Storage** | Very fast | Large datasets | Highest bandwidth, parallel downloads | Setup overhead, costs |
| **vastai copy** | Fast | Quick transfers | Uses rsync internally, CLI integration | Limited flexibility |
| **Docker image** | Slow (first time) | Pre-configured environments | Everything bundled, reproducible | Large image size, slow pulls |

### Recommended: rsync for Code

**Basic rsync Command:**
```bash
# Get SSH details
vastai ssh-url <INSTANCE_ID>

# Transfer project (excluding large files)
rsync -avz -e "ssh -p <PORT>" \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git/' \
  --exclude='models/*/pytorch_model.bin' \
  --exclude='results/' \
  --exclude='archive*/' \
  /Users/donaldbraman/Documents/GitHub/docling-testing/ \
  root@<IP_ADDRESS>:/workspace/docling-testing/
```

**rsync Flags Explained:**
- `-a` - Archive mode (preserves permissions, symlinks, timestamps)
- `-v` - Verbose output (see what's being transferred)
- `-z` - Compress during transfer (saves bandwidth)
- `-e "ssh -p <PORT>"` - Specify SSH command with custom port
- `--exclude` - Skip matching files/directories
- `--partial` - Keep partial files (resume support)
- `--progress` - Show per-file progress
- `--delete` - Delete files on destination not in source (use carefully!)

**Incremental Sync Workflow:**
```bash
# Initial transfer (full)
rsync -avz -e "ssh -p <PORT>" --exclude='.venv' /local/project/ root@<IP>:/workspace/project/

# Make local changes, then sync only changes
rsync -avz -e "ssh -p <PORT>" --exclude='.venv' /local/project/ root@<IP>:/workspace/project/

# rsync automatically detects and transfers only changed files
```

**Performance Tips:**
```bash
# For many small files: Use compression
rsync -avz ...

# For few large files: Skip compression (faster)
rsync -av --no-compress ...

# For interrupted transfers: Enable resume
rsync -avz --partial --partial-dir=.rsync-partial ...

# Monitor progress
rsync -avz --progress ...

# Dry run (see what would be transferred)
rsync -avzn ...
```

### Git-Based Deployment

**When to use:**
- Want version control on instance
- Deploying to multiple instances (consistency)
- Collaborating with team
- Need rollback capability

**Basic workflow:**
```bash
# SSH into instance
ssh -p <PORT> root@<IP>

# Clone repository
cd /workspace
git clone https://github.com/user/docling-testing.git

# Checkout specific branch
cd docling-testing
git checkout feature/issue-42-text-block-matching

# Pull updates later
git pull origin feature/issue-42-text-block-matching
```

**Optimization for large repos:**
```bash
# Shallow clone (faster, saves space)
git clone --depth 1 https://github.com/user/docling-testing.git

# Sparse checkout (only specific directories)
git clone --no-checkout https://github.com/user/docling-testing.git
cd docling-testing
git sparse-checkout init --cone
git sparse-checkout set scripts data
git checkout main
```

**Handling large files:**
- Use Git LFS for models, datasets
- Or: Use separate data transfer method (rsync, cloud storage)
- Avoid committing large binaries to git

### Cloud Storage for Large Datasets

**When to use:**
- Datasets >10GB
- Shared data across multiple instances
- Permanent backup needed
- Maximum transfer speed required

**AWS S3:**
```bash
# Install AWS CLI (on instance)
apt-get install -y awscli
aws configure  # Enter credentials

# Upload from local machine
aws s3 sync data/v3_data/raw_pdf/ s3://your-bucket/raw_pdf/ --region us-west-2

# Download on instance
aws s3 sync s3://your-bucket/raw_pdf/ /workspace/data/v3_data/raw_pdf/

# Parallel downloads (faster)
aws s3 sync s3://your-bucket/raw_pdf/ /workspace/data/ --region us-west-2 --no-progress
```

**Google Cloud Storage:**
```bash
# Install gsutil (on instance)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init  # Authenticate

# Upload from local
gsutil -m cp -r data/v3_data/raw_pdf/ gs://your-bucket/raw_pdf/

# Download on instance
gsutil -m cp -r gs://your-bucket/raw_pdf/ /workspace/data/v3_data/raw_pdf/
```

**Direct HTTPS Download:**
```bash
# For public URLs
wget -r -np -nH --cut-dirs=2 https://your-cdn.com/datasets/raw_pdf/

# With authentication
wget --http-user=user --http-password=pass https://example.com/data.tar.gz
```

**Bandwidth Optimization:**
- **Colocation:** Use same cloud region as vast.ai host (if known)
- **Parallel transfers:** Use `-m` flag (gsutil) or `aws s3 sync` (automatic)
- **Compression:** Compress before upload, decompress on instance
- **Cost:** AWS S3 egress $0.09/GB, GCS $0.12/GB (check current rates)

### Hybrid Approach (Recommended)

**Best practice for docling-testing project:**

1. **Code via rsync:** Fast iterative development
   ```bash
   rsync -avz -e "ssh -p <PORT>" --exclude='.venv' --exclude='data/' --exclude='models/' \
     /local/docling-testing/ root@<IP>:/workspace/docling-testing/
   ```

2. **Small data via rsync:** PDFs, configs, scripts
   ```bash
   rsync -avz -e "ssh -p <PORT>" /local/docling-testing/data/v3_data/raw_pdf/ \
     root@<IP>:/workspace/docling-testing/data/v3_data/raw_pdf/
   ```

3. **Large models via cloud storage:** Pre-trained weights, checkpoints
   ```bash
   aws s3 sync s3://bucket/models/ /workspace/models/
   ```

4. **Results back via rsync:** Periodic backup
   ```bash
   rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/results/ /local/results/
   ```

---

## 5. Environment Setup

### Python Environment Managers

**Option 1: uv (Recommended for docling-testing)**

**Why uv:**
- 10-100x faster than pip
- Automatic virtual environment management
- Deterministic dependency resolution
- Built-in Python version management
- Zero config for Docker containers

**Installation:**
```bash
# Inside instance
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Verify
uv --version
```

**Usage:**
```bash
cd /workspace/docling-testing

# Install dependencies (auto-creates venv)
uv sync

# Run commands (auto-activates venv)
uv run python scripts/training/train_modernbert_classifier.py

# Add package
uv add flash-attn

# Install specific Python version
uv python install 3.13
uv python pin 3.13
```

**Docker container optimization:**
```bash
# In Dockerfile, set UV_PROJECT_ENVIRONMENT to system Python
ENV UV_PROJECT_ENVIRONMENT=/usr/local

# Now `uv run` uses system Python (no venv overhead)
# Perfect for Docker's isolated environment
```

**Option 2: pip + venv (Traditional)**

**Usage:**
```bash
cd /workspace/docling-testing

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
# OR
pip install -e .  # If using pyproject.toml

# Run commands
python scripts/training/train_modernbert_classifier.py
```

**Option 3: conda (For complex dependencies)**

**When to use:**
- Need specific Python version
- Complex C/C++ dependencies
- Scientific computing packages (NumPy, SciPy with MKL)

**Installation:**
```bash
# Install miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda
eval "$($HOME/miniconda/bin/conda shell.bash hook)"

# Create environment
conda create -n docling python=3.11
conda activate docling

# Install PyTorch with CUDA
conda install pytorch torchvision pytorch-cuda=12.4 -c pytorch -c nvidia
```

**Best Practice Recommendation:**
- **uv:** For modern Python projects with pyproject.toml
- **pip + venv:** For simple requirements.txt projects
- **conda:** Only when necessary (slower, larger)

### CUDA and PyTorch Setup

**Verify CUDA:**
```bash
# Check CUDA version
nvcc --version

# Check installed drivers
nvidia-smi

# Expected output:
# CUDA Version: 12.4
# Driver Version: 535.xx or higher
```

**Verify PyTorch CUDA:**
```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}'); print(f'cuDNN version: {torch.backends.cudnn.version()}')"

# Expected output:
# PyTorch: 2.6.0
# CUDA available: True
# CUDA version: 12.4
# cuDNN version: 90100
```

**Installing PyTorch (if needed):**
```bash
# For CUDA 12.4
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# For CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Flash Attention 2 Installation

**Requirements:**
- GPU: Ampere (8.0+), Ada (8.9), or Hopper (9.0) - NO Turing (7.5)
- CUDA: 12.0+ (12.4+ recommended)
- PyTorch: 2.2+ (2.6+ recommended)

**Verify GPU Compatibility:**
```bash
nvidia-smi --query-gpu=name,compute_cap --format=csv

# Compatible:
# A100: 8.0 (Ampere)
# RTX 3090: 8.6 (Ampere)
# RTX 4090: 8.9 (Ada)
# H100: 9.0 (Hopper)

# NOT Compatible:
# T4: 7.5 (Turing)
# RTX 2080: 7.5 (Turing)
```

**Installation (Fast Method with ninja):**
```bash
# Install ninja for 50-100x faster compilation
apt-get update && apt-get install -y ninja-build

# Install Flash Attention 2
pip install flash-attn --no-build-isolation

# Time: 3-5 minutes with ninja, 60-120 minutes without
```

**Installation (Memory-Limited Machines):**
```bash
# Limit parallel compilation jobs
MAX_JOBS=4 pip install flash-attn --no-build-isolation

# For 16GB RAM machines, use MAX_JOBS=2
```

**Verification:**
```bash
python -c "import flash_attn; print(f'Flash Attention: {flash_attn.__version__}')"

# Expected: 2.x.x (latest as of 2025: 2.7.0+)
```

**Troubleshooting:**
```bash
# If fails: "nvcc not found"
apt-get install -y cuda-toolkit-12-4

# If fails: "RuntimeError: Flash Attention requires Ampere or newer"
# Solution: Use different GPU (must be Ampere/Ada/Hopper)

# If fails: Compilation timeout
# Solution: Increase MAX_JOBS or use pre-compiled wheel
```

---

## 6. Data Transfer Optimization

### Understanding Vast.ai Network Architecture

**Three Connection Types:**

1. **Default SSH Proxy:**
   - Latency: High (300-500ms)
   - Bandwidth: Moderate (10-50 MB/s)
   - Cost: Free (no bandwidth charges for proxy)
   - Use for: Small files (<1GB), interactive SSH sessions

2. **Direct SSH Connection:**
   - Latency: Low (10-50ms)
   - Bandwidth: High (50-200 MB/s)
   - Cost: Bandwidth charges apply
   - Use for: Large file transfers (1-10GB)
   - Setup: Requires Wireguard VPN (see vast.ai docs)

3. **Cloud Storage Direct:**
   - Latency: Very low (<10ms within region)
   - Bandwidth: Very high (200-1000 MB/s)
   - Cost: Cloud egress charges ($0.09-$0.12/GB)
   - Use for: Very large datasets (>10GB)

### Bandwidth Cost Optimization

**Pricing:**
- Instance-to-instance (same host): FREE
- Instance-to-instance (same datacenter): FREE or very low cost
- Instance-to-internet: Variable ($0.01-$0.10/GB depending on host)
- Proxy SSH connection: FREE (no bandwidth charges)

**Strategies:**

1. **Use proxy for small transfers:**
   ```bash
   scp -P <PORT> file.py root@<IP>:/workspace/  # Via proxy (free)
   ```

2. **Compress before transfer:**
   ```bash
   # Local: Compress
   tar -czf project.tar.gz docling-testing/

   # Transfer compressed (saves bandwidth)
   scp -P <PORT> project.tar.gz root@<IP>:/workspace/

   # Instance: Decompress
   ssh -p <PORT> root@<IP> "cd /workspace && tar -xzf project.tar.gz"
   ```

3. **Use cloud storage for large datasets:**
   ```bash
   # No bandwidth charges between instance and S3 (within same region)
   aws s3 sync s3://bucket/data/ /workspace/data/
   ```

4. **Copy between instances on same host:**
   ```bash
   # If running multiple instances on same physical host
   vastai copy <SRC_INSTANCE_ID>:/path/data <DST_INSTANCE_ID>:/path/data
   # FREE - no internet bandwidth used
   ```

### Transfer Performance Optimization

**For Many Small Files:**
```bash
# Compress first (huge speedup)
tar -czf files.tar.gz directory/
scp -P <PORT> files.tar.gz root@<IP>:/workspace/
ssh -p <PORT> root@<IP> "cd /workspace && tar -xzf files.tar.gz"

# Alternative: rsync with compression
rsync -avz -e "ssh -p <PORT>" directory/ root@<IP>:/workspace/directory/
```

**For Few Large Files:**
```bash
# Skip compression (CPU overhead not worth it)
rsync -av --no-compress -e "ssh -p <PORT>" large_file.bin root@<IP>:/workspace/

# Use parallel transfers (if multiple files)
parallel -j 4 "scp -P <PORT> {} root@<IP>:/workspace/" ::: *.bin
```

**For Resumed Transfers (Unreliable Connection):**
```bash
# rsync automatically resumes
rsync -avz --partial --partial-dir=.rsync-partial -e "ssh -p <PORT>" \
  large_file.bin root@<IP>:/workspace/

# If connection drops, re-run same command (resumes from last partial chunk)
```

**For Maximum Speed:**
```bash
# Disable encryption (only if on trusted network)
rsync -avz -e "ssh -p <PORT> -c aes128-ctr" directory/ root@<IP>:/workspace/
# Note: aes128-ctr is faster than default aes256-gcm
```

### Monitoring Transfer Progress

**Real-time progress:**
```bash
# rsync with progress bar
rsync -avz --progress -e "ssh -p <PORT>" directory/ root@<IP>:/workspace/

# scp with verbose output
scp -v -P <PORT> file.bin root@<IP>:/workspace/
```

**Network utilization:**
```bash
# On instance, monitor network usage
watch -n 1 'iftop -t -s 1'

# Or simpler:
watch -n 1 'ifstat 1 1'
```

**Bandwidth estimation:**
```bash
# Test upload speed
time scp -P <PORT> test_100mb.bin root@<IP>:/tmp/

# Calculate: 100 MB / seconds = MB/s
# Example: 100 MB in 5 seconds = 20 MB/s
```

---

## 7. Job Execution and Monitoring

### Persistent Sessions (Critical)

**Why persistent sessions:**
- SSH disconnects don't kill your job
- Log out and come back later
- Survive network interruptions
- Monitor from multiple terminals

**Option 1: screen (Simpler)**

```bash
# Create named session
screen -S training

# Run your job
uv run python scripts/training/train_modernbert_classifier.py

# Detach (job keeps running)
# Press: Ctrl+A, then D

# Reattach later
screen -r training

# List sessions
screen -ls

# Kill session (from inside)
# Press: Ctrl+A, then K, then Y
```

**Option 2: tmux (More powerful)**

```bash
# Create named session
tmux new -s training

# Run your job
uv run python scripts/training/train_modernbert_classifier.py

# Detach (job keeps running)
# Press: Ctrl+B, then D

# Reattach later
tmux attach -t training

# List sessions
tmux ls

# Kill session
tmux kill-session -t training
```

**tmux with GPU monitoring:**
```bash
# Split window horizontally
# Ctrl+B, then "

# Top pane: Training
uv run python scripts/training/train.py

# Bottom pane: GPU monitoring
watch -n 1 nvidia-smi

# Navigate between panes: Ctrl+B, then arrow keys
```

**Option 3: nohup (Simplest, no reattach)**

```bash
# Start job in background
nohup uv run python scripts/training/train.py > training.log 2>&1 &

# Monitor progress
tail -f training.log

# Check if still running
ps aux | grep python

# Kill job
pkill -f train.py
```

**Recommendation:**
- **Interactive debugging:** tmux (split screens, easy navigation)
- **Fire-and-forget:** nohup (simplest, lightweight)
- **Remote monitoring:** screen (easier reattachment)

### GPU Monitoring Tools

**nvidia-smi (Basic):**
```bash
# Single query
nvidia-smi

# Continuous monitoring (every 2 seconds)
watch -n 2 nvidia-smi

# Continuous with custom columns
nvidia-smi dmon -s pucvmet -d 2
# p=power, u=utilization, c=clock, v=voltage, m=memory, e=ecc, t=temp

# Log to file
nvidia-smi --query-gpu=timestamp,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.free \
  --format=csv -l 10 > gpu_stats.csv &
```

**nvtop (Interactive, User-Friendly):**
```bash
# Install
apt-get install -y nvtop

# Run
nvtop

# Features:
# - Real-time GPU utilization graphs
# - Process list with GPU memory usage
# - Color-coded display
# - Interactive interface (sort, filter)
```

**nvitop (Modern, Feature-Rich):**
```bash
# Install
pip install nvitop

# Run
nvitop

# Features:
# - Combines nvidia-smi + htop interface
# - Process tree view
# - GPU memory timeline
# - Integration with ML frameworks (shows training progress)
```

**gpustat (Minimal, Scriptable):**
```bash
# Install
pip install gpustat

# Run once
gpustat

# Watch mode
gpustat -i 2

# With process details
gpustat -cpu -a

# Machine-readable JSON
gpustat --json
```

**In-Script GPU Monitoring:**
```python
import torch

def log_gpu_memory():
    """Log GPU memory usage during training."""
    allocated = torch.cuda.memory_allocated() / 1e9  # GB
    reserved = torch.cuda.memory_reserved() / 1e9
    max_allocated = torch.cuda.max_memory_allocated() / 1e9

    print(f"GPU Memory: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved, {max_allocated:.2f}GB peak")

    # Reset peak stats
    torch.cuda.reset_peak_memory_stats()

# Call periodically during training
# Example: After each epoch or every N steps
```

### Training Monitoring

**TensorBoard:**
```bash
# On instance, start TensorBoard
tensorboard --logdir /workspace/logs --port 6006 --bind_all

# From local machine, forward port
ssh -p <PORT> root@<IP> -L 6006:localhost:6006

# Open in browser
http://localhost:6006
```

**Log Files:**
```bash
# Real-time log monitoring
tail -f training.log

# Search logs
grep "loss=" training.log | tail -20
grep "eval_" training.log

# Extract metrics
grep "loss=" training.log | awk '{print $NF}' > losses.txt
```

**Progress Tracking:**
```python
# In training script, save progress periodically
import json
from pathlib import Path
from datetime import datetime

def save_progress(epoch, step, metrics, output_file="/workspace/logs/progress.json"):
    progress = {
        "epoch": epoch,
        "step": step,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    }
    Path(output_file).write_text(json.dumps(progress, indent=2))

# Monitor from another terminal
watch -n 10 "cat /workspace/logs/progress.json"
```

**Alerts (Simple):**
```bash
# Email alert when training completes (if mail configured)
uv run python train.py && echo "Training complete!" | mail -s "Training Done" you@example.com

# Slack webhook alert
uv run python train.py && curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Training complete!"}' \
  https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Checkpointing Best Practices

**Automatic Checkpointing (HuggingFace Trainer):**
```python
from transformers import TrainingArguments

training_args = TrainingArguments(
    output_dir="/workspace/models/modernbert-v3",

    # Checkpoint strategy
    save_strategy="steps",
    save_steps=100,  # Save every 100 steps
    save_total_limit=3,  # Keep only 3 best checkpoints (saves disk space)

    # Recovery
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    resume_from_checkpoint=True,  # Auto-resume if checkpoint exists
)
```

**Cloud Backup (Critical for Interruptible Instances):**
```bash
# Setup AWS CLI
apt-get install -y awscli
aws configure

# Continuous checkpoint backup (run in background)
cat > /workspace/sync_checkpoints.sh << 'EOF'
#!/bin/bash
while true; do
    aws s3 sync /workspace/models/ s3://your-bucket/vast-ai-training/models/ \
        --exclude "*" --include "checkpoint-*/*" --include "*.json"
    sleep 600  # Every 10 minutes
done
EOF

chmod +x /workspace/sync_checkpoints.sh
nohup /workspace/sync_checkpoints.sh > sync.log 2>&1 &
```

**Recovery After Interruption:**
```bash
#!/bin/bash
# recovery.sh - Run this if instance is interrupted

# Download latest checkpoint from S3
echo "Downloading latest checkpoint..."
aws s3 sync s3://your-bucket/vast-ai-training/models/ /workspace/models/ \
    --exclude "*" --include "checkpoint-*/*"

# Find latest checkpoint
LATEST_CHECKPOINT=$(ls -td /workspace/models/checkpoint-* | head -1)
echo "Latest checkpoint: $LATEST_CHECKPOINT"

# Resume training
echo "Resuming training..."
uv run python scripts/training/train_modernbert_classifier.py \
    --resume-from-checkpoint "$LATEST_CHECKPOINT" \
    --output-dir /workspace/models/modernbert-v3
```

---

## 8. Cost Optimization Strategies

### Minimize Billable Time

**1. Prepare Locally**
```bash
# Test code locally before deploying (catch bugs early)
uv run pytest tests/

# Verify data integrity
md5sum data/v3_data/raw_pdf/*.pdf > checksums.txt

# Pre-package data
tar -czf data.tar.gz data/
```

**2. Use Pre-Built Docker Images**
```bash
# Instead of building on instance, use official images
pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel

# Or build locally and push to Docker Hub
docker build -t username/docling-training:latest .
docker push username/docling-training:latest

# On vast.ai, pull pre-built image (faster startup)
vastai create instance <ID> --image username/docling-training:latest
```

**3. Optimize Data Transfer**
```bash
# Use cloud storage for large datasets (much faster than rsync)
aws s3 sync s3://bucket/data/ /workspace/data/

# Compress before transfer
tar -czf project.tar.gz docling-testing/
scp -P <PORT> project.tar.gz root@<IP>:/workspace/
```

**4. Auto-Stop on Completion**
```python
# Add to end of training script
if __name__ == "__main__":
    train()  # Your training function

    # Auto-stop instance after training
    import subprocess
    import os
    instance_id = os.environ.get("CONTAINER_ID")
    if instance_id:
        subprocess.run(["vastai", "stop", "instance", instance_id])
```

### Storage Optimization

**Critical: Storage costs apply even when stopped!**

**1. Request Only Needed Disk Space**
```bash
# OCR workload: 50GB sufficient
vastai create instance <ID> --disk 50

# Training workload: 100GB typical
vastai create instance <ID> --disk 100

# Don't request 500GB if you only need 100GB
```

**2. Clean Up During Training**
```python
# In training script, remove old checkpoints
import shutil

# After saving new checkpoint
if step % 100 == 0 and step > 300:
    old_checkpoint = f"/workspace/models/checkpoint-{step-300}"
    if os.path.exists(old_checkpoint):
        shutil.rmtree(old_checkpoint)
        print(f"Removed old checkpoint: {old_checkpoint}")
```

**3. Delete Instance Immediately After**
```bash
# Download results
rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/results/ /local/results/

# Verify download
ls -lh /local/results/

# DESTROY instance (stops billing)
vastai destroy instance <INSTANCE_ID>

# Don't just STOP - you're still charged storage costs!
```

### Instance Selection Optimization

**Price vs Performance:**

| Workload | Budget Option | Balanced Option | Performance Option |
|----------|---------------|-----------------|-------------------|
| OCR | RTX 3090 @ $0.09/hr | RTX 3090 @ $0.15/hr | A100 @ $0.80/hr |
| Training | RTX 3090 @ $0.15/hr | RTX 4090 @ $0.30/hr | A100 @ $1.20/hr |
| Hyperparameter Search | Interruptible RTX 3090 | Interruptible RTX 4090 | On-Demand A100 |

**Interruptible Savings:**
- 50-70% cheaper than on-demand
- Use for: Short jobs, experimentation, fault-tolerant workloads
- Risk: Can be interrupted (mitigate with aggressive checkpointing)

**Decision Matrix:**
```
If job_duration < 2 hours AND checkpointing_available:
    Use interruptible instance (50% savings)
elif job_duration > 4 hours OR critical_deadline:
    Use on-demand instance (reliability)
else:
    Use interruptible with frequent checkpointing (balanced)
```

### Multi-Instance Strategies

**Parallel Processing (OCR):**
```bash
# Split 100 PDFs across 4 RTX 3090 instances
# Total time: 1 hour vs 4 hours sequential
# Cost: 4 × $0.15 × 1 = $0.60 vs 1 × $0.15 × 4 = $0.60 (same!)
# Benefit: Results in 1 hour instead of 4

# Launch 4 instances
for i in {1..4}; do
    vastai create instance <ID> --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel --disk 50
done

# Distribute workload
# Instance 1: PDFs 1-25
# Instance 2: PDFs 26-50
# Instance 3: PDFs 51-75
# Instance 4: PDFs 76-100
```

**Hyperparameter Search:**
```bash
# Test 5 different learning rates in parallel
# Sequential: 5 × 2 hours = 10 hours @ $0.30/hr = $3.00
# Parallel: 1 × 2 hours × 5 instances @ $0.30/hr = $3.00 (same cost, 5x faster)

# Launch 5 instances with different configs
for lr in 1e-5 2e-5 5e-5 1e-4 2e-4; do
    vastai create instance <ID> --env "-e LEARNING_RATE=$lr" ...
done
```

### Cost Monitoring

**Track Spending:**
```bash
# Show current instances with costs
vastai show instances

# Calculate total cost (manual)
# cost = dph_total × (elapsed_hours)

# Set budget alerts (manual spreadsheet)
# Or use cron job to check costs periodically
crontab -e
# Add: 0 * * * * /home/user/check_vast_costs.sh
```

**Estimated Costs for docling-testing:**

| Task | GPU | Duration | Interruptible | On-Demand |
|------|-----|----------|---------------|-----------|
| OCR 50 PDFs | RTX 3090 | 2 hours | $0.18-$0.30 | $0.30-$0.40 |
| Train ModernBERT | RTX 4090 | 0.5 hours | $0.08-$0.15 | $0.15-$0.20 |
| Hyperparameter Search (5 runs) | RTX 4090 | 2.5 hours | $0.40-$0.75 | $0.75-$1.00 |
| **TOTAL** | - | 5 hours | **$0.66-$1.20** | **$1.20-$1.60** |

**ROI Analysis:**
- Local Mac M1: 10-20 hours @ $50-150/hr value = $500-$3,000
- Vast.ai: 5 hours actual, $1.00 GPU cost = $1.00
- **Savings: $499-$2,999 in developer time**

---

## 9. Common Pitfalls and Solutions

### 1. Flash Attention 2 Installation Fails

**Problem:** `ModuleNotFoundError: No module named 'flash_attn_2_cuda'`

**Causes:**
- CUDA toolkit not installed
- Incompatible GPU (Turing or older)
- Insufficient memory during compilation

**Solutions:**
```bash
# Ensure CUDA toolkit installed
nvcc --version
# If not found:
apt-get install -y cuda-toolkit-12-4

# Reinstall with limited jobs (if OOM during compile)
MAX_JOBS=4 pip install flash-attn --no-build-isolation

# Verify GPU compatibility
nvidia-smi --query-gpu=compute_cap --format=csv
# Must be 8.0+ (Ampere, Ada, Hopper)
# If 7.5 (Turing), Flash Attention 2 NOT supported - use different GPU
```

**Prevention:**
- Choose Ampere/Ada/Hopper GPUs only (RTX 3090+, A100, H100)
- Avoid T4, RTX 2080 Ti (Turing architecture)
- Install ninja before Flash Attention: `apt-get install -y ninja-build`

### 2. CUDA Out of Memory (OOM)

**Problem:** `RuntimeError: CUDA out of memory`

**Immediate Solutions:**
```python
# 1. Reduce batch size
per_device_train_batch_size=8  # Instead of 16

# 2. Enable gradient checkpointing (trades compute for memory)
model.gradient_checkpointing_enable()

# 3. Reduce max sequence length
max_length=256  # Instead of 512

# 4. Use gradient accumulation (effective batch size stays same)
gradient_accumulation_steps=4  # batch_size=8, effective=32

# 5. Use mixed precision (FP16/BF16)
training_args.fp16=True  # Ampere GPUs
# OR
training_args.bf16=True  # Ampere+ (better numerical stability)

# 6. Clear cache between batches
import torch
torch.cuda.empty_cache()
```

**Prevention:**
- Start with small batch size, increase gradually
- Monitor GPU memory: `nvidia-smi`
- Use GPU with more VRAM (A100 40GB vs RTX 3090 24GB)

### 3. Instance Disk Full

**Problem:** `/workspace` disk full during training

**Detection:**
```bash
df -h  # Check disk usage
du -sh /workspace/*  # Find large directories
```

**Solutions:**
```bash
# 1. Remove old checkpoints
rm -rf /workspace/models/*/checkpoint-{100..400}

# 2. Keep only N best checkpoints
ls -t /workspace/models/*/checkpoint-* | tail -n +4 | xargs rm -rf

# 3. Clear pip cache
rm -rf ~/.cache/pip

# 4. Clear apt cache
apt-get clean
rm -rf /var/lib/apt/lists/*

# 5. Remove temporary files
rm -rf /tmp/*
find /workspace -name "__pycache__" -type d -exec rm -rf {} +
```

**Prevention:**
```python
# In TrainingArguments, limit checkpoints
save_total_limit=3  # Keep only 3 best

# Or manually delete old checkpoints in training loop
if step % 100 == 0 and step > 300:
    shutil.rmtree(f"checkpoint-{step-300}", ignore_errors=True)
```

### 4. SSH Connection Lost, Job Stops

**Problem:** SSH disconnects, training process dies

**Prevention:**
```bash
# ALWAYS use screen, tmux, or nohup
# Never run long jobs directly in SSH session

# Screen (recommended)
screen -S training
uv run python train.py
# Detach: Ctrl+A, D

# tmux
tmux new -s training
uv run python train.py
# Detach: Ctrl+B, D

# nohup
nohup uv run python train.py > training.log 2>&1 &
```

**Recovery:**
- Reattach to session: `screen -r training` or `tmux attach -t training`
- Check if job still running: `ps aux | grep python`
- If stopped, resume from checkpoint (if saved)

### 5. Slow Data Transfer

**Problem:** rsync/scp very slow (1-5 MB/s)

**Causes:**
- Using proxy connection (inherently slow)
- Network congestion
- Small files (overhead per file)

**Solutions:**
```bash
# 1. Use cloud storage for large datasets
aws s3 sync s3://bucket/data/ /workspace/data/  # 100-500 MB/s

# 2. Compress many small files
tar -czf data.tar.gz data/
scp -P <PORT> data.tar.gz root@<IP>:/workspace/
ssh -p <PORT> root@<IP> "cd /workspace && tar -xzf data.tar.gz"

# 3. Use parallel transfers
parallel -j 4 "scp -P <PORT> {} root@<IP>:/workspace/" ::: *.pdf

# 4. Enable compression for text files
rsync -avz -e "ssh -p <PORT>" ...  # -z compresses
```

### 6. Python Version Mismatch

**Problem:** Project requires Python 3.13, instance has 3.11

**Solutions:**
```bash
# Option 1: Use uv to install Python 3.13
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
uv python install 3.13
uv python pin 3.13
uv run python --version  # Should show 3.13.x

# Option 2: Use pyenv
curl https://pyenv.run | bash
pyenv install 3.13.0
pyenv global 3.13.0

# Option 3: Use Docker image with Python 3.13
# Build custom image: FROM python:3.13-slim
```

**Prevention:**
- Choose Docker image with correct Python version
- Or use NVIDIA base + install Python: `FROM nvidia/cuda:12.4.0-cudnn9-runtime-ubuntu22.04`

### 7. EasyOCR Not Using GPU

**Problem:** EasyOCR running on CPU (very slow)

**Detection:**
```bash
nvidia-smi  # GPU utilization 0% during OCR
```

**Solutions:**
```python
# 1. Explicitly enable GPU
import easyocr
reader = easyocr.Reader(['en'], gpu=True)

# 2. Verify CUDA available
import torch
assert torch.cuda.is_available(), "CUDA not available!"

# 3. Check GPU usage
import easyocr
reader = easyocr.Reader(['en'], gpu=True, verbose=True)
# Should print: "Using GPU: True"

# 4. Reinstall PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

### 8. Training Stops Without Error

**Problem:** Training process silently stops

**Causes:**
- Instance interrupted (interruptible instance outbid)
- OOM killer (system ran out of memory)
- Host machine crashed

**Detection:**
```bash
# Check if process still running
ps aux | grep python

# Check system logs
dmesg | tail -50  # Look for OOM killer messages

# Check instance status
vastai show instances  # Status: "running" or "stopped"
```

**Prevention:**
```bash
# 1. Use on-demand instances for long jobs
vastai create instance <ID> --ondemand

# 2. Implement aggressive checkpointing
save_steps=50  # Save every 50 steps

# 3. Backup checkpoints to cloud storage
# (See section 7: Checkpointing)

# 4. Monitor instance status
watch -n 60 'vastai show instances | grep <ID>'

# 5. Set up alerts
# Email or Slack notification when instance stops
```

**Recovery:**
```bash
# 1. Check if checkpoint exists
ls -lh /workspace/models/checkpoint-*

# 2. If no checkpoint, check S3 backup
aws s3 ls s3://bucket/models/

# 3. Resume from latest checkpoint
uv run python train.py --resume-from-checkpoint /workspace/models/checkpoint-300
```

---

## 10. Security Best Practices

### SSH Key Management

**Setup:**
```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add public key to vast.ai
# Go to: https://cloud.vast.ai/manage-keys/
# Paste contents of ~/.ssh/id_ed25519.pub

# Test SSH connection
ssh -p <PORT> root@<IP>
```

**Best Practices:**
- Use ed25519 keys (more secure than RSA)
- Protect private key: `chmod 600 ~/.ssh/id_ed25519`
- Use SSH agent: `ssh-add ~/.ssh/id_ed25519`
- Don't share private keys
- Rotate keys periodically

**Multiple Keys:**
```bash
# Create vast-specific key
ssh-keygen -t ed25519 -f ~/.ssh/vast_ai_key

# Add to SSH config
cat >> ~/.ssh/config << EOF
Host vast-*
    IdentityFile ~/.ssh/vast_ai_key
    User root
EOF

# Connect without specifying key
ssh -p <PORT> vast-<IP>
```

### Data Privacy and Security

**Understanding Vast.ai Security Model:**

**Isolation:**
- Instances run in unprivileged Docker containers
- No access to host system or other containers
- Separate network namespace

**Data Privacy:**
- No logging by vast.ai (self-hosted instances)
- Data stays on instance (not accessible by vast.ai)
- Host providers range from datacenters to hobbyists

**Recommendations for Sensitive Data:**

1. **Use Verified Datacenters:**
   ```bash
   # Filter for secure datacenters only
   vastai search offers 'secure_cloud=True' ...
   ```

2. **Encrypt Data at Rest:**
   ```bash
   # Encrypt before uploading
   tar -czf data.tar.gz data/
   gpg -c data.tar.gz  # Encrypts with passphrase

   # Upload encrypted archive
   scp -P <PORT> data.tar.gz.gpg root@<IP>:/workspace/

   # Decrypt on instance
   ssh -p <PORT> root@<IP> "gpg -d /workspace/data.tar.gz.gpg | tar -xzf -"
   ```

3. **Encrypt Data in Transit:**
   - SSH already encrypts (default)
   - For extra paranoia, use GPG encryption before transfer

4. **Avoid Uploading Credentials:**
   ```bash
   # Never upload .env files with secrets
   # Use environment variables instead
   vastai create instance <ID> --env "-e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=..."

   # Or: Set env vars via SSH after instance starts
   ssh -p <PORT> root@<IP> "export AWS_ACCESS_KEY_ID=... && python script.py"
   ```

### Credential Management

**Best Practices:**

**1. Use Environment Variables:**
```bash
# Set via instance creation
vastai create instance <ID> --env "-e HUGGINGFACE_TOKEN=hf_xxx -e AWS_ACCESS_KEY_ID=xxx"

# Or set after SSH
export HUGGINGFACE_TOKEN=hf_xxx
export AWS_ACCESS_KEY_ID=xxx
python script.py
```

**2. Use Temporary Credentials:**
```bash
# AWS: Use temporary session tokens (expire after 1-12 hours)
aws sts get-session-token --duration-seconds 3600

# Use returned temporary credentials (safer than long-term keys)
```

**3. Clean Up After Job:**
```bash
# Delete credentials before destroying instance
rm -f /workspace/.env
rm -f ~/.aws/credentials
rm -f ~/.huggingface/token

# Or just destroy instance (data deleted automatically)
vastai destroy instance <ID>
```

**4. Never Commit Secrets:**
```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo ".aws/" >> .gitignore
echo "*.pem" >> .gitignore

# Check for accidentally committed secrets
git log -p | grep -i "api_key\|password\|secret"
```

### Monitoring and Auditing

**Track Instance Usage:**
```bash
# Log instance creation
vastai show instances > instance_log_$(date +%Y%m%d).txt

# Monitor spending
vastai show instances --format json | jq '.[] | {id, dph_total, elapsed, cost: (.dph_total * .elapsed)}'

# Set up alerts (manual or via cron)
if [ $(vastai show instances --format json | jq '.[].dph_total * .[].elapsed') -gt 5 ]; then
    echo "Warning: Spending exceeds $5" | mail -s "Vast.ai Alert" you@example.com
fi
```

---

## 11. Production Deployment Checklist

### Pre-Deployment

**Code Preparation:**
- [ ] Code tested locally
- [ ] Dependencies listed in pyproject.toml or requirements.txt
- [ ] No hardcoded paths (use environment variables or CLI args)
- [ ] Logging implemented (print statements or logging module)
- [ ] Checkpoint saving implemented (every 50-100 steps)
- [ ] Error handling (try/except for known failure modes)
- [ ] Git committed (version control)

**Data Preparation:**
- [ ] Data validated locally (checksums, file counts)
- [ ] Data organized in expected directory structure
- [ ] Large datasets uploaded to cloud storage (S3/GCS)
- [ ] Data split defined (train/val/test)
- [ ] Data preprocessing tested

**Environment Preparation:**
- [ ] Docker image selected (or custom image built)
- [ ] Python version confirmed compatible
- [ ] CUDA version confirmed compatible (12.4+ for Flash Attention 2)
- [ ] Dependencies installable (test with uv sync or pip install)

### Instance Selection

**Search and Select:**
- [ ] Search for instances: `vastai search offers '...'`
- [ ] Filter by reliability: `> 0.95`
- [ ] Filter by GPU model: `gpu_name ~ A100|RTX_4090`
- [ ] Filter by CUDA version: `cuda_vers >= 12.4`
- [ ] Sort by price: `-o 'dph+'`
- [ ] Check DLPerf score (higher = better performance)
- [ ] Verify datacenter (secure_cloud=True for sensitive data)
- [ ] Choose rental type: On-demand (reliable) or Interruptible (cheap)

**Instance Creation:**
- [ ] Create instance: `vastai create instance <ID> --image ... --disk ... --ssh`
- [ ] Wait for instance to start: `vastai show instances`
- [ ] Verify SSH access: `vastai ssh-url <ID>`

### Deployment

**Code Deployment:**
- [ ] Transfer code: `rsync -avz -e "ssh -p <PORT>" --exclude='.venv' ... root@<IP>:/workspace/`
- [ ] Verify transfer: `ssh -p <PORT> root@<IP> "ls -lh /workspace/"`

**Environment Setup:**
- [ ] SSH into instance: `ssh -p <PORT> root@<IP>`
- [ ] Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] Install dependencies: `uv sync`
- [ ] Verify CUDA: `python -c "import torch; print(torch.cuda.is_available())"`
- [ ] Install Flash Attention 2 (if needed): `apt-get install -y ninja-build && uv pip install flash-attn --no-build-isolation`
- [ ] Verify Flash Attention: `python -c "import flash_attn; print(flash_attn.__version__)"`

**Data Transfer:**
- [ ] Transfer data via rsync/scp (small datasets) or cloud storage (large datasets)
- [ ] Verify data: `ls -lh /workspace/data/` and checksum comparison

### Job Execution

**Start Job:**
- [ ] Create screen/tmux session: `screen -S training`
- [ ] Set up GPU monitoring: `watch -n 2 nvidia-smi` (in separate pane)
- [ ] Start TensorBoard (if using): `tensorboard --logdir /workspace/logs --port 6006 --bind_all`
- [ ] Start training: `uv run python scripts/training/train.py`
- [ ] Detach from session: Ctrl+A, D (screen) or Ctrl+B, D (tmux)

**Checkpoint Backup:**
- [ ] Set up automatic cloud backup: `/workspace/sync_checkpoints.sh &`
- [ ] Verify backup: `aws s3 ls s3://bucket/models/`

### Monitoring

**During Job:**
- [ ] Check GPU utilization: `ssh -p <PORT> root@<IP> "nvidia-smi"`
- [ ] Check logs: `ssh -p <PORT> root@<IP> "tail -f /workspace/training.log"`
- [ ] Check progress: `ssh -p <PORT> root@<IP> "cat /workspace/logs/progress.json"`
- [ ] Check TensorBoard: `http://localhost:6006` (after port forwarding)
- [ ] Monitor disk space: `ssh -p <PORT> root@<IP> "df -h"`
- [ ] Monitor instance status: `vastai show instances`

**Checkpointing:**
- [ ] Periodic checkpoint download: `rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/models/checkpoint-* /local/backups/`
- [ ] Verify checkpoints: `ls -lh /local/backups/checkpoint-*`

### Post-Job

**Download Results:**
- [ ] Download final model: `rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/models/ /local/models/`
- [ ] Download logs: `rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/logs/ /local/logs/`
- [ ] Download results: `rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/results/ /local/results/`
- [ ] Verify downloads: Checksum or file count comparison

**Cleanup:**
- [ ] Verify all important data downloaded
- [ ] Delete sensitive data on instance (if any): `ssh -p <PORT> root@<IP> "rm -f /workspace/.env ~/.aws/credentials"`
- [ ] Destroy instance: `vastai destroy instance <ID>` (CRITICAL - stops billing)
- [ ] Verify destruction: `vastai show instances` (should not list instance)

**Documentation:**
- [ ] Record instance specs (GPU model, VRAM, cost/hr)
- [ ] Record training time (total hours)
- [ ] Record total cost (hours × cost/hr + storage + bandwidth)
- [ ] Record metrics (F1, accuracy, loss, etc.)
- [ ] Update model metadata (label_map.json)
- [ ] Git commit results

---

## Quick Reference Commands

**Instance Management:**
```bash
# Search instances
vastai search offers 'reliability > 0.95 cuda_vers >= 12.4' -o 'dph+'

# Create instance
vastai create instance <ID> --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel --disk 100 --ssh

# Show instances
vastai show instances

# SSH into instance
vastai ssh-url <ID>
ssh -p <PORT> root@<IP>

# Stop instance (still charged for storage)
vastai stop instance <ID>

# Destroy instance (stops all billing)
vastai destroy instance <ID>
```

**Data Transfer:**
```bash
# Transfer code
rsync -avz -e "ssh -p <PORT>" --exclude='.venv' /local/project/ root@<IP>:/workspace/project/

# Transfer data
rsync -avz -e "ssh -p <PORT>" /local/data/ root@<IP>:/workspace/data/

# Download results
rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/results/ /local/results/
```

**Environment Setup:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh && source $HOME/.cargo/env

# Install dependencies
uv sync

# Verify GPU
uv run python -c "import torch; print(torch.cuda.is_available())"

# Install Flash Attention 2
apt-get install -y ninja-build && uv pip install flash-attn --no-build-isolation
```

**Job Execution:**
```bash
# Start persistent session
screen -S training

# Run job
uv run python scripts/training/train.py

# Detach (Ctrl+A, D)

# Reattach
screen -r training

# Monitor GPU
watch -n 2 nvidia-smi
```

**Monitoring:**
```bash
# Check logs
tail -f training.log

# Check disk space
df -h

# Check instance status
vastai show instances

# Forward TensorBoard port
ssh -p <PORT> root@<IP> -L 6006:localhost:6006
```

---

## Additional Resources

**Official Documentation:**
- Vast.ai Docs: https://docs.vast.ai/
- Vast.ai Console: https://cloud.vast.ai/
- Vast.ai CLI: https://github.com/vast-ai/vast-cli
- API Reference: https://docs.vast.ai/api/overview-and-quickstart

**Community Resources:**
- Vast.ai Discord: https://discord.gg/vast
- GitHub Tutorials: https://github.com/joystiller/vast-ai-guide
- Community Templates: https://cloud.vast.ai/templates/

**ML Framework Docs:**
- PyTorch CUDA: https://pytorch.org/get-started/locally/
- Flash Attention 2: https://github.com/Dao-AILab/flash-attention
- HuggingFace Transformers: https://huggingface.co/docs/transformers/
- ModernBERT: https://huggingface.co/answerdotai/ModernBERT-base

**Related Guides in docling-testing:**
- [VAST_AI_DEPLOYMENT_GUIDE.md](VAST_AI_DEPLOYMENT_GUIDE.md) - Complete deployment guide
- [VAST_AI_QUICK_REFERENCE.md](VAST_AI_QUICK_REFERENCE.md) - Quick reference cheat sheet
- [VASTAI_GPU_RENTAL_ANALYSIS.md](VASTAI_GPU_RENTAL_ANALYSIS.md) - Cost-benefit analysis
- [TRAINING_QUICK_START.md](guides/TRAINING_QUICK_START.md) - ModernBERT training workflow
- [ASTRAL_SUITE_GUIDE.md](ASTRAL_SUITE_GUIDE.md) - uv package manager guide

---

**Last Updated:** 2025-10-24
**Maintainer:** Claude Code
**Project:** docling-testing
**Version:** 1.0

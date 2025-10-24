# Vast.ai GPU Deployment Guide

**Purpose:** Deploy Python OCR pipelines and ModernBERT training to vast.ai GPU instances with Flash Attention 2 support.

**Last Updated:** 2025-10-24

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [GPU Requirements](#gpu-requirements)
4. [Docker Image Selection](#docker-image-selection)
5. [Setup Process](#setup-process)
6. [Data Transfer](#data-transfer)
7. [OCR Pipeline Deployment](#ocr-pipeline-deployment)
8. [ModernBERT Training Deployment](#modernbert-training-deployment)
9. [Monitoring & Checkpointing](#monitoring--checkpointing)
10. [Retrieving Results](#retrieving-results)
11. [Common Pitfalls](#common-pitfalls)
12. [Cost Optimization](#cost-optimization)

---

## Quick Start

### For OCR Pipeline (EasyOCR)
```bash
# 1. Install vast.ai CLI
pip install vastai

# 2. Find suitable GPU (A100, RTX 3090+, CUDA 12+)
vastai search offers 'reliability > 0.95 cuda_vers >= 12.0 gpu_ram >= 16' -o 'dph+'

# 3. Launch instance with PyTorch template
vastai create instance <INSTANCE_ID> \
  --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel \
  --disk 50 \
  --ssh

# 4. SSH into instance
vastai ssh-url <INSTANCE_ID>

# 5. Transfer code and data (see Data Transfer section)
```

### For ModernBERT Training (with Flash Attention 2)
```bash
# 1. Find Ampere+ GPU (required for Flash Attention 2)
vastai search offers 'reliability > 0.95 cuda_vers >= 12.0 gpu_name ~ A100|RTX_4090|H100' -o 'dph+'

# 2. Launch with on-demand instance (for long training)
vastai create instance <INSTANCE_ID> \
  --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel \
  --disk 100 \
  --ondemand \
  --ssh

# 3. Setup environment (see Setup Process section)
```

---

## Prerequisites

### Local Machine
- Vast.ai account with API key
- Vast.ai CLI installed: `pip install vastai`
- SSH client
- (Optional) `rsync` for efficient data transfer

### Vast.ai Configuration
```bash
# Set API key
vastai set api-key YOUR_API_KEY

# Verify connection
vastai show instances
```

---

## GPU Requirements

### For EasyOCR Pipeline
- **Minimum:** RTX 3090 (24GB VRAM)
- **Recommended:** A100 40GB (faster, better batch processing)
- **CUDA:** 12.1 or newer
- **cuDNN:** 9.x (included in PyTorch Docker images)
- **Architecture:** Ampere or newer (for best performance)

### For ModernBERT Training with Flash Attention 2
- **Required GPU Architecture:** Ampere, Ada, or Hopper
  - A100, RTX 3090, RTX 4090, H100
  - **NOT compatible:** Turing (T4, RTX 2080) or older
- **Required CUDA:** 12.0+ (12.4+ recommended)
- **Required cuDNN:** 9.1.0.70+
- **Recommended VRAM:** 40GB+ for batch training
- **PyTorch:** 2.2+ (native Flash Attention 2 support)

### GPU Selection Command
```bash
# OCR workload
vastai search offers 'reliability > 0.95 cuda_vers >= 12.0 gpu_ram >= 16 num_gpus=1' -o 'dph+'

# Training workload (Flash Attention 2 required)
vastai search offers 'reliability > 0.95 cuda_vers >= 12.4 gpu_name ~ A100|RTX_4090|RTX_3090|H100' -o 'dph+'

# Multi-GPU training
vastai search offers 'reliability > 0.95 cuda_vers >= 12.4 gpu_name ~ A100 num_gpus >= 2' -o 'dph+'
```

---

## Docker Image Selection

### Recommended Images (2025)

#### 1. Official PyTorch Images (Best for most use cases)
```bash
# Python 3.12 + PyTorch 2.6 + CUDA 12.4 + cuDNN 9
pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel

# Python 3.11 + PyTorch 2.4 + CUDA 12.4
pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel
```

**Pros:** Official support, all dependencies included, well-tested
**Cons:** Large image size (~10GB)

#### 2. AI-Dock Images (Optimized for vast.ai)
```bash
# Check latest at: https://github.com/ai-dock/pytorch
ai-dock/pytorch:latest-cuda-12.4-python-3.11
```

**Pros:** Specifically designed for vast.ai/runpod, includes common ML tools
**Cons:** Less official support

#### 3. Vast.ai Official Templates
```bash
# Available in Vast.ai Console Templates tab
# Select PyTorch version via Version Tag selector
# Automatically supports CUDA 12.4+
```

#### 4. NVIDIA CUDA Base (For custom builds)
```bash
nvidia/cuda:12.4.0-cudnn9-runtime-ubuntu22.04
```

**Use case:** When you need full control over Python/package versions

### Image Selection Criteria
- **OCR Pipeline:** Use `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel` (includes all PyTorch dependencies)
- **ModernBERT Training:** Same as above, ensure Flash Attention 2 compatibility
- **Python 3.13 Required:** Build custom image from `nvidia/cuda` base + Python 3.13
- **Storage Constraints:** Use `-runtime` instead of `-devel` images (smaller size)

---

## Setup Process

### Method 1: Quick Setup (Using uv Package Manager)

**Step 1: Launch Instance**
```bash
vastai create instance <INSTANCE_ID> \
  --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel \
  --disk 100 \
  --ssh \
  --env '-e DEBIAN_FRONTEND=noninteractive'
```

**Step 2: SSH Into Instance**
```bash
# Get SSH command
vastai ssh-url <INSTANCE_ID>

# Or directly
ssh -p <PORT> root@<IP_ADDRESS> -L 8080:localhost:8080
```

**Step 3: Install uv (Fastest Package Manager)**
```bash
# Inside instance
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Verify
uv --version
```

**Step 4: Install Python 3.13 (if needed)**
```bash
uv python install 3.13
uv python pin 3.13
```

**Step 5: Transfer Project Code**
```bash
# From local machine
rsync -avz -e "ssh -p <PORT>" \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='models/' \
  --exclude='results/' \
  /Users/donaldbraman/Documents/GitHub/docling-testing/ \
  root@<IP_ADDRESS>:/workspace/docling-testing/
```

**Step 6: Setup Project Environment**
```bash
# Inside instance
cd /workspace/docling-testing

# Install dependencies with uv (10-100x faster than pip)
uv sync

# Verify PyTorch CUDA
uv run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"
```

**Step 7: Install Flash Attention 2 (For ModernBERT)**
```bash
# Install ninja for faster compilation (optional but recommended)
apt-get update && apt-get install -y ninja-build

# Install Flash Attention 2
uv pip install flash-attn --no-build-isolation

# Verify
uv run python -c "import flash_attn; print(f'Flash Attention installed: {flash_attn.__version__}')"
```

**Compilation Note:** Without `ninja`, Flash Attention compilation can take 2+ hours. With `ninja`, it takes 3-5 minutes on a 64-core machine.

**Memory-limited machines:**
```bash
# Limit parallel compilation jobs
MAX_JOBS=4 uv pip install flash-attn --no-build-isolation
```

### Method 2: Traditional Setup (Using pip/conda)

**Step 1-2:** Same as Method 1

**Step 3: Install Dependencies**
```bash
# Inside instance
cd /workspace/docling-testing

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt  # or from pyproject.toml
```

**Step 4: Install Flash Attention 2**
```bash
pip install flash-attn --no-build-isolation
```

---

## Data Transfer

### Understanding Vast.ai Data Transfer

**Default SSH Connection:**
- Uses a proxy (high latency, moderate bandwidth)
- Good for: Small files (<1GB), code, scripts
- Command: `scp` or `rsync` over proxied SSH

**Direct Connection (Recommended for large datasets):**
- Bypasses proxy (better performance)
- Good for: Large datasets, model checkpoints
- Requires: Wireguard VPN setup (see Vast.ai docs)

**Cloud Storage (Best for >10GB datasets):**
- Highest bandwidth
- Good for: Very large datasets, shared data
- Command: `wget`, `curl`, `aws s3 cp`, `gsutil`

### Transfer Methods

#### 1. rsync (Recommended for Code + Small Data)

**From Local to Vast.ai:**
```bash
# Get SSH connection details
vastai ssh-url <INSTANCE_ID>

# Transfer entire project (excluding large files)
rsync -avz -e "ssh -p <PORT>" \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='models/*/pytorch_model.bin' \
  --exclude='results/' \
  --exclude='archive*/' \
  --exclude='.git/' \
  /Users/donaldbraman/Documents/GitHub/docling-testing/ \
  root@<IP_ADDRESS>:/workspace/docling-testing/

# Transfer specific directories only
rsync -avz -e "ssh -p <PORT>" \
  /Users/donaldbraman/Documents/GitHub/docling-testing/scripts/ \
  root@<IP_ADDRESS>:/workspace/docling-testing/scripts/

# Transfer PDF corpus
rsync -avz -e "ssh -p <PORT>" \
  /Users/donaldbraman/Documents/GitHub/docling-testing/data/v3_data/raw_pdf/ \
  root@<IP_ADDRESS>:/workspace/docling-testing/data/v3_data/raw_pdf/
```

**Advantages:**
- Only transfers changed files (incremental sync)
- Preserves permissions and timestamps
- Automatic compression
- Resume support after interruptions

**Best Practices:**
- Use `-avz` flags (archive, verbose, compress)
- Exclude unnecessary files (`.venv`, `__pycache__`, large binaries)
- For large files: Use `--partial` flag for resume support

#### 2. scp (Simple One-Time Transfers)

```bash
# Single file
scp -P <PORT> local_file.pdf root@<IP_ADDRESS>:/workspace/

# Directory
scp -r -P <PORT> /path/to/directory root@<IP_ADDRESS>:/workspace/

# Multiple files
scp -P <PORT> file1.pdf file2.pdf file3.pdf root@<IP_ADDRESS>:/workspace/
```

**Note:** Use capital `-P` for port flag (different from ssh's `-p`)

#### 3. Cloud Storage (Best for Large Datasets)

**Upload from local machine to S3/GCS:**
```bash
# AWS S3
aws s3 sync data/v3_data/raw_pdf/ s3://your-bucket/raw_pdf/

# Google Cloud Storage
gsutil -m cp -r data/v3_data/raw_pdf/ gs://your-bucket/raw_pdf/
```

**Download on vast.ai instance:**
```bash
# AWS S3
aws s3 sync s3://your-bucket/raw_pdf/ /workspace/data/v3_data/raw_pdf/

# Google Cloud Storage
gsutil -m cp -r gs://your-bucket/raw_pdf/ /workspace/data/v3_data/raw_pdf/

# Direct download via wget
wget -r -np -nH --cut-dirs=2 https://your-cdn.com/datasets/raw_pdf/
```

**Advantages:**
- Highest bandwidth (often 1-10 Gbps)
- No proxy overhead
- Parallel downloads
- Permanent storage (backup)

#### 4. Vast.ai CLI Copy (Using rsync internally)

```bash
# Copy to instance
vastai copy <LOCAL_PATH> <INSTANCE_ID>:<REMOTE_PATH>

# Copy from instance
vastai copy <INSTANCE_ID>:<REMOTE_PATH> <LOCAL_PATH>

# Example: Copy PDFs to instance
vastai copy data/v3_data/raw_pdf/ 12345:/workspace/data/v3_data/raw_pdf/
```

### Transfer Performance Tips

1. **Compress before transfer (for many small files):**
```bash
# Local machine
tar -czf project.tar.gz docling-testing/

# Transfer compressed archive
scp -P <PORT> project.tar.gz root@<IP_ADDRESS>:/workspace/

# Instance: Extract
cd /workspace && tar -xzf project.tar.gz
```

2. **Parallel transfers (for multiple large files):**
```bash
# Using GNU parallel
parallel -j 4 "scp -P <PORT> {} root@<IP_ADDRESS>:/workspace/" ::: *.pdf
```

3. **Monitor transfer progress:**
```bash
# rsync with progress
rsync -avz --progress -e "ssh -p <PORT>" source/ root@<IP_ADDRESS>:/dest/

# scp with verbose output
scp -v -P <PORT> file.pdf root@<IP_ADDRESS>:/workspace/
```

### Data Transfer Checklist

**Before transferring:**
- [ ] Verify instance is running: `vastai show instances`
- [ ] Check available disk space: `ssh root@<IP> df -h`
- [ ] Exclude unnecessary files (.venv, __pycache__, .git)
- [ ] Consider compression for many small files

**After transferring:**
- [ ] Verify file integrity: `md5sum` or `sha256sum`
- [ ] Check file permissions: `ls -la`
- [ ] Verify directory structure: `tree -L 2` or `find . -type d`

---

## OCR Pipeline Deployment

### Overview
EasyOCR is PyTorch-based and GPU-accelerated. It automatically uses CUDA when available.

### Setup

**Step 1: Verify GPU Access**
```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

**Step 2: Install Additional Dependencies (if needed)**
```bash
# For PDF to image conversion
apt-get update && apt-get install -y poppler-utils

# Verify pdf2image works
uv run python -c "from pdf2image import convert_from_path; print('pdf2image OK')"
```

**Step 3: Test EasyOCR GPU Access**
```bash
uv run python -c "
import easyocr
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
reader = easyocr.Reader(['en'], gpu=True)
print('EasyOCR initialized with GPU support')
"
```

### Running OCR Pipeline

**Single PDF Processing:**
```bash
cd /workspace/docling-testing

# Extract single PDF with EasyOCR
uv run python scripts/corpus_building/extract_with_easyocr.py \
  --pdf political_mootness \
  --dpi 300
```

**Batch Processing (Multiple PDFs):**
```bash
# Create batch processing script
cat > batch_ocr.sh << 'EOF'
#!/bin/bash
PDF_DIR="/workspace/docling-testing/data/v3_data/raw_pdf"
OUTPUT_DIR="/workspace/results/ocr_pipeline_evaluation/extractions"

mkdir -p "$OUTPUT_DIR"

for pdf in "$PDF_DIR"/*.pdf; do
    basename=$(basename "$pdf" .pdf)
    echo "Processing: $basename"

    uv run python scripts/corpus_building/extract_with_easyocr.py \
        --pdf "$basename" \
        --dpi 300 \
        2>&1 | tee "$OUTPUT_DIR/${basename}_ocr.log"
done
EOF

chmod +x batch_ocr.sh
nohup ./batch_ocr.sh > batch_ocr_master.log 2>&1 &
```

**Monitor Progress:**
```bash
# Watch real-time log
tail -f batch_ocr_master.log

# Check GPU utilization
watch -n 1 nvidia-smi

# Count completed PDFs
ls results/ocr_pipeline_evaluation/extractions/*.csv | wc -l
```

### Performance Optimization

**Batch Size Tuning:**
```python
# Modify extract_with_easyocr.py
reader = easyocr.Reader(['en'], gpu=True)

# Process multiple pages in parallel (adjust batch_size based on VRAM)
results = reader.readtext(
    image,
    batch_size=8,  # Increase for A100 (40GB), decrease for RTX 3090 (24GB)
    workers=4      # CPU workers for pre/post-processing
)
```

**DPI Settings:**
- 300 DPI: Standard quality (balance speed/accuracy)
- 600 DPI: High quality (2x slower, better for degraded PDFs)
- 150 DPI: Fast processing (lower accuracy)

**Memory Management:**
```python
# Clear CUDA cache between PDFs
import torch
torch.cuda.empty_cache()
```

---

## ModernBERT Training Deployment

### Flash Attention 2 Installation

**Verify GPU Compatibility:**
```bash
# Check GPU architecture (must be Ampere/Ada/Hopper)
nvidia-smi --query-gpu=name,compute_cap --format=csv

# Expected output:
# A100: 8.0 (Ampere) ✓
# RTX 3090: 8.6 (Ampere) ✓
# RTX 4090: 8.9 (Ada) ✓
# H100: 9.0 (Hopper) ✓
# T4: 7.5 (Turing) ✗ NOT SUPPORTED
```

**Install Flash Attention 2:**
```bash
# Install ninja for faster compilation
apt-get update && apt-get install -y ninja-build

# Install Flash Attention 2
uv pip install flash-attn --no-build-isolation

# For memory-limited machines
MAX_JOBS=4 uv pip install flash-attn --no-build-isolation
```

**Verify Installation:**
```bash
uv run python -c "
import flash_attn
import torch
print(f'Flash Attention version: {flash_attn.__version__}')
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA version: {torch.version.cuda}')
print(f'cuDNN version: {torch.backends.cudnn.version()}')
"
```

### Running Training Jobs

**Quick Test (Small Dataset):**
```bash
cd /workspace/docling-testing

# Test training with small subset
uv run python scripts/training/train_quick_test.py
```

**Full Training (Long-Running):**
```bash
# Use screen or tmux for persistent sessions
screen -S modernbert_training

# Start training
uv run python scripts/training/train_modernbert_classifier.py \
  --epochs 10 \
  --batch-size 16 \
  --learning-rate 2e-5 \
  --output-dir /workspace/models/modernbert-v3 \
  --checkpoint-steps 100

# Detach from screen: Ctrl+A, D
# Reattach: screen -r modernbert_training
```

**Multi-GPU Training:**
```bash
# Using PyTorch DistributedDataParallel
uv run torchrun \
  --nproc_per_node=2 \
  scripts/training/train_modernbert_classifier.py \
  --epochs 10 \
  --batch-size 32 \
  --output-dir /workspace/models/modernbert-v3-multi-gpu
```

### Training Configuration

**Recommended Hyperparameters:**
```python
# For ModernBERT-base (149M parameters)
training_args = TrainingArguments(
    output_dir="/workspace/models/modernbert-v3",
    num_train_epochs=10,
    per_device_train_batch_size=16,  # Adjust based on VRAM
    per_device_eval_batch_size=32,
    learning_rate=2e-5,
    warmup_steps=500,
    weight_decay=0.01,
    logging_steps=50,
    eval_steps=100,
    save_steps=100,
    save_total_limit=3,  # Keep only 3 best checkpoints
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    greater_is_better=True,
    fp16=True,  # Mixed precision training (2x faster on Ampere+)
    gradient_accumulation_steps=2,  # Effective batch size = 32
)
```

**Batch Size Guidelines:**
| GPU | VRAM | Batch Size (ModernBERT-base) |
|-----|------|------------------------------|
| RTX 3090 | 24GB | 8-16 |
| A100 40GB | 40GB | 16-32 |
| A100 80GB | 80GB | 32-64 |
| H100 | 80GB | 64-128 |

**Memory Optimization:**
```python
# Enable gradient checkpointing (trades compute for memory)
model.gradient_checkpointing_enable()

# Use Flash Attention 2 (automatic with ModernBERT)
# No code changes needed - ModernBERT uses FA2 by default

# Mixed precision training
training_args.fp16 = True  # For Ampere GPUs
# OR
training_args.bf16 = True  # For Ampere+ (better numerical stability)
```

---

## Monitoring & Checkpointing

### Monitoring Long-Running Jobs

#### 1. TensorBoard (Real-Time Metrics)

**Setup:**
```bash
# Inside training script, ensure trainer logs to TensorBoard
from transformers import TrainingArguments

training_args = TrainingArguments(
    output_dir="/workspace/models/modernbert-v3",
    logging_dir="/workspace/logs/tensorboard",
    logging_steps=50,
    report_to="tensorboard",
)
```

**Launch TensorBoard:**
```bash
# On vast.ai instance
tensorboard --logdir /workspace/logs/tensorboard --port 6006 --bind_all

# SSH port forwarding (from local machine)
ssh -p <PORT> root@<IP> -L 6006:localhost:6006

# Open in browser: http://localhost:6006
```

#### 2. Training Logs

**View Real-Time Logs:**
```bash
# If using nohup
tail -f nohup.out

# If using screen/tmux
screen -r training_session

# Custom log file
tail -f /workspace/logs/training.log
```

**Parse Logs for Metrics:**
```bash
# Extract loss values
grep "loss=" nohup.out | tail -20

# Extract evaluation metrics
grep "eval_" nohup.out | tail -10
```

#### 3. GPU Monitoring

**Real-Time GPU Utilization:**
```bash
# Basic monitoring
watch -n 1 nvidia-smi

# Detailed monitoring
nvidia-smi dmon -s pucvmet -d 5  # Update every 5 seconds

# Log GPU stats to file
nvidia-smi --query-gpu=timestamp,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.free \
  --format=csv -l 10 > gpu_stats.csv &
```

**GPU Memory Tracking:**
```python
# Inside training script
import torch

def log_gpu_memory():
    allocated = torch.cuda.memory_allocated() / 1e9  # GB
    reserved = torch.cuda.memory_reserved() / 1e9
    print(f"GPU Memory: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")

# Call after each training step
```

#### 4. Progress Tracking

**Simple Progress File:**
```bash
# Create progress tracker in training script
import json
from pathlib import Path

def save_progress(epoch, step, metrics):
    progress = {
        "epoch": epoch,
        "step": step,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    }
    Path("/workspace/logs/progress.json").write_text(json.dumps(progress, indent=2))

# Monitor from another terminal
watch -n 10 "cat /workspace/logs/progress.json"
```

### Checkpointing Strategies

#### 1. Automatic Checkpointing (HuggingFace Trainer)

```python
from transformers import TrainingArguments

training_args = TrainingArguments(
    output_dir="/workspace/models/modernbert-v3",
    save_strategy="steps",
    save_steps=100,  # Save every 100 steps
    save_total_limit=3,  # Keep only 3 best checkpoints (save disk space)
    load_best_model_at_end=True,
    metric_for_best_model="f1",
)
```

**Checkpoint Directory Structure:**
```
/workspace/models/modernbert-v3/
├── checkpoint-100/
│   ├── config.json
│   ├── model.safetensors
│   ├── optimizer.pt
│   ├── scheduler.pt
│   ├── trainer_state.json
│   └── training_args.bin
├── checkpoint-200/
├── checkpoint-300/
└── runs/  # TensorBoard logs
```

#### 2. Manual Checkpointing

```python
import torch
from pathlib import Path

def save_checkpoint(model, optimizer, epoch, step, metrics, path):
    checkpoint = {
        'epoch': epoch,
        'step': step,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'metrics': metrics,
    }
    torch.save(checkpoint, path)
    print(f"Checkpoint saved: {path}")

def load_checkpoint(model, optimizer, path):
    checkpoint = torch.load(path)
    model.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    return checkpoint['epoch'], checkpoint['step'], checkpoint['metrics']

# Usage
save_checkpoint(
    model, optimizer, epoch=3, step=1500,
    metrics={'loss': 0.123, 'f1': 0.87},
    path="/workspace/models/checkpoint_epoch3_step1500.pt"
)
```

#### 3. Cloud Backup Strategy (Critical for Interruptible Instances)

**Automatic S3 Sync (Every N Steps):**
```bash
# Install AWS CLI (inside instance)
apt-get install -y awscli

# Configure AWS credentials
aws configure

# Create sync script
cat > sync_checkpoints.sh << 'EOF'
#!/bin/bash
while true; do
    aws s3 sync /workspace/models/ s3://your-bucket/vast-ai-training/models/ \
        --exclude "*" --include "checkpoint-*/*" --include "*.json"
    sleep 600  # Sync every 10 minutes
done
EOF

chmod +x sync_checkpoints.sh
nohup ./sync_checkpoints.sh > sync.log 2>&1 &
```

**Rsync to Local Machine (Periodic):**
```bash
# From local machine, run periodically
while true; do
    rsync -avz -e "ssh -p <PORT>" \
        root@<IP>:/workspace/models/modernbert-v3/checkpoint-* \
        /Users/donaldbraman/Documents/GitHub/docling-testing/models/vast-ai-backups/
    sleep 1800  # Every 30 minutes
done
```

#### 4. Resume Training from Checkpoint

```python
from transformers import Trainer, TrainingArguments

# Auto-resume from last checkpoint
training_args = TrainingArguments(
    output_dir="/workspace/models/modernbert-v3",
    resume_from_checkpoint=True,  # Auto-detect latest checkpoint
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
)

# Start training (automatically resumes if checkpoint exists)
trainer.train(resume_from_checkpoint=True)

# OR manually specify checkpoint
trainer.train(resume_from_checkpoint="/workspace/models/modernbert-v3/checkpoint-500")
```

### Handling Instance Interruptions

#### On-Demand vs Interruptible Instances

**On-Demand Instances:**
- Guaranteed availability (no interruptions)
- Higher cost (2-3x interruptible)
- **Recommended for:** Training jobs >4 hours, final production runs

**Interruptible Instances:**
- Can be paused/stopped if outbid
- Lower cost
- **Recommended for:** Experimentation, short jobs (<2 hours), fault-tolerant workloads

**Best Practices:**
1. Use **on-demand instances** for long training runs (>4 hours)
2. Use **interruptible instances** for experimentation/debugging
3. Select hosts with **high reliability scores** (>0.95)
4. Implement **aggressive checkpointing** (every 50-100 steps)
5. Backup checkpoints to **cloud storage** regularly

#### Recovery Script

```bash
#!/bin/bash
# recovery.sh - Auto-restart training after interruption

CHECKPOINT_DIR="/workspace/models/modernbert-v3"
BACKUP_BUCKET="s3://your-bucket/vast-ai-training/models/"

# 1. Download latest checkpoint from S3
echo "Downloading latest checkpoint from S3..."
aws s3 sync "$BACKUP_BUCKET" "$CHECKPOINT_DIR" --exclude "*" --include "checkpoint-*/*"

# 2. Find latest checkpoint
LATEST_CHECKPOINT=$(ls -td "$CHECKPOINT_DIR"/checkpoint-* | head -1)
echo "Latest checkpoint: $LATEST_CHECKPOINT"

# 3. Resume training
echo "Resuming training..."
uv run python scripts/training/train_modernbert_classifier.py \
    --resume-from-checkpoint "$LATEST_CHECKPOINT" \
    --output-dir "$CHECKPOINT_DIR"
```

---

## Retrieving Results

### During Training

**Download Checkpoints:**
```bash
# From local machine
rsync -avz -e "ssh -p <PORT>" \
    root@<IP>:/workspace/models/modernbert-v3/checkpoint-* \
    /Users/donaldbraman/Documents/GitHub/docling-testing/models/vast-ai/
```

**Download Logs:**
```bash
rsync -avz -e "ssh -p <PORT>" \
    root@<IP>:/workspace/logs/ \
    /Users/donaldbraman/Documents/GitHub/docling-testing/logs/vast-ai/
```

### After Training Completes

**Download Final Model:**
```bash
# Entire model directory
rsync -avz -e "ssh -p <PORT>" \
    root@<IP>:/workspace/models/modernbert-v3/ \
    /Users/donaldbraman/Documents/GitHub/docling-testing/models/modernbert-v3/

# Only model weights (faster)
scp -P <PORT> root@<IP>:/workspace/models/modernbert-v3/pytorch_model.bin \
    /Users/donaldbraman/Documents/GitHub/docling-testing/models/
```

**Download OCR Results:**
```bash
# CSV outputs
rsync -avz -e "ssh -p <PORT>" \
    root@<IP>:/workspace/results/ocr_pipeline_evaluation/ \
    /Users/donaldbraman/Documents/GitHub/docling-testing/results/vast-ai-ocr/

# Annotated PDFs
rsync -avz -e "ssh -p <PORT>" \
    root@<IP>:/workspace/results/ocr_pipeline_evaluation/ocrmypdf_pdfs/ \
    /Users/donaldbraman/Documents/GitHub/docling-testing/results/annotated_pdfs/
```

### Archive and Cleanup

**Before Destroying Instance:**
```bash
# 1. Create complete archive
ssh -p <PORT> root@<IP> "cd /workspace && tar -czf results_archive.tar.gz \
    models/modernbert-v3/ \
    results/ocr_pipeline_evaluation/ \
    logs/"

# 2. Download archive
scp -P <PORT> root@<IP>:/workspace/results_archive.tar.gz \
    /Users/donaldbraman/Documents/GitHub/docling-testing/

# 3. Verify archive integrity
tar -tzf results_archive.tar.gz | head -20

# 4. Destroy instance (via CLI or console)
vastai destroy instance <INSTANCE_ID>
```

---

## Common Pitfalls

### 1. Flash Attention 2 Installation Issues

**Problem:** `ModuleNotFoundError: No module named 'flash_attn_2_cuda'`

**Solution:**
```bash
# Ensure CUDA toolkit is available
nvcc --version

# If nvcc not found, install CUDA toolkit
apt-get install -y cuda-toolkit-12-4

# Reinstall Flash Attention
pip uninstall flash-attn -y
MAX_JOBS=4 pip install flash-attn --no-build-isolation
```

**Problem:** `RuntimeError: Flash Attention requires Ampere or newer GPU`

**Solution:** Flash Attention 2 does NOT support Turing GPUs (T4, RTX 2080). You must use Ampere+ GPUs (A100, RTX 3090+).

### 2. Out of Memory (OOM) Errors

**Problem:** `CUDA out of memory` during training

**Solution:**
```python
# Reduce batch size
per_device_train_batch_size=8  # Instead of 16

# Enable gradient checkpointing
model.gradient_checkpointing_enable()

# Reduce max sequence length
max_length=256  # Instead of 512

# Use gradient accumulation
gradient_accumulation_steps=4  # Effective batch size = 32
```

### 3. Instance Disk Full

**Problem:** `/workspace` disk full during training

**Solution:**
```bash
# Check disk usage
df -h

# Remove old checkpoints
rm -rf /workspace/models/*/checkpoint-{100..400}

# Keep only best 3 checkpoints
ls -t /workspace/models/*/checkpoint-* | tail -n +4 | xargs rm -rf

# Request instance with more disk space
vastai create instance <ID> --disk 200  # 200GB
```

### 4. SSH Connection Lost

**Problem:** SSH disconnects, training stops

**Solution:**
```bash
# Use screen or tmux for persistent sessions
screen -S training
# Run training inside screen
# Detach: Ctrl+A, D
# Reattach after reconnect: screen -r training

# OR use nohup
nohup uv run python scripts/training/train_modernbert_classifier.py > training.log 2>&1 &
```

### 5. Slow Data Transfer

**Problem:** rsync/scp is very slow

**Solution:**
```bash
# Use cloud storage instead
aws s3 cp data/ s3://bucket/data/ --recursive
# Then download on instance
aws s3 sync s3://bucket/data/ /workspace/data/

# Use compression
tar -czf data.tar.gz data/
scp -P <PORT> data.tar.gz root@<IP>:/workspace/
ssh -p <PORT> root@<IP> "cd /workspace && tar -xzf data.tar.gz"
```

### 6. Python Version Mismatch

**Problem:** Python 3.13 required, instance has 3.11

**Solution:**
```bash
# Use uv to install Python 3.13
uv python install 3.13
uv python pin 3.13

# Verify
uv run python --version  # Should show 3.13.x
```

### 7. EasyOCR Not Using GPU

**Problem:** EasyOCR defaulting to CPU

**Solution:**
```python
# Explicitly enable GPU
reader = easyocr.Reader(['en'], gpu=True)

# Verify CUDA is available
import torch
assert torch.cuda.is_available(), "CUDA not available"

# Check EasyOCR GPU usage
import easyocr
reader = easyocr.Reader(['en'], gpu=True, verbose=True)
# Should print: "Using GPU: True"
```

### 8. Checkpoint Not Found After Interruption

**Problem:** Training crashes, checkpoint lost

**Solution:**
```bash
# Always backup checkpoints to cloud storage
aws s3 sync /workspace/models/ s3://bucket/models/ --exclude "*" --include "checkpoint-*/*"

# Set up automatic sync
cat > sync_checkpoints.sh << 'EOF'
#!/bin/bash
while true; do
    aws s3 sync /workspace/models/ s3://bucket/models/
    sleep 600
done
EOF
nohup ./sync_checkpoints.sh > sync.log 2>&1 &
```

---

## Cost Optimization

### Instance Selection

**Choose Right Instance Type:**
| Workload | GPU | VRAM | Cost/hr | Recommendation |
|----------|-----|------|---------|----------------|
| OCR (small batch) | RTX 3090 | 24GB | $0.20-0.40 | Good balance |
| OCR (large batch) | A100 40GB | 40GB | $0.80-1.50 | Faster, higher throughput |
| Training (small model) | RTX 3090 | 24GB | $0.20-0.40 | Cost-effective |
| Training (large model) | A100 40GB | 40GB | $0.80-1.50 | Required for large batch sizes |
| Multi-GPU training | 2x A100 | 80GB | $1.50-3.00 | Faster training |

**Interruptible vs On-Demand:**
- Interruptible: 50-70% cheaper
- On-Demand: 2-3x more expensive, guaranteed availability

### Minimize Billable Time

**1. Prepare Locally:**
```bash
# Test code locally before deploying
uv run pytest tests/

# Verify data integrity locally
md5sum data/v3_data/raw_pdf/*.pdf > checksums.txt
```

**2. Use Docker Build Caching:**
```dockerfile
# Build Docker image locally, push to Docker Hub
docker build -t username/docling-training:latest .
docker push username/docling-training:latest

# On vast.ai, pull pre-built image (faster startup)
docker pull username/docling-training:latest
```

**3. Destroy Instances Immediately After:**
```bash
# Download results
rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/results/ /local/results/

# Verify download
ls -lh /local/results/

# Destroy instance
vastai destroy instance <INSTANCE_ID>
```

**4. Use Auto-Stop on Completion:**
```bash
# Add to end of training script
# train_modernbert_classifier.py
if __name__ == "__main__":
    train()

    # Auto-stop instance after training
    import subprocess
    instance_id = os.environ.get("CONTAINER_ID")
    if instance_id:
        subprocess.run(["vastai", "stop", "instance", instance_id])
```

### Storage Optimization

**1. Minimize Disk Space:**
```bash
# Request only needed disk space
vastai create instance <ID> --disk 50  # Instead of 200

# Clean up during training
# Add to training script
import shutil
if step % 500 == 0:
    # Remove old checkpoints
    shutil.rmtree(f"/workspace/models/checkpoint-{step-500}", ignore_errors=True)
```

**2. Use Shared Storage (Advanced):**
```bash
# Mount external NFS/S3 storage for datasets
# Avoid downloading large datasets to instance disk
s3fs your-bucket /workspace/data -o use_cache=/tmp
```

### Multi-Instance Strategies

**Parallel OCR Processing:**
```bash
# Split 100 PDFs across 4 instances
# Instance 1: PDFs 1-25
# Instance 2: PDFs 26-50
# Instance 3: PDFs 51-75
# Instance 4: PDFs 76-100

# Launch 4 instances
for i in {1..4}; do
    vastai create instance <ID> --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel
done

# Distribute workload via script arguments
# Instance 1:
uv run python batch_ocr.py --start 1 --end 25

# Aggregate results locally after completion
```

### Cost Monitoring

**Track Spending:**
```bash
# Check current instance costs
vastai show instances --format json | jq '.[] | {id, dph_total, elapsed}'

# Calculate total cost
vastai show instances --format json | jq '[.[] | .dph_total * .elapsed] | add'

# Set budget alerts (manual monitoring)
echo "Budget: $50/week, Current: $12.34" > budget.txt
```

**Estimated Costs (Interruptible Instances):**
| Task | GPU | Duration | Cost |
|------|-----|----------|------|
| OCR 100 PDFs | RTX 3090 | 4 hours | $1.60 |
| Train ModernBERT (10 epochs) | A100 40GB | 8 hours | $12.00 |
| Hyperparameter search (5 runs) | A100 40GB | 20 hours | $30.00 |

---

## Quick Reference Commands

### Instance Management
```bash
# Search instances
vastai search offers 'reliability > 0.95 cuda_vers >= 12.0' -o 'dph+'

# Create instance
vastai create instance <ID> --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel --disk 100 --ssh

# SSH into instance
vastai ssh-url <INSTANCE_ID>

# Stop instance
vastai stop instance <INSTANCE_ID>

# Destroy instance
vastai destroy instance <INSTANCE_ID>

# Show running instances
vastai show instances
```

### Data Transfer
```bash
# Transfer code
rsync -avz -e "ssh -p <PORT>" --exclude='.venv' /local/project/ root@<IP>:/workspace/project/

# Transfer data
rsync -avz -e "ssh -p <PORT>" /local/data/ root@<IP>:/workspace/data/

# Download results
rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/results/ /local/results/
```

### Environment Setup
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install Flash Attention 2
uv pip install flash-attn --no-build-isolation

# Verify GPU
uv run python -c "import torch; print(torch.cuda.is_available())"
```

### Training
```bash
# Start training in background
screen -S training
uv run python scripts/training/train_modernbert_classifier.py
# Detach: Ctrl+A, D

# Monitor progress
tail -f nohup.out
nvidia-smi
tensorboard --logdir /workspace/logs --port 6006
```

### Monitoring
```bash
# GPU usage
nvidia-smi

# Disk space
df -h

# Training logs
tail -f nohup.out

# Process list
ps aux | grep python
```

---

## Additional Resources

### Official Documentation
- Vast.ai Docs: https://docs.vast.ai/
- Vast.ai CLI: https://github.com/vast-ai/vast-cli
- Flash Attention 2: https://github.com/Dao-AILab/flash-attention
- PyTorch CUDA: https://pytorch.org/get-started/locally/

### Community Resources
- Vast.ai Discord: https://discord.gg/vast
- Vast.ai Reddit: https://reddit.com/r/vastai
- PyTorch Forums: https://discuss.pytorch.org/

### Related Guides
- [TRAINING_QUICK_START.md](guides/TRAINING_QUICK_START.md) - ModernBERT training workflow
- [ASTRAL_SUITE_GUIDE.md](ASTRAL_SUITE_GUIDE.md) - uv package manager guide
- [OCR_INVESTIGATION_FINDINGS.md](OCR_INVESTIGATION_FINDINGS.md) - OCR pipeline details

---

**Last Updated:** 2025-10-24
**Maintainer:** Claude Code
**Project:** docling-testing

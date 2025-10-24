# Vast.ai Quick Reference Cheat Sheet

**One-page reference for deploying OCR pipelines and ModernBERT training to vast.ai**

---

## Essential Commands

### Setup
```bash
# Install CLI
pip install vastai

# Configure API key
vastai set api-key YOUR_API_KEY

# Find GPU instances
vastai search offers 'reliability > 0.95 cuda_vers >= 12.0 gpu_ram >= 16' -o 'dph+'
```

### Instance Management
```bash
# Launch instance
vastai create instance <ID> --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel --disk 100 --ssh

# SSH into instance
vastai ssh-url <ID>

# Show running instances
vastai show instances

# Stop instance
vastai stop instance <ID>

# Destroy instance
vastai destroy instance <ID>
```

### Data Transfer
```bash
# Transfer project code
rsync -avz -e "ssh -p <PORT>" --exclude='.venv' --exclude='models/' \
  /Users/donaldbraman/Documents/GitHub/docling-testing/ root@<IP>:/workspace/docling-testing/

# Download results
rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/results/ /local/results/
```

---

## Quick Setup (Inside Instance)

### 1. Install uv Package Manager
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### 2. Setup Project
```bash
cd /workspace/docling-testing
uv sync
uv run python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

### 3. Install Flash Attention 2 (ModernBERT only)
```bash
apt-get update && apt-get install -y ninja-build
uv pip install flash-attn --no-build-isolation
```

---

## GPU Requirements

### OCR Pipeline (EasyOCR)
- GPU: RTX 3090+ or A100
- VRAM: 16GB+
- CUDA: 12.1+

### ModernBERT Training (Flash Attention 2)
- GPU: A100, RTX 3090/4090, H100 (Ampere/Ada/Hopper only)
- VRAM: 24GB+ (40GB recommended)
- CUDA: 12.4+
- Architecture: NO T4/RTX 2080 (Turing not supported)

---

## Running Jobs

### OCR Pipeline
```bash
# Single PDF
uv run python scripts/corpus_building/extract_with_easyocr.py --pdf political_mootness --dpi 300

# Batch processing
screen -S ocr
for pdf in data/v3_data/raw_pdf/*.pdf; do
    uv run python scripts/corpus_building/extract_with_easyocr.py --pdf $(basename $pdf .pdf)
done
```

### ModernBERT Training
```bash
# Start training in persistent session
screen -S training
uv run python scripts/training/train_modernbert_classifier.py \
  --output-dir /workspace/models/modernbert-v3

# Detach: Ctrl+A, D
# Reattach: screen -r training
```

---

## Monitoring

### GPU Usage
```bash
watch -n 1 nvidia-smi
```

### Training Logs
```bash
tail -f nohup.out
```

### TensorBoard
```bash
# On instance
tensorboard --logdir /workspace/logs --port 6006 --bind_all

# SSH port forward (local)
ssh -p <PORT> root@<IP> -L 6006:localhost:6006

# Open: http://localhost:6006
```

---

## Checkpointing

### Automatic Cloud Backup
```bash
# Install AWS CLI
apt-get install -y awscli
aws configure

# Auto-sync checkpoints every 10 minutes
cat > sync.sh << 'EOF'
while true; do
    aws s3 sync /workspace/models/ s3://bucket/models/ --exclude "*" --include "checkpoint-*/*"
    sleep 600
done
EOF
nohup ./sync.sh > sync.log 2>&1 &
```

### Download Checkpoints (Local)
```bash
# Periodic backup
rsync -avz -e "ssh -p <PORT>" root@<IP>:/workspace/models/checkpoint-* /local/backups/
```

---

## Recommended Docker Images

| Use Case | Image |
|----------|-------|
| OCR + Training | `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel` |
| Lightweight | `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime` |
| Custom build | `nvidia/cuda:12.4.0-cudnn9-runtime-ubuntu22.04` |

---

## Common Issues

### Flash Attention Install Fails
```bash
# Install CUDA toolkit
apt-get install -y cuda-toolkit-12-4

# Reinstall with limited jobs
MAX_JOBS=4 uv pip install flash-attn --no-build-isolation
```

### CUDA Out of Memory
```python
# Reduce batch size
per_device_train_batch_size=8

# Enable gradient checkpointing
model.gradient_checkpointing_enable()

# Clear cache
torch.cuda.empty_cache()
```

### SSH Disconnects
```bash
# Use screen/tmux
screen -S job_name
# Run command
# Detach: Ctrl+A, D
# Reattach: screen -r job_name
```

---

## Cost Optimization

### Choose Right Instance
- OCR (experimentation): RTX 3090 @ $0.20-0.40/hr
- OCR (production): A100 40GB @ $0.80-1.50/hr
- Training (small): RTX 3090 @ $0.20-0.40/hr
- Training (large): A100 40GB @ $0.80-1.50/hr

### Minimize Runtime
- Test locally first
- Use interruptible instances for short jobs
- Use on-demand for training >4 hours
- Destroy instance immediately after downloading results

### Estimated Costs (Interruptible)
- OCR 100 PDFs (RTX 3090, 4hr): $1.60
- Train ModernBERT (A100, 8hr): $12.00

---

## Batch Size Guidelines

| GPU | VRAM | ModernBERT Batch Size |
|-----|------|-----------------------|
| RTX 3090 | 24GB | 8-16 |
| A100 40GB | 40GB | 16-32 |
| A100 80GB | 80GB | 32-64 |
| H100 | 80GB | 64-128 |

---

## Before Destroying Instance

```bash
# 1. Create archive
ssh -p <PORT> root@<IP> "cd /workspace && tar -czf results.tar.gz models/ results/ logs/"

# 2. Download
scp -P <PORT> root@<IP>:/workspace/results.tar.gz /local/

# 3. Verify
tar -tzf results.tar.gz | head -20

# 4. Destroy
vastai destroy instance <ID>
```

---

## Emergency Recovery

### If Instance Interrupted
```bash
# 1. Download latest checkpoint from S3
aws s3 sync s3://bucket/models/ /workspace/models/

# 2. Find latest checkpoint
ls -td /workspace/models/checkpoint-* | head -1

# 3. Resume training
uv run python scripts/training/train_modernbert_classifier.py \
  --resume-from-checkpoint /workspace/models/checkpoint-500
```

---

**Full Guide:** [VAST_AI_DEPLOYMENT_GUIDE.md](VAST_AI_DEPLOYMENT_GUIDE.md)

**Last Updated:** 2025-10-24

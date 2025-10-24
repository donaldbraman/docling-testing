# Vast.ai Deployment Guide for body-extractor

Complete guide for deploying and using the body-extractor Docker image on vast.ai GPU instances.

## Overview

**Docker Image:** `donaldbraman/body-extractor:latest`
**Purpose:** EasyOCR text extraction from PDFs on cloud GPUs
**Typical Cost:** $0.07-0.15/hour for RTX 3060/3070 GPUs

---

## Prerequisites

1. **Vast.ai Account**
   - Sign up at https://cloud.vast.ai
   - Add funds (minimum $10 recommended)
   - Get API key from https://cloud.vast.ai/account/

2. **Local Setup**
   ```bash
   # Install vast.ai CLI
   uv tool install vastai

   # Set API key
   vastai set api-key YOUR_API_KEY

   # Verify installation
   vastai show instances
   ```

3. **SSH Key Setup**
   ```bash
   # Check for existing SSH key
   ls ~/.ssh/id_ed25519.pub

   # If none exists, create one
   ssh-keygen -t ed25519 -C "vastai-deployment"

   # Add to vast.ai (one-time)
   vastai create ssh-key ~/.ssh/id_ed25519.pub -y
   ```

---

## Quick Start

### 1. Search for GPU Instances

```bash
# Search for affordable RTX GPUs with good reliability
vastai search offers 'reliability > 0.95 cuda_vers >= 12.0 gpu_ram >= 12 num_gpus=1' -o 'dph+' | head -20
```

**Recommended criteria:**
- **Reliability:** > 0.95 (99%+ uptime)
- **CUDA:** >= 12.0 (required for PyTorch 2.6)
- **VRAM:** >= 12GB (minimum for EasyOCR)
- **GPU:** RTX 3060/3070/4070 (good value for OCR)
- **Location:** Europe/North America (lower latency)

**Sample output:**
```
ID        CUDA   N  Model        $/hr    Disk  Location
19296795  12.4  1x  RTX_3060     0.0716  384   Poland
21188449  12.7  1x  RTX_3060     0.0733  210   Thailand
```

### 2. Create Instance

```bash
# Replace INSTANCE_ID with ID from search results
vastai create instance INSTANCE_ID \
  --image donaldbraman/body-extractor:latest \
  --disk 40 \
  --ssh
```

**Output:**
```
Started. {'success': True, 'new_contract': 27233335}
```

Note the contract ID (your instance ID).

### 3. Monitor Instance Startup

```bash
# Create monitoring script
cat > monitor_vastai.py << 'EOF'
#!/usr/bin/env python3
import subprocess, time, sys

INSTANCE_ID = "27233335"  # Replace with your instance ID
MAX_CHECKS = 60
CHECK_INTERVAL = 15

print(f"Monitoring instance {INSTANCE_ID} until running...\n")

for i in range(1, MAX_CHECKS + 1):
    result = subprocess.run(
        ["vastai", "show", "instances"],
        capture_output=True, text=True, check=True
    )

    for line in result.stdout.split('\n'):
        if INSTANCE_ID in line:
            parts = line.split()
            if len(parts) >= 3:
                status = parts[2]
                print(f"[{time.strftime('%H:%M:%S')}] Check {i}/{MAX_CHECKS}: Status={status}")

                if status == "running":
                    print("\n✅ Instance is RUNNING!\n")
                    print(result.stdout)
                    sys.exit(0)
            break

    if i < MAX_CHECKS:
        time.sleep(CHECK_INTERVAL)

print("\n⚠️  Instance still not running")
subprocess.run(["vastai", "show", "instances"])
EOF

# Run monitor
uv run python monitor_vastai.py
```

**Expected time:** 1-3 minutes for instance startup

### 4. Attach SSH Key to Instance

**IMPORTANT:** Must be done after instance starts

```bash
# Attach your SSH key to the running instance
vastai attach ssh INSTANCE_ID "$(cat ~/.ssh/id_ed25519.pub)"
```

**Output:**
```
{'success': True, 'msg': 'SSH key added to instance.'}
```

### 5. Get SSH Connection Info

```bash
# Show instance details
vastai show instances

# Look for SSH_Addr and SSH_Port columns
# Example: ssh6.vast.ai, 33334
```

### 6. Connect via SSH

```bash
# Connect (use -i flag to specify key explicitly)
ssh -i ~/.ssh/id_ed25519 -p PORT root@HOST

# Example:
ssh -i ~/.ssh/id_ed25519 -p 33334 root@ssh6.vast.ai
```

### 7. Verify Environment

```bash
# Once connected, verify setup
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python3 -c "import easyocr; print('EasyOCR installed')"
nvidia-smi
```

**Expected output:**
```
CUDA available: True
EasyOCR installed
NVIDIA GeForce RTX 3060, 12288 MiB
```

---

## Running OCR Extraction

### Upload PDFs to Instance

```bash
# From your local machine
rsync -avz -e 'ssh -i ~/.ssh/id_ed25519 -p 33334' \
  data/v3_data/raw_pdf/*.pdf \
  root@ssh6.vast.ai:/workspace/data/
```

### Run EasyOCR

```bash
# SSH into instance
ssh -i ~/.ssh/id_ed25519 -p 33334 root@ssh6.vast.ai

# Run OCR on a single PDF
cd /workspace
python3 << 'EOF'
import easyocr
import sys

# Initialize reader (models already pre-downloaded in Docker image)
reader = easyocr.Reader(['en'], gpu=True)

# Read PDF
pdf_path = '/workspace/data/your_file.pdf'
result = reader.readtext(pdf_path)

# Print results
for (bbox, text, prob) in result:
    print(f"[{prob:.2f}] {text}")
EOF
```

### Batch Processing

```bash
# Process multiple PDFs
cd /workspace
for pdf in data/*.pdf; do
  echo "Processing $pdf..."
  python3 your_extraction_script.py --input "$pdf" --output "results/$(basename $pdf .pdf).json"
done
```

### Download Results

```bash
# From your local machine
rsync -avz -e 'ssh -i ~/.ssh/id_ed25519 -p 33334' \
  root@ssh6.vast.ai:/workspace/results/ \
  ./results_vastai/
```

---

## Instance Management

### Check Instance Status

```bash
vastai show instances
```

**Status values:**
- `loading` - Downloading Docker image
- `running` - Ready to use
- `stopped` - Paused (not charged)
- `exited` - Terminated

### Stop Instance (Pause Billing)

```bash
vastai stop instance INSTANCE_ID
```

**Note:** You're only charged when status is `running`

### Start Stopped Instance

```bash
vastai start instance INSTANCE_ID
```

### Destroy Instance (Permanent)

```bash
vastai destroy instance INSTANCE_ID
```

**WARNING:** This deletes all data on the instance!

### Monitor Costs

```bash
# Show current usage
vastai show instances

# Check billing
vastai show invoices | head -20
```

---

## Troubleshooting

### SSH Connection Fails

**Problem:** `Permission denied (publickey)`

**Solution:**
```bash
# 1. Verify SSH key is added to vast.ai
vastai show ssh-keys

# 2. Re-attach key to instance
vastai attach ssh INSTANCE_ID "$(cat ~/.ssh/id_ed25519.pub)"

# 3. Connect with explicit key
ssh -i ~/.ssh/id_ed25519 -p PORT root@HOST
```

### Instance Stuck in "loading"

**Problem:** Instance status doesn't change to "running"

**Causes:**
- Docker image download can take 3-5 minutes
- Slow network on host machine
- Host machine issues

**Solution:**
```bash
# Wait 5-10 minutes total
# If still stuck, destroy and create new instance
vastai destroy instance INSTANCE_ID
vastai create instance NEW_INSTANCE_ID --image donaldbraman/body-extractor:latest --disk 40 --ssh
```

### CUDA Not Available

**Problem:** `torch.cuda.is_available()` returns `False`

**Solution:**
```bash
# Check NVIDIA driver
nvidia-smi

# If driver issue, destroy and create new instance with different host
```

### Out of Disk Space

**Problem:** `/workspace` full

**Solution:**
```bash
# Check disk usage
df -h

# Clean up
rm -rf /workspace/data/*.pdf  # After processing
rm -rf /tmp/*

# Or recreate instance with more disk
vastai create instance ID --image donaldbraman/body-extractor:latest --disk 80 --ssh
```

---

## Cost Optimization

### Choose Cheaper Instances

```bash
# Sort by price ($/hour)
vastai search offers 'reliability > 0.90 cuda_vers >= 12.0 gpu_ram >= 12' -o 'dph+' | head -10
```

**Typical pricing:**
- RTX 3060 12GB: $0.07-0.10/hr
- RTX 3070 8GB: $0.10-0.15/hr
- RTX 4070: $0.15-0.25/hr

### Stop When Not Using

```bash
# Always stop when done
vastai stop instance INSTANCE_ID
```

**Example savings:**
- Running 24/7: $0.08/hr × 24 = $1.92/day
- Running 8hr/day: $0.08/hr × 8 = $0.64/day
- **Savings: $1.28/day** ($38/month)

### Use Spot Instances

Vast.ai uses interruptible instances by default (can be reclaimed). For guaranteed uptime, consider dedicated instances (more expensive).

---

## Advanced Usage

### Custom Docker Image

If you modify the Dockerfile:

```bash
# 1. Update Dockerfile.vastai locally
# 2. Push changes to GitHub
git add Dockerfile.vastai
git commit -m "Update Docker image"
git push

# 3. Trigger GitHub Actions build
gh workflow run build-easyocr-image.yml --ref feature/issue-42-text-block-matching

# 4. Wait for build to complete (~6 minutes)
gh run watch

# 5. Create instance with updated image
vastai create instance ID --image donaldbraman/body-extractor:latest --disk 40 --ssh
```

### Persistent Storage

To keep data between instance restarts:

```bash
# Create network volume
vastai create network-volume --size 50 --name body-extractor-data

# Attach to instance when creating
vastai create instance ID \
  --image donaldbraman/body-extractor:latest \
  --disk 40 \
  --ssh \
  --volume-id VOLUME_ID:/data
```

### Multiple Instances

Run parallel OCR jobs:

```bash
# Create 3 instances
for i in {1..3}; do
  vastai create instance $(vastai search offers 'reliability > 0.95 gpu_ram >= 12' -o 'dph+' | head -1 | awk '{print $1}') \
    --image donaldbraman/body-extractor:latest \
    --disk 40 \
    --ssh
done

# Distribute PDFs across instances
# Process in parallel
```

---

## Summary

**Successful Deployment Checklist:**

- [✓] Install vastai CLI via `uv tool install vastai`
- [✓] Set API key via `vastai set api-key`
- [✓] Create/add SSH key via `vastai create ssh-key`
- [✓] Search for instances via `vastai search offers`
- [✓] Create instance via `vastai create instance`
- [✓] Monitor startup until status = `running`
- [✓] Attach SSH key via `vastai attach ssh`
- [✓] Connect via `ssh -i ~/.ssh/id_ed25519 -p PORT root@HOST`
- [✓] Verify CUDA and EasyOCR work
- [✓] Upload PDFs, run OCR, download results
- [✓] Stop instance when done to save costs

**Active Instance:**
- Instance ID: 27233335
- GPU: RTX 3060 (12GB)
- Location: Poland
- Cost: $0.0781/hr
- SSH: `ssh -i ~/.ssh/id_ed25519 -p 33334 root@ssh6.vast.ai`

---

## References

- Vast.ai CLI Docs: https://vast.ai/docs/cli/commands
- Docker Image: https://hub.docker.com/r/donaldbraman/body-extractor
- GitHub Actions: https://github.com/donaldbraman/body-extractor/actions
- EasyOCR Docs: https://github.com/JaidedAI/EasyOCR

---

*Last updated: 2025-10-24*

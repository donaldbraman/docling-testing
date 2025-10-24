# Custom Docker Image for vast.ai Deployments

This guide explains how to build, publish, and use a custom Docker image for vast.ai that includes all dependencies pre-installed.

## Benefits

- **5-10 minute time savings** per deployment (no dependency installation)
- **Pre-downloaded EasyOCR models** (~98MB)
- **Consistent environment** across all deployments
- **Faster iteration** when running multiple experiments

---

## Quick Start

### Using Pre-built Image (Recommended)

```bash
# When creating vast.ai instance, use:
--image docker.io/donaldbraman/docling-easyocr:latest
```

### Building Your Own Image

```bash
# 1. Build the image locally
docker build -f Dockerfile.vastai -t docling-easyocr:latest .

# 2. Test locally (requires NVIDIA GPU)
docker run --gpus all -it docling-easyocr:latest python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# 3. Tag for Docker Hub
docker tag docling-easyocr:latest yourusername/docling-easyocr:latest

# 4. Push to Docker Hub
docker push yourusername/docling-easyocr:latest
```

---

## Detailed Build Instructions

### Prerequisites

- Docker installed locally
- Docker Hub account (free): https://hub.docker.com
- NVIDIA GPU (optional, for local testing)

### Step 1: Build the Image

```bash
cd /path/to/docling-testing

# Build image (takes ~5-10 minutes)
docker build -f Dockerfile.vastai -t docling-easyocr:latest .

# Check image size
docker images docling-easyocr:latest
```

**Expected image size**: ~15-20GB (includes CUDA, PyTorch, EasyOCR models)

### Step 2: Test Locally (Optional)

```bash
# Test CUDA availability
docker run --gpus all -it docling-easyocr:latest \
  python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# Test EasyOCR (models already downloaded)
docker run --gpus all -it docling-easyocr:latest \
  python3 -c "import easyocr; reader = easyocr.Reader(['en'], gpu=True); print('EasyOCR ready!')"

# Interactive shell
docker run --gpus all -it docling-easyocr:latest /bin/bash
```

### Step 3: Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Tag image with your username
docker tag docling-easyocr:latest yourusername/docling-easyocr:latest

# Push to Docker Hub (takes ~10-20 minutes for first push)
docker push yourusername/docling-easyocr:latest
```

### Step 4: Verify on Docker Hub

Visit: https://hub.docker.com/r/yourusername/docling-easyocr

---

## Using Custom Image on vast.ai

### Create Instance with Custom Image

```bash
# Using vastai CLI
uv run vastai create instance INSTANCE_ID \
  --image docker.io/yourusername/docling-easyocr:latest \
  --disk 50 \
  --ssh
```

### Deployment Script

```bash
# Select best instance
INSTANCE_ID=$(uv run python scripts/utilities/select_best_vastai_instance.py --gpu RTX_4090 --auto-select)

# Create with custom image
uv run vastai create instance $INSTANCE_ID \
  --image docker.io/yourusername/docling-easyocr:latest \
  --disk 50 \
  --ssh

echo "Instance created. Waiting for startup..."
sleep 30

# Get SSH connection
SSH_URL=$(uv run vastai ssh-url INSTANCE_ID)

# Upload files and run processing
# (No dependency installation needed!)
```

---

## Alternative: GitHub Container Registry

### Push to ghcr.io

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Tag for GitHub
docker tag docling-easyocr:latest ghcr.io/yourusername/docling-easyocr:latest

# Push
docker push ghcr.io/yourusername/docling-easyocr:latest
```

### Use on vast.ai

```bash
uv run vastai create instance INSTANCE_ID \
  --image ghcr.io/yourusername/docling-easyocr:latest \
  --disk 50 \
  --ssh
```

---

## Image Contents

**Base Image**: `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`

**System Packages**:
- poppler-utils (for pdf2image)
- libgl1-mesa-glx, libglib2.0-0 (for OpenCV)

**Python Packages**:
- easyocr==1.7.2
- pdf2image==1.17.0
- pillow==11.0.0
- pandas==2.3.3
- pymupdf==1.26.5
- rapidfuzz==3.14.1

**Pre-downloaded Models**:
- craft_mlt_25k.pth (83MB) - Text detection
- english_g2.pth (15MB) - Text recognition

---

## Maintenance

### Updating the Image

```bash
# 1. Modify Dockerfile.vastai
vim Dockerfile.vastai

# 2. Rebuild with new tag
docker build -f Dockerfile.vastai -t docling-easyocr:v2 .

# 3. Tag and push
docker tag docling-easyocr:v2 yourusername/docling-easyocr:v2
docker push yourusername/docling-easyocr:v2

# 4. Update 'latest' tag
docker tag docling-easyocr:v2 yourusername/docling-easyocr:latest
docker push yourusername/docling-easyocr:latest
```

### Version Tags

Recommended tagging strategy:
- `latest` - Always points to most recent stable build
- `v1`, `v2`, etc. - Specific versions
- `dev` - Development/testing builds

---

## Troubleshooting

### Image too large for Docker Hub free tier

**Problem**: Free Docker Hub accounts have a 100GB storage limit

**Solution**:
1. Use GitHub Container Registry (unlimited for public repos)
2. Or compress image layers:

```dockerfile
# Combine RUN commands to reduce layers
RUN apt-get update && apt-get install -y poppler-utils && \
    pip install easyocr pandas pymupdf && \
    rm -rf /var/lib/apt/lists/* /root/.cache/pip
```

### CUDA not available in container

**Problem**: `torch.cuda.is_available()` returns False

**Solution**:
- Ensure vast.ai instance has NVIDIA GPU
- Check CUDA version compatibility (needs CUDA 12.0+)
- Verify `--gpus all` flag when testing locally

### EasyOCR models not pre-downloaded

**Problem**: First OCR run still downloads models

**Solution**:
- Check Dockerfile RUN command that downloads models
- Ensure `easyocr.Reader(['en'], gpu=False)` runs during build
- Check Docker build logs for download confirmation

---

## Cost Analysis

### With Custom Image
- **Instance startup**: 30 seconds
- **Dependency installation**: 0 seconds (pre-installed)
- **Total setup time**: 30 seconds

### Without Custom Image (Standard pytorch image)
- **Instance startup**: 30 seconds
- **System dependencies**: 60 seconds (apt-get install)
- **Python dependencies**: 180 seconds (pip install)
- **EasyOCR model download**: 60 seconds (98MB)
- **Total setup time**: 5.5 minutes

### Savings
- **Time saved**: 5 minutes per deployment
- **Cost saved**: $0.025 per deployment @ $0.30/hr RTX 4090
- **Break-even**: After 2-3 deployments

---

## Example: Full Deployment Workflow

```bash
#!/bin/bash
# deploy_to_vastai_custom.sh

# 1. Select instance
INSTANCE_ID=$(uv run python scripts/utilities/select_best_vastai_instance.py --gpu RTX_4090 --auto-select)

# 2. Create with custom image (FAST - no dependency installation!)
uv run vastai create instance $INSTANCE_ID \
  --image docker.io/donaldbraman/docling-easyocr:latest \
  --disk 50 \
  --ssh

echo "Waiting for instance startup (30 seconds)..."
sleep 30

# 3. Get SSH details
SSH_PORT=$(uv run vastai ssh-url $INSTANCE_ID | grep -oP '(?<=-p )\d+')
SSH_HOST=$(uv run vastai ssh-url $INSTANCE_ID | grep -oP '(?<=root@)[^:]+')

# 4. Upload files (dependencies already installed!)
rsync -avz -e "ssh -p $SSH_PORT" data/v3_data/raw_pdf/*.pdf root@$SSH_HOST:/workspace/
rsync -avz -e "ssh -p $SSH_PORT" scripts/ root@$SSH_HOST:/workspace/scripts/

# 5. Run processing (starts immediately!)
ssh -p $SSH_PORT root@$SSH_HOST 'cd /workspace && python3 scripts/extract_with_easyocr.py --pdf my_document --dpi 300'

# 6. Download results
mkdir -p results_vastai
rsync -avz -e "ssh -p $SSH_PORT" root@$SSH_HOST:/workspace/results/ ./results_vastai/

# 7. Destroy instance
uv run vastai destroy instance $INSTANCE_ID

echo "Total deployment time: ~2 minutes (vs 7+ minutes without custom image)"
```

---

## Next Steps

1. **Build and push** your custom image to Docker Hub
2. **Update deployment scripts** to use custom image
3. **Test with 1 PDF** to verify everything works
4. **Scale to 50 PDFs** with confidence

---

*Last updated: 2025-10-24*

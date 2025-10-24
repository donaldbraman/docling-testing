#!/bin/bash
# Quick test deployment for 1 PDF on vast.ai RTX 4090
# Usage: ./scripts/utilities/vastai_quick_test.sh

set -e

echo "========================================="
echo "VAST.AI QUICK TEST - 1 PDF DEPLOYMENT"
echo "========================================="
echo ""

# Configuration
PDF_NAME="texas_law_review_extraterritoriality-patent-infringement"
GPU_TYPE="RTX_4090"
MAX_PRICE="0.40"  # Max $0.40/hour

echo "Configuration:"
echo "  PDF: ${PDF_NAME}"
echo "  Target GPU: ${GPU_TYPE}"
echo "  Max price: \$${MAX_PRICE}/hour"
echo ""

# Step 1: Search for available instances
echo "Step 1: Searching for available RTX 4090 instances..."
uv run vastai search offers \
  "reliability > 0.95 cuda_vers >= 12.0 gpu_name ~ ${GPU_TYPE} dph < ${MAX_PRICE} num_gpus=1" \
  -o 'dph+' | head -20

echo ""
read -p "Enter instance ID to rent (or 'q' to quit): " INSTANCE_ID

if [ "$INSTANCE_ID" = "q" ]; then
    echo "Cancelled."
    exit 0
fi

# Step 2: Create instance
echo ""
echo "Step 2: Creating instance ${INSTANCE_ID}..."
uv run vastai create instance ${INSTANCE_ID} \
  --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  --disk 50 \
  --ssh

echo "Waiting for instance to start (30 seconds)..."
sleep 30

# Step 3: Get SSH connection info
echo ""
echo "Step 3: Getting SSH connection info..."
SSH_CMD=$(uv run vastai ssh-url ${INSTANCE_ID})
echo "SSH command: ${SSH_CMD}"

# Extract port and host from SSH command
# Format: ssh -p PORT root@HOST -L 8080:localhost:8080
PORT=$(echo $SSH_CMD | grep -oP '(?<=-p )\d+')
HOST=$(echo $SSH_CMD | grep -oP '(?<=root@)[^ ]+')

echo "  Port: ${PORT}"
echo "  Host: ${HOST}"

# Step 4: Install dependencies
echo ""
echo "Step 4: Installing dependencies on instance..."
ssh -p ${PORT} root@${HOST} << 'ENDSSH'
set -e
apt-get update && apt-get install -y poppler-utils
pip install --no-cache-dir easyocr pdf2image pillow
python3 -c "import easyocr; reader = easyocr.Reader(['en'], gpu=True); print('EasyOCR ready!')"
ENDSSH

# Step 5: Upload PDF and script
echo ""
echo "Step 5: Uploading PDF and script..."
rsync -avz -e "ssh -p ${PORT}" \
  data/v3_data/raw_pdf/${PDF_NAME}.pdf \
  root@${HOST}:/workspace/

rsync -avz -e "ssh -p ${PORT}" \
  scripts/corpus_building/extract_with_easyocr.py \
  root@${HOST}:/workspace/

# Step 6: Run OCR
echo ""
echo "Step 6: Running EasyOCR on instance..."
echo "Starting processing..."
START_TIME=$(date +%s)

ssh -p ${PORT} root@${HOST} << ENDSSH
cd /workspace
python3 extract_with_easyocr.py --pdf ${PDF_NAME} --dpi 300
ENDSSH

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo "Processing completed in ${ELAPSED} seconds!"

# Step 7: Download results
echo ""
echo "Step 7: Downloading results..."
mkdir -p results/vastai_test/

rsync -avz -e "ssh -p ${PORT}" \
  root@${HOST}:/workspace/*_blocks_*.csv \
  results/vastai_test/

echo "Results downloaded to: results/vastai_test/"

# Step 8: Show cost
echo ""
echo "Step 8: Checking instance cost..."
uv run vastai show instance ${INSTANCE_ID}

echo ""
read -p "Destroy instance now? (y/n): " DESTROY

if [ "$DESTROY" = "y" ]; then
    echo "Destroying instance ${INSTANCE_ID}..."
    uv run vastai destroy instance ${INSTANCE_ID}
    echo "Instance destroyed!"
else
    echo ""
    echo "Instance still running. To destroy later:"
    echo "  uv run vastai destroy instance ${INSTANCE_ID}"
fi

echo ""
echo "========================================="
echo "QUICK TEST COMPLETE!"
echo "========================================="
echo "Processing time: ${ELAPSED} seconds"
echo "Results: results/vastai_test/"
echo ""

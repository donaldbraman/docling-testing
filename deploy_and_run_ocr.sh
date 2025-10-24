#!/bin/bash
# Deploy OCR script to vast.ai and run extraction
# Usage: ./deploy_and_run_ocr.sh

set -e

# Configuration
INSTANCE_ID="27233335"
SSH_PORT="33334"
SSH_HOST="ssh6.vast.ai"
SSH_KEY="$HOME/.ssh/id_ed25519"
LOCAL_PDF_DIR="data/v3_data/raw_pdf"
REMOTE_WORK_DIR="/workspace"

echo "════════════════════════════════════════════════════════"
echo "  Body Extractor - Vast.ai OCR Deployment"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Instance: $INSTANCE_ID"
echo "SSH: $SSH_HOST:$SSH_PORT"
echo ""

# Step 1: Upload OCR script
echo "📤 Step 1/4: Uploading OCR extraction script..."
scp -i "$SSH_KEY" -P "$SSH_PORT" \
  scripts/vastai/run_ocr_extraction.py \
  root@"$SSH_HOST":"$REMOTE_WORK_DIR"/
echo "✅ Script uploaded"
echo ""

# Step 2: Upload PDFs
echo "📤 Step 2/4: Uploading PDFs..."
if [ ! -d "$LOCAL_PDF_DIR" ]; then
  echo "❌ PDF directory not found: $LOCAL_PDF_DIR"
  exit 1
fi

PDF_COUNT=$(find "$LOCAL_PDF_DIR" -name "*.pdf" | wc -l)
echo "Found $PDF_COUNT PDFs to upload"

rsync -avz -e "ssh -i $SSH_KEY -p $SSH_PORT" \
  "$LOCAL_PDF_DIR"/*.pdf \
  root@"$SSH_HOST":"$REMOTE_WORK_DIR"/data/

echo "✅ PDFs uploaded"
echo ""

# Step 3: Run OCR extraction
echo "🔄 Step 3/4: Running OCR extraction on vast.ai..."
echo "This may take several minutes depending on PDF count..."
echo ""

ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" << 'ENDSSH'
cd /workspace

# Create output directory
mkdir -p results

# Run OCR extraction
python3 run_ocr_extraction.py \
  --batch \
  --input-dir ./data \
  --output-dir ./results

echo ""
echo "✅ OCR extraction complete!"
echo ""
echo "Results:"
ls -lh results/
ENDSSH

echo ""
echo "✅ Extraction completed on remote instance"
echo ""

# Step 4: Download results
echo "📥 Step 4/4: Downloading results..."
mkdir -p results_vastai

rsync -avz -e "ssh -i $SSH_KEY -p $SSH_PORT" \
  root@"$SSH_HOST":"$REMOTE_WORK_DIR"/results/ \
  results_vastai/

echo "✅ Results downloaded to: results_vastai/"
echo ""

# Show summary
echo "════════════════════════════════════════════════════════"
echo "  ✅ OCR EXTRACTION COMPLETE"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Results location: ./results_vastai/"
echo ""
echo "Generated files per PDF:"
echo "  • .txt        - Plain text extraction"
echo "  • .json       - JSON with bounding boxes and confidence"
echo "  • .csv        - CSV with coordinates"
echo "  • _annotated.pdf - PDF with OCR annotations"
echo ""
echo "To view results:"
echo "  ls -lh results_vastai/"
echo "  cat results_vastai/yourfile.txt"
echo "  open results_vastai/yourfile_annotated.pdf"
echo ""

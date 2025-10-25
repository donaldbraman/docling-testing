#!/bin/bash
# Run OCR + Classification on vast.ai with lightweight Ubuntu + runtime install
# Uses uv for 10-100x faster dependency installation
set -e

# Parse arguments
TEST_PDF="${1:-test_corpus/law_reviews/Jackson_2014.pdf}"
MODEL_PATH="${2:-models/doclingbert-v2-rebalanced/final_model}"
OUTPUT_DIR="${3:-results_classified}"
SSH_KEY="${4:-$HOME/.ssh/id_ed25519}"
GPU_TYPE="${5:-RTX_4090}"  # RTX_4090, RTX_3090, etc.

# Robust file upload function with fallback methods
# Based on VASTAI_BEST_PRACTICES.md
upload_file() {
    local LOCAL_FILE="$1"
    local REMOTE_PATH="$2"
    local SSH_OPTS="-i $SSH_KEY -p $SSH_PORT -o ConnectTimeout=10 -o StrictHostKeyChecking=no"

    # Method 1: rsync (most robust, resumable)
    echo "   Trying rsync..."
    if rsync -avz --partial --timeout=300 -e "ssh $SSH_OPTS" \
         "$LOCAL_FILE" root@"$SSH_HOST":"$REMOTE_PATH" 2>/dev/null; then
        return 0
    fi

    # Method 2: Legacy SCP with -O flag (works with vast.ai ASCII art)
    echo "   rsync failed, trying legacy SCP..."
    if scp -O -q $SSH_OPTS "$LOCAL_FILE" root@"$SSH_HOST":"$REMOTE_PATH" 2>/dev/null; then
        return 0
    fi

    # Method 3: SSH pipe (always works, bypasses SCP protocol)
    echo "   SCP failed, trying SSH pipe..."
    local REMOTE_FILE=$(basename "$REMOTE_PATH")
    local REMOTE_DIR=$(dirname "$REMOTE_PATH")
    if cat "$LOCAL_FILE" | ssh $SSH_OPTS root@"$SSH_HOST" \
         "mkdir -p $REMOTE_DIR && cat > $REMOTE_PATH" 2>/dev/null; then
        return 0
    fi

    echo "   ❌ All upload methods failed"
    return 1
}

echo "════════════════════════════════════════════════════════"
echo "  Body Extractor - OCR + Classification Test (vast.ai)"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Test PDF:    $TEST_PDF"
echo "Model:       $MODEL_PATH"
echo "Output Dir:  $OUTPUT_DIR"
echo "SSH Key:     $SSH_KEY"
echo "GPU Type:    $GPU_TYPE"
echo ""

# Validate inputs
if [ ! -f "$TEST_PDF" ]; then
  echo "❌ Test PDF not found: $TEST_PDF"
  echo ""
  echo "Usage: $0 [TEST_PDF] [MODEL_PATH] [OUTPUT_DIR] [SSH_KEY] [GPU_TYPE]"
  echo ""
  echo "Arguments:"
  echo "  TEST_PDF       Path to PDF to process"
  echo "                 Default: test_corpus/law_reviews/Jackson_2014.pdf"
  echo "  MODEL_PATH     Path to trained model"
  echo "                 Default: models/doclingbert-v2-rebalanced/final_model"
  echo "  OUTPUT_DIR     Directory for results"
  echo "                 Default: results_classified"
  echo "  SSH_KEY        Path to SSH private key"
  echo "                 Default: ~/.ssh/id_ed25519"
  echo "  GPU_TYPE       vast.ai GPU type"
  echo "                 Default: RTX_4090"
  echo ""
  echo "Example:"
  echo "  $0"
  echo "  $0 test.pdf models/mymodel results/test ~/.ssh/id_rsa RTX_3090"
  exit 1
fi

if [ ! -d "$MODEL_PATH" ]; then
  echo "❌ Model not found: $MODEL_PATH"
  exit 1
fi

if [ ! -f "$SSH_KEY" ]; then
  echo "❌ SSH key not found: $SSH_KEY"
  exit 1
fi

# Extract PDF basename for remote operations
PDF_BASENAME=$(basename "$TEST_PDF")

# Create vast.ai instance with lightweight Ubuntu image (fast startup)
echo "🚀 Creating vast.ai instance..."
echo "   Image: ubuntu:22.04 (fast startup)"
echo "   GPU: $GPU_TYPE"
echo "   Storage: 20GB"
echo ""

# Step 1: Find best offer (prioritize reliability > price)
echo "   Searching for best offer..."
OFFER_ID=$(vastai search offers "reliability > 0.99 gpu_name=$GPU_TYPE disk_space > 20 inet_down > 100" --raw | \
    jq -r 'sort_by(-(.reliability * 100) + .dph_total) | .[0].id')

if [ -z "$OFFER_ID" ] || [ "$OFFER_ID" = "null" ]; then
    echo "❌ No suitable offers found"
    echo "   Try: vastai search offers 'reliability > 0.98 gpu_name=$GPU_TYPE disk_space > 20'"
    exit 1
fi

echo "   Found offer: $OFFER_ID"

# Step 2: Create instance from offer
INSTANCE_ID=$(vastai create instance "$OFFER_ID" --image ubuntu:22.04 --disk 20 2>&1 | \
    grep -oE "'new_contract': [0-9]+" | grep -oE "[0-9]+")

if [ -z "$INSTANCE_ID" ]; then
    echo "❌ Failed to create vast.ai instance from offer $OFFER_ID"
    exit 1
fi

echo "✅ Created instance: $INSTANCE_ID"
echo ""

# Cleanup function for errors
cleanup() {
    echo ""
    echo "🗑️  Cleaning up vast.ai instance..."
    vastai destroy instance "$INSTANCE_ID"
    echo "✅ Instance destroyed"
}

trap cleanup EXIT

# Wait for instance to be running
echo "⏳ Waiting for instance to start (Ubuntu images start in ~30 seconds)..."
for i in {1..20}; do
    sleep 5
    STATUS=$(vastai show instance $INSTANCE_ID 2>&1 | tail -1 | awk '{print $3}')
    echo "   Attempt $i/20: Status = $STATUS"

    if [ "$STATUS" = "running" ]; then
        echo "✅ Instance is running"
        break
    fi

    if [ $i -eq 20 ]; then
        echo "❌ Instance failed to start after 100 seconds"
        exit 1
    fi
done

echo ""

# Get SSH connection info
echo "🔍 Getting SSH connection details..."
SSH_INFO=$(vastai show instances | grep $INSTANCE_ID)
SSH_HOST=$(echo "$SSH_INFO" | awk '{print $10}')
SSH_PORT=$(echo "$SSH_INFO" | awk '{print $11}')

if [ -z "$SSH_HOST" ] || [ -z "$SSH_PORT" ]; then
    echo "❌ Failed to get SSH connection info"
    exit 1
fi

echo "✅ SSH connection: root@$SSH_HOST:$SSH_PORT"
echo ""

# Attach SSH key
echo "🔑 Attaching SSH key..."
vastai attach ssh $INSTANCE_ID "$(cat $SSH_KEY.pub)" > /dev/null 2>&1
sleep 5
echo "✅ SSH key attached"
echo ""

# Test SSH connection
echo "🔌 Testing SSH connection..."
for i in {1..10}; do
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p "$SSH_PORT" -i "$SSH_KEY" \
           root@"$SSH_HOST" "echo 'SSH test successful'" 2>/dev/null | grep -q "SSH test successful"; then
        echo "✅ SSH connection established"
        break
    fi
    echo "   Attempt $i/10: Connection failed, retrying..."
    sleep 5

    if [ $i -eq 10 ]; then
        echo "❌ SSH connection failed after 10 attempts"
        exit 1
    fi
done

echo ""

# Install dependencies with uv (10-100x faster than pip)
echo "📦 Step 1/6: Installing dependencies with uv..."
echo "   This takes ~25-30 seconds with uv (vs 5+ minutes with pip)"
echo ""

ssh -o StrictHostKeyChecking=no -p "$SSH_PORT" -i "$SSH_KEY" root@"$SSH_HOST" bash << 'ENDSSH'
set -e
export DEBIAN_FRONTEND=noninteractive

# Install system dependencies
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq curl python3-pip python3-venv libgl1 libglib2.0-0 > /dev/null 2>&1

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh > /dev/null 2>&1
export PATH="/root/.local/bin:$PATH"

# Create virtual environment and install packages
mkdir -p /workspace
cd /workspace
uv venv venv > /dev/null 2>&1
source venv/bin/activate

# Install all dependencies (takes ~25 seconds with uv)
uv pip install --quiet \
    torch==2.1.0 \
    transformers==4.50.0 \
    easyocr==1.7.2 \
    opencv-python-headless==4.11.0.86 \
    pypdfium2==4.30.1 \
    pymupdf==1.26.5 \
    "pillow>=10.0.0" \
    "numpy<2"

echo "✅ Dependencies installed"
ENDSSH

echo ""
echo "📤 Step 2/6: Uploading classification script..."
if ! upload_file scripts/vastai/run_ocr_with_classification.py /workspace/run_ocr_with_classification.py; then
    echo "❌ Failed to upload classification script"
    exit 1
fi
echo "✅ Done"

echo ""
echo "📤 Step 3/6: Uploading ModernBERT model (~500MB, may take 30-60 sec)..."
ssh -o StrictHostKeyChecking=no -p "$SSH_PORT" -i "$SSH_KEY" root@"$SSH_HOST" \
    "mkdir -p /workspace/models/doclingbert-v2-rebalanced"
rsync -avz --progress -e "ssh -o StrictHostKeyChecking=no -p $SSH_PORT -i $SSH_KEY" \
  "$MODEL_PATH"/ \
  root@"$SSH_HOST":/workspace/models/doclingbert-v2-rebalanced/final_model/ | grep -E "(sent|speedup|total)"
echo "✅ Done"

echo ""
echo "📤 Step 4/6: Uploading PDF..."
ssh -o StrictHostKeyChecking=no -p "$SSH_PORT" -i "$SSH_KEY" root@"$SSH_HOST" \
    "mkdir -p /workspace/test_input"
if ! upload_file "$TEST_PDF" "/workspace/test_input/$PDF_BASENAME"; then
    echo "❌ Failed to upload PDF"
    exit 1
fi
echo "✅ Done"

echo ""
echo "🔄 Step 5/6: Running OCR + Classification..."
echo "   Note: First run downloads EasyOCR models (~250-300MB), subsequent runs are fast"
echo ""

ssh -o StrictHostKeyChecking=no -p "$SSH_PORT" -i "$SSH_KEY" root@"$SSH_HOST" bash << ENDSSH
set -e
export PATH="/root/.local/bin:$PATH"
cd /workspace
source venv/bin/activate

START=\$(date +%s)

python3 run_ocr_with_classification.py \
  --input ./test_input/$PDF_BASENAME \
  --output-dir ./test_results \
  --model-path ./models/doclingbert-v2-rebalanced/final_model

END=\$(date +%s)
DURATION=\$((END - START))

echo ""
echo "✅ Processing complete in \${DURATION}s!"
echo ""
echo "Generated files:"
ls -lh test_results/
ENDSSH

echo ""
echo "📥 Step 6/6: Downloading results..."
mkdir -p "$OUTPUT_DIR"

rsync -avz -e "ssh -o StrictHostKeyChecking=no -p $SSH_PORT -i $SSH_KEY" \
  root@"$SSH_HOST":/workspace/test_results/ \
  "$OUTPUT_DIR/" | grep -E "(sent|speedup|total)"

echo "✅ Results downloaded"
echo ""

# Trap will handle cleanup
echo "════════════════════════════════════════════════════════"
echo "  ✅ CLASSIFICATION TEST COMPLETE"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Results in: $OUTPUT_DIR/"
echo ""
ls -lh "$OUTPUT_DIR/"
echo ""
echo "Generated outputs:"
echo "  1. Plain text:           *.txt"
echo "  2. Text overlay PDF:     *_text_overlay.pdf"
echo "  3. Class overlay PDF:    *_class_overlay.pdf"
echo "  4. CSV with classes:     *.csv"
echo "  5. Full JSON metadata:   *.json"
echo ""
echo "View results:"
echo "  cat $OUTPUT_DIR/*.txt"
echo "  open $OUTPUT_DIR/*_text_overlay.pdf"
echo "  open $OUTPUT_DIR/*_class_overlay.pdf"
echo "  cat $OUTPUT_DIR/*.csv | column -t -s,"
echo ""

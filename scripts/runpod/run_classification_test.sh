#!/bin/bash
# Run OCR + Classification on RunPod with auto-cleanup
set -e

# Parse arguments
TEST_PDF="${1:-test_corpus/law_reviews/Jackson_2014.pdf}"
MODEL_PATH="${2:-models/doclingbert-v2-rebalanced/final_model}"
OUTPUT_DIR="${3:-results_classified}"
SSH_KEY="${4:-$HOME/.ssh/id_ed25519}"
GPU_TYPE="${5:-NVIDIA RTX 3090}"  # Default to RTX 3090 (cheapest reliable option)

# Robust file upload function with fallback methods
# Based on VASTAI_BEST_PRACTICES.md - works for RunPod too
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

    # Method 2: Legacy SCP with -O flag
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
echo "  Body Extractor - OCR + Classification Test (RunPod)"
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
  echo "  GPU_TYPE       RunPod GPU type"
  echo "                 Default: NVIDIA RTX 3090"
  echo ""
  echo "Example:"
  echo "  $0"
  echo "  $0 test.pdf models/mymodel results/test ~/.ssh/id_rsa 'NVIDIA RTX 4090'"
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

# Create RunPod instance
echo "🚀 Creating RunPod instance..."
echo "   Image: PyTorch 2.1.0 with CUDA 12.1"
echo "   GPU: $GPU_TYPE"
echo "   Storage: 80GB"
echo ""

POD_ID=$(runpod pod create \
  --name "body-extractor-test" \
  --imageName "runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel-ubuntu22.04" \
  --gpuTypeId "$GPU_TYPE" \
  --cloudType COMMUNITY \
  --volumeSize 80 \
  --ports "22/tcp" 2>&1 | grep -oP 'Pod created: \K[a-z0-9]+' || echo "")

if [ -z "$POD_ID" ]; then
    echo "❌ Failed to create RunPod instance"
    echo "   Check: runpod pod list"
    exit 1
fi

echo "✅ Created pod: $POD_ID"
echo ""

# Cleanup function for errors
cleanup() {
    echo ""
    echo "🗑️  Cleaning up RunPod instance..."
    runpod pod terminate "$POD_ID"
    echo "✅ Instance terminated"
}

trap cleanup EXIT

# Wait for pod to be ready
echo "⏳ Waiting for pod to start (may take 30-60 seconds)..."
for i in {1..20}; do
    sleep 10
    STATUS=$(runpod pod get "$POD_ID" 2>&1 | grep -oP 'status: \K\w+' || echo "unknown")
    echo "   Attempt $i/20: Status = $STATUS"

    if [ "$STATUS" = "running" ] || [ "$STATUS" = "RUNNING" ]; then
        echo "✅ Pod is running"
        break
    fi

    if [ $i -eq 20 ]; then
        echo "❌ Pod failed to start after 200 seconds"
        exit 1
    fi
done

echo ""

# Get SSH connection info
echo "🔍 Getting SSH connection details..."
POD_INFO=$(runpod pod get "$POD_ID" 2>&1)
SSH_HOST=$(echo "$POD_INFO" | grep -oP 'connectTo.*?host: \K[^\s,]+' || echo "")
SSH_PORT=$(echo "$POD_INFO" | grep -oP 'connectTo.*?port: \K\d+' || echo "")

if [ -z "$SSH_HOST" ] || [ -z "$SSH_PORT" ]; then
    echo "❌ Failed to get SSH connection info"
    echo "$POD_INFO"
    exit 1
fi

echo "✅ SSH connection: root@$SSH_HOST:$SSH_PORT"
echo ""

# Test SSH connection
echo "🔑 Testing SSH connection..."
for i in {1..10}; do
    if ssh -i "$SSH_KEY" -p "$SSH_PORT" -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
           root@"$SSH_HOST" "echo 'SSH test successful'" 2>/dev/null; then
        echo "✅ SSH connection established"
        break
    fi
    echo "   Attempt $i/10: Connection failed, retrying..."
    sleep 10

    if [ $i -eq 10 ]; then
        echo "❌ SSH connection failed after 10 attempts"
        exit 1
    fi
done

echo ""

# Install dependencies
echo "📦 Step 1/6: Installing dependencies..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no root@"$SSH_HOST" bash << 'ENDSSH'
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq python3-pip > /dev/null 2>&1

pip3 install -q \
    torch==2.1.0 \
    transformers==4.50.0 \
    easyocr==1.7.2 \
    opencv-python-headless==4.11.0.86 \
    pypdfium2==4.30.1 \
    pillow==11.2.0 \
    > /dev/null 2>&1

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
ssh -i "$SSH_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no root@"$SSH_HOST" "mkdir -p /workspace/models/doclingbert-v2-rebalanced"
rsync -avz --progress -e "ssh -i $SSH_KEY -p $SSH_PORT -o StrictHostKeyChecking=no" \
  "$MODEL_PATH"/ \
  root@"$SSH_HOST":/workspace/models/doclingbert-v2-rebalanced/final_model/
echo "✅ Done"

echo ""
echo "📤 Step 4/6: Uploading PDF..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no root@"$SSH_HOST" "mkdir -p /workspace/test_input"
if ! upload_file "$TEST_PDF" "/workspace/test_input/$PDF_BASENAME"; then
    echo "❌ Failed to upload PDF"
    exit 1
fi
echo "✅ Done"

echo ""
echo "🔄 Step 5/6: Running OCR + Classification..."
echo ""

ssh -i "$SSH_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no root@"$SSH_HOST" bash << ENDSSH
cd /workspace
mkdir -p test_results

python3 run_ocr_with_classification.py \
  --input ./test_input/$PDF_BASENAME \
  --output-dir ./test_results \
  --model-path ./models/doclingbert-v2-rebalanced/final_model

echo ""
echo "Generated files:"
ls -lh test_results/
ENDSSH

echo ""
echo "📥 Step 6/6: Downloading results..."
mkdir -p "$OUTPUT_DIR"

rsync -avz -e "ssh -i $SSH_KEY -p $SSH_PORT -o StrictHostKeyChecking=no" \
  root@"$SSH_HOST":/workspace/test_results/ \
  "$OUTPUT_DIR/"

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

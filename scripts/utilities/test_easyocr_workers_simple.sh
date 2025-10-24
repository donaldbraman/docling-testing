#!/usr/bin/env bash
# Simple sequential test of EasyOCR worker configurations
# Tests workers=0, 4, 8 sequentially on same PDF to find optimal config

set -e

PDF_NAME="afrofuturism_in_protest__dissent_and_revolution"
TEST_WORKERS=(0 4 8)

echo "==========================================="
echo "EASYOCR WORKER OPTIMIZATION TEST"
echo "==========================================="
echo ""
echo "Testing configurations: ${TEST_WORKERS[@]}"
echo "PDF: $PDF_NAME (92 pages)"
echo ""

# Find best RTX 4090 instance
echo "Finding best available RTX 4090 instance..."
INSTANCE_ID=$(uv run vastai search offers 'gpu_name=RTX_4090' -o 'dph+' --raw | \
    python3 -c "import json, sys; data = json.load(sys.stdin); print([i['id'] for i in data[:1] if i.get('reliability2', 0) > 0.98][0])")

echo "Selected instance: $INSTANCE_ID"
echo ""

# Test each configuration
for WORKERS in "${TEST_WORKERS[@]}"; do
    echo "==========================================="
    echo "Testing EASYOCR_WORKERS=$WORKERS"
    echo "==========================================="

    # Create instance
    echo "Creating instance..."
    CREATE_OUTPUT=$(uv run vastai create instance $INSTANCE_ID \
        --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
        --disk 20 \
        --ssh)

    CONTRACT_ID=$(echo "$CREATE_OUTPUT" | sed -n 's/.*new_contract[^0-9]*\([0-9]*\).*/\1/p')

    if [ -z "$CONTRACT_ID" ]; then
        echo "Error: Failed to create instance"
        echo "Output: $CREATE_OUTPUT"
        exit 1
    fi

    echo "Contract ID: $CONTRACT_ID"
    echo "Waiting for instance startup (60s)..."
    sleep 60

    # Get SSH port
    SSH_INFO=$(uv run vastai ssh-url $CONTRACT_ID)
    PORT=$(echo $SSH_INFO | sed -n 's/.*:\([0-9]*\).*/\1/p')

    echo "SSH Port: $PORT"

    # Install dependencies with uv
    echo "Installing dependencies..."
    ssh -o StrictHostKeyChecking=no -p $PORT root@ssh9.vast.ai \
        'apt-get update -qq && apt-get install -y poppler-utils curl && \
         curl -LsSf https://astral.sh/uv/install.sh | sh && \
         /root/.cargo/bin/uv pip install --system easyocr pdf2image pillow pandas pymupdf rapidfuzz' 2>&1 | grep -v "debconf"

    # Upload files
    echo "Uploading files..."
    rsync -az -e "ssh -p $PORT -o StrictHostKeyChecking=no" \
        data/v3_data/raw_pdf/${PDF_NAME}.pdf \
        root@ssh9.vast.ai:/workspace/

    rsync -az -e "ssh -p $PORT -o StrictHostKeyChecking=no" \
        scripts/corpus_building/extract_with_easyocr.py \
        root@ssh9.vast.ai:/workspace/

    # Start processing
    echo "Starting EasyOCR (workers=$WORKERS)..."
    START_TIME=$(date +%s)

    ssh -p $PORT root@ssh9.vast.ai \
        "cd /workspace && EASYOCR_WORKERS=$WORKERS python3 extract_with_easyocr.py \
         --pdf ${PDF_NAME} --dpi 300" 2>&1 | tee /tmp/workers_${WORKERS}.log

    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))

    echo ""
    echo "Workers=$WORKERS completed in ${ELAPSED}s"
    echo "$WORKERS $ELAPSED" >> /tmp/worker_results.txt

    # Destroy instance
    echo "Destroying instance $CONTRACT_ID..."
    uv run vastai destroy instance $CONTRACT_ID

    echo ""
    sleep 10
done

echo ""
echo "==========================================="
echo "FINAL RESULTS"
echo "==========================================="
sort -k2 -n /tmp/worker_results.txt | while read WORKERS TIME; do
    echo "Workers=$WORKERS: ${TIME}s"
done

rm -f /tmp/worker_results.txt /tmp/workers_*.log

echo ""
echo "Test complete!"

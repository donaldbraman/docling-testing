# RunPod Setup Guide for body-extractor

**Alternative to vast.ai with better reliability and similar pricing**

## Quick Start

### 1. Create Account
- Visit: https://www.runpod.io/
- Sign up with email or GitHub
- Add payment method (credit card or crypto)
- $10 minimum credit recommended

### 2. Deploy GPU Instance

**Using Web Interface:**
1. Click "Deploy" → "GPU Pods"
2. Choose GPU:
   - **RTX 3090** ($0.34/hr spot, $0.69/hr on-demand) - Recommended
   - **RTX 4090** ($0.69/hr spot, $1.39/hr on-demand) - Best performance
   - **A5000** ($0.39/hr spot) - Good balance
3. Select "Community Cloud" (cheaper) or "Secure Cloud" (more reliable)
4. Choose template: "PyTorch 2.0.1" or "RunPod PyTorch"
5. Storage: 80GB minimum
6. Deploy!

**Using CLI (recommended for automation):**

```bash
# Install RunPod CLI
pip install runpod

# Login
runpod config

# List available GPUs
runpod pod list-gpu-types

# Deploy instance
runpod pod create \
  --name "body-extractor" \
  --image-name "runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel-ubuntu22.04" \
  --gpu-type-id "NVIDIA RTX 3090" \
  --cloud-type COMMUNITY \
  --volume-size 80 \
  --ports "22/tcp,8888/tcp"
```

### 3. Deploy Our Docker Image

**Option A: Use existing Docker image**
```bash
runpod pod create \
  --name "body-extractor" \
  --image-name "donaldbraman/body-extractor:latest" \
  --gpu-type-id "NVIDIA RTX 3090" \
  --cloud-type COMMUNITY \
  --volume-size 80 \
  --ports "22/tcp"
```

**Option B: Build on RunPod**
1. Deploy base PyTorch image
2. SSH into instance
3. Clone repo and build:
```bash
git clone https://github.com/yourusername/body-extractor.git
cd body-extractor
# Copy Dockerfile.vastai and build
docker build -t body-extractor:latest -f Dockerfile.vastai .
```

### 4. Run Classification Test

```bash
# Get pod ID
POD_ID=$(runpod pod list --json | jq -r '.[0].id')

# Get SSH connection info
runpod pod connect $POD_ID

# Upload files (shown in SSH connect output)
scp -P <PORT> -i ~/.ssh/id_rsa \
  scripts/vastai/run_ocr_with_classification.py \
  root@<HOST>:/workspace/

# Upload model
rsync -avz -e "ssh -p <PORT> -i ~/.ssh/id_rsa" \
  models/doclingbert-v2-rebalanced/final_model/ \
  root@<HOST>:/workspace/models/doclingbert-v2-rebalanced/final_model/

# Upload PDF
scp -P <PORT> -i ~/.ssh/id_rsa \
  data/v3_data/raw_pdf/antitrusts_interdependence_paradox.pdf \
  root@<HOST>:/workspace/test_input/

# Run classification
ssh -p <PORT> -i ~/.ssh/id_rsa root@<HOST> \
  "cd /workspace && python3 run_ocr_with_classification.py \
   --input ./test_input/antitrusts_interdependence_paradox.pdf \
   --output-dir ./results \
   --model-path ./models/doclingbert-v2-rebalanced/final_model"

# Download results
scp -P <PORT> -i ~/.ssh/id_rsa -r \
  root@<HOST>:/workspace/results/ \
  ./runpod_results/
```

### 5. Stop Instance

```bash
# Stop pod (preserves data)
runpod pod stop $POD_ID

# Terminate pod (deletes data, stops billing)
runpod pod terminate $POD_ID
```

## Pricing Comparison

| Provider | GPU | Spot Price | On-Demand | Reliability |
|----------|-----|------------|-----------|-------------|
| **RunPod** | RTX 3090 | $0.34/hr | $0.69/hr | ~99% |
| **vast.ai** | RTX 3090 | $0.08-0.15/hr | N/A | 95-100% (varies) |
| **RunPod** | RTX 4090 | $0.69/hr | $1.39/hr | ~99% |
| **vast.ai** | RTX 4090 | $0.15-0.30/hr | N/A | 95-100% (varies) |

**Verdict:**
- **vast.ai**: 50-70% cheaper, but more variable reliability
- **RunPod**: 2-3x more expensive, but more predictable and easier to use

## RunPod Advantages

✅ **Better reliability** - Commercial SLA, ~99% uptime
✅ **Easier to use** - Better UI/UX, simpler SSH
✅ **Persistent storage** - Network volumes available
✅ **Better support** - Discord community, documentation
✅ **Jupyter integration** - Built-in notebooks
✅ **API access** - RESTful API for automation

## RunPod Disadvantages

❌ **More expensive** - 2-3x cost of vast.ai
❌ **Less GPU variety** - Fewer exotic GPU options
❌ **No CPU-only** - GPU required (vast.ai has CPU instances)

## Automation Script

Create `scripts/runpod/deploy_and_test.sh`:

```bash
#!/bin/bash
set -e

# Create RunPod instance
POD_ID=$(runpod pod create \
  --name "body-extractor-test" \
  --image-name "donaldbraman/body-extractor:latest" \
  --gpu-type-id "NVIDIA RTX 3090" \
  --cloud-type COMMUNITY \
  --volume-size 80 \
  --ports "22/tcp" \
  --json | jq -r '.id')

echo "Created pod: $POD_ID"
echo "Waiting for pod to be ready..."
sleep 60

# Get SSH info
SSH_INFO=$(runpod pod connect $POD_ID --json)
SSH_HOST=$(echo "$SSH_INFO" | jq -r '.ssh_host')
SSH_PORT=$(echo "$SSH_INFO" | jq -r '.ssh_port')

echo "SSH: $SSH_HOST:$SSH_PORT"

# Run test
./scripts/vastai/run_classification_test.sh \
  --host $SSH_HOST \
  --port $SSH_PORT \
  --key ~/.ssh/id_rsa

# Cleanup
runpod pod terminate $POD_ID
echo "Pod terminated"
```

## Best Practices

1. **Use Spot Instances** - 50% cheaper than on-demand
2. **Auto-stop** - Set max runtime to avoid surprise bills
3. **Network Volumes** - Use for persistent data (models, datasets)
4. **Template Library** - Save your own templates for quick deployment
5. **Budget Alerts** - Set spending limits in settings

## Links

- **RunPod Dashboard**: https://www.runpod.io/console/pods
- **CLI Docs**: https://docs.runpod.io/cli/overview
- **API Docs**: https://docs.runpod.io/api-reference
- **Pricing**: https://www.runpod.io/console/gpu-cloud
- **Discord**: https://discord.gg/runpod

---

**Next Steps:**
1. Create RunPod account
2. Add $10 credit
3. Deploy test instance
4. Run classification test
5. Compare with vast.ai results

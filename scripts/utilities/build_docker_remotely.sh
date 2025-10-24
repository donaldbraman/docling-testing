#!/usr/bin/env bash
# Build Docker image on vast.ai instance (fast hardware, no local resources)

set -e

INSTANCE_ID="${1:-27226347}"
SSH_PORT="26346"
SSH_HOST="ssh8.vast.ai"
DOCKER_USER="donaldbraman"
IMAGE_NAME="easyocr-test"

echo "Building Docker image on vast.ai instance $INSTANCE_ID..."

# Install Docker on remote instance
ssh -p $SSH_PORT root@$SSH_HOST << 'REMOTE_SETUP'
set -e

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    apt-get update
    apt-get install -y docker.io
    systemctl start docker
fi

# Create workspace
mkdir -p /workspace/build
cd /workspace/build
REMOTE_SETUP

echo "✓ Docker installed on remote instance"

# Copy files needed for build
echo "Copying build files..."
scp -P $SSH_PORT Dockerfile.easyocr-test root@$SSH_HOST:/workspace/build/Dockerfile
scp -P $SSH_PORT scripts/corpus_building/extract_with_easyocr.py root@$SSH_HOST:/workspace/build/

# Copy PDFs
ssh -p $SSH_PORT root@$SSH_HOST 'mkdir -p /workspace/build/data/v3_data/raw_pdf'
scp -P $SSH_PORT \
    data/v3_data/raw_pdf/afrofuturism_in_protest__dissent_and_revolution.pdf \
    data/v3_data/raw_pdf/antitrusts_interdependence_paradox.pdf \
    data/v3_data/raw_pdf/california_law_review_affirmative-asylum.pdf \
    root@$SSH_HOST:/workspace/build/data/v3_data/raw_pdf/

echo "✓ Files copied"

# Build image remotely
echo "Building Docker image on remote (this will be fast on their hardware)..."
ssh -p $SSH_PORT root@$SSH_HOST << REMOTE_BUILD
set -e
cd /workspace/build
docker build -f Dockerfile -t ${DOCKER_USER}/${IMAGE_NAME}:latest .
echo "✓ Build complete"

# Login to Docker Hub and push
echo "Pushing to Docker Hub..."
docker login -u ${DOCKER_USER}
docker push ${DOCKER_USER}/${IMAGE_NAME}:latest
echo "✓ Image pushed to ${DOCKER_USER}/${IMAGE_NAME}:latest"
REMOTE_BUILD

echo "=========================================="
echo "SUCCESS! Image available at:"
echo "docker.io/${DOCKER_USER}/${IMAGE_NAME}:latest"
echo "=========================================="

#!/bin/bash
# Deploy BrainNet to beast server via OpenClaw nodes
# Usage: Run individual commands via nodes tool when beast is connected

set -e
DEST="/home/jake/brainnet"

echo "🚀 Deploying BrainNet to beast..."

# Create directory structure
echo "Creating directories..."
mkdir -p $DEST/{brainnet,tests,scripts}

# Copy all Python files
echo "Copying files..."
for f in brainnet/*.py tests/*.py scripts/*.py scripts/*.sh main.py requirements.txt README.md; do
    if [ -f "$f" ]; then
        cp "$f" "$DEST/$f"
        echo "  ✅ $f"
    fi
done

# Install dependencies
echo "Installing dependencies..."
pip install --break-system-packages -r $DEST/requirements.txt

# Ensure Redis is running
echo "Checking Redis..."
if ! docker ps | grep -q brainnet-redis; then
    docker run -d --name brainnet-redis -p 6379:6379 redis:alpine
fi

# Download models
echo "Downloading models..."
bash $DEST/scripts/download_models.sh

# Run checks
echo "Running checks..."
python3 $DEST/scripts/check_gpu.py

# Run unit tests
echo "Running unit tests..."
cd $DEST
python3 -m tests.test_messages
python3 -m tests.test_cache
python3 -m tests.test_gossip

echo ""
echo "🎉 BrainNet deployed! Run with: cd $DEST && python3 main.py"

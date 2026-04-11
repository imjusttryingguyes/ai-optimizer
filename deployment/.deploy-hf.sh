#!/bin/bash
set -e

echo "🚀 Deploying to HuggingFace Spaces..."

# Check for HF token
if [ -z "$HF_TOKEN" ]; then
    echo "❌ HF_TOKEN not set"
    echo "   Create token at: https://huggingface.co/settings/tokens"
    echo "   export HF_TOKEN='hf_...'"
    exit 1
fi

SPACE_NAME="SamShal1/phase4-analytics"
TEMP_DIR="/tmp/hf-space-$$"

echo "📁 Cloning Space repository..."
git clone https://oauth2:${HF_TOKEN}@huggingface.co/spaces/${SPACE_NAME} "$TEMP_DIR"
cd "$TEMP_DIR"

echo "📝 Copying files..."
cp ../dashboard.py .
cp ../requirements.txt .
mkdir -p .streamlit
cp ../.streamlit/config.toml .streamlit/
mkdir -p results
cp ../results/*.json results/

echo "✅ Files copied"
echo "📊 File sizes:"
ls -lh *.py *.txt
du -sh results/

echo "🔄 Committing changes..."
git add .
git commit -m "Update dashboard with Stage 3 per-campaign analysis

- Updated dashboard.py with JSON-based loading
- New requirements.txt (no DB dependencies)
- Results with 7 campaigns + 87 segment entries
- All segments verified Cost >= threshold"

echo "🚀 Pushing to HuggingFace..."
git push

echo "✨ Deployment complete!"
echo "   Space URL: https://huggingface.co/spaces/${SPACE_NAME}"
echo "   Space will auto-reload in ~30 seconds"

# Cleanup
cd /
rm -rf "$TEMP_DIR"

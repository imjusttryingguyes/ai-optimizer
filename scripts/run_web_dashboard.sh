#!/usr/bin/env bash
set -euo pipefail

# Start the Flask web dashboard in the background
cd /opt/ai-optimizer/web
/opt/ai-optimizer/venv/bin/python app.py &

echo "✅ Web dashboard started on http://0.0.0.0:5000"

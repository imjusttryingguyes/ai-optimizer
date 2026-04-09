#!/bin/bash
set -euo pipefail

cd /opt/ai-optimizer

echo "🚀 Starting AI Optimizer Dashboard..."

# Activate virtual environment
source venv/bin/activate

# Create logs directory if doesn't exist
mkdir -p logs

# Kill any existing Flask process on port 5000
lsof -ti :5000 | xargs kill -9 2>/dev/null || true
sleep 1

# Start Flask in background with output
cd web
nohup python app.py >> ../logs/dashboard.log 2>&1 &

# Wait for server to start
sleep 3

# Check if server is running
if curl -s http://localhost:5000/ > /dev/null 2>&1; then
    echo "✅ Dashboard started successfully!"
    echo "📍 Open: http://localhost:5000"
    echo "📊 Logs: tail -f /opt/ai-optimizer/logs/dashboard.log"
else
    echo "❌ Dashboard failed to start"
    echo "Check logs: cat /opt/ai-optimizer/logs/dashboard.log"
    exit 1
fi

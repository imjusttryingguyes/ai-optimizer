#!/bin/bash
# Start Simple HTTP KPI Dashboard

cd "$(dirname "$0")" || exit 1

# Kill existing process on port 8501 if running
echo "Checking for running instances..."
PID=$(lsof -i :8501 2>/dev/null | tail -1 | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "Stopping existing process (PID: $PID)..."
    kill -9 "$PID" 2>/dev/null
    sleep 1
fi

echo "🚀 Starting KPI Dashboard..."
nohup python3 dashboard_simple.py > dashboard.log 2>&1 &

sleep 2

# Verify it started
if curl -s http://127.0.0.1:8501 > /dev/null 2>&1; then
    echo "✅ Dashboard started successfully!"
    echo ""
    echo "📍 Access URLs:"
    echo "   Local:  http://localhost:8501"
    echo "   Remote: http://127.0.0.1:8501"
    echo "   Network: http://43.245.224.117:8501"
    echo ""
    echo "📊 Features:"
    echo "   ✅ Select account from dropdown"
    echo "   ✅ View KPI status and metrics"
    echo "   ✅ Set monthly KPI targets"
    echo "   ✅ See forecasts and alerts"
    echo ""
    echo "🛑 To stop: kill -9 \$(lsof -i :8501 | tail -1 | awk '{print \$2}')"
else
    echo "❌ Failed to start dashboard"
    echo "Check logs: tail -20 dashboard.log"
    exit 1
fi

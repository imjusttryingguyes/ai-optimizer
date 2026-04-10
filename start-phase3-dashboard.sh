#!/bin/bash
# Start Phase 3 Analytics Dashboard

cd "$(dirname "$0")" || exit 1

# Kill existing process on port 8502 if running
echo "🔍 Checking for running instances on port 8502..."
PID=$(lsof -i :8502 2>/dev/null | tail -1 | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "⏹️  Stopping existing process (PID: $PID)..."
    kill -9 "$PID" 2>/dev/null
    sleep 1
fi

echo "🚀 Starting Phase 3 Analytics Dashboard..."
nohup python3 dashboard_optimized.py > dashboard_phase3.log 2>&1 &

sleep 2

# Verify it started
if curl -s http://127.0.0.1:8502 > /dev/null 2>&1; then
    echo "✅ Dashboard started successfully!"
    echo ""
    echo "📍 Access URLs:"
    echo "   Local:  http://localhost:8502"
    echo "   Remote: http://127.0.0.1:8502"
    echo ""
    echo "📊 Features:"
    echo "   ✅ Select account from dropdown"
    echo "   ✅ View problems and opportunities"
    echo "   ✅ Click on segment → See top-3 campaigns"
    echo "   ✅ Full campaign drill-down analytics"
    echo ""
    echo "📝 Logs:"
    echo "   tail -f dashboard_phase3.log"
    echo ""
    echo "🛑 To stop:"
    echo "   kill -9 \$(lsof -i :8502 | tail -1 | awk '{print \$2}')"
else
    echo "❌ Failed to start dashboard"
    echo "Check logs: tail -20 dashboard_phase3.log"
    exit 1
fi

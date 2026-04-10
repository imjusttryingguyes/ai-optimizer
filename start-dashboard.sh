#!/bin/bash
# Start AI Optimizer Dashboard

cd /opt/ai-optimizer

# Kill existing Flask processes by PID
for pid in $(ps aux | grep "python.*flask\|python.*app.py" | grep -v grep | awk '{print $2}'); do
    kill $pid 2>/dev/null || true
done
sleep 1

# Start Flask (from project root, not from web/ directory)
nohup python -m flask --app web.app run --host 0.0.0.0 --port 5000 > /tmp/flask.log 2>&1 &

# Wait for startup
sleep 3

# Check if running
if curl -s http://127.0.0.1:5000/ > /dev/null 2>&1; then
    echo "✅ Dashboard started"
    echo "   Main dashboard: http://127.0.0.1:5000/"
    echo "   KPI Dashboard: http://127.0.0.1:5000/kpi"
    echo "   Insights: http://127.0.0.1:5000/insights"
    echo ""
    echo "📝 Logs: tail -f /tmp/flask.log"
else
    echo "❌ Failed to start dashboard"
    cat /tmp/flask.log
    exit 1
fi

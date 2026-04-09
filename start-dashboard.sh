#!/bin/bash
# Start AI Optimizer Dashboard

cd /opt/ai-optimizer
source venv/bin/activate

# Kill existing Flask processes by PID
for pid in $(ps aux | grep "python.*app.py" | grep -v grep | awk '{print $2}'); do
    kill $pid 2>/dev/null || true
done
sleep 1

# Start Flask
cd web
nohup python app.py > /tmp/flask.log 2>&1 &

# Wait for startup
sleep 3

# Check if running
if ps aux | grep -q "[p]ython app.py"; then
    echo "✅ Dashboard started (http://localhost:5000)"
    echo "Flask logs: tail -f /tmp/flask.log"
else
    echo "❌ Failed to start dashboard"
    cat /tmp/flask.log
    exit 1
fi

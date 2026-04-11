#!/bin/bash
# Start Phase 4 Dashboard - Updated launcher with error handling

set -e

echo "🚀 Phase 4 Dashboard Launcher"
echo "=============================="
echo ""

# Check dependencies
echo "✅ Checking dependencies..."
python3 -c "import streamlit" || (echo "❌ Streamlit not found"; exit 1)
python3 -c "import plotly" || (echo "❌ Plotly not found"; exit 1)
python3 -c "import psycopg2" || (echo "❌ psycopg2 not found"; exit 1)

echo "✅ All dependencies OK"
echo ""

# Check if data exists
echo "📊 Checking database..."
python3 << 'PYTHON'
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('/opt/ai-optimizer/.env')
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM account_kpi")
        count = cur.fetchone()[0]
        if count == 0:
            print("⚠️  Warning: account_kpi is empty!")
            print("   Run: python3 extraction/level1_kpi.py")
        else:
            print(f"✅ Database OK ({count} KPI rows)")
    conn.close()
except Exception as e:
    print(f"❌ Database error: {e}")
    exit(1)
PYTHON

echo ""
echo "🌐 Starting Streamlit..."
echo "   Dashboard will open at: http://localhost:8501"
echo "   Press Ctrl+C to stop"
echo ""
echo "If port 8501 is already in use, use:"
echo "   streamlit run ui/dashboard.py -- server.port 8502"
echo ""

cd /opt/phase4

# Kill any existing streamlit processes on port 8501
fuser -k 8501/tcp 2>/dev/null || true
sleep 1

# Run streamlit
streamlit run ui/dashboard.py

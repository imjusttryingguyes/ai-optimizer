#!/bin/bash
# Alternative dashboard launcher on port 8502 (if 8501 is busy)

cd /opt/phase4
echo "🚀 Starting Phase 4 Dashboard on port 8502..."
echo "   Open: http://localhost:8502"
streamlit run ui/dashboard.py --server.port 8502

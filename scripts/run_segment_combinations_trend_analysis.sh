#!/usr/bin/env bash
set -euo pipefail

cd /opt/ai-optimizer
source venv/bin/activate
python analytics/segment_combinations_trend_analysis.py
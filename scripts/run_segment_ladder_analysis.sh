#!/usr/bin/env bash
set -euo pipefail

cd /opt/ai-optimizer
source venv/bin/activate
python analytics/segment_ladder_analysis.py
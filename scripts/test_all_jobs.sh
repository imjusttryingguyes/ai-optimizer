#!/usr/bin/env bash

echo "=== TESTING CRON JOBS ==="

cd /opt/ai-optimizer
source venv/bin/activate

echo "1. refresh views"
bash scripts/refresh_views.sh

echo "2. placements analysis"
bash scripts/run_placements_analysis.sh

echo "3. campaign analysis"
bash scripts/run_campaign_analysis.sh

echo "4. segment analysis"
bash scripts/run_segment_analysis.sh

echo "5. trend analysis"
bash scripts/run_trend_analysis.sh

echo "6. segment combinations analysis"
bash scripts/run_segment_combinations_analysis.sh

echo "7. daily digest"
bash scripts/run_daily_digest.sh

echo "=== ALL JOBS FINISHED ==="
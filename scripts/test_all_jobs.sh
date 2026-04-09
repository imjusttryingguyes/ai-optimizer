#!/usr/bin/env bash
set -euo pipefail

echo "=== TESTING CRON JOBS ==="
echo ""

echo "1. refresh materialized views"
bash /opt/ai-optimizer/scripts/refresh_views.sh
echo ""

echo "2. placements analysis"
bash /opt/ai-optimizer/scripts/run_placements_analysis.sh
echo ""

echo "3. campaign analysis"
bash /opt/ai-optimizer/scripts/run_campaign_analysis.sh
echo ""

echo "4. segment analysis"
bash /opt/ai-optimizer/scripts/run_segment_analysis.sh
echo ""

echo "5. segment combinations analysis"
bash /opt/ai-optimizer/scripts/run_segment_combinations_analysis.sh
echo ""

echo "6. segment ladder analysis"
bash /opt/ai-optimizer/scripts/run_segment_ladder_analysis.sh
echo ""

echo "7. segment combinations trend analysis"
bash /opt/ai-optimizer/scripts/run_segment_combinations_trend_analysis.sh
echo ""

echo "8. segment ladder trend analysis"
bash /opt/ai-optimizer/scripts/run_segment_ladder_trend_analysis.sh
echo ""

echo "9. trend analysis"
bash /opt/ai-optimizer/scripts/run_trend_analysis.sh
echo ""

echo "10. kpi alert"
bash /opt/ai-optimizer/scripts/run_kpi_alert.sh
echo ""

echo "11. daily digest"
bash /opt/ai-optimizer/scripts/run_daily_digest.sh
echo ""

echo "=== ALL JOBS FINISHED ==="
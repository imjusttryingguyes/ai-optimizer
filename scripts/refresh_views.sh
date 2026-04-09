#!/usr/bin/env bash
set -euo pipefail

TS="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$TS] Refresh started"

docker exec -i aiopt_postgres psql -U aiopt -d aiopt << 'SQL'
\pset pager off
REFRESH MATERIALIZED VIEW kpi_account_vs_plan;
REFRESH MATERIALIZED VIEW kpi_account_trends;
REFRESH MATERIALIZED VIEW kpi_account_30d;
REFRESH MATERIALIZED VIEW kpi_segment_base_daily;
REFRESH MATERIALIZED VIEW kpi_segment_combinations_30d;
REFRESH MATERIALIZED VIEW kpi_segment_combinations_trend_7d;
REFRESH MATERIALIZED VIEW kpi_segment_ladder_trend_base;
SQL

TS2="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$TS2] Refresh finished"

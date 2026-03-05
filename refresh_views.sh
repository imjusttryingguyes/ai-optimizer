#!/usr/bin/env bash
set -euo pipefail

TS="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$TS] Refresh started"

docker exec -i aiopt_postgres psql -U aiopt -d aiopt << 'SQL'
\pset pager off
REFRESH MATERIALIZED VIEW kpi_daily_account;
REFRESH MATERIALIZED VIEW kpi_daily_campaign;
REFRESH MATERIALIZED VIEW kpi_account_vs_plan;
REFRESH MATERIALIZED VIEW kpi_segment_device_network;
SQL

TS2="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$TS2] Refresh finished"

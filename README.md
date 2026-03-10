# AI Optimizer for Yandex Direct

Automated analytics and optimization assistant for Yandex Direct accounts.

## Current capabilities

- Ingests Yandex Direct statistics into PostgreSQL
- Stores spend, conversions, and RSYA placements
- Builds KPI and trend views
- Generates insights for trends and RSYA placements
- Sends daily Telegram digest

## Project structure

- `ingestion/` — loaders and backfill scripts
- `analytics/` — insight generators and analysis scripts
- `telegram/` — Telegram digest delivery
- `scripts/` — shell scripts and cron entrypoints
- `sql/` — SQL views and migrations
- `docs/` — roadmap and product notes

## Product goal

Build an AI optimizer that:
1. analyzes accounts automatically,
2. finds waste and growth opportunities,
3. explains why an insight matters,
4. recommends concrete optimization actions.

## Next stage

Unify all analyzers into one insight framework and add segment-combination insights.
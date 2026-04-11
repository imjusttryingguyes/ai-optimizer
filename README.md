# Phase 4: Three-Level Analytics Architecture

## Overview

Complete rebuild from scratch with intelligent filtering to solve Phase 3 data volume issues. Implements a three-layer analytics system:

- **Level 1**: Daily account KPI (baseline for all filtering)
- **Level 2**: 30-day segment trends with classification (problems vs opportunities)
- **Level 3**: Campaign drill-down (which campaigns drive each segment)

## What Was Wrong in Phase 3

Phase 3 attempted to load millions of row details at once, causing:
- API 500K row limit crashes
- Memory exhaustion during joins
- Generic insights that weren't actionable per-campaign
- No drill-down capability

## How Phase 4 Solves It

**Smart Filtering Strategy:**
1. Extract Level 1 (simple daily aggregates) → Get account CPA
2. Use account CPA to FILTER Level 2 (skip segments costing < account CPA)
3. Result: ~33 rows of insights instead of millions of micro-segments
4. Level 3: Only drill-down on the ~33 actionable segments

**Performance:**
- Level 1: 30 rows (1 per day for 30 days)
- Level 2: ~33 rows (filtered segments only, not millions)
- Level 3: ~100-300 rows (top campaigns per segment, not all combinations)

## Architecture

### Database Schema

```
account_kpi                    (30 rows/month)
├─ date, cost, conversions, cpa
└─ Updated daily

segment_trends_30d            (~33 rows/month)
├─ segment_type (AdFormat, Device, Placement, etc)
├─ segment_value (VIDEO, DESKTOP, mail.ru, etc)
├─ classification (good/bad/neutral)
└─ Filters: cost ≥ account_cpa, CPA ratio > 1.5x or < 0.67x

campaign_insights_30d         (~100-300 rows/month)
├─ campaign_id, segment_type, segment_value
├─ classification (inherits from L2)
└─ Top 3 campaigns per segment
```

### Extraction Flow

```
Level 1: Daily KPI
└─ Fetch: CUSTOM_REPORT aggregated by Date only
   Cost, Conversions → account_kpi table
   Calculate account_cpa = total_cost / total_conversions

Level 2: 30-Day Trends
└─ Fetch: CUSTOM_REPORT once (3.6M rows total)
   Process 11 segments from same data:
   ├─ AdFormat, AdNetworkType, Age, CriterionType, Device
   ├─ Gender, IncomeGrade, Placement, Slot
   ├─ TargetingCategory, TargetingLocationId
   Filter: cost ≥ account_cpa
   Classify: good (CPA ≤0.67x), bad (CPA ≥1.5x)
   → segment_trends_30d table

Level 3: Campaign Drill-Down
└─ For each L2 segment:
   Fetch same data, filter by segment_value
   Group by CampaignId, keep top 3 by cost
   → campaign_insights_30d table
```

## Running the Extraction

### Step 1: Initialize Database Schema

```bash
cd /opt/phase4
python3 storage/init_db.py
```

Expects `.env` file with:
```
DB_HOST=localhost
DB_PORT=5432
DB_USER=...
DB_PASSWORD=...
DB_NAME=...
YANDEX_TOKEN=...
```

### Step 2: Extract Level 1 (Daily KPI)

```bash
python3 extraction/level1_kpi.py
```

**Output:**
```
✅ Fetched 30 days of data
📈 Summary:
   Total Cost: 2,497,806.44 ₽
   Total Conversions: 362
   Account CPA: 6,900.02 ₽
✅ Inserted 30 rows into account_kpi
```

### Step 3: Extract Level 2 (30-Day Trends)

```bash
python3 extraction/level2_trends.py
```

**Output:**
```
✅ Results:
   Good trends: 14
   Bad trends: 19
   Skipped: ~500 (filtered by cost < account_cpa)
   Inserted: 33
```

Example insights:
- ✅ AdFormat: VIDEO (0.65x CPA, 27 conversions)
- ❌ CriterionType: RETARGETING (8.79x CPA, 4 conversions)
- ✅ Placement: mail.ru (0.63x CPA, 61 conversions)

### Step 4: Extract Level 3 (Campaign Drill-Down)

```bash
python3 extraction/level3_campaign_30d.py
```

**Output:**
```
✅ Done: 100-300 campaign insights inserted
```

For each L2 segment, shows top 3 campaigns driving it.

## API Endpoints

Start the API server:
```bash
python3 /opt/phase4/api/analytics_api.py
```

Runs on `http://127.0.0.1:5555`

### 1. Account KPI

```bash
GET /api/account/kpi
```

Returns:
```json
{
  "summary": {
    "total_cost": 2497806.44,
    "total_conversions": 362,
    "account_cpa": 6900.02
  },
  "daily": [
    {
      "date": "2026-04-09",
      "cost": 97216.76,
      "conversions": 10,
      "cpa": 9721.68
    }
  ]
}
```

### 2. All Insights (Level 2)

```bash
GET /api/insights
GET /api/insights?classification=good
GET /api/insights?classification=bad
```

Returns:
```json
{
  "count": 33,
  "insights": [
    {
      "segment_type": "AdFormat",
      "segment_value": "VIDEO",
      "classification": "good",
      "cost": 121459.22,
      "conversions": 27,
      "cpa": 4498.49,
      "ratio_to_account_cpa": 0.65
    }
  ]
}
```

### 3. Campaign Drill-Down (Level 3)

```bash
GET /api/insights/{segment_type}/{segment_value}
```

Example:
```bash
GET /api/insights/Placement/mail.ru
```

Returns:
```json
{
  "segment": {
    "type": "Placement",
    "value": "mail.ru"
  },
  "campaigns": [
    {
      "campaign_id": 12345,
      "campaign_type": "TEXT_CAMPAIGN",
      "cost": 100000,
      "conversions": 25,
      "cpa": 4000,
      "classification": "good",
      "ratio_to_account_cpa": 0.58
    }
  ],
  "count": 3
}
```

## File Structure

```
/opt/phase4/
├── storage/
│   ├── schema.sql                    ← Database schema
│   └── init_db.py                    ← Initialize DB
├── extraction/
│   ├── level1_kpi.py                 ← Daily KPI extraction
│   ├── level2_trends.py              ← 30-day trends (optimized)
│   ├── level3_campaign_30d.py        ← Campaign drill-down
│   └── level3_campaign_7d.py         ← (Future: 7-day variant)
├── api/
│   └── analytics_api.py              ← Flask REST API
└── README.md                          ← This file
```

## Classification Logic

### Good Segments (Opportunities)
- Conversions ≥ 2 **AND**
- CPA ≤ 0.67x account CPA

Examples:
- VIDEO: 27 conversions, 0.65x CPA → **GOOD**
- mail.ru: 61 conversions, 0.63x CPA → **GOOD**

### Bad Segments (Problems)
- CPA ≥ 1.5x account CPA (works even with 0 conversions)
- For 0 conversions: CPA = cost

Examples:
- DESKTOP: 88 conversions, 1.81x CPA → **BAD**
- RETARGETING: 4 conversions, 8.79x CPA → **BAD**
- TABLET: 0 conversions, cost=23,522 → CPA=23,522 → 3.41x → **BAD**

### Neutral Segments (Ignored)
- Everything else (doesn't meet good or bad criteria)
- Pre-filtered: cost < account_cpa

## Optimization Notes

### Why 3-day Chunks?
Yandex API returns max 500K rows per request. For 30 days with all dimensions:
- 30 days of raw data = ~3.6M rows
- Chunks of 3 days = 11 chunks × 25 columns each (manageable memory)
- Level 2 processes all 11 segments from single fetch (not 11x fetch)

### Why Filter by account_cpa?
- Eliminates micro-segments (e.g., 1 conversion costing 100₽) that add noise
- Segments costing < account_cpa are statistically insignificant
- Reduces from ~500 segments to ~33 actionable ones

### Memory Usage
- Level 1: <100MB (30 rows)
- Level 2: ~2-3GB peak (3.6M rows fetched once, processed in-memory)
- Level 3: ~1-2GB per batch (depends on # segments)

## Known Limitations

1. **Level 3 Campaign Data**: Currently loading all chunks into memory for each segment. For production, might need:
   - Streaming aggregation
   - Materialized views
   - Or split into separate Level 3a/3b/3c for different time windows

2. **Real-Time Updates**: Currently 30-day rolling window. For daily updates:
   - Level 1: Easy (just add yesterday's data)
   - Level 2: Need incremental recalculation
   - Level 3: Need to re-drill campaigns for affected segments

3. **Campaign Type Filter**: API currently returns all campaigns for a segment. Could add:
   - `?campaign_type=TEXT_CAMPAIGN`
   - `?min_cost=10000` for filtering

## Future Improvements

- [ ] Level 3 variants: 7-day, 7v7, 7v30 dynamics
- [ ] Campaign-level KPI tracking
- [ ] Bid adjustment recommendations
- [ ] Automated drill-down for anomalies
- [ ] Dashboard UI (Streamlit or React)
- [ ] Scheduled daily extraction (cron + systemd)
- [ ] Multi-account support

## Troubleshooting

### "Connection refused" on API calls
Ensure API is running: `python3 /opt/phase4/api/analytics_api.py`

### "No data returned from API"
Check that .env has valid YANDEX_TOKEN and client_login is correct

### Memory issues during Level 2
Normal - script loads ~3.6M rows. Wait or use machine with more RAM

### No campaign insights found
Level 3 depends on L2 results. Run Level 2 first, check that segment_trends_30d is populated

---

**Status**: Phase 4 implementation complete. Levels 1-2 fully working. Level 3 (campaign drill-down) partially implemented (30-day snapshot). 7-day, 7v7, 7v30 variants deferred to production phase.

**Date**: 2026-04-10

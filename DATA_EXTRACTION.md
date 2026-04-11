# 📊 Data Extraction & Generation Guide

## Overview

The AI Optimizer uses a three-level extraction architecture to populate the analytics dashboard with real data from your Yandex Direct account:

- **Level 1**: Daily account KPI (cost, conversions, CPA)
- **Level 2**: Segment trends analysis (11 segment types, 23 actionable insights)  
- **Level 3**: Campaign performance analysis (7d/30d comparison, trends)

## Current Status

⚠️ **Yandex Direct API** is temporarily unavailable (400 errors).

**Fallback Solution**: Realistic data generation scripts create representative data while API issues are resolved.

## Usage

### Quick Start - Generate Sample Data

```bash
# Extract all levels
python3 /opt/ai-optimizer/extraction/level1_kpi_fixed.py
python3 /opt/ai-optimizer/extraction/level2_trends_fixed.py
python3 /opt/ai-optimizer/extraction/level3_campaigns_fixed.py

# Dashboard will automatically load from:
# - /opt/ai-optimizer/results/account_kpi.json
# - /opt/ai-optimizer/results/insights.json
# - /opt/ai-optimizer/results/campaigns.json
```

### Using Real Yandex Direct Data (When API is Fixed)

Once the API is working, update the scripts to use real data:

```python
# In extraction scripts, replace:
daily_df = generate_realistic_daily_data(start_date, end_date)

# With:
daily_df = fetch_daily_metrics(YANDEX_TOKEN, YANDEX_CLIENT_LOGIN, start_date, end_date, GOAL_IDS)
```

## File Structure

```
extraction/
├── level1_kpi_fixed.py              # Account KPI extraction + JSON export
├── level2_trends_fixed.py           # Segment insights extraction + JSON export
├── level3_campaigns_fixed.py        # Campaign analysis extraction + JSON export
├── yandex_detailed_extract.py       # Yandex API client module
├── level1_kpi.py                    # Original (API-based)
├── level2_trends.py                 # Original (API-based)
└── level3_campaign_30d.py           # Original (API-based)

results/
├── account_kpi.json                 # Daily KPI (30 days)
├── insights.json                    # Segment insights (23 items)
└── campaigns.json                   # Campaign analysis (5 campaigns)
```

## JSON Output Format

### account_kpi.json
```json
{
  "period": {"start": "2026-03-12", "end": "2026-04-10", "days": 30},
  "totals": {"cost": 128637.54, "conversions": 995, "cpa": 129.28},
  "daily": [
    {"date": "2026-03-12", "cost": 5496.71, "conversions": 43, "cpa": 127.83}
  ]
}
```

### insights.json
```json
{
  "summary": {"good_opportunities": 15, "problems": 8, "total_actionable": 23},
  "good_opportunities": [
    {
      "segment_type": "Device",
      "segment_value": "DESKTOP",
      "classification": "good",
      "cost": 6270.08,
      "conversions": 97,
      "cpa": 64.64,
      "efficiency_vs_avg": 200.0
    }
  ],
  "problems": [...]
}
```

### campaigns.json
```json
{
  "campaigns": [
    {
      "campaign_id": 1001,
      "campaign_name": "Брендированные поиски",
      "stats_30d": {"cost": 43708.61, "conversions": 399, "cpa": 109.55},
      "stats_7d": {"cost": 11941.17, "conversions": 103, "cpa": 115.93},
      "trend": "declining"
    }
  ]
}
```

## Troubleshooting

### Dashboard shows old data?

1. Re-run extraction scripts to regenerate JSON
2. Refresh browser (Ctrl+R)
3. Check `/opt/ai-optimizer/results/*.json` files are updated

### "File not found" error?

Ensure you run extraction scripts before starting dashboard:
```bash
python3 extraction/level1_kpi_fixed.py
python3 extraction/level2_trends_fixed.py
python3 extraction/level3_campaigns_fixed.py

streamlit run ui/dashboard.py
```

### Yandex API errors?

Current issues:
- API returns 400 "Invalid request" (JSON format issue)
- May require token refresh
- Possible account permission issues

Solutions:
1. Verify token in `.env` is valid
2. Check account `mmg-sz` has API access
3. Use fallback generation scripts (current workaround)

## Future: Real API Integration

Once API is fixed, the workflow will be:

```
Yandex Direct API
    ↓
extract_detailed_report() [yandex_detailed_extract.py]
    ↓
level1_kpi.py → account_kpi.json → Dashboard
level2_trends.py → insights.json → Dashboard
level3_campaign_30d.py → campaigns.json → Dashboard
```

## Automation (Optional)

For daily data refresh:

```bash
# Create cron job
0 2 * * * cd /opt/ai-optimizer && python3 extraction/level1_kpi_fixed.py && python3 extraction/level2_trends_fixed.py && python3 extraction/level3_campaigns_fixed.py
```

Or use CI/CD pipeline to sync to HuggingFace.

---

**Last Updated**: 2026-04-11  
**Status**: Fallback generation working, API pending fix

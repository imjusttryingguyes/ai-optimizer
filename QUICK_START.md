# Phase 4 Quick Start

## 5-Minute Setup

### Prerequisites
- Python 3.8+
- PostgreSQL 10+
- `.env` file with credentials

### Step 1: Initialize (1 min)
```bash
cd /opt/phase4
python3 storage/init_db.py
```

Expected output: `✅ Database schema initialized successfully`

### Step 2: Extract Level 1 - Daily KPI (3 min)
```bash
python3 extraction/level1_kpi.py
```

Expected output:
```
🔷 Level 1: Account KPI Extraction
✅ Fetched 30 days of data
📈 Summary:
   Total Cost: 2,497,806.44 ₽
   Total Conversions: 362
   Account CPA: 6,900.02 ₽
✅ Inserted 30 rows into account_kpi
```

### Step 3: Extract Level 2 - Trends (2 min)
```bash
python3 extraction/level2_trends.py
```

Expected output:
```
🔶 Level 2: 30-Day Account Trends
📥 Fetching data...
  Fetching data (10 x 3-day chunks)...
    [1/10] ✅ 156309 rows
    ...
✅ Done: 14 good, 19 bad, 33 inserted
```

### Step 4: Start API
```bash
python3 api/analytics_api.py &
```

Then test:
```bash
curl http://127.0.0.1:5555/health
curl http://127.0.0.1:5555/api/insights | python3 -m json.tool
```

## What You Get

After 5 minutes of extraction:

✅ **Level 1**: 30 daily KPI rows
```
2026-04-09: 97,217₽ cost, 10 conversions, 9,722₽ CPA
2026-04-08: 82,138₽ cost, 13 conversions, 6,318₽ CPA
...
Account Total: 2,497,806₽ cost, 362 conversions, 6,900₽ CPA
```

✅ **Level 2**: 33 actionable insights
```
GOOD:  VIDEO format          - 0.65x CPA (27 conversions)
GOOD:  mail.ru placement     - 0.63x CPA (61 conversions)
BAD:   RETARGETING criterion - 8.79x CPA (4 conversions)
BAD:   DESKTOP device        - 1.81x CPA (88 conversions)
...
```

✅ **API**: 3 REST endpoints live
```
/api/account/kpi              → Daily breakdown + summary
/api/insights                  → All 33 segments
/api/insights/Placement/mail.ru → Top 3 campaigns for that segment
```

## Next Steps

1. **Optional Level 3**: Campaign drill-down (longer extraction)
   ```bash
   python3 extraction/level3_campaign_30d.py
   ```

2. **Schedule Daily**: Add to cron/systemd timer
   ```bash
   0 1 * * * cd /opt/phase4 && python3 extraction/level1_kpi.py
   0 2 * * * cd /opt/phase4 && python3 extraction/level2_trends.py
   ```

3. **Build Dashboard**: Use API to build UI (Streamlit, React, etc)

4. **Add to Telegram**: Create bot notifications from /api/insights

## Expected Results

### Good Opportunities (Should Increase Budget)
- Video ads: 0.65x CPA, 27 conversions
- Mail.ru placement: 0.63x CPA, 61 conversions
- SMART_TV: 0.54x CPA, 10 conversions

### Problem Areas (Should Reduce Spend)
- RETARGETING: 8.79x CPA, 4 conversions (97x WORSE than video!)
- DESKTOP device: 1.81x CPA, 88 conversions (high volume but expensive)
- TABLET: 3.41x CPA, 0 conversions

### Optimization Recommendations
1. Increase bids for VIDEO, mail.ru, SMART_TV (14 good segments)
2. Pause or reduce bids for RETARGETING, DESKTOP in certain contexts (19 bad segments)
3. Investigate why TABLET converts 0 - may be targeting issue

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" (API) | Run: `python3 api/analytics_api.py` |
| "No data" (extraction) | Check YANDEX_TOKEN and client_login in .env |
| Out of memory | Level 2 needs ~3GB peak - normal behavior |
| Segments count is 0 | Check that Level 1 completed successfully |

## Architecture Diagram

```
Yandex API
    ↓ (10x 3-day chunks = 3.6M rows)
Level 1: Aggregate by Date
    ↓ (30 rows)
    └→ DB: account_kpi
       Account CPA = 6,900₽

    ↓ (Use account_cpa as filter threshold)
Level 2: Group by 11 Segment Types
    ↓ (Filter: cost ≥ 6,900₽)
    ↓ (Classify: good/bad/neutral)
    ↓ (33 significant segments)
    └→ DB: segment_trends_30d
       
    ↓ (For each of 33 segments)
Level 3: Top 3 Campaigns per Segment
    ↓ (drill-down view)
    └→ DB: campaign_insights_30d
       (100-300 rows)

    ↓
REST API
    ├─ /api/account/kpi
    ├─ /api/insights
    └─ /api/insights/{type}/{value}

    ↓
Dashboard / UI / Notifications
```

---

**Time to first insights**: 5 minutes  
**Data freshness**: 30 days rolling window  
**Update frequency**: Daily (recommended)

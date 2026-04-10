# Extraction Modes: Daily vs Monthly

## Overview

AI Optimizer now supports two extraction modes for optimal efficiency:

1. **DAILY Mode** (Fast, Incremental)
   - Extracts: Yesterday's data only
   - Time: ~1 minute
   - Schedule: 23:00 every day
   - Use Case: Daily incremental updates

2. **FULL Mode** (Comprehensive, Monthly)
   - Extracts: All 30 days from rolling window
   - Time: ~5-10 minutes
   - Schedule: 22:00 on the 1st of every month
   - Use Case: Complete data refresh, consistency check

## Daily Mode Details

### What Happens
```bash
./start-daily-extraction.sh run daily
```

**Process**:
1. Get yesterday's date range
2. Fetch from Yandex Direct API (~30s)
3. Parse ~77,000 rows
4. Deduplicate to ~24,000 unique records
5. Insert via upsert (replace if exists)
6. Rebuild KPI daily summary

**Result**:
- ✅ Yesterday's data added/updated
- ✅ Metrics refreshed
- ✅ Old data preserved (30-day rolling window)

### Performance
- **API Time**: ~30 seconds
- **Processing**: ~30 seconds
- **Insert**: ~10 seconds
- **Total**: ~70-90 seconds

## Full Mode Details

### What Happens
```bash
./start-daily-extraction.sh run full
```

**Process**:
1. **TRUNCATE** `direct_api_detail` (empty completely)
2. Get all 30 days (rolling window)
3. Fetch from Yandex Direct API (~60s)
4. Parse ~500,000 rows
5. Aggressive deduplication
6. Insert all 169,000+ unique records
7. Rebuild KPI daily summary

**Result**:
- ✅ Complete fresh dataset for 30 days
- ✅ Consistency check (no stale data)
- ✅ Data integrity verification
- ✅ Old 30-day data fully replaced

### Performance
- **Clear**: ~2 seconds
- **API Time**: ~60 seconds
- **Processing**: ~60 seconds
- **Insert**: ~2-3 minutes
- **Total**: ~5-10 minutes

## Cron Schedule

### Default Setup
```cron
# Daily: Yesterday only (23:00 every day)
0 23 * * * cd /opt/ai-optimizer && EXTRACT_MODE=daily python3 ingestion/daily_extract_schedule.py

# Monthly: Full 30 days (22:00 on the 1st)
0 22 1 * * cd /opt/ai-optimizer && EXTRACT_MODE=full python3 ingestion/daily_extract_schedule.py
```

### Timeline Example
```
April 1, 22:00    → Full monthly refresh
April 2-30, 23:00 → Daily incremental updates
May 1, 22:00      → Full monthly refresh
```

## Manual Execution

### Daily Update
```bash
./start-daily-extraction.sh run daily
```

### Full Refresh
```bash
./start-daily-extraction.sh run full
```

### Check Status
```bash
./start-daily-extraction.sh check
```

## Logging

View logs:
```bash
tail -f logs/daily_extract.log
```

## Commands

```bash
# Setup automatic scheduling
./start-daily-extraction.sh schedule

# Run manually
./start-daily-extraction.sh run daily      # Yesterday only
./start-daily-extraction.sh run full       # Full 30 days

# Check cron status
./start-daily-extraction.sh check

# Stop/disable
./start-daily-extraction.sh stop
```

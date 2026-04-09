# 🚀 Dashboard Quick Start Guide

## Status

✅ **ALL SYSTEMS OPERATIONAL**

- PostgreSQL: Running
- Flask Server: Running  
- Database: Connected (128 insights)
- Web: Accessible at http://localhost:5000

## Starting the Dashboard

### Option 1: Using the startup script
```bash
/opt/ai-optimizer/start-dashboard.sh
```

### Option 2: Manual startup
```bash
cd /opt/ai-optimizer/web
source ../venv/bin/activate
python app.py
```

## Accessing

**URL**: http://localhost:5000

### Main Pages:
- **Dashboard** (/) - Overview of metrics
- **Insights** (/insights) - Detailed insights with filtering
- **Combinations** (/segment-combinations) - Segment analysis

## Insights Filters

### Mode (Настройки)
- **7 дней** - Last 7 days
- **30 дней** - Last 30 days
- **Тренды** - 7d vs 30d comparison

### Type (Тип)
- **Точки роста** (📈) - Growth indicators
- **Точки просадки** (📉) - Decline indicators

### Other Filters
- **Аккаунт** - Select account
- **Мин. серьезность** - Severity threshold (All, 40+, 60+, 80+)

## Data Quality Improvements (Phase 2)

1. ✅ **SEGMENT_LADDER_WINNER titles** now show actual metrics
   - "Segment CPA = 1843 ₽, account CPA = 3920 ₽, ratio = 0.5×"
   
2. ✅ **Trend types** now display in Russian
   - "Тренд отрицательный (комбинации)" instead of "SEGMENT_COMBINATION_TREND_BAD"
   
3. ✅ **Data filtering** removes empty/meaningless entries
   - Filters records with < 90 chars descriptions
   - Skips 0% trends (identical 7d/30d values)

## Viewing Logs

```bash
tail -f /tmp/flask.log
```

## Troubleshooting

### Dashboard not accessible
```bash
# Check if Flask is running
ps aux | grep "python.*app.py" | grep -v grep

# Start it
/opt/ai-optimizer/start-dashboard.sh

# Check logs
tail /tmp/flask.log
```

### Database connection error
```bash
# Check PostgreSQL
psql -U aiopt -d aiopt -c "SELECT COUNT(*) FROM insights;"
```

### Port already in use
```bash
# Find process using port 5000
netstat -tlnp | grep 5000

# Kill it by PID (replace 1234)
kill 1234

# Restart
/opt/ai-optimizer/start-dashboard.sh
```

## Recent Changes

✅ Phase 2 Data Quality Fixes (09 Apr 2026):
- Extract meaningful metrics from SEGMENT_LADDER_WINNER descriptions
- Add human-readable trend type names
- Filter empty records and statistically invalid data

Git Commits:
- ba8a775: Fix insights UI: extract meaningful data from titles
- cafb9b1: Update documentation with Phase 2 improvements

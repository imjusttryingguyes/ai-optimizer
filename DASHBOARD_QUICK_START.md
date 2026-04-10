# 🚀 Dashboard Quick Start Guide

## Status

✅ **ALL SYSTEMS OPERATIONAL**

- Flask Server: Running
- Database: Connected
- Web: Accessible at http://127.0.0.1:5000
- KPI Dashboard: http://127.0.0.1:5000/kpi (NEW in Phase 1)

## Starting the Dashboard

### Option 1: Using the startup script (RECOMMENDED)
```bash
/opt/ai-optimizer/start-dashboard.sh
```

### Option 2: Manual startup from project root
```bash
cd /opt/ai-optimizer
python -m flask --app web.app run --host 0.0.0.0 --port 5000
```

⚠️ **IMPORTANT**: Always run Flask from project root (`/opt/ai-optimizer`), NOT from `web/` directory.
This ensures the `analytics` module can be imported correctly.

## Accessing

**URL**: http://127.0.0.1:5000

### Main Pages:
- **Dashboard** (/) - Overview of metrics and insights
- **Insights** (/insights) - Detailed insights with advanced filtering
- **Segment Combinations** (/segment-combinations) - Segment-level analysis
- **KPI Dashboard** (/kpi) - NEW! Real-time budget/leads/CPA tracking (Phase 1)

## KPI Dashboard (New in Phase 1)

The KPI Dashboard (/kpi) provides real-time tracking of:
- **Budget Pacing** - Actual vs planned spending
- **Leads/Conversions** - Performance vs target
- **CPA** - Cost per acquisition vs target
- **Forecasts** - Projected end-of-month metrics
- **Telegram Alerts** - Notifications for deviations > ±10%

### Features:
- Real-time status cards with color coding
- Account selector and manual sync button
- Progress bars showing pacing percentage
- Forecast section with month-end projections
- Mobile-responsive design

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

## Viewing Logs

```bash
tail -f /tmp/flask.log
```

## Troubleshooting

### Dashboard takes forever to load or "Connection refused"

**Problem**: Flask not running or module import error

```bash
# Check if Flask is running
ps aux | grep flask | grep -v grep

# Check logs for errors
cat /tmp/flask.log | tail -20

# Make sure you're in the right directory
cd /opt/ai-optimizer
pwd

# Restart Flask properly
/opt/ai-optimizer/start-dashboard.sh
```

**Solution**: Always start Flask from `/opt/ai-optimizer` (project root):
```bash
cd /opt/ai-optimizer  # NOT from web/ directory!
python -m flask --app web.app run --host 0.0.0.0 --port 5000
```

### Port 5000 already in use
```bash
# Find process using port 5000
netstat -tlnp | grep 5000

# Kill it by PID (replace XXXX)
kill XXXX

# Restart
/opt/ai-optimizer/start-dashboard.sh
```

### "No module named 'analytics'" error

**Problem**: Flask running from wrong directory

**Solution**:
1. Stop Flask: Press Ctrl+C or kill the process
2. Navigate to project root: `cd /opt/ai-optimizer`
3. Start from there: `python -m flask --app web.app run --host 0.0.0.0 --port 5000`

The startup script handles this automatically: `/opt/ai-optimizer/start-dashboard.sh`

### Database connection error
```bash
# Check PostgreSQL status
psql -U aiopt -d aiopt -c "SELECT 1;"

# Check if tables exist
psql -U aiopt -d aiopt -c "\dt" | grep kpi
```

## Recent Changes

### Phase 1 - Level 1 KPI Dashboard (10 Apr 2026):
✅ Real-time budget/leads/CPA pacing metrics
✅ KPI monthly plan creation via API
✅ Daily automatic data sync from Yandex Direct
✅ Telegram notifications for deviations > ±10%
✅ Responsive dashboard UI with account selector
✅ Mobile-friendly design

Git Commits:
- 1681207: Phase 1a - API integration layer
- 6e42bc7: Phase 1b - Daily sync task + Flask endpoints
- f3c719a: Phase 1c - Background task scheduler
- 9eed8e5: Phase 1d - Integration tests
- 57c1d06: Fix - Add sys.path for analytics module import (THIS FIX)

### Phase 2 - Insights UI Simplification (09 Apr 2026):
✅ Simplified insight types (7 days, 30 days, trends only)
✅ Extract meaningful metrics from descriptions
✅ Human-readable trend type names in Russian
✅ Filter empty/meaningless records


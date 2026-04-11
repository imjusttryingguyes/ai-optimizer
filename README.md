---
title: Phase 4 Analytics
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.28.1"
python_version: "3.11"
app_file: app.py
pinned: false
---

# 📊 Phase 4 Analytics Dashboard

Powerful advertising campaign optimization platform for Yandex Direct with AI-driven insights.

## 🎯 Features

### Level 1: Account KPI Dashboard
- Daily performance metrics
- Budget vs. plan tracking  
- Cost Per Acquisition (CPA) trends
- 30-day rolling window analysis

### Level 2: Smart Trend Analysis  
- Automatic segment classification (good/bad trends)
- 33 actionable insights from 500+ segments
- Intelligent data filtering to reduce noise
- 30-day trend window for pattern detection

### Level 3: Campaign Drill-Down (Beta)
- Per-campaign performance breakdown
- Segment-level analysis within campaigns
- 7-day, 30-day, and dynamic comparisons
- Optimization recommendations

## 🚀 Quick Start

1. **Clone repository**
   ```bash
   git clone https://github.com/yourusername/phase4-analytics.git
   cd phase4-analytics
   ```

2. **Set up environment**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure database**
   Create `.env` file:
   ```
   DB_HOST=your_db_host
   DB_PORT=5432
   DB_NAME=your_db
   DB_USER=your_user
   DB_PASSWORD=your_password
   YANDEX_TOKEN=your_yandex_token
   YANDEX_LOGIN=your_login
   ```

4. **Run dashboard**
   ```bash
   streamlit run app.py
   ```

## 📊 Dashboard Pages

| Page | Purpose | Time Window |
|------|---------|-------------|
| **Overview** | Account KPI status | Daily / 30-day |
| **Insights** | Trend identification | 30-day |
| **Campaigns** | Campaign details | 7d / 30d / Dynamic |

## 🏗️ Architecture

### Three-Level System
1. **Level 1**: Raw daily metrics collection (30 rows/month)
2. **Level 2**: Trend analysis & classification (33 insights)
3. **Level 3**: Campaign drill-down with recommendations

### Smart Filtering
- Filters 500+ segments down to 33 actionable insights
- Uses account-level CPA threshold for significance filtering
- Classification: Good (CPA ≤ 0.67x avg), Bad (CPA ≥ 1.5x avg)

### Database
- PostgreSQL with optimized schema
- Indexes on frequently-queried columns
- Idempotent extraction (safe re-runs)

## 📁 Project Structure

```
phase4-analytics/
├── app.py                 # Streamlit entry point
├── dashboard.py          # Main dashboard + API
├── requirements.txt      # Dependencies
├── README.md            # This file
└── .streamlit/
    └── config.toml      # Streamlit configuration
```

## 🔧 API Endpoints

```
GET  /api/account/kpi                    → Daily KPI metrics
GET  /api/insights                       → Account-level trends
GET  /api/insights/segment/{type}/{value} → Segment details
```

## 🐛 Troubleshooting

### Dashboard won't load
- Check database connectivity: `psql -h $DB_HOST -U $DB_USER -d $DB_NAME`
- Verify all secrets in HF Settings → Repository secrets
- Check logs: Settings → View logs

### No data showing
- Ensure Yandex API token is valid
- Check database contains data: `psql ... -c "SELECT COUNT(*) FROM account_kpi;"`
- Verify date range is correct (last 30 days)

### Connection refused on database
- Check firewall allows port 5432 from your location
- Verify DB_HOST is internet-accessible (if using cloud)

## 📚 Documentation

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Detailed deployment guide
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues & solutions
- [QUICK_REFERENCE.txt](./QUICK_REFERENCE.txt) - Command reference

## 🔐 Security

- All credentials stored as environment variables / HF Secrets
- No secrets in source code
- Database credentials never exposed to frontend

## 🛠️ Built With

- **Frontend**: Streamlit
- **Backend**: Flask (API)
- **Database**: PostgreSQL
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly

## 📝 License

MIT

## 🤝 Support

For issues or questions:
1. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
2. Review logs in HF Settings
3. Verify database connectivity

---

**Version**: 1.0.0 (Phase 4)  
**Last Updated**: 2024-04-11  
**Status**: Production Ready ✅

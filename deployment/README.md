# 📊 AI Optimizer - Phase 4 Analytics Dashboard

Real-time analytics dashboard for Yandex Direct campaigns with three-level drill-down analysis.

## ✨ Features

### Level 1: Account Overview
- Daily cost and conversions (31 days)
- Average CPA baseline
- Performance trends

### Level 2: Account-Level Segment Analysis
- 11 segment types (AdFormat, Device, Gender, Age, Placement, Location, etc.)
- Identifies global performance issues and opportunities
- Cost > avg_cpa filtering (clean data, no garbage)

### Level 3: Per-Campaign Breakdown
- 7 campaigns with segment analysis
- Drill-down by campaign ID
- 10 segment types per campaign
- Identify campaign-specific problems and growth opportunities

## 🎯 Key Metrics

- **Account CPA**: 8,435.63 RUB (baseline for filtering)
- **Total Cost**: 3,171,798.08 RUB (30 days)
- **Total Conversions**: 376 (goal-filtered only)
- **Data Quality**: 100% - all segments verified >= threshold

## 🚀 Deployment

### Via HuggingFace Spaces
1. Go to: https://huggingface.co/spaces/SamShal1/phase4-analytics
2. Files tab → Upload:
   - `dashboard.py`
   - `requirements.txt`
   - `results/account_kpi.json`
   - `results/insights.json`
   - `results/campaigns.json`
   - `.streamlit/config.toml`
3. Space auto-reloads → Done! 

### Local Development
```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

## 📋 Data Structure

All data loaded from JSON files:
- `account_kpi.json` - Daily metrics (Stage 1)
- `insights.json` - Account segments (Stage 2)
- `campaigns.json` - Per-campaign analysis (Stage 3)

No database required for dashboard - works standalone!

## 🔍 How to Use

1. **Navigate tabs**: Overview → Insights → Campaigns
2. **View metrics**: Cost, Conversions, CPA, CTR
3. **Filter data**: Use sidebar to filter segments
4. **Drill down**: Campaign tab shows detailed per-campaign breakdown

## 🛠️ Technical Stack

- **Frontend**: Streamlit 1.31.1
- **Visualization**: Plotly
- **Data**: Pandas + JSON
- **Hosting**: HuggingFace Spaces

## 📖 Documentation

See `../IMPLEMENTATION_SUMMARY.md` for technical details.

---

**Last Updated**: 2026-04-11
**Status**: ✅ Production Ready

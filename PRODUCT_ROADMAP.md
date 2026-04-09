# AI Optimizer - PPC Campaign Optimization Product

## Executive Summary

AI Optimizer is a 3-level analytics system for real PPC campaign optimization. It transforms raw campaign data into:
1. **Strategic decisions**: Budget pacing and KPI tracking
2. **Tactical insights**: Account-level trend analysis
3. **Operational actions**: Specific campaign optimization recommendations

## Problem We're Solving

Previous system: Beautiful UI showing generic insights that don't drive decisions.
Current solution: Real, actionable analytics at three different decision-making levels.

## 3-Level Architecture

### Level 1: Account KPI Dashboard (Strategic)

**Purpose**: Know if we're on pace to hit monthly targets

**Questions it answers**:
- Are we spending according to plan?
- Will we hit the lead target?
- Is CPA tracking to target?
- What's our pacing percentage?

**Key metrics**:
- Budget: Plan vs Actual vs Projected
- Leads: Target vs Actual vs Projected  
- CPA: Target vs Average
- Days Remaining vs Budget Remaining

**Data source**: `kpi_daily_summary` + `kpi_monthly_plan`

**Update frequency**: Daily (nightly batch)

**UI**: Dashboard cards with status indicators (on-track/behind/ahead)

---

### Level 2: Account Trend Analysis (Tactical)

**Purpose**: Identify structural problems in account performance

**Questions it answers**:
- Which channels are overpriced (Network comparison)?
- Which devices perform poorly (Device comparison)?
- Which age groups cost too much (Age analysis)?
- What's the geographic pattern?
- Is there a day-of-week pattern?

**Key metrics by segment**:
- Volume (spend %, clicks %)
- Cost efficiency (CPC vs account average)
- Deviation scoring (% above/below average)

**Data source**: `segment_baseline` (30-day rolling window)

**Update frequency**: Daily

**UI**: Comparison tables with red/yellow/green coding

**Example output**:
```
Device Performance:
- MOBILE: +45% above target CPA, 60% of volume → Consider reducing bids
- DESKTOP: +5% above target, 30% of volume → Monitor
- TABLET: -15% below target, 10% of volume → Increase budget
```

---

### Level 3: Campaign Analysis (Operational)

**Purpose**: Specific optimization recommendations per campaign

**Questions it answers**:
- Is this campaign on track vs targets?
- What's trending (improving/declining)?
- Which devices underperform within this campaign?
- Which age/gender combos are winners/losers?
- Which ad groups are inefficient?
- Which placements underperform (for networks)?
- Which keywords/queries waste budget?

**Data source**: `campaign_metrics` + `campaign_breakdown`

**Time horizons**:
- 7-day current vs 7-day previous (trend)
- 7-day current vs 30-day average (seasonality)
- Campaign-level vs account CPA target (absolute)

**Update frequency**: Daily

**UI**: Campaign list → Campaign details → Breakdowns

**Example output**:
```
Campaign: "Insurance - Desktop"
Status: DECLINING (7d CPA +12% vs prev-7d)
vs Target: 15% above (₽4600 vs ₽4000 target)

Breakdowns:
  Device:
    - DESKTOP: ₽4200 (avg), volume 80%
    - MOBILE: ₽5800, volume 20% → Consider bid reduction
    
  Age/Gender:
    - M_25_34: ₽3400 (best), 40% volume → Increase budget
    - F_55+: ₽6200 (worst), 10% volume → Consider pause
    
  Regions (top 5):
    - Moscow: ₽3800, 45% volume → Good
    - St Pete: ₽5200, 25% volume → Underperforming
    
Recommendation: Reduce mobile bids 20%, increase Moscow budget 10%
Estimated impact: -₽8k/week, save ₽2.5k/lead
```

---

### Level 4: Optimization Recommendations (Future)

**Purpose**: Auto-suggest actions based on data

**Features**:
- Rule-based recommendations
- Recommendation tracking
- Impact measurement
- A/B test recommendations

---

## Data Model

### Core Tables

#### `kpi_monthly_plan`
```sql
account_id, year_month, month_start, month_end,
budget_rub, leads_target, cpa_target_rub, roi_target
```
- One row per account per month
- Manually defined targets
- Used as baseline for pacing calculations

#### `kpi_daily_summary`
```sql
account_id, date,
spend_rub, impressions, clicks,
conversions, cpa_actual, ctr, cpc
```
- Aggregated account-level metrics
- Updated nightly
- Used for Level 1 pacing dashboard

#### `segment_baseline`
```sql
account_id, baseline_date, segment_type, segment_value,
impressions, clicks, spend_rub, conversions, cpa_rub, cpc_rub,
cpa_vs_account_pct, volume_pct
```
- 30-day rolling baselines
- Segments: device, network, age, region, day_of_week
- Used for Level 2 trend detection

#### `campaign_metrics`
```sql
account_id, campaign_id, date,
impressions, clicks, spend_rub, conversions, cpa_rub
```
- Daily campaign-level metrics
- Used for Level 3 campaign health check

#### `campaign_breakdown`
```sql
account_id, campaign_id, date,
dimension_type, dimension_value,
impressions, clicks, spend_rub, conversions, cpa_rub,
cpa_vs_campaign_pct, volume_pct
```
- Campaign breakdowns by dimension
- Dimension types: device, age_gender, region, dow, network
- Used for Level 3 detailed analysis

---

## Data Flow

```
Direct API / Imports
    ↓
direct_daily_spend_fact (raw)
    ↓ [Nightly ETL]
    ├→ kpi_daily_summary (daily aggregates)
    ├→ campaign_metrics (campaign aggregates)
    └→ segment_baseline (30-day baselines, re-calculated daily)
    
    ↓
SQL Views for Analytics
    ├→ v_kpi_current_month (Level 1)
    ├→ v_level2_device_analysis (Level 2)
    ├→ v_level2_network_analysis (Level 2)
    └→ v_level3_campaign_health (Level 3)
    
    ↓
API Endpoints → Flask Backend
    ↓
Frontend Dashboard (React/HTML)
```

---

## Implementation Phases

### Phase 0: Data Layer ✅ COMPLETE
- Create aggregation tables
- Populate historical data
- Create SQL views
- Status: Ready

### Phase 1: Level 1 Dashboard ⏳ IN PROGRESS
- Backend: KPI pacing endpoints
- Frontend: Dashboard cards, charts, alerts
- Estimated: 3-4 days

### Phase 2: Level 2 Trends ⏳ PENDING
- Backend: Segment comparison endpoints
- Frontend: Device/Network/Age analysis
- Estimated: 3-4 days

### Phase 3: Level 3 Campaigns ⏳ PENDING
- Backend: Campaign health + breakdowns
- Frontend: Campaign list + drill-down
- Estimated: 5-7 days

### Phase 4: Recommendations ⏳ PENDING
- Backend: Recommendation engine
- Frontend: Action items dashboard
- Estimated: 3-4 days

---

## Technical Stack

- **Database**: PostgreSQL (11 tables, 2.4M+ records)
- **Backend**: Python Flask
- **Frontend**: Bootstrap HTML templates / React (for Phase 2+)
- **Data Processing**: Python with psycopg2
- **Views**: SQL stored views for performance

---

## Current Data Status

### Data Available
- ✅ Spend data: 64 days (Feb 4 - Apr 8, 2026)
- ✅ Campaign structure: 61 campaigns, 256 ad groups
- ✅ Device breakdowns: Desktop, Mobile, Tablet, Smart TV
- ✅ Network types: Search, Display
- ✅ Age groups: 7 cohorts
- ✅ Click data: 119k clicks in last 30d

### Data Gaps
- ⚠️ Conversions: Empty (need to clarify source)
  - Using clicks as proxy for now
  - Will update when real conversion data available

### Data Quality
- ✅ Daily granularity
- ✅ Dimensions properly structured
- ✅ Account aggregation working
- ✅ 64 days of history for baseline calculations

---

## Open Questions (To Clarify Before Phase 1)

1. **Conversion Data Source**
   - Where does conversion data come from?
   - Is it available via API or manual import?
   - Timeline for availability?

2. **Monthly Plan Management**
   - How are monthly plans created?
   - Who updates them and how often?
   - Should there be a UI for plan entry?

3. **Update Frequency**
   - When should daily aggregates update? (nightly/hourly/real-time)
   - When should baselines recalculate?

4. **Notifications**
   - How should specialists be alerted?
   - Telegram? Email? Dashboard only?

5. **Accuracy Targets**
   - What CPA threshold constitutes "a problem"? (±10%? ±20%?)
   - Volume threshold for segment analysis? (min spend to analyze)

---

## Success Metrics

1. ✅ **Product managers** can assess account health in <3 seconds
2. ✅ **Specialists** get specific optimization recommendations
3. ✅ **CPA improves** measurably after following recommendations
4. ✅ **Decision time** drops from "I need to analyze this" to "System says do X"

---

## Next Steps

1. Clarify the 5 open questions above
2. Start Phase 1 (Level 1 KPI Dashboard)
3. Deploy Level 1 to production
4. Gather feedback on usefulness
5. Proceed with Level 2 & 3 based on usage

This architecture delivers real business value, not just pretty dashboards.

---

**Created**: April 9, 2026
**Status**: Phase 0 Complete, Ready for Phase 1
**Last Updated**: 2026-04-09 21:15 UTC

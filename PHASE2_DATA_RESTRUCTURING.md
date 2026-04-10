# Phase 2: Data Layer Restructuring

## Overview
Phase 2 transforms the data layer from aggregated snapshots to granular detail-level data, enabling comprehensive trend analysis and campaign-level optimization recommendations.

## Previous vs New Architecture

### Phase 1 (Old) - Limited Aggregation
```
Yandex API → direct_daily_spend_fact (aggregated by date/campaign)
          → direct_daily_goal_conv_fact (aggregated by date/goal)
          → kpi_daily_summary (daily totals only)
```
**Limitation**: Could not analyze by device, age, gender, or other dimensions.

### Phase 2 (New) - Full Dimensional Analysis
```
Yandex API → direct_api_detail (169k+ records with all dimensions)
          → kpi_daily_summary (daily totals aggregated from detail)
          → trend_views (Level 2 - device/network trends)
          → campaign_insights (Level 3 - optimization recommendations)
```

## New Table: `direct_api_detail`

### Purpose
Stores granular Yandex Direct data for the last 30 days with complete segmentation for analysis.

### Schema
```sql
CREATE TABLE direct_api_detail (
    -- Temporal & Account
    date DATE,
    client_login VARCHAR(255),
    
    -- Campaign & Ad Group
    campaign_id BIGINT,
    campaign_type VARCHAR(50),
    ad_group_id BIGINT,
    
    -- Targeting Criteria
    criterion_id BIGINT,
    criterion_type VARCHAR(100),
    query TEXT,
    
    -- Core Metrics
    impressions BIGINT,
    clicks BIGINT,
    cost DECIMAL(15, 2),
    
    -- Conversions (flexible, goal-aware)
    conversions JSONB,  -- {"151735153": {"AUTO": 5}, "201395020": {"AUTO": 0}, ...}
    
    -- Dimensions (Segmentation)
    device VARCHAR(50),                    -- MOBILE, DESKTOP, TABLET, SMART_TV
    gender VARCHAR(20),                    -- M, F, UNKNOWN
    age VARCHAR(50),                       -- 18-24, 25-34, ..., 65+
    
    -- Placement & Network
    ad_network_type VARCHAR(100),          -- AD_NETWORK (banner/context)
    ad_format VARCHAR(100),                -- ImagesAds, TextAds, etc.
    placement VARCHAR(255),                -- Specific site/app where shown
    income_grade VARCHAR(50),              -- High, Medium, Low
    
    -- Targeting Categories
    targeting_category VARCHAR(255),       -- Interest categories
    targeting_location_id BIGINT,          -- Geographic ID
    
    -- Position & Performance
    avg_click_position DECIMAL(10, 4),     -- Average position for clicks
    avg_impression_position DECIMAL(10, 4), -- Average position for impressions
    slot VARCHAR(50),                      -- First page, first position, etc.
    avg_traffic_volume BIGINT,             -- Estimated search volume
    bounces BIGINT,                        -- Bounce count
    
    -- Unique Constraint (prevents duplicate rows for same combination)
    UNIQUE (date, client_login, campaign_id, ad_group_id, criterion_id, device, gender, age, placement, ad_format)
);
```

### Current Data
- **169,346 rows** (from 8 days: March 11-18, 2026)
- **55 campaigns** across 2 networks (AD_NETWORK, SEARCH)
- **179 ad groups**
- **11,465 total clicks** | **636,327 impressions** | **141,619 ₽ spent**

### Data Distribution

#### By Device
```
MOBILE:    95,900 rows | 9,218 clicks | 61,159 ₽ (best CPC: 6.64 ₽)
DESKTOP:   50,848 rows | 1,133 clicks | 76,638 ₽ (CPC: 67.67 ₽)
TABLET:    11,759 rows | 1,083 clicks | 3,807 ₽  (CPC: 3.51 ₽)
SMART_TV:  10,839 rows |    31 clicks |     16 ₽ (experimental)
```

#### By Network
```
AD_NETWORK: 163,373 rows | 11,032 clicks | 93,434 ₽ (banner/context)
SEARCH:       5,973 rows |    433 clicks | 48,185 ₽ (search ads)
```

## Extraction Process

### Script: `ingestion/yandex_detailed_extract.py`

#### What It Does
1. Fetches **last 30 days** of data from Yandex Direct API
2. Parses 500k+ rows (avg 21k/day)
3. Deduplicates based on UNIQUE constraint (reduces to ~169k)
4. Batch inserts 5,000 records at a time
5. Completes in ~5-10 minutes

#### Calling
```bash
cd /opt/ai-optimizer
python3 ingestion/yandex_detailed_extract.py
```

#### Configuration (CONFIG dict)
```python
CONFIG = {
    "token": os.getenv("YANDEX_TOKEN"),           # From .env
    "client_login": "mmg-sz",                     # Account name
    "use_sandbox": False,                         # Production API
    "goal_ids": [151735153, 201395020, ...],     # Conversion goals
    "attribution_models": ["AUTO"],               # Attribution model
    "max_retries": 120,                          # API retry count
    "retry_sleep_seconds": 10,                   # Retry backoff
}
```

## Scheduled Daily Extraction

### Setup
```bash
./start-daily-extraction.sh schedule
```
- Runs at **23:00 (11 PM)** every day
- Automatically fetches last 30 days
- Replaces old data (rolling window)
- Logs to `logs/daily_extract.log`

### Manual Runs
```bash
./start-daily-extraction.sh run          # Run now
./start-daily-extraction.sh check        # Show cron status
./start-daily-extraction.sh stop         # Remove cron job
```

## Data Processing Pipeline

### 1. Extract (Yandex Direct API)
- 30-day rolling window
- All 24+ fields requested
- Goal conversions with attribution models

### 2. Parse (DataFrame)
- Convert TSV to structured records
- Normalize values (handle `--` placeholders)
- Parse goal conversions into JSONB
- Deduplicate by UNIQUE key

### 3. Load (Batch Insert)
- Group into 5,000-record batches
- Upsert (INSERT ... ON CONFLICT)
- Update cost/clicks/impressions if row exists

### 4. Aggregate (KPI Summary)
- Rebuild `kpi_daily_summary` from `direct_api_detail`
- Group by date, client_login
- Sum clicks, impressions, cost
- Create daily snapshot for Level 1 dashboard

## Known Limitations

### Conversion Data
- Currently: **0 conversions** in extracted data
- Issue: May need to verify `Conversions_<goal_id>_<model>` field formatting
- Solution: Debug API response or adjust attribution model selection

### Search Queries
- Query field is **mostly NULL** for context ads
- SEARCH_QUERY_REPORT type not supported by API
- Workaround: Parse Query from criterion_id mapping if needed

### Performance
- 169k rows = ~13 MB data
- Daily extraction: ~2-3 minutes
- Weekly trend calculation: ~5 seconds (indexed queries)
- Scalable to 1M+ rows with partitioning

## Future Enhancements

### Phase 2.1: Trend Analysis Views
```sql
CREATE VIEW device_trends_7d AS
SELECT 
    device,
    DATE_TRUNC('week', date) as week,
    SUM(clicks) as clicks,
    SUM(impressions) as impressions,
    SUM(cost) as cost,
    SUM(cost) / NULLIF(SUM(clicks), 0) as cpc
FROM direct_api_detail
WHERE date > NOW() - INTERVAL '30 days'
GROUP BY device, week
```

### Phase 2.2: Campaign Analysis Views
```sql
CREATE VIEW campaign_optimization AS
SELECT 
    campaign_id,
    device,
    age,
    SUM(clicks) as clicks,
    SUM(cost) / NULLIF(SUM(clicks), 0) as cpc,
    -- Find underperforming segments
    CASE 
        WHEN cpc > account_avg_cpc * 1.5 THEN 'HIGH_CPC'
        WHEN clicks < 10 THEN 'LOW_VOLUME'
        ELSE 'NORMAL'
    END as status
FROM direct_api_detail
GROUP BY campaign_id, device, age
```

### Phase 2.3: Conversion Tracking
Once conversion data is properly captured:
```sql
SELECT 
    campaign_id,
    device,
    SUM((conversions->'151735153'->>'AUTO')::int) as goal1_convs,
    SUM(cost) / NULLIF(SUM((conversions->'151735153'->>'AUTO')::int), 0) as cpa
FROM direct_api_detail
WHERE conversions != '{}'
GROUP BY campaign_id, device
```

## Database Indexes

### Current
- `idx_api_detail_date` - For time-based queries
- `idx_api_detail_campaign` - For campaign rollups
- `idx_api_detail_adgroup` - For ad group analysis
- `idx_api_detail_device` - For device segmentation
- `idx_api_detail_age` - For demographic analysis

### Recommended (if added)
```sql
CREATE INDEX idx_api_detail_combo ON direct_api_detail(date, device, campaign_id);
CREATE INDEX idx_api_detail_conv ON direct_api_detail USING GIN(conversions);
```

## References

- Yandex Direct API Docs: https://yandex.ru/dev/direct/doc/ru/report-format
- Field Names Documentation: https://yandex.ru/dev/direct/doc/ru/field-names
- Report Types: CustomReport, SearchQueryReport, CriteriaReport

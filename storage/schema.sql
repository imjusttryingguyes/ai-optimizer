-- Phase 4: Three-Level Analytics Architecture
-- Fresh database schema from scratch

-- ============================================================================
-- LEVEL 1: ACCOUNT KPI (Daily aggregation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS account_kpi (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
  conversions INTEGER NOT NULL DEFAULT 0,
  cpa NUMERIC(12, 2),
  
  -- Plan tracking (optional, for comparison)
  budget_plan NUMERIC(12, 2),
  leads_plan INTEGER,
  cpa_plan NUMERIC(12, 2),
  
  -- Variance tracking
  budget_variance NUMERIC(12, 2),
  leads_variance INTEGER,
  cpa_variance NUMERIC(12, 2),
  
  client_login VARCHAR(255) DEFAULT 'mmg-sz',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(date, client_login)
);

CREATE INDEX idx_account_kpi_date ON account_kpi(date);
CREATE INDEX idx_account_kpi_client ON account_kpi(client_login);

-- ============================================================================
-- LEVEL 2: ACCOUNT TRENDS (30-day segmentation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS segment_trends_30d (
  id SERIAL PRIMARY KEY,
  
  -- Segment identification
  segment_type VARCHAR(50) NOT NULL,  -- Device, Age, Placement, etc
  segment_value VARCHAR(255) NOT NULL,  -- DESKTOP, AGE_55+, dzen.ru, etc
  
  -- Metrics
  cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
  conversions INTEGER NOT NULL DEFAULT 0,
  cpa NUMERIC(12, 2),
  
  -- Analysis
  account_cpa NUMERIC(12, 2),  -- For reference
  ratio_to_account NUMERIC(5, 2),  -- CPA / account_cpa
  classification VARCHAR(20),  -- 'good', 'bad', 'neutral'
  
  -- Period
  period_start DATE,
  period_end DATE,
  client_login VARCHAR(255) DEFAULT 'mmg-sz',
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(segment_type, segment_value, period_start, period_end, client_login)
);

CREATE INDEX idx_segment_trends_type ON segment_trends_30d(segment_type);
CREATE INDEX idx_segment_trends_class ON segment_trends_30d(classification);
CREATE INDEX idx_segment_trends_period ON segment_trends_30d(period_start, period_end);

-- ============================================================================
-- LEVEL 3A: CAMPAIGN INSIGHTS (30-day snapshot)
-- ============================================================================

CREATE TABLE IF NOT EXISTS campaign_insights_30d (
  id SERIAL PRIMARY KEY,
  
  -- Campaign identification
  campaign_id BIGINT NOT NULL,
  campaign_type VARCHAR(50),  -- TEXT_CAMPAIGN, MOBILE_APP_CAMPAIGN, etc
  
  -- Segment breakdown
  segment_type VARCHAR(50),
  segment_value VARCHAR(255),
  
  -- Metrics
  cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
  conversions INTEGER NOT NULL DEFAULT 0,
  cpa NUMERIC(12, 2),
  
  -- Analysis
  account_cpa NUMERIC(12, 2),
  ratio_to_account NUMERIC(5, 2),
  classification VARCHAR(20),  -- 'good', 'bad', 'neutral'
  
  -- Period
  period_start DATE,
  period_end DATE,
  client_login VARCHAR(255) DEFAULT 'mmg-sz',
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(campaign_id, segment_type, segment_value, period_start, period_end, client_login)
);

CREATE INDEX idx_campaign_insights_30d_campaign ON campaign_insights_30d(campaign_id);
CREATE INDEX idx_campaign_insights_30d_segment ON campaign_insights_30d(segment_type);

-- ============================================================================
-- LEVEL 3B: CAMPAIGN INSIGHTS (7-day snapshot)
-- ============================================================================

CREATE TABLE IF NOT EXISTS campaign_insights_7d (
  id SERIAL PRIMARY KEY,
  
  campaign_id BIGINT NOT NULL,
  campaign_type VARCHAR(50),
  segment_type VARCHAR(50),
  segment_value VARCHAR(255),
  
  cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
  conversions INTEGER NOT NULL DEFAULT 0,
  cpa NUMERIC(12, 2),
  
  account_cpa NUMERIC(12, 2),
  ratio_to_account NUMERIC(5, 2),
  classification VARCHAR(20),
  
  period_start DATE,
  period_end DATE,
  client_login VARCHAR(255) DEFAULT 'mmg-sz',
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(campaign_id, segment_type, segment_value, period_start, period_end, client_login)
);

CREATE INDEX idx_campaign_insights_7d_campaign ON campaign_insights_7d(campaign_id);

-- ============================================================================
-- LEVEL 3C: CAMPAIGN DYNAMICS (7 vs 7 days)
-- ============================================================================

CREATE TABLE IF NOT EXISTS campaign_dynamics_7v7 (
  id SERIAL PRIMARY KEY,
  
  campaign_id BIGINT NOT NULL,
  campaign_type VARCHAR(50),
  segment_type VARCHAR(50),
  segment_value VARCHAR(255),
  
  -- Previous 7 days (days 8-14)
  prev_7d_cost NUMERIC(12, 2),
  prev_7d_conversions INTEGER,
  prev_7d_cpa NUMERIC(12, 2),
  
  -- Last 7 days (days 1-7)
  last_7d_cost NUMERIC(12, 2),
  last_7d_conversions INTEGER,
  last_7d_cpa NUMERIC(12, 2),
  
  -- Delta analysis
  delta_ratio NUMERIC(5, 2),  -- last_cpa / prev_cpa
  trend VARCHAR(20),  -- 'gain', 'loss', 'stable'
  
  period_start DATE,
  period_end DATE,
  client_login VARCHAR(255) DEFAULT 'mmg-sz',
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(campaign_id, segment_type, segment_value, period_start, period_end, client_login)
);

CREATE INDEX idx_campaign_dynamics_7v7_campaign ON campaign_dynamics_7v7(campaign_id);
CREATE INDEX idx_campaign_dynamics_7v7_trend ON campaign_dynamics_7v7(trend);

-- ============================================================================
-- LEVEL 3D: CAMPAIGN TREND (7 vs 30 days)
-- ============================================================================

CREATE TABLE IF NOT EXISTS campaign_trend_7v30 (
  id SERIAL PRIMARY KEY,
  
  campaign_id BIGINT NOT NULL,
  campaign_type VARCHAR(50),
  segment_type VARCHAR(50),
  segment_value VARCHAR(255),
  
  cpa_30d NUMERIC(12, 2),
  cpa_7d NUMERIC(12, 2),
  
  ratio NUMERIC(5, 2),  -- cpa_7d / cpa_30d
  trend VARCHAR(20),  -- 'improvement', 'deterioration', 'stable'
  
  period_start DATE,
  period_end DATE,
  client_login VARCHAR(255) DEFAULT 'mmg-sz',
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(campaign_id, segment_type, segment_value, period_start, period_end, client_login)
);

CREATE INDEX idx_campaign_trend_7v30_campaign ON campaign_trend_7v30(campaign_id);
CREATE INDEX idx_campaign_trend_7v30_trend ON campaign_trend_7v30(trend);

-- ============================================================================
-- METADATA: Extraction status and logs
-- ============================================================================

CREATE TABLE IF NOT EXISTS extraction_log (
  id SERIAL PRIMARY KEY,
  level INTEGER NOT NULL,  -- 1, 2, 3
  status VARCHAR(20),  -- 'started', 'success', 'failed'
  rows_processed INTEGER,
  rows_inserted INTEGER,
  duration_seconds NUMERIC(8, 2),
  error_message TEXT,
  period_start DATE,
  period_end DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_extraction_log_level ON extraction_log(level);
CREATE INDEX idx_extraction_log_date ON extraction_log(created_at);

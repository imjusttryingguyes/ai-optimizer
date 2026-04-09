-- AI Optimizer: Production Analytics Reports
-- Generated for Phase 1-3 implementation

-- ============================================================================
-- LEVEL 1: ACCOUNT KPI DASHBOARD (Strategic)
-- ============================================================================

-- 1.1: Current Month Pacing Status
CREATE OR REPLACE VIEW v_kpi_current_month AS
SELECT 
    p.account_id,
    p.year_month,
    EXTRACT(DAY FROM CURRENT_DATE) as days_elapsed,
    (EXTRACT(DAY FROM p.month_end) - EXTRACT(DAY FROM p.month_start) + 1)::INT as total_days,
    p.budget_rub,
    p.leads_target,
    p.cpa_target_rub,
    
    -- Expected daily pace
    (p.budget_rub / ((EXTRACT(DAY FROM p.month_end) - EXTRACT(DAY FROM p.month_start) + 1)))::NUMERIC(10,2) as daily_budget_pace,
    (p.leads_target / ((EXTRACT(DAY FROM p.month_end) - EXTRACT(DAY FROM p.month_start) + 1)))::NUMERIC(10,2) as daily_leads_pace,
    
    -- Actual to date
    COALESCE(SUM(ks.spend_rub), 0)::NUMERIC(15,2) as spend_actual,
    COALESCE(SUM(ks.clicks), 0) as conversions_actual,  -- TODO: Use real conversions when available
    
    -- Pacing calculations
    (COALESCE(SUM(ks.spend_rub), 0) / (p.budget_rub / ((EXTRACT(DAY FROM p.month_end) - EXTRACT(DAY FROM p.month_start) + 1) * EXTRACT(DAY FROM CURRENT_DATE))))::NUMERIC(5,2) as budget_pacing_pct,
    (COALESCE(SUM(ks.clicks), 0) / (p.leads_target / ((EXTRACT(DAY FROM p.month_end) - EXTRACT(DAY FROM p.month_start) + 1) * EXTRACT(DAY FROM CURRENT_DATE))))::NUMERIC(5,2) as leads_pacing_pct,
    
    -- Projected end-of-month
    (COALESCE(SUM(ks.spend_rub), 0) / EXTRACT(DAY FROM CURRENT_DATE) * (EXTRACT(DAY FROM p.month_end) - EXTRACT(DAY FROM p.month_start) + 1))::NUMERIC(15,2) as spend_projected,
    (COALESCE(SUM(ks.clicks), 0) / EXTRACT(DAY FROM CURRENT_DATE) * (EXTRACT(DAY FROM p.month_end) - EXTRACT(DAY FROM p.month_start) + 1))::BIGINT as conversions_projected,
    
    -- Status
    CASE 
        WHEN (COALESCE(SUM(ks.spend_rub), 0) / (p.budget_rub / ((EXTRACT(DAY FROM p.month_end) - EXTRACT(DAY FROM p.month_start) + 1) * EXTRACT(DAY FROM CURRENT_DATE)))) > 1.1 THEN 'over_budget'
        WHEN (COALESCE(SUM(ks.spend_rub), 0) / (p.budget_rub / ((EXTRACT(DAY FROM p.month_end) - EXTRACT(DAY FROM p.month_start) + 1) * EXTRACT(DAY FROM CURRENT_DATE)))) < 0.9 THEN 'under_budget'
        ELSE 'on_track'
    END as budget_status
    
FROM kpi_monthly_plan p
LEFT JOIN kpi_daily_summary ks ON p.account_id = ks.account_id 
    AND ks.date >= p.month_start AND ks.date <= p.month_end
WHERE p.year_month = DATE_TRUNC('month', CURRENT_DATE)::DATE
GROUP BY p.id, p.account_id, p.year_month, p.budget_rub, p.leads_target, p.cpa_target_rub, p.month_start, p.month_end;

-- ============================================================================
-- LEVEL 2: TREND ANALYSIS (30-day account baselines) (Tactical)
-- ============================================================================

-- 2.1: Device Performance Comparison
CREATE OR REPLACE VIEW v_level2_device_analysis AS
SELECT 
    account_id,
    segment_value as device,
    impressions,
    clicks,
    spend_rub,
    cpc_rub,
    
    -- Account average
    (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'device' AND baseline_date = sb.baseline_date) as account_avg_cpc,
    
    -- Deviation %
    ((cpc_rub - (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'device' AND baseline_date = sb.baseline_date)) 
     / (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'device' AND baseline_date = sb.baseline_date) * 100)::NUMERIC(5,2) as deviation_pct,
    
    -- Volume %
    (spend_rub / (SELECT SUM(spend_rub) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'device' AND baseline_date = sb.baseline_date) * 100)::NUMERIC(5,2) as volume_pct,
    
    CASE 
        WHEN cpc_rub > (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
             WHERE account_id = sb.account_id AND segment_type = 'device' AND baseline_date = sb.baseline_date) * 1.2 THEN 'critical'
        WHEN cpc_rub > (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
             WHERE account_id = sb.account_id AND segment_type = 'device' AND baseline_date = sb.baseline_date) * 1.1 THEN 'warning'
        ELSE 'ok'
    END as status
    
FROM segment_baseline sb
WHERE segment_type = 'device'
AND baseline_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY deviation_pct DESC;

-- 2.2: Network (Search vs Display) Performance
CREATE OR REPLACE VIEW v_level2_network_analysis AS
SELECT 
    account_id,
    segment_value as network,
    impressions,
    clicks,
    spend_rub,
    cpc_rub,
    
    (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'network' AND baseline_date = sb.baseline_date) as account_avg_cpc,
    
    ((cpc_rub - (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'network' AND baseline_date = sb.baseline_date)) 
     / (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'network' AND baseline_date = sb.baseline_date) * 100)::NUMERIC(5,2) as deviation_pct,
    
    (spend_rub / (SELECT SUM(spend_rub) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'network' AND baseline_date = sb.baseline_date) * 100)::NUMERIC(5,2) as volume_pct
    
FROM segment_baseline sb
WHERE segment_type = 'network'
AND baseline_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY deviation_pct DESC;

-- 2.3: Age Group Performance
CREATE OR REPLACE VIEW v_level2_age_analysis AS
SELECT 
    account_id,
    segment_value as age_group,
    impressions,
    clicks,
    spend_rub,
    cpc_rub,
    
    (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'age' AND baseline_date = sb.baseline_date) as account_avg_cpc,
    
    ((cpc_rub - (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'age' AND baseline_date = sb.baseline_date)) 
     / (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'age' AND baseline_date = sb.baseline_date) * 100)::NUMERIC(5,2) as deviation_pct,
    
    (spend_rub / (SELECT SUM(spend_rub) FROM segment_baseline 
     WHERE account_id = sb.account_id AND segment_type = 'age' AND baseline_date = sb.baseline_date) * 100)::NUMERIC(5,2) as volume_pct,
    
    CASE 
        WHEN cpc_rub > (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
             WHERE account_id = sb.account_id AND segment_type = 'age' AND baseline_date = sb.baseline_date) * 1.5 THEN 'high_cost'
        WHEN cpc_rub > (SELECT SUM(spend_rub) / NULLIF(SUM(clicks), 0) FROM segment_baseline 
             WHERE account_id = sb.account_id AND segment_type = 'age' AND baseline_date = sb.baseline_date) * 1.2 THEN 'above_avg'
        ELSE 'normal'
    END as status
    
FROM segment_baseline sb
WHERE segment_type = 'age'
AND baseline_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY deviation_pct DESC;

-- ============================================================================
-- LEVEL 3: CAMPAIGN ANALYSIS (7-day dynamics) (Operational)
-- ============================================================================

-- 3.1: Campaign Health Check (current week vs plan)
CREATE OR REPLACE VIEW v_level3_campaign_health AS
SELECT 
    cm.account_id,
    cm.campaign_id,
    MAX(cm.date) as last_date,
    
    SUM(cm.spend_rub)::NUMERIC(15,2) as spend_7d,
    SUM(cm.clicks)::BIGINT as clicks_7d,
    SUM(cm.impressions)::BIGINT as impressions_7d,
    
    CASE WHEN SUM(cm.clicks) > 0 THEN (SUM(cm.spend_rub) / SUM(cm.clicks))::NUMERIC(10,2) ELSE 0 END as cpc_7d,
    
    -- vs account target
    at.cpa_target_rub,
    CASE 
        WHEN (SUM(cm.spend_rub) / NULLIF(SUM(cm.clicks), 0)) > at.cpa_target_rub * 1.2 THEN 'high_cost'
        WHEN (SUM(cm.spend_rub) / NULLIF(SUM(cm.clicks), 0)) > at.cpa_target_rub THEN 'above_target'
        ELSE 'ok'
    END as vs_target_status,
    
    -- Previous 7d comparison
    (SELECT SUM(spend_rub) FROM campaign_metrics cm2 
     WHERE cm2.campaign_id = cm.campaign_id AND cm2.date BETWEEN (MAX(cm.date) - INTERVAL '14 days') AND (MAX(cm.date) - INTERVAL '8 days')) as spend_prev_7d,
    
    (SELECT SUM(clicks) FROM campaign_metrics cm2 
     WHERE cm2.campaign_id = cm.campaign_id AND cm2.date BETWEEN (MAX(cm.date) - INTERVAL '14 days') AND (MAX(cm.date) - INTERVAL '8 days')) as clicks_prev_7d

FROM campaign_metrics cm
LEFT JOIN account_targets at ON cm.account_id = at.account_id
WHERE cm.date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY cm.account_id, cm.campaign_id, at.cpa_target_rub
ORDER BY spend_7d DESC;


DROP MATERIALIZED VIEW IF EXISTS kpi_account_trends;

CREATE MATERIALIZED VIEW kpi_account_trends AS
WITH daily_metrics AS (
	SELECT
		date,
		account_id,
		client_login,
		SUM(impressions) AS impressions,
		SUM(clicks) AS clicks,
		SUM(cost_rub) AS spend_rub
	FROM direct_daily_spend_fact
	WHERE date >= CURRENT_DATE - INTERVAL '7 days'
	GROUP BY date, account_id, client_login
),
daily_conv AS (
	SELECT
		date,
		account_id,
		client_login,
		SUM(conversions) AS conversions
	FROM direct_daily_goal_conv_fact
	WHERE date >= CURRENT_DATE - INTERVAL '7 days'
	GROUP BY date, account_id, client_login
),
account_periods AS (
	SELECT
		account_id,
		client_login,
		
		-- Last 3 days
		SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '2 days' THEN d.spend_rub ELSE 0 END) AS spend_last_3d,
		SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '2 days' THEN COALESCE(c.conversions, 0) ELSE 0 END) AS conv_last_3d,
		COUNT(CASE WHEN date >= CURRENT_DATE - INTERVAL '2 days' THEN 1 END) AS data_days_last_3d,
		
		-- Previous 4 days (days 4-7 ago)
		SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '6 days' AND date < CURRENT_DATE - INTERVAL '2 days' THEN d.spend_rub ELSE 0 END) AS spend_prev_4d,
		SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '6 days' AND date < CURRENT_DATE - INTERVAL '2 days' THEN COALESCE(c.conversions, 0) ELSE 0 END) AS conv_prev_4d,
		COUNT(CASE WHEN date >= CURRENT_DATE - INTERVAL '6 days' AND date < CURRENT_DATE - INTERVAL '2 days' THEN 1 END) AS data_days_prev_4d
		
	FROM daily_metrics d
	LEFT JOIN daily_conv c USING (date, account_id, client_login)
	GROUP BY account_id, client_login
)
SELECT
	account_id,
	client_login,
	CURRENT_DATE AS anchor_date,
	data_days_last_3d,
	data_days_prev_4d,
	
	-- CPA calculations
	CASE 
		WHEN conv_last_3d > 0 THEN spend_last_3d / conv_last_3d 
		ELSE NULL 
	END AS cpa_last_3d,
	
	CASE 
		WHEN conv_prev_4d > 0 THEN spend_prev_4d / conv_prev_4d 
		ELSE NULL 
	END AS cpa_prev_4d,
	
	-- Conversions per day
	CASE 
		WHEN data_days_last_3d > 0 THEN conv_last_3d / data_days_last_3d 
		ELSE 0 
	END AS conv_per_day_last_3d,
	
	CASE 
		WHEN data_days_prev_4d > 0 THEN conv_prev_4d / data_days_prev_4d 
		ELSE 0 
	END AS conv_per_day_prev_4d
	
FROM account_periods
ORDER BY account_id;
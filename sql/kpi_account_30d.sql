DROP MATERIALIZED VIEW IF EXISTS kpi_account_30d;

CREATE MATERIALIZED VIEW kpi_account_30d AS
WITH spend AS (
	SELECT
		account_id,
		client_login,
		SUM(impressions) AS impressions,
		SUM(clicks) AS clicks,
		SUM(cost_rub) AS spend_rub
	FROM direct_daily_spend_fact
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
	GROUP BY
		account_id,
		client_login
),
conv AS (
	SELECT
		account_id,
		client_login,
		SUM(conversions) AS conversions
	FROM direct_daily_goal_conv_fact
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
	GROUP BY
		account_id,
		client_login
)
SELECT
	s.account_id,
	s.client_login,
	s.impressions,
	s.clicks,
	s.spend_rub,
	COALESCE(c.conversions, 0) AS conversions,
	CASE
		WHEN s.clicks > 0
			THEN COALESCE(c.conversions, 0)::numeric / s.clicks
		ELSE 0
	END AS cr,
	CASE
		WHEN COALESCE(c.conversions, 0) > 0
			THEN s.spend_rub / COALESCE(c.conversions, 0)
		ELSE NULL
	END AS cpa
FROM spend s
LEFT JOIN conv c
	ON s.account_id = c.account_id
	AND s.client_login = c.client_login;
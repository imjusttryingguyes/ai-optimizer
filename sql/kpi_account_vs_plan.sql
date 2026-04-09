DROP MATERIALIZED VIEW IF EXISTS kpi_account_vs_plan;

CREATE MATERIALIZED VIEW kpi_account_vs_plan AS
WITH spend_week AS (
	SELECT
		account_id,
		client_login,
		SUM(impressions) AS impressions_week,
		SUM(clicks) AS clicks_week,
		SUM(cost_rub) AS spend_rub_week
	FROM direct_daily_spend_fact
	WHERE date >= CURRENT_DATE - INTERVAL '7 days'
	GROUP BY account_id, client_login
),
spend_30d AS (
	SELECT
		account_id,
		client_login,
		SUM(impressions) AS impressions_30d,
		SUM(clicks) AS clicks_30d,
		SUM(cost_rub) AS spend_rub_30d
	FROM direct_daily_spend_fact
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
	GROUP BY account_id, client_login
),
conv_week AS (
	SELECT
		account_id,
		client_login,
		SUM(conversions) AS conversions_week
	FROM direct_daily_goal_conv_fact
	WHERE date >= CURRENT_DATE - INTERVAL '7 days'
	GROUP BY account_id, client_login
),
conv_30d AS (
	SELECT
		account_id,
		client_login,
		SUM(conversions) AS conversions_30d
	FROM direct_daily_goal_conv_fact
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
	GROUP BY account_id, client_login
),
targets AS (
	SELECT
		account_id,
		client_login,
		cpa_plan,
		conversions_plan_daily
	FROM account_targets
	WHERE is_active = true
)
SELECT
	COALESCE(s7.account_id, s30.account_id, c7.account_id, c30.account_id, t.account_id) AS account_id,
	COALESCE(s7.client_login, s30.client_login, c7.client_login, c30.client_login, t.client_login) AS client_login,

	-- Data availability
	CASE WHEN s7.clicks_week IS NOT NULL THEN 7 ELSE 0 END AS data_days_week,
	CASE WHEN s30.clicks_30d IS NOT NULL THEN 30 ELSE 0 END AS data_days_30d,

	-- Week metrics
	COALESCE(s7.spend_rub_week, 0) AS spend_rub_week,
	COALESCE(s7.clicks_week, 0) AS clicks_week,
	COALESCE(c7.conversions_week, 0) AS conversions_week,
	CASE
		WHEN COALESCE(c7.conversions_week, 0) > 0
			THEN COALESCE(s7.spend_rub_week, 0) / COALESCE(c7.conversions_week, 0)
		ELSE NULL
	END AS cpa_week,
	COALESCE(c7.conversions_week, 0)::numeric / 7 AS conversions_per_day_week,

	-- 30d metrics
	COALESCE(s30.spend_rub_30d, 0) AS spend_rub_30d,
	COALESCE(s30.clicks_30d, 0) AS clicks_30d,
	COALESCE(c30.conversions_30d, 0) AS conversions_30d,
	CASE
		WHEN COALESCE(c30.conversions_30d, 0) > 0
			THEN COALESCE(s30.spend_rub_30d, 0) / COALESCE(c30.conversions_30d, 0)
		ELSE NULL
	END AS cpa_30d,
	COALESCE(c30.conversions_30d, 0)::numeric / 30 AS conversions_per_day_30d,

	-- Plan targets
	COALESCE(t.cpa_plan, 0) AS cpa_plan,
	COALESCE(t.conversions_plan_daily, 0) AS conversions_plan_daily

FROM spend_week s7
FULL OUTER JOIN spend_30d s30 USING (account_id, client_login)
FULL OUTER JOIN conv_week c7 USING (account_id, client_login)
FULL OUTER JOIN conv_30d c30 USING (account_id, client_login)
FULL OUTER JOIN targets t USING (account_id, client_login);
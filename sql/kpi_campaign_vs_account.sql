DROP MATERIALIZED VIEW IF EXISTS kpi_campaign_vs_account;

CREATE MATERIALIZED VIEW kpi_campaign_vs_account AS
WITH campaign_spend AS (
	SELECT
		date,
		account_id,
		client_login,
		campaign_id,
		SUM(impressions) AS impressions,
		SUM(clicks) AS clicks,
		SUM(cost_rub) AS spend_rub
	FROM direct_daily_spend_fact
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
	GROUP BY date, account_id, client_login, campaign_id
),
campaign_conv AS (
	SELECT
		date,
		account_id,
		client_login,
		campaign_id,
		SUM(conversions) AS conversions
	FROM direct_daily_goal_conv_fact
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
	GROUP BY date, account_id, client_login, campaign_id
),
account_totals AS (
	SELECT
		account_id,
		client_login,
		SUM(impressions) AS account_impressions,
		SUM(clicks) AS account_clicks,
		SUM(spend_rub) AS account_spend,
		SUM(conversions) AS account_conversions
	FROM (
		SELECT
			account_id,
			client_login,
			impressions,
			clicks,
			spend_rub,
			0 AS conversions
		FROM campaign_spend
		UNION ALL
		SELECT
			account_id,
			client_login,
			0 AS impressions,
			0 AS clicks,
			0 AS spend_rub,
			conversions
		FROM campaign_conv
	) t
	GROUP BY account_id, client_login
)
SELECT
	c.date,
	c.account_id,
	c.client_login,
	c.campaign_id,
	c.impressions,
	c.clicks,
	c.spend_rub,
	COALESCE(cv.conversions, 0) AS conversions,

	-- Campaign metrics
	CASE
		WHEN c.clicks > 0 THEN COALESCE(cv.conversions, 0)::numeric / c.clicks
		ELSE 0
	END AS cr,
	CASE
		WHEN COALESCE(cv.conversions, 0) > 0 THEN c.spend_rub / COALESCE(cv.conversions, 0)
		ELSE NULL
	END AS cpa,

	-- Account totals for comparison
	a.account_impressions,
	a.account_clicks,
	a.account_spend,
	a.account_conversions,

	-- Campaign share of account
	CASE
		WHEN a.account_spend > 0 THEN c.spend_rub / a.account_spend
		ELSE 0
	END AS spend_share,
	CASE
		WHEN a.account_conversions > 0 THEN COALESCE(cv.conversions, 0) / a.account_conversions
		ELSE 0
	END AS conversions_share

FROM campaign_spend c
LEFT JOIN campaign_conv cv USING (date, account_id, client_login, campaign_id)
LEFT JOIN account_totals a USING (account_id, client_login)
ORDER BY c.account_id, c.client_login, c.spend_rub DESC;
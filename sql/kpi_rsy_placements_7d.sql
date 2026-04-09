DROP MATERIALIZED VIEW IF EXISTS kpi_rsy_placements_7d;

CREATE MATERIALIZED VIEW kpi_rsy_placements_7d AS
WITH placement_spend AS (
	SELECT
		date,
		account_id,
		client_login,
		placement,
		SUM(impressions) AS impressions,
		SUM(clicks) AS clicks,
		SUM(cost_rub) AS spend_rub
	FROM direct_daily_placement_fact
	WHERE date >= CURRENT_DATE - INTERVAL '7 days'
	GROUP BY date, account_id, client_login, placement
),
placement_conv AS (
	SELECT
		date,
		account_id,
		client_login,
		placement,
		SUM(conversions_selected) AS conversions
	FROM direct_daily_placement_fact
	WHERE date >= CURRENT_DATE - INTERVAL '7 days'
	GROUP BY date, account_id, client_login, placement
),
placement_stats AS (
	SELECT
		p.date,
		p.account_id,
		p.client_login,
		p.placement,
		p.impressions,
		p.clicks,
		p.spend_rub,
		COALESCE(c.conversions, 0) AS conversions,
		CASE
			WHEN p.clicks > 0 THEN COALESCE(c.conversions, 0)::numeric / p.clicks
			ELSE 0
		END AS cr,
		CASE
			WHEN COALESCE(c.conversions, 0) > 0 THEN p.spend_rub / COALESCE(c.conversions, 0)
			ELSE NULL
		END AS cpa
	FROM placement_spend p
	LEFT JOIN placement_conv c USING (date, account_id, client_login, placement)
)
SELECT
	date,
	account_id,
	client_login,
	placement,
	impressions,
	clicks,
	spend_rub,
	conversions,
	cr,
	cpa,

	-- Performance ranking within account
	RANK() OVER (
		PARTITION BY account_id, client_login
		ORDER BY spend_rub DESC
	) AS spend_rank,

	RANK() OVER (
		PARTITION BY account_id, client_login
		ORDER BY conversions DESC
	) AS conversions_rank,

	RANK() OVER (
		PARTITION BY account_id, client_login
		ORDER BY cpa ASC NULLS LAST
	) AS cpa_rank

FROM placement_stats
ORDER BY account_id, client_login, spend_rub DESC;
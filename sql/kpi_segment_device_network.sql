DROP MATERIALIZED VIEW IF EXISTS kpi_segment_device_network;

CREATE MATERIALIZED VIEW kpi_segment_device_network AS
WITH segment_spend AS (
	SELECT
		date,
		account_id,
		client_login,
		ad_network_type,
		device,
		SUM(impressions) AS impressions,
		SUM(clicks) AS clicks,
		SUM(cost_rub) AS spend_rub
	FROM direct_daily_spend_fact
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
	GROUP BY date, account_id, client_login, ad_network_type, device
),
segment_conv AS (
	SELECT
		date,
		account_id,
		client_login,
		ad_network_type,
		device,
		SUM(conversions) AS conversions
	FROM direct_daily_goal_conv_fact
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
	GROUP BY date, account_id, client_login, ad_network_type, device
),
segment_metrics AS (
	SELECT
		s.date,
		s.account_id,
		s.client_login,
		s.ad_network_type,
		s.device,
		s.impressions,
		s.clicks,
		s.spend_rub,
		COALESCE(c.conversions, 0) AS conversions,
		CASE
			WHEN s.clicks > 0 THEN COALESCE(c.conversions, 0)::numeric / s.clicks
			ELSE 0
		END AS cr,
		CASE
			WHEN COALESCE(c.conversions, 0) > 0 THEN s.spend_rub / COALESCE(c.conversions, 0)
			ELSE NULL
		END AS cpa
	FROM segment_spend s
	LEFT JOIN segment_conv c USING (date, account_id, client_login, ad_network_type, device)
)
SELECT
	date,
	account_id,
	client_login,
	ad_network_type,
	device,
	s.impressions,
	s.clicks,
	s.spend_rub,
	s.conversions,
	s.cr,
	s.cpa AS cpa_segment,
	a.cpa AS cpa_account,

	-- Performance within account
	RANK() OVER (
		PARTITION BY s.account_id, s.client_login
		ORDER BY s.spend_rub DESC
	) AS spend_rank,

	RANK() OVER (
		PARTITION BY s.account_id, s.client_login
		ORDER BY s.conversions DESC
	) AS conversions_rank,

	RANK() OVER (
		PARTITION BY s.account_id, s.client_login
		ORDER BY s.cpa ASC NULLS LAST
	) AS cpa_rank,

	-- Network/device combinations
	CASE
		WHEN ad_network_type = 'SEARCH' AND device = 'DESKTOP' THEN 'Search Desktop'
		WHEN ad_network_type = 'SEARCH' AND device = 'MOBILE' THEN 'Search Mobile'
		WHEN ad_network_type = 'NETWORK' AND device = 'DESKTOP' THEN 'Network Desktop'
		WHEN ad_network_type = 'NETWORK' AND device = 'MOBILE' THEN 'Network Mobile'
		ELSE ad_network_type || ' ' || device
	END AS segment_name

FROM segment_metrics s
LEFT JOIN kpi_account_30d a USING (account_id, client_login)
ORDER BY s.account_id, s.client_login, s.spend_rub DESC;
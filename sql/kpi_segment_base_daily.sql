DROP MATERIALIZED VIEW IF EXISTS kpi_segment_base_daily;

CREATE MATERIALIZED VIEW kpi_segment_base_daily AS
WITH spend AS (
	SELECT
		date,
		account_id,
		client_login,
		ad_network_type,
		device,
		age,
		gender,
		SUM(impressions) AS impressions,
		SUM(clicks) AS clicks,
		SUM(cost_rub) AS spend_rub
	FROM direct_daily_spend_fact
	GROUP BY
		date,
		account_id,
		client_login,
		ad_network_type,
		device,
		age,
		gender
),
conv AS (
	SELECT
		date,
		account_id,
		client_login,
		ad_network_type,
		device,
		age,
		gender,
		SUM(conversions) AS conversions
	FROM direct_daily_goal_conv_fact
	GROUP BY
		date,
		account_id,
		client_login,
		ad_network_type,
		device,
		age,
		gender
)
SELECT
	s.date,
	s.account_id,
	s.client_login,
	s.ad_network_type,
	s.device,
	s.age,
	s.gender,
	s.impressions,
	s.clicks,
	s.spend_rub,
	COALESCE(c.conversions, 0) AS conversions
FROM spend s
LEFT JOIN conv c
	ON s.date = c.date
	AND s.account_id = c.account_id
	AND s.client_login = c.client_login
	AND s.ad_network_type = c.ad_network_type
	AND s.device = c.device
	AND s.age = c.age
	AND s.gender = c.gender;
DROP MATERIALIZED VIEW IF EXISTS kpi_segment_combinations_30d;

CREATE MATERIALIZED VIEW kpi_segment_combinations_30d AS
WITH spend AS (
	SELECT
		date,
		account_id,
		client_login,
		campaign_id,
		adgroup_id,
		criterion_id,
		device,
		ad_network_type,
		location_of_presence_name,
		targeting_location_name,
		age,
		gender,
		to_char(date, 'FMDay') AS weekday,
		SUM(impressions) AS impressions,
		SUM(clicks) AS clicks,
		SUM(cost_rub) AS spend_rub
	FROM direct_daily_spend_fact
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
	GROUP BY
		date,
		account_id,
		client_login,
		campaign_id,
		adgroup_id,
		criterion_id,
		device,
		ad_network_type,
		location_of_presence_name,
		targeting_location_name,
		age,
		gender
),
conv AS (
	SELECT
		date,
		account_id,
		client_login,
		campaign_id,
		adgroup_id,
		criterion_id,
		device,
		ad_network_type,
		location_of_presence_name,
		targeting_location_name,
		age,
		gender,
		to_char(date, 'FMDay') AS weekday,
		SUM(conversions) AS conversions
	FROM direct_daily_goal_conv_fact
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
	GROUP BY
		date,
		account_id,
		client_login,
		campaign_id,
		adgroup_id,
		criterion_id,
		device,
		ad_network_type,
		location_of_presence_name,
		targeting_location_name,
		age,
		gender
)
SELECT
	s.date,
	s.weekday,
	s.account_id,
	s.client_login,
	s.campaign_id,
	s.adgroup_id,
	s.criterion_id,
	s.device,
	s.ad_network_type,
	s.location_of_presence_name,
	s.targeting_location_name,
	s.age,
	s.gender,
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
	ON s.date = c.date
	AND s.account_id = c.account_id
	AND s.client_login = c.client_login
	AND s.campaign_id = c.campaign_id
	AND s.adgroup_id = c.adgroup_id
	AND s.criterion_id = c.criterion_id
	AND s.device = c.device
	AND s.ad_network_type = c.ad_network_type
	AND s.location_of_presence_name = c.location_of_presence_name
	AND s.targeting_location_name = c.targeting_location_name
	AND s.age = c.age
	AND s.gender = c.gender;
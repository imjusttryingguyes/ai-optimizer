DROP MATERIALIZED VIEW IF EXISTS kpi_segment_combinations_trend_7d;

CREATE MATERIALIZED VIEW kpi_segment_combinations_trend_7d AS
WITH daily AS (
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
		SUM(spend_rub) AS spend_rub,
		SUM(conversions) AS conversions
	FROM kpi_segment_combinations_30d
	GROUP BY
		date,
		account_id,
		client_login,
		ad_network_type,
		device,
		age,
		gender
),
recent AS (
	SELECT
		account_id,
		client_login,
		ad_network_type,
		device,
		age,
		gender,
		COUNT(DISTINCT date) AS data_days_recent_7d,
		SUM(impressions) AS impressions_recent_7d,
		SUM(clicks) AS clicks_recent_7d,
		SUM(spend_rub) AS spend_recent_7d,
		SUM(conversions) AS conversions_recent_7d
	FROM daily
	WHERE date >= CURRENT_DATE - INTERVAL '7 days'
	GROUP BY
		account_id,
		client_login,
		ad_network_type,
		device,
		age,
		gender
),
baseline AS (
	SELECT
		account_id,
		client_login,
		ad_network_type,
		device,
		age,
		gender,
		COUNT(DISTINCT date) AS data_days_baseline_23d,
		SUM(impressions) AS impressions_baseline_23d,
		SUM(clicks) AS clicks_baseline_23d,
		SUM(spend_rub) AS spend_baseline_23d,
		SUM(conversions) AS conversions_baseline_23d
	FROM daily
	WHERE date >= CURRENT_DATE - INTERVAL '30 days'
		AND date < CURRENT_DATE - INTERVAL '7 days'
	GROUP BY
		account_id,
		client_login,
		ad_network_type,
		device,
		age,
		gender
)
SELECT
	r.account_id,
	r.client_login,
	r.ad_network_type,
	r.device,
	r.age,
	r.gender,

	r.data_days_recent_7d,
	b.data_days_baseline_23d,

	r.impressions_recent_7d,
	r.clicks_recent_7d,
	r.spend_recent_7d,
	r.conversions_recent_7d,

	b.impressions_baseline_23d,
	b.clicks_baseline_23d,
	b.spend_baseline_23d,
	b.conversions_baseline_23d,

	CASE
		WHEN r.conversions_recent_7d > 0
			THEN r.spend_recent_7d / r.conversions_recent_7d
		ELSE NULL
	END AS cpa_recent_7d,

	CASE
		WHEN b.conversions_baseline_23d > 0
			THEN b.spend_baseline_23d / b.conversions_baseline_23d
		ELSE NULL
	END AS cpa_baseline_23d,

	CASE
		WHEN r.clicks_recent_7d > 0
			THEN r.conversions_recent_7d::numeric / r.clicks_recent_7d
		ELSE 0
	END AS cr_recent_7d,

	CASE
		WHEN b.clicks_baseline_23d > 0
			THEN b.conversions_baseline_23d::numeric / b.clicks_baseline_23d
		ELSE 0
	END AS cr_baseline_23d,

	CASE
		WHEN r.data_days_recent_7d > 0
			THEN r.conversions_recent_7d::numeric / r.data_days_recent_7d
		ELSE 0
	END AS conv_per_day_recent_7d,

	CASE
		WHEN b.data_days_baseline_23d > 0
			THEN b.conversions_baseline_23d::numeric / b.data_days_baseline_23d
		ELSE 0
	END AS conv_per_day_baseline_23d

FROM recent r
JOIN baseline b
	ON r.account_id = b.account_id
	AND r.client_login = b.client_login
	AND r.ad_network_type = b.ad_network_type
	AND r.device = b.device
	AND r.age = b.age
	AND r.gender = b.gender;
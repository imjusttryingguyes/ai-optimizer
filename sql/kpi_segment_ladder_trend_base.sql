DROP MATERIALIZED VIEW IF EXISTS kpi_segment_ladder_trend_base;

CREATE MATERIALIZED VIEW kpi_segment_ladder_trend_base AS
SELECT
	date,
	account_id,
	client_login,
	ad_network_type,
	device,
	age,
	gender,
	impressions,
	clicks,
	spend_rub,
	conversions
FROM kpi_segment_base_daily;
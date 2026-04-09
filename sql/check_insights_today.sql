SELECT
	type,
	COUNT(*) AS cnt,
	SUM(impact_rub) AS total_impact
FROM insights
WHERE insight_date = CURRENT_DATE
GROUP BY type
ORDER BY total_impact DESC NULLS LAST;

SELECT
	type,
	title,
	impact_rub,
	confidence,
	priority,
	status
FROM insights
WHERE insight_date = CURRENT_DATE
ORDER BY priority DESC NULLS LAST
LIMIT 30;
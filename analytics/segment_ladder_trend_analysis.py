import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

from insight_utils import insert_insight


RECENT_DAYS = 7
BASELINE_DAYS = 23

MIN_RECENT_SPEND_RUB = 1000
MIN_RECENT_CLICKS = 10
MIN_RECENT_CONVERSIONS = 1
MIN_BASELINE_CONVERSIONS = 1
MIN_RECENT_DATA_DAYS = 1
MIN_BASELINE_DATA_DAYS = 1

TREND_BAD_MULTIPLIER = 1.3
TREND_GOOD_MULTIPLIER = 0.7

DIMENSION_PROFILES = [
	("ad_network_type", "device", "age", "gender"),

	("ad_network_type", "device", "age"),
	("ad_network_type", "device", "gender"),
	("ad_network_type", "age", "gender"),
	("device", "age", "gender"),

	("ad_network_type", "device"),
	("ad_network_type", "age"),
	("ad_network_type", "gender"),
	("device", "age"),
	("device", "gender"),
	("age", "gender"),

	("ad_network_type",),
	("device",),
	("age",),
	("gender",),
]


def get_conn():
	return psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)


def build_segment_key(profile, row_dict):
	parts = []
	for dim in profile:
		parts.append(str(row_dict.get(dim, "ALL")))
	return "|".join(parts)


def build_title(profile, row_dict):
	parts = []
	for dim in profile:
		parts.append(f"{dim}={row_dict.get(dim, 'ALL')}")
	return ", ".join(parts)


def has_unknown_dimension(profile, row_dict):
	for dim in profile:
		value = row_dict.get(dim)
		if value is None:
			return True
		if str(value).upper() == "UNKNOWN":
			return True
	return False


def build_projection_key(target_profile, row_dict):
	parts = []
	for dim in target_profile:
		parts.append(str(row_dict.get(dim, "ALL")))
	return "|".join(parts)


def get_parent_profiles(profile):
	parents = []

	for candidate in DIMENSION_PROFILES:
		if candidate == profile:
			continue

		if len(candidate) >= len(profile):
			continue

		if all(dim in profile for dim in candidate):
			parents.append(candidate)

	return parents


def fetch_profile_rows(cur, profile):
	select_dims = ",\n\t\t\t".join(profile)
	group_dims = ",\n\t\t\t".join(profile)

	query = f"""
		WITH recent AS (
			SELECT
				account_id,
				client_login,
				{select_dims},
				COUNT(DISTINCT date) AS data_days_recent,
				SUM(impressions) AS impressions_recent,
				SUM(clicks) AS clicks_recent,
				SUM(spend_rub) AS spend_recent,
				SUM(conversions) AS conversions_recent
			FROM kpi_segment_ladder_trend_base
			WHERE date >= CURRENT_DATE - INTERVAL '{RECENT_DAYS} days'
			GROUP BY
				account_id,
				client_login,
				{group_dims}
		),
		baseline AS (
			SELECT
				account_id,
				client_login,
				{select_dims},
				COUNT(DISTINCT date) AS data_days_baseline,
				SUM(impressions) AS impressions_baseline,
				SUM(clicks) AS clicks_baseline,
				SUM(spend_rub) AS spend_baseline,
				SUM(conversions) AS conversions_baseline
			FROM kpi_segment_ladder_trend_base
			WHERE date >= CURRENT_DATE - INTERVAL '{RECENT_DAYS + BASELINE_DAYS} days'
				AND date < CURRENT_DATE - INTERVAL '{RECENT_DAYS} days'
			GROUP BY
				account_id,
				client_login,
				{group_dims}
		)
		SELECT
			r.account_id,
			r.client_login,
			{", ".join([f"r.{d}" for d in profile])},
			r.data_days_recent,
			b.data_days_baseline,
			r.impressions_recent,
			r.clicks_recent,
			r.spend_recent,
			r.conversions_recent,
			b.impressions_baseline,
			b.clicks_baseline,
			b.spend_baseline,
			b.conversions_baseline,
			CASE
				WHEN r.conversions_recent > 0
					THEN r.spend_recent / r.conversions_recent
				ELSE NULL
			END AS cpa_recent,
			CASE
				WHEN b.conversions_baseline > 0
					THEN b.spend_baseline / b.conversions_baseline
				ELSE NULL
			END AS cpa_baseline,
			CASE
				WHEN r.data_days_recent > 0
					THEN r.conversions_recent::numeric / r.data_days_recent
				ELSE 0
			END AS conv_per_day_recent,
			CASE
				WHEN b.data_days_baseline > 0
					THEN b.conversions_baseline::numeric / b.data_days_baseline
				ELSE 0
			END AS conv_per_day_baseline
		FROM recent r
		JOIN baseline b
			ON r.account_id = b.account_id
			AND r.client_login = b.client_login
			AND {" AND ".join([f"r.{d} = b.{d}" for d in profile])}
	"""

	cur.execute(query)
	colnames = [desc[0] for desc in cur.description]
	rows = cur.fetchall()

	result = []
	for row in rows:
		result.append(dict(zip(colnames, row)))

	return result


def main():
	conn = get_conn()
	cur = conn.cursor()

	covered_segments = set()

	for profile in DIMENSION_PROFILES:
		print(f"Processing trend profile: {profile}")

		rows = fetch_profile_rows(cur, profile)

		for row in rows:
			account_id = row["account_id"]
			client_login = row["client_login"]

			data_days_recent = int(row["data_days_recent"] or 0)
			data_days_baseline = int(row["data_days_baseline"] or 0)

			impressions_recent = int(row["impressions_recent"] or 0)
			clicks_recent = int(row["clicks_recent"] or 0)
			spend_recent = float(row["spend_recent"] or 0)
			conversions_recent = float(row["conversions_recent"] or 0)

			impressions_baseline = int(row["impressions_baseline"] or 0)
			clicks_baseline = int(row["clicks_baseline"] or 0)
			spend_baseline = float(row["spend_baseline"] or 0)
			conversions_baseline = float(row["conversions_baseline"] or 0)

			cpa_recent = float(row["cpa_recent"]) if row["cpa_recent"] is not None else None
			cpa_baseline = float(row["cpa_baseline"]) if row["cpa_baseline"] is not None else None
			conv_per_day_recent = float(row["conv_per_day_recent"] or 0)
			conv_per_day_baseline = float(row["conv_per_day_baseline"] or 0)

			if has_unknown_dimension(profile, row):
				continue

			segment_key = build_segment_key(profile, row)
			profile_name = "__".join(profile)

			current_key = (account_id, profile_name, segment_key)
			if current_key in covered_segments:
				continue

			if data_days_recent < MIN_RECENT_DATA_DAYS:
				continue

			if data_days_baseline < MIN_BASELINE_DATA_DAYS:
				continue

			if spend_recent < MIN_RECENT_SPEND_RUB:
				continue

			if clicks_recent < MIN_RECENT_CLICKS:
				continue

			if conversions_recent < MIN_RECENT_CONVERSIONS:
				continue

			if conversions_baseline < MIN_BASELINE_CONVERSIONS:
				continue

			if cpa_recent is None or cpa_baseline is None or cpa_baseline <= 0:
				continue

			# 1. TREND_BAD
			if cpa_recent > cpa_baseline * TREND_BAD_MULTIPLIER:
				cpa_ratio = cpa_recent / cpa_baseline
				excess_cost = max(0.0, spend_recent - (conversions_recent * cpa_baseline))

				print(
					f"Creating SEGMENT_LADDER_TREND_BAD for {account_id}: "
					f"profile={profile_name}, segment={segment_key}, "
					f"cpa_recent={cpa_recent:.0f}, cpa_baseline={cpa_baseline:.0f}"
				)

				insert_insight(
					account_id=account_id,
					type="SEGMENT_LADDER_TREND_BAD",
					entity_type="segment_ladder",
					entity_id=f"{profile_name}|{segment_key}|TREND_BAD",
					severity=80,
					impact_rub=excess_cost,
					title=f"Segment trend worsened ({profile_name})",
					description=(
						f"{build_title(profile, row)} | "
						f"CPA last {RECENT_DAYS}d = {cpa_recent:.0f} ₽, "
						f"baseline {BASELINE_DAYS}d = {cpa_baseline:.0f} ₽, "
						f"ratio = {cpa_ratio:.1f}×"
					),
					recommendation=(
						"Check recent bid changes, traffic quality, creative fatigue and delivery "
						"for this segment. Consider reducing bids or isolating it."
					),
					evidence={
						"profile": list(profile),
						"profile_name": profile_name,
						"segment_key": segment_key,
						"client_login": client_login,
						"data_days_recent": data_days_recent,
						"data_days_baseline": data_days_baseline,
						"impressions_recent": impressions_recent,
						"clicks_recent": clicks_recent,
						"spend_recent": spend_recent,
						"conversions_recent": conversions_recent,
						"impressions_baseline": impressions_baseline,
						"clicks_baseline": clicks_baseline,
						"spend_baseline": spend_baseline,
						"conversions_baseline": conversions_baseline,
						"cpa_recent": cpa_recent,
						"cpa_baseline": cpa_baseline,
						"conv_per_day_recent": conv_per_day_recent,
						"conv_per_day_baseline": conv_per_day_baseline,
						"cpa_ratio": cpa_ratio,
						"estimated_excess_cost_rub": excess_cost,
						"recent_days": RECENT_DAYS,
						"baseline_days": BASELINE_DAYS,
						"dimensions": {dim: row.get(dim) for dim in profile},
					},
					confidence=1.0,
				)

				covered_segments.add(current_key)

				for parent_profile in get_parent_profiles(profile):
					parent_profile_name = "__".join(parent_profile)
					parent_segment_key = build_projection_key(parent_profile, row)
					parent_key = (account_id, parent_profile_name, parent_segment_key)
					covered_segments.add(parent_key)

				continue

			# 2. TREND_GOOD
			if (
				cpa_recent < cpa_baseline * TREND_GOOD_MULTIPLIER
				and conv_per_day_recent >= conv_per_day_baseline
			):
				cpa_ratio = cpa_recent / cpa_baseline
				saved_rub = max(0.0, (cpa_baseline - cpa_recent) * conversions_recent)

				print(
					f"Creating SEGMENT_LADDER_TREND_GOOD for {account_id}: "
					f"profile={profile_name}, segment={segment_key}, "
					f"cpa_recent={cpa_recent:.0f}, cpa_baseline={cpa_baseline:.0f}"
				)

				insert_insight(
					account_id=account_id,
					type="SEGMENT_LADDER_TREND_GOOD",
					entity_type="segment_ladder",
					entity_id=f"{profile_name}|{segment_key}|TREND_GOOD",
					severity=56,
					impact_rub=saved_rub,
					title=f"Segment trend improved ({profile_name})",
					description=(
						f"{build_title(profile, row)} | "
						f"CPA last {RECENT_DAYS}d = {cpa_recent:.0f} ₽, "
						f"baseline {BASELINE_DAYS}d = {cpa_baseline:.0f} ₽, "
						f"ratio = {cpa_ratio:.1f}×, "
						f"conv/day recent = {conv_per_day_recent:.2f}, "
						f"baseline = {conv_per_day_baseline:.2f}"
					),
					recommendation=(
						"Consider scaling this segment carefully while performance remains strong. "
						"Review bids, budgets, creatives and whether the segment should be isolated."
					),
					evidence={
						"profile": list(profile),
						"profile_name": profile_name,
						"segment_key": segment_key,
						"client_login": client_login,
						"data_days_recent": data_days_recent,
						"data_days_baseline": data_days_baseline,
						"impressions_recent": impressions_recent,
						"clicks_recent": clicks_recent,
						"spend_recent": spend_recent,
						"conversions_recent": conversions_recent,
						"impressions_baseline": impressions_baseline,
						"clicks_baseline": clicks_baseline,
						"spend_baseline": spend_baseline,
						"conversions_baseline": conversions_baseline,
						"cpa_recent": cpa_recent,
						"cpa_baseline": cpa_baseline,
						"conv_per_day_recent": conv_per_day_recent,
						"conv_per_day_baseline": conv_per_day_baseline,
						"cpa_ratio": cpa_ratio,
						"estimated_saved_rub": saved_rub,
						"recent_days": RECENT_DAYS,
						"baseline_days": BASELINE_DAYS,
						"dimensions": {dim: row.get(dim) for dim in profile},
					},
					confidence=1.0,
				)

				covered_segments.add(current_key)

				for parent_profile in get_parent_profiles(profile):
					parent_profile_name = "__".join(parent_profile)
					parent_segment_key = build_projection_key(parent_profile, row)
					parent_key = (account_id, parent_profile_name, parent_segment_key)
					covered_segments.add(parent_key)

				continue

	print("Segment ladder trend analysis complete.")

	cur.close()
	conn.close()


if __name__ == "__main__":
	main()
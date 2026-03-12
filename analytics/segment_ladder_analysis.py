import os
import sys
import itertools
import psycopg2
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

from insight_utils import insert_insight


WINDOW_DAYS = 30

MIN_SPEND_RUB_WASTE = 3000
MIN_CLICKS_WASTE = 30

MIN_SPEND_RUB_CPA_BAD = 5000
MIN_CLICKS_CPA_BAD = 50
MIN_CONVERSIONS_CPA_BAD = 2
CPA_BAD_MULTIPLIER = 1.8

MIN_SPEND_RUB_WINNER = 5000
MIN_CLICKS_WINNER = 50
MIN_CONVERSIONS_WINNER = 3
WINNER_CPA_MULTIPLIER = 0.6

DIMENSIONS = ["ad_network_type", "device", "age", "gender"]

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

def fetch_account_cpa_map(cur):
	cur.execute("""
		SELECT
			account_id,
			cpa
		FROM kpi_account_30d
		WHERE cpa IS NOT NULL
			AND cpa > 0
	""")

	rows = cur.fetchall()

	result = {}
	for account_id, cpa in rows:
		result[account_id] = float(cpa)

	return result

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
		SELECT
			account_id,
			client_login,
			{select_dims},
			SUM(impressions) AS impressions,
			SUM(clicks) AS clicks,
			SUM(spend_rub) AS spend_rub,
			SUM(conversions) AS conversions,
			CASE
				WHEN SUM(conversions) > 0
					THEN SUM(spend_rub) / SUM(conversions)
				ELSE NULL
			END AS segment_cpa
		FROM kpi_segment_base_daily
		WHERE date >= CURRENT_DATE - INTERVAL '{WINDOW_DAYS} days'
		GROUP BY
			account_id,
			client_login,
			{group_dims}
	"""

	cur.execute(query)
	colnames = [desc[0] for desc in cur.description]
	rows = cur.fetchall()

	result = []
	for row in rows:
		row_dict = dict(zip(colnames, row))
		result.append(row_dict)

	return result


def main():
	conn = get_conn()
	cur = conn.cursor()

	account_cpa_map = fetch_account_cpa_map(cur)
	covered_segments = set()

	for profile in DIMENSION_PROFILES:
		print(f"Processing profile: {profile}")

		rows = fetch_profile_rows(cur, profile)

		for row in rows:
			account_id = row["account_id"]
			client_login = row["client_login"]
			impressions = int(row["impressions"] or 0)
			clicks = int(row["clicks"] or 0)
			spend_rub = float(row["spend_rub"] or 0)
			conversions = float(row["conversions"] or 0)
			segment_cpa = float(row["segment_cpa"]) if row["segment_cpa"] is not None else None
			account_cpa = account_cpa_map.get(account_id)
			
			if has_unknown_dimension(profile, row):
				continue

			segment_key = build_segment_key(profile, row)
			profile_name = "__".join(profile)

			current_key = (account_id, profile_name, segment_key)
			if current_key in covered_segments:
				print(
					f"Skipping covered parent segment for {account_id}: "
					f"profile={profile_name}, segment={segment_key}"
				)
				continue

			# 1. CPA_BAD
			if (
				spend_rub >= MIN_SPEND_RUB_CPA_BAD
				and clicks >= MIN_CLICKS_CPA_BAD
				and conversions >= MIN_CONVERSIONS_CPA_BAD
				and segment_cpa is not None
				and account_cpa is not None
				and account_cpa > 0
				and segment_cpa > account_cpa * CPA_BAD_MULTIPLIER
			):
				cpa_ratio = segment_cpa / account_cpa
				excess_cost = max(0.0, spend_rub - (conversions * account_cpa))

				print(
					f"Creating SEGMENT_LADDER_CPA_BAD for {account_id}: "
					f"profile={profile_name}, segment={segment_key}, "
					f"segment_cpa={segment_cpa:.0f}, account_cpa={account_cpa:.0f}"
				)

				insert_insight(
					account_id=account_id,
					type="SEGMENT_LADDER_CPA_BAD",
					entity_type="segment_ladder",
					entity_id=f"{profile_name}|{segment_key}|CPA_BAD",
					severity=76,
					impact_rub=excess_cost,
					title=f"Segment CPA is too high ({profile_name})",
					description=(
						f"{build_title(profile, row)} | "
						f"Segment CPA = {segment_cpa:.0f} ₽, "
						f"account CPA = {account_cpa:.0f} ₽, "
						f"ratio = {cpa_ratio:.1f}×"
					),
					recommendation=(
						"Review this segment level for bid reductions, exclusions, "
						"creative updates or campaign restructuring."
					),
					evidence={
						"profile": list(profile),
						"profile_name": profile_name,
						"segment_key": segment_key,
						"client_login": client_login,
						"impressions": impressions,
						"clicks": clicks,
						"spend_rub": spend_rub,
						"conversions": conversions,
						"segment_cpa": segment_cpa,
						"account_cpa": account_cpa,
						"cpa_ratio": cpa_ratio,
						"estimated_excess_cost_rub": excess_cost,
						"window_days": WINDOW_DAYS,
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

			# 2. WINNER
			if (
				spend_rub >= MIN_SPEND_RUB_WINNER
				and clicks >= MIN_CLICKS_WINNER
				and conversions >= MIN_CONVERSIONS_WINNER
				and segment_cpa is not None
				and account_cpa is not None
				and account_cpa > 0
				and segment_cpa < account_cpa * WINNER_CPA_MULTIPLIER
			):
				cpa_ratio = segment_cpa / account_cpa
				saved_rub = max(0.0, (account_cpa - segment_cpa) * conversions)

				print(
					f"Creating SEGMENT_LADDER_WINNER for {account_id}: "
					f"profile={profile_name}, segment={segment_key}, "
					f"segment_cpa={segment_cpa:.0f}, account_cpa={account_cpa:.0f}"
				)

				insert_insight(
					account_id=account_id,
					type="SEGMENT_LADDER_WINNER",
					entity_type="segment_ladder",
					entity_id=f"{profile_name}|{segment_key}|WINNER",
					severity=58,
					impact_rub=saved_rub,
					title=f"Segment outperforms account average ({profile_name})",
					description=(
						f"{build_title(profile, row)} | "
						f"Segment CPA = {segment_cpa:.0f} ₽, "
						f"account CPA = {account_cpa:.0f} ₽, "
						f"ratio = {cpa_ratio:.1f}×"
					),
					recommendation=(
						"Consider scaling this segment carefully: increase bids, "
						"allocate more budget, or isolate it into a dedicated campaign."
					),
					evidence={
						"profile": list(profile),
						"profile_name": profile_name,
						"segment_key": segment_key,
						"client_login": client_login,
						"impressions": impressions,
						"clicks": clicks,
						"spend_rub": spend_rub,
						"conversions": conversions,
						"segment_cpa": segment_cpa,
						"account_cpa": account_cpa,
						"cpa_ratio": cpa_ratio,
						"estimated_saved_rub": saved_rub,
						"window_days": WINDOW_DAYS,
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

			# 3. WASTE
			if spend_rub < MIN_SPEND_RUB_WASTE:
				continue

			if clicks < MIN_CLICKS_WASTE:
				continue

			if conversions > 0:
				continue

			print(
				f"Creating SEGMENT_LADDER_WASTE for {account_id}: "
				f"profile={profile_name}, segment={segment_key}, "
				f"spend={spend_rub:.0f}, clicks={clicks}"
			)

			insert_insight(
				account_id=account_id,
				type="SEGMENT_LADDER_WASTE",
				entity_type="segment_ladder",
				entity_id=f"{profile_name}|{segment_key}",
				severity=74,
				impact_rub=spend_rub,
				title=f"Segment wastes budget ({profile_name})",
				description=(
					f"{build_title(profile, row)} | "
					f"Spent {spend_rub:.0f} ₽ with {clicks} clicks and 0 conversions "
					f"over the last {WINDOW_DAYS} days"
				),
				recommendation=(
					"Review this segment level for exclusions, bid reductions, "
					"or campaign restructuring. If performance stays weak, "
					"exclude or isolate the segment."
				),
				evidence={
					"profile": list(profile),
					"profile_name": profile_name,
					"segment_key": segment_key,
					"client_login": client_login,
					"impressions": impressions,
					"clicks": clicks,
					"spend_rub": spend_rub,
					"conversions": conversions,
					"window_days": WINDOW_DAYS,
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

	print("Segment ladder analysis complete.")

	cur.close()
	conn.close()


if __name__ == "__main__":
	main()
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

from insight_utils import insert_insight


def get_conn():
	return psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)


def main():
	conn = get_conn()
	cur = conn.cursor()

	cur.execute("""
		SELECT
			t.account_id,
			t.cpa_last_3d,
			t.cpa_prev_4d,
			t.conv_per_day_last_3d,
			t.conv_per_day_prev_4d
		FROM kpi_account_trends t
	""")

	rows = cur.fetchall()
	cur.close()
	conn.close()

	for account_id, cpa_last, cpa_prev, conv_last, conv_prev in rows:
		cpa_last = float(cpa_last or 0)
		cpa_prev = float(cpa_prev or 0)
		conv_last = float(conv_last or 0)
		conv_prev = float(conv_prev or 0)

		# 1. CPA worsened materially
		if cpa_prev > 0 and cpa_last > cpa_prev * 1.3:
			change_pct = ((cpa_last - cpa_prev) / cpa_prev) * 100
			impact = max(0.0, cpa_last - cpa_prev)

			insert_insight(
				account_id=account_id,
				type="ACCOUNT_CPA_TREND_BAD",
				entity_type="account",
				entity_id=account_id,
				severity=80,
				impact_rub=impact,
				title=f"CPA worsened by {change_pct:.0f}%",
				description=f"CPA last 3d = {cpa_last:.0f}, previous 4d = {cpa_prev:.0f}",
				recommendation="Investigate campaigns, segments, and RSYA placements that deteriorated recently",
				evidence={
					"cpa_last_3d": cpa_last,
					"cpa_prev_4d": cpa_prev,
					"change_pct": change_pct,
				},
				confidence=1.0,
			)

		# 2. Leads/day dropped materially
		if conv_prev > 0 and conv_last < conv_prev * 0.7:
			change_pct = ((conv_prev - conv_last) / conv_prev) * 100
			impact = max(0.0, conv_prev - conv_last)

			insert_insight(
				account_id=account_id,
				type="ACCOUNT_LEADS_TREND_BAD",
				entity_type="account",
				entity_id=account_id,
				severity=75,
				impact_rub=impact,
				title=f"Leads/day dropped by {change_pct:.0f}%",
				description=f"Leads/day last 3d = {conv_last:.1f}, previous 4d = {conv_prev:.1f}",
				recommendation="Check recent budget, bid changes, segment drops and campaign delivery",
				evidence={
					"conv_per_day_last_3d": conv_last,
					"conv_per_day_prev_4d": conv_prev,
					"change_pct": change_pct,
				},
				confidence=1.0,
			)

	print("Trend analysis complete.")


if __name__ == "__main__":
	main()
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
			t.anchor_date,
			t.data_days_last_3d,
			t.data_days_prev_4d,
			t.cpa_last_3d,
			t.cpa_prev_4d,
			t.conv_per_day_last_3d,
			t.conv_per_day_prev_4d,
			COALESCE(at.cpa_plan, 0) AS cpa_plan
		FROM kpi_account_trends t
		LEFT JOIN account_targets at
			ON at.account_id = t.account_id
		WHERE at.is_active = true
	""")

	rows = cur.fetchall()

	for (
		account_id,
		anchor_date,
		data_days_last_3d,
		data_days_prev_4d,
		cpa_last,
		cpa_prev,
		conv_last,
		conv_prev,
		cpa_plan
	) in rows:
		cpa_last = float(cpa_last or 0)
		cpa_prev = float(cpa_prev or 0)
		conv_last = float(conv_last or 0)
		conv_prev = float(conv_prev or 0)
		cpa_plan = float(cpa_plan or 0)

		data_days_last_3d = int(data_days_last_3d or 0)
		data_days_prev_4d = int(data_days_prev_4d or 0)

		# Защита от ложных трендов на неполных данных
		if data_days_last_3d < 2 or data_days_prev_4d < 3:
			print(
				f"Skipping trends for {account_id}: "
				f"anchor={anchor_date}, "
				f"data_days_last_3d={data_days_last_3d}, "
				f"data_days_prev_4d={data_days_prev_4d}"
			)
			continue

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
			lost_leads_per_day = max(0.0, conv_prev - conv_last)
			impact = lost_leads_per_day * cpa_plan

			insert_insight(
				account_id=account_id,
				type="ACCOUNT_LEADS_TREND_BAD",
				entity_type="account",
				entity_id=account_id,
				severity=75,
				impact_rub=impact,
				title=f"Leads/day dropped by {change_pct:.0f}%",
				description=(
					f"Leads/day last 3d = {conv_last:.1f}, previous 4d = {conv_prev:.1f}, "
					f"lost = {lost_leads_per_day:.1f}/day, est. impact = {impact:.0f} ₽"
				),
				recommendation="Check recent budget, bid changes, segment drops and campaign delivery",
				evidence={
					"conv_per_day_last_3d": conv_last,
					"conv_per_day_prev_4d": conv_prev,
					"lost_leads_per_day": lost_leads_per_day,
					"cpa_plan": cpa_plan,
					"estimated_impact_rub": impact,
					"change_pct": change_pct,
				},
				confidence=1.0,
			)

	print("Trend analysis complete.")

	cur.close()
	conn.close()


if __name__ == "__main__":
	main()
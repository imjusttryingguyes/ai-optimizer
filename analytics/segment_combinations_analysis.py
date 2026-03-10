import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

from insight_utils import insert_insight


MIN_SPEND_RUB = 4000
MIN_CLICKS = 30


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
			account_id,
			client_login,
			ad_network_type,
			device,
			age,
			gender
	""")

	rows = cur.fetchall()

	for (
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
	) in rows:
		impressions = int(impressions or 0)
		clicks = int(clicks or 0)
		spend_rub = float(spend_rub or 0)
		conversions = float(conversions or 0)

		if spend_rub < MIN_SPEND_RUB:
			continue

		if clicks < MIN_CLICKS:
			continue

		if conversions > 0:
			continue

		segment_key = f"{ad_network_type}|{device}|{age}|{gender}"

		print(
			f"Creating SEGMENT_COMBINATION_WASTE for {account_id}: "
			f"{segment_key}, spend={spend_rub:.0f}, clicks={clicks}, conv={conversions}"
		)

		insert_insight(
			account_id=account_id,
			type="SEGMENT_COMBINATION_WASTE",
			entity_type="segment_combination",
			entity_id=segment_key,
			severity=70,
			impact_rub=spend_rub,
			title=f"Segment combination wastes budget: {device}, {age}, {gender}, {ad_network_type}",
			description=(
				f"Spent {spend_rub:.0f} ₽ with {clicks} clicks and 0 conversions "
				f"over the last 30 days"
			),
			recommendation=(
				"Review bids, creatives, campaign targeting and whether this segment "
				"should be excluded or separated"
			),
			evidence={
				"client_login": client_login,
				"ad_network_type": ad_network_type,
				"device": device,
				"age": age,
				"gender": gender,
				"impressions": impressions,
				"clicks": clicks,
				"spend_rub": spend_rub,
				"conversions": conversions,
				"window_days": 30,
			},
			confidence=1.0,
		)

	print("Segment combinations analysis complete.")

	cur.close()
	conn.close()


if __name__ == "__main__":
	main()
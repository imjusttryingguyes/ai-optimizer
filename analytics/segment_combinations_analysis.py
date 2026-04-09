import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

from insight_utils import insert_insight


MIN_SPEND_RUB = 4000
MIN_CLICKS = 30
MIN_SPEND_RUB_CPA_BAD = 5000
MIN_CLICKS_CPA_BAD = 50
MIN_CONVERSIONS_CPA_BAD = 2
CPA_BAD_MULTIPLIER = 1.8
MIN_SPEND_RUB_WINNER = 5000
MIN_CLICKS_WINNER = 30
MIN_CONVERSIONS_WINNER = 2
WINNER_CPA_MULTIPLIER = 0.6


def get_conn():
	return psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)

def has_unknown_values(*values):
	for value in values:
		if value is None:
			return True
		if isinstance(value, str) and not value.strip():
			return True
		if isinstance(value, (int, float)) and value == 0:
			return True
		if str(value).upper() == "UNKNOWN":
			return True
	return False


def build_segment_label(campaign_id, adgroup_id, criterion_id, device,
		ad_network_type, location_of_presence_name, targeting_location_name,
		age, gender, weekday):
	parts = [
		f"weekday={weekday}",
		f"campaign_id={campaign_id}",
		f"adgroup_id={adgroup_id}",
		f"criterion_id={criterion_id}",
	]
	if location_of_presence_name:
		parts.append(f"location={location_of_presence_name}")
	if targeting_location_name:
		parts.append(f"targeting={targeting_location_name}")
	parts.extend([
		f"device={device}",
		f"age={age}",
		f"gender={gender}",
		f"network={ad_network_type}",
	])
	return ", ".join(parts)


def main():
	conn = get_conn()
	cur = conn.cursor()

	cur.execute("""
		SELECT
			sc.account_id,
			sc.client_login,
			sc.campaign_id,
			sc.adgroup_id,
			sc.criterion_id,
			sc.ad_network_type,
			sc.device,
			sc.location_of_presence_name,
			sc.targeting_location_name,
			sc.age,
			sc.gender,
			sc.weekday,
			SUM(sc.impressions) AS impressions,
			SUM(sc.clicks) AS clicks,
			SUM(sc.spend_rub) AS spend_rub,
			SUM(sc.conversions) AS conversions,
			CASE
				WHEN SUM(sc.conversions) > 0
					THEN SUM(sc.spend_rub) / SUM(sc.conversions)
				ELSE NULL
			END AS segment_cpa,
			acc.cpa AS account_cpa
		FROM kpi_segment_combinations_30d sc
		LEFT JOIN kpi_account_30d acc
			ON acc.account_id = sc.account_id
		GROUP BY
			sc.account_id,
			sc.client_login,
			sc.campaign_id,
			sc.adgroup_id,
			sc.criterion_id,
			sc.ad_network_type,
			sc.device,
			sc.location_of_presence_name,
			sc.targeting_location_name,
			sc.age,
			sc.gender,
			sc.weekday,
			acc.cpa
	""")

	rows = cur.fetchall()

	for (
		account_id,
		client_login,
		campaign_id,
		adgroup_id,
		criterion_id,
		ad_network_type,
		device,
		location_of_presence_name,
		targeting_location_name,
		age,
		gender,
		weekday,
		impressions,
		clicks,
		spend_rub,
		conversions,
		segment_cpa,
		account_cpa
	) in rows:
		impressions = int(impressions or 0)
		clicks = int(clicks or 0)
		spend_rub = float(spend_rub or 0)
		conversions = float(conversions or 0)
		segment_cpa = float(segment_cpa) if segment_cpa is not None else None
		account_cpa = float(account_cpa) if account_cpa is not None else None

		if has_unknown_values(
			campaign_id,
			adgroup_id,
			criterion_id,
			ad_network_type,
			device,
			location_of_presence_name,
			targeting_location_name,
			age,
			gender,
			weekday,
		):
			continue

		if spend_rub < MIN_SPEND_RUB:
			continue

		if spend_rub < MIN_SPEND_RUB_CPA_BAD:
			continue

		if clicks < MIN_CLICKS_CPA_BAD:
			continue

		if conversions < MIN_CONVERSIONS_CPA_BAD:
			continue

		if segment_cpa is None or account_cpa is None or account_cpa <= 0:
			continue

		if segment_cpa <= account_cpa * CPA_BAD_MULTIPLIER:
			continue

		segment_key = (
			f"{weekday}|{campaign_id}|{adgroup_id}|{criterion_id}|"
			f"{location_of_presence_name}|{targeting_location_name}|{device}|{age}|{gender}|{ad_network_type}"
		)
		cpa_ratio = segment_cpa / account_cpa
		segment_label = build_segment_label(
			campaign_id,
			adgroup_id,
			criterion_id,
			device,
			ad_network_type,
			location_of_presence_name,
			targeting_location_name,
			age,
			gender,
			weekday,
		)

		print(
			f"Creating SEGMENT_COMBINATION_CPA_BAD for {account_id}: "
			f"{segment_key}, segment_cpa={segment_cpa:.0f}, "
			f"account_cpa={account_cpa:.0f}, ratio={cpa_ratio:.2f}"
		)

		insert_insight(
			account_id=account_id,
			type="SEGMENT_COMBINATION_CPA_BAD",
			entity_type="segment_combination",
			entity_id=f"{segment_key}|CPA_BAD",
			severity=72,
			impact_rub=max(0.0, spend_rub - (conversions * account_cpa)),
			title=(
				f"Segment CPA is {cpa_ratio:.1f}× worse than account average: "
				f"{segment_label}"
			),
			description=(
				f"Segment CPA = {segment_cpa:.0f} ₽, account CPA = {account_cpa:.0f} ₽, "
				f"spend = {spend_rub:.0f} ₽, conversions = {conversions:.1f}"
			),
			recommendation=(
				"Review bids, creatives and targeting for this segment. "
				"Consider lowering bids, splitting it into a separate campaign, or excluding it."
			),
			evidence={
				"client_login": client_login,
				"campaign_id": campaign_id,
				"adgroup_id": adgroup_id,
				"criterion_id": criterion_id,
				"ad_network_type": ad_network_type,
				"device": device,
				"location_of_presence_name": location_of_presence_name,
				"targeting_location_name": targeting_location_name,
				"age": age,
				"gender": gender,
				"weekday": weekday,
				"impressions": impressions,
				"clicks": clicks,
				"spend_rub": spend_rub,
				"conversions": conversions,
				"segment_cpa": segment_cpa,
				"account_cpa": account_cpa,
				"cpa_ratio": cpa_ratio,
				"window_days": 30,
			},
			confidence=1.0,
		)

		if spend_rub < MIN_SPEND_RUB_WINNER:
			continue

		if clicks < MIN_CLICKS_WINNER:
			continue

		if conversions < MIN_CONVERSIONS_WINNER:
			continue

		if segment_cpa is None or account_cpa is None or account_cpa <= 0:
			continue

		if segment_cpa >= account_cpa * WINNER_CPA_MULTIPLIER:
			continue

		segment_key = (
			f"{weekday}|{campaign_id}|{adgroup_id}|{criterion_id}|"
			f"{location_of_presence_name}|{targeting_location_name}|{device}|{age}|{gender}|{ad_network_type}"
		)
		cpa_ratio = segment_cpa / account_cpa
		saved_rub = max(0.0, (account_cpa - segment_cpa) * conversions)
		segment_label = build_segment_label(
			campaign_id,
			adgroup_id,
			criterion_id,
			device,
			ad_network_type,
			location_of_presence_name,
			targeting_location_name,
			age,
			gender,
			weekday,
		)

		print(
			f"Creating SEGMENT_COMBINATION_WINNER for {account_id}: "
			f"{segment_key}, segment_cpa={segment_cpa:.0f}, "
			f"account_cpa={account_cpa:.0f}, ratio={cpa_ratio:.2f}"
		)

		insert_insight(
			account_id=account_id,
			type="SEGMENT_COMBINATION_WINNER",
			entity_type="segment_combination",
			entity_id=f"{segment_key}|WINNER",
			severity=55,
			impact_rub=saved_rub,
			title=(
				f"Segment outperforms account average: {segment_label}"
			),
			description=(
				f"Segment CPA = {segment_cpa:.0f} ₽, account CPA = {account_cpa:.0f} ₽, "
				f"conversions = {conversions:.1f}, estimated upside = {saved_rub:.0f} ₽"
			),
			recommendation=(
				"Consider scaling this segment: increase bids carefully, "
				"allocate more budget, or split it into a dedicated campaign."
			),
			evidence={
				"client_login": client_login,
				"campaign_id": campaign_id,
				"adgroup_id": adgroup_id,
				"criterion_id": criterion_id,
				"ad_network_type": ad_network_type,
				"device": device,
				"location_of_presence_name": location_of_presence_name,
				"targeting_location_name": targeting_location_name,
				"age": age,
				"gender": gender,
				"weekday": weekday,
				"impressions": impressions,
				"clicks": clicks,
				"spend_rub": spend_rub,
				"conversions": conversions,
				"segment_cpa": segment_cpa,
				"account_cpa": account_cpa,
				"cpa_ratio": cpa_ratio,
				"estimated_upside_rub": saved_rub,
				"window_days": 30,
			},
			confidence=1.0,
		)

		if clicks < MIN_CLICKS:
			continue

		if conversions > 0:
			continue

		segment_key = (
			f"{weekday}|{campaign_id}|{adgroup_id}|{criterion_id}|"
			f"{location_of_presence_name}|{targeting_location_name}|{device}|{age}|{gender}|{ad_network_type}"
		)
		segment_label = build_segment_label(
			campaign_id,
			adgroup_id,
			criterion_id,
			device,
			ad_network_type,
			location_of_presence_name,
			targeting_location_name,
			age,
			gender,
			weekday,
		)

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
			title=f"Segment combination wastes budget: {segment_label}",
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
				"campaign_id": campaign_id,
				"adgroup_id": adgroup_id,
				"criterion_id": criterion_id,
				"ad_network_type": ad_network_type,
				"device": device,
				"location_of_presence_name": location_of_presence_name,
				"targeting_location_name": targeting_location_name,
				"age": age,
				"gender": gender,
				"weekday": weekday,
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
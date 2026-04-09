import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

from insight_utils import insert_insight


MIN_RECENT_SPEND_RUB = 1000
MIN_RECENT_CLICKS = 10
MIN_RECENT_CONVERSIONS = 1
MIN_BASELINE_CONVERSIONS = 1
MIN_RECENT_DATA_DAYS = 1
MIN_BASELINE_DATA_DAYS = 1

CPA_BAD_TREND_MULTIPLIER = 1.2
TREND_GOOD_CPA_MULTIPLIER = 0.8


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
			data_days_recent_7d,
			data_days_baseline_23d,
			impressions_recent_7d,
			clicks_recent_7d,
			spend_recent_7d,
			conversions_recent_7d,
			impressions_baseline_23d,
			clicks_baseline_23d,
			spend_baseline_23d,
			conversions_baseline_23d,
			cpa_recent_7d,
			cpa_baseline_23d,
			cr_recent_7d,
			cr_baseline_23d,
			conv_per_day_recent_7d,
			conv_per_day_baseline_23d
		FROM kpi_segment_combinations_trend_7d
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
		data_days_recent_7d,
		data_days_baseline_23d,
		impressions_recent_7d,
		clicks_recent_7d,
		spend_recent_7d,
		conversions_recent_7d,
		impressions_baseline_23d,
		clicks_baseline_23d,
		spend_baseline_23d,
		conversions_baseline_23d,
		cpa_recent_7d,
		cpa_baseline_23d,
		cr_recent_7d,
		cr_baseline_23d,
		conv_per_day_recent_7d,
		conv_per_day_baseline_23d
	) in rows:
		data_days_recent_7d = int(data_days_recent_7d or 0)
		data_days_baseline_23d = int(data_days_baseline_23d or 0)

		impressions_recent_7d = int(impressions_recent_7d or 0)
		clicks_recent_7d = int(clicks_recent_7d or 0)
		spend_recent_7d = float(spend_recent_7d or 0)
		conversions_recent_7d = float(conversions_recent_7d or 0)

		impressions_baseline_23d = int(impressions_baseline_23d or 0)
		clicks_baseline_23d = int(clicks_baseline_23d or 0)
		spend_baseline_23d = float(spend_baseline_23d or 0)
		conversions_baseline_23d = float(conversions_baseline_23d or 0)

		cpa_recent_7d = float(cpa_recent_7d) if cpa_recent_7d is not None else None
		cpa_baseline_23d = float(cpa_baseline_23d) if cpa_baseline_23d is not None else None
		cr_recent_7d = float(cr_recent_7d or 0)
		cr_baseline_23d = float(cr_baseline_23d or 0)
		conv_per_day_recent_7d = float(conv_per_day_recent_7d or 0)
		conv_per_day_baseline_23d = float(conv_per_day_baseline_23d or 0)
		
		segment_key = (
			f"{weekday}|{campaign_id}|{adgroup_id}|{criterion_id}|"
			f"{location_of_presence_name}|{targeting_location_name}|{device}|{age}|{gender}|{ad_network_type}"
		)
		
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

		if data_days_recent_7d < MIN_RECENT_DATA_DAYS:
			print(f"SKIP recent_days {account_id} {segment_key}")
			continue

		if data_days_baseline_23d < MIN_BASELINE_DATA_DAYS:
			print(f"SKIP baseline_days {account_id} {segment_key}")
			continue

		if spend_recent_7d < MIN_RECENT_SPEND_RUB:
			print(f"SKIP spend {account_id} {segment_key}")
			continue

		if clicks_recent_7d < MIN_RECENT_CLICKS:
			print(f"SKIP clicks {account_id} {segment_key}")
			continue

		if conversions_recent_7d < MIN_RECENT_CONVERSIONS:
			print(f"SKIP recent_conv {account_id} {segment_key}")
			continue

		if conversions_baseline_23d < MIN_BASELINE_CONVERSIONS:
			print(f"SKIP baseline_conv {account_id} {segment_key}")
			continue

		if cpa_recent_7d is None or cpa_baseline_23d is None or cpa_baseline_23d <= 0:
			print(f"SKIP cpa_null {account_id} {segment_key}")
			continue

		if cpa_recent_7d <= cpa_baseline_23d * CPA_BAD_TREND_MULTIPLIER:
			print(
				f"SKIP ratio {account_id} {segment_key}: "
				f"{cpa_recent_7d:.2f} <= {cpa_baseline_23d * CPA_BAD_TREND_MULTIPLIER:.2f}"
			)
			continue

		segment_key = (
			f"{weekday}|{campaign_id}|{adgroup_id}|{criterion_id}|"
			f"{location_of_presence_name}|{targeting_location_name}|{device}|{age}|{gender}|{ad_network_type}"
		)
		cpa_ratio = cpa_recent_7d / cpa_baseline_23d
		excess_cost = max(0.0, spend_recent_7d - (conversions_recent_7d * cpa_baseline_23d))
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
			f"Creating SEGMENT_COMBINATION_TREND_BAD for {account_id}: "
			f"{segment_key}, cpa_recent={cpa_recent_7d:.0f}, "
			f"cpa_baseline={cpa_baseline_23d:.0f}, ratio={cpa_ratio:.2f}"
		)

		insert_insight(
			account_id=account_id,
			type="SEGMENT_COMBINATION_TREND_BAD",
			entity_type="segment_combination",
			entity_id=f"{segment_key}|TREND_BAD",
			severity=78,
			impact_rub=excess_cost,
			title=(
				f"Segment trend worsened in last 7d: {segment_label}"
			),
			description=(
				f"CPA last 7d = {cpa_recent_7d:.0f} ₽, "
				f"baseline 23d = {cpa_baseline_23d:.0f} ₽, "
				f"ratio = {cpa_ratio:.1f}×"
			),
			recommendation=(
				"Check recent changes in bids, creatives, traffic quality and campaign delivery "
				"for this segment. Consider reducing bids or isolating the segment."
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
				"data_days_recent_7d": data_days_recent_7d,
				"data_days_baseline_23d": data_days_baseline_23d,
				"impressions_recent_7d": impressions_recent_7d,
				"clicks_recent_7d": clicks_recent_7d,
				"spend_recent_7d": spend_recent_7d,
				"conversions_recent_7d": conversions_recent_7d,
				"impressions_baseline_23d": impressions_baseline_23d,
				"clicks_baseline_23d": clicks_baseline_23d,
				"spend_baseline_23d": spend_baseline_23d,
				"conversions_baseline_23d": conversions_baseline_23d,
				"cpa_recent_7d": cpa_recent_7d,
				"cpa_baseline_23d": cpa_baseline_23d,
				"cr_recent_7d": cr_recent_7d,
				"cr_baseline_23d": cr_baseline_23d,
				"conv_per_day_recent_7d": conv_per_day_recent_7d,
				"conv_per_day_baseline_23d": conv_per_day_baseline_23d,
				"cpa_ratio": cpa_ratio,
				"window_recent_days": 7,
				"window_baseline_days": 23,
			},
			confidence=1.0,
		)

		if data_days_recent_7d < MIN_RECENT_DATA_DAYS:
			continue

		if data_days_baseline_23d < MIN_BASELINE_DATA_DAYS:
			continue

		if spend_recent_7d < MIN_RECENT_SPEND_RUB:
			continue

		if clicks_recent_7d < MIN_RECENT_CLICKS:
			continue

		if conversions_recent_7d < MIN_RECENT_CONVERSIONS:
			continue

		if conversions_baseline_23d < MIN_BASELINE_CONVERSIONS:
			continue

		if cpa_recent_7d is None or cpa_baseline_23d is None or cpa_baseline_23d <= 0:
			continue

		if cpa_recent_7d >= cpa_baseline_23d * TREND_GOOD_CPA_MULTIPLIER:
			continue

		if conv_per_day_recent_7d < conv_per_day_baseline_23d * 0.8:
			continue

		segment_key = (
			f"{weekday}|{campaign_id}|{adgroup_id}|{criterion_id}|"
			f"{location_of_presence_name}|{targeting_location_name}|{device}|{age}|{gender}|{ad_network_type}"
		)
		cpa_ratio = cpa_recent_7d / cpa_baseline_23d
		saved_rub = max(0.0, (cpa_baseline_23d - cpa_recent_7d) * conversions_recent_7d)
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
			f"Creating SEGMENT_COMBINATION_TREND_GOOD for {account_id}: "
			f"{segment_key}, cpa_recent={cpa_recent_7d:.0f}, "
			f"cpa_baseline={cpa_baseline_23d:.0f}, ratio={cpa_ratio:.2f}"
		)

		insert_insight(
			account_id=account_id,
			type="SEGMENT_COMBINATION_TREND_GOOD",
			entity_type="segment_combination",
			entity_id=f"{segment_key}|TREND_GOOD",
			severity=52,
			impact_rub=saved_rub,
			title=(
				f"Segment trend improved in last 7d: {segment_label}"
			),
			description=(
				f"CPA last 7d = {cpa_recent_7d:.0f} ₽, "
				f"baseline 23d = {cpa_baseline_23d:.0f} ₽, "
				f"ratio = {cpa_ratio:.1f}×, "
				f"conv/day last 7d = {conv_per_day_recent_7d:.2f}, "
				f"baseline = {conv_per_day_baseline_23d:.2f}"
			),
			recommendation=(
				"Consider scaling this segment carefully. Review whether bids, budgets, "
				"creatives or targeting should be expanded while performance remains strong."
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
				"data_days_recent_7d": data_days_recent_7d,
				"data_days_baseline_23d": data_days_baseline_23d,
				"impressions_recent_7d": impressions_recent_7d,
				"clicks_recent_7d": clicks_recent_7d,
				"spend_recent_7d": spend_recent_7d,
				"conversions_recent_7d": conversions_recent_7d,
				"impressions_baseline_23d": impressions_baseline_23d,
				"clicks_baseline_23d": clicks_baseline_23d,
				"spend_baseline_23d": spend_baseline_23d,
				"conversions_baseline_23d": conversions_baseline_23d,
				"cpa_recent_7d": cpa_recent_7d,
				"cpa_baseline_23d": cpa_baseline_23d,
				"cr_recent_7d": cr_recent_7d,
				"cr_baseline_23d": cr_baseline_23d,
				"conv_per_day_recent_7d": conv_per_day_recent_7d,
				"conv_per_day_baseline_23d": conv_per_day_baseline_23d,
				"cpa_ratio": cpa_ratio,
				"estimated_saved_rub": saved_rub,
				"window_recent_days": 7,
				"window_baseline_days": 23,
			},
			confidence=1.0,
		)

	print("Segment combinations trend analysis complete.")

	cur.close()
	conn.close()


if __name__ == "__main__":
	main()
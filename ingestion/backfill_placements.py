from datetime import date, timedelta
import os

import psycopg2

from ingestion.placements_loader import (
	CONFIG,
	get_conn,
	fetch_direct_report_tsv,
	parse_tsv,
	upsert_placement_fact,
)


ACCOUNT_ID = os.getenv("AI_ACCOUNT_ID") or os.getenv("DIRECT_CLIENT_LOGIN") or "mmg-sz"
FALLBACK_START_DATE = date(2026, 2, 4)


def daterange(start_date, end_date):
	current = start_date
	while current <= end_date:
		yield current
		current += timedelta(days=1)


def get_start_date():
	conn = psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)
	try:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT COALESCE(MAX(date), %s)
				FROM direct_daily_placement_fact
				WHERE account_id = %s
				""",
				(FALLBACK_START_DATE, ACCOUNT_ID),
			)
			last_loaded = cur.fetchone()[0]
		return last_loaded + timedelta(days=1)
	finally:
		conn.close()


def load_placements_day(day_str: str):
	tsv = fetch_direct_report_tsv(
		token=CONFIG["token"],
		client_login=CONFIG["client_login"],
		date_from=day_str,
		date_to=day_str,
		goal_ids=CONFIG["goal_ids"],
		attribution_models=CONFIG["attribution_models"],
		use_sandbox=CONFIG["use_sandbox"],
		max_retries=CONFIG["max_retries"],
		retry_sleep_seconds=CONFIG["retry_sleep_seconds"],
		only_ad_network=CONFIG["only_ad_network"],
	)

	df = parse_tsv(tsv, CONFIG["goal_ids"], CONFIG["attribution_models"])
	if df.empty:
		print(f"[{day_str}] No placement rows.")
		return 0

	conn = get_conn()
	try:
		inserted = upsert_placement_fact(
			conn,
			df,
			account_id=CONFIG["client_login"],
			client_login=CONFIG["client_login"],
		)
		return inserted
	finally:
		conn.close()


def main():
	start_date = get_start_date()
	end_date = date.today() - timedelta(days=1)

	print(f"ACCOUNT_ID={ACCOUNT_ID}")
	print(f"PLACEMENTS refresh range: {start_date} -> {end_date}")

	if start_date > end_date:
		print("Nothing to load for placements layer.")
		return

	total_rows = 0
	failed_days = []

	for d in daterange(start_date, end_date):
		day_str = d.strftime("%Y-%m-%d")
		try:
			inserted = load_placements_day(day_str)
			total_rows += inserted
			print(f"[{day_str}] placement={inserted}")
		except Exception as e:
			print(f"[{day_str}] ERROR: {e}")
			failed_days.append(day_str)

	print("")
	print("===== PLACEMENTS REFRESH COMPLETE =====")
	print(f"Total placement rows: {total_rows}")

	if failed_days:
		print("Failed days:")
		for day in failed_days:
			print(f"- {day}")
	else:
		print("No failed days.")


if __name__ == "__main__":
	main()
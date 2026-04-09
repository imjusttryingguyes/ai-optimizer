from datetime import date, timedelta
import os

import psycopg2

from ingestion.main import load_direct_day


ACCOUNT_ID = os.getenv("AI_ACCOUNT_ID") or os.getenv("DIRECT_CLIENT_LOGIN") or "mmg-sz"
FALLBACK_START_DATE = date(2026, 2, 4)


def get_conn():
	return psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)


def daterange(start_date, end_date):
	current = start_date
	while current <= end_date:
		yield current
		current += timedelta(days=1)


def get_start_date():
	conn = get_conn()
	try:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT COALESCE(MAX(date), %s)
				FROM direct_daily_spend_fact
				WHERE account_id = %s
				""",
				(FALLBACK_START_DATE, ACCOUNT_ID),
			)
			last_loaded = cur.fetchone()[0]
		return last_loaded + timedelta(days=1)
	finally:
		conn.close()


def main():
	start_date = get_start_date()
	end_date = date.today() - timedelta(days=1)

	print(f"ACCOUNT_ID={ACCOUNT_ID}")
	print(f"MAIN refresh range: {start_date} -> {end_date}")

	if start_date > end_date:
		print("Nothing to load for main layer.")
		return

	total_spend = 0
	total_conv = 0
	failed_days = []

	for d in daterange(start_date, end_date):
		day_str = d.strftime("%Y-%m-%d")
		try:
			inserted_spend, inserted_conv = load_direct_day(day_str, day_str)
			total_spend += inserted_spend
			total_conv += inserted_conv
			print(f"[{day_str}] spend={inserted_spend}, conv={inserted_conv}")
		except Exception as e:
			print(f"[{day_str}] ERROR: {e}")
			failed_days.append(day_str)

	print("")
	print("===== MAIN REFRESH COMPLETE =====")
	print(f"Total spend rows: {total_spend}")
	print(f"Total conv rows: {total_conv}")

	if failed_days:
		print("Failed days:")
		for day in failed_days:
			print(f"- {day}")
	else:
		print("No failed days.")


if __name__ == "__main__":
	main()
from datetime import datetime, timedelta

from placements_loader import (
	CONFIG,
	get_conn,
	fetch_direct_report_tsv,
	parse_tsv,
	upsert_placement_fact,
)


def daterange(start_date, end_date):
	current = start_date
	while current <= end_date:
		yield current
		current += timedelta(days=1)


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
	inserted = upsert_placement_fact(
		conn,
		df,
		account_id=CONFIG["client_login"],
		client_login=CONFIG["client_login"]
	)
	conn.close()

	print(f"[{day_str}] placement={inserted}")
	return inserted


def main():
	date_from = "2026-02-04"
	date_to = "2026-03-05"

	start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
	end_date = datetime.strptime(date_to, "%Y-%m-%d").date()

	total_rows = 0
	failed_days = []

	for d in daterange(start_date, end_date):
		day_str = d.strftime("%Y-%m-%d")

		try:
			inserted = load_placements_day(day_str)
			total_rows += inserted
		except Exception as e:
			print(f"[{day_str}] ERROR: {e}")
			failed_days.append(day_str)

	print("")
	print("===== BACKFILL PLACEMENTS COMPLETE =====")
	print(f"Total placement rows: {total_rows}")

	if failed_days:
		print("Failed days:")
		for day in failed_days:
			print(f"- {day}")
	else:
		print("No failed days.")


if __name__ == "__main__":
	main()
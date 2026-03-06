from datetime import datetime, timedelta

from main import load_direct_day


def daterange(start_date, end_date):
	current = start_date
	while current <= end_date:
		yield current
		current += timedelta(days=1)


def main():
	date_from = "2026-02-04"
	date_to = "2026-03-05"

	start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
	end_date = datetime.strptime(date_to, "%Y-%m-%d").date()

	total_spend = 0
	total_conv = 0
	failed_days = []

	for d in daterange(start_date, end_date):
		day_str = d.strftime("%Y-%m-%d")

		try:
			inserted_spend, inserted_conv = load_direct_day(day_str, day_str)
			total_spend += inserted_spend
			total_conv += inserted_conv
		except Exception as e:
			print(f"[{day_str}] ERROR: {e}")
			failed_days.append(day_str)

	print("")
	print("===== BACKFILL MAIN COMPLETE =====")
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
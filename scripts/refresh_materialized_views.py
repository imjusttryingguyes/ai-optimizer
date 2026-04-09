import os

import psycopg2


MATERIALIZED_VIEWS = [
	"kpi_account_vs_plan",
	"kpi_account_trends",
	"kpi_account_30d",
	"kpi_campaign_vs_account",
	"kpi_rsy_placements_7d",
	"kpi_segment_base_daily",
	"kpi_segment_device_network",
	"kpi_segment_combinations_30d",
	"kpi_segment_combinations_trend_7d",
	"kpi_segment_ladder_trend_base",
]


def get_conn():
	return psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)


def refresh_mv(cur, mv_name: str):
	print(f"Refreshing {mv_name}...")
	cur.execute(f"REFRESH MATERIALIZED VIEW {mv_name};")
	print(f"Done: {mv_name}")


def main():
	conn = get_conn()
	conn.autocommit = True

	try:
		with conn.cursor() as cur:
			for mv_name in MATERIALIZED_VIEWS:
				refresh_mv(cur, mv_name)
	finally:
		conn.close()

	print("All materialized views refreshed.")


if __name__ == "__main__":
	main()
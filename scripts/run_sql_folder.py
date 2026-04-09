import os
from pathlib import Path

import psycopg2


SQL_DIR = Path("sql")


def get_conn():
	return psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)


def read_sql(path: Path) -> str:
	with open(path, "r", encoding="utf-8") as f:
		sql = f.read()

	if not sql or not sql.strip():
		return ""

	return sql.strip()


def run_sql_file(cur, path: Path):
	sql = read_sql(path)

	if not sql:
		print(f"Skipping empty file: {path.name}")
		return

	print(f"Running {path.name}...")
	cur.execute(sql)
	print(f"Done: {path.name}")


def main():
	files = sorted(SQL_DIR.glob("*.sql"))

	if not files:
		print("No .sql files found in /sql")
		return

	conn = get_conn()
	conn.autocommit = True

	try:
		with conn.cursor() as cur:
			for path in files:
				run_sql_file(cur, path)
	finally:
		conn.close()

	print("All SQL executed.")


if __name__ == "__main__":
	main()